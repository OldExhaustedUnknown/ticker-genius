#!/usr/bin/env python
"""
DDG 기반 Enrichment 실행
========================
DuckDuckGo 검색으로 523개 PDUFA 이벤트 임상 데이터 보완.

사용법:
    python scripts/enrich_with_ddg.py
    python scripts/enrich_with_ddg.py --limit 10
    python scripts/enrich_with_ddg.py --from-checkpoint
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tickergenius.collection.ddg_searcher import enrich_with_ddg
from tickergenius.collection.enrichment.models import SearchFieldMeta, SearchStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
ENRICHED_DIR = DATA_DIR / "enriched"
CHECKPOINT_FILE = DATA_DIR / "ddg_enrichment_checkpoint.json"


def load_enriched_events(enriched_dir: Path) -> list[dict]:
    """Enriched 이벤트 로드."""
    events = []
    for f in sorted(enriched_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                event = json.load(fp)
                event["_file_path"] = str(f)
                events.append(event)
        except Exception as e:
            logger.warning(f"Failed to load {f}: {e}")
    return events


def load_checkpoint(checkpoint_file: Path) -> set[str]:
    """체크포인트 로드."""
    if not checkpoint_file.exists():
        return set()
    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("completed_ids", []))
    except Exception:
        return set()


def save_checkpoint(checkpoint_file: Path, completed_ids: set[str]) -> None:
    """체크포인트 저장."""
    data = {
        "completed_ids": list(completed_ids),
        "last_updated": datetime.now().isoformat(),
    }
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def needs_enrichment(event: dict) -> bool:
    """Enrichment가 필요한지 확인."""
    # primary_endpoint_met이 not_searched인 경우
    pem = event.get("primary_endpoint_met", {})
    if pem.get("status") in ("not_searched", "not_found"):
        return True
    return False


def update_event(event: dict, ddg_result: dict) -> bool:
    """DDG 결과로 이벤트 업데이트."""
    updated = False

    # Primary endpoint
    if ddg_result.get("primary_endpoint_met") is not None:
        event["primary_endpoint_met"] = {
            "status": "found",
            "value": ddg_result["primary_endpoint_met"],
            "source": "ddg_search",
            "confidence": ddg_result.get("confidence", 0.7),
            "evidence": ddg_result.get("evidence", []),
            "searched_sources": ["ddg_search"],
            "last_searched": datetime.now().isoformat(),
            "error": None,
        }
        updated = True

    # P-value
    if ddg_result.get("p_value"):
        event["p_value"] = {
            "status": "found",
            "value": ddg_result["p_value"],
            "source": "ddg_search",
            "confidence": 0.8,
            "evidence": [],
            "searched_sources": ["ddg_search"],
            "last_searched": datetime.now().isoformat(),
            "error": None,
        }
        # 수치 변환 시도
        try:
            event["p_value_numeric"] = float(ddg_result["p_value"])
        except ValueError:
            pass
        updated = True

    # AdCom
    if ddg_result.get("adcom_held") is not None:
        event["adcom_held"] = {
            "status": "found",
            "value": ddg_result["adcom_held"],
            "source": "ddg_search",
            "confidence": 0.8,
            "evidence": [],
            "searched_sources": ["ddg_search"],
            "last_searched": datetime.now().isoformat(),
            "error": None,
        }
        if ddg_result.get("adcom_vote"):
            event["adcom_vote_favorable"] = ddg_result["adcom_vote"]
        updated = True

    # Approval type
    if ddg_result.get("approval_type"):
        event["approval_type"] = {
            "status": "found",
            "value": ddg_result["approval_type"],
            "source": "ddg_search",
            "confidence": ddg_result.get("confidence", 0.7),
            "evidence": [],
            "searched_sources": ["ddg_search"],
            "last_searched": datetime.now().isoformat(),
            "error": None,
        }
        updated = True

    if updated:
        event["enriched_at"] = datetime.now().isoformat()

    return updated


def save_event(event: dict, file_path: str) -> None:
    """이벤트 저장."""
    with open(file_path, "w", encoding="utf-8") as f:
        # _file_path 필드 제거
        save_event = {k: v for k, v in event.items() if not k.startswith("_")}
        json.dump(save_event, f, indent=2, ensure_ascii=False)


def run_enrichment(
    events: list[dict],
    checkpoint_file: Path,
    from_checkpoint: bool = False,
    limit: int = None,
) -> dict:
    """DDG Enrichment 실행."""
    # 체크포인트 로드
    completed_ids = load_checkpoint(checkpoint_file) if from_checkpoint else set()
    logger.info(f"Checkpoint: {len(completed_ids)} already completed")

    # 필터링
    remaining = [
        e for e in events
        if e.get("event_id") not in completed_ids and needs_enrichment(e)
    ]

    if limit:
        remaining = remaining[:limit]

    logger.info(f"Remaining: {len(remaining)} events to enrich")

    if not remaining:
        return {"total": len(events), "processed": 0, "skipped": len(events)}

    stats = {
        "processed": 0,
        "updated": 0,
        "failed": 0,
        "endpoint_found": 0,
        "pvalue_found": 0,
        "adcom_found": 0,
        "approval_type_found": 0,
    }

    for i, event in enumerate(remaining):
        event_id = event.get("event_id")
        ticker = event.get("ticker", "?")
        drug = event.get("drug_name", "?")

        try:
            logger.info(f"[{i+1}/{len(remaining)}] Searching: {ticker}/{drug[:30]}")

            # DDG 검색
            ddg_result = enrich_with_ddg(ticker, drug)

            # 업데이트
            if update_event(event, ddg_result):
                save_event(event, event["_file_path"])
                stats["updated"] += 1

                if ddg_result.get("primary_endpoint_met") is not None:
                    stats["endpoint_found"] += 1
                if ddg_result.get("p_value"):
                    stats["pvalue_found"] += 1
                if ddg_result.get("adcom_held"):
                    stats["adcom_found"] += 1
                if ddg_result.get("approval_type"):
                    stats["approval_type_found"] += 1

                logger.info(
                    f"  → endpoint={ddg_result.get('primary_endpoint_met')}, "
                    f"p={ddg_result.get('p_value')}, "
                    f"type={ddg_result.get('approval_type')}"
                )
            else:
                logger.info(f"  → No data found")

            stats["processed"] += 1

            # 체크포인트 업데이트
            completed_ids.add(event_id)
            if (i + 1) % 10 == 0:
                save_checkpoint(checkpoint_file, completed_ids)

        except Exception as e:
            logger.error(f"  → FAILED: {e}")
            stats["failed"] += 1

    # 최종 체크포인트 저장
    save_checkpoint(checkpoint_file, completed_ids)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Enrich PDUFA events with DDG search")
    parser.add_argument("--limit", type=int, default=None, help="Limit events")
    parser.add_argument("--from-checkpoint", action="store_true", help="Resume")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DDG-based Clinical Data Enrichment")
    logger.info("=" * 60)

    events = load_enriched_events(ENRICHED_DIR)
    logger.info(f"Loaded {len(events)} enriched events")

    stats = run_enrichment(
        events=events,
        checkpoint_file=CHECKPOINT_FILE,
        from_checkpoint=args.from_checkpoint,
        limit=args.limit,
    )

    logger.info("=" * 60)
    logger.info("Results:")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
