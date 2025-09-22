#!/usr/bin/env python
"""
Comprehensive API testing script for Document to Text Extractor API.
Tests all exposed API functionality with all supported file types.
"""

import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx

API_BASE_URL = os.environ.get("API_URL", "http://localhost:8081")
TEST_FILES_DIR = Path("tests/test_files")
OUTPUT_DIR = Path("test_outputs")


class APITester:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.test_results = []
        self.jobs_created = []

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp and level."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def test_endpoint(
        self, name: str, method: str, endpoint: str, expected_status: list[int] = None, **kwargs
    ) -> dict[Any, Any] | None:
        """Test a single endpoint and record results."""
        if expected_status is None:
            expected_status = [200, 201]

        url = f"{self.base_url}{endpoint}"
        test_passed = False
        response_data = None

        try:
            self.log(f"Testing: {name} - {method} {endpoint}")
            with httpx.Client() as client:
                response = client.request(method, url, **kwargs)

            if response.status_code in expected_status:
                test_passed = True
                response_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.content
                )
                self.log(f"✅ {name}: PASSED (Status: {response.status_code})", "SUCCESS")
            else:
                self.log(
                    f"❌ {name}: FAILED (Status: {response.status_code}, Expected: {expected_status})",
                    "ERROR",
                )
                self.log(f"Response: {response.text}", "ERROR")

        except Exception as e:
            self.log(f"❌ {name}: FAILED with exception: {str(e)}", "ERROR")

        self.test_results.append(
            {
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "passed": test_passed,
                "response": response_data,
            }
        )

        return response_data

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        return self.test_endpoint("Health Check", "GET", "/api/health")

    def test_document_extraction(self, file_path: Path, description: str) -> str | None:
        """Test document extraction for a specific file."""
        if not file_path.exists():
            self.log(f"File not found: {file_path}", "WARNING")
            return None

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            result = self.test_endpoint(
                f"Extract {description}", "POST", "/api/extract", files=files
            )

        if result and "job_id" in result:
            job_id = result["job_id"]
            self.jobs_created.append(job_id)
            self.log(f"Job created: {job_id} for {file_path.name}")
            return job_id
        return None

    def test_job_status(self, job_id: str, wait_for_completion: bool = True) -> dict | None:
        """Test job status endpoint."""
        max_attempts = 60  # 60 seconds timeout
        attempt = 0

        while attempt < max_attempts:
            result = self.test_endpoint(f"Job Status ({job_id})", "GET", f"/api/jobs/{job_id}")

            if result:
                status = result.get("status")
                self.log(f"Job {job_id} status: {status}")

                if not wait_for_completion or status in ["completed", "failed"]:
                    return result

            time.sleep(1)
            attempt += 1

        self.log(f"Timeout waiting for job {job_id}", "WARNING")
        return None

    def test_list_jobs(self, limit: int = 10):
        """Test list jobs endpoint."""
        return self.test_endpoint("List Jobs", "GET", f"/api/jobs?limit={limit}")

    def test_download_results(self, job_id: str, save_path: Path | None = None) -> bool:
        """Test downloading job results as ZIP."""
        url = f"{self.base_url}/api/extract/{job_id}/download"

        try:
            self.log(f"Downloading results for job {job_id}")
            with httpx.Client() as client:
                response = client.get(url)

            if response.status_code == 200:
                if save_path is None:
                    save_path = OUTPUT_DIR / f"{job_id}_results.zip"

                save_path.parent.mkdir(parents=True, exist_ok=True)

                with open(save_path, "wb") as f:
                    f.write(response.content)

                # Verify ZIP file
                with zipfile.ZipFile(save_path, "r") as zf:
                    files = zf.namelist()
                    self.log(f"✅ Downloaded ZIP contains {len(files)} files: {files}", "SUCCESS")

                    # Extract and verify contents
                    extract_dir = OUTPUT_DIR / f"{job_id}_extracted"
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    zf.extractall(extract_dir)

                    # Check for expected files
                    expected_files = ["content.txt", "meta.txt", "extraction_log.json"]
                    for expected in expected_files:
                        if any(expected in f for f in files):
                            self.log(f"  ✓ Found {expected}")
                        else:
                            self.log(f"  ✗ Missing {expected}", "WARNING")

                return True
            else:
                self.log(f"❌ Failed to download results: Status {response.status_code}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Download failed with exception: {str(e)}", "ERROR")
            return False

    def test_get_job_result(self, job_id: str):
        """Test getting job result directly."""
        return self.test_endpoint(f"Get Job Result ({job_id})", "GET", f"/api/jobs/{job_id}/result")

    def test_delete_job(self, job_id: str):
        """Test deleting a job - should return 405 Method Not Allowed since this endpoint doesn't exist."""
        return self.test_endpoint(
            f"Delete Job ({job_id})", "DELETE", f"/api/jobs/{job_id}", expected_status=[405]
        )

    def test_invalid_requests(self):
        """Test API behavior with invalid requests."""
        self.log("Testing invalid request scenarios...")

        # Test with non-existent job ID - should return 404
        self.test_endpoint(
            "Non-existent Job Status",
            "GET",
            "/api/jobs/invalid-job-id-12345",
            expected_status=[404],
        )

        # Test extraction without file - should return 422
        self.test_endpoint("Extract without file", "POST", "/api/extract", expected_status=[422])

        # Test with invalid file type - should return 400
        with tempfile.NamedTemporaryFile(suffix=".invalid") as tf:
            tf.write(b"Invalid file content")
            tf.seek(0)
            files = {"file": ("test.invalid", tf, "application/octet-stream")}
            self.test_endpoint(
                "Extract invalid file type",
                "POST",
                "/api/extract",
                expected_status=[400],
                files=files,
            )

    def run_comprehensive_tests(self):
        """Run all comprehensive API tests."""
        self.log("=" * 60)
        self.log("Starting Comprehensive API Testing")
        self.log("=" * 60)

        # 1. Test health endpoint
        health_result = self.test_health_endpoint()
        if health_result:
            self.log(f"API Version: {health_result.get('version')}")
            self.log(f"Supported formats: {health_result.get('supported_formats')}")

        # 2. Test document extraction for all file types
        test_files = [
            (TEST_FILES_DIR / "sample.md", "Markdown file"),
            (TEST_FILES_DIR / "Chennai_Madurai_Travel_Guide_Illustrated.pdf", "PDF file"),
            (TEST_FILES_DIR / "Chennai_Madurai_Guide_10page.docx", "DOCX file"),
            (TEST_FILES_DIR / "Channai_Madurai.xlsx", "XLSX file"),
        ]

        job_ids = []
        for file_path, description in test_files:
            job_id = self.test_document_extraction(file_path, description)
            if job_id:
                job_ids.append((job_id, file_path.name))

        # 3. Test list jobs
        self.test_list_jobs(limit=5)

        # 4. Wait for jobs to complete and test status
        completed_jobs = []
        for job_id, filename in job_ids:
            result = self.test_job_status(job_id, wait_for_completion=True)
            if result and result.get("status") == "completed":
                completed_jobs.append((job_id, filename))

        # 5. Test downloading results for completed jobs
        self.log("\nTesting result downloads...")
        for job_id, _filename in completed_jobs:
            # Test getting job result
            self.test_get_job_result(job_id)

            # Test downloading as ZIP
            self.test_download_results(job_id)

        # 6. Test invalid requests
        self.test_invalid_requests()

        # 7. Test job deletion
        if completed_jobs:
            job_id, _ = completed_jobs[0]
            self.test_delete_job(job_id)

        # Print summary and return result
        return self.print_summary()

    def print_summary(self):
        """Print test results summary."""
        self.log("=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)

        total = len(self.test_results)
        passed = sum(1 for t in self.test_results if t["passed"])
        failed = total - passed

        self.log(f"Total tests: {total}")
        self.log(f"Passed: {passed} ✅")
        self.log(f"Failed: {failed} ❌")
        self.log(f"Success rate: {(passed / total) * 100:.1f}%")

        if failed > 0:
            self.log("\nFailed tests:")
            for test in self.test_results:
                if not test["passed"]:
                    self.log(f"  - {test['name']} ({test['method']} {test['endpoint']})")

        # Clean up created jobs
        if self.jobs_created:
            self.log(f"\nCreated {len(self.jobs_created)} jobs during testing")

        return passed == total


def main():
    """Main entry point."""
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check if API is running
    try:
        with httpx.Client() as client:
            response = client.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API is not healthy at {API_BASE_URL}")
            print("Please start the API server with 'make run' first")
            sys.exit(1)
    except (httpx.ConnectError, httpx.TimeoutException):
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print("Please start the API server with 'make run' first")
        sys.exit(1)

    # Run tests
    tester = APITester()
    success = tester.run_comprehensive_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
