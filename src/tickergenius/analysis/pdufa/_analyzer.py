"""
Ticker-Genius PDUFA Analyzer
=============================
M3: Main facade for PDUFA probability analysis.

This is the single entry point for probability calculation.
Uses FactorRegistry with layer-based calculation.

Usage:
    analyzer = PDUFAAnalyzer()
    result = analyzer.analyze(context)
    print(f"Approval probability: {result.probability:.1%}")
"""

from __future__ import annotations

import logging
from typing import Optional

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.analysis.pdufa._result import AnalysisResult, LayerSummary
from tickergenius.analysis.pdufa._layers import LAYER_ORDER


logger = logging.getLogger(__name__)


class PDUFAAnalyzer:
    """
    Main PDUFA probability analyzer.

    Coordinates factor calculation across all layers using FactorRegistry.

    Design:
    - Facade pattern: Single entry point, hides complexity
    - Strategy pattern: Layers can be customized per analysis
    - Open-Closed: New factors added via registration, not code changes
    """

    def __init__(
        self,
        layer_order: Optional[list[str]] = None,
        skip_layers: Optional[list[str]] = None,
    ):
        """
        Initialize analyzer.

        Args:
            layer_order: Custom layer order (default: LAYER_ORDER)
            skip_layers: Layers to skip (for testing/debugging)
        """
        self._layer_order = layer_order or LAYER_ORDER
        self._skip_layers = set(skip_layers or [])

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """
        Perform full PDUFA probability analysis.

        Args:
            context: Analysis context with all input data

        Returns:
            AnalysisResult with probability and factor breakdown
        """
        logger.info(f"Starting analysis for {context.ticker}")

        all_factors: list[FactorResult] = []
        layer_summaries: list[LayerSummary] = []
        warnings: list[str] = []

        # Apply layers in order
        current_prob = 0.0  # Will be set by base layer
        base_prob = 0.0

        for layer in self._layer_order:
            if layer in self._skip_layers:
                logger.debug(f"Skipping layer: {layer}")
                continue

            input_prob = current_prob

            try:
                new_prob, layer_factors = FactorRegistry.apply_layer(
                    layer, context, current_prob
                )
            except Exception as e:
                logger.error(f"Error in layer {layer}: {e}")
                warnings.append(f"Layer {layer} error: {e}")
                layer_factors = []
                new_prob = current_prob

            all_factors.extend(layer_factors)

            # Track base probability from base layer
            if layer == "base":
                base_prob = new_prob

            # Create layer summary
            total_adj = sum(f.adjustment for f in layer_factors if f.applied)
            layer_summaries.append(
                LayerSummary(
                    layer=layer,
                    input_prob=input_prob,
                    output_prob=new_prob,
                    factors_applied=layer_factors,
                    total_adjustment=total_adj,
                )
            )

            current_prob = new_prob
            logger.debug(f"Layer {layer}: {input_prob:.1%} -> {new_prob:.1%}")

        # Calculate confidence score
        confidence, confidence_warnings = self._calculate_confidence(
            context, all_factors
        )
        warnings.extend(confidence_warnings)

        # Build result
        result = AnalysisResult(
            probability=current_prob,
            base_probability=base_prob,
            factors=all_factors,
            layers=layer_summaries,
            ticker=context.ticker,
            drug_name=context.drug_name,
            confidence_score=confidence,
            data_quality_warnings=warnings,
        )

        logger.info(f"Analysis complete: {result.probability:.1%} (confidence: {confidence:.2f})")
        return result

    def analyze_quick(self, context: AnalysisContext) -> float:
        """
        Quick analysis - returns just the probability.

        Args:
            context: Analysis context

        Returns:
            Approval probability as float
        """
        result = self.analyze(context)
        return result.probability

    def analyze_with_scenarios(
        self,
        context: AnalysisContext,
        scenarios: dict[str, AnalysisContext],
    ) -> dict[str, AnalysisResult]:
        """
        Analyze multiple scenarios.

        Args:
            context: Base context (analyzed as "base")
            scenarios: Named scenario contexts

        Returns:
            Dict of scenario name -> result
        """
        results = {"base": self.analyze(context)}

        for name, scenario_ctx in scenarios.items():
            results[name] = self.analyze(scenario_ctx)

        return results

    # -------------------------------------------------------------------------
    # Confidence Calculation
    # -------------------------------------------------------------------------

    def _calculate_confidence(
        self,
        context: AnalysisContext,
        factors: list[FactorResult],
    ) -> tuple[float, list[str]]:
        """
        Calculate confidence score based on data quality.

        Confidence is based on:
        1. Data completeness (key fields filled)
        2. Data recency (dates not stale)
        3. Factor confidence (weighted average)

        Returns:
            Tuple of (confidence_score 0-1, list of warnings)
        """
        warnings: list[str] = []
        confidence = 1.0

        # 1. Data Completeness Check (40% weight)
        completeness_score = self._check_data_completeness(context)
        if completeness_score < 0.5:
            warnings.append(f"데이터 불완전: {completeness_score:.0%}")
        confidence_from_completeness = 0.4 * completeness_score

        # 2. Data Recency Check (30% weight)
        recency_score, recency_warnings = self._check_data_recency(context)
        warnings.extend(recency_warnings)
        confidence_from_recency = 0.3 * recency_score

        # 3. Factor Confidence Check (30% weight)
        if factors:
            applied_factors = [f for f in factors if f.applied]
            if applied_factors:
                avg_factor_conf = sum(f.confidence for f in applied_factors) / len(applied_factors)
            else:
                avg_factor_conf = 1.0
        else:
            avg_factor_conf = 1.0
        confidence_from_factors = 0.3 * avg_factor_conf

        confidence = confidence_from_completeness + confidence_from_recency + confidence_from_factors

        # Clamp to [0.1, 1.0]
        confidence = max(0.1, min(1.0, confidence))

        return confidence, warnings

    def _check_data_completeness(self, context: AnalysisContext) -> float:
        """Check how complete the input data is."""
        fields_checked = 0
        fields_filled = 0

        # Key fields to check
        checks = [
            # Basic info
            (context.ticker, "ticker"),
            (context.drug_name, "drug_name"),
            (context.pdufa_date, "pdufa_date"),
            # Clinical
            (context.clinical.primary_endpoint_met is not None, "primary_endpoint_met"),
            (context.clinical.phase, "phase"),
            # FDA designations - at least one should be known
            (context.fda_designations.count() > 0 or True, "fda_designations"),  # Optional
            # AdCom - if held, should have vote ratio
            (not context.adcom.was_held or context.adcom.vote_ratio is not None, "adcom_vote"),
            # Manufacturing - PAI status known
            (context.manufacturing.pai_status is not None or context.manufacturing.pai_passed, "pai_status"),
        ]

        for is_filled, name in checks:
            fields_checked += 1
            if is_filled:
                fields_filled += 1

        return fields_filled / fields_checked if fields_checked > 0 else 1.0

    def _check_data_recency(self, context: AnalysisContext) -> tuple[float, list[str]]:
        """Check if date-dependent data is fresh."""
        warnings = []
        recency_score = 1.0

        # Check PDUFA date
        if context.pdufa_date:
            days_to_pdufa = context.days_to_pdufa
            if days_to_pdufa and days_to_pdufa < 0:
                # PDUFA date has passed
                warnings.append("PDUFA 날짜 경과")
                recency_score *= 0.5

        # Check AdCom date if held
        if context.adcom.was_held and context.adcom.adcom_date:
            days_since = context.days_since_adcom
            if days_since and days_since > 180:
                warnings.append(f"AdCom {days_since}일 전 (오래됨)")
                recency_score *= 0.9

        # Check manufacturing dates
        if context.manufacturing.has_warning_letter:
            if not context.manufacturing.warning_letter_date:
                warnings.append("Warning Letter 날짜 미확인")
                recency_score *= 0.9

        return recency_score, warnings

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def list_registered_factors(self) -> list[str]:
        """List all registered factors."""
        return [f.name for f in FactorRegistry.list_factors()]

    def get_factor_info(self, name: str) -> Optional[dict]:
        """Get detailed info about a factor."""
        info = FactorRegistry.get(name)
        if info is None:
            return None

        return {
            "name": info.name,
            "layer": info.layer,
            "order": info.order,
            "version": info.version,
            "status": info.status.value,
            "description": info.description,
        }

    def simulate_factor(
        self,
        context: AnalysisContext,
        factor_name: str,
        current_prob: float = 0.70,
    ) -> Optional[FactorResult]:
        """
        Simulate a single factor application.

        Useful for debugging/testing individual factors.
        """
        info = FactorRegistry.get(factor_name)
        if info is None:
            return None

        return info.func(context, current_prob)


# =============================================================================
# Module-level convenience function
# =============================================================================

def analyze_pdufa(context: AnalysisContext) -> AnalysisResult:
    """
    Analyze PDUFA probability (convenience function).

    Args:
        context: Analysis context

    Returns:
        AnalysisResult
    """
    analyzer = PDUFAAnalyzer()
    return analyzer.analyze(context)


__all__ = ["PDUFAAnalyzer", "analyze_pdufa"]
