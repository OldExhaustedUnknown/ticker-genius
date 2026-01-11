"""
NCT Data Collection Script
============================
NCT ID로 임상시험 디자인 정보 수집

- is_single_arm: 단일군 여부
- trial_region: 시험 지역
- phase: 임상 단계
- enrollment: 등록 환자 수

Usage:
    python scripts/collect_nct.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
from datetime import datetime
from collections import Counter
from enum import Enum
from typing import Any

DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "collect_nct.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

CHECKPOINT_FILE = DATA_DIR / "nct_checkpoint.json"


def json_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Pydantic 모델 직렬화 (BaseModel 포함)
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception as e:
            logger.warning(f"model_dump failed for {type(obj)}: {e}")
    # Enum 직렬화
    if isinstance(obj, Enum):
        return obj.value
    # 그 외 객체
    logger.error(f"Cannot serialize type: {type(obj)}")
    raise TypeError(f"Type {type(obj)} not serializable")


def load_checkpoint() -> set:
    """처리 완료된 event_id 로드."""
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("processed_ids", []))
    return set()


def save_checkpoint(processed_ids: set):
    """체크포인트 저장."""
    data = {
        "processed_ids": list(processed_ids),
        "count": len(processed_ids),
        "last_updated": datetime.now().isoformat(),
    }
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


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


def get_nct_ids(event: dict) -> list[str]:
    """이벤트에서 NCT ID 추출."""
    # nct_ids (복수형) 먼저 확인
    nct_ids = event.get("nct_ids") or event.get("nct_id")
    if not nct_ids:
        return []

    # 리스트인 경우
    if isinstance(nct_ids, list):
        return [v for v in nct_ids if v and isinstance(v, str) and v.startswith("NCT")]

    # StatusField 형태인 경우
    if isinstance(nct_ids, dict):
        val = nct_ids.get("value")
        if not val:
            return []
        if isinstance(val, list):
            return [v for v in val if v and isinstance(v, str) and v.startswith("NCT")]
        if isinstance(val, str) and val.startswith("NCT"):
            return [val]
        return []

    # 직접 문자열인 경우
    if isinstance(nct_ids, str) and nct_ids.startswith("NCT"):
        return [nct_ids]

    return []


async def collect_all():
    """NCT ID가 있는 이벤트에 대해 임상 정보 수집."""
    from tickergenius.collection.nct_enricher import NCTEnricher

    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # NCT ID가 있는 이벤트만 필터링
    events_with_nct = [(e, get_nct_ids(e)) for e in events]
    events_with_nct = [(e, ncts) for e, ncts in events_with_nct if ncts]
    logger.info(f"Events with NCT ID: {len(events_with_nct)}")

    # 체크포인트 로드
    processed_ids = load_checkpoint()
    logger.info(f"Checkpoint: {len(processed_ids)} already processed")

    updated = 0
    single_arm_count = 0
    region_count = 0
    errors = 0
    skipped = 0

    async with NCTEnricher() as enricher:
        for i, (event, nct_ids) in enumerate(events_with_nct):
            event_id = event.get("event_id", "")

            # 체크포인트 확인
            if event_id in processed_ids:
                skipped += 1
                continue

            try:
                result = await enricher.enrich_event(nct_ids)

                # is_single_arm
                if "is_single_arm" in result:
                    is_single_arm = result["is_single_arm"]
                    if hasattr(is_single_arm, "model_dump"):
                        sa_dict = is_single_arm.model_dump(mode="json")
                        event["is_single_arm"] = sa_dict
                        if sa_dict.get("value") is True:
                            single_arm_count += 1
                    elif isinstance(is_single_arm, dict):
                        event["is_single_arm"] = is_single_arm
                        if is_single_arm.get("value") is True:
                            single_arm_count += 1

                # trial_region
                if "trial_region" in result:
                    trial_region = result["trial_region"]
                    if hasattr(trial_region, "model_dump"):
                        tr_dict = trial_region.model_dump(mode="json")
                        event["trial_region"] = tr_dict
                        if tr_dict.get("value"):
                            region_count += 1
                    elif isinstance(trial_region, dict):
                        event["trial_region"] = trial_region
                        if trial_region.get("value"):
                            region_count += 1

                # phase (기존 값 보완)
                if result.get("phase") and not event.get("phase", {}).get("value"):
                    event["phase"] = {
                        "value": result["phase"],
                        "status": "found",
                        "source": "clinicaltrials.gov",
                        "confidence": 0.9,
                        "tier": 2,
                    }

                # enrollment
                if result.get("enrollment"):
                    event["enrollment"] = {
                        "value": result["enrollment"],
                        "status": "found",
                        "source": "clinicaltrials.gov",
                        "confidence": 0.95,
                        "tier": 2,
                    }

                save_event(event)
                updated += 1
                processed_ids.add(event_id)

            except Exception as e:
                logger.error(f"Error for {event_id} ({nct_ids}): {e}")
                errors += 1
                processed_ids.add(event_id)  # 에러도 스킵하도록

            # Progress + 체크포인트
            if (i + 1) % 50 == 0:
                save_checkpoint(processed_ids)
                logger.info(
                    f"Progress: {i+1}/{len(events_with_nct)} | "
                    f"Updated: {updated} | SingleArm: {single_arm_count} | "
                    f"Region: {region_count} | Errors: {errors}"
                )

            # Rate limit (ClinicalTrials.gov는 관대하지만 예의상)
            await asyncio.sleep(0.5)

    # 최종 체크포인트
    save_checkpoint(processed_ids)

    logger.info(f"\nCollection Complete!")
    logger.info(f"Updated: {updated}")
    logger.info(f"Single arm trials: {single_arm_count}")
    logger.info(f"Region found: {region_count}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Skipped: {skipped}")

    print_status()


def print_status():
    events = load_events()

    print("\n" + "=" * 60)
    print("NCT DATA STATUS")
    print("=" * 60)

    # NCT ID 현황
    with_nct = 0
    for e in events:
        ncts = get_nct_ids(e)
        if ncts:
            with_nct += 1
    print(f"Events with NCT ID: {with_nct}/{len(events)}")

    # is_single_arm
    stats = Counter()
    true_count = 0
    for e in events:
        val = e.get("is_single_arm", {})
        if isinstance(val, dict):
            status = val.get("status", "not_searched")
            stats[status] += 1
            if val.get("value") == True:
                true_count += 1
        else:
            stats["not_searched"] += 1
    print(f"is_single_arm: {stats.get('found', 0)} found ({true_count} True)")

    # trial_region
    region_stats = Counter()
    for e in events:
        val = e.get("trial_region", {})
        if isinstance(val, dict) and val.get("value"):
            region_stats[val["value"]] += 1
    print(f"trial_region: {sum(region_stats.values())} found")
    for region, count in region_stats.most_common():
        print(f"  {region}: {count}")


if __name__ == "__main__":
    asyncio.run(collect_all())
