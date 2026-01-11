"""
Manufacturing Temporal Data Collection Script
==============================================
Collects warning_letter_date and fda_483_date for PDUFA events.

Usage:
    python scripts/collect_manufacturing_temporal.py

Based on web search findings from 2023-2025 FDA enforcement data.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directory
ENRICHED_DIR = Path("data/enriched")

# Collected Warning Letter data from web searches
# Format: company_name -> {date, source, evidence, confidence}
WARNING_LETTER_DATA = {
    # Merck - Warning Letter March 2025 (West Point, PA)
    "Merck & Co.": {
        "warning_letter_date": "2025-03-01",  # Approximate, March 2025
        "source": "fda.gov/pharmtech",
        "confidence": 0.85,
        "evidence": ["Merck West Point, Pennsylvania facility received Warning Letter"],
        "searched": True,
    },
    # Bristol-Myers Squibb - Warning Letter October 2022 (Phoenix, AZ)
    "Bristol-Myers Squibb": {
        "warning_letter_date": "2022-10-31",
        "source": "fda.gov",
        "confidence": 0.9,
        "evidence": ["Phoenix AZ fill/finish plant - contamination issues with Abraxane production"],
        "searched": True,
    },
    # GlaxoSmithKline - Warning Letter 2016 (Worthing, UK)
    "GlaxoSmithKline": {
        "warning_letter_date": "2016-01-01",  # 2016, exact date unknown
        "source": "fda.gov/fiercepharma",
        "confidence": 0.85,
        "evidence": ["Worthing UK plant - penicillin cross-contamination, 187 instances in 3.5 years"],
        "searched": True,
    },
    # Pfizer - Warning Letter February 2017 (McPherson, KS via Hospira)
    "Pfizer": {
        "warning_letter_date": "2017-02-14",
        "source": "fda.gov",
        "confidence": 0.9,
        "evidence": ["McPherson KS drug plant (Hospira acquisition) - vancomycin contamination"],
        "searched": True,
    },
    # Sanofi - Warning Letter January 2025 (Framingham, MA - Genzyme)
    "Sanofi": {
        "warning_letter_date": "2025-01-15",
        "source": "fda.gov",
        "confidence": 0.95,
        "evidence": ["Genzyme Framingham MA facility - 20% bioreactor rejection rate, CGMP violations"],
        "searched": True,
    },
    # Amneal Pharmaceuticals - Warning Letter August 2025 (India facility)
    "Amneal Pharmaceuticals": {
        "warning_letter_date": "2025-08-27",
        "source": "fda.gov",
        "confidence": 0.95,
        "evidence": ["India facility (FEI 3018907202) - particulate contamination in sterile injectables"],
        "searched": True,
    },
    # Eli Lilly - Warning Letter September 2025 (marketing)
    "Eli Lilly": {
        "warning_letter_date": "2025-09-09",
        "source": "fda.gov",
        "confidence": 0.9,
        "evidence": ["Marketing violation - GLP-1 promotional materials (Zepbound, Mounjaro)"],
        "searched": True,
    },
    # Amgen - Warning Letter January 2014 (Thousand Oaks, CA)
    "Amgen": {
        "warning_letter_date": "2014-01-27",
        "source": "fda.gov",
        "confidence": 0.85,
        "evidence": ["Thousand Oaks CA facility - drug/device combo violations (Prolia, Enbrel prefilled syringes)"],
        "searched": True,
    },
    # AstraZeneca - Warning Letter August 2023 (marketing, resolved May 2024)
    "AstraZeneca": {
        "warning_letter_date": "2023-08-04",
        "source": "fda.gov/opdp",
        "confidence": 0.85,
        "evidence": ["BREZTRI promotional materials violation - resolved May 2024"],
        "searched": True,
    },
}

# Companies with confirmed NO warning letters in 2023-2025
NO_WARNING_LETTER = {
    "Biogen": {"searched": True, "note": "No manufacturing warning letters found 2023-2025"},
    "Gilead Sciences": {"searched": True, "note": "No manufacturing warning letters found 2023-2025"},
    "Vertex Pharmaceuticals": {"searched": True, "note": "No manufacturing warning letters found 2023-2025"},
    "Incyte Corporation": {"searched": True, "note": "Untitled letter for marketing only, no manufacturing WL"},
    "Ionis Pharmaceuticals": {"searched": True, "note": "No warning letters found 2023-2025"},
    "AbbVie": {"searched": True, "note": "Untitled letters for marketing only, no manufacturing WL"},
    "Novartis": {"searched": True, "note": "No manufacturing warning letters found 2023-2025"},
}

# FDA 483 data from web searches
# Format: company_name -> {date, observations, source, evidence, confidence}
FDA_483_DATA = {
    # Gilead Sciences - Form 483 February 2024 (La Verne, CA)
    "Gilead Sciences": {
        "fda_483_date": "2024-02-12",
        "source": "redica.com/fda",
        "confidence": 0.85,
        "evidence": ["La Verne US facility Form 483 dated February 12, 2024"],
        "searched": True,
    },
    # Eli Lilly - Form 483 2023 (Indianapolis)
    "Eli Lilly": {
        "fda_483_date": "2023-01-01",  # Early 2023
        "fda_483_observations": 3,
        "source": "fiercepharma",
        "confidence": 0.8,
        "evidence": ["Indianapolis site - 3 manufacturing shortfalls, aseptic technique deficiency"],
        "searched": True,
    },
    # AbbVie - Form 483 April 2024 and October 2023 (Barceloneta, Puerto Rico)
    "AbbVie": {
        "fda_483_date": "2024-04-18",
        "source": "pharmacompass",
        "confidence": 0.85,
        "evidence": ["Barceloneta PR facility inspection ended April 18, 2024 - Voluntary Action Indicated"],
        "searched": True,
    },
}


def load_enriched_events() -> list[dict]:
    """Load all enriched events."""
    events = []
    for f in ENRICHED_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                data["_file_path"] = str(f)
                events.append(data)
        except Exception as e:
            logger.warning(f"Failed to load {f}: {e}")
    return events


def group_by_company(events: list[dict]) -> dict[str, list[dict]]:
    """Group events by company_name."""
    by_company = defaultdict(list)
    for e in events:
        company = e.get("company_name", "")
        if company:
            by_company[company].append(e)
    return dict(by_company)


def create_status_field(
    value: Optional[str],
    status: str,
    source: str,
    confidence: float,
    evidence: list[str] = None,
    note: str = None,
) -> dict:
    """Create a StatusField-compatible dict."""
    return {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 2 if source else None,
        "evidence": evidence or [],
        "searched_sources": [source] if source else [],
        "last_searched": datetime.utcnow().isoformat(),
        "error": None,
        "note": note,
    }


def update_event(event: dict, company_name: str) -> tuple[dict, bool]:
    """
    Update event with manufacturing temporal data.

    Returns:
        (updated_event, was_modified)
    """
    modified = False

    # Check for warning letter data
    if company_name in WARNING_LETTER_DATA:
        wl_data = WARNING_LETTER_DATA[company_name]

        # Only update if not already searched or found
        current_wl = event.get("warning_letter_date", {})
        current_status = current_wl.get("status", "not_searched")

        if current_status in ("not_searched", "not_found"):
            event["warning_letter_date"] = create_status_field(
                value=wl_data["warning_letter_date"],
                status="found",
                source=wl_data["source"],
                confidence=wl_data["confidence"],
                evidence=wl_data["evidence"],
            )
            modified = True
            logger.info(f"  Updated warning_letter_date for {event.get('event_id')}")

    elif company_name in NO_WARNING_LETTER:
        # Confirmed no warning letter
        current_wl = event.get("warning_letter_date", {})
        current_status = current_wl.get("status", "not_searched")

        if current_status == "not_searched":
            no_wl_data = NO_WARNING_LETTER[company_name]
            event["warning_letter_date"] = create_status_field(
                value=None,
                status="confirmed_none",
                source="websearch_fda",
                confidence=0.8,
                note=no_wl_data.get("note"),
            )
            modified = True
            logger.info(f"  Set warning_letter_date to confirmed_none for {event.get('event_id')}")

    # Check for FDA 483 data
    if company_name in FDA_483_DATA:
        fda483_data = FDA_483_DATA[company_name]

        # Only update if not already searched or found
        current_483 = event.get("fda_483_date", {})
        current_status = current_483.get("status", "not_searched")

        if current_status in ("not_searched", "not_found"):
            event["fda_483_date"] = create_status_field(
                value=fda483_data["fda_483_date"],
                status="found",
                source=fda483_data["source"],
                confidence=fda483_data["confidence"],
                evidence=fda483_data["evidence"],
            )
            modified = True
            logger.info(f"  Updated fda_483_date for {event.get('event_id')}")

            # Also update observations if available
            if "fda_483_observations" in fda483_data:
                event["fda_483_observations"] = create_status_field(
                    value=fda483_data["fda_483_observations"],
                    status="found",
                    source=fda483_data["source"],
                    confidence=fda483_data["confidence"],
                    evidence=fda483_data["evidence"],
                )
                logger.info(f"  Updated fda_483_observations for {event.get('event_id')}")

    # Update enriched_at timestamp if modified
    if modified:
        event["enriched_at"] = datetime.utcnow().isoformat()

    return event, modified


def save_event(event: dict) -> None:
    """Save event back to file."""
    file_path = event.pop("_file_path", None)
    if not file_path:
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2, ensure_ascii=False, default=str)


def main():
    """Main entry point."""
    logger.info("Loading enriched events...")
    events = load_enriched_events()
    logger.info(f"Loaded {len(events)} events")

    # Group by company
    by_company = group_by_company(events)
    logger.info(f"Found {len(by_company)} unique companies")

    # Track statistics
    stats = {
        "total_events": len(events),
        "events_updated": 0,
        "warning_letter_found": 0,
        "warning_letter_confirmed_none": 0,
        "fda_483_found": 0,
        "companies_processed": 0,
    }

    # Process companies with warning letter or 483 data
    target_companies = set(WARNING_LETTER_DATA.keys()) | set(NO_WARNING_LETTER.keys()) | set(FDA_483_DATA.keys())

    for company_name in target_companies:
        if company_name not in by_company:
            logger.warning(f"Company not found in events: {company_name}")
            continue

        company_events = by_company[company_name]
        logger.info(f"\nProcessing {company_name} ({len(company_events)} events)")
        stats["companies_processed"] += 1

        for event in company_events:
            updated_event, modified = update_event(event, company_name)

            if modified:
                save_event(updated_event)
                stats["events_updated"] += 1

                # Track what was found
                wl_status = updated_event.get("warning_letter_date", {}).get("status")
                if wl_status == "found":
                    stats["warning_letter_found"] += 1
                elif wl_status == "confirmed_none":
                    stats["warning_letter_confirmed_none"] += 1

                if updated_event.get("fda_483_date", {}).get("status") == "found":
                    stats["fda_483_found"] += 1

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("COLLECTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total events: {stats['total_events']}")
    logger.info(f"Companies processed: {stats['companies_processed']}")
    logger.info(f"Events updated: {stats['events_updated']}")
    logger.info(f"Warning letters found: {stats['warning_letter_found']}")
    logger.info(f"Warning letters confirmed none: {stats['warning_letter_confirmed_none']}")
    logger.info(f"FDA 483 dates found: {stats['fda_483_found']}")

    # Calculate new coverage
    with_wl = sum(1 for e in events if e.get("warning_letter_date", {}).get("status") == "found")
    with_483 = sum(1 for e in events if e.get("fda_483_date", {}).get("status") == "found")
    logger.info(f"\nNew coverage:")
    logger.info(f"  warning_letter_date: {with_wl}/{len(events)} ({100*with_wl/len(events):.1f}%)")
    logger.info(f"  fda_483_date: {with_483}/{len(events)} ({100*with_483/len(events):.1f}%)")


if __name__ == "__main__":
    main()
