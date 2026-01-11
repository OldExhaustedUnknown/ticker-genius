"""
Ticker-Genius Pipeline Schemas
==============================
M1: Core pipeline and PDUFA event schemas.

Wave 2 Update (2026-01-10):
- PDUFAEventLegacy: 기존 단순 이벤트 (deprecated)
- PDUFAEvent: 완전한 데이터 스키마 + 12개 신규 필드

Pipeline represents a drug's complete FDA journey including:
- Basic drug information
- PDUFA dates and history
- Clinical trial data
- Manufacturing status
- Approval probability
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional, Any
from pydantic import Field, field_validator

from tickergenius.schemas.base import (
    BaseSchema,
    VersionedSchema,
    StatusField,
    DataStatus,
    SearchStatus,
)
from tickergenius.schemas.enums import (
    ApprovalType,
    CRLType,
    PAIStatus,
    DrugClassification,
    TimingSignal,
    TrialRegion,
    CRLReasonType,
)


# =============================================================================
# Nested Models for StatusField
# =============================================================================

class FDADesignations(BaseSchema):
    """FDA 지정 현황."""
    breakthrough_therapy: bool = False
    fast_track: bool = False
    priority_review: bool = False
    orphan_drug: bool = False
    accelerated_approval: bool = False


class AdComInfo(BaseSchema):
    """Advisory Committee 정보."""
    scheduled: bool = False
    held: bool = False
    date: Optional[date] = None
    outcome: Optional[str] = None  # "positive", "negative", "split"
    vote_for: Optional[int] = None
    vote_against: Optional[int] = None

    @property
    def vote_ratio(self) -> Optional[float]:
        """투표 비율 (찬성/전체)."""
        if self.vote_for is not None and self.vote_against is not None:
            total = self.vote_for + self.vote_against
            if total > 0:
                return self.vote_for / total
        return None


class Enrollment(BaseSchema):
    """임상시험 등록 정보."""
    count: int = 0
    type: str = "ACTUAL"  # ACTUAL, ESTIMATED
    nct_id: Optional[str] = None
    source: str = ""
    fetched_at: Optional[datetime] = None


class PValue(BaseSchema):
    """P-value 통합 모델."""
    value: Optional[str] = None  # 원본 문자열 (e.g., "<0.001", "0.0234")
    numeric: Optional[float] = None  # 숫자값
    is_significant: bool = False  # p < 0.05

    @classmethod
    def from_string(cls, value: str) -> "PValue":
        """문자열에서 PValue 생성."""
        numeric = None
        if value:
            try:
                if value.startswith("<"):
                    numeric = float(value[1:])
                else:
                    numeric = float(value)
            except ValueError:
                pass
        return cls(
            value=value,
            numeric=numeric,
            is_significant=numeric is not None and numeric < 0.05
        )


class CRLReason(BaseSchema):
    """CRL 사유 상세."""
    type: CRLReasonType = CRLReasonType.UNKNOWN
    details: Optional[str] = None
    is_cmc_only: bool = False


# =============================================================================
# PDUFAEvent - Legacy Simple Event (DEPRECATED)
# =============================================================================

class PDUFAEventLegacy(BaseSchema):
    """
    A single PDUFA date event (DEPRECATED).

    Use PDUFAEvent for complete data model.
    Represents one FDA decision date for a drug application.
    """
    pdufa_date: date
    is_confirmed: bool = False  # Official vs estimated date
    source: str = ""
    notes: str = ""

    # Historical tracking
    original_date: Optional[date] = None  # If date was moved
    delay_reason: Optional[str] = None


# =============================================================================
# PDUFAEvent - Complete Data Schema (Wave 2)
# =============================================================================

class PDUFAEvent(BaseSchema):
    """
    완전한 PDUFA 이벤트 스키마.

    Wave 2 (2026-01-10): 12개 신규 필드 추가
    - 사전 수집 (5개): is_single_arm, trial_region, is_biosimilar, is_first_in_class, crl_reason_type
    - 캐시+30일 (4개): warning_letter_date, fda_483_date, fda_483_observations, cdmo_name
    - 분석시 검색 (3개): pai_passed, pai_date, clinical_hold_history
    """

    # ========================================
    # A. 식별자 (Identifiers) - 항상 존재
    # ========================================
    event_id: str
    ticker: str
    company_name: str = ""
    drug_name: str
    pdufa_date: date
    result: str = "pending"  # approved, crl, pending, withdrawn

    # ========================================
    # B. 기본 검색 필드 (StatusField)
    # ========================================
    approval_type: StatusField[str] = Field(default_factory=StatusField.not_searched)
    indication: StatusField[str] = Field(default_factory=StatusField.not_searched)
    generic_name: StatusField[str] = Field(default_factory=StatusField.not_searched)
    therapeutic_area: StatusField[str] = Field(default_factory=StatusField.not_searched)
    mechanism_of_action: StatusField[str] = Field(default_factory=StatusField.not_searched)

    # ========================================
    # C. 임상 정보 (StatusField)
    # ========================================
    phase: StatusField[str] = Field(default_factory=StatusField.not_searched)
    primary_endpoint_met: StatusField[bool] = Field(default_factory=StatusField.not_searched)
    p_value: StatusField[str] = Field(default_factory=StatusField.not_searched)
    p_value_numeric: Optional[float] = None  # 편의를 위한 숫자값
    effect_size: StatusField[str] = Field(default_factory=StatusField.not_searched)
    nct_ids: list[str] = Field(default_factory=list)
    phase3_study_names: list[str] = Field(default_factory=list)
    enrollment: Optional[Enrollment] = None

    # ========================================
    # D. FDA 정보 (StatusField)
    # ========================================
    fda_designations: Optional[FDADesignations] = None
    adcom_info: Optional[AdComInfo] = None

    # ========================================
    # E. CRL 관련 (StatusField)
    # ========================================
    has_prior_crl: StatusField[bool] = Field(default_factory=StatusField.not_searched)
    prior_crl_reason: Optional[str] = None
    is_resubmission: StatusField[Any] = Field(default_factory=StatusField.not_searched)

    # ========================================
    # F. 제조/안전성 (StatusField)
    # ========================================
    pai_passed: StatusField[bool] = Field(default_factory=StatusField.not_searched)
    warning_letter: StatusField[bool] = Field(default_factory=StatusField.not_searched)
    safety_signal: StatusField[bool] = Field(default_factory=StatusField.not_searched)

    # ========================================
    # G. 신규 12개 필드 (Wave 2)
    # ========================================
    # 사전 수집 (5개) - enriched JSON에 저장
    is_single_arm: StatusField[bool] = Field(
        default_factory=StatusField.not_searched,
        description="NCT API designInfo.interventionModel == SINGLE_GROUP"
    )
    trial_region: StatusField[str] = Field(
        default_factory=StatusField.not_searched,
        description="us_only | global | ex_us | china_only"
    )
    is_biosimilar: StatusField[bool] = Field(
        default_factory=StatusField.not_searched,
        description="웹서치 → Purple Book → 접미사 패턴"
    )
    is_first_in_class: StatusField[bool] = Field(
        default_factory=StatusField.not_searched,
        description="FDA Novel Drug Approvals 보고서 웹서치"
    )
    crl_reason_type: StatusField[str] = Field(
        default_factory=StatusField.not_searched,
        description="cmc | efficacy | safety | labeling | unknown"
    )

    # 캐시 + 30일 갱신 (4개) - 회사별 캐시
    warning_letter_date: StatusField[date] = Field(
        default_factory=StatusField.not_searched,
        description="FDA Warning Letters DB"
    )
    fda_483_date: StatusField[date] = Field(
        default_factory=StatusField.not_searched,
        description="FDA 483 DB"
    )
    fda_483_observations: StatusField[int] = Field(
        default_factory=StatusField.not_searched,
        description="FDA 483 관찰 수"
    )
    cdmo_name: StatusField[str] = Field(
        default_factory=StatusField.not_searched,
        description="SEC 10-K manufacturing agreement 검색"
    )

    # 분석 시 검색 (3개) - 실시간 웹서치
    pai_date: StatusField[date] = Field(
        default_factory=StatusField.not_searched,
        description="PAI 통과 날짜"
    )
    clinical_hold_history: StatusField[bool] = Field(
        default_factory=StatusField.not_searched,
        description="Clinical hold FDA 이력"
    )

    # ========================================
    # H. 파생 필드 (Derived)
    # ========================================
    days_to_pdufa: Optional[int] = None
    pdufa_status: Optional[str] = None  # past, imminent, upcoming
    risk_tier: Optional[str] = None  # HIGH, MEDIUM, LOW
    days_calculated_at: Optional[datetime] = None

    # ========================================
    # I. 메타데이터 (Metadata)
    # ========================================
    original_case_id: Optional[str] = None
    data_quality_score: float = 0.0
    collected_at: Optional[datetime] = None
    enriched_at: Optional[datetime] = None
    needs_manual_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    # ========================================
    # 검증
    # ========================================
    @field_validator("pdufa_date", mode="before")
    @classmethod
    def parse_pdufa_date(cls, v):
        """다양한 날짜 형식을 date로 변환."""
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    # ========================================
    # 유틸리티 메서드
    # ========================================
    @property
    def is_approved(self) -> bool:
        """승인 여부."""
        return self.result == "approved"

    @property
    def is_crl(self) -> bool:
        """CRL 여부."""
        return self.result == "crl"

    @property
    def is_pending(self) -> bool:
        """대기 중 여부."""
        return self.result == "pending"

    def get_designation_flags(self) -> dict[str, bool]:
        """FDA 지정 플래그 반환."""
        if self.fda_designations:
            return {
                "btd": self.fda_designations.breakthrough_therapy,
                "fast_track": self.fda_designations.fast_track,
                "priority_review": self.fda_designations.priority_review,
                "orphan_drug": self.fda_designations.orphan_drug,
                "accelerated_approval": self.fda_designations.accelerated_approval,
            }
        return {
            "btd": False,
            "fast_track": False,
            "priority_review": False,
            "orphan_drug": False,
            "accelerated_approval": False,
        }


class CRLDetail(BaseSchema):
    """
    Complete Response Letter detail.

    Tracks CRL history and resubmission probability.
    """
    crl_date: date
    crl_type: CRLType
    issues: list[str] = Field(default_factory=list)

    # Resolution tracking
    resubmission_date: Optional[date] = None
    resolution_timeline_months: Optional[int] = None
    resubmission_class: Optional[str] = None  # Class 1 (2 months) or Class 2 (6 months)

    # Probability impact
    base_approval_impact: float = 0.0  # Negative value (e.g., -0.15)


class ApprovalProbability(BaseSchema):
    """
    FDA approval probability analysis.

    Includes point estimate and confidence interval.
    """
    base_probability: float = Field(ge=0.0, le=1.0)
    adjusted_probability: float = Field(ge=0.0, le=1.0)
    confidence_level: float = Field(ge=0.0, le=1.0)

    # Confidence interval (TF 28차)
    probability_lower: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    probability_upper: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Factor breakdown
    factors: dict[str, float] = Field(default_factory=dict)
    rationale: list[str] = Field(default_factory=list)

    # Method used
    method: str = "hybrid"  # rule, ml, hybrid


class Pipeline(VersionedSchema):
    """
    Complete drug pipeline entry.

    Central data structure for PDUFA analysis. Contains all information
    needed for approval probability calculation and trading decisions.
    """
    # Identifiers
    ticker: str
    drug_name: str
    company_name: str = ""

    # Drug classification
    indication: str = ""
    approval_type: ApprovalType = ApprovalType.NDA
    drug_classification: Optional[DrugClassification] = None

    # PDUFA tracking (using StatusField for uncertain data)
    pdufa_date: StatusField[date] = Field(default_factory=StatusField.unknown)
    days_to_pdufa: Optional[int] = None

    # Historical PDUFA events
    pdufa_history: list[PDUFAEvent] = Field(default_factory=list)

    # CRL history
    crl_history: list[CRLDetail] = Field(default_factory=list)
    has_prior_crl: bool = False

    # Manufacturing/PAI status
    pai_status: StatusField[PAIStatus] = Field(default_factory=StatusField.unknown)
    manufacturing_site: Optional[str] = None

    # Clinical data references
    primary_endpoint: Optional[str] = None
    phase: Optional[str] = None  # Phase 3, etc.
    nct_id: Optional[str] = None  # ClinicalTrials.gov ID

    # Approval probability
    approval_probability: Optional[ApprovalProbability] = None

    # Trading signals
    timing_signal: Optional[TimingSignal] = None

    # Market data (for context)
    market_cap: Optional[float] = None
    current_price: Optional[float] = None

    def get_probability(self) -> float:
        """Get adjusted approval probability or 0 if not calculated."""
        if self.approval_probability:
            return self.approval_probability.adjusted_probability
        return 0.0

    def has_confirmed_pdufa(self) -> bool:
        """Check if PDUFA date is confirmed."""
        return self.pdufa_date.is_confirmed()

    def get_pdufa_date(self) -> Optional[date]:
        """Get PDUFA date if confirmed, else None."""
        if self.pdufa_date.is_confirmed():
            return self.pdufa_date.value
        return None


class PipelineSummary(BaseSchema):
    """
    Lightweight pipeline summary for lists/scans.

    Used in scan results where full Pipeline is too heavy.
    """
    ticker: str
    drug_name: str
    indication: str = ""
    pdufa_date: Optional[date] = None
    days_to_pdufa: Optional[int] = None
    approval_probability: Optional[float] = None
    timing_signal: Optional[TimingSignal] = None


__all__ = [
    # Nested Models (Wave 2)
    "FDADesignations",
    "AdComInfo",
    "Enrollment",
    "PValue",
    "CRLReason",
    # PDUFA Events
    "PDUFAEvent",
    "PDUFAEventLegacy",  # deprecated
    # Other
    "CRLDetail",
    "ApprovalProbability",
    "Pipeline",
    "PipelineSummary",
]
