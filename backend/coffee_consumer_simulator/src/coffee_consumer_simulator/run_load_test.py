"""
Load Test Runner - Executes locust breakpoint tests and uploads results to Azure Blob Storage.

This script:
1. Runs locust with breakpoint mode to find system limits
2. Generates an HTML report
3. Uploads the report to Azure Blob Storage at load-tests/{timestamp}/{version}.html

Environment Variables:
    API_VERSION: v2 or v3 (default: v2)
    TARGET_HOST: API endpoint URL (default: http://coffee-rt-api:8005)
    BREAKPOINT_START: Starting users (default: 10)
    BREAKPOINT_STEP: Users per step (default: 10)
    BREAKPOINT_INTERVAL: Seconds between steps (default: 15)
    BREAKPOINT_MAX: Maximum users (default: 500)
    BREAKPOINT_THRESHOLD: Failure rate to stop (default: 0.10)
    STORAGE_ACCOUNT_NAME: Azure storage account name
    STORAGE_CONTAINER_NAME: Container for results (default: load-tests)
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


def get_env(name: str, default: str) -> str:
    """Get environment variable with default."""
    return os.environ.get(name, default)


def run_locust_test(output_html: Path) -> int:
    """Run locust breakpoint test and generate HTML report."""
    api_version = get_env("API_VERSION", "v2")
    target_host = get_env("TARGET_HOST", "http://coffee-rt-api:8005")
    breakpoint_start = get_env("BREAKPOINT_START", "10")
    breakpoint_step = get_env("BREAKPOINT_STEP", "10")
    breakpoint_interval = get_env("BREAKPOINT_INTERVAL", "15")
    breakpoint_max = get_env("BREAKPOINT_MAX", "500")
    breakpoint_threshold = get_env("BREAKPOINT_THRESHOLD", "0.10")

    cmd = [
        "locust",
        "-f",
        "src/coffee_consumer_simulator/benchmark.py",
        "--host",
        target_host,
        "--api-version",
        api_version,
        "--headless",
        "--breakpoint-mode",
        "--breakpoint-start",
        breakpoint_start,
        "--breakpoint-step",
        breakpoint_step,
        "--breakpoint-interval",
        breakpoint_interval,
        "--breakpoint-max",
        breakpoint_max,
        "--breakpoint-threshold",
        breakpoint_threshold,
        "--html",
        str(output_html),
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"API Version: {api_version}")
    print(f"Target: {target_host}")
    print(f"Breakpoint: start={breakpoint_start}, step={breakpoint_step}, max={breakpoint_max}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd="/app/backend/coffee_consumer_simulator")
    return result.returncode


def upload_to_blob(local_file: Path, blob_path: str) -> str:
    """Upload file to Azure Blob Storage using workload identity."""
    storage_account = get_env("STORAGE_ACCOUNT_NAME", "")
    container_name = get_env("STORAGE_CONTAINER_NAME", "load-tests")

    if not storage_account:
        print("ERROR: STORAGE_ACCOUNT_NAME not set, skipping upload")
        return ""

    account_url = f"https://{storage_account}.blob.core.windows.net"

    print(f"Uploading to: {account_url}/{container_name}/{blob_path}")

    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = blob_service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_path)

    with open(local_file, "rb") as f:
        blob_client.upload_blob(f, overwrite=True, content_settings={"content_type": "text/html"})

    blob_url = f"{account_url}/{container_name}/{blob_path}"
    print(f"Uploaded successfully: {blob_url}")
    return blob_url


def main() -> int:
    """Main entry point."""
    api_version = get_env("API_VERSION", "v2")
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    # Create results directory
    results_dir = Path("/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Output file paths
    html_file = results_dir / f"{api_version}.html"
    blob_path = f"{timestamp}/{api_version}.html"

    print("=" * 60)
    print(f"Coffee-RT Load Test - {api_version.upper()}")
    print(f"Timestamp: {timestamp}")
    print("=" * 60)

    # Run the test
    exit_code = run_locust_test(html_file)

    print("-" * 60)
    print(f"Test completed with exit code: {exit_code}")

    # Upload results even if test "failed" (breakpoint reached is expected)
    if html_file.exists():
        try:
            blob_url = upload_to_blob(html_file, blob_path)
            if blob_url:
                print(f"\nResults available at: {blob_url}")
        except Exception as e:
            print(f"ERROR uploading to blob: {e}")
            # Don't fail the job just because upload failed
    else:
        print(f"WARNING: HTML report not found at {html_file}")

    print("=" * 60)
    return 0  # Always return success - breakpoint tests "fail" by design


if __name__ == "__main__":
    sys.exit(main())
