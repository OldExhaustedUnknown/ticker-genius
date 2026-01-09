#!/usr/bin/env python3
"""
데이터 수집 재개 스크립트
=========================

체크포인트 기반으로 데이터 수집을 재개하는 CLI 스크립트입니다.

사용법:
    python scripts/resume_enrichment.py --from-checkpoint
    python scripts/resume_enrichment.py --wave 2
    python scripts/resume_enrichment.py --field phase --retry-failed
    python scripts/resume_enrichment.py --status

참조: docs/DATA_COLLECTION_DESIGN.md
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tickergenius.collection.checkpoint import (
    CheckpointManager,
    CheckpointState,
    FieldProgress,
)
from tickergenius.collection.fallback_chain import (
    FallbackChainManager,
    create_fallback_chain_manager,
    ChainExecutionResult,
)
from tickergenius.collection.models import SearchStatus

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# 이벤트 데이터 로딩
# =============================================================================

DATA_FILE_PATHS = [
    # 우선순위 순서
    PROJECT_ROOT / "data" / "pdufa_final_enriched.json",
    PROJECT_ROOT / "data" / "processed" / "pdufa_enriched.json",
    PROJECT_ROOT / "data" / "collected" / "processed",  # 폴더 (여러 JSON 파일)
]


def load_events() -> list[dict]:
    """
    이벤트 데이터 로드.

    여러 경로를 시도하여 이벤트 데이터를 로드합니다:
    1. data/pdufa_final_enriched.json
    2. data/processed/pdufa_enriched.json
    3. data/collected/processed/ (개별 JSON 파일들)

    Returns:
        이벤트 딕셔너리 리스트
    """
    events = []

    for path in DATA_FILE_PATHS:
        if not path.exists():
            logger.debug(f"Path not found: {path}")
            continue

        # 단일 JSON 파일
        if path.is_file() and path.suffix == ".json":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    events = data
                    logger.info(f"Loaded {len(events)} events from {path}")
                    return events
                elif isinstance(data, dict):
                    # 단일 이벤트 또는 래핑된 데이터
                    if "events" in data:
                        events = data["events"]
                    else:
                        events = [data]
                    logger.info(f"Loaded {len(events)} events from {path}")
                    return events

            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}")
                continue

        # 폴더 (여러 JSON 파일)
        elif path.is_dir():
            try:
                json_files = list(path.glob("*.json"))

                if not json_files:
                    logger.debug(f"No JSON files in {path}")
                    continue

                for json_file in sorted(json_files):
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            event = json.load(f)

                        # 필수 필드 확인
                        if "ticker" in event or "case_id" in event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to load {json_file}: {e}")

                if events:
                    logger.info(f"Loaded {len(events)} events from {path}")
                    return events

            except Exception as e:
                logger.warning(f"Failed to scan directory {path}: {e}")
                continue

    logger.warning("No event data found in any of the expected paths")
    return events


def get_event_id(event: dict) -> str:
    """이벤트 ID 추출."""
    return event.get("case_id") or event.get("event_id") or f"{event.get('ticker', 'UNKNOWN')}_{hash(json.dumps(event, sort_keys=True)) % 10**8:08x}"


def get_event_ticker(event: dict) -> str:
    """이벤트 티커 추출."""
    return event.get("ticker", "UNKNOWN")


def get_event_drug_name(event: dict) -> str:
    """이벤트 약물명 추출."""
    return event.get("drug_name") or event.get("drug", "")


# =============================================================================
# 상태 출력
# =============================================================================

def show_status(checkpoint: CheckpointManager) -> None:
    """
    현재 상태 출력.

    체크포인트 정보를 상세히 출력합니다.

    Args:
        checkpoint: 체크포인트 매니저
    """
    if checkpoint.state is None:
        print("체크포인트가 로드되지 않았습니다.")
        return

    state = checkpoint.state

    # 기본 리포트 출력
    checkpoint.print_report()

    # 추가 정보 출력
    print()
    print("--- 추가 정보 ---")
    print()

    # 웨이브 상태
    print("웨이브 상태:")
    for wave_id, wave in sorted(state.waves.items()):
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[~]",
            "completed": "[O]",
            "failed": "[X]",
        }.get(wave.status, "[?]")

        duration = ""
        if wave.started_at and wave.completed_at:
            delta = wave.completed_at - wave.started_at
            duration = f" ({delta.total_seconds():.1f}s)"

        print(f"  {status_icon} Wave {wave_id}: {wave.name}{duration}")

    print()

    # 실패한 이벤트
    failed = checkpoint.get_retry_queue()
    if failed:
        print(f"재시도 대기 중인 실패 이벤트: {len(failed)}개")
        for fe in failed[:5]:
            print(f"  - {fe.event_id} ({fe.field_name}): {fe.error_message[:50]}...")
        if len(failed) > 5:
            print(f"  ... 외 {len(failed) - 5}개")
        print()

    # 재개 명령
    if state.resume_command:
        print(f"재개 명령: {state.resume_command}")
    else:
        print("재개 명령: python scripts/resume_enrichment.py --from-checkpoint")


# =============================================================================
# Wave 실행
# =============================================================================

async def run_wave_1(
    checkpoint: CheckpointManager,
    dry_run: bool = False,
) -> None:
    """
    Wave 1: 인프라 검증.

    체크포인트, 예외 처리, 폴백 체인 인프라가 올바르게 설정되었는지 확인합니다.
    이 단계는 이미 checkpoint.py, search_exceptions.py, fallback_chain.py가
    구현되어 있으므로 기본적으로 완료 처리됩니다.

    Args:
        checkpoint: 체크포인트 매니저
        dry_run: 실제 실행 없이 계획만 출력
    """
    print("=" * 60)
    print("Wave 1: 인프라 검증")
    print("=" * 60)

    if dry_run:
        print("[DRY-RUN] 실제 실행하지 않음")
        print("  - checkpoint.py 검증")
        print("  - search_exceptions.py 검증")
        print("  - fallback_chain.py 검증")
        return

    checkpoint.start_wave(1, "인프라 검증", 4)
    checkpoint.start_task("1.1_checkpoint_validation")

    # 인프라 모듈 검증
    validation_results = []

    # 1. checkpoint.py
    try:
        from tickergenius.collection.checkpoint import CheckpointManager, CheckpointState
        validation_results.append(("checkpoint.py", True, "OK"))
    except Exception as e:
        validation_results.append(("checkpoint.py", False, str(e)))

    # 2. search_exceptions.py
    try:
        from tickergenius.collection.search_exceptions import (
            SearchException, RateLimitException, TimeoutException
        )
        validation_results.append(("search_exceptions.py", True, "OK"))
    except Exception as e:
        validation_results.append(("search_exceptions.py", False, str(e)))

    # 3. fallback_chain.py
    try:
        from tickergenius.collection.fallback_chain import (
            FallbackChainManager, FALLBACK_CHAINS
        )
        validation_results.append(("fallback_chain.py", True, "OK"))
    except Exception as e:
        validation_results.append(("fallback_chain.py", False, str(e)))

    # 4. models.py (SearchStatus)
    try:
        from tickergenius.collection.models import SearchStatus
        validation_results.append(("models.py (SearchStatus)", True, "OK"))
    except Exception as e:
        validation_results.append(("models.py (SearchStatus)", False, str(e)))

    # 결과 출력
    print()
    print("인프라 검증 결과:")
    all_passed = True
    for name, passed, message in validation_results:
        icon = "[O]" if passed else "[X]"
        print(f"  {icon} {name}: {message}")
        if not passed:
            all_passed = False

    if all_passed:
        checkpoint.complete_wave(1)
        print()
        print("Wave 1 완료!")
    else:
        checkpoint.fail("인프라 검증 실패")
        print()
        print("Wave 1 실패 - 위의 에러를 수정하세요")

    checkpoint.save()


async def run_wave_2(
    checkpoint: CheckpointManager,
    events: list[dict],
    field: Optional[str] = None,
    retry_failed: bool = False,
    max_concurrent: int = 10,
    dry_run: bool = False,
) -> None:
    """
    Wave 2: 필드별 수집.

    FallbackChainManager를 사용하여 각 이벤트의 필드 데이터를 수집합니다.

    Args:
        checkpoint: 체크포인트 매니저
        events: 이벤트 리스트
        field: 특정 필드만 처리 (None이면 모든 필드)
        retry_failed: 실패한 이벤트만 재시도
        max_concurrent: 최대 동시 처리 수
        dry_run: 실제 실행 없이 계획만 출력
    """
    # 처리할 필드 결정
    all_fields = ["phase", "primary_endpoint_met", "adcom", "pai_passed"]
    fields = [field] if field else all_fields

    print("=" * 60)
    print(f"Wave 2: 필드별 수집")
    print("=" * 60)
    print(f"처리 필드: {', '.join(fields)}")
    print(f"대상 이벤트: {len(events)}개")
    print(f"최대 동시 처리: {max_concurrent}")
    print(f"실패 재시도 모드: {retry_failed}")
    print()

    if dry_run:
        print("[DRY-RUN] 실제 실행하지 않음")
        print()
        print("실행 계획:")
        for field_name in fields:
            print(f"  - {field_name}: {len(events)}개 이벤트 처리 예정")
        return

    # 체크포인트 시작
    total_tasks = len(events) * len(fields)
    checkpoint.start_wave(2, "필드별 수집", total_tasks)

    # 재시도 모드: 실패한 이벤트만 처리
    target_events = events
    if retry_failed:
        retry_queue = checkpoint.get_retry_queue()
        retry_event_ids = {fe.event_id for fe in retry_queue}
        target_events = [e for e in events if get_event_id(e) in retry_event_ids]
        print(f"재시도 대상: {len(target_events)}개 이벤트")

    if not target_events:
        print("처리할 이벤트가 없습니다.")
        checkpoint.complete_wave(2)
        checkpoint.save()
        return

    # FallbackChainManager 생성
    # NOTE: AACT와 ClinicalTrials.gov는 현재 차단 상태 (2026-01)
    # - AACT: "role aact is not permitted to log in"
    # - ClinicalTrials.gov v2/classic: 403 Forbidden
    try:
        fallback_manager = create_fallback_chain_manager(
            use_aact=False,  # 차단됨 - 인증 필요
            use_clinicaltrials=False,  # 차단됨 - 403 에러
            use_pubmed=True,
            use_sec=True,
            use_fda=True,
            use_web=True,
        )
        logger.info("FallbackChainManager created (AACT/CT.gov disabled due to blocking)")
    except Exception as e:
        logger.warning(f"Failed to create FallbackChainManager with all clients: {e}")
        # 최소 구성으로 재시도
        fallback_manager = FallbackChainManager()

    # 필드별 진행 상황 초기화
    for field_name in fields:
        checkpoint.update_field_progress(
            field_name=field_name,
            total=len(target_events),
            completed=0,
            found=0,
            confirmed_none=0,
            not_found=0,
            not_searched=len(target_events),
        )

    # 이벤트 처리
    processed = 0
    for field_name in fields:
        checkpoint.start_task(f"2.x_{field_name}")
        print(f"\n--- 필드: {field_name} ---")

        # 세마포어로 동시 처리 제한
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_event(event: dict) -> tuple[str, ChainExecutionResult]:
            """단일 이벤트 처리."""
            async with semaphore:
                event_id = get_event_id(event)
                ticker = get_event_ticker(event)
                drug_name = get_event_drug_name(event)

                try:
                    result = await fallback_manager.execute_chain(
                        field_name=field_name,
                        ticker=ticker,
                        drug_name=drug_name,
                    )
                    return event_id, result
                except Exception as e:
                    logger.error(f"Error processing {event_id}: {e}")
                    return event_id, ChainExecutionResult.not_found(
                        searched_sources=[],
                        errors=[str(e)],
                    )

        # 배치 처리
        tasks = [process_event(event) for event in target_events]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 집계
        found_count = 0
        confirmed_none_count = 0
        not_found_count = 0

        for result in results:
            if isinstance(result, Exception):
                not_found_count += 1
                continue

            event_id, chain_result = result

            if chain_result.status == SearchStatus.FOUND:
                found_count += 1
                checkpoint.remove_from_failed(event_id, field_name)
            elif chain_result.status == SearchStatus.CONFIRMED_NONE:
                confirmed_none_count += 1
                checkpoint.remove_from_failed(event_id, field_name)
            else:
                not_found_count += 1
                # 실패 기록
                error_msg = "; ".join(chain_result.errors) if chain_result.errors else "Not found"
                checkpoint.add_failed_event(event_id, field_name, error_msg)

            checkpoint.increment_api_calls()
            checkpoint.update_event_progress(event_id)
            processed += 1

        # 필드 진행 상황 업데이트
        checkpoint.increment_field_stat(
            field_name=field_name,
            found=found_count,
            confirmed_none=confirmed_none_count,
            not_found=not_found_count,
        )

        print(f"  Found: {found_count}, Confirmed None: {confirmed_none_count}, Not Found: {not_found_count}")

    # Wave 완료
    checkpoint.complete_wave(2)
    checkpoint.save()

    print()
    print(f"Wave 2 완료! 총 {processed}개 처리됨")


async def run_wave_3(
    checkpoint: CheckpointManager,
    events: list[dict],
    dry_run: bool = False,
) -> None:
    """
    Wave 3: 통합 & 검증.

    수집된 데이터를 통합하고 품질 리포트를 생성합니다.

    Args:
        checkpoint: 체크포인트 매니저
        events: 이벤트 리스트
        dry_run: 실제 실행 없이 계획만 출력
    """
    print("=" * 60)
    print("Wave 3: 통합 & 검증")
    print("=" * 60)

    if dry_run:
        print("[DRY-RUN] 실제 실행하지 않음")
        print("  - 수집 데이터 통합")
        print("  - 품질 리포트 생성")
        print("  - 최종 데이터 저장")
        return

    checkpoint.start_wave(3, "통합 & 검증", 3)

    # 3.1 품질 리포트 생성
    checkpoint.start_task("3.1_quality_report")

    field_summary = checkpoint.get_field_summary()

    print()
    print("품질 리포트:")
    print("-" * 40)

    for field_name, summary in field_summary.items():
        completion = summary["completion_rate"]
        success = summary["success_rate"]
        found = summary["found"]

        quality = "Good" if completion >= 80 and success >= 50 else "Needs Review"
        print(f"  {field_name}:")
        print(f"    완료율: {completion:.1f}%")
        print(f"    성공률: {success:.1f}%")
        print(f"    발견: {found}개")
        print(f"    품질: {quality}")
        print()

    # 3.2 실패 이벤트 요약
    checkpoint.start_task("3.2_failed_events_summary")

    retry_queue = checkpoint.get_retry_queue()
    if retry_queue:
        print(f"재시도 가능한 실패 이벤트: {len(retry_queue)}개")

        # 필드별 실패 집계
        field_failures = {}
        for fe in retry_queue:
            field_failures[fe.field_name] = field_failures.get(fe.field_name, 0) + 1

        for field_name, count in sorted(field_failures.items(), key=lambda x: -x[1]):
            print(f"  - {field_name}: {count}개")
        print()

    # 3.3 최종 상태 저장
    checkpoint.start_task("3.3_final_save")

    checkpoint.complete_wave(3)
    checkpoint.complete()
    checkpoint.save()

    print("Wave 3 완료!")


# =============================================================================
# 메인
# =============================================================================

def parse_args() -> argparse.Namespace:
    """명령줄 인수 파싱."""
    parser = argparse.ArgumentParser(
        description="데이터 수집 재개 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    # 체크포인트에서 재개
    python scripts/resume_enrichment.py --from-checkpoint

    # 특정 Wave부터 시작
    python scripts/resume_enrichment.py --wave 2

    # 특정 필드만 재처리
    python scripts/resume_enrichment.py --field phase

    # 실패한 이벤트만 재시도
    python scripts/resume_enrichment.py --retry-failed

    # 현재 상태 확인
    python scripts/resume_enrichment.py --status

    # Dry-run 모드
    python scripts/resume_enrichment.py --wave 2 --dry-run
        """,
    )

    parser.add_argument(
        "--from-checkpoint",
        action="store_true",
        help="마지막 체크포인트에서 재개",
    )
    parser.add_argument(
        "--wave",
        type=int,
        choices=[1, 2, 3],
        help="특정 Wave부터 시작",
    )
    parser.add_argument(
        "--field",
        type=str,
        choices=["phase", "primary_endpoint_met", "adcom", "pai_passed", "nct_id"],
        help="특정 필드만 처리",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="실패한 이벤트만 재시도",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="현재 상태 출력",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 실행 없이 계획만 출력",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,  # Rate limit 방지를 위해 낮춤 (기존 10)
        help="최대 동시 처리 수 (기본: 10)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 로그 출력",
    )

    return parser.parse_args()


async def main() -> None:
    """메인 함수."""
    args = parse_args()

    # 로깅 레벨 설정
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 체크포인트 매니저 초기화
    state_file = PROJECT_ROOT / "data" / "enrichment_state.json"
    checkpoint = CheckpointManager(state_file=state_file)

    # --status: 상태만 출력하고 종료
    if args.status:
        if checkpoint.load():
            show_status(checkpoint)
        else:
            print("체크포인트 없음. 새로 시작해야 합니다.")
            print(f"시작 명령: python scripts/resume_enrichment.py --wave 1")
        return

    # 체크포인트 로드 또는 새로 생성
    if args.from_checkpoint:
        if not checkpoint.load():
            print("체크포인트를 찾을 수 없습니다. --wave 옵션으로 시작하세요.")
            print(f"시작 명령: python scripts/resume_enrichment.py --wave 1")
            sys.exit(1)
        print(f"체크포인트 로드됨:")
        print(f"  - 상태: {checkpoint.state.status}")
        print(f"  - Wave: {checkpoint.state.current_wave}")
        print(f"  - Task: {checkpoint.state.current_task}")
        print()
    else:
        # 새 체크포인트 또는 기존 로드
        if checkpoint.has_checkpoint() and checkpoint.load():
            print(f"기존 체크포인트 발견됨: {checkpoint.state.status}")
            if args.wave:
                print(f"--wave {args.wave} 옵션으로 덮어씁니다.")
        else:
            checkpoint.create()
            print("새 체크포인트 생성됨")

    # 이벤트 로드
    events = load_events()
    if not events:
        print("이벤트 데이터를 찾을 수 없습니다.")
        print("다음 경로 중 하나에 데이터가 있어야 합니다:")
        for path in DATA_FILE_PATHS:
            print(f"  - {path}")
        sys.exit(1)

    print(f"총 {len(events)}개 이벤트 로드됨")
    print()

    # 총 이벤트 수 설정
    checkpoint.state.total_events = len(events)

    # 실행할 Wave 결정
    if args.wave:
        start_wave = args.wave
    elif args.from_checkpoint and checkpoint.state:
        start_wave = checkpoint.state.current_wave
    else:
        start_wave = 1

    # 재개 명령 저장
    resume_cmd = f"python scripts/resume_enrichment.py --from-checkpoint"
    checkpoint.state.resume_command = resume_cmd

    try:
        # Wave 실행
        if start_wave <= 1:
            await run_wave_1(checkpoint, args.dry_run)

        if start_wave <= 2:
            await run_wave_2(
                checkpoint,
                events,
                field=args.field,
                retry_failed=args.retry_failed,
                max_concurrent=args.max_concurrent,
                dry_run=args.dry_run,
            )

        if start_wave <= 3 and not args.field:
            await run_wave_3(checkpoint, events, args.dry_run)

        # 완료
        print()
        print("=" * 60)
        print("완료!")
        print("=" * 60)
        checkpoint.print_report()

    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("중단됨. 체크포인트 저장 중...")
        print("=" * 60)

        checkpoint.pause(resume_cmd)

        print(f"체크포인트 저장 완료: {state_file}")
        print()
        print(f"재개 명령: {resume_cmd}")
        sys.exit(1)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"에러 발생: {e}")
        print("=" * 60)

        logger.exception("Unhandled exception")

        # 체크포인트 저장
        checkpoint.fail(str(e))

        print(f"체크포인트 저장 완료: {state_file}")
        print()
        print(f"재개 명령: {resume_cmd}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
