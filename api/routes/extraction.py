import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.dependencies import get_file_manager, get_job_manager
from api.models import JobCreateResponse, JobStatus
from core.file_manager import FileManager
from core.job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Managers are now injected as dependencies


@router.post("/extract", response_model=JobCreateResponse)
async def extract_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_manager: JobManager = Depends(get_job_manager),
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Submit a document for text extraction.

    The file will be processed asynchronously. Use the returned job_id
    to check the status and retrieve results.
    """
    try:
        # Save uploaded file
        file_path = await file_manager.save_upload_file(file)

        # Create job
        job_id = job_manager.create_job(
            filename=file.filename,
            file_size=file.size or file_path.stat().st_size,
            file_type=file_path.suffix.lower(),
        )

        # Start background processing
        background_tasks.add_task(job_manager.process_job, job_id, file_path)

        # Start cleanup task if not already running
        background_tasks.add_task(job_manager.start_cleanup_task)

        return JobCreateResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=f"Document '{file.filename}' submitted for extraction. Use the job_id to check status.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}") from e


@router.get("/extract/{job_id}/download")
async def download_results(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    file_manager: FileManager = Depends(get_file_manager),
):
    """
    Download the extraction results as a ZIP file.

    The ZIP file contains:
    - content.txt: Extracted text content
    - meta.txt: Document metadata
    - images/: Any extracted images
    - extraction_log.json: Processing details
    """
    job_info = job_manager.get_job(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400, detail=f"Job not completed. Current status: {job_info.status.value}"
        )

    # Check if output exists
    if not file_manager.job_output_exists(job_id):
        raise HTTPException(status_code=404, detail="Job results not found")

    # Create ZIP file
    zip_path = file_manager.create_result_zip(job_id)
    if not zip_path:
        raise HTTPException(status_code=500, detail="Failed to create results archive")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"{job_info.filename}_{job_id}_results.zip",
        headers={
            "Content-Disposition": f"attachment; filename={job_info.filename}_{job_id}_results.zip"
        },
    )
