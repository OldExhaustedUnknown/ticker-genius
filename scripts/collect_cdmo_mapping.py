"""
CDMO Mapping Collection Script
==============================
바이오텍-CDMO 관계 수집 및 CDMO 이슈 전파

Usage:
    python scripts/collect_cdmo_mapping.py --fetch      # CDMO 관계 검색
    python scripts/collect_cdmo_mapping.py --propagate  # 이슈 전파
    python scripts/collect_cdmo_mapping.py --status     # 상태 확인
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
import re
import argparse
from datetime import datetime, date
from collections import defaultdict, Counter
from typing import Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"
CDMO_MAP_FILE = DATA_DIR / "cdmo_mapping.json"
CDMO_ISSUES_FILE = DATA_DIR / "cdmo_issues.json"


def json_serializer(obj: Any) -> str:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Known CDMO list with their FDA issues
CDMO_DATABASE = {
    "Catalent": {
        "facilities": [
            {"name": "Bloomington", "location": "Indiana", "type": "biologics"},
            {"name": "Somerset", "location": "New Jersey", "type": "oral solid dose"},
            {"name": "Madison", "location": "Wisconsin", "type": "gene therapy"},
            {"name": "Anagni", "location": "Italy", "type": "sterile fill-finish"},
        ],
        "fda_issues": [
            {"date": "2023-09-01", "type": "483", "facility": "Bloomington", "observations": 4},
            {"date": "2022-12-01", "type": "483", "facility": "Somerset"},
        ],
    },
    "Lonza": {
        "facilities": [
            {"name": "Portsmouth", "location": "New Hampshire", "type": "biologics"},
            {"name": "Visp", "location": "Switzerland", "type": "API"},
            {"name": "Houston", "location": "Texas", "type": "cell therapy"},
        ],
        "fda_issues": [
            {"date": "2023-08-01", "type": "483", "facility": "Portsmouth"},
        ],
    },
    "Thermo Fisher": {
        "facilities": [
            {"name": "Greenville", "location": "North Carolina", "type": "sterile"},
            {"name": "St. Louis", "location": "Missouri", "type": "biologics"},
        ],
        "fda_issues": [
            {"date": "2023-10-01", "type": "483", "facility": "Greenville"},
        ],
    },
    "Samsung Biologics": {
        "facilities": [
            {"name": "Incheon", "location": "South Korea", "type": "biologics"},
        ],
        "fda_issues": [],  # Clean record
    },
    "WuXi Biologics": {
        "facilities": [
            {"name": "Wuxi", "location": "China", "type": "biologics"},
            {"name": "Shanghai", "location": "China", "type": "cell therapy"},
        ],
        "fda_issues": [],  # Note: Geopolitical concerns
    },
    "WuXi AppTec": {
        "facilities": [
            {"name": "Shanghai", "location": "China", "type": "API"},
        ],
        "fda_issues": [],
    },
    "Boehringer Ingelheim": {
        "facilities": [
            {"name": "Fremont", "location": "California", "type": "biologics"},
            {"name": "Vienna", "location": "Austria", "type": "biologics"},
        ],
        "fda_issues": [],  # Clean record
    },
    "FUJIFILM Diosynth": {
        "facilities": [
            {"name": "Research Triangle Park", "location": "North Carolina", "type": "biologics"},
            {"name": "College Station", "location": "Texas", "type": "gene therapy"},
        ],
        "fda_issues": [],
    },
    "Emergent BioSolutions": {
        "facilities": [
            {"name": "Bayview", "location": "Maryland", "type": "vaccines"},
        ],
        "fda_issues": [
            {"date": "2021-04-01", "type": "warning_letter", "facility": "Bayview", "issue": "J&J vaccine contamination"},
        ],
    },
    "Patheon": {
        "facilities": [
            {"name": "Cincinnati", "location": "Ohio", "type": "oral solid dose"},
            {"name": "Greenville", "location": "North Carolina", "type": "sterile"},
        ],
        "fda_issues": [],
    },
}

# Known drug-CDMO relationships (manually curated)
KNOWN_DRUG_CDMO = {
    # Drug name patterns -> CDMO
    "moderna": ["Catalent", "Lonza"],  # COVID vaccines
    "biontech": ["Catalent"],
    "novavax": ["Emergent BioSolutions"],
    "bluebird bio": ["Lonza"],  # Gene therapy
    "spark therapeutics": ["Catalent"],
    "biomarin": ["Catalent"],
    "ultragenyx": ["Catalent"],
    "sarepta": ["Catalent"],  # Gene therapy
    "rocket pharmaceuticals": ["Lonza"],
    "solid biosciences": ["Catalent"],
    "passage bio": ["Catalent"],
    "regenxbio": ["Catalent"],
    "voyager therapeutics": ["Catalent"],
    "sangamo therapeutics": ["Lonza"],
    "intellia therapeutics": ["Lonza"],
    "crispr therapeutics": ["Lonza"],
    "editas medicine": ["Lonza"],
    "beam therapeutics": ["Lonza"],
    # Biosimilars often use Samsung
    "samsung bioepis": ["Samsung Biologics"],
    "alvotech": ["Samsung Biologics"],
    "coherus biosciences": ["Samsung Biologics"],
}


def load_events() -> list[dict]:
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


def save_event(event: dict):
    """Save event back to file."""
    file_path = event.pop("_file_path", None)
    if not file_path:
        return
    event["enriched_at"] = datetime.now().isoformat()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2, ensure_ascii=False, default=json_serializer)


def create_status_field(
    value: Optional[Any],
    status: str,
    source: str,
    confidence: float,
    evidence: list[str] = None,
) -> dict:
    """Create StatusField-compatible dict."""
    return {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 3,  # CDMO mapping is tier 3
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
        "error": None,
    }


def match_drug_to_cdmo(drug_name: str, company_name: str) -> list[str]:
    """Match a drug/company to potential CDMOs."""
    cdmos = []

    # Normalize names
    drug_lower = drug_name.lower()
    company_lower = company_name.lower()

    # Check known relationships
    for pattern, cdmo_list in KNOWN_DRUG_CDMO.items():
        if pattern in drug_lower or pattern in company_lower:
            cdmos.extend(cdmo_list)

    # Check for gene therapy (likely uses Catalent/Lonza)
    gene_therapy_keywords = ["gene therapy", "aav", "lentiviral", "crispr", "car-t", "cell therapy"]
    if any(kw in drug_lower or kw in company_lower for kw in gene_therapy_keywords):
        if "Catalent" not in cdmos:
            cdmos.append("Catalent")
        if "Lonza" not in cdmos:
            cdmos.append("Lonza")

    # Check for biosimilar (likely uses Samsung)
    if "biosimilar" in drug_lower or "bioepis" in company_lower:
        if "Samsung Biologics" not in cdmos:
            cdmos.append("Samsung Biologics")

    return list(set(cdmos))


def get_cdmo_issues(cdmo_name: str) -> list[dict]:
    """Get FDA issues for a CDMO."""
    cdmo_data = CDMO_DATABASE.get(cdmo_name, {})
    return cdmo_data.get("fda_issues", [])


async def search_cdmo_relationship(company_name: str) -> list[str]:
    """Search for CDMO relationships via web search."""
    from tickergenius.collection.web_search import WebSearchClient

    client = WebSearchClient()
    cdmos_found = []

    try:
        # Search for manufacturing partnerships
        queries = [
            f'"{company_name}" manufacturing agreement',
            f'"{company_name}" contract manufacturing CDMO',
        ]

        for query in queries:
            results = await client.search(query, max_results=5)

            for result in results:
                text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

                # Check for CDMO mentions
                for cdmo_name in CDMO_DATABASE.keys():
                    if cdmo_name.lower() in text:
                        cdmos_found.append(cdmo_name)

            await asyncio.sleep(2)  # Rate limit

    except Exception as e:
        logger.error(f"Search error for {company_name}: {e}")

    return list(set(cdmos_found))


def propagate_cdmo_issues():
    """Propagate CDMO FDA issues to related events."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # Load or create CDMO mapping
    cdmo_mapping = {}
    if CDMO_MAP_FILE.exists():
        with open(CDMO_MAP_FILE, "r", encoding="utf-8") as f:
            cdmo_mapping = json.load(f)

    # Stats
    updated = 0
    cdmo_matched = Counter()

    for event in events:
        drug_name = event.get("drug_name", "")
        company_name = event.get("company_name", "")
        event_id = event.get("event_id", "")

        # Check existing 483 status
        existing_483 = event.get("fda_483_date", {})
        existing_status = existing_483.get("status") if isinstance(existing_483, dict) else None

        # Skip if already has 483 data
        if existing_status == "found":
            continue

        # Find CDMOs
        cdmos = match_drug_to_cdmo(drug_name, company_name)

        # Check cached mapping
        if company_name in cdmo_mapping:
            cached_cdmos = cdmo_mapping[company_name]
            cdmos = list(set(cdmos + cached_cdmos))

        if not cdmos:
            continue

        # Get CDMO issues
        for cdmo_name in cdmos:
            issues = get_cdmo_issues(cdmo_name)

            if issues:
                # Get the most recent issue
                most_recent = max(issues, key=lambda x: x.get("date", ""))
                cdmo_matched[cdmo_name] += 1

                # Update event with CDMO issue
                event["fda_483_date"] = create_status_field(
                    value=most_recent["date"],
                    status="found",
                    source=f"cdmo_{cdmo_name.lower().replace(' ', '_')}",
                    confidence=0.7,  # Lower confidence for CDMO-based
                    evidence=[
                        f"CDMO: {cdmo_name}",
                        f"Facility: {most_recent.get('facility', 'N/A')}",
                        f"Type: {most_recent.get('type', 'N/A')}",
                    ],
                )

                # Also add CDMO name to event
                event["cdmo_name"] = create_status_field(
                    value=cdmo_name,
                    status="found",
                    source="cdmo_mapping",
                    confidence=0.7,
                )

                save_event(event)
                updated += 1
                logger.debug(f"Updated {event_id} with CDMO {cdmo_name} issue")
                break  # Only apply first matching CDMO with issues

    logger.info(f"\nUpdated {updated} events with CDMO-based FDA 483 data")
    logger.info("CDMO matches:")
    for cdmo, count in cdmo_matched.most_common():
        logger.info(f"  {cdmo}: {count}")


async def fetch_cdmo_relationships(limit: Optional[int] = None):
    """Fetch CDMO relationships via web search."""
    logger.info("Fetching CDMO relationships...")

    events = load_events()

    # Get unique companies
    companies = set()
    for e in events:
        company = e.get("company_name", "")
        if company:
            companies.add(company)

    companies = sorted(companies)
    if limit:
        companies = companies[:limit]

    logger.info(f"Companies to search: {len(companies)}")

    # Load existing mapping
    cdmo_mapping = {}
    if CDMO_MAP_FILE.exists():
        with open(CDMO_MAP_FILE, "r", encoding="utf-8") as f:
            cdmo_mapping = json.load(f)

    new_found = 0
    for i, company in enumerate(companies):
        if company in cdmo_mapping:
            continue

        logger.info(f"[{i+1}/{len(companies)}] Searching: {company}")

        # First check known relationships
        cdmos = []
        for e in events:
            if e.get("company_name") == company:
                drug = e.get("drug_name", "")
                cdmos.extend(match_drug_to_cdmo(drug, company))

        # Web search for additional relationships
        search_cdmos = await search_cdmo_relationship(company)
        cdmos.extend(search_cdmos)

        cdmos = list(set(cdmos))

        if cdmos:
            cdmo_mapping[company] = cdmos
            new_found += 1
            logger.info(f"  Found CDMOs: {cdmos}")

        if (i + 1) % 20 == 0:
            # Save progress
            with open(CDMO_MAP_FILE, "w", encoding="utf-8") as f:
                json.dump(cdmo_mapping, f, indent=2)

    # Save final mapping
    with open(CDMO_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(cdmo_mapping, f, indent=2)

    logger.info(f"\nFound CDMO relationships for {new_found} new companies")
    logger.info(f"Total companies with CDMO mapping: {len(cdmo_mapping)}")


def print_status():
    """Print current status."""
    events = load_events()

    # CDMO coverage
    with_cdmo = 0
    cdmo_based_483 = 0

    for e in events:
        cdmo = e.get("cdmo_name", {})
        if isinstance(cdmo, dict) and cdmo.get("status") == "found":
            with_cdmo += 1

        f483 = e.get("fda_483_date", {})
        if isinstance(f483, dict):
            source = f483.get("source", "")
            if "cdmo" in source:
                cdmo_based_483 += 1

    # 483 overall
    f483_status = Counter()
    for e in events:
        f483 = e.get("fda_483_date", {})
        status = f483.get("status", "not_searched") if isinstance(f483, dict) else "not_searched"
        f483_status[status] += 1

    print("\n" + "=" * 60)
    print("CDMO Mapping Status")
    print("=" * 60)
    print(f"\nTotal events: {len(events)}")
    print(f"Events with CDMO mapping: {with_cdmo} ({100*with_cdmo/len(events):.1f}%)")
    print(f"Events with CDMO-based 483: {cdmo_based_483}")

    print("\nFDA 483 Date (including CDMO):")
    for status, count in sorted(f483_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(events):.1f}%)")

    # CDMO mapping file
    if CDMO_MAP_FILE.exists():
        with open(CDMO_MAP_FILE, "r", encoding="utf-8") as f:
            cdmo_mapping = json.load(f)
        print(f"\nCDMO mapping file: {len(cdmo_mapping)} companies")

        # Count CDMO usage
        cdmo_usage = Counter()
        for cdmos in cdmo_mapping.values():
            for cdmo in cdmos:
                cdmo_usage[cdmo] += 1

        print("CDMO usage in mapping:")
        for cdmo, count in cdmo_usage.most_common(10):
            print(f"  {cdmo}: {count}")


async def main():
    parser = argparse.ArgumentParser(description="CDMO Mapping Collection")
    parser.add_argument("--fetch", action="store_true", help="Fetch CDMO relationships")
    parser.add_argument("--propagate", action="store_true", help="Propagate CDMO issues to events")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--limit", type=int, help="Limit companies to search")
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.fetch:
        await fetch_cdmo_relationships(args.limit)
        print_status()
    elif args.propagate:
        propagate_cdmo_issues()
        print_status()
    else:
        # Default: propagate known relationships
        propagate_cdmo_issues()
        print_status()


if __name__ == "__main__":
    asyncio.run(main())
