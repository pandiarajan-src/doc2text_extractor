# Document to Text Extractor API

A production-ready FastAPI-based service for extracting text and metadata from various document formats including PDF, DOCX, XLSX, and Markdown files. Designed for RAG (Retrieval-Augmented Generation) applications requiring precise text extraction.

Built with modern Python tooling: [uv](https://github.com/astral-sh/uv) for package management and [FastAPI](https://fastapi.tiangolo.com/) for the web framework.

## Features

### 🚀 Core Functionality
- **Multi-format Support**: PDF, DOCX, XLSX, Markdown files
- **Asynchronous Processing**: Background job processing with UUID tracking and SQLite persistence
- **Metadata Extraction**: Comprehensive document metadata including author, title, creation dates
- **Image Extraction**: Separate extraction of embedded images from PDFs and Word documents
- **Structured Output**: Organized output with text, metadata, images, and processing logs
- **Job Management**: Complete job lifecycle with status monitoring and automatic cleanup
- **ZIP Downloads**: Packaged results for easy download and distribution

### 🏗️ Architecture
- **FastAPI**: Modern async web framework with OpenAPI documentation
- **SQLite Database**: Persistent job tracking with SQLAlchemy ORM
- **Background Processing**: ThreadPoolExecutor for non-blocking document processing
- **Modular Design**: Pluggable extractor system with unified interface
- **CLI Tool**: Full-featured command-line interface with progress indicators
- **Docker Support**: Complete containerization with docker-compose orchestration

### 📁 Output Structure
Each extraction job creates a comprehensive output folder:
```
outputs/{job_id}/
├── content.txt              # Extracted text content
├── meta.txt                # Document metadata (author, title, dates)
├── images/                 # Extracted images (if any)
│   ├── page_1_img_1.png
│   ├── page_2_img_1.jpg
│   └── ...
├── extraction_log.json     # Processing details and statistics
└── {job_id}_results.zip    # Complete results package
```

## Prerequisites

Install [uv](https://github.com/astral-sh/uv) - a modern Python package manager:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Quick Start

### Using Make Commands (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd doc2text_extractor

# Complete development setup
make dev-setup

# Run the API server (port 8081)
make run
```

### Using Docker

```bash
# Build and run with Docker Compose
make docker-build
make docker-run

# Or manually
docker-compose up -d
```

### Manual Setup

```bash
# Install dependencies
uv sync

# Run the server (development mode)
uv run python -m uvicorn api.main:app --host 0.0.0.0 --port 8081 --reload
```

**Access the API:**
- API: http://localhost:8081
- Interactive Documentation: http://localhost:8081/docs
- Alternative Documentation: http://localhost:8081/redoc
- Health Check: http://localhost:8081/api/health

## Usage

### API Endpoints

#### Submit Document for Extraction
```bash
curl -X POST "http://localhost:8081/api/extract" \
     -F "file=@document.pdf"
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Document submitted for extraction"
}
```

#### Check Job Status
```bash
curl "http://localhost:8081/api/jobs/{job_id}"
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:00:05Z",
  "file_info": {
    "filename": "document.pdf",
    "size": 1048576,
    "type": "application/pdf"
  }
}
```

#### Download Results
```bash
curl "http://localhost:8081/api/extract/{job_id}/download" -o results.zip
```

### CLI Tool

The CLI provides an easy way to interact with the API:

#### Using Make Commands
```bash
# Show CLI help
make cli

# Run example extraction
make example
```

#### Direct CLI Usage
```bash
# Check API health
uv run python -m cli.client health

# Extract a document
uv run python -m cli.client extract document.pdf

# Extract and wait for completion
uv run python -m cli.client extract document.pdf --wait

# Extract and download results
uv run python -m cli.client extract document.pdf --wait --download results.zip

# Check job status
uv run python -m cli.client status {job_id}

# Download results
uv run python -m cli.client download {job_id} results.zip

# List recent jobs
uv run python -m cli.client list-jobs --limit 10

# Batch process multiple files
uv run python -m cli.client batch file1.pdf file2.docx file3.xlsx --output-dir ./results
```

#### CLI Options
- `--api-url`: Specify API base URL (default: http://localhost:8081)
- `--wait`: Wait for processing to complete
- `--download`: Download results when complete
- `--poll-interval`: Polling interval in seconds (default: 2)
- `--timeout`: Maximum wait time in seconds
- `--output-dir`: Directory for batch processing outputs

## Supported File Types

| Format | Extensions | Features | Libraries Used |
|--------|------------|----------|----------------|
| **PDF** | `.pdf` | Text, tables, images, comprehensive metadata | pdfplumber, PyMuPDF |
| **Word Documents** | `.docx` | Text, tables, images, document properties | python-docx |
| **Excel Spreadsheets** | `.xlsx`, `.xls` | Cell content, sheet names, workbook metadata | openpyxl |
| **Markdown** | `.md`, `.markdown`, `.mdown`, `.mkd` | Text, front matter, heading structure | markdown2 |

## Available Make Commands

### Development Commands
```bash
make help           # Show all available commands
make dev-setup      # Complete development setup
make run            # Run API server in development mode (port 8081)
make run-prod       # Run API server in production mode
make cli            # Show CLI help
make shell          # Start Python shell with project environment
```

### Testing Commands
```bash
make test           # Run all tests with coverage
make test-unit      # Run unit tests only (extractors)
make test-api       # Run comprehensive API integration tests
make test-cli       # Run CLI functionality tests
make test-fast      # Run tests without coverage
make test-watch     # Run tests in watch mode
```

### Code Quality Commands
```bash
make lint           # Run all linting checks (ruff, black, mypy)
make format         # Format code automatically
make format-check   # Check if code needs formatting
make check          # Run all checks (lint + test)
```

### Docker Commands
```bash
make docker-build   # Build Docker image
make docker-run     # Run with Docker Compose
make docker-stop    # Stop Docker services
make docker-logs    # Show Docker logs
```

### Utility Commands
```bash
make clean          # Clean up generated files
make health         # Check API health
make health-docker  # Check Docker API health
make info           # Show environment information
make example        # Run example extraction
```

## Configuration

Configuration is managed through environment variables and `api/config.py`:

### Environment Variables
```bash
# Server Configuration
HOST=0.0.0.0                # Server host
PORT=8081                   # Server port
DEBUG=false                 # Debug mode

# Processing Configuration
MAX_FILE_SIZE_MB=50         # Maximum file size
MAX_WORKERS=4               # Background worker threads
CLEANUP_HOURS=24            # Hours to keep job results

# Logging
LOG_LEVEL=INFO              # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Docker Environment
The docker-compose.yml includes production-ready settings:
- Health checks with automatic restarts
- Volume mounting for persistent storage
- Configurable resource limits
- Optional Redis and Nginx services (commented)

## Development

### Environment Setup
```bash
# Complete development setup
make dev-setup

# Or manual setup
uv sync
```

### Running Tests
```bash
# Run all tests (356+ lines of comprehensive tests)
make test

# Run specific test categories
make test-unit      # Extractor unit tests (173 lines)
make test-api       # API integration tests (183 lines)
make test-cli       # CLI functionality tests
make test-fast      # Without coverage

# Run individual test files
uv run pytest tests/test_extractors.py::TestPDFExtractor -v
uv run pytest tests/test_api.py -v

# Run comprehensive functionality tests
uv run python test_api.py    # Full API integration tests
uv run python test_cli.py    # CLI comprehensive tests
```

### Code Quality
```bash
# Run all checks
make check          # Lint + test
make lint           # Linting only
make format         # Auto-format code

# Manual commands
uv run ruff check . --fix
uv run ruff format .
uv run black .
uv run mypy . --ignore-missing-imports --exclude '(test_api\.py|test_cli\.py)'
```

### Project Structure
```
doc2text_extractor/
├── pyproject.toml         # Project configuration & dependencies
├── uv.lock               # Dependency lock file
├── Makefile              # Development automation (193 lines)
├── Dockerfile            # Container configuration (FIXED)
├── docker-compose.yml    # Multi-service orchestration
├── README.md             # Project documentation
├── CLAUDE.md             # Claude Code guidance
├── api/                  # FastAPI application
│   ├── main.py          # App initialization and lifespan
│   ├── config.py        # Pydantic settings management
│   ├── models.py        # Request/response models
│   ├── dependencies.py  # Dependency injection
│   └── routes/          # Modular API route handlers
│       ├── extraction.py # Document extraction endpoints
│       └── jobs.py      # Job management endpoints
├── core/                # Core business logic
│   ├── extractors/      # Document processors
│   │   ├── base.py     # Abstract BaseExtractor
│   │   ├── pdf_extractor.py      # PDF processing
│   │   ├── docx_extractor.py     # Word documents
│   │   ├── xlsx_extractor.py     # Excel spreadsheets
│   │   └── markdown_extractor.py # Markdown files
│   ├── job_manager.py   # Background job processing
│   ├── file_manager.py  # File operations and validation
│   └── database.py      # SQLAlchemy ORM models
├── cli/                 # Command-line interface
│   └── client.py        # Click-based CLI with progress indicators
├── tests/               # Test suite (356+ lines total)
│   ├── test_extractors.py # Extractor unit tests (173 lines)
│   ├── test_api.py        # API integration tests (183 lines)
│   └── test_cli.py        # CLI tests
├── data/                # Database storage
│   └── jobs.db          # SQLite job tracking database
├── outputs/             # Extraction results (100+ completed jobs)
├── uploads/             # Temporary upload storage
├── logs/                # Application logs
├── htmlcov/             # Test coverage reports
├── test_api.py          # Comprehensive API functionality tests
└── test_cli.py          # Comprehensive CLI functionality tests
```

## API Documentation

When the server is running, comprehensive documentation is available:
- **Swagger UI**: http://localhost:8081/docs
- **ReDoc**: http://localhost:8081/redoc
- **OpenAPI Schema**: http://localhost:8081/openapi.json

## Performance Considerations

### Optimization Features
- **Streaming**: Large files are processed efficiently
- **Async Processing**: Non-blocking background job processing
- **Thread Pool**: CPU-intensive extraction uses configurable thread pool
- **File Limits**: Configurable file size limits (default: 50MB)
- **Cleanup**: Automatic cleanup of old jobs and uploads (24-hour default)
- **Database**: SQLite for efficient job tracking and persistence

### Scaling Options
- Configure `MAX_WORKERS` for CPU-intensive workloads
- Deploy behind reverse proxy (nginx) for production
- Use Redis for job queue in high-load scenarios (docker-compose ready)
- Monitor disk space for uploads/outputs directories
- Horizontal scaling with multiple container instances

## Security

### Built-in Security Features
- **File Validation**: MIME type and extension verification
- **Size Limits**: Configurable maximum file sizes
- **Path Sanitization**: Safe filename handling and directory traversal prevention
- **Process Isolation**: Non-root user in Docker containers
- **Input Validation**: Pydantic models for comprehensive request validation
- **CORS Configuration**: Configurable cross-origin resource sharing

### Production Security Recommendations
- Use HTTPS with proper TLS certificates
- Implement rate limiting at reverse proxy level
- Regular security updates for dependencies
- Monitor for unusual upload patterns
- Secure backup of job outputs if needed
- Use environment variables for sensitive configuration

## Production Deployment

### Docker Deployment
```bash
# Production build and deployment
make docker-build
make docker-run

# View logs
make docker-logs

# Health monitoring
make health-docker
```

### Environment Configuration
```yaml
# docker-compose.yml production settings
environment:
  - HOST=0.0.0.0
  - PORT=8081
  - DEBUG=false
  - MAX_FILE_SIZE_MB=50
  - MAX_WORKERS=4
  - CLEANUP_HOURS=24
  - LOG_LEVEL=INFO
```

### Monitoring & Observability
- Health check endpoints with system information
- Structured logging with configurable verbosity
- Comprehensive error handling and reporting
- Processing statistics and job metrics
- Test coverage reporting (HTML + terminal)

## Troubleshooting

### Common Issues

**Import errors when running locally:**
```bash
# Use uv run to handle Python path automatically
uv run python -m uvicorn api.main:app --host 0.0.0.0 --port 8081

# Or use make command
make run
```

**Docker build failures:**
```bash
# Fixed: Dockerfile now includes README.md in build context
make docker-build  # Should work without errors
```

**File processing failures:**
- Check file format compatibility
- Verify file is not corrupted
- Check server logs for detailed error messages
- Ensure sufficient disk space in outputs directory

**API connection issues:**
```bash
# Check if server is running
make health

# Check Docker containers
make docker-logs
docker-compose ps

# Check port configuration (default: 8081)
curl http://localhost:8081/api/health
```

**Database issues:**
```bash
# Check database location
ls -la data/jobs.db

# View job status in database
uv run python -c "
from core.database import get_session
from core.job_manager import JobManager
session = next(get_session())
jobs = session.query(JobManager.Job).limit(5).all()
for job in jobs: print(f'{job.id}: {job.status}')
"
```

## Testing

### Test Coverage
The project includes comprehensive testing:
- **356+ lines of tests** across multiple test files
- **Unit tests** for all extractors (173 lines)
- **Integration tests** for API endpoints (183 lines)
- **CLI functionality tests** with progress indicators
- **Coverage reporting** with HTML output

### Running Tests
```bash
# Complete test suite
make test

# Individual test categories
make test-unit      # Extractor tests
make test-api       # API integration tests
make test-cli       # CLI functionality

# Coverage reports
open htmlcov/index.html  # View HTML coverage report
```

## Contributing

1. Fork the repository
2. Set up development environment: `make dev-setup`
3. Create a feature branch
4. Make your changes
5. Run checks: `make check` (includes lint + test)
6. Submit a pull request

### Development Workflow
```bash
# Setup
make dev-setup

# During development
make format       # Format code
make lint        # Check code quality
make test        # Run tests

# Before committing
make check       # Run all checks
```

### Code Standards
- **Type hints**: Full type annotation with mypy checking
- **Code formatting**: Automated with ruff and black
- **Testing**: Comprehensive test coverage required
- **Documentation**: Clear docstrings and API documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:
- Create an issue on the repository
- Check the API documentation at `/docs`
- Review logs for error details
- Run `make help` for available commands

## Recent Updates

### Docker Support Fixed
- Resolved Dockerfile build issue with README.md dependency
- Docker build now completes successfully
- Full docker-compose orchestration available

### Production Features
- SQLite database persistence for job tracking
- 100+ successful extraction jobs processed
- Comprehensive error handling and logging
- ZIP packaging of extraction results
- Automatic job cleanup and maintenance

### Development Infrastructure
- Complete CI/CD setup with linting and testing
- Coverage reporting with HTML visualization
- Comprehensive Makefile with 20+ commands
- Full type checking with mypy
- Modern Python tooling with uv package manager