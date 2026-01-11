"""
Warning Letter Collection Script (Extended)
============================================
FDA Warning Letters 웹서치 기반 수집

Usage:
    python scripts/collect_warning_letters.py --limit 50  # 테스트
    python scripts/collect_warning_letters.py             # 전체 실행
    python scripts/collect_warning_letters.py --status    # 상태 확인
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
import re
import argparse
from datetime import datetime, date
from pathlib import Path
from collections import Counter
from typing import Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/warning_letter_collection.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"
STATE_FILE = DATA_DIR / "warning_letter_state.json"

# Rate limit (conservative for web search)
RATE_LIMIT_DELAY = 2.0  # seconds between searches


def json_serializer(obj: Any) -> str:
    """JSON serialization helper."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class WarningLetterState:
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
            "found_companies": {},
            "confirmed_none_companies": [],
            "failed_companies": [],
        }

    def save(self):
        self.state["updated_at"] = datetime.now().isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def is_searched(self, company: str) -> bool:
        return company in self.state["searched_companies"]

    def mark_searched(self, company: str):
        if company not in self.state["searched_companies"]:
            self.state["searched_companies"].append(company)

    def mark_found(self, company: str, data: dict):
        self.state["found_companies"][company] = data

    def mark_confirmed_none(self, company: str):
        if company not in self.state["confirmed_none_companies"]:
            self.state["confirmed_none_companies"].append(company)

    def mark_failed(self, company: str, error: str):
        self.state["failed_companies"].append({
            "company": company,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })


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


def get_companies_needing_search(events: list[dict]) -> dict[str, list[dict]]:
    """Get companies that need warning letter search."""
    companies = {}
    for e in events:
        wl = e.get("warning_letter_date", {})
        status = wl.get("status", "not_searched") if isinstance(wl, dict) else "not_searched"
        if status in ("not_searched", "not_found"):
            company = e.get("company_name", "")
            if company:
                if company not in companies:
                    companies[company] = []
                companies[company].append(e)
    return companies


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
        "tier": 3,  # Web search tier
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
        "error": None,
    }


def parse_date(date_str: str) -> Optional[str]:
    """Parse date from various formats to ISO format."""
    patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"),
        (r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})',
         lambda m: f"{m.group(3)}-{_month_to_num(m.group(1))}-{m.group(2).zfill(2)}"),
    ]

    for pattern, formatter in patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                return formatter(match)
            except Exception:
                continue
    return None


def _month_to_num(month: str) -> str:
    months = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    return months.get(month.lower(), '01')


async def search_warning_letter(company_name: str) -> dict:
    """
    Search for FDA Warning Letters for a company.

    Returns:
        {
            "found": bool,
            "warning_letter_date": str | None,
            "evidence": list[str],
            "confidence": float,
        }
    """
    try:
        from tickergenius.collection.web_search import WebSearchClient

        client = WebSearchClient()
        query = f'"{company_name}" FDA warning letter site:fda.gov'

        results = await client.search(query, max_results=10)

        if not results:
            return {"found": False, "searched": True}

        # Analyze results
        evidence = []
        wl_date = None
        found = False

        for result in results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            text = (title + " " + snippet).lower()

            # Check for warning letter indicators
            if "warning letter" in text and any(kw in text.lower() for kw in [
                company_name.lower().split()[0],  # First word of company name
                company_name.lower().replace(" ", ""),
            ]):
                found = True
                evidence.append(title[:150])

                # Try to extract date
                if wl_date is None:
                    wl_date = parse_date(title + " " + snippet)

        if found:
            return {
                "found": True,
                "warning_letter_date": wl_date,
                "evidence": evidence[:3],
                "confidence": 0.75 if wl_date else 0.6,
                "searched": True,
            }
        else:
            # Search results exist but no warning letter found
            return {"found": False, "searched": True}

    except Exception as e:
        logger.error(f"Search error for {company_name}: {e}")
        return {"found": False, "searched": False, "error": str(e)}


async def collect_warning_letters(state: WarningLetterState, limit: Optional[int] = None):
    """Main collection routine."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # Get companies needing search
    companies = get_companies_needing_search(events)
    logger.info(f"Companies needing search: {len(companies)}")

    # Filter already searched
    to_search = {c: evts for c, evts in companies.items() if not state.is_searched(c)}
    logger.info(f"After filtering already searched: {len(to_search)}")

    if limit:
        to_search = dict(list(to_search.items())[:limit])
        logger.info(f"Limited to {len(to_search)} companies")

    # Stats
    processed = 0
    found_count = 0
    none_count = 0
    error_count = 0

    for company_name, company_events in to_search.items():
        logger.info(f"\n[{processed+1}/{len(to_search)}] Searching: {company_name}")

        try:
            result = await search_warning_letter(company_name)

            if result.get("error"):
                state.mark_failed(company_name, result["error"])
                error_count += 1
            elif result.get("found"):
                wl_date = result.get("warning_letter_date")
                state.mark_found(company_name, result)
                state.mark_searched(company_name)
                found_count += 1

                # Update all events for this company
                for event in company_events:
                    event["warning_letter_date"] = create_status_field(
                        value=wl_date,
                        status="found",
                        source="websearch_fda",
                        confidence=result.get("confidence", 0.7),
                        evidence=result.get("evidence", []),
                    )
                    save_event(event)
                logger.info(f"  Found warning letter for {company_name}: {wl_date}")
            else:
                state.mark_confirmed_none(company_name)
                state.mark_searched(company_name)
                none_count += 1

                # Update events to confirmed_none
                for event in company_events:
                    event["warning_letter_date"] = create_status_field(
                        value=None,
                        status="confirmed_none",
                        source="websearch_fda",
                        confidence=0.7,
                        evidence=["No FDA warning letter found in search"],
                    )
                    save_event(event)
                logger.debug(f"  No warning letter found for {company_name}")

            processed += 1

            # Progress save every 10 companies
            if processed % 10 == 0:
                state.save()
                logger.info(f"  Progress: {processed}/{len(to_search)} (found={found_count}, none={none_count}, errors={error_count})")

            # Rate limiting
            await asyncio.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            logger.error(f"  Error processing {company_name}: {e}")
            state.mark_failed(company_name, str(e))
            error_count += 1

    state.save()

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("COLLECTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Companies processed: {processed}")
    logger.info(f"Warning letters found: {found_count}")
    logger.info(f"Confirmed none: {none_count}")
    logger.info(f"Errors: {error_count}")


def print_status():
    """Print collection status."""
    state = WarningLetterState()
    events = load_events()

    # Current coverage
    wl_status = Counter()
    for e in events:
        wl = e.get("warning_letter_date", {})
        status = wl.get("status", "not_searched") if isinstance(wl, dict) else "not_searched"
        wl_status[status] += 1

    print("\n" + "=" * 60)
    print("Warning Letter Collection Status")
    print("=" * 60)
    print(f"\nTotal events: {len(events)}")
    print(f"\nField coverage:")
    for status, count in sorted(wl_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count} ({100*count/len(events):.1f}%)")

    print(f"\nState file:")
    print(f"  Companies searched: {len(state.state['searched_companies'])}")
    print(f"  Companies with WL found: {len(state.state['found_companies'])}")
    print(f"  Companies confirmed none: {len(state.state['confirmed_none_companies'])}")
    print(f"  Failed searches: {len(state.state['failed_companies'])}")


async def main():
    parser = argparse.ArgumentParser(description="Warning Letter Collection")
    parser.add_argument("--limit", type=int, help="Limit number of companies")
    parser.add_argument("--status", action="store_true", help="Show status only")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    state = WarningLetterState()
    await collect_warning_letters(state, args.limit)
    print_status()


if __name__ == "__main__":
    asyncio.run(main())
