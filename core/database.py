"""
Database models and connection management using SQLAlchemy.
"""

import enum
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_PATH = Path("data/jobs.db")
DATABASE_PATH.parent.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with thread-safe settings for SQLite
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


class JobStatus(enum.Enum):
    """Job status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    """Job model for tracking document extraction jobs."""

    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True, index=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    output_path = Column(String, nullable=True)

    # Additional fields for better tracking
    text_length = Column(Integer, nullable=True)
    images_count = Column(Integer, nullable=True)
    extractor_used = Column(String, nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds

    def to_dict(self) -> dict:
        """Convert job to dictionary."""
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
            "text_length": self.text_length,
            "images_count": self.images_count,
            "extractor_used": self.extractor_used,
            "processing_time": self.processing_time,
        }


def init_db():
    """Initialize database by creating all tables."""
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {DATABASE_PATH}")


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def migrate_from_json(json_file_path: Path):
    """Migrate existing jobs from JSON file to SQLite database."""
    import json

    if not json_file_path.exists():
        logger.info("No existing JSON file to migrate")
        return

    try:
        with open(json_file_path) as f:
            jobs_data = json.load(f)

        migrated_count = 0
        with get_db_session() as db:
            for job_id, job_data in jobs_data.items():
                # Check if job already exists
                existing = db.query(Job).filter(Job.job_id == job_id).first()
                if existing:
                    continue

                # Create new job
                job = Job(
                    job_id=job_id,
                    status=JobStatus(job_data["status"]),
                    filename=job_data["filename"],
                    file_size=job_data["file_size"],
                    file_type=job_data["file_type"],
                    created_at=(
                        datetime.fromisoformat(job_data["created_at"])
                        if job_data["created_at"]
                        else None
                    ),
                    started_at=(
                        datetime.fromisoformat(job_data["started_at"])
                        if job_data.get("started_at")
                        else None
                    ),
                    completed_at=(
                        datetime.fromisoformat(job_data["completed_at"])
                        if job_data.get("completed_at")
                        else None
                    ),
                    error_message=job_data.get("error_message"),
                    output_path=job_data.get("output_path"),
                )
                db.add(job)
                migrated_count += 1

            db.commit()
            logger.info(f"Migrated {migrated_count} jobs from JSON to SQLite")

    except Exception as e:
        logger.error(f"Failed to migrate from JSON: {e}")


# Initialize database on module import
init_db()
