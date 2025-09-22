#!/usr/bin/env python3

import json
import sys
import time
from pathlib import Path

import click
import httpx


class Doc2TextClient:
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def health_check(self) -> dict:
        response = self.client.get(f"{self.base_url}/api/health")
        response.raise_for_status()
        return response.json()

    def submit_document(self, file_path: Path) -> dict:
        if not file_path.exists():
            raise click.ClickException(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = self.client.post(f"{self.base_url}/api/extract", files=files)

        if response.status_code != 200:
            try:
                error_data = response.json()
                raise click.ClickException(
                    f"Upload failed: {error_data.get('error', response.text)}"
                )
            except json.JSONDecodeError:
                raise click.ClickException(
                    f"Upload failed with status {response.status_code}: {response.text}"
                ) from None

        return response.json()

    def get_job_status(self, job_id: str) -> dict:
        response = self.client.get(f"{self.base_url}/api/jobs/{job_id}")
        if response.status_code == 404:
            raise click.ClickException(f"Job not found: {job_id}")
        response.raise_for_status()
        return response.json()

    def get_job_result(self, job_id: str) -> dict:
        response = self.client.get(f"{self.base_url}/api/jobs/{job_id}/result")
        if response.status_code == 404:
            raise click.ClickException(f"Job not found: {job_id}")
        response.raise_for_status()
        return response.json()

    def download_results(self, job_id: str, output_path: Path) -> None:
        response = self.client.get(f"{self.base_url}/api/extract/{job_id}/download")
        if response.status_code == 404:
            raise click.ClickException(f"Results not found for job: {job_id}")
        elif response.status_code == 400:
            error_data = response.json()
            raise click.ClickException(f"Download failed: {error_data.get('error', response.text)}")

        response.raise_for_status()

        # Save the file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)

    def list_jobs(self, limit: int = 10) -> dict:
        response = self.client.get(f"{self.base_url}/api/jobs", params={"limit": limit})
        response.raise_for_status()
        return response.json()


@click.group()
@click.option("--api-url", default="http://localhost:8081", help="API base URL")
@click.pass_context
def cli(ctx, api_url):
    """Document to Text Extractor CLI Client"""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url


@cli.command()
@click.pass_context
def health(ctx):
    """Check API health status"""
    try:
        with Doc2TextClient(ctx.obj["api_url"]) as client:
            result = client.health_check()
            click.echo(f"API Status: {result['status']}")
            click.echo(f"Supported formats: {', '.join(result['supported_formats'])}")
            click.echo(f"Timestamp: {result['timestamp']}")
    except Exception as e:
        click.echo(f"Health check failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--wait", is_flag=True, help="Wait for processing to complete")
@click.option(
    "--download",
    type=click.Path(path_type=Path),
    help="Download results to this path when complete",
)
@click.option("--poll-interval", default=2, help="Polling interval in seconds when waiting")
@click.pass_context
def extract(ctx, file_path, wait, download, poll_interval):
    """Submit a document for extraction"""
    try:
        with Doc2TextClient(ctx.obj["api_url"]) as client:
            click.echo(f"Uploading {file_path.name}...")
            result = client.submit_document(file_path)

            job_id = result["job_id"]
            click.echo(f"Job created: {job_id}")
            click.echo(f"Status: {result['status']}")

            if wait or download:
                click.echo("Waiting for processing to complete...")

                with click.progressbar(length=100, label="Processing") as bar:
                    last_status = None

                    while True:
                        status = client.get_job_status(job_id)
                        current_status = status["status"]

                        if current_status != last_status:
                            click.echo(f"Status: {current_status}")
                            last_status = current_status

                        if current_status == "completed":
                            bar.update(100)
                            break
                        elif current_status == "failed":
                            click.echo(
                                f"Job failed: {status.get('error_message', 'Unknown error')}",
                                err=True,
                            )
                            sys.exit(1)
                        elif current_status == "processing":
                            bar.update(50)  # Approximate progress

                        time.sleep(poll_interval)

                click.echo("Processing completed!")

                # Show results summary
                result_info = client.get_job_result(job_id)
                if result_info.get("result_summary"):
                    summary = result_info["result_summary"]
                    click.echo(f"Text length: {summary['text_length']:,} characters")
                    click.echo(f"Images extracted: {summary['images_count']}")
                    click.echo(f"Extraction method: {summary['extraction_method']}")

                # Download if requested
                if download:
                    click.echo(f"Downloading results to {download}...")
                    client.download_results(job_id, download)
                    click.echo(f"Results saved to {download}")
            else:
                click.echo(f"Use 'uv run python -m cli.client status {job_id}' to check progress")
                click.echo(
                    f"Use 'uv run python -m cli.client download {job_id} output.zip' to get results"
                )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("job_id")
@click.pass_context
def status(ctx, job_id):
    """Check job status"""
    try:
        with Doc2TextClient(ctx.obj["api_url"]) as client:
            result = client.get_job_status(job_id)

            click.echo(f"Job ID: {result['job_id']}")
            click.echo(f"Status: {result['status']}")
            click.echo(f"Filename: {result['filename']}")
            click.echo(f"File size: {result['file_size']:,} bytes")
            click.echo(f"File type: {result['file_type']}")
            click.echo(f"Created: {result['created_at']}")

            if result["started_at"]:
                click.echo(f"Started: {result['started_at']}")
            if result["completed_at"]:
                click.echo(f"Completed: {result['completed_at']}")
            if result["error_message"]:
                click.echo(f"Error: {result['error_message']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("job_id")
@click.argument("output_path", type=click.Path(path_type=Path))
@click.pass_context
def download(ctx, job_id, output_path):
    """Download extraction results"""
    try:
        with Doc2TextClient(ctx.obj["api_url"]) as client:
            click.echo(f"Downloading results for job {job_id}...")
            client.download_results(job_id, output_path)
            click.echo(f"Results saved to {output_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--limit", default=10, help="Number of jobs to show")
@click.pass_context
def list_jobs(ctx, limit):
    """List recent jobs"""
    try:
        with Doc2TextClient(ctx.obj["api_url"]) as client:
            result = client.list_jobs(limit=limit)

            if not result["jobs"]:
                click.echo("No jobs found")
                return

            click.echo(f"Recent jobs (showing {len(result['jobs'])} of {result['total']}):")
            click.echo()

            for job in result["jobs"]:
                status_icon = {
                    "pending": "[PENDING]",
                    "processing": "[PROCESSING]",
                    "completed": "[COMPLETED]",
                    "failed": "[FAILED]",
                }.get(job["status"], "[UNKNOWN]")

                click.echo(
                    f"{status_icon} {job['job_id'][:8]}... - {job['filename']} ({job['status']})"
                )
                click.echo(f"   Created: {job['created_at']}")
                if job["error_message"]:
                    click.echo(f"   Error: {job['error_message']}")
                click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("./extractions"),
    help="Directory to save results",
)
@click.option("--poll-interval", default=2, help="Polling interval in seconds")
@click.pass_context
def batch(ctx, files, output_dir, poll_interval):
    """Process multiple files in batch"""
    if not files:
        click.echo("No files specified", err=True)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with Doc2TextClient(ctx.obj["api_url"]) as client:
            # Submit all files
            jobs = []
            click.echo(f"Submitting {len(files)} files...")

            for file_path in files:
                result = client.submit_document(file_path)
                jobs.append(
                    {"job_id": result["job_id"], "filename": file_path.name, "status": "pending"}
                )
                click.echo(f"   {file_path.name} -> {result['job_id']}")

            # Monitor all jobs
            click.echo(f"Monitoring {len(jobs)} jobs...")
            completed = 0

            while completed < len(jobs):
                for job in jobs:
                    if job["status"] in ["completed", "failed"]:
                        continue

                    status = client.get_job_status(job["job_id"])
                    old_status = job["status"]
                    job["status"] = status["status"]

                    if job["status"] != old_status:
                        if job["status"] == "completed":
                            completed += 1
                            click.echo(f"   {job['filename']} completed ({completed}/{len(jobs)})")

                            # Download immediately
                            output_file = (
                                output_dir / f"{job['filename']}_{job['job_id'][:8]}_results.zip"
                            )
                            client.download_results(job["job_id"], output_file)
                            click.echo(f"      Results saved to {output_file}")

                        elif job["status"] == "failed":
                            completed += 1
                            click.echo(f"   {job['filename']} failed")

                if completed < len(jobs):
                    time.sleep(poll_interval)

            click.echo(f"Batch processing complete! Results in {output_dir}")

    except Exception as e:
        click.echo(f"Batch processing error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
