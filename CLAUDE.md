# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Document to Text Extractor API - A production-ready FastAPI-based service for extracting text and metadata from various document formats (PDF, DOCX, XLSX, Markdown) designed for RAG applications. Uses local Python libraries for processing without external LLM dependencies.

## Architecture

### Core Components

- **FastAPI Application** (`api/`): RESTful API with async processing, CORS support, structured routing
  - `main.py`: FastAPI app initialization, lifespan management, CORS configuration
  - `config.py`: Pydantic settings management with environment variable support
  - `models.py`: Request/response models and data validation schemas
  - `dependencies.py`: Dependency injection for shared services (JobManager, FileManager)
  - `routes/`: Modular route handlers for extraction and job management endpoints

- **Extractors** (`core/extractors/`): Document-specific extractors with unified interface
  - `base.py`: Abstract BaseExtractor with common functionality and error handling
  - `pdf_extractor.py`: PDF processing using pdfplumber and PyMuPDF for text and images
  - `docx_extractor.py`: Microsoft Word document extraction with embedded media support
  - `xlsx_extractor.py`: Excel spreadsheet processing with multi-sheet support
  - `markdown_extractor.py`: Markdown to HTML conversion with metadata extraction

- **Core Services**:
  - `job_manager.py`: Background job processing with UUID tracking, status monitoring, SQLite persistence
  - `file_manager.py`: File validation, secure storage, cleanup operations, MIME type detection
  - `database.py`: SQLAlchemy ORM models for job persistence and status tracking

- **CLI Client** (`cli/client.py`): Full-featured command-line interface using Click
  - Health checks, file extraction, batch processing, download management
  - Progress indicators, colored output, comprehensive error handling

### Processing Flow

1. **Upload**: File uploaded via API endpoint → validated by FileManager (size, type, security)
2. **Job Creation**: JobManager creates UUID-tracked job → stores in SQLite database
3. **Background Processing**: ThreadPoolExecutor processes job asynchronously
4. **Extraction**: ExtractorFactory selects appropriate extractor → processes document
5. **Output**: Results saved to `outputs/{job_id}/` with structured files:
   - `content.txt`: Extracted plain text content
   - `meta.txt`: Document metadata (author, creation date, etc.)
   - `images/`: Extracted images (if any)
   - `extraction_log.json`: Processing logs and statistics
   - `{job_id}_results.zip`: Complete results package for download

## Development Commands

### Essential Commands

```bash
# Install dependencies (using uv package manager)
uv sync

# Run API server (development) - Port 8081
make run
# or: uv run python -m uvicorn api.main:app --host 0.0.0.0 --port 8081 --reload

# Run tests with coverage
make test
# or: uv run pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html

# Run specific test categories
make test-unit     # Unit tests only (extractors)
make test-api      # Comprehensive API tests
make test-cli      # CLI functionality tests
make test-fast     # Tests without coverage

# Linting and formatting
make lint          # Run all linting checks (ruff, black, mypy)
make format        # Auto-format code with ruff and black
# Manual commands:
uv run ruff check . --fix
uv run ruff format .
uv run black .
uv run mypy . --ignore-missing-imports --exclude '(test_api\.py|test_cli\.py)'

# CLI usage
uv run python -m cli.client health
uv run python -m cli.client extract document.pdf --wait --download results.zip
uv run python -m cli.client batch file1.pdf file2.docx --output-dir ./results

# Docker operations (FIXED - now working)
make docker-build    # Build Docker image
make docker-run      # Start with docker-compose
make docker-stop     # Stop services
make docker-logs     # View logs
```

### Testing Individual Components

```bash
# Run single test file
uv run pytest tests/test_extractors.py::TestPDFExtractor -v

# Run comprehensive functionality tests
uv run python test_api.py    # Full API integration tests
uv run python test_cli.py    # CLI comprehensive tests

# Test with specific file
uv run python -c "
from core.extractors import PDFExtractor
from pathlib import Path
extractor = PDFExtractor()
result = extractor.extract(Path('document.pdf'), Path('outputs/test'))
print(result.success, result.error)
"
```

## Key Implementation Details

### Extractor Pattern

All extractors inherit from `BaseExtractor` (core/extractors/base.py) and must implement:
- `extract()` method returning `ExtractionResult`
- `_extract_text()` for document text extraction
- `_extract_images()` for embedded image extraction
- `_extract_metadata()` for document metadata

### Job Processing

- Jobs tracked via UUID in `JobManager` (core/job_manager.py)
- Background processing using ThreadPoolExecutor with configurable workers
- Status states: pending → processing → completed/failed
- SQLite database persistence (data/jobs.db)
- Automatic cleanup after `CLEANUP_HOURS` (default: 24)
- ZIP packaging of results for download

### API Endpoints

- `POST /api/extract`: Submit document for extraction
- `GET /api/jobs/{job_id}`: Check job status and progress
- `GET /api/extract/{job_id}/download`: Download results as ZIP
- `GET /api/health`: Health check endpoint with system info

### Database Schema

SQLite database with job tracking:
- Job ID (UUID), status, timestamps
- File information and processing metadata
- Error logs and processing statistics

## Configuration

Settings managed via Pydantic in `api/config.py`:
- `MAX_FILE_SIZE_MB`: Maximum upload size (default: 50MB)
- `MAX_WORKERS`: Background worker threads (default: 4)
- `CLEANUP_HOURS`: Job retention period (default: 24)
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8081)

## Dependencies

Managed by `uv` package manager (pyproject.toml):

### Core Dependencies
- FastAPI[all]>=0.104.1: Web framework with async support
- uvicorn[standard]>=0.24.0: ASGI server
- pydantic>=2.5.0: Data validation and settings
- SQLAlchemy>=2.0.23: Database ORM

### Document Processing
- pdfplumber>=0.10.3: PDF text extraction
- PyMuPDF>=1.23.9: PDF image extraction
- python-docx>=1.1.0: Microsoft Word documents
- openpyxl>=3.1.2: Excel spreadsheets
- markdown2>=2.4.10: Markdown processing
- Pillow>=10.1.0: Image processing

### Development Tools
- pytest>=7.4.3: Testing framework
- ruff>=0.1.6: Fast Python linter
- black>=23.11.0: Code formatter
- mypy>=1.7.1: Type checking

## File Structure

```
doc2text_extractor/
├── api/                    # FastAPI application
│   ├── main.py            # App initialization and lifespan
│   ├── config.py          # Settings and configuration
│   ├── models.py          # Pydantic models
│   ├── dependencies.py    # Dependency injection
│   └── routes/            # API route handlers
├── core/                  # Core business logic
│   ├── extractors/        # Document processors
│   ├── job_manager.py     # Background job processing
│   ├── file_manager.py    # File operations
│   └── database.py        # SQLAlchemy models
├── cli/                   # Command-line interface
│   └── client.py          # Click-based CLI
├── tests/                 # Test suite (356 lines total)
│   ├── test_extractors.py # Extractor unit tests (173 lines)
│   ├── test_api.py        # API integration tests (183 lines)
│   └── test_cli.py        # CLI tests (empty - tests via test_cli.py)
├── data/                  # Database and persistent storage
├── outputs/               # Extraction results (100+ job outputs)
├── uploads/               # Temporary file uploads
├── logs/                  # Application logs
├── htmlcov/              # Test coverage reports
├── Dockerfile            # Container configuration (FIXED)
├── docker-compose.yml    # Multi-service orchestration
├── pyproject.toml        # Project configuration and dependencies
├── Makefile              # Development automation
├── test_api.py           # Comprehensive API functionality tests
└── test_cli.py           # Comprehensive CLI functionality tests
```

## Production Deployment

### Docker Support
- Multi-stage Docker build for optimal image size
- Docker Compose orchestration with health checks
- Volume mounting for persistent storage
- Environment variable configuration
- Optional Redis and Nginx services (commented)

### Security Features
- File type validation and MIME checking
- Size limits and upload restrictions
- Non-root container user
- CORS configuration
- Input sanitization

### Monitoring & Observability
- Structured logging with configurable levels
- Health check endpoints
- Comprehensive error handling
- Processing statistics and metrics
- Coverage reporting (HTML + terminal)

## Recent Updates

### Docker Build Fix
- Fixed Dockerfile to include README.md in build context before dependency installation
- Resolved pyproject.toml reference error during `uv sync`
- Docker build now completes successfully

### Testing Infrastructure
- Comprehensive test suite with 356+ lines of tests
- Coverage reporting with HTML output
- Separate test files for different components
- Integration tests for full API functionality

### Project Maturity
- Production-ready codebase with proper error handling
- Extensive job processing with 100+ completed extractions
- Full CI/CD setup with linting, formatting, and type checking
- Database persistence with SQLite backend

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.