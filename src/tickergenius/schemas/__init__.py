# -*- coding: utf-8 -*-
"""
Ticker-Genius V4 Pydantic Schemas

TF 히스토리 반영:
- TF 46차: CRL Class/CMC-only 필드 정의
- TF 47차: program_status, 다중 CRL 처리
- TF 56차: 데이터 품질 이슈, 피처 분류
- TF 59차: CMC/Trial Design 피처
- TF 긴급회의: data_quality 필드, 플래깅 방식
"""

from .base import DataStatus, StatusField
from .pipeline import (
    Pipeline,
    TickerPipelines,
    PDUFAEvent,
    CRLDetail,
    CRLHistoryEntry,
    Application,
    FDADesignations,
    AdComInfo,
    LegalIssue,
    # Type literals
    DELAY_REASONS,
    SPECIAL_CIRCUMSTANCES,
    PENDING_STATUS,
)
from .manufacturing import (
    ManufacturingSite,
    FDA483,
    WarningLetter,
    ManufacturingInfo,
)
from .clinical import ClinicalTrial
from .data_quality import DataQuality, DataQualityIssue

__all__ = [
    # Base
    "DataStatus",
    "StatusField",
    # Pipeline
    "Pipeline",
    "TickerPipelines",
    "PDUFAEvent",
    "CRLDetail",
    "CRLHistoryEntry",
    "Application",
    "FDADesignations",
    "AdComInfo",
    "LegalIssue",
    "DELAY_REASONS",
    "SPECIAL_CIRCUMSTANCES",
    "PENDING_STATUS",
    # Manufacturing
    "ManufacturingSite",
    "FDA483",
    "WarningLetter",
    "ManufacturingInfo",
    # Clinical
    "ClinicalTrial",
    # Data Quality
    "DataQuality",
    "DataQualityIssue",
]
