"""
Special Layer - Special Application Factors
============================================
Handles special application types and SPA factors.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="first_in_class",
    layer="special",
    order=10,
    version="1.0",
    description="First-in-Class 보너스",
)
def apply_first_in_class_bonus(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply bonus for first-in-class designation."""
    if not ctx.fda_designations.is_first_in_class:
        return FactorResult.neutral("first_in_class")

    factor = get_factor_adjustment("special", "first_in_class")
    if factor is None:
        return FactorResult.neutral("first_in_class", "팩터 정의 없음")

    return FactorResult.bonus(
        name="first_in_class",
        value=factor.score,
        reason=f"First-in-Class (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="supplement_application",
    layer="special",
    order=20,
    version="1.0",
    description="Supplement 신청 보너스",
)
def apply_supplement_bonus(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply bonus for supplement application (already approved drug)."""
    if not ctx.is_supplement:
        return FactorResult.neutral("supplement_application")

    factor = get_factor_adjustment("special", "supplement")
    if factor is None:
        return FactorResult.neutral("supplement_application", "팩터 정의 없음")

    return FactorResult.bonus(
        name="supplement_application",
        value=factor.score,
        reason=f"Supplement 신청 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="spa_agreed",
    layer="special",
    order=30,
    version="1.0",
    description="SPA 합의 보너스",
)
def apply_spa_agreed_bonus(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply bonus for Special Protocol Assessment agreement."""
    # SPA rescinded takes precedence
    if ctx.spa_rescinded:
        return FactorResult.neutral("spa_agreed", "SPA 철회됨")

    if not ctx.spa_agreed:
        return FactorResult.neutral("spa_agreed")

    factor = get_factor_adjustment("special", "spa_agreed")
    if factor is None:
        return FactorResult.neutral("spa_agreed", "팩터 정의 없음")

    return FactorResult.bonus(
        name="spa_agreed",
        value=factor.score,
        reason=f"SPA 합의 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="spa_rescinded",
    layer="special",
    order=40,
    version="1.0",
    description="SPA 철회 페널티",
)
def apply_spa_rescinded_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply penalty for SPA rescinded."""
    if not ctx.spa_rescinded:
        return FactorResult.neutral("spa_rescinded")

    factor = get_factor_adjustment("special", "spa_rescinded")
    if factor is None:
        return FactorResult.neutral("spa_rescinded", "팩터 정의 없음")

    return FactorResult.penalty(
        name="spa_rescinded",
        value=factor.score,
        reason=f"SPA 철회 ({factor.score:.0%})",
    )
