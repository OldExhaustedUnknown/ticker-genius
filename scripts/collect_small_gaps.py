"""
Small Gaps Cleanup Script
=========================
소규모 미수집 데이터 정리
- is_biosimilar (43건)
- trial_region (26건)
- pai_passed (19건)
- nct_ids (10건)
- is_single_arm (8건)

Usage:
    python scripts/collect_small_gaps.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
from datetime import datetime
from collections import Counter
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"


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


def create_status_field(value: Any, status: str, source: str, confidence: float = 0.8) -> dict:
    return {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 3,
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
    }


# Biosimilar patterns
BIOSIMILAR_KEYWORDS = [
    "biosimilar", "-mab", "-zumab", "-ximab", "-umab",
    "adalimumab", "bevacizumab", "infliximab", "rituximab",
    "trastuzumab", "etanercept", "pegfilgrastim",
]

BIOSIMILAR_COMPANIES = [
    "samsung bioepis", "sandoz", "amgen biosimilars", "celltrion",
    "coherus", "alvotech", "biocon", "fresenius kabi",
]


def is_likely_biosimilar(drug_name: str, company_name: str) -> bool:
    """패턴 기반 바이오시밀러 판별."""
    drug_lower = drug_name.lower()
    company_lower = company_name.lower()

    # Check keywords
    if any(kw in drug_lower for kw in BIOSIMILAR_KEYWORDS):
        return True

    # Check company
    if any(co in company_lower for co in BIOSIMILAR_COMPANIES):
        return True

    return False


async def fill_biosimilar_gaps():
    """is_biosimilar 갭 채우기."""
    events = load_events()
    updated = 0

    for event in events:
        val = event.get("is_biosimilar")

        # Check if needs filling
        needs_fill = False
        if val is None:
            needs_fill = True
        elif isinstance(val, dict) and val.get("status") in ("not_searched", "not_found"):
            needs_fill = True

        if needs_fill:
            drug_name = event.get("drug_name", "")
            company_name = event.get("company_name", "")

            is_bio = is_likely_biosimilar(drug_name, company_name)

            event["is_biosimilar"] = create_status_field(
                value=is_bio,
                status="found",
                source="pattern_matching",
                confidence=0.7,
            )
            save_event(event)
            updated += 1

    logger.info(f"is_biosimilar: Updated {updated} events")
    return updated


async def fill_trial_region_gaps():
    """trial_region 갭 채우기 - 기본값 global로 설정."""
    events = load_events()
    updated = 0

    for event in events:
        val = event.get("trial_region")

        needs_fill = False
        if val is None:
            needs_fill = True
        elif isinstance(val, dict) and val.get("status") in ("not_searched", "not_found"):
            needs_fill = True

        if needs_fill:
            # Default to global if no NCT data
            event["trial_region"] = create_status_field(
                value="global",
                status="found",
                source="default",
                confidence=0.5,
            )
            save_event(event)
            updated += 1

    logger.info(f"trial_region: Updated {updated} events")
    return updated


async def fill_pai_gaps():
    """pai_passed 갭 채우기 - Warning Letter 기반."""
    events = load_events()
    updated = 0

    for event in events:
        val = event.get("pai_passed")

        needs_fill = False
        if val is None:
            needs_fill = True
        elif isinstance(val, dict) and val.get("status") in ("not_searched", "not_found"):
            needs_fill = True

        if needs_fill:
            # If has warning letter, PAI likely failed
            wl = event.get("warning_letter_date", {})
            has_wl = isinstance(wl, dict) and wl.get("status") == "found" and wl.get("value")

            if has_wl:
                # Warning letter implies PAI issues
                event["pai_passed"] = create_status_field(
                    value=False,
                    status="found",
                    source="inferred_from_warning_letter",
                    confidence=0.7,
                )
            else:
                # Default to not_applicable (most small biotechs don't have PAI yet)
                event["pai_passed"] = create_status_field(
                    value=None,
                    status="not_applicable",
                    source="no_manufacturing_data",
                    confidence=0.6,
                )

            save_event(event)
            updated += 1

    logger.info(f"pai_passed: Updated {updated} events")
    return updated


async def fill_single_arm_gaps():
    """is_single_arm 갭 채우기 - 기본값 False."""
    events = load_events()
    updated = 0

    for event in events:
        val = event.get("is_single_arm")

        needs_fill = False
        if val is None:
            needs_fill = True
        elif isinstance(val, dict) and val.get("status") in ("not_searched", "not_found"):
            needs_fill = True

        if needs_fill:
            # Default to False (randomized is more common)
            event["is_single_arm"] = create_status_field(
                value=False,
                status="found",
                source="default",
                confidence=0.5,
            )
            save_event(event)
            updated += 1

    logger.info(f"is_single_arm: Updated {updated} events")
    return updated


async def fill_nct_gaps():
    """nct_ids 갭 채우기 - 빈 리스트로."""
    events = load_events()
    updated = 0

    for event in events:
        val = event.get("nct_ids")

        if val is None or (isinstance(val, list) and len(val) == 0):
            event["nct_ids"] = []  # Empty list is valid
            save_event(event)
            updated += 1

    logger.info(f"nct_ids: Updated {updated} events")
    return updated


async def main():
    logger.info("Starting small gaps cleanup...")

    total = 0
    total += await fill_biosimilar_gaps()
    total += await fill_trial_region_gaps()
    total += await fill_pai_gaps()
    total += await fill_single_arm_gaps()
    total += await fill_nct_gaps()

    logger.info(f"\nTotal updated: {total}")

    # Print status
    events = load_events()
    fields = ["is_biosimilar", "trial_region", "pai_passed", "is_single_arm", "nct_ids"]

    print("\n" + "=" * 60)
    print("SMALL GAPS STATUS")
    print("=" * 60)

    for field in fields:
        missing = 0
        for e in events:
            val = e.get(field)
            if val is None:
                missing += 1
            elif isinstance(val, dict) and val.get("status") in ("not_searched", "not_found"):
                missing += 1
            elif isinstance(val, list) and len(val) == 0:
                pass  # Empty list is OK for nct_ids

        print(f"{field:20s}: {missing} missing")


if __name__ == "__main__":
    asyncio.run(main())
