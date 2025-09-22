import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_file_manager, get_job_manager
from api.models import (
    ExtractionResultSummary,
    JobListResponse,
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
)
from core.file_manager import FileManager
from core.job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Managers are now injected as dependencies


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, job_manager: JobManager = Depends(get_job_manager)):
    """
    Get the current status of an extraction job.

    Returns detailed information about the job including:
    - Current status (pending, processing, completed, failed)
    - File information
    - Timestamps
    - Error details if applicable
    """
    job_info = job_manager.get_job(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_info.job_id,
        status=job_info.status,
        filename=job_info.filename,
        file_size=job_info.file_size,
        file_type=job_info.file_type,
        created_at=job_info.created_at,
        started_at=job_info.started_at,
        completed_at=job_info.completed_at,
        error_message=job_info.error_message,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Get extraction results summary for a completed job.

    Provides information about the extracted content without
    downloading the full results.
    """
    job_info = job_manager.get_job(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    response = JobResultResponse(
        job_id=job_info.job_id, status=job_info.status, filename=job_info.filename
    )

    if job_info.status == JobStatus.COMPLETED and job_info.output_path:
        try:
            # Read extraction log for summary
            log_file = file_manager.get_job_output_dir(job_id) / "extraction_log.json"
            if log_file.exists():
                with open(log_file, encoding="utf-8") as f:
                    log_data = json.load(f)

                response.result_summary = ExtractionResultSummary(
                    text_length=log_data.get("text_length", 0),
                    images_count=log_data.get("images_count", 0),
                    has_metadata=True,  # We always generate metadata
                    extraction_method=log_data.get("extractor_used", "unknown"),
                )

            response.download_url = f"/api/extract/{job_id}/download"

        except Exception as e:
            logger.warning(f"Failed to read extraction log for job {job_id}: {e}")

    return response


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(default=50, le=200, description="Maximum number of jobs to return"),
    status: JobStatus | None = Query(default=None, description="Filter by job status"),
    job_manager: JobManager = Depends(get_job_manager),
):
    """
    List recent extraction jobs.

    Optionally filter by status and limit the number of results.
    Jobs are returned in reverse chronological order (newest first).
    """
    try:
        jobs = job_manager.list_jobs(limit=limit)

        # Filter by status if specified
        if status:
            jobs = [job for job in jobs if job.status == status]

        job_responses = []
        for job in jobs:
            job_responses.append(
                JobStatusResponse(
                    job_id=job.job_id,
                    status=job.status,
                    filename=job.filename,
                    file_size=job.file_size,
                    file_type=job.file_type,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    error_message=job.error_message,
                )
            )

        return JobListResponse(jobs=job_responses, total=len(job_responses))

    except Exception as e:
        logger.error(f"List jobs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs") from e
