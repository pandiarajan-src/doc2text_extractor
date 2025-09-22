#!/usr/bin/env python
"""
Comprehensive CLI testing script for Document to Text Extractor CLI.
Tests all CLI functionality with all supported file types.
"""

import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

API_BASE_URL = os.environ.get("API_URL", "http://localhost:8081")
TEST_FILES_DIR = Path("tests/test_files")
OUTPUT_DIR = Path("test_outputs_cli")


class CLITester:
    def __init__(self, api_url: str = API_BASE_URL):
        self.api_url = api_url
        self.test_results = []
        self.jobs_created = []
        self.cli_command = ["uv", "run", "python", "-m", "cli.client"]

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp and level."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_cli_command(self, args: list[str], timeout: int = 30) -> tuple[bool, str, str]:
        """Run a CLI command and return success status, stdout, stderr."""
        full_command = self.cli_command + ["--api-url", self.api_url] + args

        try:
            self.log(f"Running CLI: {' '.join(full_command)}")
            result = subprocess.run(full_command, capture_output=True, text=True, timeout=timeout)

            return result.returncode == 0, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def test_cli_command(
        self, name: str, args: list[str], expected_success: bool = True, timeout: int = 30
    ) -> tuple[bool, str, str]:
        """Test a CLI command and record results."""
        success, stdout, stderr = self.run_cli_command(args, timeout)

        test_passed = success == expected_success

        if test_passed:
            self.log(f"✅ {name}: PASSED", "SUCCESS")
        else:
            self.log(f"❌ {name}: FAILED", "ERROR")
            if stderr:
                self.log(f"STDERR: {stderr}", "ERROR")

        self.test_results.append(
            {"name": name, "args": args, "passed": test_passed, "stdout": stdout, "stderr": stderr}
        )

        return success, stdout, stderr

    def test_cli_help(self):
        """Test CLI help command."""
        return self.test_cli_command("CLI Help", ["--help"])

    def test_health_command(self):
        """Test the health command."""
        return self.test_cli_command("Health Check", ["health"])

    def test_extract_command(
        self, file_path: Path, description: str, extra_args: list[str] = None
    ) -> str | None:
        """Test document extraction command."""
        if not file_path.exists():
            self.log(f"File not found: {file_path}", "WARNING")
            return None

        args = ["extract", str(file_path)]
        if extra_args:
            args.extend(extra_args)

        success, stdout, stderr = self.test_cli_command(f"Extract {description}", args, timeout=60)

        if success and stdout:
            # Try to extract job ID from output
            lines = stdout.strip().split("\n")
            for line in lines:
                if "job_id" in line.lower() or "Job ID:" in line:
                    job_id = line.split()[-1]
                    if len(job_id) == 36:  # UUID length
                        self.jobs_created.append(job_id)
                        self.log(f"Extracted job ID: {job_id}")
                        return job_id

        return None

    def test_extract_with_wait(self, file_path: Path, description: str) -> str | None:
        """Test extraction with --wait flag."""
        return self.test_extract_command(file_path, f"{description} (with wait)", ["--wait"])

    def test_extract_with_download(self, file_path: Path, description: str) -> str | None:
        """Test extraction with --wait and --download flags."""
        output_file = OUTPUT_DIR / f"{file_path.stem}_results.zip"
        return self.test_extract_command(
            file_path, f"{description} (with download)", ["--wait", "--download", str(output_file)]
        )

    def test_status_command(self, job_id: str):
        """Test status command for a job."""
        return self.test_cli_command(f"Status Check ({job_id[:8]}...)", ["status", job_id])

    def test_download_command(self, job_id: str):
        """Test download command for a job."""
        output_file = OUTPUT_DIR / f"{job_id}_cli_download.zip"
        success, stdout, stderr = self.test_cli_command(
            f"Download ({job_id[:8]}...)", ["download", job_id, str(output_file)]
        )

        if success and output_file.exists():
            # Verify ZIP file
            try:
                with zipfile.ZipFile(output_file, "r") as zf:
                    files = zf.namelist()
                    self.log(f"  ✓ Downloaded ZIP contains {len(files)} files")

                    # Extract and check contents
                    extract_dir = OUTPUT_DIR / f"{job_id}_cli_extracted"
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    zf.extractall(extract_dir)

                    expected_files = ["content.txt", "meta.txt", "extraction_log.json"]
                    for expected in expected_files:
                        if any(expected in f for f in files):
                            self.log(f"    ✓ Found {expected}")
                        else:
                            self.log(f"    ✗ Missing {expected}", "WARNING")

            except Exception as e:
                self.log(f"  ✗ Error verifying ZIP: {e}", "ERROR")

        return success, stdout, stderr

    def test_list_jobs_command(self):
        """Test list-jobs command."""
        return self.test_cli_command("List Jobs", ["list-jobs", "--limit", "10"])

    def test_batch_processing(self):
        """Test batch processing of multiple files."""
        batch_files = []
        for file_path in TEST_FILES_DIR.glob("*"):
            if file_path.suffix.lower() in [".pdf", ".docx", ".xlsx", ".md"]:
                batch_files.append(str(file_path))

        if len(batch_files) < 2:
            self.log("Not enough files for batch testing", "WARNING")
            return

        output_dir = OUTPUT_DIR / "batch_results"
        args = ["batch"] + batch_files + ["--output-dir", str(output_dir)]

        success, stdout, stderr = self.test_cli_command("Batch Processing", args, timeout=120)

        if success and output_dir.exists():
            results = list(output_dir.glob("*.zip"))
            self.log(f"  ✓ Batch processing created {len(results)} result files")

    def test_invalid_commands(self):
        """Test CLI behavior with invalid commands and arguments."""
        self.log("Testing invalid command scenarios...")

        # Test with non-existent file
        self.test_cli_command(
            "Extract non-existent file",
            ["extract", "non_existent_file.pdf"],
            expected_success=False,
        )

        # Test status with invalid job ID
        self.test_cli_command(
            "Status with invalid job ID", ["status", "invalid-job-id-12345"], expected_success=False
        )

        # Test download with invalid job ID
        output_file = OUTPUT_DIR / "invalid_download.zip"
        self.test_cli_command(
            "Download with invalid job ID",
            ["download", "invalid-job-id-12345", str(output_file)],
            expected_success=False,
        )

        # Test with invalid API URL
        self.log("Testing with invalid API URL...")
        invalid_cli = CLITester("http://invalid-url:9999")
        invalid_cli.test_cli_command(
            "Health check with invalid URL", ["health"], expected_success=False
        )

    def test_polling_behavior(self):
        """Test CLI polling behavior with custom intervals."""
        # Find a small file for quick processing
        test_file = TEST_FILES_DIR / "sample.md"
        if test_file.exists():
            success, stdout, stderr = self.test_cli_command(
                "Extract with custom poll interval",
                ["extract", str(test_file), "--wait", "--poll-interval", "1"],
                timeout=60,
            )

    def run_comprehensive_tests(self):
        """Run all comprehensive CLI tests."""
        self.log("=" * 60)
        self.log("Starting Comprehensive CLI Testing")
        self.log("=" * 60)

        # Create output directory
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Test CLI help
        self.test_cli_help()

        # 2. Test health command
        self.test_health_command()

        # 3. Test document extraction for all file types
        test_files = [
            (TEST_FILES_DIR / "sample.md", "Markdown file"),
            (TEST_FILES_DIR / "Chennai_Madurai_Travel_Guide_Illustrated.pdf", "PDF file"),
            (TEST_FILES_DIR / "Chennai_Madurai_Guide_10page.docx", "DOCX file"),
            (TEST_FILES_DIR / "Channai_Madurai.xlsx", "XLSX file"),
        ]

        job_ids = []

        # Test basic extraction
        for file_path, description in test_files:
            job_id = self.test_extract_command(file_path, description)
            if job_id:
                job_ids.append(job_id)

        # Test extraction with wait
        for file_path, description in test_files:
            job_id = self.test_extract_with_wait(file_path, description)
            if job_id:
                job_ids.append(job_id)

        # Test extraction with download
        for file_path, description in test_files:
            self.test_extract_with_download(file_path, description)

        # 4. Test list jobs
        self.test_list_jobs_command()

        # 5. Test status command for created jobs
        for job_id in job_ids[:3]:  # Test first 3 jobs
            self.test_status_command(job_id)

        # 6. Test download command
        if job_ids:
            self.test_download_command(job_ids[0])

        # 7. Test batch processing
        self.test_batch_processing()

        # 8. Test polling behavior
        self.test_polling_behavior()

        # 9. Test invalid commands
        self.test_invalid_commands()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary."""
        self.log("=" * 60)
        self.log("CLI TEST SUMMARY")
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
                    self.log(f"  - {test['name']}")
                    if test["stderr"]:
                        self.log(f"    Error: {test['stderr']}")

        if self.jobs_created:
            self.log(f"\nCreated {len(self.jobs_created)} jobs during testing")

        return passed == total


def main():
    """Main entry point."""
    # Check if API is running
    import httpx

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
    tester = CLITester()
    success = tester.run_comprehensive_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
