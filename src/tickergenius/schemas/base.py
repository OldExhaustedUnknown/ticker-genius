"""
Ticker-Genius Base Schemas
==========================
M1: Core schema primitives and StatusField 3-state system.

StatusField 3-State:
- CONFIRMED: Data verified from reliable source
- EMPTY: No data available (explicit absence)
- UNKNOWN: Data exists but unverified or uncertain

All fields that can have uncertain/missing data should use StatusField.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Optional, Any

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class DataStatus(str, Enum):
    """Data verification status."""
    CONFIRMED = "CONFIRMED"  # Data verified from reliable source
    EMPTY = "EMPTY"          # No data available (explicit absence)
    UNKNOWN = "UNKNOWN"      # Data exists but unverified


class StatusField(BaseModel, Generic[T]):
    """
    Generic field with 3-state status tracking.

    Usage:
        class Pipeline(BaseModel):
            pdufa_date: StatusField[datetime]

        # Creating instances:
        confirmed = StatusField(value=datetime(2025, 3, 15), status=DataStatus.CONFIRMED)
        empty = StatusField.empty()
        unknown = StatusField(value=datetime(2025, 3, 15), status=DataStatus.UNKNOWN)

        # Checking:
        if pipeline.pdufa_date.is_confirmed():
            date = pipeline.pdufa_date.value
    """
    model_config = ConfigDict(frozen=True)

    value: Optional[T] = None
    status: DataStatus = DataStatus.UNKNOWN
    source: str = ""
    updated_at: Optional[datetime] = None

    def is_confirmed(self) -> bool:
        """Check if data is confirmed."""
        return self.status == DataStatus.CONFIRMED

    def is_empty(self) -> bool:
        """Check if data is explicitly empty."""
        return self.status == DataStatus.EMPTY

    def is_unknown(self) -> bool:
        """Check if data status is unknown."""
        return self.status == DataStatus.UNKNOWN

    def get_or_default(self, default: T) -> T:
        """Get value or default if empty/unknown."""
        if self.is_confirmed() and self.value is not None:
            return self.value
        return default

    @classmethod
    def confirmed(cls, value: T, source: str = "") -> "StatusField[T]":
        """Create a confirmed field."""
        return cls(
            value=value,
            status=DataStatus.CONFIRMED,
            source=source,
            updated_at=datetime.utcnow(),
        )

    @classmethod
    def empty(cls, source: str = "") -> "StatusField[T]":
        """Create an explicitly empty field."""
        return cls(
            value=None,
            status=DataStatus.EMPTY,
            source=source,
            updated_at=datetime.utcnow(),
        )

    @classmethod
    def unknown(cls, value: Optional[T] = None, source: str = "") -> "StatusField[T]":
        """Create an unknown status field."""
        return cls(
            value=value,
            status=DataStatus.UNKNOWN,
            source=source,
            updated_at=datetime.utcnow(),
        )


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
    "DataStatus",
    "StatusField",
    "BaseSchema",
    "TimestampedSchema",
    "VersionedSchema",
]
