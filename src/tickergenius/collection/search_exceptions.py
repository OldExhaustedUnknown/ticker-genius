"""
Search Exceptions
==================
검색 관련 예외 클래스들.

각 예외는 디버깅에 유용한 컨텍스트 정보를 포함합니다.

사용 예시:
    from tickergenius.collection.search_exceptions import (
        RateLimitException,
        APIBlockedException,
        TimeoutException,
        DataNotFoundException,
        ValidationException,
    )

    try:
        result = api_client.search(query)
    except RateLimitException as e:
        time.sleep(e.retry_after)
    except APIBlockedException as e:
        result = fallback_search(e.fallback_source)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class SearchException(Exception):
    """
    검색 예외 기본 클래스.

    모든 검색 관련 예외의 베이스 클래스입니다.
    디버깅에 유용한 컨텍스트 정보를 포함합니다.

    Attributes:
        message: 에러 메시지
        source: 에러가 발생한 소스 (api, web_search 등)
        context: 추가 컨텍스트 정보
        timestamp: 예외 발생 시각
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.source = source
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]

        if self.source:
            parts.append(f"source={self.source}")

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"context=[{context_str}]")

        return " | ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"source={self.source!r}, "
            f"context={self.context!r})"
        )


class RateLimitException(SearchException):
    """
    Rate limit 초과 예외.

    API rate limit에 도달했을 때 발생합니다.
    retry_after 값을 사용하여 재시도 시점을 결정할 수 있습니다.

    Attributes:
        retry_after: 재시도까지 대기 시간 (초)
        limit: rate limit 값 (분당 호출 수)
        remaining: 남은 호출 수

    Usage:
        try:
            result = client.search(query)
        except RateLimitException as e:
            logger.warning(f"Rate limited, waiting {e.retry_after}s")
            time.sleep(e.retry_after)
            result = client.search(query)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        source: Optional[str] = None,
        retry_after: float = 60.0,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        ctx = context or {}
        ctx.update({
            k: v for k, v in {
                "limit": limit,
                "remaining": remaining,
            }.items() if v is not None
        })

        super().__init__(message=message, source=source, context=ctx)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining

    def __str__(self) -> str:
        base = super().__str__()
        return f"{base} | retry_after={self.retry_after}s"


class APIBlockedException(SearchException):
    """
    API 차단 예외.

    API가 차단되었을 때 발생합니다 (403 Forbidden 등).
    fallback_source를 사용하여 대체 검색을 수행할 수 있습니다.

    Attributes:
        fallback_source: 대체 검색 소스
        status_code: HTTP 상태 코드
        is_temporary: 일시적 차단 여부

    Usage:
        try:
            result = primary_client.search(query)
        except APIBlockedException as e:
            if e.fallback_source:
                result = fallback_client.search(query, source=e.fallback_source)
            else:
                raise
    """

    def __init__(
        self,
        message: str = "API access blocked",
        source: Optional[str] = None,
        fallback_source: Optional[str] = None,
        status_code: int = 403,
        is_temporary: bool = False,
        context: Optional[dict[str, Any]] = None,
    ):
        ctx = context or {}
        ctx["status_code"] = status_code
        if is_temporary:
            ctx["is_temporary"] = True

        super().__init__(message=message, source=source, context=ctx)
        self.fallback_source = fallback_source
        self.status_code = status_code
        self.is_temporary = is_temporary

    def __str__(self) -> str:
        base = super().__str__()
        parts = [base]

        if self.fallback_source:
            parts.append(f"fallback_source={self.fallback_source}")

        return " | ".join(parts)


class TimeoutException(SearchException):
    """
    타임아웃 예외.

    요청 타임아웃이 발생했을 때 발생합니다.
    retry_count를 통해 현재까지의 재시도 횟수를 추적합니다.

    Attributes:
        retry_count: 현재까지 재시도 횟수
        max_retries: 최대 재시도 횟수
        timeout_seconds: 타임아웃 설정값 (초)

    Usage:
        try:
            result = client.search(query)
        except TimeoutException as e:
            if e.retry_count < e.max_retries:
                # Retry with increased timeout
                result = client.search(query, timeout=e.timeout_seconds * 2)
            else:
                logger.error(f"Max retries exceeded: {e}")
    """

    def __init__(
        self,
        message: str = "Request timed out",
        source: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        url: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        ctx = context or {}
        if url:
            ctx["url"] = url

        super().__init__(message=message, source=source, context=ctx)
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.url = url

    @property
    def can_retry(self) -> bool:
        """재시도 가능 여부."""
        return self.retry_count < self.max_retries

    @property
    def remaining_retries(self) -> int:
        """남은 재시도 횟수."""
        return max(0, self.max_retries - self.retry_count)

    def __str__(self) -> str:
        base = super().__str__()
        return (
            f"{base} | retry_count={self.retry_count}/{self.max_retries}, "
            f"timeout={self.timeout_seconds}s"
        )


class DataNotFoundException(SearchException):
    """
    데이터 없음 예외.

    검색 결과 데이터를 찾지 못했을 때 발생합니다.
    is_confirmed_none으로 공식적으로 없음이 확인된 경우와
    단순히 찾지 못한 경우를 구분합니다.

    Attributes:
        is_confirmed_none: 공식 소스에서 없음 확인 여부
        searched_sources: 검색 시도한 소스 목록
        query: 검색 쿼리
        ticker: 관련 티커 (있는 경우)
        drug_name: 관련 약물명 (있는 경우)

    Usage:
        try:
            result = client.search_btd(ticker, drug_name)
        except DataNotFoundException as e:
            if e.is_confirmed_none:
                # 공식적으로 없음 확인됨 - 재시도 불필요
                return FieldValue(value=None, status=SearchStatus.CONFIRMED_NONE)
            else:
                # 찾지 못함 - 다른 소스로 재시도 가능
                return FieldValue(value=None, status=SearchStatus.NOT_FOUND)
    """

    def __init__(
        self,
        message: str = "Data not found",
        source: Optional[str] = None,
        is_confirmed_none: bool = False,
        searched_sources: Optional[list[str]] = None,
        query: Optional[str] = None,
        ticker: Optional[str] = None,
        drug_name: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        ctx = context or {}
        if ticker:
            ctx["ticker"] = ticker
        if drug_name:
            ctx["drug_name"] = drug_name
        if query:
            ctx["query"] = query

        super().__init__(message=message, source=source, context=ctx)
        self.is_confirmed_none = is_confirmed_none
        self.searched_sources = searched_sources or []
        self.query = query
        self.ticker = ticker
        self.drug_name = drug_name

    @property
    def needs_retry(self) -> bool:
        """재시도 필요 여부 (confirmed_none이 아닌 경우)."""
        return not self.is_confirmed_none

    def __str__(self) -> str:
        base = super().__str__()
        parts = [base]

        if self.is_confirmed_none:
            parts.append("confirmed_none=True")

        if self.searched_sources:
            sources_str = ", ".join(self.searched_sources[:5])
            if len(self.searched_sources) > 5:
                sources_str += f"... (+{len(self.searched_sources) - 5})"
            parts.append(f"searched=[{sources_str}]")

        return " | ".join(parts)


class ValidationException(SearchException):
    """
    검증 실패 예외.

    검색 결과 검증에 실패했을 때 발생합니다.

    Attributes:
        field_name: 검증 실패한 필드명
        expected: 기대값 (있는 경우)
        actual: 실제값 (있는 경우)
        validation_errors: 검증 에러 목록

    Usage:
        try:
            result = validator.validate_crl_result(data)
        except ValidationException as e:
            logger.warning(
                f"Validation failed for {e.field_name}: "
                f"expected={e.expected}, actual={e.actual}"
            )
            for error in e.validation_errors:
                logger.debug(f"  - {error}")
    """

    def __init__(
        self,
        message: str = "Validation failed",
        source: Optional[str] = None,
        field_name: Optional[str] = None,
        expected: Any = None,
        actual: Any = None,
        validation_errors: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        ctx = context or {}
        if field_name:
            ctx["field"] = field_name

        super().__init__(message=message, source=source, context=ctx)
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        self.validation_errors = validation_errors or []

    def __str__(self) -> str:
        base = super().__str__()
        parts = [base]

        if self.expected is not None or self.actual is not None:
            parts.append(f"expected={self.expected!r}, actual={self.actual!r}")

        if self.validation_errors:
            errors_str = "; ".join(self.validation_errors[:3])
            if len(self.validation_errors) > 3:
                errors_str += f"... (+{len(self.validation_errors) - 3})"
            parts.append(f"errors=[{errors_str}]")

        return " | ".join(parts)


# Export all exception classes
__all__ = [
    "SearchException",
    "RateLimitException",
    "APIBlockedException",
    "TimeoutException",
    "DataNotFoundException",
    "ValidationException",
]
