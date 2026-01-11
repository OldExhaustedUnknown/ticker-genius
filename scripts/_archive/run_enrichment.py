#!/usr/bin/env python
"""
Enrichment 실행 스크립트
=======================
수집된 PDUFA 이벤트 데이터를 enrichment 파이프라인으로 처리.

사용법:
    python scripts/run_enrichment.py
    python scripts/run_enrichment.py --limit 10
    python scripts/run_enrichment.py --from-checkpoint
    python scripts/run_enrichment.py --dry-run
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# src를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tickergenius.collection.enrichment import (
    EnrichedPDUFAEvent,
    EnrichmentOrchestrator,
)
from tickergenius.collection.api_clients import SECEdgarClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# === 경로 설정 ===
DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_DIR = DATA_DIR / "collected" / "processed"
OUTPUT_DIR = DATA_DIR / "enriched"
CHECKPOINT_FILE = DATA_DIR / "enrichment_checkpoint.json"
STATE_FILE = DATA_DIR / "enrichment_state.json"


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


def load_checkpoint(checkpoint_file: Path) -> set[str]:
    """체크포인트에서 완료된 케이스 ID 로드."""
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
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_enriched_event(event: EnrichedPDUFAEvent, output_dir: Path) -> Path:
    """Enriched 이벤트 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{event.ticker}_{event.event_id}.json"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(event.to_dict(), f, indent=2, ensure_ascii=False)

    return output_path


def update_state(
    state_file: Path,
    current: int,
    total: int,
    stats: dict,
) -> None:
    """상태 파일 업데이트."""
    state = {
        "progress": {"current": current, "total": total},
        "stats": stats,
        "last_updated": datetime.now().isoformat(),
    }
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def run_enrichment(
    cases: list[dict],
    output_dir: Path,
    checkpoint_file: Path,
    state_file: Path,
    dry_run: bool = False,
    from_checkpoint: bool = False,
) -> dict:
    """Enrichment 실행."""
    # 체크포인트 로드
    completed_ids = load_checkpoint(checkpoint_file) if from_checkpoint else set()
    logger.info(f"Checkpoint: {len(completed_ids)} already completed")

    # 미완료 케이스만 필터링
    remaining = [c for c in cases if c.get("case_id") not in completed_ids]
    logger.info(f"Remaining: {len(remaining)} cases to process")

    if not remaining:
        logger.info("All cases already completed!")
        return {"total": len(cases), "processed": 0, "skipped": len(cases)}

    # Dry run 모드
    if dry_run:
        logger.info("DRY RUN mode - no actual processing")
        for c in remaining[:5]:
            logger.info(f"  Would process: {c.get('ticker')}/{c.get('drug_name')}")
        return {"total": len(cases), "dry_run": True}

    # Orchestrator 생성
    try:
        sec_client = SECEdgarClient()
    except Exception as e:
        logger.warning(f"SEC client init failed: {e}")
        sec_client = None

    # 웹 검색 클라이언트 (선택적)
    web_client = None
    try:
        from tickergenius.collection.web_search import WebSearchClient
        web_client = WebSearchClient()
    except Exception as e:
        logger.warning(f"Web search client init failed: {e}")

    orchestrator = EnrichmentOrchestrator(
        sec_client=sec_client,
        web_client=web_client,
    )

    # 통계
    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "approval_type_found": 0,
        "endpoint_found": 0,
        "adcom_found": 0,
    }

    total = len(remaining)

    for i, case in enumerate(remaining):
        case_id = case.get("case_id")
        ticker = case.get("ticker", "?")
        drug = case.get("drug_name", "?")

        try:
            logger.info(f"[{i+1}/{total}] Processing: {ticker}/{drug}")

            # Enrichment 실행
            event = orchestrator.enrich_event(case)

            # 저장
            output_path = save_enriched_event(event, output_dir)

            # 통계 업데이트
            stats["processed"] += 1
            stats["success"] += 1

            if event.approval_type.status.value == "found":
                stats["approval_type_found"] += 1
            if event.primary_endpoint_met.status.value == "found":
                stats["endpoint_found"] += 1
            if event.adcom_held.status.value == "found":
                stats["adcom_found"] += 1

            # 체크포인트 업데이트
            completed_ids.add(case_id)
            if (i + 1) % 10 == 0:  # 10개마다 저장
                save_checkpoint(checkpoint_file, completed_ids)

            # 상태 업데이트
            update_state(state_file, i + 1, total, stats)

            logger.info(
                f"  → Saved: {output_path.name} "
                f"(quality: {event.data_quality_score:.2f})"
            )

        except Exception as e:
            logger.error(f"  → FAILED: {e}")
            stats["failed"] += 1
            continue

    # 최종 체크포인트 저장
    save_checkpoint(checkpoint_file, completed_ids)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Run enrichment pipeline")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of cases to process"
    )
    parser.add_argument(
        "--from-checkpoint", action="store_true",
        help="Resume from checkpoint"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Dry run mode (no actual processing)"
    )
    parser.add_argument(
        "--input-dir", type=str, default=None,
        help="Input directory (default: data/collected/processed)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: data/enriched)"
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir) if args.input_dir else INPUT_DIR
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    logger.info("=" * 60)
    logger.info("PDUFA Event Enrichment Pipeline")
    logger.info("=" * 60)
    logger.info(f"Input:  {input_dir}")
    logger.info(f"Output: {output_dir}")

    # 케이스 로드
    cases = load_cases(input_dir, limit=args.limit)

    if not cases:
        logger.error("No cases found!")
        sys.exit(1)

    # Enrichment 실행
    stats = run_enrichment(
        cases=cases,
        output_dir=output_dir,
        checkpoint_file=CHECKPOINT_FILE,
        state_file=STATE_FILE,
        dry_run=args.dry_run,
        from_checkpoint=args.from_checkpoint,
    )

    # 결과 출력
    logger.info("=" * 60)
    logger.info("Results:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
