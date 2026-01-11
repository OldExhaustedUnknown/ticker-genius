"""
FDA Designations Collection Script
===================================
OpenFDA API를 통한 BTD, PR, FT, OD, AA 수집

Usage:
    python scripts/collect_fda_designations.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
import re
import httpx
from datetime import datetime
from collections import Counter
from typing import Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"

# OpenFDA API
OPENFDA_BASE = "https://api.fda.gov/drug/drugsfda.json"


def json_serializer(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def load_events() -> list[dict]:
    events = []
    for f in ENRICHED_DIR.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            data["_file_path"] = str(f)
            events.append(data)
    return events


def save_event(event: dict):
    file_path = event.pop("_file_path", None)
    if not file_path:
        return
    event["enriched_at"] = datetime.now().isoformat()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2, ensure_ascii=False, default=json_serializer)


def create_status_field(value: Any, status: str, source: str, confidence: float, evidence: list = None) -> dict:
    return {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 1 if "openfda" in source else 3,
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
    }


async def search_openfda(drug_name: str, client: httpx.AsyncClient) -> dict:
    """OpenFDA에서 약물 정보 검색."""
    try:
        # Clean drug name
        clean_name = re.sub(r'[^\w\s]', '', drug_name).strip()
        query = f'openfda.brand_name:"{clean_name}" OR openfda.generic_name:"{clean_name}"'

        params = {
            "search": query,
            "limit": 5,
        }

        response = await client.get(OPENFDA_BASE, params=params, timeout=30)

        if response.status_code == 404:
            return {"found": False}

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            return {"found": False}

        # Parse designations from submissions
        designations = {
            "breakthrough_therapy": False,
            "priority_review": False,
            "fast_track": False,
            "orphan_drug": False,
            "accelerated_approval": False,
        }
        evidence = []

        for result in results:
            submissions = result.get("submissions", [])
            for sub in submissions:
                sub_type = sub.get("submission_type", "")
                sub_status = sub.get("submission_status", "")
                review_priority = sub.get("review_priority", "")

                # Priority Review
                if review_priority and review_priority.upper() == "PRIORITY":
                    designations["priority_review"] = True
                    evidence.append(f"Review Priority: {review_priority}")

                # Check application docs for designations
                app_docs = sub.get("application_docs", [])
                for doc in app_docs:
                    doc_type = doc.get("type", "").lower()

                    if "breakthrough" in doc_type:
                        designations["breakthrough_therapy"] = True
                        evidence.append("Breakthrough Therapy designation doc")
                    if "fast track" in doc_type:
                        designations["fast_track"] = True
                        evidence.append("Fast Track designation doc")
                    if "orphan" in doc_type:
                        designations["orphan_drug"] = True
                        evidence.append("Orphan Drug designation doc")
                    if "accelerated" in doc_type:
                        designations["accelerated_approval"] = True
                        evidence.append("Accelerated Approval doc")

            # Check products for orphan
            products = result.get("products", [])
            for prod in products:
                if prod.get("orphan_designation"):
                    designations["orphan_drug"] = True
                    evidence.append("Orphan designation in product")

        return {
            "found": True,
            "designations": designations,
            "evidence": evidence[:5],
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"found": False}
        logger.warning(f"OpenFDA API error for {drug_name}: {e}")
        return {"found": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error searching {drug_name}: {e}")
        return {"found": False, "error": str(e)}


async def search_websearch_designations(drug_name: str, company_name: str) -> dict:
    """웹서치로 FDA designations 검색."""
    from tickergenius.collection.web_search import WebSearchClient

    client = WebSearchClient()
    designations = {
        "breakthrough_therapy": None,
        "priority_review": None,
        "fast_track": None,
        "orphan_drug": None,
        "accelerated_approval": None,
    }
    evidence = []

    try:
        # Search for designations
        query = f'"{drug_name}" FDA designation breakthrough priority orphan'
        results = await client.search(query, max_results=10)

        for result in results:
            text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

            if "breakthrough therapy" in text or "btd" in text:
                designations["breakthrough_therapy"] = True
                evidence.append(f"BTD: {result.get('title', '')[:80]}")

            if "priority review" in text:
                designations["priority_review"] = True
                evidence.append(f"PR: {result.get('title', '')[:80]}")

            if "fast track" in text:
                designations["fast_track"] = True
                evidence.append(f"FT: {result.get('title', '')[:80]}")

            if "orphan drug" in text or "orphan designation" in text:
                designations["orphan_drug"] = True
                evidence.append(f"OD: {result.get('title', '')[:80]}")

            if "accelerated approval" in text:
                designations["accelerated_approval"] = True
                evidence.append(f"AA: {result.get('title', '')[:80]}")

        # Set None to False if not found
        for key in designations:
            if designations[key] is None:
                designations[key] = False

        return {
            "found": True,
            "designations": designations,
            "evidence": evidence[:5],
            "source": "websearch",
        }

    except Exception as e:
        logger.error(f"Websearch error for {drug_name}: {e}")
        return {"found": False, "error": str(e)}


async def collect_all():
    """모든 이벤트에 대해 FDA designations 수집."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # Stats
    updated = 0
    openfda_hits = 0
    websearch_hits = 0

    async with httpx.AsyncClient() as client:
        for i, event in enumerate(events):
            drug_name = event.get("drug_name", "")
            company_name = event.get("company_name", "")

            if not drug_name:
                continue

            # Check if already has designations
            existing = event.get("breakthrough_therapy")
            if existing is not None and isinstance(existing, dict) and existing.get("status") == "found":
                continue

            # Try OpenFDA first
            result = await search_openfda(drug_name, client)

            source = "openfda"
            if result.get("found") and result.get("designations"):
                openfda_hits += 1
            else:
                # Fallback to websearch
                result = await search_websearch_designations(drug_name, company_name)
                source = "websearch"
                if result.get("found"):
                    websearch_hits += 1

            if result.get("found") and result.get("designations"):
                desig = result["designations"]
                evidence = result.get("evidence", [])

                # Update all designation fields
                for field, value in desig.items():
                    event[field] = create_status_field(
                        value=value,
                        status="found",
                        source=source,
                        confidence=0.9 if source == "openfda" else 0.75,
                        evidence=evidence,
                    )

                save_event(event)
                updated += 1
            else:
                # Mark as confirmed_none (searched but not found)
                for field in ["breakthrough_therapy", "priority_review", "fast_track", "orphan_drug", "accelerated_approval"]:
                    event[field] = create_status_field(
                        value=False,
                        status="confirmed_none",
                        source="openfda+websearch",
                        confidence=0.7,
                    )
                save_event(event)
                updated += 1

            # Progress
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(events)} (OpenFDA: {openfda_hits}, WebSearch: {websearch_hits})")

            # Rate limit
            await asyncio.sleep(0.2)

    logger.info(f"\nCollection Complete!")
    logger.info(f"Updated: {updated}")
    logger.info(f"OpenFDA hits: {openfda_hits}")
    logger.info(f"WebSearch hits: {websearch_hits}")

    # Print final status
    print_status()


def print_status():
    events = load_events()

    fields = ["breakthrough_therapy", "priority_review", "fast_track", "orphan_drug", "accelerated_approval"]

    print("\n" + "=" * 60)
    print("FDA DESIGNATIONS STATUS")
    print("=" * 60)

    for field in fields:
        stats = Counter()
        true_count = 0
        for e in events:
            val = e.get(field, {})
            if isinstance(val, dict):
                status = val.get("status", "not_searched")
                stats[status] += 1
                if val.get("value") == True:
                    true_count += 1
            else:
                stats["not_searched"] += 1

        found = stats.get("found", 0)
        none = stats.get("confirmed_none", 0)
        ns = stats.get("not_searched", 0)
        print(f"{field:25s}: {found:4d} found ({true_count} True), {none:4d} none, {ns:4d} not searched")


if __name__ == "__main__":
    asyncio.run(collect_all())
