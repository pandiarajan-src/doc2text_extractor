import logging
import re
import zipfile
from pathlib import Path

import aiofiles
import magic
from fastapi import HTTPException, UploadFile

from .extractors import extractor_factory

logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self, uploads_dir: Path, outputs_dir: Path, max_file_size: int = 50 * 1024 * 1024):
        self.uploads_dir = Path(uploads_dir)
        self.outputs_dir = Path(outputs_dir)
        self.max_file_size = max_file_size

        # Create directories if they don't exist
        self.uploads_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)

        # Supported file extensions
        self.supported_extensions = extractor_factory.get_supported_extensions()

        logger.info(
            f"FileManager initialized with supported extensions: {self.supported_extensions}"
        )

    def sanitize_filename(self, filename: str) -> str:
        # Remove any path separators and dangerous characters
        filename = re.sub(r"[^\w\-_\.]", "_", filename)

        # Remove multiple consecutive underscores
        filename = re.sub(r"_+", "_", filename)

        # Ensure it's not empty and has an extension
        if not filename or filename.startswith("."):
            filename = "document" + filename

        return filename

    def validate_file_type(self, file_path: Path) -> tuple[bool, str]:
        try:
            # Check file extension
            extension = file_path.suffix.lower()
            if extension not in self.supported_extensions:
                return False, f"Unsupported file extension: {extension}"

            # Check MIME type
            mime = magic.Magic(mime=True)
            file_mime_type = mime.from_file(str(file_path))

            # Create a temporary extractor to validate
            extractor = extractor_factory.create_extractor(file_path)
            if not extractor:
                return False, f"No suitable extractor found for file type: {extension}"

            logger.info(f"File validated: {file_path.name}, MIME: {file_mime_type}")
            return True, file_mime_type

        except Exception as e:
            logger.error(f"File validation error for {file_path}: {e}")
            return False, f"File validation failed: {str(e)}"

    async def save_upload_file(self, upload_file: UploadFile) -> Path:
        if not upload_file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Check file size
        if upload_file.size and upload_file.size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {self.max_file_size // (1024 * 1024)}MB",
            )

        # Sanitize filename
        safe_filename = self.sanitize_filename(upload_file.filename)

        # Create unique filename to avoid conflicts
        import time

        timestamp = str(int(time.time()))
        name, ext = safe_filename.rsplit(".", 1) if "." in safe_filename else (safe_filename, "")
        unique_filename = f"{name}_{timestamp}.{ext}" if ext else f"{name}_{timestamp}"

        file_path = self.uploads_dir / unique_filename

        try:
            # Save file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                content = await upload_file.read()

                # Double-check file size
                if len(content) > self.max_file_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {self.max_file_size // (1024 * 1024)}MB",
                    )

                await f.write(content)

            # Validate file type
            is_valid, mime_type_or_error = self.validate_file_type(file_path)
            if not is_valid:
                # Clean up invalid file
                file_path.unlink()
                raise HTTPException(status_code=400, detail=mime_type_or_error)

            logger.info(f"Successfully saved upload file: {file_path}")
            return file_path

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Clean up file if something went wrong
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup file {file_path}: {cleanup_error}")

            logger.error(f"Failed to save upload file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}") from e

    def create_result_zip(self, job_id: str) -> Path | None:
        job_output_dir = self.outputs_dir / job_id

        if not job_output_dir.exists():
            logger.warning(f"Job output directory not found: {job_output_dir}")
            return None

        try:
            # Create temporary zip file
            zip_path = job_output_dir / f"{job_id}_results.zip"

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add all files in the job output directory
                for file_path in job_output_dir.rglob("*"):
                    if file_path.is_file() and file_path.name != zip_path.name:
                        # Calculate relative path for archive
                        arcname = file_path.relative_to(job_output_dir)
                        zipf.write(file_path, arcname)

            logger.info(f"Created result zip: {zip_path}")
            return zip_path

        except Exception as e:
            logger.error(f"Failed to create result zip for job {job_id}: {e}")
            return None

    def cleanup_file(self, file_path: Path) -> bool:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
        return False

    def get_job_output_dir(self, job_id: str) -> Path:
        return self.outputs_dir / job_id

    def job_output_exists(self, job_id: str) -> bool:
        job_dir = self.outputs_dir / job_id
        return job_dir.exists() and any(job_dir.iterdir())

    def get_job_files(self, job_id: str) -> list[Path]:
        job_dir = self.outputs_dir / job_id
        if not job_dir.exists():
            return []

        return [f for f in job_dir.rglob("*") if f.is_file()]

    def cleanup_uploads_dir(self, older_than_hours: int = 1):
        try:
            import time

            current_time = time.time()
            cutoff_time = current_time - (older_than_hours * 3600)

            cleaned_count = 0
            for file_path in self.uploads_dir.iterdir():
                if file_path.is_file():
                    file_age = file_path.stat().st_mtime
                    if file_age < cutoff_time:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to cleanup old upload {file_path}: {e}")

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old upload files")

        except Exception as e:
            logger.error(f"Error during uploads directory cleanup: {e}")
