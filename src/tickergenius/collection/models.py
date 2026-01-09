"""
Data Collection Models
=======================
Data structures for collected PDUFA data.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Any
from enum import Enum


class SourceTier(Enum):
    """Source reliability tier."""
    TIER1 = 1  # FDA CDER, OpenFDA (99% reliable)
    TIER2 = 2  # SEC EDGAR, ClinicalTrials.gov (90% reliable)
    TIER3 = 3  # Company PR, News (75% reliable)
    TIER4 = 4  # Analyst reports, inference (50% reliable)


class ValidationStatus(Enum):
    """Validation result status."""
    VALID = "valid"
    NEEDS_REVIEW = "needs_review"
    INVALID = "invalid"
    MISSING = "missing"


class SearchStatus(str, Enum):
    """
    검색 상태 - 필드 값의 검색/확인 상태를 나타냄.

    5가지 상태:
    - FOUND: 값을 찾음 (재시도 불필요)
    - CONFIRMED_NONE: 공식 소스에서 없음 확인 (재시도 불필요)
    - NOT_APPLICABLE: 해당 케이스에 적용 안됨 (재시도 불필요)
    - NOT_FOUND: 검색했지만 못 찾음 (재시도 필요)
    - NOT_SEARCHED: 아직 검색 안함 (재시도 필요)
    """
    FOUND = "found"
    CONFIRMED_NONE = "confirmed_none"
    NOT_APPLICABLE = "not_applicable"
    NOT_FOUND = "not_found"
    NOT_SEARCHED = "not_searched"

    @property
    def needs_retry(self) -> bool:
        """재시도 필요 여부."""
        return self in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @property
    def is_complete(self) -> bool:
        """검색 완료 여부 (값 있든 없든)."""
        return self in (
            SearchStatus.FOUND,
            SearchStatus.CONFIRMED_NONE,
            SearchStatus.NOT_APPLICABLE
        )


@dataclass
class SourceInfo:
    """Information about a data source."""
    name: str
    tier: SourceTier
    url: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_data: Optional[dict] = None


@dataclass
class FieldValue:
    """A field value with source tracking and search status."""
    value: Any
    status: SearchStatus = SearchStatus.NOT_SEARCHED  # 검색 상태
    sources: list[SourceInfo] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)  # 검색 시도한 소스들
    confidence: float = 1.0
    last_searched: Optional[datetime] = None
    needs_manual_review: bool = False
    conflicts: list[str] = field(default_factory=list)

    @property
    def primary_source(self) -> Optional[SourceInfo]:
        """Get the highest tier source."""
        if not self.sources:
            return None
        return min(self.sources, key=lambda s: s.tier.value)

    @property
    def needs_retry(self) -> bool:
        """재시도 필요 여부."""
        return self.status.needs_retry

    @property
    def is_complete(self) -> bool:
        """검색 완료 여부."""
        return self.status.is_complete

    @property
    def has_value(self) -> bool:
        """값이 있는지 (FOUND 상태)."""
        return self.status == SearchStatus.FOUND and self.value is not None

    def mark_found(self, value: Any, source: str, confidence: float = 1.0):
        """값을 찾았을 때 상태 업데이트."""
        self.value = value
        self.status = SearchStatus.FOUND
        self.confidence = confidence
        if source not in self.searched_sources:
            self.searched_sources.append(source)
        self.last_searched = datetime.now()

    def mark_not_found(self, source: str):
        """검색했지만 못 찾았을 때."""
        if source not in self.searched_sources:
            self.searched_sources.append(source)
        # 이미 FOUND면 유지
        if self.status != SearchStatus.FOUND:
            self.status = SearchStatus.NOT_FOUND
        self.last_searched = datetime.now()

    def mark_confirmed_none(self, source: str):
        """공식 소스에서 없음을 확인했을 때."""
        self.value = None
        self.status = SearchStatus.CONFIRMED_NONE
        if source not in self.searched_sources:
            self.searched_sources.append(source)
        self.last_searched = datetime.now()

    def mark_not_applicable(self):
        """해당 필드가 적용되지 않을 때."""
        self.value = None
        self.status = SearchStatus.NOT_APPLICABLE


@dataclass
class CollectedCase:
    """A single collected PDUFA case."""
    # Identifiers
    ticker: str
    drug_name: str
    case_id: str = ""  # ticker_drugname hash

    # PDUFA info
    pdufa_date: Optional[FieldValue] = None
    result: Optional[FieldValue] = None  # "approved", "crl", "pending"

    # FDA designations
    breakthrough_therapy: Optional[FieldValue] = None
    priority_review: Optional[FieldValue] = None
    fast_track: Optional[FieldValue] = None
    orphan_drug: Optional[FieldValue] = None
    accelerated_approval: Optional[FieldValue] = None

    # Clinical info
    phase: Optional[FieldValue] = None
    primary_endpoint_met: Optional[FieldValue] = None
    nct_id: Optional[FieldValue] = None

    # AdCom info
    adcom_held: Optional[FieldValue] = None
    adcom_date: Optional[FieldValue] = None
    adcom_vote_ratio: Optional[FieldValue] = None

    # CRL info
    has_prior_crl: Optional[FieldValue] = None
    crl_class: Optional[FieldValue] = None  # "class1", "class2"
    is_resubmission: Optional[FieldValue] = None

    # Manufacturing
    pai_passed: Optional[FieldValue] = None
    has_warning_letter: Optional[FieldValue] = None
    warning_letter_date: Optional[FieldValue] = None

    # Metadata
    collected_at: datetime = field(default_factory=datetime.now)
    collection_version: str = "1.0"
    legacy_data: Optional[dict] = None  # v12 data for reference

    def __post_init__(self):
        if not self.case_id:
            # Generate case ID from ticker and drug name
            import hashlib
            key = f"{self.ticker}_{self.drug_name}".lower()
            self.case_id = hashlib.md5(key.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        def field_to_dict(fv: Optional[FieldValue]) -> Optional[dict]:
            if fv is None:
                return None
            return {
                "value": fv.value,
                "confidence": fv.confidence,
                "sources": [s.name for s in fv.sources],
                "needs_review": fv.needs_manual_review,
                "conflicts": fv.conflicts,
            }

        return {
            "case_id": self.case_id,
            "ticker": self.ticker,
            "drug_name": self.drug_name,
            "pdufa_date": field_to_dict(self.pdufa_date),
            "result": field_to_dict(self.result),
            "breakthrough_therapy": field_to_dict(self.breakthrough_therapy),
            "priority_review": field_to_dict(self.priority_review),
            "fast_track": field_to_dict(self.fast_track),
            "orphan_drug": field_to_dict(self.orphan_drug),
            "accelerated_approval": field_to_dict(self.accelerated_approval),
            "phase": field_to_dict(self.phase),
            "primary_endpoint_met": field_to_dict(self.primary_endpoint_met),
            "nct_id": field_to_dict(self.nct_id),
            "adcom_held": field_to_dict(self.adcom_held),
            "adcom_date": field_to_dict(self.adcom_date),
            "adcom_vote_ratio": field_to_dict(self.adcom_vote_ratio),
            "has_prior_crl": field_to_dict(self.has_prior_crl),
            "crl_class": field_to_dict(self.crl_class),
            "is_resubmission": field_to_dict(self.is_resubmission),
            "pai_passed": field_to_dict(self.pai_passed),
            "has_warning_letter": field_to_dict(self.has_warning_letter),
            "warning_letter_date": field_to_dict(self.warning_letter_date),
            "collected_at": self.collected_at.isoformat(),
            "collection_version": self.collection_version,
        }


@dataclass
class ValidationResult:
    """Result of validating collected data."""
    case_id: str
    status: ValidationStatus
    field_validations: dict[str, ValidationStatus] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID

    @property
    def needs_review(self) -> bool:
        return self.status == ValidationStatus.NEEDS_REVIEW
