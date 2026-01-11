"""
Ticker-Genius Base Schemas
==========================
M1: Core schema primitives and StatusField 5-state system.

StatusField 5-State (Wave 2 - SearchStatus):
- FOUND: 값을 찾음 (재시도 불필요)
- CONFIRMED_NONE: 공식 소스에서 없음 확인 (재시도 불필요)
- NOT_APPLICABLE: 해당 케이스에 적용 안됨 (재시도 불필요)
- NOT_FOUND: 검색했지만 못 찾음 (재시도 필요)
- NOT_SEARCHED: 아직 검색 안함 (재시도 필요)

All fields that can have uncertain/missing data should use StatusField.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Optional, Any

from pydantic import BaseModel, Field, ConfigDict, computed_field

T = TypeVar("T")


# Legacy DataStatus kept for backward compatibility
class DataStatus(str, Enum):
    """Data verification status (DEPRECATED - use SearchStatus)."""
    CONFIRMED = "CONFIRMED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


# Import SearchStatus from enums to avoid circular imports
from tickergenius.schemas.enums import SearchStatus, SourceTier


class StatusField(BaseModel, Generic[T]):
    """
    Generic field with 5-state search status tracking.

    Usage:
        class PDUFAEvent(BaseModel):
            phase: StatusField[str]

        # Creating instances:
        found = StatusField.found("Phase 3", source="clinicaltrials.gov")
        not_found = StatusField.not_found(["websearch", "sec_edgar"])
        confirmed_none = StatusField.confirmed_none("fda.gov")
        not_applicable = StatusField.not_applicable("biosimilar")
        not_searched = StatusField.not_searched()

        # Checking:
        if event.phase.has_value:
            phase = event.phase.value
        if event.phase.needs_retry:
            # Re-search needed
    """
    model_config = ConfigDict(frozen=False)  # Mutable for updates

    value: Optional[T] = None
    status: SearchStatus = SearchStatus.NOT_SEARCHED
    source: str = ""
    confidence: float = 0.0
    tier: Optional[int] = None  # SourceTier value (1-4)
    evidence: list[str] = Field(default_factory=list)
    searched_sources: list[str] = Field(default_factory=list)
    last_searched: Optional[datetime] = None
    error: Optional[str] = None
    note: Optional[str] = None  # Additional context

    @computed_field
    @property
    def has_value(self) -> bool:
        """값이 있는지 (FOUND 상태)."""
        return self.status == SearchStatus.FOUND and self.value is not None

    @computed_field
    @property
    def needs_retry(self) -> bool:
        """재시도 필요 여부."""
        return self.status in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @computed_field
    @property
    def is_complete(self) -> bool:
        """검색 완료 여부 (값 있든 없든)."""
        return self.status in (
            SearchStatus.FOUND,
            SearchStatus.CONFIRMED_NONE,
            SearchStatus.NOT_APPLICABLE
        )

    def get_or_default(self, default: T) -> T:
        """Get value or default if not found."""
        if self.has_value:
            return self.value
        return default

    # Legacy compatibility methods
    def is_confirmed(self) -> bool:
        """Check if data is found (legacy compatibility)."""
        return self.status == SearchStatus.FOUND

    def is_empty(self) -> bool:
        """Check if data is confirmed none (legacy compatibility)."""
        return self.status == SearchStatus.CONFIRMED_NONE

    def is_unknown(self) -> bool:
        """Check if data needs search (legacy compatibility)."""
        return self.needs_retry

    # Factory methods
    @classmethod
    def found(
        cls,
        value: T,
        source: str,
        confidence: float = 0.9,
        tier: Optional[int] = None,
        evidence: Optional[list[str]] = None,
        **kwargs
    ) -> "StatusField[T]":
        """Create a FOUND field with value."""
        return cls(
            value=value,
            status=SearchStatus.FOUND,
            source=source,
            confidence=confidence,
            tier=tier,
            evidence=evidence or [],
            searched_sources=[source] if source else [],
            last_searched=datetime.utcnow(),
            **kwargs
        )

    @classmethod
    def not_found(cls, searched_sources: list[str]) -> "StatusField[T]":
        """검색했지만 못 찾음."""
        return cls(
            value=None,
            status=SearchStatus.NOT_FOUND,
            searched_sources=searched_sources,
            last_searched=datetime.utcnow(),
        )

    @classmethod
    def confirmed_none(cls, source: str) -> "StatusField[T]":
        """공식 소스에서 없음 확인."""
        return cls(
            value=None,
            status=SearchStatus.CONFIRMED_NONE,
            source=source,
            searched_sources=[source],
            last_searched=datetime.utcnow(),
        )

    @classmethod
    def not_applicable(cls, reason: str = "") -> "StatusField[T]":
        """해당 케이스에 적용 안됨."""
        return cls(
            value=None,
            status=SearchStatus.NOT_APPLICABLE,
            note=reason,
        )

    @classmethod
    def not_searched(cls) -> "StatusField[T]":
        """아직 검색 안함."""
        return cls(
            value=None,
            status=SearchStatus.NOT_SEARCHED,
        )

    # Legacy factory methods (for backward compatibility)
    @classmethod
    def confirmed(cls, value: T, source: str = "") -> "StatusField[T]":
        """Create a confirmed field (legacy - use found())."""
        return cls.found(value, source)

    @classmethod
    def empty(cls, source: str = "") -> "StatusField[T]":
        """Create an empty field (legacy - use confirmed_none())."""
        return cls.confirmed_none(source) if source else cls.not_searched()

    @classmethod
    def unknown(cls, value: Optional[T] = None, source: str = "") -> "StatusField[T]":
        """Create an unknown field (legacy - use not_searched())."""
        if value is not None:
            return cls.found(value, source, confidence=0.5)
        return cls.not_searched()


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        extra="ignore",
    )


class TimestampedSchema(BaseSchema):
    """Schema with timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VersionedSchema(TimestampedSchema):
    """Schema with version tracking for data lineage."""
    schema_version: str = "1.0.0"
    data_source: str = ""


__all__ = [
    # Search status (Wave 2)
    "SearchStatus",
    "SourceTier",
    # Legacy (deprecated)
    "DataStatus",
    # Core
    "StatusField",
    "BaseSchema",
    "TimestampedSchema",
    "VersionedSchema",
]
