"""
Ticker-Genius Schemas
=====================
M1: Pydantic v2 data models for the application.

Wave 2 Update (2026-01-10):
- StatusField: 5-state SearchStatus (FOUND/CONFIRMED_NONE/NOT_APPLICABLE/NOT_FOUND/NOT_SEARCHED)
- PDUFAEvent: 완전한 데이터 스키마 + 12개 신규 필드
- Price models: PriceHistory, PDUFAPriceWindow, TradingSignal

Modules:
- base: Core primitives (StatusField, BaseSchema)
- enums: All enumeration types (including SearchStatus, SourceTier)
- pipeline: Pipeline, PDUFAEvent, ApprovalProbability
- price_models: PriceHistory, PDUFAPriceWindow, TradingSignal
- clinical: ClinicalTrial, ClinicalEndpoint
- manufacturing: ManufacturingFacility, PAITracking
"""

# Base
from tickergenius.schemas.base import (
    DataStatus,
    SearchStatus,
    SourceTier,
    StatusField,
    BaseSchema,
    TimestampedSchema,
    VersionedSchema,
)

# Enums
from tickergenius.schemas.enums import (
    # Data Collection (Wave 2)
    SearchStatus,
    SourceTier,
    TrialRegion,
    CRLReasonType,
    # Core
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

# Pipeline (Wave 2 - includes nested models)
from tickergenius.schemas.pipeline import (
    FDADesignations,
    AdComInfo,
    Enrollment,
    PValue,
    CRLReason,
    PDUFAEvent,
    PDUFAEventLegacy,
    CRLDetail,
    ApprovalProbability,
    Pipeline,
    PipelineSummary,
)

# Price Models (Wave 2)
from tickergenius.schemas.price_models import (
    PricePoint,
    PriceHistory,
    PDUFAPriceWindow,
    TradingSignal,
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
    "SearchStatus",
    "SourceTier",
    "StatusField",
    "BaseSchema",
    "TimestampedSchema",
    "VersionedSchema",
    # Enums (Wave 2)
    "TrialRegion",
    "CRLReasonType",
    # Enums (Core)
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
    # Pipeline - Nested Models (Wave 2)
    "FDADesignations",
    "AdComInfo",
    "Enrollment",
    "PValue",
    "CRLReason",
    # Pipeline - Events
    "PDUFAEvent",
    "PDUFAEventLegacy",
    "CRLDetail",
    "ApprovalProbability",
    "Pipeline",
    "PipelineSummary",
    # Price Models (Wave 2)
    "PricePoint",
    "PriceHistory",
    "PDUFAPriceWindow",
    "TradingSignal",
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
