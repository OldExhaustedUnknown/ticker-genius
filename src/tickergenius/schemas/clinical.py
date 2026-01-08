"""
Ticker-Genius Clinical Trial Schemas
====================================
M1: Clinical trial data schemas.

Represents clinical trial information from ClinicalTrials.gov
and related FDA analysis data.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import Field

from tickergenius.schemas.base import BaseSchema, StatusField
from tickergenius.schemas.enums import (
    EndpointType,
    ClinicalQualityTier,
    MentalHealthIndication,
)


class ClinicalEndpoint(BaseSchema):
    """Clinical trial endpoint definition."""
    name: str
    endpoint_type: EndpointType
    is_primary: bool = False
    description: str = ""

    # Results (if available)
    result_value: Optional[float] = None
    p_value: Optional[float] = None
    met_endpoint: Optional[bool] = None


class ClinicalTrial(BaseSchema):
    """
    Clinical trial information.

    Represents a single clinical trial with endpoints and results.
    """
    # Identifiers
    nct_id: str  # ClinicalTrials.gov ID (e.g., NCT12345678)
    ticker: Optional[str] = None
    drug_name: str = ""

    # Trial info
    title: str = ""
    phase: str = ""  # Phase 1, Phase 2, Phase 3, etc.
    status: str = ""  # Recruiting, Completed, etc.

    # Indication
    indication: str = ""
    therapeutic_area: str = ""
    is_mental_health: bool = False
    mental_health_type: Optional[MentalHealthIndication] = None

    # Enrollment
    enrollment: Optional[int] = None
    enrollment_target: Optional[int] = None

    # Dates
    start_date: Optional[date] = None
    primary_completion_date: Optional[date] = None
    completion_date: Optional[date] = None

    # Endpoints
    endpoints: list[ClinicalEndpoint] = Field(default_factory=list)
    primary_endpoint_met: StatusField[bool] = Field(default_factory=StatusField.unknown)

    # Quality assessment
    quality_tier: Optional[ClinicalQualityTier] = None

    # Sponsor
    sponsor: str = ""
    collaborators: list[str] = Field(default_factory=list)

    def get_primary_endpoint(self) -> Optional[ClinicalEndpoint]:
        """Get the primary endpoint if exists."""
        for ep in self.endpoints:
            if ep.is_primary:
                return ep
        return None


class ClinicalQualityScore(BaseSchema):
    """
    Clinical trial quality assessment.

    Based on FDA reviewer perspective (TF 6차 토론).
    """
    # P-value assessment
    p_value: Optional[float] = None
    p_value_tier: Optional[ClinicalQualityTier] = None

    # Sample size assessment
    sample_size: Optional[int] = None
    sample_tier: Optional[ClinicalQualityTier] = None

    # Effect size assessment
    effect_size: Optional[float] = None
    effect_tier: Optional[ClinicalQualityTier] = None

    # Overall score
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Concerns
    concerns: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)


class TrialComparison(BaseSchema):
    """
    Comparison of multiple trials for same drug/indication.

    Used when there are multiple Phase 3 trials.
    """
    ticker: str
    drug_name: str
    indication: str

    trials: list[ClinicalTrial] = Field(default_factory=list)

    # Aggregated assessment
    consistent_results: bool = False
    overall_success: StatusField[bool] = Field(default_factory=StatusField.unknown)
    notes: str = ""


__all__ = [
    "ClinicalEndpoint",
    "ClinicalTrial",
    "ClinicalQualityScore",
    "TrialComparison",
]
