"""
Shared dependencies and singleton instances for the API.
"""

import logging
from collections.abc import Generator

from sqlalchemy.orm import Session

from api.config import settings
from core.database import get_db_session, migrate_from_json
from core.file_manager import FileManager
from core.job_manager import JobManager

logger = logging.getLogger(__name__)


# Create singleton instances
_job_manager_instance = None
_file_manager_instance = None


def get_job_manager() -> JobManager:
    """Get or create singleton JobManager instance."""
    global _job_manager_instance
    if _job_manager_instance is None:
        logger.info("Creating JobManager singleton instance")
        _job_manager_instance = JobManager(
            outputs_dir=settings.outputs_path,
            max_workers=settings.max_workers,
            cleanup_hours=settings.cleanup_hours,
        )
        # Migrate existing JSON data on first initialization
        json_file = settings.outputs_path / "jobs.json"
        if json_file.exists():
            logger.info("Migrating existing jobs from JSON to SQLite")
            migrate_from_json(json_file)
    return _job_manager_instance


def get_file_manager() -> FileManager:
    """Get or create singleton FileManager instance."""
    global _file_manager_instance
    if _file_manager_instance is None:
        logger.info("Creating FileManager singleton instance")
        _file_manager_instance = FileManager(
            uploads_dir=settings.uploads_path,
            outputs_dir=settings.outputs_path,
            max_file_size=settings.max_file_size_bytes,
        )
    return _file_manager_instance


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    with get_db_session() as db:
        yield db
