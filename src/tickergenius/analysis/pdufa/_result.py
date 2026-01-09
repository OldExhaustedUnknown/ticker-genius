"""
Ticker-Genius Analysis Result
==============================
M3: Structured result for probability analysis.

Contains the final probability and complete factor breakdown
for transparency and debugging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from tickergenius.analysis.pdufa._registry import FactorResult


@dataclass
class LayerSummary:
    """Summary of factors applied in a single layer."""
    layer: str
    input_prob: float
    output_prob: float
    factors_applied: list[FactorResult]
    total_adjustment: float

    @property
    def factor_count(self) -> int:
        return len([f for f in self.factors_applied if f.applied])


@dataclass
class AnalysisResult:
    """
    Complete result of PDUFA probability analysis.

    Contains:
    - Final approval probability
    - Base rate used
    - All factor adjustments with explanations
    - Layer-by-layer breakdown
    - Metadata for audit trail
    """

    # Core results
    probability: float
    base_probability: float

    # Factor breakdown
    factors: list[FactorResult] = field(default_factory=list)
    layers: list[LayerSummary] = field(default_factory=list)

    # Metadata
    ticker: str = ""
    drug_name: str = ""
    analysis_version: str = "3.0"
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    # Confidence metrics
    confidence_score: float = 1.0
    data_quality_warnings: list[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------

    @property
    def total_adjustment(self) -> float:
        """Total adjustment from all factors."""
        return sum(f.adjustment for f in self.factors if f.applied)

    @property
    def applied_factors(self) -> list[FactorResult]:
        """Only factors that were actually applied."""
        return [f for f in self.factors if f.applied]

    @property
    def bonus_factors(self) -> list[FactorResult]:
        """Factors with positive adjustment."""
        return [f for f in self.applied_factors if f.adjustment > 0]

    @property
    def penalty_factors(self) -> list[FactorResult]:
        """Factors with negative adjustment."""
        return [f for f in self.applied_factors if f.adjustment < 0]

    @property
    def total_bonus(self) -> float:
        """Sum of all positive adjustments."""
        return sum(f.adjustment for f in self.bonus_factors)

    @property
    def total_penalty(self) -> float:
        """Sum of all negative adjustments (as positive number)."""
        return abs(sum(f.adjustment for f in self.penalty_factors))

    # -------------------------------------------------------------------------
    # Display Methods
    # -------------------------------------------------------------------------

    def summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"PDUFA Analysis: {self.ticker} ({self.drug_name})",
            f"=" * 50,
            f"Final Probability: {self.probability:.1%}",
            f"Base Rate: {self.base_probability:.1%}",
            f"Total Adjustment: {self.total_adjustment:+.1%}",
            f"  - Bonuses: +{self.total_bonus:.1%} ({len(self.bonus_factors)} factors)",
            f"  - Penalties: -{self.total_penalty:.1%} ({len(self.penalty_factors)} factors)",
        ]

        if self.data_quality_warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.data_quality_warnings:
                lines.append(f"  ! {warning}")

        return "\n".join(lines)

    def factor_table(self) -> str:
        """Get factor breakdown table."""
        lines = ["Factor Breakdown:", "-" * 60]

        for factor in self.applied_factors:
            adj_str = f"{factor.adjustment:+.1%}"
            lines.append(f"  {factor.name:30} {adj_str:>8}  {factor.reason}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "probability": self.probability,
            "base_probability": self.base_probability,
            "total_adjustment": self.total_adjustment,
            "ticker": self.ticker,
            "drug_name": self.drug_name,
            "analysis_version": self.analysis_version,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "confidence_score": self.confidence_score,
            "data_quality_warnings": self.data_quality_warnings,
            "factors": [
                {
                    "name": f.name,
                    "adjustment": f.adjustment,
                    "reason": f.reason,
                    "applied": f.applied,
                    "confidence": f.confidence,
                }
                for f in self.factors
            ],
            "summary": {
                "bonus_count": len(self.bonus_factors),
                "penalty_count": len(self.penalty_factors),
                "total_bonus": self.total_bonus,
                "total_penalty": self.total_penalty,
            },
        }


__all__ = ["LayerSummary", "AnalysisResult"]
