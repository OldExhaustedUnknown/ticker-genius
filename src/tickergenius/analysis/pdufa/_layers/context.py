"""
Context Layer - Factor Interaction Effects
==========================================
Handles special effects when multiple factors are present together.

This layer runs AFTER individual factor layers but BEFORE cap layer.
It applies modifiers based on factor combinations.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult


# Context interaction definitions
# Each interaction has:
#   - conditions: Required factors (all must be present)
#   - min_count: Minimum number of conditions to match
#   - effect: "penalty_reduction" or "bonus"
#   - value: Effect magnitude (e.g., 0.75 = 75% penalty reduction)
CONTEXT_INTERACTIONS = {
    "strong_designation_combo": {
        "description": "BTD + Orphan + First-in-Class 조합",
        "conditions": ["breakthrough_therapy", "orphan_drug", "first_in_class"],
        "min_count": 3,
        "effect": "penalty_reduction",
        "value": 0.75,  # Penalties reduced by 75%
    },
    "clinical_support_combo": {
        "description": "SPA + AdCom 긍정 조합",
        "conditions": ["spa_agreed", "adcom_positive"],
        "min_count": 2,
        "effect": "bonus",
        "value": 0.03,  # Additional 3% bonus
    },
    "manufacturing_risk_combo": {
        "description": "Warning Letter + High Risk CDMO 조합",
        "conditions": ["warning_letter", "high_risk_cdmo"],
        "min_count": 2,
        "effect": "penalty_amplification",
        "value": 1.25,  # Penalties amplified by 25%
    },
}


def _check_conditions(ctx: AnalysisContext, conditions: list[str]) -> int:
    """Check how many conditions are met."""
    count = 0
    for condition in conditions:
        if condition == "breakthrough_therapy":
            count += ctx.fda_designations.breakthrough_therapy
        elif condition == "orphan_drug":
            count += ctx.fda_designations.orphan_drug
        elif condition == "first_in_class":
            count += ctx.fda_designations.is_first_in_class
        elif condition == "spa_agreed":
            count += ctx.spa_agreed and not ctx.spa_rescinded
        elif condition == "adcom_positive":
            count += ctx.adcom_vote_positive
        elif condition == "warning_letter":
            count += ctx.manufacturing.has_warning_letter
        elif condition == "high_risk_cdmo":
            count += ctx.manufacturing.is_high_risk_cdmo
    return count


@FactorRegistry.register(
    name="context_strong_designation",
    layer="context",
    order=10,
    version="1.0",
    description="강력한 지정 조합 보너스",
)
def apply_strong_designation_interaction(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply bonus for strong designation combination.

    BTD + Orphan + First-in-Class → Reduces negative factors by 75%
    """
    interaction = CONTEXT_INTERACTIONS["strong_designation_combo"]
    count = _check_conditions(ctx, interaction["conditions"])

    if count < interaction["min_count"]:
        return FactorResult.neutral("context_strong_designation")

    # This is a conceptual effect - in practice, it modifies how we interpret
    # the total probability rather than adding a direct bonus
    # For now, we add a small bonus to represent the positive synergy
    bonus = 0.05  # 5% synergy bonus for having all three

    return FactorResult.bonus(
        name="context_strong_designation",
        value=bonus,
        reason=f"강력한 지정 조합 보너스 (+{bonus:.0%})",
    )


@FactorRegistry.register(
    name="context_clinical_support",
    layer="context",
    order=20,
    version="1.0",
    description="임상 지원 조합 보너스",
)
def apply_clinical_support_interaction(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply bonus for clinical support combination.

    SPA agreed + AdCom positive → Additional confidence bonus
    """
    interaction = CONTEXT_INTERACTIONS["clinical_support_combo"]
    count = _check_conditions(ctx, interaction["conditions"])

    if count < interaction["min_count"]:
        return FactorResult.neutral("context_clinical_support")

    bonus = interaction["value"]

    return FactorResult.bonus(
        name="context_clinical_support",
        value=bonus,
        reason=f"SPA + AdCom 긍정 조합 (+{bonus:.0%})",
    )


@FactorRegistry.register(
    name="context_manufacturing_risk",
    layer="context",
    order=30,
    version="1.0",
    description="제조 리스크 조합 페널티",
)
def apply_manufacturing_risk_interaction(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply additional penalty for manufacturing risk combination.

    Warning Letter + High Risk CDMO → Amplified risk
    """
    interaction = CONTEXT_INTERACTIONS["manufacturing_risk_combo"]
    count = _check_conditions(ctx, interaction["conditions"])

    if count < interaction["min_count"]:
        return FactorResult.neutral("context_manufacturing_risk")

    penalty = 0.05  # Additional 5% penalty for combined risk

    return FactorResult.penalty(
        name="context_manufacturing_risk",
        value=penalty,
        reason=f"제조 복합 리스크 ({penalty:.0%})",
    )
