"""
Batch Processor
================
병렬 배치 처리기 - Rate Limit 관리 및 병렬 처리.

핵심 기능:
- 토큰 버킷 기반 Rate Limiting
- asyncio 기반 병렬 처리
- 체크포인트 자동 저장
- 폴백 체인 통합

참조: docs/DATA_COLLECTION_DESIGN.md
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any, Optional

from .checkpoint import CheckpointManager
from .fallback_chain import FallbackChainManager, ChainExecutionResult
from .models import SearchStatus
from .search_exceptions import RateLimitException, TimeoutException

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limit 설정
# =============================================================================

RATE_LIMITS = {
    "sec_edgar": {"requests_per_second": 10, "burst": 5},
    "openfda": {"requests_per_minute": 200, "burst": 20},
    "pubmed": {"requests_per_second": 3, "burst": 3},
    "aact_db": {"requests_per_second": 50, "burst": 10},
    "web_search": {"requests_per_second": 1, "burst": 1},
    "clinicaltrials": {"requests_per_second": 3, "burst": 3},
}


# =============================================================================
# Rate Limiter
# =============================================================================

@dataclass
class RateLimiter:
    """
    토큰 버킷 알고리즘 기반 Rate Limiter.

    토큰 버킷 알고리즘:
    - 버킷에는 최대 'burst' 개의 토큰이 있음
    - 요청당 1개의 토큰 소비
    - 시간이 지나면 토큰이 'requests_per_second' 속도로 리필됨
    - 토큰이 없으면 대기
    """
    requests_per_second: float = 1.0
    requests_per_minute: float = 0.0  # 분당 제한 (옵션)
    burst: int = 1
    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.burst)
        self.last_update = time.time()
        # requests_per_minute가 설정되면 초당으로 변환
        if self.requests_per_minute > 0:
            self.requests_per_second = self.requests_per_minute / 60.0

    def _refill(self) -> None:
        """토큰 리필 (시간 경과에 따라)."""
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        # 경과 시간에 비례하여 토큰 추가
        added_tokens = elapsed * self.requests_per_second
        self.tokens = min(self.burst, self.tokens + added_tokens)

    def try_acquire(self) -> bool:
        """
        토큰 획득 시도 (non-blocking).

        Returns:
            토큰 획득 성공 여부
        """
        self._refill()

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def get_wait_time(self) -> float:
        """
        토큰 획득까지 대기 시간 반환.

        Returns:
            대기 시간 (초). 토큰이 있으면 0.
        """
        self._refill()

        if self.tokens >= 1.0:
            return 0.0

        # 1개 토큰이 리필될 때까지 대기 시간 계산
        tokens_needed = 1.0 - self.tokens
        wait_time = tokens_needed / self.requests_per_second
        return wait_time


class GlobalRateLimiter:
    """
    전역 Rate Limiter 관리자.

    각 데이터 소스별로 Rate Limiter를 관리합니다.
    asyncio.Lock을 사용하여 동시성을 제어합니다.

    Usage:
        limiter = GlobalRateLimiter()
        await limiter.acquire("sec_edgar")  # 토큰 획득 (필요시 대기)
        # ... API 호출 ...
    """

    def __init__(self):
        self.limiters: dict[str, RateLimiter] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # 설정에서 리미터 초기화
        for source, config in RATE_LIMITS.items():
            self.limiters[source] = RateLimiter(**config)

    def get_limiter(self, source: str) -> RateLimiter:
        """
        소스별 Rate Limiter 가져오기.

        없으면 기본 설정으로 생성.
        """
        if source not in self.limiters:
            # 기본 설정: 초당 1회
            self.limiters[source] = RateLimiter(
                requests_per_second=1.0,
                burst=1,
            )
        return self.limiters[source]

    async def acquire(self, source: str) -> None:
        """
        토큰 획득 (필요시 대기).

        Args:
            source: 데이터 소스 이름
        """
        async with self._locks[source]:
            limiter = self.get_limiter(source)

            while not limiter.try_acquire():
                wait_time = limiter.get_wait_time()
                if wait_time > 0:
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {source}")
                    await asyncio.sleep(wait_time)

    def get_wait_time(self, source: str) -> float:
        """
        현재 대기 시간 반환.

        Args:
            source: 데이터 소스 이름

        Returns:
            대기 시간 (초)
        """
        limiter = self.get_limiter(source)
        return limiter.get_wait_time()

    def add_limiter(
        self,
        source: str,
        requests_per_second: float = 1.0,
        requests_per_minute: float = 0.0,
        burst: int = 1,
    ) -> None:
        """
        새 Rate Limiter 추가.

        Args:
            source: 데이터 소스 이름
            requests_per_second: 초당 요청 수
            requests_per_minute: 분당 요청 수 (우선)
            burst: 버스트 크기
        """
        self.limiters[source] = RateLimiter(
            requests_per_second=requests_per_second,
            requests_per_minute=requests_per_minute,
            burst=burst,
        )


# =============================================================================
# Batch Result
# =============================================================================

@dataclass
class BatchResult:
    """
    배치 처리 결과.

    단일 이벤트의 단일 필드 처리 결과를 나타냅니다.
    """
    event_id: str
    field_name: str
    success: bool
    value: Any = None
    error: str | None = None
    source_used: str | None = None
    duration_ms: float = 0.0
    status: SearchStatus = SearchStatus.NOT_SEARCHED
    confidence: float = 0.0
    searched_sources: list[str] = field(default_factory=list)

    @classmethod
    def from_chain_result(
        cls,
        event_id: str,
        field_name: str,
        result: ChainExecutionResult,
        duration_ms: float = 0.0,
    ) -> "BatchResult":
        """ChainExecutionResult에서 BatchResult 생성."""
        return cls(
            event_id=event_id,
            field_name=field_name,
            success=result.status == SearchStatus.FOUND,
            value=result.value,
            source_used=result.source,
            duration_ms=duration_ms,
            status=result.status,
            confidence=result.confidence,
            searched_sources=result.searched_sources,
        )

    @classmethod
    def error_result(
        cls,
        event_id: str,
        field_name: str,
        error_message: str,
        duration_ms: float = 0.0,
    ) -> "BatchResult":
        """에러 결과 생성."""
        return cls(
            event_id=event_id,
            field_name=field_name,
            success=False,
            error=error_message,
            duration_ms=duration_ms,
            status=SearchStatus.NOT_FOUND,
        )


# =============================================================================
# Batch Processor
# =============================================================================

class BatchProcessor:
    """
    병렬 배치 처리기.

    여러 이벤트를 병렬로 처리하면서:
    - Rate Limit 준수
    - 체크포인트 자동 저장
    - 폴백 체인 실행
    - 에러 처리 및 재시도

    Usage:
        processor = BatchProcessor(
            checkpoint_manager=CheckpointManager(),
            fallback_manager=FallbackChainManager(...),
        )

        results = await processor.process_batch(
            events=[{"event_id": "1", "ticker": "AXSM", "drug_name": "AXS-05"}, ...],
            field_name="btd",
            progress_callback=lambda done, total: print(f"{done}/{total}"),
        )
    """

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        fallback_manager: FallbackChainManager,
        max_concurrent: int = 10,
        save_interval: int = 50,
    ):
        """
        Args:
            checkpoint_manager: CheckpointManager 인스턴스
            fallback_manager: FallbackChainManager 인스턴스
            max_concurrent: 최대 동시 실행 수
            save_interval: N개 처리마다 체크포인트 저장
        """
        self.checkpoint = checkpoint_manager
        self.fallback = fallback_manager
        self.max_concurrent = max_concurrent
        self.save_interval = save_interval
        self.rate_limiter = GlobalRateLimiter()
        self._semaphore: asyncio.Semaphore | None = None
        self._processed_count = 0
        self._lock = asyncio.Lock()

    async def process_batch(
        self,
        events: list[dict],
        field_name: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[BatchResult]:
        """
        이벤트 배치를 병렬로 처리.

        Args:
            events: 이벤트 리스트. 각 이벤트는 다음 필드 포함:
                - event_id: str
                - ticker: str
                - drug_name: str
                - start_date: str (옵션)
                - before_date: str (옵션)
            field_name: 처리할 필드명
            progress_callback: 진행 상황 콜백 (completed, total)

        Returns:
            BatchResult 리스트
        """
        if not events:
            return []

        total = len(events)
        logger.info(f"Starting batch processing: {total} events for field '{field_name}'")

        # Semaphore 초기화
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._processed_count = 0

        # 태스크 생성
        tasks = [
            self._process_with_semaphore(
                event=event,
                field_name=field_name,
                progress_callback=progress_callback,
                total=total,
            )
            for event in events
        ]

        # 병렬 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외를 BatchResult로 변환
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                event_id = events[i].get("event_id", f"unknown_{i}")
                batch_results.append(BatchResult.error_result(
                    event_id=event_id,
                    field_name=field_name,
                    error_message=str(result),
                ))
            else:
                batch_results.append(result)

        # 최종 체크포인트 저장
        self.checkpoint.save(force=True)

        # 통계 로깅
        success_count = sum(1 for r in batch_results if r.success)
        logger.info(
            f"Batch processing completed: {success_count}/{total} successful "
            f"for field '{field_name}'"
        )

        return batch_results

    async def _process_with_semaphore(
        self,
        event: dict,
        field_name: str,
        progress_callback: Callable[[int, int], None] | None,
        total: int,
    ) -> BatchResult:
        """세마포어로 동시 실행 제한."""
        async with self._semaphore:
            result = await self._process_single_event(event, field_name)

            # 진행 상황 업데이트
            async with self._lock:
                self._processed_count += 1
                completed = self._processed_count

                # 체크포인트 저장 (interval마다)
                if completed % self.save_interval == 0:
                    self.checkpoint.save()
                    logger.debug(f"Checkpoint saved at {completed}/{total}")

            # 콜백 호출
            if progress_callback:
                try:
                    progress_callback(completed, total)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

            return result

    async def _process_single_event(
        self,
        event: dict,
        field_name: str,
    ) -> BatchResult:
        """
        단일 이벤트 처리.

        Args:
            event: 이벤트 딕셔너리
            field_name: 필드명

        Returns:
            BatchResult
        """
        event_id = event.get("event_id", "")
        ticker = event.get("ticker", "")
        drug_name = event.get("drug_name", "")
        start_date = event.get("start_date")
        before_date = event.get("before_date")

        start_time = datetime.now()

        try:
            # 폴백 체인 실행
            chain_result = await self.fallback.execute_chain(
                field_name=field_name,
                ticker=ticker,
                drug_name=drug_name,
                start_date=start_date,
                before_date=before_date,
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # 결과 생성
            result = BatchResult.from_chain_result(
                event_id=event_id,
                field_name=field_name,
                result=chain_result,
                duration_ms=duration_ms,
            )

            # 체크포인트 업데이트
            if chain_result.status == SearchStatus.FOUND:
                self.checkpoint.increment_field_stat(field_name, found=1)
            elif chain_result.status == SearchStatus.CONFIRMED_NONE:
                self.checkpoint.increment_field_stat(field_name, confirmed_none=1)
            else:
                self.checkpoint.increment_field_stat(field_name, not_found=1)

            self.checkpoint.update_event_progress(event_id)

            # 실패 목록에서 제거 (성공 시)
            if result.success:
                self.checkpoint.remove_from_failed(event_id, field_name)

            logger.debug(
                f"[{event_id}] {field_name}: {chain_result.status.value} "
                f"({duration_ms:.0f}ms)"
            )

            return result

        except RateLimitException as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Rate limit: {e.message} (retry_after={e.retry_after}s)"

            self.checkpoint.add_failed_event(event_id, field_name, error_msg)
            logger.warning(f"[{event_id}] {field_name}: {error_msg}")

            return BatchResult.error_result(
                event_id=event_id,
                field_name=field_name,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

        except TimeoutException as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Timeout: {e.message}"

            self.checkpoint.add_failed_event(event_id, field_name, error_msg)
            logger.warning(f"[{event_id}] {field_name}: {error_msg}")

            return BatchResult.error_result(
                event_id=event_id,
                field_name=field_name,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"

            self.checkpoint.add_failed_event(event_id, field_name, error_msg)
            logger.error(f"[{event_id}] {field_name}: {error_msg}")

            return BatchResult.error_result(
                event_id=event_id,
                field_name=field_name,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

    async def process_multiple_fields(
        self,
        events: list[dict],
        field_names: list[str],
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, list[BatchResult]]:
        """
        여러 필드를 순차적으로 처리.

        각 필드는 전체 이벤트에 대해 처리된 후 다음 필드로 진행됩니다.
        이렇게 하면 Rate Limit을 더 효율적으로 관리할 수 있습니다.

        Args:
            events: 이벤트 리스트
            field_names: 처리할 필드명 리스트
            progress_callback: 진행 상황 콜백 (field_name, completed, total)

        Returns:
            {field_name: [BatchResult, ...]}
        """
        results = {}
        total_fields = len(field_names)

        for i, field_name in enumerate(field_names):
            logger.info(f"Processing field {i+1}/{total_fields}: {field_name}")

            # 필드별 진행 상황 콜백 래퍼
            field_callback = None
            if progress_callback:
                def make_callback(fn: str):
                    def callback(completed: int, total: int):
                        progress_callback(fn, completed, total)
                    return callback
                field_callback = make_callback(field_name)

            # 배치 처리
            field_results = await self.process_batch(
                events=events,
                field_name=field_name,
                progress_callback=field_callback,
            )

            results[field_name] = field_results

            # 필드 간 짧은 대기 (API 부하 분산)
            if i < total_fields - 1:
                await asyncio.sleep(1.0)

        return results

    async def retry_failed_events(
        self,
        field_name: str,
        events_data: dict[str, dict],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[BatchResult]:
        """
        실패한 이벤트 재시도.

        Args:
            field_name: 필드명
            events_data: {event_id: event_dict} 매핑
            progress_callback: 진행 상황 콜백

        Returns:
            BatchResult 리스트
        """
        # 재시도 가능한 실패 이벤트 가져오기
        failed_events = self.checkpoint.get_retry_queue()
        retry_events = [
            fe for fe in failed_events
            if fe.field_name == field_name and fe.should_retry
        ]

        if not retry_events:
            logger.info(f"No events to retry for field '{field_name}'")
            return []

        logger.info(f"Retrying {len(retry_events)} failed events for field '{field_name}'")

        # 이벤트 데이터 구성
        events = []
        for fe in retry_events:
            if fe.event_id in events_data:
                events.append(events_data[fe.event_id])

        if not events:
            logger.warning("No event data found for failed events")
            return []

        # 재처리
        return await self.process_batch(
            events=events,
            field_name=field_name,
            progress_callback=progress_callback,
        )

    def get_stats(self) -> dict:
        """처리 통계 반환."""
        return {
            "processed_count": self._processed_count,
            "max_concurrent": self.max_concurrent,
            "save_interval": self.save_interval,
            "rate_limiters": list(self.rate_limiter.limiters.keys()),
        }


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "RATE_LIMITS",
    "RateLimiter",
    "GlobalRateLimiter",
    "BatchResult",
    "BatchProcessor",
]


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def test_rate_limiter():
        """Rate Limiter 테스트."""
        print("\n=== Rate Limiter Test ===")

        # 단일 리미터 테스트
        limiter = RateLimiter(requests_per_second=2.0, burst=3)
        print(f"Initial tokens: {limiter.tokens}")

        # 버스트 소진
        for i in range(5):
            acquired = limiter.try_acquire()
            wait_time = limiter.get_wait_time()
            print(f"  Attempt {i+1}: acquired={acquired}, wait_time={wait_time:.3f}s")

        # 대기 후 재시도
        await asyncio.sleep(1.0)
        acquired = limiter.try_acquire()
        print(f"  After 1s wait: acquired={acquired}")

        # 글로벌 리미터 테스트
        print("\n=== Global Rate Limiter Test ===")
        global_limiter = GlobalRateLimiter()

        start = time.time()
        for i in range(5):
            await global_limiter.acquire("web_search")
            elapsed = time.time() - start
            print(f"  Acquired {i+1} at {elapsed:.2f}s")

        print("Rate limiter tests passed!")

    async def test_batch_processor():
        """Batch Processor 테스트 (mock)."""
        print("\n=== Batch Processor Test (Mock) ===")

        # Mock CheckpointManager
        class MockCheckpointManager:
            def save(self, force=False):
                pass

            def increment_field_stat(self, field_name, found=0, confirmed_none=0, not_found=0):
                pass

            def update_event_progress(self, event_id):
                pass

            def add_failed_event(self, event_id, field_name, error_msg):
                pass

            def remove_from_failed(self, event_id, field_name):
                pass

            def get_retry_queue(self):
                return []

        # Mock FallbackChainManager
        class MockFallbackChainManager:
            async def execute_chain(self, field_name, ticker, drug_name, **kwargs):
                await asyncio.sleep(0.1)  # 시뮬레이션
                return ChainExecutionResult.found(
                    value=True,
                    source="mock_source",
                    source_tier=1,
                    confidence=0.9,
                )

        processor = BatchProcessor(
            checkpoint_manager=MockCheckpointManager(),
            fallback_manager=MockFallbackChainManager(),
            max_concurrent=3,
            save_interval=2,
        )

        # 테스트 이벤트
        events = [
            {"event_id": f"test_{i}", "ticker": "TEST", "drug_name": "TestDrug"}
            for i in range(5)
        ]

        def progress(completed, total):
            print(f"  Progress: {completed}/{total}")

        results = await processor.process_batch(
            events=events,
            field_name="btd",
            progress_callback=progress,
        )

        print(f"\nResults: {len(results)} processed")
        for r in results:
            print(f"  {r.event_id}: success={r.success}, value={r.value}")

        print("\nBatch processor tests passed!")

    async def main():
        await test_rate_limiter()
        await test_batch_processor()
        print("\n=== All tests passed! ===")

    asyncio.run(main())
