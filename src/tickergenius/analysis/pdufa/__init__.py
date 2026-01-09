"""
Ticker-Genius PDUFA Analysis Module
====================================
M3: FDA approval probability analysis.

Public API:
    # Main analyzer
    from tickergenius.analysis.pdufa import PDUFAAnalyzer, analyze_pdufa

    # Context building
    from tickergenius.analysis.pdufa import AnalysisContext

    # Results
    from tickergenius.analysis.pdufa import AnalysisResult

Usage:
    # Quick analysis from Pipeline
    from tickergenius.analysis.pdufa import PDUFAAnalyzer, AnalysisContext

    context = AnalysisContext.from_pipeline(pipeline)
    analyzer = PDUFAAnalyzer()
    result = analyzer.analyze(context)

    print(f"Approval probability: {result.probability:.1%}")
    print(result.summary())

    # Direct analysis with minimal context
    context = AnalysisContext.minimal("TICKER")
    result = analyze_pdufa(context)
"""

# Import layers to register factors with FactorRegistry
# This must happen before using PDUFAAnalyzer
from tickergenius.analysis.pdufa import _layers  # noqa: F401

# Public API
from tickergenius.analysis.pdufa._context import (
    AnalysisContext,
    FDADesignations,
    AdComInfo,
    CRLInfo,
    ClinicalInfo,
    ManufacturingInfo,
    DisputeInfo,
    EarningsCallInfo,
    CitizenPetitionInfo,
)
from tickergenius.analysis.pdufa._result import AnalysisResult, LayerSummary
from tickergenius.analysis.pdufa._analyzer import PDUFAAnalyzer, analyze_pdufa
from tickergenius.analysis.pdufa._registry import (
    FactorRegistry,
    FactorResult,
    FactorStatus,
    FactorInfo,
)

__all__ = [
    # Main entry points
    "PDUFAAnalyzer",
    "analyze_pdufa",
    # Context
    "AnalysisContext",
    "FDADesignations",
    "AdComInfo",
    "CRLInfo",
    "ClinicalInfo",
    "ManufacturingInfo",
    "DisputeInfo",
    "EarningsCallInfo",
    "CitizenPetitionInfo",
    # Results
    "AnalysisResult",
    "LayerSummary",
    # Registry (for advanced usage)
    "FactorRegistry",
    "FactorResult",
    "FactorStatus",
    "FactorInfo",
]
