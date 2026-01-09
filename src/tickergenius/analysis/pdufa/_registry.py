"""
Ticker-Genius Factor Registry
==============================
M3: Open-Closed principle for factor management.

FactorRegistry allows adding, removing, and disabling factors dynamically
without modifying the core calculation logic.

Design Principles:
1. Open-Closed: Open for extension, closed for modification
2. Plugin-like: Factors register themselves
3. Order-preserving: Factors applied in defined order
4. Lifecycle-aware: Factors can be deprecated/disabled

Usage:
    @FactorRegistry.register("btd_bonus", layer="designation", order=10)
    def apply_btd_bonus(ctx: AnalysisContext, prob: float) -> FactorResult:
        if ctx.fda_designations.breakthrough_therapy:
            return FactorResult("btd_bonus", 0.08, "Breakthrough Therapy 지정")
        return FactorResult.neutral("btd_bonus")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from enum import Enum
import logging

from tickergenius.analysis.pdufa._context import AnalysisContext


logger = logging.getLogger(__name__)


# =============================================================================
# Factor Result
# =============================================================================

@dataclass
class FactorResult:
    """
    Result of applying a single factor.

    Contains the adjustment value and explanation for transparency.
    """
    name: str
    adjustment: float
    reason: str = ""
    confidence: float = 1.0
    applied: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def neutral(cls, name: str, reason: str = "") -> "FactorResult":
        """Create a neutral (no effect) result."""
        return cls(name=name, adjustment=0.0, reason=reason or "조건 미충족", applied=False)

    @classmethod
    def bonus(cls, name: str, value: float, reason: str) -> "FactorResult":
        """Create a bonus (positive) result."""
        return cls(name=name, adjustment=abs(value), reason=reason)

    @classmethod
    def penalty(cls, name: str, value: float, reason: str) -> "FactorResult":
        """Create a penalty (negative) result."""
        return cls(name=name, adjustment=-abs(value), reason=reason)


# =============================================================================
# Factor Status
# =============================================================================

class FactorStatus(str, Enum):
    """Factor lifecycle status."""
    ACTIVE = "ACTIVE"           # Normal operation
    DEPRECATED = "DEPRECATED"   # Will be removed, use with warning
    DISABLED = "DISABLED"       # Temporarily disabled
    REMOVED = "REMOVED"         # No longer available


class FactorGroupType(str, Enum):
    """Factor group aggregation type."""
    INDEPENDENT = "independent"  # All factors apply (default)
    EXCLUSIVE = "exclusive"      # First matching factor only
    MAX_ONLY = "max_only"        # Only highest adjustment in group


# =============================================================================
# Factor Info
# =============================================================================

@dataclass
class FactorInfo:
    """Information about a registered factor."""
    name: str
    layer: str
    order: int
    version: str
    func: Callable[[AnalysisContext, float], FactorResult]
    status: FactorStatus = FactorStatus.ACTIVE
    description: str = ""
    deprecated_reason: str = ""
    group: Optional[str] = None  # Group name (e.g., "fda_designation")
    group_type: FactorGroupType = FactorGroupType.INDEPENDENT

    def is_active(self) -> bool:
        """Check if factor is active."""
        return self.status == FactorStatus.ACTIVE

    def should_apply(self) -> bool:
        """Check if factor should be applied."""
        return self.status in (FactorStatus.ACTIVE, FactorStatus.DEPRECATED)


# =============================================================================
# Factor Registry
# =============================================================================

class FactorRegistry:
    """
    Central registry for all probability adjustment factors.

    Implements the Open-Closed principle: you can add new factors
    without modifying existing code.

    Thread-safe for reads, not for writes (assumes factors are
    registered at startup).
    """

    _factors: dict[str, FactorInfo] = {}
    _layers: dict[str, list[str]] = {}  # layer -> factor names (ordered)
    _initialized: bool = False

    @classmethod
    def register(
        cls,
        name: str,
        layer: str,
        order: int,
        version: str = "1.0",
        description: str = "",
        group: Optional[str] = None,
        group_type: FactorGroupType = FactorGroupType.INDEPENDENT,
    ) -> Callable:
        """
        Decorator to register a factor function.

        Args:
            name: Unique factor name
            layer: Layer name (base, designation, adcom, crl, clinical, etc.)
            order: Order within layer (lower = earlier)
            version: Factor version for tracking
            description: Human-readable description
            group: Optional group name for aggregation
            group_type: How to aggregate factors in same group

        Group Types:
            - INDEPENDENT: All factors apply (default)
            - EXCLUSIVE: First matching factor only
            - MAX_ONLY: Only highest adjustment in group

        Usage:
            @FactorRegistry.register(
                "btd_bonus", layer="designation", order=10,
                group="fda_designation", group_type=FactorGroupType.MAX_ONLY
            )
            def apply_btd(ctx, prob):
                ...
        """
        def decorator(func: Callable[[AnalysisContext, float], FactorResult]):
            info = FactorInfo(
                name=name,
                layer=layer,
                order=order,
                version=version,
                func=func,
                description=description,
                group=group,
                group_type=group_type,
            )
            cls._factors[name] = info

            # Add to layer
            if layer not in cls._layers:
                cls._layers[layer] = []
            cls._layers[layer].append(name)

            # Sort layer by order
            cls._layers[layer].sort(key=lambda n: cls._factors[n].order)

            return func

        return decorator

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Remove a factor from registry."""
        if name not in cls._factors:
            return False

        info = cls._factors[name]
        layer = info.layer

        # Remove from layer
        if layer in cls._layers and name in cls._layers[layer]:
            cls._layers[layer].remove(name)

        # Remove from factors
        del cls._factors[name]
        return True

    @classmethod
    def disable(cls, name: str, reason: str = "") -> bool:
        """Temporarily disable a factor."""
        if name not in cls._factors:
            return False

        # Create new FactorInfo with disabled status
        old = cls._factors[name]
        cls._factors[name] = FactorInfo(
            name=old.name,
            layer=old.layer,
            order=old.order,
            version=old.version,
            func=old.func,
            status=FactorStatus.DISABLED,
            description=old.description,
            deprecated_reason=reason,
        )
        return True

    @classmethod
    def enable(cls, name: str) -> bool:
        """Re-enable a disabled factor."""
        if name not in cls._factors:
            return False

        old = cls._factors[name]
        if old.status != FactorStatus.DISABLED:
            return False

        cls._factors[name] = FactorInfo(
            name=old.name,
            layer=old.layer,
            order=old.order,
            version=old.version,
            func=old.func,
            status=FactorStatus.ACTIVE,
            description=old.description,
        )
        return True

    @classmethod
    def deprecate(cls, name: str, reason: str) -> bool:
        """Mark a factor as deprecated."""
        if name not in cls._factors:
            return False

        old = cls._factors[name]
        cls._factors[name] = FactorInfo(
            name=old.name,
            layer=old.layer,
            order=old.order,
            version=old.version,
            func=old.func,
            status=FactorStatus.DEPRECATED,
            description=old.description,
            deprecated_reason=reason,
        )
        logger.warning(f"Factor '{name}' deprecated: {reason}")
        return True

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    @classmethod
    def get(cls, name: str) -> Optional[FactorInfo]:
        """Get factor info by name."""
        return cls._factors.get(name)

    @classmethod
    def get_layer_factors(cls, layer: str) -> list[FactorInfo]:
        """Get all factors in a layer (ordered)."""
        names = cls._layers.get(layer, [])
        return [cls._factors[n] for n in names if cls._factors[n].should_apply()]

    @classmethod
    def get_all_layers(cls) -> list[str]:
        """Get all layer names."""
        return list(cls._layers.keys())

    @classmethod
    def list_factors(cls, active_only: bool = True) -> list[FactorInfo]:
        """List all registered factors."""
        factors = list(cls._factors.values())
        if active_only:
            factors = [f for f in factors if f.should_apply()]
        return sorted(factors, key=lambda f: (f.layer, f.order))

    @classmethod
    def count(cls) -> int:
        """Count registered factors."""
        return len(cls._factors)

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    @classmethod
    def apply_layer(
        cls,
        layer: str,
        context: AnalysisContext,
        current_probability: float,
    ) -> tuple[float, list[FactorResult]]:
        """
        Apply all factors in a layer with group handling.

        Args:
            layer: Layer name
            context: Analysis context
            current_probability: Current probability before layer

        Returns:
            (new_probability, list of results)

        Group Handling:
            - INDEPENDENT: All factors apply normally
            - EXCLUSIVE: First matching factor in group wins
            - MAX_ONLY: Only highest adjustment in group applies
        """
        factors = cls.get_layer_factors(layer)
        results = []
        prob = current_probability

        # Group factors by group name
        group_results: dict[str, list[FactorResult]] = {}
        ungrouped_results: list[FactorResult] = []

        for factor in factors:
            if factor.status == FactorStatus.DEPRECATED:
                logger.warning(f"Using deprecated factor: {factor.name}")

            try:
                result = factor.func(context, prob)

                if factor.group:
                    # Grouped factor
                    if factor.group not in group_results:
                        group_results[factor.group] = []
                    group_results[factor.group].append((factor, result))
                else:
                    # Ungrouped factor - apply immediately
                    ungrouped_results.append(result)
                    results.append(result)
                    if result.applied:
                        prob += result.adjustment

            except Exception as e:
                logger.error(f"Error applying factor '{factor.name}': {e}")
                err_result = FactorResult.neutral(factor.name, f"Error: {e}")
                results.append(err_result)

        # Process grouped factors
        for group_name, group_factor_results in group_results.items():
            applied_results = [(f, r) for f, r in group_factor_results if r.applied]

            if not applied_results:
                # No factors matched - add all as neutral
                for factor, result in group_factor_results:
                    results.append(result)
                continue

            # Determine group type from first factor
            group_type = group_factor_results[0][0].group_type

            if group_type == FactorGroupType.EXCLUSIVE:
                # Only first matching factor
                chosen_factor, chosen_result = applied_results[0]
                prob += chosen_result.adjustment
                results.append(chosen_result)

                # Mark others as skipped
                for factor, result in group_factor_results:
                    if factor.name != chosen_factor.name:
                        skipped = FactorResult.neutral(
                            factor.name,
                            f"그룹 배타 ({chosen_factor.name} 적용됨)"
                        )
                        results.append(skipped)

            elif group_type == FactorGroupType.MAX_ONLY:
                # Only highest adjustment
                max_factor, max_result = max(
                    applied_results,
                    key=lambda x: abs(x[1].adjustment)
                )
                prob += max_result.adjustment
                results.append(max_result)

                # Mark others as skipped
                for factor, result in group_factor_results:
                    if factor.name != max_factor.name:
                        if result.applied:
                            skipped = FactorResult.neutral(
                                factor.name,
                                f"그룹 최대값 ({max_factor.name}={max_result.adjustment:+.0%} 적용)"
                            )
                        else:
                            skipped = result
                        results.append(skipped)

            else:  # INDEPENDENT
                # All apply
                for factor, result in group_factor_results:
                    results.append(result)
                    if result.applied:
                        prob += result.adjustment

        return prob, results

    @classmethod
    def apply_all(
        cls,
        context: AnalysisContext,
        initial_probability: float,
        layer_order: Optional[list[str]] = None,
    ) -> tuple[float, list[FactorResult]]:
        """
        Apply all factors in order.

        Args:
            context: Analysis context
            initial_probability: Starting probability
            layer_order: Custom layer order (default: alphabetical)

        Returns:
            (final_probability, all results)
        """
        if layer_order is None:
            layer_order = sorted(cls.get_all_layers())

        all_results = []
        prob = initial_probability

        for layer in layer_order:
            prob, results = cls.apply_layer(layer, context, prob)
            all_results.extend(results)

        return prob, all_results

    # -------------------------------------------------------------------------
    # Reset (for testing)
    # -------------------------------------------------------------------------

    @classmethod
    def reset(cls) -> None:
        """Reset registry (for testing)."""
        cls._factors.clear()
        cls._layers.clear()
        cls._initialized = False


__all__ = [
    "FactorResult",
    "FactorStatus",
    "FactorGroupType",
    "FactorInfo",
    "FactorRegistry",
]
