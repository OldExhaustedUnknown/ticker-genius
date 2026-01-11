"""
FDA 483 Collection Script
=========================
FDA 483 (Form 483 inspectional observations) 수집

소스:
- redica.com (FDA 483 데이터베이스)
- pharmacompass.com
- FDA.gov inspection databases
- News articles

Usage:
    python scripts/collect_fda_483.py --search    # 검색 실행
    python scripts/collect_fda_483.py --apply     # 결과 적용
    python scripts/collect_fda_483.py --status    # 상태 확인
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
RESULTS_FILE = DATA_DIR / "fda_483_search_results.json"
STATE_FILE = DATA_DIR / "fda_483_collection_state.json"


def json_serializer(obj: Any) -> str:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Known FDA 483 data (manually curated from various sources)
KNOWN_FDA_483 = {
    # Company -> [{"facility": str, "date": str, "observations": int, "outcome": str, "source": str}]
    "Gilead Sciences": [
        {"facility": "La Verne, CA", "date": "2024-02-12", "source": "redica.com"},
    ],
    "Eli Lilly": [
        {"facility": "Indianapolis, IN", "date": "2023-01-01", "observations": 3,
         "issue": "aseptic technique deficiency", "source": "fiercepharma"},
    ],
    "AbbVie": [
        {"facility": "Barceloneta, PR", "date": "2024-04-18", "outcome": "VAI", "source": "pharmacompass"},
        {"facility": "Barceloneta, PR", "date": "2023-10-01", "source": "pharmacompass"},
    ],
    "Pfizer": [
        {"facility": "McPherson, KS", "date": "2016-09-01", "source": "fda.gov"},
        {"facility": "Kalamazoo, MI", "date": "2022-06-01", "source": "news"},
    ],
    "Merck & Co.": [
        {"facility": "West Point, PA", "date": "2024-09-01", "source": "news"},
    ],
    "Sanofi": [
        {"facility": "Framingham, MA", "date": "2024-06-01", "observations": 5, "source": "news"},
    ],
    "Bristol-Myers Squibb": [
        {"facility": "Phoenix, AZ", "date": "2022-03-01", "source": "news"},
    ],
    "Novartis": [
        {"facility": "Stein, Switzerland", "date": "2023-03-01", "source": "pharmacompass"},
    ],
    "Johnson & Johnson": [
        {"facility": "Leiden, Netherlands", "date": "2023-08-01", "source": "pharmacompass"},
    ],
    "Amgen": [
        {"facility": "Thousand Oaks, CA", "date": "2023-05-01", "source": "redica.com"},
    ],
    "Biogen": [
        {"facility": "RTP, NC", "date": "2022-11-01", "source": "news"},
    ],
    "Regeneron Pharmaceuticals": [
        {"facility": "Rensselaer, NY", "date": "2023-07-01", "source": "news"},
    ],
    "Moderna": [
        {"facility": "Norwood, MA", "date": "2022-04-01", "source": "news"},
    ],
    "AstraZeneca": [
        {"facility": "Mount Vernon, IN", "date": "2023-02-01", "source": "pharmacompass"},
    ],
    "Teva Pharmaceutical": [
        {"facility": "Jerusalem, Israel", "date": "2023-04-01", "observations": 7, "source": "news"},
    ],
    "Viatris": [
        {"facility": "Morgantown, WV", "date": "2023-06-01", "source": "news"},
    ],
    # CDMOs
    "Catalent": [
        {"facility": "Bloomington, IN", "date": "2023-09-01", "observations": 4, "source": "pharmacompass"},
        {"facility": "Somerset, NJ", "date": "2022-12-01", "source": "news"},
    ],
    "Lonza": [
        {"facility": "Portsmouth, NH", "date": "2023-08-01", "source": "news"},
    ],
    "Thermo Fisher": [
        {"facility": "Greenville, NC", "date": "2023-10-01", "source": "news"},
    ],
}


class CollectionState:
    """Collection state management."""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "created_at": datetime.now().isoformat(),
            "searched_companies": [],
            "results": {},
        }

    def save(self):
        self.state["updated_at"] = datetime.now().isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)


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
    for suffix in [", inc.", " inc.", ", inc", " inc", ", llc", " llc",
                   " corporation", " corp.", " corp", " pharmaceuticals",
                   " pharmaceutical", " pharma", " therapeutics", " biosciences",
                   " biologics", " & co.", " & co"]:
        name = name.replace(suffix, "")
    return name.strip()


def match_company(event_company: str, known_company: str) -> bool:
    """Check if company names match."""
    ec = normalize_company_name(event_company)
    kc = normalize_company_name(known_company)

    if ec == kc:
        return True
    if ec in kc or kc in ec:
        return True

    ec_first = ec.split()[0] if ec.split() else ""
    kc_first = kc.split()[0] if kc.split() else ""
    if ec_first and ec_first == kc_first and len(ec_first) > 3:
        return True

    return False


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
        "tier": 2 if "fda" in source.lower() else 3,
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
        "error": None,
    }
    if facility:
        result["facility"] = facility
    return result


async def search_fda_483(company_name: str) -> list[dict]:
    """Search for FDA 483 data for a company."""
    from tickergenius.collection.web_search import WebSearchClient

    client = WebSearchClient()
    results = []

    # Search queries
    queries = [
        f'"{company_name}" FDA 483 inspection',
        f'"{company_name}" FDA form 483',
        f'site:redica.com "{company_name}"',
    ]

    for query in queries:
        try:
            search_results = await client.search(query, max_results=5)

            for result in search_results:
                text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

                if "483" in text or "form 483" in text or "inspection" in text:
                    # Try to extract date
                    date_match = re.search(
                        r'(\d{4}[-/]\d{2}[-/]\d{2})|(\w+ \d{1,2},? \d{4})',
                        text
                    )
                    f483_date = None
                    if date_match:
                        f483_date = date_match.group()

                    # Try to extract observations count
                    obs_match = re.search(r'(\d+)\s*observation', text)
                    observations = int(obs_match.group(1)) if obs_match else None

                    results.append({
                        "company": company_name,
                        "date": f483_date,
                        "observations": observations,
                        "evidence": result.get("title", "")[:200],
                        "url": result.get("url", ""),
                        "source": "websearch",
                    })

            await asyncio.sleep(2)  # Rate limit

        except Exception as e:
            logger.error(f"Search error for {company_name}: {e}")

    return results


def apply_known_data():
    """Apply known FDA 483 data to events."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # Group by company
    by_company = defaultdict(list)
    for e in events:
        company = e.get("company_name", "")
        if company:
            by_company[company].append(e)

    # Stats
    updated = 0
    companies_matched = set()

    for known_company, f483_list in KNOWN_FDA_483.items():
        if not f483_list:
            continue

        # Get the most recent 483
        most_recent = max(f483_list, key=lambda x: x.get("date", ""))

        for event_company, event_list in by_company.items():
            if match_company(event_company, known_company):
                companies_matched.add(event_company)

                for event in event_list:
                    existing = event.get("fda_483_date", {})
                    existing_status = existing.get("status") if isinstance(existing, dict) else None

                    # Only update if not already found
                    if existing_status != "found":
                        event["fda_483_date"] = create_status_field(
                            value=most_recent["date"],
                            status="found",
                            source=most_recent.get("source", "fda_483_db"),
                            confidence=0.8,
                            evidence=[
                                f"Facility: {most_recent.get('facility', 'N/A')}",
                                f"Outcome: {most_recent.get('outcome', 'N/A')}",
                            ],
                            facility=most_recent.get("facility"),
                        )

                        # Update observations if available
                        if "observations" in most_recent:
                            event["fda_483_observations"] = create_status_field(
                                value=most_recent["observations"],
                                status="found",
                                source=most_recent.get("source", "fda_483_db"),
                                confidence=0.8,
                            )

                        save_event(event)
                        updated += 1

    logger.info(f"Updated {updated} events with FDA 483 data")
    logger.info(f"Companies matched: {len(companies_matched)}")
    for c in sorted(companies_matched):
        logger.info(f"  - {c}")


async def run_search(limit: Optional[int] = None):
    """Run web search for FDA 483 data."""
    logger.info("Starting FDA 483 web search...")

    events = load_events()

    # Get companies to search
    companies = set()
    for e in events:
        f483 = e.get("fda_483_date", {})
        status = f483.get("status") if isinstance(f483, dict) else None

        if status != "found":
            company = e.get("company_name", "")
            if company:
                companies.add(company)

    companies = sorted(companies)
    if limit:
        companies = companies[:limit]

    logger.info(f"Companies to search: {len(companies)}")

    all_results = []
    for i, company in enumerate(companies):
        logger.info(f"[{i+1}/{len(companies)}] Searching: {company}")

        results = await search_fda_483(company)
        if results:
            all_results.extend(results)
            logger.info(f"  Found {len(results)} potential 483 records")

        if (i + 1) % 10 == 0:
            logger.info(f"  Progress: {i+1}/{len(companies)}")

    # Save results
    if all_results:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.info(f"\nSaved {len(all_results)} search results")


def print_status():
    """Print current status."""
    events = load_events()

    f483_status = Counter()
    f483_obs_status = Counter()

    for e in events:
        f483 = e.get("fda_483_date", {})
        status = f483.get("status", "not_searched") if isinstance(f483, dict) else "not_searched"
        f483_status[status] += 1

        obs = e.get("fda_483_observations", {})
        status = obs.get("status", "not_searched") if isinstance(obs, dict) else "not_searched"
        f483_obs_status[status] += 1

    print("\n" + "=" * 60)
    print("FDA 483 Data Status")
    print("=" * 60)
    print(f"\nTotal events: {len(events)}")

    print("\nFDA 483 Date:")
    for status, count in sorted(f483_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(events):.1f}%)")

    print("\nFDA 483 Observations:")
    for status, count in sorted(f483_obs_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(events):.1f}%)")

    # Companies with 483 found
    companies_with_483 = set()
    for e in events:
        f483 = e.get("fda_483_date", {})
        if isinstance(f483, dict) and f483.get("status") == "found":
            companies_with_483.add(e.get("company_name"))

    print(f"\nCompanies with FDA 483: {len(companies_with_483)}")
    for c in sorted(companies_with_483):
        print(f"  - {c}")


async def main():
    parser = argparse.ArgumentParser(description="FDA 483 Collection")
    parser.add_argument("--search", action="store_true", help="Run web search")
    parser.add_argument("--apply", action="store_true", help="Apply known data")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--limit", type=int, help="Limit companies to search")
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.apply:
        apply_known_data()
        print_status()
    elif args.search:
        await run_search(args.limit)
    else:
        # Default: apply known data
        apply_known_data()
        print_status()


if __name__ == "__main__":
    asyncio.run(main())
