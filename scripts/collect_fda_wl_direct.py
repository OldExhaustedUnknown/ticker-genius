"""
FDA Warning Letters Direct Collection
=====================================
FDA.gov에서 Warning Letters 직접 수집 후 이벤트와 매칭

Usage:
    python scripts/collect_fda_wl_direct.py --fetch    # FDA에서 WL 목록 가져오기
    python scripts/collect_fda_wl_direct.py --match    # 이벤트와 매칭
    python scripts/collect_fda_wl_direct.py --status   # 상태 확인
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
from collections import defaultdict
from typing import Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"
WL_CACHE_FILE = DATA_DIR / "fda_warning_letters_cache.json"
FACILITY_MAP_FILE = DATA_DIR / "company_facilities.json"


def json_serializer(obj: Any) -> str:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Known pharmaceutical manufacturing facilities (manually curated)
# Format: company_name -> [{"facility": str, "location": str, "fei": str}]
KNOWN_FACILITIES = {
    "Pfizer": [
        {"facility": "McPherson", "location": "Kansas", "fei": "3002806991"},
        {"facility": "Kalamazoo", "location": "Michigan"},
        {"facility": "Puurs", "location": "Belgium"},
        {"facility": "Hospira", "location": "McPherson, KS"},  # Acquired
    ],
    "Merck & Co.": [
        {"facility": "West Point", "location": "Pennsylvania"},
        {"facility": "Durham", "location": "North Carolina"},
        {"facility": "Riverside", "location": "California"},
    ],
    "Bristol-Myers Squibb": [
        {"facility": "Phoenix", "location": "Arizona"},
        {"facility": "Devens", "location": "Massachusetts"},
        {"facility": "New Brunswick", "location": "New Jersey"},
    ],
    "Sanofi": [
        {"facility": "Genzyme Framingham", "location": "Massachusetts"},
        {"facility": "Genzyme Allston", "location": "Massachusetts"},
        {"facility": "Frankfurt", "location": "Germany"},
    ],
    "Eli Lilly": [
        {"facility": "Indianapolis", "location": "Indiana"},
        {"facility": "Branchburg", "location": "New Jersey"},
        {"facility": "Research Triangle Park", "location": "North Carolina"},
    ],
    "AbbVie": [
        {"facility": "Barceloneta", "location": "Puerto Rico"},
        {"facility": "North Chicago", "location": "Illinois"},
    ],
    "Amgen": [
        {"facility": "Thousand Oaks", "location": "California"},
        {"facility": "West Greenwich", "location": "Rhode Island"},
    ],
    "Gilead Sciences": [
        {"facility": "La Verne", "location": "California"},
        {"facility": "Foster City", "location": "California"},
    ],
    "Novartis": [
        {"facility": "East Hanover", "location": "New Jersey"},
        {"facility": "Stein", "location": "Switzerland"},
    ],
    "Johnson & Johnson": [
        {"facility": "Janssen Beerse", "location": "Belgium"},
        {"facility": "Leiden", "location": "Netherlands"},
    ],
    "AstraZeneca": [
        {"facility": "Mount Vernon", "location": "Indiana"},
        {"facility": "Frederick", "location": "Maryland"},
    ],
    "Regeneron": [
        {"facility": "Rensselaer", "location": "New York"},
        {"facility": "Limerick", "location": "Ireland"},
    ],
    "Biogen": [
        {"facility": "Research Triangle Park", "location": "North Carolina"},
        {"facility": "Cambridge", "location": "Massachusetts"},
    ],
    "Vertex Pharmaceuticals": [
        {"facility": "Boston", "location": "Massachusetts"},
    ],
    "Moderna": [
        {"facility": "Norwood", "location": "Massachusetts"},
    ],
    "BioNTech": [
        {"facility": "Mainz", "location": "Germany"},
        {"facility": "Marburg", "location": "Germany"},
    ],
    # CDMOs (Contract Manufacturing)
    "Catalent": [
        {"facility": "Bloomington", "location": "Indiana"},
        {"facility": "Madison", "location": "Wisconsin"},
        {"facility": "Somerset", "location": "New Jersey"},
    ],
    "Lonza": [
        {"facility": "Portsmouth", "location": "New Hampshire"},
        {"facility": "Visp", "location": "Switzerland"},
    ],
    "Samsung Biologics": [
        {"facility": "Incheon", "location": "South Korea"},
    ],
    "Thermo Fisher": [
        {"facility": "St. Louis", "location": "Missouri"},
        {"facility": "Greenville", "location": "North Carolina"},
    ],
    "Amneal Pharmaceuticals": [
        {"facility": "Ahmedabad", "location": "India", "fei": "3018907202"},
    ],
}

# Known Warning Letters (2020-2025) - facility-level
KNOWN_WARNING_LETTERS = [
    {
        "company": "Pfizer",
        "facility": "McPherson",
        "date": "2017-02-14",
        "product": "vancomycin",
        "issue": "contamination",
        "source": "fda.gov",
    },
    {
        "company": "Merck & Co.",
        "facility": "West Point",
        "date": "2025-03-01",
        "issue": "CGMP violations",
        "source": "fda.gov",
    },
    {
        "company": "Bristol-Myers Squibb",
        "facility": "Phoenix",
        "date": "2022-10-31",
        "product": "Abraxane",
        "issue": "contamination",
        "source": "fda.gov",
    },
    {
        "company": "Sanofi",
        "facility": "Genzyme Framingham",
        "date": "2025-01-15",
        "issue": "bioreactor rejection, CGMP",
        "source": "fda.gov",
    },
    {
        "company": "Eli Lilly",
        "facility": "Indianapolis",
        "date": "2025-09-09",
        "issue": "GLP-1 marketing violation",
        "source": "fda.gov",
    },
    {
        "company": "Amneal Pharmaceuticals",
        "facility": "Ahmedabad",
        "date": "2025-08-27",
        "issue": "particulate contamination, sterile injectables",
        "source": "fda.gov",
    },
    {
        "company": "Amgen",
        "facility": "Thousand Oaks",
        "date": "2014-01-27",
        "product": "Prolia, Enbrel",
        "issue": "drug/device combo violations",
        "source": "fda.gov",
    },
    {
        "company": "GlaxoSmithKline",
        "facility": "Worthing",
        "date": "2016-01-01",
        "issue": "penicillin cross-contamination",
        "source": "fda.gov",
    },
    {
        "company": "AstraZeneca",
        "facility": "Marketing",
        "date": "2023-08-04",
        "product": "BREZTRI",
        "issue": "promotional materials violation",
        "source": "fda.gov/opdp",
    },
]

# Known FDA 483 observations
KNOWN_FDA_483 = [
    {
        "company": "Gilead Sciences",
        "facility": "La Verne",
        "date": "2024-02-12",
        "source": "redica.com",
    },
    {
        "company": "Eli Lilly",
        "facility": "Indianapolis",
        "date": "2023-01-01",
        "observations": 3,
        "issue": "aseptic technique deficiency",
        "source": "fiercepharma",
    },
    {
        "company": "AbbVie",
        "facility": "Barceloneta",
        "date": "2024-04-18",
        "outcome": "VAI",  # Voluntary Action Indicated
        "source": "pharmacompass",
    },
]


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


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    name = name.lower()
    # Remove common suffixes
    for suffix in [", inc.", " inc.", ", inc", " inc", ", llc", " llc",
                   " corporation", " corp.", " corp", " pharmaceuticals",
                   " pharmaceutical", " pharma", " therapeutics", " biosciences",
                   " biologics", " & co.", " & co"]:
        name = name.replace(suffix, "")
    return name.strip()


def match_company(event_company: str, wl_company: str) -> bool:
    """Check if company names match."""
    ec = normalize_company_name(event_company)
    wc = normalize_company_name(wl_company)

    # Exact match
    if ec == wc:
        return True

    # Partial match (one contains the other)
    if ec in wc or wc in ec:
        return True

    # First word match
    ec_first = ec.split()[0] if ec.split() else ""
    wc_first = wc.split()[0] if wc.split() else ""
    if ec_first and ec_first == wc_first and len(ec_first) > 3:
        return True

    return False


async def search_facility_wl(company_name: str, facilities: list[dict]) -> list[dict]:
    """Search for Warning Letters using facility names."""
    from tickergenius.collection.web_search import WebSearchClient

    client = WebSearchClient()
    results = []

    for facility in facilities:
        facility_name = facility.get("facility", "")
        location = facility.get("location", "")

        # Search queries
        queries = [
            f'"{company_name}" "{facility_name}" FDA warning letter',
            f'"{facility_name}" {location} FDA warning letter',
        ]

        for query in queries:
            try:
                search_results = await client.search(query, max_results=5)

                for result in search_results:
                    text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

                    if "warning letter" in text:
                        # Try to extract date
                        date_match = re.search(
                            r'(\d{4}[-/]\d{2}[-/]\d{2})|(\w+ \d{1,2},? \d{4})',
                            text
                        )
                        wl_date = None
                        if date_match:
                            wl_date = date_match.group()

                        results.append({
                            "company": company_name,
                            "facility": facility_name,
                            "location": location,
                            "date": wl_date,
                            "evidence": result.get("title", "")[:200],
                            "url": result.get("url", ""),
                        })

                await asyncio.sleep(1)  # Rate limit

            except Exception as e:
                logger.error(f"Search error for {facility_name}: {e}")

    return results


def create_status_field(
    value: Optional[Any],
    status: str,
    source: str,
    confidence: float,
    evidence: list[str] = None,
    facility: str = None,
) -> dict:
    """Create StatusField-compatible dict."""
    result = {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 1 if "fda.gov" in source else 3,
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
        "error": None,
    }
    if facility:
        result["facility"] = facility
    return result


def match_and_update():
    """Match known Warning Letters to events and update."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # Group by company
    by_company = defaultdict(list)
    for e in events:
        company = e.get("company_name", "")
        if company:
            by_company[company].append(e)

    logger.info(f"Found {len(by_company)} unique companies")

    # Stats
    updated_wl = 0
    updated_483 = 0

    # Match Warning Letters
    for wl in KNOWN_WARNING_LETTERS:
        wl_company = wl["company"]

        for event_company, event_list in by_company.items():
            if match_company(event_company, wl_company):
                for event in event_list:
                    # Check if already has WL with same or later date
                    existing = event.get("warning_letter_date", {})
                    existing_status = existing.get("status") if isinstance(existing, dict) else None

                    # Only update if not already found or if this is more recent
                    if existing_status != "found":
                        event["warning_letter_date"] = create_status_field(
                            value=wl["date"],
                            status="found",
                            source=wl.get("source", "fda.gov"),
                            confidence=0.9,
                            evidence=[
                                f"Facility: {wl.get('facility', 'N/A')}",
                                f"Issue: {wl.get('issue', 'N/A')}",
                                f"Product: {wl.get('product', 'N/A')}",
                            ],
                            facility=wl.get("facility"),
                        )
                        save_event(event)
                        updated_wl += 1
                        logger.info(f"Updated WL for {event.get('event_id')}: {wl['date']}")

    # Match FDA 483
    for f483 in KNOWN_FDA_483:
        f483_company = f483["company"]

        for event_company, event_list in by_company.items():
            if match_company(event_company, f483_company):
                for event in event_list:
                    existing = event.get("fda_483_date", {})
                    existing_status = existing.get("status") if isinstance(existing, dict) else None

                    if existing_status != "found":
                        event["fda_483_date"] = create_status_field(
                            value=f483["date"],
                            status="found",
                            source=f483.get("source", "fda.gov"),
                            confidence=0.85,
                            evidence=[
                                f"Facility: {f483.get('facility', 'N/A')}",
                                f"Outcome: {f483.get('outcome', 'N/A')}",
                            ],
                            facility=f483.get("facility"),
                        )

                        # Also update observations if available
                        if "observations" in f483:
                            event["fda_483_observations"] = create_status_field(
                                value=f483["observations"],
                                status="found",
                                source=f483.get("source", "fda.gov"),
                                confidence=0.85,
                            )

                        save_event(event)
                        updated_483 += 1
                        logger.info(f"Updated 483 for {event.get('event_id')}: {f483['date']}")

    logger.info(f"\nUpdated {updated_wl} events with Warning Letter data")
    logger.info(f"Updated {updated_483} events with FDA 483 data")


async def fetch_and_search():
    """Fetch FDA data and search for additional Warning Letters."""
    logger.info("Searching for additional Warning Letters using facility names...")

    events = load_events()

    # Get unique companies that need WL search
    companies_to_search = set()
    for e in events:
        company = e.get("company_name", "")
        wl = e.get("warning_letter_date", {})
        status = wl.get("status") if isinstance(wl, dict) else None

        # Search companies that have confirmed_none (might find with facility search)
        if status == "confirmed_none" and company in KNOWN_FACILITIES:
            companies_to_search.add(company)

    logger.info(f"Companies to search with facilities: {len(companies_to_search)}")

    all_results = []
    for company in companies_to_search:
        facilities = KNOWN_FACILITIES.get(company, [])
        if facilities:
            logger.info(f"Searching {company} ({len(facilities)} facilities)...")
            results = await search_facility_wl(company, facilities)
            all_results.extend(results)

            if results:
                logger.info(f"  Found {len(results)} potential Warning Letters")

    # Save results
    if all_results:
        with open(DATA_DIR / "facility_wl_search_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.info(f"\nSaved {len(all_results)} search results to facility_wl_search_results.json")


def print_status():
    """Print current status."""
    events = load_events()

    from collections import Counter
    wl_status = Counter()
    f483_status = Counter()

    for e in events:
        wl = e.get("warning_letter_date", {})
        status = wl.get("status", "not_searched") if isinstance(wl, dict) else "not_searched"
        wl_status[status] += 1

        f483 = e.get("fda_483_date", {})
        status = f483.get("status", "not_searched") if isinstance(f483, dict) else "not_searched"
        f483_status[status] += 1

    print("\n" + "=" * 60)
    print("FDA Manufacturing Data Status")
    print("=" * 60)
    print(f"\nTotal events: {len(events)}")

    print("\nWarning Letter Date:")
    for status, count in sorted(wl_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(events):.1f}%)")

    print("\nFDA 483 Date:")
    for status, count in sorted(f483_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(events):.1f}%)")

    # Companies with WL found
    companies_with_wl = set()
    for e in events:
        wl = e.get("warning_letter_date", {})
        if isinstance(wl, dict) and wl.get("status") == "found":
            companies_with_wl.add(e.get("company_name"))

    print(f"\nCompanies with Warning Letter: {len(companies_with_wl)}")
    for c in sorted(companies_with_wl):
        print(f"  - {c}")


async def main():
    parser = argparse.ArgumentParser(description="FDA Warning Letters Collection")
    parser.add_argument("--fetch", action="store_true", help="Fetch and search using facility names")
    parser.add_argument("--match", action="store_true", help="Match known data to events")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.match:
        match_and_update()
        print_status()
    elif args.fetch:
        await fetch_and_search()
    else:
        # Default: match known data
        match_and_update()
        print_status()


if __name__ == "__main__":
    asyncio.run(main())
