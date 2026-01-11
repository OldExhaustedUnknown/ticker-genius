"""
AdCom Data Collection Script
============================
Advisory Committee 개최 여부 및 투표 비율 수집

Usage:
    python scripts/collect_adcom.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import json
import logging
import re
from datetime import datetime
from collections import Counter
from typing import Optional, Any

DATA_DIR = Path("data")
ENRICHED_DIR = DATA_DIR / "enriched"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 로그 설정: 콘솔 + 파일
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "collect_adcom.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

CHECKPOINT_FILE = DATA_DIR / "adcom_checkpoint.json"


def json_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Pydantic 모델 직렬화
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    # Enum 직렬화
    if hasattr(obj, "value") and hasattr(obj, "name"):
        return obj.value
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


def create_status_field(value: Any, status: str, source: str, confidence: float, evidence: list = None) -> dict:
    return {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 3,
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.utcnow().isoformat(),
    }


def parse_vote_ratio(text: str) -> Optional[float]:
    """투표 비율 파싱 (예: '12-1', '10 to 2', '85%')"""
    # Pattern: X-Y or X to Y
    match = re.search(r'(\d+)\s*[-to]+\s*(\d+)', text)
    if match:
        yes = int(match.group(1))
        no = int(match.group(2))
        if yes + no > 0:
            return yes / (yes + no)

    # Pattern: XX%
    match = re.search(r'(\d+)%', text)
    if match:
        return int(match.group(1)) / 100

    return None


def search_ddg(query: str, max_results: int = 10) -> list[dict]:
    """ddgs Yahoo 백엔드로 검색 (가장 빠르고 안정적)."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS(verify=False) as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results, backend='yahoo'))
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                })
        return results
    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")
        return []


async def search_adcom(drug_name: str, company_name: str) -> dict:
    """웹서치로 AdCom 정보 검색."""
    import asyncio

    try:
        # Search for advisory committee meeting
        query = f'"{drug_name}" FDA advisory committee meeting vote'
        results = await asyncio.to_thread(search_ddg, query, 10)

        adcom_held = False
        vote_ratio = None
        evidence = []

        for result in results:
            text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

            # Check for AdCom indicators
            adcom_keywords = [
                "advisory committee", "adcom", "fda panel",
                "advisory panel", "fda committee",
            ]

            if any(kw in text for kw in adcom_keywords):
                # Check if it's actually about this drug
                if drug_name.lower().split()[0] in text:
                    adcom_held = True
                    evidence.append(result.get("title", "")[:100])

                    # Try to extract vote ratio
                    if vote_ratio is None:
                        vote_ratio = parse_vote_ratio(text)
                        if vote_ratio:
                            evidence.append(f"Vote ratio extracted: {vote_ratio:.1%}")

        return {
            "found": True,
            "adcom_held": adcom_held,
            "vote_ratio": vote_ratio,
            "evidence": evidence[:3],
        }

    except Exception as e:
        logger.error(f"Search error for {drug_name}: {e}")
        return {"found": False, "error": str(e)}


async def collect_all():
    """모든 이벤트에 대해 AdCom 데이터 수집."""
    logger.info("Loading events...")
    events = load_events()
    logger.info(f"Loaded {len(events)} events")

    # 체크포인트 로드
    processed_ids = load_checkpoint()
    logger.info(f"Checkpoint: {len(processed_ids)} already processed")

    updated = 0
    adcom_found = 0
    vote_found = 0
    skipped = 0

    for i, event in enumerate(events):
        event_id = event.get("event_id", "")
        drug_name = event.get("drug_name", "")
        company_name = event.get("company_name", "")

        if not drug_name:
            continue

        # 체크포인트 확인 - 이미 처리된 경우 스킵
        if event_id in processed_ids:
            skipped += 1
            continue

        # Check if already has adcom data
        existing = event.get("adcom_scheduled")
        if existing is not None and isinstance(existing, dict) and existing.get("status") == "found":
            processed_ids.add(event_id)
            continue

        result = await search_adcom(drug_name, company_name)

        if result.get("found"):
            adcom_held = result.get("adcom_held", False)
            vote_ratio = result.get("vote_ratio")
            evidence = result.get("evidence", [])

            # Update adcom_scheduled
            event["adcom_scheduled"] = create_status_field(
                value=adcom_held,
                status="found" if adcom_held else "confirmed_none",
                source="websearch_adcom",
                confidence=0.75 if adcom_held else 0.7,
                evidence=evidence,
            )

            # Update adcom_vote_ratio
            if vote_ratio is not None:
                event["adcom_vote_ratio"] = create_status_field(
                    value=vote_ratio,
                    status="found",
                    source="websearch_adcom",
                    confidence=0.7,
                    evidence=evidence,
                )
                vote_found += 1
            else:
                event["adcom_vote_ratio"] = create_status_field(
                    value=None,
                    status="not_applicable" if not adcom_held else "not_found",
                    source="websearch_adcom",
                    confidence=0.6,
                )

            save_event(event)
            updated += 1
            processed_ids.add(event_id)

            if adcom_held:
                adcom_found += 1
        else:
            # Mark as searched
            event["adcom_scheduled"] = create_status_field(
                value=False,
                status="confirmed_none",
                source="websearch_adcom",
                confidence=0.6,
            )
            event["adcom_vote_ratio"] = create_status_field(
                value=None,
                status="not_applicable",
                source="websearch_adcom",
                confidence=0.6,
            )
            save_event(event)
            updated += 1
            processed_ids.add(event_id)

        # Progress + 체크포인트 저장
        if (i + 1) % 50 == 0:
            save_checkpoint(processed_ids)
            logger.info(f"Progress: {i+1}/{len(events)} | AdCom: {adcom_found} | Votes: {vote_found} | Skipped: {skipped}")

        # Rate limit
        await asyncio.sleep(1.5)

    # 최종 체크포인트 저장
    save_checkpoint(processed_ids)

    logger.info(f"\nCollection Complete!")
    logger.info(f"Updated: {updated}")
    logger.info(f"AdCom meetings found: {adcom_found}")
    logger.info(f"Vote ratios found: {vote_found}")
    logger.info(f"Skipped (from checkpoint): {skipped}")

    print_status()


def print_status():
    events = load_events()

    print("\n" + "=" * 60)
    print("ADCOM DATA STATUS")
    print("=" * 60)

    # adcom_scheduled
    stats = Counter()
    true_count = 0
    for e in events:
        val = e.get("adcom_scheduled", {})
        if isinstance(val, dict):
            status = val.get("status", "not_searched")
            stats[status] += 1
            if val.get("value") == True:
                true_count += 1
        else:
            stats["not_searched"] += 1

    print(f"adcom_scheduled: {stats.get('found', 0) + stats.get('confirmed_none', 0)} complete ({true_count} True)")
    print(f"  found: {stats.get('found', 0)}, confirmed_none: {stats.get('confirmed_none', 0)}, not_searched: {stats.get('not_searched', 0)}")

    # adcom_vote_ratio
    stats = Counter()
    with_vote = 0
    for e in events:
        val = e.get("adcom_vote_ratio", {})
        if isinstance(val, dict):
            status = val.get("status", "not_searched")
            stats[status] += 1
            if val.get("value") is not None:
                with_vote += 1
        else:
            stats["not_searched"] += 1

    print(f"adcom_vote_ratio: {with_vote} with votes")
    print(f"  found: {stats.get('found', 0)}, not_applicable: {stats.get('not_applicable', 0)}, not_searched: {stats.get('not_searched', 0)}")


if __name__ == "__main__":
    asyncio.run(collect_all())
