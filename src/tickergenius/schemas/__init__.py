"""
Ticker-Genius Schemas
=====================
M1: Pydantic v2 data models for the application.

This module provides all data schemas used throughout the application.
All schemas use Pydantic v2 and follow these conventions:

1. StatusField for uncertain/missing data (3-state: CONFIRMED/EMPTY/UNKNOWN)
2. Immutable where possible (frozen=True)
3. Clear validation rules with Field constraints
4. Type hints for all fields

Modules:
- base: Core primitives (StatusField, BaseSchema)
- enums: All enumeration types
- pipeline: Pipeline, PDUFAEvent, ApprovalProbability
- clinical: ClinicalTrial, ClinicalEndpoint
- manufacturing: ManufacturingFacility, PAITracking
"""

# Base
from tickergenius.schemas.base import (
    DataStatus,
    StatusField,
    BaseSchema,
    TimestampedSchema,
    VersionedSchema,
)

# Enums
from tickergenius.schemas.enums import (
    TimingSignal,
    StrategyType,
    CRLType,
    CRLDelayCategory,
    DisputeResolutionResult,
    EndpointType,
    ClinicalQualityTier,
    MentalHealthIndication,
    PAIStatus,
    DrugClassification,
    ApprovalType,
    DrugType,
    MarketSize,
    CitizenPetitionTiming,
    CitizenPetitionQuality,
    CitizenPetitionFDAResponse,
)

# Pipeline
from tickergenius.schemas.pipeline import (
    PDUFAEvent,
    CRLDetail,
    ApprovalProbability,
    Pipeline,
    PipelineSummary,
)

# Clinical
from tickergenius.schemas.clinical import (
    ClinicalEndpoint,
    ClinicalTrial,
    ClinicalQualityScore,
    TrialComparison,
)

# Manufacturing
from tickergenius.schemas.manufacturing import (
    ManufacturingFacility,
    CMCAssessment,
    PAITracking,
)

__all__ = [
    # Base
    "DataStatus",
    "StatusField",
    "BaseSchema",
    "TimestampedSchema",
    "VersionedSchema",
    # Enums
    "TimingSignal",
    "StrategyType",
    "CRLType",
    "CRLDelayCategory",
    "DisputeResolutionResult",
    "EndpointType",
    "ClinicalQualityTier",
    "MentalHealthIndication",
    "PAIStatus",
    "DrugClassification",
    "ApprovalType",
    "DrugType",
    "MarketSize",
    "CitizenPetitionTiming",
    "CitizenPetitionQuality",
    "CitizenPetitionFDAResponse",
    # Pipeline
    "PDUFAEvent",
    "CRLDetail",
    "ApprovalProbability",
    "Pipeline",
    "PipelineSummary",
    # Clinical
    "ClinicalEndpoint",
    "ClinicalTrial",
    "ClinicalQualityScore",
    "TrialComparison",
    # Manufacturing
    "ManufacturingFacility",
    "CMCAssessment",
    "PAITracking",
]
