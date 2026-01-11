#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collect enrollment data from ClinicalTrials.gov API for enriched drug data.

This script:
1. Reads each JSON file in data/enriched/
2. For files with nct_ids, fetches enrollment info from ClinicalTrials.gov API
3. Updates the JSON file with enrollment data
4. Handles rate limiting (max 3 requests/second)

Uses curl subprocess for reliable API access (ClinicalTrials.gov blocks some Python libraries).
"""

import json
import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure UTF-8 encoding on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data" / "enriched"
API_BASE = "https://clinicaltrials.gov/api/v2/studies"
RATE_LIMIT_DELAY = 0.34  # ~3 requests per second (1/3 second between requests)
REQUEST_TIMEOUT = 30


def fetch_enrollment_curl(nct_id: str) -> dict[str, Any] | None:
    """
    Fetch enrollment info from ClinicalTrials.gov API using curl.

    Args:
        nct_id: The NCT ID to look up (e.g., "NCT06493604")

    Returns:
        Dict with enrollment info or None if not found/error
    """
    url = f"{API_BASE}/{nct_id}?fields=EnrollmentInfo"

    try:
        result = subprocess.run(
            [
                "curl",
                "-s",  # Silent mode
                "-H", "User-Agent: Mozilla/5.0",
                "-H", "Accept: application/json",
                "--max-time", str(REQUEST_TIMEOUT),
                url
            ],
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT + 5,
            encoding="utf-8"
        )

        if result.returncode != 0:
            print(f"  [ERROR] curl failed for {nct_id}: return code {result.returncode}")
            return None

        if not result.stdout.strip():
            print(f"  [WARN] Empty response for {nct_id}")
            return None

        data = json.loads(result.stdout)

        # Check for error response
        if "errors" in data:
            print(f"  [WARN] API error for {nct_id}: {data.get('errors')}")
            return None

        # Extract enrollment info from response
        # API returns: {"protocolSection": {"designModule": {"enrollmentInfo": {...}}}}
        protocol_section = data.get("protocolSection", {})
        design_module = protocol_section.get("designModule", {})
        enrollment_info = design_module.get("enrollmentInfo", {})

        if enrollment_info:
            return {
                "count": enrollment_info.get("count"),
                "type": enrollment_info.get("type"),  # ACTUAL or ESTIMATED
                "nct_id": nct_id,
                "source": "clinicaltrials.gov",
                "fetched_at": datetime.now().isoformat()
            }

        return None

    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Timeout for {nct_id}")
        return None
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Invalid JSON for {nct_id}: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Request failed for {nct_id}: {e}")
        return None


def process_file(file_path: Path, stats: dict) -> bool:
    """
    Process a single JSON file, fetching enrollment for its NCT IDs.

    Args:
        file_path: Path to the JSON file
        stats: Statistics dictionary to update

    Returns:
        True if file was updated, False otherwise
    """
    try:
        # Read file with UTF-8 encoding
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [ERROR] Failed to read {file_path.name}: {e}")
        stats["errors"] += 1
        return False

    # Check for nct_ids
    nct_ids = data.get("nct_ids", [])
    if not nct_ids:
        stats["no_nct_ids"] += 1
        return False

    # Skip if enrollment already collected
    existing_enrollment = data.get("enrollment")
    if existing_enrollment is not None:
        # Check if it's a proper enrollment dict (not just null)
        if isinstance(existing_enrollment, dict) and existing_enrollment.get("count") is not None:
            stats["already_has_enrollment"] += 1
            return False

    # Collect enrollment for all NCT IDs
    enrollments = []
    for nct_id in nct_ids:
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        enrollment = fetch_enrollment_curl(nct_id)
        if enrollment:
            enrollments.append(enrollment)
            stats["api_success"] += 1
        else:
            stats["api_failed"] += 1

    if not enrollments:
        return False

    # Use the enrollment with the highest count (for multi-NCT cases)
    # Or the first ACTUAL enrollment if available
    best_enrollment = None
    for e in enrollments:
        if e.get("type") == "ACTUAL":
            if best_enrollment is None or (e.get("count") or 0) > (best_enrollment.get("count") or 0):
                best_enrollment = e

    if best_enrollment is None:
        best_enrollment = max(enrollments, key=lambda x: x.get("count") or 0)

    # Update the data
    data["enrollment"] = best_enrollment

    # Write back with UTF-8 encoding
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        stats["files_updated"] += 1
        return True
    except OSError as e:
        print(f"  [ERROR] Failed to write {file_path.name}: {e}")
        stats["errors"] += 1
        return False


def main():
    """Main function to process all enriched data files."""
    print("=" * 60)
    print("Enrollment Data Collection from ClinicalTrials.gov")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Rate limit: ~3 requests/second")
    print()

    if not DATA_DIR.exists():
        print(f"[ERROR] Data directory not found: {DATA_DIR}")
        sys.exit(1)

    # Get all JSON files
    json_files = sorted(DATA_DIR.glob("*.json"))
    total_files = len(json_files)
    print(f"Found {total_files} JSON files to process")
    print()

    # Statistics
    stats = {
        "files_updated": 0,
        "no_nct_ids": 0,
        "already_has_enrollment": 0,
        "api_success": 0,
        "api_failed": 0,
        "errors": 0
    }

    for i, file_path in enumerate(json_files, 1):
        ticker_event = file_path.stem  # e.g., "ALDX_4ea94b84c6b7"

        # Progress indicator
        print(f"[{i:3d}/{total_files}] Processing {ticker_event}...", end=" ", flush=True)

        updated = process_file(file_path, stats)

        if updated:
            print("UPDATED")
        else:
            # Determine the reason for not updating
            current_no_nct = stats["no_nct_ids"]
            current_has_enroll = stats["already_has_enrollment"]

            # Check what happened in this iteration
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    check_data = json.load(f)
                if not check_data.get("nct_ids", []):
                    print("(no NCT IDs)")
                elif isinstance(check_data.get("enrollment"), dict) and check_data.get("enrollment", {}).get("count") is not None:
                    print("(already has enrollment)")
                else:
                    print("(no data found)")
            except Exception:
                print("(error)")

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files processed:     {total_files}")
    print(f"Files updated:             {stats['files_updated']}")
    print(f"Files without NCT IDs:     {stats['no_nct_ids']}")
    print(f"Already had enrollment:    {stats['already_has_enrollment']}")
    print(f"API calls successful:      {stats['api_success']}")
    print(f"API calls failed:          {stats['api_failed']}")
    print(f"Errors:                    {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
