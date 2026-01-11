"""
Phase 3 Study Names Collector - ClinicalTrials.gov API

Collects OfficialTitle or BriefTitle for NCT IDs in enriched data files.
API: https://clinicaltrials.gov/api/v2/studies/{nct_id}?fields=IdentificationModule
"""
import json
import os
import sys
import time
import requests
import urllib3
from pathlib import Path
from datetime import datetime
from typing import Optional

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Constants
DATA_DIR = Path("d:/ticker-genius/data/enriched")
PROGRESS_FILE = Path("d:/ticker-genius/data/study_names_progress.json")
API_BASE = "https://clinicaltrials.gov/api/v2/studies"
RATE_LIMIT_DELAY = 0.3  # 300ms between requests
BATCH_SIZE = 50  # Save progress every N files

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def create_session() -> requests.Session:
    """Create a requests session with proper headers"""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_study_title(nct_id: str, session: requests.Session, retry_count: int = 0) -> Optional[str]:
    """Fetch study title from ClinicalTrials.gov API v2"""
    url = f"{API_BASE}/{nct_id}"
    params = {"fields": "IdentificationModule"}

    try:
        resp = session.get(url, params=params, timeout=30, verify=False)

        if resp.status_code == 200:
            data = resp.json()
            id_module = data.get("protocolSection", {}).get("identificationModule", {})

            # Prefer OfficialTitle, fall back to BriefTitle
            title = id_module.get("officialTitle") or id_module.get("briefTitle")
            return title

        elif resp.status_code == 404:
            # Study not found
            return None
        elif resp.status_code == 429:
            # Rate limited - wait and retry
            if retry_count < 3:
                time.sleep(5)
                return fetch_study_title(nct_id, session, retry_count + 1)
            return None
        elif resp.status_code == 403:
            # Forbidden - try again
            if retry_count < 2:
                time.sleep(2)
                return fetch_study_title(nct_id, session, retry_count + 1)
            print(f"  API forbidden for {nct_id}")
            return None
        else:
            print(f"  API error for {nct_id}: HTTP {resp.status_code}")
            return None

    except requests.exceptions.Timeout:
        print(f"  Timeout for {nct_id}")
        return None
    except Exception as e:
        print(f"  Error for {nct_id}: {e}")
        return None


def load_progress() -> dict:
    """Load progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "completed_files": [],
        "completed_nct_ids": {},  # nct_id -> title
        "stats": {
            "files_processed": 0,
            "nct_ids_processed": 0,
            "titles_found": 0,
            "not_found": 0
        },
        "started_at": datetime.now().isoformat(),
        "last_updated": None
    }


def save_progress(progress: dict):
    """Save progress to file"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)


def collect_all_nct_ids() -> dict:
    """Collect all unique NCT IDs and their source files"""
    nct_to_files = {}  # nct_id -> list of file paths

    for fpath in DATA_DIR.glob("*.json"):
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        nct_ids = data.get("nct_ids", [])
        if not nct_ids:
            continue

        for nct_id in nct_ids:
            if nct_id not in nct_to_files:
                nct_to_files[nct_id] = []
            nct_to_files[nct_id].append(str(fpath))

    return nct_to_files


def main():
    print("=" * 60)
    print("Phase 3 Study Names Collector")
    print("=" * 60)

    # Reset progress if needed (uncomment to reset)
    # if PROGRESS_FILE.exists():
    #     PROGRESS_FILE.unlink()

    # Load progress
    progress = load_progress()

    # Reset progress since we had HTTP 403 errors before
    cached_titles = {}  # Reset cache - previous entries had None values due to 403
    progress["completed_nct_ids"] = {}
    progress["stats"] = {
        "files_processed": 0,
        "nct_ids_processed": 0,
        "titles_found": 0,
        "not_found": 0
    }

    completed_files = set(progress.get("completed_files", []))

    print(f"\nCached NCT IDs: {len(cached_titles)}")
    print(f"Already processed files: {len(completed_files)}")

    # Collect all NCT IDs first
    print("\nScanning files for NCT IDs...")
    nct_to_files = collect_all_nct_ids()

    unique_nct_ids = set(nct_to_files.keys())
    uncached_nct_ids = unique_nct_ids - set(cached_titles.keys())

    print(f"Total unique NCT IDs: {len(unique_nct_ids)}")
    print(f"NCT IDs to fetch: {len(uncached_nct_ids)}")

    # Fetch titles for uncached NCT IDs
    if uncached_nct_ids:
        print(f"\nFetching titles for {len(uncached_nct_ids)} NCT IDs...")

        session = create_session()

        for idx, nct_id in enumerate(sorted(uncached_nct_ids), 1):
            print(f"[{idx}/{len(uncached_nct_ids)}] {nct_id}", end=" ")

            title = fetch_study_title(nct_id, session)

            if title:
                cached_titles[nct_id] = title
                progress["stats"]["titles_found"] += 1
                # Safe print for titles with unicode
                safe_title = title[:60] + "..." if len(title) > 60 else title
                safe_title = safe_title.encode('ascii', 'replace').decode('ascii')
                print(f"-> {safe_title}")
            else:
                cached_titles[nct_id] = None  # Mark as not found
                progress["stats"]["not_found"] += 1
                print("-> NOT FOUND")

            progress["stats"]["nct_ids_processed"] += 1
            progress["completed_nct_ids"] = cached_titles

            # Save progress periodically
            if idx % 20 == 0:
                save_progress(progress)
                print(f"  [Progress saved: {idx}/{len(uncached_nct_ids)}]")

            time.sleep(RATE_LIMIT_DELAY)

        # Final save of NCT IDs
        save_progress(progress)

    # Now update all JSON files
    print("\n" + "=" * 60)
    print("Updating JSON files with study names...")
    print("=" * 60)

    files_updated = 0

    for fpath in DATA_DIR.glob("*.json"):
        file_key = fpath.name

        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        nct_ids = data.get("nct_ids", [])
        if not nct_ids:
            continue

        # Collect study names for this file's NCT IDs
        study_names = []
        for nct_id in nct_ids:
            title = cached_titles.get(nct_id)
            if title:
                study_names.append(title)

        # Check if update needed
        current_names = data.get("phase3_study_names", [])
        if set(study_names) != set(current_names):
            data["phase3_study_names"] = study_names

            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            files_updated += 1
            ticker = data.get("ticker", "?")
            drug = data.get("drug_name", "?")
            safe_drug = drug.encode('ascii', 'replace').decode('ascii')
            print(f"Updated: {ticker} - {safe_drug} ({len(study_names)} studies)")

        progress["stats"]["files_processed"] += 1

    progress["completed_files"] = [f.name for f in DATA_DIR.glob("*.json")]
    save_progress(progress)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"NCT IDs processed: {progress['stats']['nct_ids_processed']}")
    print(f"Titles found: {progress['stats']['titles_found']}")
    print(f"Not found: {progress['stats']['not_found']}")
    print(f"Files updated: {files_updated}")
    print(f"Progress saved to: {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
