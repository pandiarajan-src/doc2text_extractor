import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.dependencies import get_job_manager
from api.models import ErrorResponse, HealthResponse
from api.routes import extraction, jobs
from core.extractors import extractor_factory

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Managers are now initialized in dependencies.py as singletons


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting doc2text_extractor API")
    logger.info(f"Supported file extensions: {extractor_factory.get_supported_extensions()}")

    # Get shared JobManager instance and start background tasks
    job_manager = get_job_manager()
    await job_manager.start_cleanup_task()

    yield

    # Shutdown
    logger.info("Shutting down doc2text_extractor API")
    job_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Document to Text Extractor API",
    description="Extract text and metadata from PDF, DOCX, XLSX, and Markdown documents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.detail, detail=getattr(exc, "detail", None)).model_dump(
            mode="json"
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error", detail="An unexpected error occurred"
        ).model_dump(mode="json"),
    )


# Include routers
app.include_router(extraction.router, prefix="/api", tags=["extraction"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the current status of the API and supported file formats.
    """
    return HealthResponse(supported_formats=extractor_factory.get_supported_extensions())


@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "name": "Document to Text Extractor API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


def run_server():
    """Entry point for running the server via CLI."""
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run_server()
