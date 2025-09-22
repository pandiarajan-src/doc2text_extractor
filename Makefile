# Document to Text Extractor Makefile
# Requires uv package manager: https://github.com/astral-sh/uv

.PHONY: help install install-dev sync run run-prod cli test lint format clean build docker-build docker-run docker-stop

# Default target
help: ## Show this help message
	@echo "Document to Text Extractor - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Prerequisites:"
	@echo "  - uv package manager: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo ""

# Installation and Environment
install: ## Install production dependencies
	@echo "📦 Installing production dependencies with uv..."
	uv sync --no-dev

install-dev: ## Install all dependencies including dev tools
	@echo "📦 Installing all dependencies (including dev) with uv..."
	uv sync

sync: ## Sync dependencies (same as install-dev)
	@echo "🔄 Syncing dependencies..."
	uv sync

# Development
run: ## Run the API server in development mode
	@echo "🚀 Starting API server..."
	uv run python -m uvicorn api.main:app --host 0.0.0.0 --port 8081 --reload

run-prod: ## Run the API server in production mode
	@echo "🚀 Starting API server (production)..."
	uv run python -m api.main

cli: ## Show CLI help
	@echo "🖥️  CLI Help:"
	uv run python -m cli.client --help

# Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	uv run python -m pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	@echo "🔬 Running unit tests..."
	uv run python -m pytest tests/test_extractors.py -v

test-api: ## Run comprehensive API functionality tests
	@echo "🌐 Running comprehensive API tests..."
	uv run python test_api.py

test-cli: ## Run comprehensive CLI functionality tests
	@echo "🖥️  Running comprehensive CLI tests..."
	uv run python test_cli.py

test-fast: ## Run tests without coverage
	@echo "⚡ Running fast tests..."
	uv run python -m pytest tests/ -v

test-watch: ## Run tests in watch mode
	@echo "👀 Running tests in watch mode..."
	uv run python -m pytest tests/ -v --tb=short -f

# Code Quality
lint: ## Run all linting checks
	@echo "🔍 Running linting checks..."
	@echo "  📝 Ruff linting..."
	uv run ruff check .
	@echo "  🎨 Ruff formatting check..."
	uv run ruff format --check .
	@echo "  ⚫ Black formatting check..."
	uv run black --check .
	@echo "  🔍 MyPy type checking..."
	uv run mypy . --ignore-missing-imports --no-error-summary --exclude '(test_api\.py|test_cli\.py)'
	@echo "✅ All linting checks completed!"

format: ## Format code automatically
	@echo "🎨 Formatting code..."
	uv run ruff check . --fix
	uv run ruff format .
	uv run black .
	@echo "✅ Code formatted!"

format-check: ## Check if code needs formatting
	@echo "🔍 Checking code formatting..."
	uv run ruff format --check .
	uv run black --check .

# Docker
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t doc2text-extractor:latest .

docker-run: ## Run with Docker Compose
	@echo "🐳 Starting services with Docker Compose..."
	docker-compose up -d

docker-stop: ## Stop Docker services
	@echo "🛑 Stopping Docker services..."
	docker-compose down

docker-logs: ## Show Docker logs
	@echo "📋 Docker logs:"
	docker-compose logs -f doc2text-api

# Project Management
clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf uploads/* outputs/*
	@echo "✅ Cleanup completed!"

build: ## Build the package
	@echo "📦 Building package..."
	uv build

# Development helpers
shell: ## Start a Python shell with project environment
	@echo "🐍 Starting Python shell..."
	uv run python

jupyter: ## Start Jupyter notebook (if available)
	@echo "📓 Starting Jupyter notebook..."
	uv run jupyter notebook

# Health checks
health: ## Check API health
	@echo "🏥 Checking API health..."
	curl -s http://localhost:8081/api/health | python -m json.tool || echo "❌ API not running or unhealthy"

health-docker: ## Check Docker API health
	@echo "🏥 Checking Docker API health..."
	curl -s http://localhost:8081/api/health | python -m json.tool || echo "❌ Docker API not running or unhealthy"

# Example usage
example: ## Run example extraction
	@echo "📄 Running example extraction..."
	@if [ -f "tests/test_files/sample.md" ]; then \
		echo "Extracting sample.md..."; \
		uv run doc2text extract tests/test_files/sample.md --wait; \
	else \
		echo "❌ Sample file not found. Run 'make install-dev' first."; \
	fi

# CI/CD helpers
ci-install: ## Install for CI environment
	@echo "🤖 Installing for CI..."
	uv sync --frozen

ci-test: ## Run tests for CI
	@echo "🤖 Running CI tests..."
	uv run python -m pytest tests/ -v --tb=short --cov=. --cov-report=xml

ci-lint: ## Run linting for CI
	@echo "🤖 Running CI linting..."
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy . --ignore-missing-imports

# All-in-one commands
dev-setup: install-dev ## Complete development setup
	@echo "🛠️  Development setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make run' to start the API server"
	@echo "  2. Run 'make test' to run tests"
	@echo "  3. Run 'make lint' to check code quality"
	@echo "  4. Visit http://localhost:8081/docs for API documentation"

check: lint test ## Run all checks (lint + test)
	@echo "✅ All checks passed!"

# Show environment info
info: ## Show environment information
	@echo "📊 Environment Information:"
	@echo "  Python: $$(python --version)"
	@echo "  UV: $$(uv --version)"
	@echo "  Project: $$(pwd)"
	@echo "  Virtual env: $$VIRTUAL_ENV"
	@echo ""
	@echo "📦 Project dependencies:"
	@uv tree --depth 1 2>/dev/null || echo "  Run 'make install-dev' to see dependency tree"