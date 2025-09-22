FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    curl \
    libmagic1 \
    libmagic-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy uv configuration files and README first for better caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/api/health || exit 1

# Run the application using uv
CMD ["uv", "run", "python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8081"]