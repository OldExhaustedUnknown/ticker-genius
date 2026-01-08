"""
Ticker-Genius Pipeline Schemas
==============================
M1: Core pipeline and PDUFA event schemas.

Pipeline represents a drug's complete FDA journey including:
- Basic drug information
- PDUFA dates and history
- Clinical trial data
- Manufacturing status
- Approval probability
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional
from pydantic import Field

from tickergenius.schemas.base import (
    BaseSchema,
    VersionedSchema,
    StatusField,
    DataStatus,
)
from tickergenius.schemas.enums import (
    ApprovalType,
    CRLType,
    PAIStatus,
    DrugClassification,
    TimingSignal,
)


class PDUFAEvent(BaseSchema):
    """
    A single PDUFA date event.

    Represents one FDA decision date for a drug application.
    """
    pdufa_date: date
    is_confirmed: bool = False  # Official vs estimated date
    source: str = ""
    notes: str = ""

    # Historical tracking
    original_date: Optional[date] = None  # If date was moved
    delay_reason: Optional[str] = None


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
    "PDUFAEvent",
    "CRLDetail",
    "ApprovalProbability",
    "Pipeline",
    "PipelineSummary",
]
