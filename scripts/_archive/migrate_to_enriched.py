#!/usr/bin/env python
"""
기존 데이터 마이그레이션
=======================
외부 API 호출 없이 기존 CollectedCase → EnrichedPDUFAEvent 변환.

사용법:
    python scripts/migrate_to_enriched.py
    python scripts/migrate_to_enriched.py --limit 10
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tickergenius.collection.enrichment import EnrichedPDUFAEvent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_DIR = DATA_DIR / "collected" / "processed"
OUTPUT_DIR = DATA_DIR / "enriched"


def load_cases(input_dir: Path, limit: int = None) -> list[dict]:
    """수집된 케이스 로드."""
    cases = []
    files = sorted(input_dir.glob("*.json"))

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                case = json.load(fp)
                case["_source_file"] = str(f)
                cases.append(case)
        except Exception as e:
            logger.warning(f"Failed to load {f}: {e}")

    if limit:
        cases = cases[:limit]

    logger.info(f"Loaded {len(cases)} cases from {input_dir}")
    return cases


def migrate_case(case: dict) -> EnrichedPDUFAEvent:
    """단일 케이스 마이그레이션."""
    event = EnrichedPDUFAEvent.from_collected_case(case)
    event.calculate_quality_score()
    event.enriched_at = datetime.now().isoformat()
    return event


def save_event(event: EnrichedPDUFAEvent, output_dir: Path) -> Path:
    """Enriched 이벤트 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{event.ticker}_{event.event_id}.json"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(event.to_dict(), f, indent=2, ensure_ascii=False)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Migrate collected cases to enriched format")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases")
    parser.add_argument("--input-dir", type=str, default=None, help="Input directory")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")

    args = parser.parse_args()

    input_dir = Path(args.input_dir) if args.input_dir else INPUT_DIR
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    logger.info("=" * 60)
    logger.info("Migrate CollectedCase → EnrichedPDUFAEvent")
    logger.info("=" * 60)
    logger.info(f"Input:  {input_dir}")
    logger.info(f"Output: {output_dir}")

    cases = load_cases(input_dir, limit=args.limit)
    if not cases:
        logger.error("No cases found!")
        sys.exit(1)

    stats = {
        "total": len(cases),
        "migrated": 0,
        "failed": 0,
        "with_btd": 0,
        "with_priority_review": 0,
        "with_crl": 0,
    }

    for i, case in enumerate(cases):
        try:
            event = migrate_case(case)
            output_path = save_event(event, output_dir)

            stats["migrated"] += 1

            # 통계 수집
            if event.btd.status.value == "found" and event.btd.value:
                stats["with_btd"] += 1
            if event.priority_review.status.value == "found" and event.priority_review.value:
                stats["with_priority_review"] += 1
            if event.has_prior_crl.status.value == "found" and event.has_prior_crl.value:
                stats["with_crl"] += 1

            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(cases)}")

        except Exception as e:
            logger.error(f"Failed to migrate {case.get('ticker')}/{case.get('drug_name')}: {e}")
            stats["failed"] += 1

    logger.info("=" * 60)
    logger.info("Migration Results:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)

    # 미수집 필드가 있는 케이스 요약
    logger.info("\nMissing field summary (needs WebSearch enrichment):")
    logger.info("  All events need: approval_type, indication, primary_endpoint_met, p_value, adcom_held, pai_passed")


if __name__ == "__main__":
    main()
