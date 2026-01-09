"""
Ticker-Genius Analysis Context
================================
M3: Input objectification to prevent parameter explosion.

AnalysisContext encapsulates all input data needed for probability calculation.
This prevents the "20+ parameter" problem seen in the legacy code.

Usage:
    context = AnalysisContext.from_pipeline(pipeline)
    probability = calculator.calculate(context)

Design Principles:
1. Immutable: Context is frozen after creation
2. Complete: Contains all data needed for analysis
3. Derivable: Can compute derived fields (days_to_pdufa, etc.)
4. Extensible: Extra fields via extra_factors dict
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Any

from tickergenius.schemas.enums import (
    CRLType,
    ApprovalType,
    PAIStatus,
)


@dataclass(frozen=True)
class CRLInfo:
    """CRL information for context."""
    crl_type: CRLType
    crl_date: Optional[date] = None
    resubmission_class: Optional[str] = None  # "class1" or "class2"
    is_cmc_only: bool = False
    issues: tuple[str, ...] = ()
    days_to_resubmission: Optional[int] = None


@dataclass(frozen=True)
class AdComInfo:
    """AdCom information for context."""
    was_held: bool = False
    was_waived: bool = False
    vote_ratio: Optional[float] = None  # favor / total
    vote_for: Optional[int] = None
    vote_against: Optional[int] = None
    outcome: Optional[str] = None  # "positive", "negative", "mixed"
    adcom_date: Optional[date] = None  # 이벤트 일자


@dataclass(frozen=True)
class ClinicalInfo:
    """Clinical trial information for context."""
    phase: str = "phase3"
    primary_endpoint_met: Optional[bool] = None
    is_single_arm: bool = False
    is_rwe_external_control: bool = False
    trial_region: Optional[str] = None  # "global", "us_only", "china_only"
    has_clinical_hold_history: bool = False
    sample_size: Optional[int] = None
    nct_id: Optional[str] = None
    # Mental health indication (high placebo response baseline)
    is_mental_health: bool = False
    mental_health_type: Optional[str] = None  # "mdd", "ptsd", "anxiety", "bipolar", "schizophrenia"
    # Clinical hold dates
    clinical_hold_date: Optional[date] = None
    clinical_hold_lifted_date: Optional[date] = None


@dataclass(frozen=True)
class ManufacturingInfo:
    """Manufacturing/facility information for context."""
    pai_status: Optional[PAIStatus] = None
    pai_passed: bool = False
    has_warning_letter: bool = False
    fda_483_observations: int = 0
    cdmo_name: Optional[str] = None
    is_high_risk_cdmo: bool = False
    facility_recent_approval: bool = False
    # 이벤트 일자
    pai_date: Optional[date] = None
    warning_letter_date: Optional[date] = None
    fda_483_date: Optional[date] = None


@dataclass(frozen=True)
class FDADesignations:
    """FDA designations for context."""
    breakthrough_therapy: bool = False
    priority_review: bool = False
    fast_track: bool = False
    orphan_drug: bool = False
    accelerated_approval: bool = False
    is_first_in_class: bool = False

    def count(self) -> int:
        """Count total designations."""
        return sum([
            self.breakthrough_therapy,
            self.priority_review,
            self.fast_track,
            self.orphan_drug,
            self.accelerated_approval,
        ])

    def has_any(self) -> bool:
        """Check if has any designation."""
        return self.count() > 0


@dataclass(frozen=True)
class DisputeInfo:
    """FDA dispute resolution information for context."""
    has_dispute: bool = False
    dispute_result: Optional[str] = None  # "won_fully", "partial", "lost_fully"
    dispute_date: Optional[date] = None
    dispute_type: Optional[str] = None  # "scientific", "labeling", "approval_pathway"


@dataclass(frozen=True)
class EarningsCallInfo:
    """Earnings call signals for context."""
    label_negotiation_mentioned: bool = False
    timeline_delayed: bool = False
    management_confident: bool = False
    management_cautious: bool = False
    last_earnings_date: Optional[date] = None
    relevant_quotes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CitizenPetitionInfo:
    """Citizen petition information for context."""
    has_petition: bool = False
    petition_status: Optional[str] = None  # "filed", "denied", "granted"
    petition_date: Optional[date] = None
    petition_docket_id: Optional[str] = None
    petitioner: Optional[str] = None


@dataclass(frozen=True)
class AnalysisContext:
    """
    Complete context for PDUFA analysis.

    This is the single input object for probability calculation,
    replacing the 20+ parameter functions in legacy code.

    Immutable by design (frozen=True) to ensure consistency.
    """

    # Required
    ticker: str
    drug_name: str

    # PDUFA date
    pdufa_date: Optional[date] = None
    pdufa_confirmed: bool = False
    days_to_pdufa: Optional[int] = None

    # Application info
    approval_type: ApprovalType = ApprovalType.NDA
    is_supplement: bool = False
    is_biosimilar: bool = False
    is_resubmission: bool = False

    # Structured info
    fda_designations: FDADesignations = field(default_factory=FDADesignations)
    adcom: AdComInfo = field(default_factory=AdComInfo)
    crl_history: tuple[CRLInfo, ...] = ()
    clinical: ClinicalInfo = field(default_factory=ClinicalInfo)
    manufacturing: ManufacturingInfo = field(default_factory=ManufacturingInfo)

    # SPA info
    spa_agreed: bool = False
    spa_rescinded: bool = False

    # New factors (M3 확장)
    dispute: DisputeInfo = field(default_factory=DisputeInfo)
    earnings_call: EarningsCallInfo = field(default_factory=EarningsCallInfo)
    citizen_petition: CitizenPetitionInfo = field(default_factory=CitizenPetitionInfo)

    # Extra factors (for extensibility)
    extra_factors: dict[str, Any] = field(default_factory=dict)

    # Metadata
    analysis_date: date = field(default_factory=date.today)

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------

    @property
    def has_prior_crl(self) -> bool:
        """Check if has prior CRL."""
        return len(self.crl_history) > 0

    @property
    def latest_crl(self) -> Optional[CRLInfo]:
        """Get latest CRL if any."""
        if not self.crl_history:
            return None
        return self.crl_history[-1]

    @property
    def is_class1_resubmission(self) -> bool:
        """Check if class 1 resubmission."""
        if not self.is_resubmission or not self.latest_crl:
            return False
        return self.latest_crl.resubmission_class == "class1"

    @property
    def is_class2_resubmission(self) -> bool:
        """Check if class 2 resubmission."""
        if not self.is_resubmission or not self.latest_crl:
            return False
        return self.latest_crl.resubmission_class == "class2"

    @property
    def is_cmc_only_crl(self) -> bool:
        """Check if latest CRL was CMC-only."""
        if not self.latest_crl:
            return False
        return self.latest_crl.is_cmc_only

    @property
    def adcom_vote_positive(self) -> bool:
        """Check if AdCom vote was positive (>50%)."""
        if not self.adcom.was_held or self.adcom.vote_ratio is None:
            return False
        return self.adcom.vote_ratio > 0.5

    @property
    def adcom_vote_negative(self) -> bool:
        """Check if AdCom vote was negative (<=50%)."""
        if not self.adcom.was_held or self.adcom.vote_ratio is None:
            return False
        return 0 < self.adcom.vote_ratio <= 0.5

    # -------------------------------------------------------------------------
    # Temporal Properties (이벤트 선후관계)
    # -------------------------------------------------------------------------

    @property
    def days_since_adcom(self) -> Optional[int]:
        """AdCom 이후 경과 일수."""
        if not self.adcom.adcom_date:
            return None
        return (self.analysis_date - self.adcom.adcom_date).days

    @property
    def days_since_warning_letter(self) -> Optional[int]:
        """Warning Letter 이후 경과 일수."""
        if not self.manufacturing.warning_letter_date:
            return None
        return (self.analysis_date - self.manufacturing.warning_letter_date).days

    @property
    def days_since_pai(self) -> Optional[int]:
        """PAI 이후 경과 일수."""
        if not self.manufacturing.pai_date:
            return None
        return (self.analysis_date - self.manufacturing.pai_date).days

    @property
    def days_since_latest_crl(self) -> Optional[int]:
        """최근 CRL 이후 경과 일수."""
        if not self.latest_crl or not self.latest_crl.crl_date:
            return None
        return (self.analysis_date - self.latest_crl.crl_date).days

    @property
    def is_warning_letter_recent(self) -> bool:
        """Warning Letter가 최근(180일 이내)인지 확인."""
        days = self.days_since_warning_letter
        if days is None:
            return self.manufacturing.has_warning_letter  # 날짜 없으면 있는 것으로 간주
        return days <= 180

    @property
    def is_warning_letter_stale(self) -> bool:
        """Warning Letter가 오래됐는지(365일 초과) 확인."""
        days = self.days_since_warning_letter
        if days is None:
            return False
        return days > 365

    @property
    def warning_letter_after_pai(self) -> bool:
        """Warning Letter가 PAI 이후에 발생했는지 (더 심각)."""
        if not self.manufacturing.warning_letter_date or not self.manufacturing.pai_date:
            return False
        return self.manufacturing.warning_letter_date > self.manufacturing.pai_date

    @property
    def adcom_before_pdufa_days(self) -> Optional[int]:
        """AdCom이 PDUFA 몇 일 전인지."""
        if not self.adcom.adcom_date or not self.pdufa_date:
            return None
        return (self.pdufa_date - self.adcom.adcom_date).days

    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    @classmethod
    def from_pipeline(cls, pipeline: "Pipeline") -> "AnalysisContext":
        """
        Create context from Pipeline schema.

        Args:
            pipeline: Pipeline schema instance

        Returns:
            AnalysisContext populated from pipeline data
        """
        from tickergenius.schemas.pipeline import Pipeline

        # Extract PDUFA date
        pdufa_date = None
        pdufa_confirmed = False
        if pipeline.pdufa_date.is_confirmed():
            pdufa_date = pipeline.pdufa_date.value
            pdufa_confirmed = True
        elif pipeline.pdufa_date.value:
            pdufa_date = pipeline.pdufa_date.value

        # Build CRL history
        crl_history = tuple(
            CRLInfo(
                crl_type=crl.crl_type,
                crl_date=crl.crl_date,
                resubmission_class=crl.resubmission_class,
                is_cmc_only=(crl.crl_type == CRLType.CMC),
                issues=tuple(crl.issues),
            )
            for crl in pipeline.crl_history
        )

        # Build FDA designations (would need to be extracted from pipeline)
        # For now, use defaults - will be populated by data layer
        fda_designations = FDADesignations()

        # Build clinical info
        clinical = ClinicalInfo(
            phase=pipeline.phase or "phase3",
            nct_id=pipeline.nct_id,
        )

        return cls(
            ticker=pipeline.ticker,
            drug_name=pipeline.drug_name,
            pdufa_date=pdufa_date,
            pdufa_confirmed=pdufa_confirmed,
            days_to_pdufa=pipeline.days_to_pdufa,
            approval_type=pipeline.approval_type,
            is_resubmission=pipeline.has_prior_crl,
            fda_designations=fda_designations,
            crl_history=crl_history,
            clinical=clinical,
        )

    @classmethod
    def minimal(cls, ticker: str, drug_name: str = "") -> "AnalysisContext":
        """Create minimal context for testing."""
        return cls(ticker=ticker, drug_name=drug_name or ticker)


__all__ = [
    "CRLInfo",
    "AdComInfo",
    "ClinicalInfo",
    "ManufacturingInfo",
    "FDADesignations",
    "DisputeInfo",
    "EarningsCallInfo",
    "CitizenPetitionInfo",
    "AnalysisContext",
]
