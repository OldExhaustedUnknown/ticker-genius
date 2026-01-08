"""
Ticker-Genius Manufacturing Schemas
===================================
M1: Manufacturing and PAI (Pre-Approval Inspection) schemas.

Manufacturing/CMC issues account for ~50% of CRLs.
PAI status is critical for approval prediction.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import Field

from tickergenius.schemas.base import BaseSchema, StatusField
from tickergenius.schemas.enums import PAIStatus


class ManufacturingFacility(BaseSchema):
    """
    Manufacturing facility information.

    Tracks facility status for PAI tracking.
    """
    facility_name: str
    location: str = ""  # City, Country
    facility_type: str = ""  # In-house, CDMO, etc.

    # FDA inspection history
    last_inspection_date: Optional[date] = None
    inspection_result: Optional[str] = None  # NAI, VAI, OAI
    form_483_issued: bool = False
    warning_letter: bool = False

    # PAI status
    pai_status: PAIStatus = PAIStatus.PENDING
    pai_scheduled_date: Optional[date] = None
    pai_completed_date: Optional[date] = None

    # Risk assessment
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_factors: list[str] = Field(default_factory=list)


class CMCAssessment(BaseSchema):
    """
    Chemistry, Manufacturing, and Controls assessment.

    CMC issues are a major source of CRLs.
    """
    ticker: str
    drug_name: str

    # Facility info
    facilities: list[ManufacturingFacility] = Field(default_factory=list)
    primary_facility: Optional[str] = None

    # Process status
    process_validated: StatusField[bool] = Field(default_factory=StatusField.unknown)
    scale_up_complete: StatusField[bool] = Field(default_factory=StatusField.unknown)
    stability_data_complete: StatusField[bool] = Field(default_factory=StatusField.unknown)

    # Risk factors
    uses_cdmo: bool = False  # Third-party manufacturing
    multiple_sites: bool = False
    complex_molecule: bool = False  # Biologics, etc.

    # Overall assessment
    cmc_risk_level: str = "medium"  # low, medium, high
    cmc_risk_factors: list[str] = Field(default_factory=list)
    estimated_cmc_crl_probability: float = Field(default=0.0, ge=0.0, le=1.0)


class PAITracking(BaseSchema):
    """
    Pre-Approval Inspection tracking.

    PAI is required before FDA approval. Failure = CRL.
    """
    ticker: str
    drug_name: str

    # Current status
    pai_status: PAIStatus = PAIStatus.PENDING

    # Timeline
    pai_request_date: Optional[date] = None
    pai_scheduled_date: Optional[date] = None
    pai_completed_date: Optional[date] = None

    # Results
    pai_result: Optional[str] = None  # Passed, Failed, Pending
    observations: list[str] = Field(default_factory=list)
    form_483_observations: int = 0

    # Impact on approval
    blocks_approval: bool = False
    remediation_required: bool = False
    estimated_remediation_months: Optional[int] = None

    def is_complete(self) -> bool:
        """Check if PAI is complete (passed or failed)."""
        return self.pai_status in [PAIStatus.PASSED, PAIStatus.FAILED]

    def is_blocking(self) -> bool:
        """Check if PAI is blocking approval."""
        return self.pai_status == PAIStatus.FAILED or self.blocks_approval


__all__ = [
    "ManufacturingFacility",
    "CMCAssessment",
    "PAITracking",
]
