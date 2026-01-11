"""
Clinical Layer - Clinical Trial Factors
========================================
Handles clinical trial related factors.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="primary_endpoint_not_met",
    layer="clinical",
    order=10,
    version="1.0",
    description="1차 평가지표 미달성 페널티",
)
def apply_primary_endpoint_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty for primary endpoint not met.

    This is a catastrophic factor - Hard Cap 5% applies.
    """
    # None means unknown, only apply if explicitly False
    if ctx.clinical.primary_endpoint_met is None or ctx.clinical.primary_endpoint_met:
        return FactorResult.neutral("primary_endpoint_not_met")

    factor = get_factor_adjustment("clinical", "primary_endpoint_not_met")
    if factor is None:
        return FactorResult.neutral("primary_endpoint_not_met", "팩터 정의 없음")

    return FactorResult.penalty(
        name="primary_endpoint_not_met",
        value=factor.score,
        reason=f"1차 평가지표 미달성 ({factor.score:.0%})",
    )


@FactorRegistry.register(
    name="single_arm_trial",
    layer="clinical",
    order=20,
    version="2.0",  # Wave 4: merged with RWE/external control
    description="단일군 시험 페널티 (RWE/외부대조군 포함)",
)
def apply_single_arm_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty for single-arm trial design.

    Wave 4 Update (2026-01-10):
    - Merged with RWE/external control penalty
    - is_single_arm now includes RWE/external control cases
    - Penalty increased from -5% to -7%
    """
    if not ctx.clinical.is_single_arm:
        return FactorResult.neutral("single_arm_trial")

    factor = get_factor_adjustment("clinical", "single_arm_trial")
    if factor is None:
        # Default: -7% (increased from -5% after merging RWE)
        return FactorResult.penalty(
            name="single_arm_trial",
            value=-0.07,
            reason="단일군/RWE 시험 (-7%)",
        )

    return FactorResult.penalty(
        name="single_arm_trial",
        value=factor.score,
        reason=f"단일군/RWE 시험 ({factor.score:.0%})",
    )


@FactorRegistry.register(
    name="trial_region_china_only",
    layer="clinical",
    order=40,
    version="1.0",
    description="중국 단독 임상 페널티",
)
def apply_china_only_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply penalty for China-only clinical trial."""
    if ctx.clinical.trial_region != "china_only":
        return FactorResult.neutral("trial_region_china_only")

    factor = get_factor_adjustment("clinical", "trial_region_china_only")
    if factor is None:
        return FactorResult.neutral("trial_region_china_only", "팩터 정의 없음")

    return FactorResult.penalty(
        name="trial_region_china_only",
        value=factor.score,
        reason=f"중국 단독 임상 ({factor.score:.0%})",
    )


@FactorRegistry.register(
    name="clinical_hold_history",
    layer="clinical",
    order=50,
    version="1.0",
    description="Clinical Hold 이력 페널티",
)
def apply_clinical_hold_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply penalty for clinical hold history."""
    if not ctx.clinical.has_clinical_hold_history:
        return FactorResult.neutral("clinical_hold_history")

    factor = get_factor_adjustment("clinical", "clinical_hold_history")
    if factor is None:
        return FactorResult.neutral("clinical_hold_history", "팩터 정의 없음")

    return FactorResult.penalty(
        name="clinical_hold_history",
        value=factor.score,
        reason=f"Clinical Hold 이력 ({factor.score:.0%})",
    )


# Mental Health Indication Penalties
# High placebo response rates make it harder to show drug efficacy
MENTAL_HEALTH_PENALTIES = {
    "mdd": -0.12,       # Major Depressive Disorder - very high placebo response
    "ptsd": -0.10,      # PTSD - high placebo response
    "anxiety": -0.08,   # Anxiety disorders
    "bipolar": -0.06,   # Bipolar - moderate
    "schizophrenia": -0.04,  # Schizophrenia - lower placebo but complex endpoints
    "default": -0.08,   # Default for unspecified mental health
}


@FactorRegistry.register(
    name="mental_health_indication",
    layer="clinical",
    order=60,
    version="1.0",
    description="정신건강 적응증 페널티 (높은 플라시보 반응)",
)
def apply_mental_health_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty for mental health indications.

    Mental health trials have high placebo response rates (30-50%),
    making it harder to demonstrate statistical significance.
    """
    if not ctx.clinical.is_mental_health:
        return FactorResult.neutral("mental_health_indication")

    # Get specific penalty based on indication type
    indication = ctx.clinical.mental_health_type
    if indication and indication.lower() in MENTAL_HEALTH_PENALTIES:
        penalty = MENTAL_HEALTH_PENALTIES[indication.lower()]
        indication_name = indication.upper()
    else:
        penalty = MENTAL_HEALTH_PENALTIES["default"]
        indication_name = "정신건강"

    return FactorResult.penalty(
        name="mental_health_indication",
        value=penalty,
        reason=f"{indication_name} 적응증 - 높은 플라시보 반응 ({penalty:.0%})",
    )
