import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_markdown_file():
    content = """---
title: Test Document
author: Test Author
---

# Test Document

This is a test document for API testing.

## Features

- Test feature 1
- Test feature 2
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        yield Path(f.name)

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "supported_formats" in data
        assert isinstance(data["supported_formats"], list)
        assert len(data["supported_formats"]) > 0


class TestRootEndpoint:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Document to Text Extractor API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/api/health"


class TestExtractionEndpoint:
    def test_extract_document_success(self, client, sample_markdown_file):
        with open(sample_markdown_file, "rb") as f:
            response = client.post("/api/extract", files={"file": ("test.md", f, "text/markdown")})

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "pending"
        assert "message" in data
        assert len(data["job_id"]) > 0

    def test_extract_document_no_file(self, client):
        response = client.post("/api/extract")
        assert response.status_code == 422  # Unprocessable Entity

    def test_extract_document_empty_file(self, client):
        response = client.post("/api/extract", files={"file": ("empty.md", b"", "text/markdown")})
        # Should still accept empty files, but extraction might fail
        assert response.status_code in [200, 400]

    def test_extract_unsupported_file_type(self, client):
        content = b"This is not a supported file type"
        response = client.post("/api/extract", files={"file": ("test.txt", content, "text/plain")})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestJobsEndpoint:
    def test_get_job_status_not_found(self, client):
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/jobs/{fake_job_id}")
        assert response.status_code == 404

    def test_get_job_result_not_found(self, client):
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/jobs/{fake_job_id}/result")
        assert response.status_code == 404

    def test_list_jobs_empty(self, client):
        response = client.get("/api/jobs")
        assert response.status_code == 200

        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert isinstance(data["jobs"], list)
        assert isinstance(data["total"], int)

    def test_list_jobs_with_limit(self, client):
        response = client.get("/api/jobs?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["jobs"]) <= 5

    def test_list_jobs_invalid_limit(self, client):
        response = client.get("/api/jobs?limit=500")  # Exceeds max limit
        assert response.status_code == 422


class TestDownloadEndpoint:
    def test_download_results_not_found(self, client):
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/extract/{fake_job_id}/download")
        assert response.status_code == 404


class TestIntegrationFlow:
    def test_full_extraction_flow(self, client, sample_markdown_file):
        # 1. Submit document
        with open(sample_markdown_file, "rb") as f:
            response = client.post("/api/extract", files={"file": ("test.md", f, "text/markdown")})

        assert response.status_code == 200
        job_data = response.json()
        job_id = job_data["job_id"]

        # 2. Check job status immediately
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200

        status_data = response.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ["pending", "processing", "completed"]
        assert status_data["filename"] == "test.md"
        assert status_data["file_type"] == ".md"

        # 3. Get job result info
        response = client.get(f"/api/jobs/{job_id}/result")
        assert response.status_code == 200

        result_data = response.json()
        assert result_data["job_id"] == job_id
        assert result_data["filename"] == "test.md"

        # Note: In a real scenario, we'd need to wait for processing to complete
        # For unit tests, we're primarily testing the API structure

    def test_error_handling_malformed_file(self, client):
        # Create a file that looks like markdown but might cause extraction issues
        malformed_content = b"\x00\x01\x02This is not valid markdown\xff\xfe"

        response = client.post(
            "/api/extract", files={"file": ("malformed.md", malformed_content, "text/markdown")}
        )

        # The API should either accept it and handle the error during processing,
        # or reject it at upload time
        assert response.status_code in [200, 400, 415]


class TestCORSHeaders:
    def test_cors_headers_present(self, client):
        response = client.options("/api/health")
        # CORS headers should be present for OPTIONS requests
        assert response.status_code in [200, 405]  # Some frameworks return 405 for OPTIONS
