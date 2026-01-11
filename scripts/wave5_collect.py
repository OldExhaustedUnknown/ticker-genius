"""
Wave 5 Data Collection Script
==============================
523개 이벤트에 대해 12개 신규 필드 수집

실행:
    python scripts/wave5_collect.py --wave 5.1   # NCT fields only
    python scripts/wave5_collect.py --wave 5.2   # Biosimilar only
    python scripts/wave5_collect.py --wave 5.3   # WebSearch fields
    python scripts/wave5_collect.py --all        # All waves
    python scripts/wave5_collect.py --status     # Check progress

병렬 실행 (권장):
    # 터미널 1
    python scripts/wave5_collect.py --wave 5.1

    # 터미널 2 (동시에)
    python scripts/wave5_collect.py --wave 5.2
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any
import argparse


def json_serializer(obj: Any) -> str:
    """JSON 직렬화 헬퍼."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tickergenius.collection.nct_enricher import NCTEnricher
from tickergenius.collection.biosimilar_detector import BiosimilarDetector
from tickergenius.collection.ondemand_searcher import OnDemandSearcher
from tickergenius.schemas.base import StatusField
from tickergenius.schemas.enums import SearchStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/wave5_collection.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"
STATE_FILE = DATA_DIR / "wave5_state.json"

# Rate limits
NCT_RATE_LIMIT = 3  # requests per second
WEBSEARCH_RATE_LIMIT = 1  # requests per second


class Wave5State:
    """Wave 5 수집 상태 관리."""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """상태 파일 로드."""
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "created_at": datetime.now().isoformat(),
            "waves": {
                "5.1": {"status": "pending", "processed": [], "failed": []},
                "5.2": {"status": "pending", "processed": [], "failed": []},
                "5.3": {"status": "pending", "processed": [], "failed": []},
            },
            "field_stats": {},
        }

    def save(self):
        """상태 저장."""
        self.state["updated_at"] = datetime.now().isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def mark_processed(self, wave: str, event_id: str):
        """처리 완료 마킹."""
        if event_id not in self.state["waves"][wave]["processed"]:
            self.state["waves"][wave]["processed"].append(event_id)

    def mark_failed(self, wave: str, event_id: str, error: str):
        """실패 마킹."""
        self.state["waves"][wave]["failed"].append({
            "event_id": event_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

    def is_processed(self, wave: str, event_id: str) -> bool:
        """처리 여부 확인."""
        return event_id in self.state["waves"][wave]["processed"]

    def get_status(self) -> dict:
        """상태 요약."""
        total = len(list(ENRICHED_DIR.glob("*.json")))
        return {
            "total_events": total,
            "waves": {
                wave: {
                    "processed": len(data["processed"]),
                    "failed": len(data["failed"]),
                    "remaining": total - len(data["processed"]),
                }
                for wave, data in self.state["waves"].items()
            }
        }


def load_event(event_id: str) -> Optional[dict]:
    """이벤트 JSON 로드."""
    path = ENRICHED_DIR / f"{event_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_event(event_id: str, data: dict):
    """이벤트 JSON 저장."""
    path = ENRICHED_DIR / f"{event_id}.json"
    data["enriched_at"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=json_serializer)


def get_all_event_ids() -> list[str]:
    """모든 이벤트 ID 조회."""
    return [p.stem for p in ENRICHED_DIR.glob("*.json")]


async def collect_wave_5_1(state: Wave5State, limit: Optional[int] = None):
    """
    Wave 5.1: NCT 기반 필드 수집
    - is_single_arm
    - trial_region
    """
    logger.info("=== Wave 5.1: NCT Fields Collection ===")

    event_ids = get_all_event_ids()
    if limit:
        event_ids = event_ids[:limit]

    processed = 0
    skipped = 0
    errors = 0

    async with NCTEnricher() as enricher:
        for i, event_id in enumerate(event_ids):
            # 이미 처리된 경우 스킵
            if state.is_processed("5.1", event_id):
                skipped += 1
                continue

            try:
                event = load_event(event_id)
                if not event:
                    continue

                # NCT ID 확인
                nct_ids = event.get("nct_ids", [])
                if not nct_ids:
                    # NCT ID 없으면 NOT_APPLICABLE
                    event["is_single_arm"] = StatusField.not_applicable("no_nct_id").model_dump()
                    event["trial_region"] = StatusField.not_applicable("no_nct_id").model_dump()
                    save_event(event_id, event)
                    state.mark_processed("5.1", event_id)
                    processed += 1
                    continue

                # NCT API 호출
                result = await enricher.enrich_event(nct_ids)

                # 결과 저장
                if "is_single_arm" in result:
                    event["is_single_arm"] = result["is_single_arm"].model_dump()
                if "trial_region" in result:
                    event["trial_region"] = result["trial_region"].model_dump()

                save_event(event_id, event)
                state.mark_processed("5.1", event_id)
                processed += 1

                # Rate limiting
                await asyncio.sleep(1 / NCT_RATE_LIMIT)

                # Progress log
                if (i + 1) % 50 == 0:
                    logger.info(f"  Progress: {i+1}/{len(event_ids)} (processed={processed}, skipped={skipped})")
                    state.save()

            except Exception as e:
                logger.error(f"  Error {event_id}: {e}")
                state.mark_failed("5.1", event_id, str(e))
                errors += 1

    state.state["waves"]["5.1"]["status"] = "completed"
    state.save()

    logger.info(f"Wave 5.1 Complete: processed={processed}, skipped={skipped}, errors={errors}")


async def collect_wave_5_2(state: Wave5State, limit: Optional[int] = None):
    """
    Wave 5.2: 오프라인 바이오시밀러 판별
    - is_biosimilar
    """
    logger.info("=== Wave 5.2: Biosimilar Detection ===")

    event_ids = get_all_event_ids()
    if limit:
        event_ids = event_ids[:limit]

    detector = BiosimilarDetector()
    processed = 0
    skipped = 0

    for i, event_id in enumerate(event_ids):
        if state.is_processed("5.2", event_id):
            skipped += 1
            continue

        try:
            event = load_event(event_id)
            if not event:
                continue

            drug_name = event.get("drug_name", "")
            generic_name = event.get("generic_name", {}).get("value") if isinstance(event.get("generic_name"), dict) else None
            approval_type = event.get("approval_type", {}).get("value") if isinstance(event.get("approval_type"), dict) else None

            # 바이오시밀러 판별 (오프라인)
            result = await detector.detect(
                drug_name=drug_name,
                generic_name=generic_name,
                approval_type=approval_type,
            )

            event["is_biosimilar"] = result.model_dump()
            save_event(event_id, event)
            state.mark_processed("5.2", event_id)
            processed += 1

            # Progress log (no rate limiting needed)
            if (i + 1) % 100 == 0:
                logger.info(f"  Progress: {i+1}/{len(event_ids)} (processed={processed})")
                state.save()

        except Exception as e:
            logger.error(f"  Error {event_id}: {e}")
            state.mark_failed("5.2", event_id, str(e))

    state.state["waves"]["5.2"]["status"] = "completed"
    state.save()

    logger.info(f"Wave 5.2 Complete: processed={processed}, skipped={skipped}")


async def collect_wave_5_3(state: Wave5State, limit: Optional[int] = None):
    """
    Wave 5.3: 웹서치 기반 필드 수집
    - pai_passed, pai_date
    - clinical_hold_history

    Note: 기존에 status="found"인 데이터는 보존하고 덮어쓰지 않음
    """
    logger.info("=== Wave 5.3: WebSearch Fields Collection ===")

    event_ids = get_all_event_ids()
    if limit:
        event_ids = event_ids[:limit]

    searcher = OnDemandSearcher()
    processed = 0
    skipped = 0
    errors = 0
    preserved = 0  # Count of fields preserved (not overwritten)

    for i, event_id in enumerate(event_ids):
        if state.is_processed("5.3", event_id):
            skipped += 1
            continue

        try:
            event = load_event(event_id)
            if not event:
                continue

            drug_name = event.get("drug_name", "")
            company_name = event.get("company_name", "")

            if not drug_name or not company_name:
                # 필수 정보 없음
                event["clinical_hold_history"] = StatusField.not_applicable("missing_info").model_dump()
                save_event(event_id, event)
                state.mark_processed("5.3", event_id)
                processed += 1
                continue

            # Helper to check if existing field has valid data (status == "found")
            def has_valid_data(field_name: str) -> bool:
                existing = event.get(field_name)
                if isinstance(existing, dict):
                    return existing.get("status") == "found"
                return False

            # 웹서치 실행
            result = await searcher.search_all(drug_name, company_name)

            # 결과 저장 (기존에 status="found"인 데이터는 보존)
            if "pai_passed" in result:
                if has_valid_data("pai_passed"):
                    preserved += 1
                    logger.debug(f"  {event_id}: pai_passed preserved (already found)")
                else:
                    event["pai_passed"] = result["pai_passed"].model_dump()
            if "pai_date" in result:
                if has_valid_data("pai_date"):
                    preserved += 1
                    logger.debug(f"  {event_id}: pai_date preserved (already found)")
                else:
                    event["pai_date"] = result["pai_date"].model_dump()
            if "clinical_hold_history" in result:
                if has_valid_data("clinical_hold_history"):
                    preserved += 1
                    logger.debug(f"  {event_id}: clinical_hold_history preserved (already found)")
                else:
                    event["clinical_hold_history"] = result["clinical_hold_history"].model_dump()

            save_event(event_id, event)
            state.mark_processed("5.3", event_id)
            processed += 1

            # Rate limiting (웹서치는 보수적으로)
            await asyncio.sleep(1 / WEBSEARCH_RATE_LIMIT)

            # Progress log
            if (i + 1) % 20 == 0:
                logger.info(f"  Progress: {i+1}/{len(event_ids)} (processed={processed}, skipped={skipped}, preserved={preserved})")
                state.save()

        except Exception as e:
            logger.error(f"  Error {event_id}: {e}")
            state.mark_failed("5.3", event_id, str(e))
            errors += 1

    state.state["waves"]["5.3"]["status"] = "completed"
    state.save()

    logger.info(f"Wave 5.3 Complete: processed={processed}, skipped={skipped}, errors={errors}, preserved={preserved}")


def print_status(state: Wave5State):
    """상태 출력."""
    status = state.get_status()
    print("\n" + "=" * 50)
    print("Wave 5 Collection Status")
    print("=" * 50)
    print(f"Total Events: {status['total_events']}")
    print()
    for wave, data in status["waves"].items():
        pct = (data["processed"] / status["total_events"] * 100) if status["total_events"] > 0 else 0
        print(f"Wave {wave}:")
        print(f"  Processed: {data['processed']} ({pct:.1f}%)")
        print(f"  Failed:    {data['failed']}")
        print(f"  Remaining: {data['remaining']}")
        print()


async def main():
    parser = argparse.ArgumentParser(description="Wave 5 Data Collection")
    parser.add_argument("--wave", choices=["5.1", "5.2", "5.3"], help="Run specific wave")
    parser.add_argument("--all", action="store_true", help="Run all waves sequentially")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--limit", type=int, help="Limit number of events (for testing)")
    args = parser.parse_args()

    state = Wave5State()

    if args.status:
        print_status(state)
        return

    if args.wave == "5.1":
        await collect_wave_5_1(state, args.limit)
    elif args.wave == "5.2":
        await collect_wave_5_2(state, args.limit)
    elif args.wave == "5.3":
        await collect_wave_5_3(state, args.limit)
    elif args.all:
        # Wave 5.1과 5.2는 병렬 실행 가능
        await asyncio.gather(
            collect_wave_5_1(state, args.limit),
            collect_wave_5_2(state, args.limit),
        )
        # Wave 5.3은 순차 실행
        await collect_wave_5_3(state, args.limit)
    else:
        print("Usage: python scripts/wave5_collect.py --wave 5.1|5.2|5.3 | --all | --status")
        print_status(state)


if __name__ == "__main__":
    asyncio.run(main())
