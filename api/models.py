from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreateResponse(BaseModel):
    job_id: str = Field(..., description="Unique identifier for the extraction job")
    status: JobStatus = Field(..., description="Current status of the job")
    message: str = Field(..., description="Human-readable status message")


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    file_size: int
    file_type: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int


class ExtractionResultSummary(BaseModel):
    text_length: int
    images_count: int
    has_metadata: bool
    extraction_method: str


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    result_summary: ExtractionResultSummary | None = None
    download_url: str | None = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    supported_formats: list[str]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
