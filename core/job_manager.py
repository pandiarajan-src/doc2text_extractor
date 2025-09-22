import asyncio
import json
import logging
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from .database import Job, JobStatus, get_db_session
from .extractors import extractor_factory

logger = logging.getLogger(__name__)


class JobInfo:
    """Legacy JobInfo class for compatibility."""

    def __init__(self, job: Job):
        self.job_id = job.job_id
        # Convert database enum to API enum
        from api.models import JobStatus as APIJobStatus

        if job.status:
            self.status = APIJobStatus(job.status.value.lower())
        else:
            self.status = APIJobStatus.PENDING
        self.filename = job.filename
        self.file_size = job.file_size
        self.file_type = job.file_type
        self.created_at = job.created_at
        self.started_at = job.started_at
        self.completed_at = job.completed_at
        self.error_message = job.error_message
        self.output_path = job.output_path

    def to_dict(self):
        """Convert to dictionary for compatibility."""
        return {
            "job_id": self.job_id,
            "status": self.status.value if self.status else None,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "output_path": self.output_path,
        }


class JobManager:
    def __init__(self, outputs_dir: Path, max_workers: int = 4, cleanup_hours: int = 24):
        self.outputs_dir = Path(outputs_dir)
        self.outputs_dir.mkdir(exist_ok=True)

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cleanup_hours = cleanup_hours

        # Background cleanup task
        self._cleanup_task = None

        logger.info("JobManager initialized with SQLite database")

    def create_job(self, filename: str, file_size: int, file_type: str) -> str:
        """Create a new job in the database."""
        job_id = str(uuid.uuid4())

        with get_db_session() as db:
            job = Job(
                job_id=job_id,
                status=JobStatus.PENDING,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                created_at=datetime.now(),
            )
            db.add(job)
            db.commit()

        logger.info(f"Created job {job_id} for file {filename}")
        return job_id

    def get_job(self, job_id: str) -> JobInfo | None:
        """Get job information from the database."""
        with get_db_session() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                return JobInfo(job)
            return None

    def list_jobs(self, limit: int = 100) -> list[JobInfo]:
        """List jobs from the database."""
        with get_db_session() as db:
            jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
            return [JobInfo(job) for job in jobs]

    async def process_job(self, job_id: str, file_path: Path) -> bool:
        """Process a job - extract document content."""
        start_time = datetime.now()

        # Update job status to processing
        with get_db_session() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now()
            db.commit()

        try:
            # Create output directory for this job
            output_dir = self.outputs_dir / job_id
            output_dir.mkdir(exist_ok=True)

            # Get appropriate extractor
            extractor = extractor_factory.create_extractor(file_path)
            if not extractor:
                raise ValueError(f"No extractor found for file type: {file_path.suffix}")

            # Run extraction in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, extractor.extract, file_path, output_dir
            )

            # Update job with results
            with get_db_session() as db:
                job = db.query(Job).filter(Job.job_id == job_id).first()

                if result.success:
                    job.status = JobStatus.COMPLETED
                    job.output_path = str(output_dir)
                    job.text_length = len(result.text) if result.text else 0
                    job.images_count = len(result.images) if result.images else 0
                    job.extractor_used = extractor.__class__.__name__

                    # Save extraction log
                    extraction_log = {
                        "job_id": job_id,
                        "filename": job.filename,
                        "extractor_used": extractor.__class__.__name__,
                        "extraction_timestamp": datetime.now().isoformat(),
                        "text_length": job.text_length,
                        "images_count": job.images_count,
                        "success": True,
                    }

                    log_file = output_dir / "extraction_log.json"
                    with open(log_file, "w", encoding="utf-8") as f:
                        json.dump(extraction_log, f, indent=2)

                    logger.info(f"Job {job_id} completed successfully")
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = result.error
                    logger.error(f"Job {job_id} failed: {result.error}")

                job.completed_at = datetime.now()
                job.processing_time = (job.completed_at - start_time).total_seconds()
                db.commit()

        except Exception as e:
            logger.error(f"Job {job_id} failed with exception: {e}")

            with get_db_session() as db:
                job = db.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                    job.processing_time = (job.completed_at - start_time).total_seconds()
                    db.commit()

        finally:
            # Clean up uploaded file
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup uploaded file {file_path}: {e}")

        # Check final status
        with get_db_session() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            return job and job.status == JobStatus.COMPLETED

    async def cleanup_old_jobs(self):
        """Clean up old jobs from database and filesystem."""
        cutoff_time = datetime.now() - timedelta(hours=self.cleanup_hours)

        with get_db_session() as db:
            # Find old completed or abandoned pending jobs
            old_jobs = (
                db.query(Job)
                .filter(
                    ((Job.status == JobStatus.COMPLETED) & (Job.completed_at < cutoff_time))
                    | ((Job.status == JobStatus.PENDING) & (Job.created_at < cutoff_time))
                )
                .all()
            )

            for job in old_jobs:
                try:
                    # Remove output directory
                    output_dir = self.outputs_dir / job.job_id
                    if output_dir.exists():
                        shutil.rmtree(output_dir)

                    # Remove from database
                    db.delete(job)
                    logger.info(f"Cleaned up old job {job.job_id}")

                except Exception as e:
                    logger.warning(f"Failed to cleanup job {job.job_id}: {e}")

            db.commit()

            if old_jobs:
                logger.info(f"Cleaned up {len(old_jobs)} old jobs")

    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())

    async def _cleanup_worker(self):
        """Background worker for periodic cleanup."""
        while True:
            try:
                await self.cleanup_old_jobs()
                await asyncio.sleep(3600)  # Run cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def shutdown(self):
        """Shutdown the JobManager."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        self.executor.shutdown(wait=True)
