"""
FDA Designation Re-collection Script
=====================================
TDD 검증된 designation_collector를 사용하여 모든 이벤트의 designation 재수집.

실행:
    python scripts/recollect_designations.py
    python scripts/recollect_designations.py --limit 10  # 테스트
    python scripts/recollect_designations.py --resume     # 중단점부터 재개
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
import argparse
from datetime import datetime
from collections import Counter

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "recollect_designations.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/enriched")
CHECKPOINT_FILE = Path("data/temp/designation_checkpoint.json")
RATE_LIMIT = 2.0  # seconds between queries


def load_checkpoint() -> set:
    """체크포인트에서 처리된 event_id 로드."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("processed_ids", []))
    return set()


def save_checkpoint(processed_ids: set, stats: dict):
    """체크포인트 저장."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "processed_ids": list(processed_ids),
            "stats": stats,
            "last_updated": datetime.now().isoformat(),
        }, f, indent=2)


def load_events() -> list[dict]:
    """모든 이벤트 로드."""
    events = []
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                data["_file_path"] = str(f)
                data["_event_id"] = f.stem
                events.append(data)
        except Exception as e:
            logger.warning(f"Failed to load {f}: {e}")
    return events


def save_event(event: dict):
    """이벤트 저장."""
    file_path = event.pop("_file_path", None)
    event.pop("_event_id", None)

    if not file_path:
        return

    event["enriched_at"] = datetime.now().isoformat()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2, ensure_ascii=False)


async def collect_single_event(event: dict, stats: Counter) -> bool:
    """단일 이벤트에 대한 designation 수집."""
    from tickergenius.collection.designation_collector import (
        search_designation_websearch,
        create_designation_status,
        DESIGNATION_TYPES,
        FIELD_NAMES,
    )

    drug_name = event.get("drug_name", "")
    generic_name = event.get("generic_name", {})
    if isinstance(generic_name, dict):
        generic_name = generic_name.get("value", "")
    company_name = event.get("company_name", "")

    if not drug_name:
        stats["no_drug_name"] += 1
        return False

    updated = False

    for dtype in DESIGNATION_TYPES:
        field_name = FIELD_NAMES[dtype]

        try:
            result = await search_designation_websearch(
                drug_name=drug_name,
                generic_name=generic_name,
                company_name=company_name,
                designation_type=dtype,
                rate_limit=RATE_LIMIT,
            )

            event[field_name] = create_designation_status(
                value=result.get("value"),
                found=result.get("found", False),
                source=result.get("source", "websearch"),
                confidence=result.get("confidence", 0.0),
                evidence=result.get("evidence", []),
            )

            if result.get("value") == True:
                stats[f"{dtype}_true"] += 1
            elif result.get("found"):
                stats[f"{dtype}_found"] += 1
            else:
                stats[f"{dtype}_not_found"] += 1

            updated = True

        except Exception as e:
            logger.warning(f"Error collecting {dtype} for {drug_name}: {e}")
            stats[f"{dtype}_error"] += 1

    return updated


async def main(limit: int = None, resume: bool = False):
    """메인 수집 루프."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # 체크포인트 로드
    processed_ids = load_checkpoint() if resume else set()
    if processed_ids:
        logger.info(f"Resuming from checkpoint: {len(processed_ids)} already processed")

    # 필터링
    pending_events = [e for e in events if e.get("_event_id") not in processed_ids]
    if limit:
        pending_events = pending_events[:limit]

    logger.info(f"Will process {len(pending_events)} events")

    stats = Counter()

    for i, event in enumerate(pending_events):
        event_id = event.get("_event_id", "unknown")
        drug_name = event.get("drug_name", "Unknown")

        try:
            updated = await collect_single_event(event, stats)

            if updated:
                save_event(event)
                stats["saved"] += 1

            processed_ids.add(event_id)

            # 진행 상황 출력
            if (i + 1) % 10 == 0:
                logger.info(
                    f"Progress: {i + 1}/{len(pending_events)} | "
                    f"BTD: {stats.get('btd_true', 0)}, "
                    f"Orphan: {stats.get('orphan_true', 0)}"
                )
                # 체크포인트 저장
                save_checkpoint(processed_ids, dict(stats))

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            save_checkpoint(processed_ids, dict(stats))
            break
        except Exception as e:
            logger.error(f"Error processing {event_id} ({drug_name}): {e}")
            stats["error"] += 1

    # 최종 체크포인트 저장
    save_checkpoint(processed_ids, dict(stats))

    # 최종 통계
    print("\n" + "=" * 60)
    print("COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Total processed: {len(processed_ids)}")
    print(f"Saved: {stats.get('saved', 0)}")
    print(f"\nDesignation Results:")
    for dtype in ["btd", "orphan", "priority", "fast_track", "accelerated"]:
        true_count = stats.get(f"{dtype}_true", 0)
        found_count = stats.get(f"{dtype}_found", 0)
        not_found = stats.get(f"{dtype}_not_found", 0)
        print(f"  {dtype:15s}: {true_count:4d} True, {found_count:4d} Found, {not_found:4d} Not Found")

    if stats.get("error", 0) > 0:
        print(f"\nErrors: {stats['error']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-collect FDA designations")
    parser.add_argument("--limit", type=int, help="Limit number of events to process")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, resume=args.resume))
