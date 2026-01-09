"""
Full Data Enrichment Runner
============================
Step B2: 이벤트 데이터 100% 보강

사용법:
    python run_enrichment.py             # 전체 실행
    python run_enrichment.py --limit 50  # 50개만 테스트
    python run_enrichment.py --analyze   # 분석만
"""
import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Reduce HTTP noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from tickergenius.collection.data_enricher import DataEnricher
from tickergenius.collection.event_store import EventStore


def main():
    parser = argparse.ArgumentParser(description="Data Enrichment Runner")
    parser.add_argument("--limit", type=int, help="Limit number of events to process")
    parser.add_argument("--skip", type=int, default=0, help="Skip first N events")
    parser.add_argument("--analyze", action="store_true", help="Only analyze, don't enrich")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    args = parser.parse_args()

    print("=" * 60)
    print("Data Enrichment Runner - Step B2")
    print("=" * 60)

    # Initialize
    store = EventStore(base_dir=Path("data/events"))
    enricher = DataEnricher(store=store, dry_run=args.dry_run)

    # Current analysis
    print("\n--- Current Data Quality ---")
    analysis = enricher.analyze()
    print(f"Total events: {analysis['total']}")
    print("\nField completion rates:")
    for field, counts in sorted(analysis["fields"].items()):
        rate = counts["rate"] * 100
        filled = counts["filled"]
        bar = "#" * int(rate / 10) + "-" * (10 - int(rate / 10))
        print(f"  {field:<25} [{bar}] {rate:5.1f}% ({filled}/{counts['filled']+counts['null']})")

    if args.analyze:
        return

    # Run enrichment
    print("\n--- Running Enrichment ---")
    if args.limit:
        print(f"Processing up to {args.limit} events (skip={args.skip})")
    else:
        print(f"Processing all events (skip={args.skip})")

    if args.dry_run:
        print("DRY RUN - no changes will be saved")

    def progress_callback(current, total):
        pct = current / total * 100
        print(f"\r  Progress: {current}/{total} ({pct:.0f}%)       ", end="", flush=True)

    stats = enricher.enrich(
        limit=args.limit,
        skip=args.skip,
        progress_callback=progress_callback,
    )

    print("\n\n--- Enrichment Results ---")
    print(f"Events processed: {stats.events_processed}")
    print(f"Events updated: {stats.events_updated}")
    print(f"Fields updated: {stats.fields_updated}")
    print(f"API calls: {stats.api_calls}")
    print(f"API errors: {stats.api_errors}")
    print(f"\nBreakdown:")
    print(f"  NCT IDs found: {stats.nct_id_found}")
    print(f"  Phases found: {stats.phase_found}")
    print(f"  Endpoints found: {stats.endpoint_found}")
    print(f"  AdCom found: {stats.adcom_found}")
    print(f"\nDuration: {stats.duration_seconds:.1f}s")

    # Show fallback status
    if enricher._ct_api_failed:
        print("\nNote: ClinicalTrials.gov API blocked, using PubMed fallback")
    else:
        print("\nNote: ClinicalTrials.gov API available")

    # Show errors if any
    if stats.errors:
        print(f"\n--- Errors ({len(stats.errors)}) ---")
        for e in stats.errors[:10]:
            print(f"  - {e}")
        if len(stats.errors) > 10:
            print(f"  ... and {len(stats.errors) - 10} more")

    # Final analysis
    print("\n--- Final Data Quality ---")
    final_analysis = enricher.analyze()
    print("\nField completion rates (after):")
    for field, counts in sorted(final_analysis["fields"].items()):
        rate = counts["rate"] * 100
        old_rate = analysis["fields"][field]["rate"] * 100
        change = rate - old_rate
        bar = "#" * int(rate / 10) + "-" * (10 - int(rate / 10))
        change_str = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"
        print(f"  {field:<25} [{bar}] {rate:5.1f}% ({change_str})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
