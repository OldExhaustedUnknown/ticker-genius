"""
CRL Layer - Complete Response Letter History
=============================================
Handles CRL history and resubmission factors.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="crl_class1_bonus",
    layer="crl",
    order=10,
    version="1.0",
    description="Class 1 재제출 보너스",
)
def apply_class1_bonus(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Class 1 resubmission bonus."""
    if not ctx.is_class1_resubmission:
        return FactorResult.neutral("crl_class1_bonus")

    factor = get_factor_adjustment("crl_resubmission", "class1_resubmission")
    if factor is None:
        return FactorResult.neutral("crl_class1_bonus", "팩터 정의 없음")

    return FactorResult.bonus(
        name="crl_class1_bonus",
        value=factor.score,
        reason=f"Class 1 재제출 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="crl_class2_bonus",
    layer="crl",
    order=20,
    version="1.0",
    description="Class 2 재제출 보너스",
)
def apply_class2_bonus(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Class 2 resubmission bonus."""
    if not ctx.is_class2_resubmission:
        return FactorResult.neutral("crl_class2_bonus")

    factor = get_factor_adjustment("crl_resubmission", "class2_resubmission")
    if factor is None:
        return FactorResult.neutral("crl_class2_bonus", "팩터 정의 없음")

    return FactorResult.bonus(
        name="crl_class2_bonus",
        value=factor.score,
        reason=f"Class 2 재제출 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="new_app_got_crl",
    layer="crl",
    order=30,
    version="1.0",
    description="신규 신청에 CRL 발생 페널티",
)
def apply_new_app_crl(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty for new applications that received CRL.

    Note: This is different from resubmission status - it applies
    when a fresh application got CRL'd.
    """
    # Only applies if has prior CRL but NOT currently in resubmission
    # (i.e., analyzing the original submission that got CRL)
    if not ctx.has_prior_crl or ctx.is_resubmission:
        return FactorResult.neutral("new_app_got_crl")

    factor = get_factor_adjustment("crl_resubmission", "new_app_got_crl")
    if factor is None:
        return FactorResult.neutral("new_app_got_crl", "팩터 정의 없음")

    return FactorResult.penalty(
        name="new_app_got_crl",
        value=factor.score,
        reason=f"신규 신청 CRL ({factor.score:.0%})",
    )


@FactorRegistry.register(
    name="is_resubmission",
    layer="crl",
    order=40,
    version="1.0",
    description="재제출 기본 페널티",
)
def apply_resubmission_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply base resubmission penalty.

    Note: This is a baseline penalty; class-specific bonuses above
    may offset this.
    """
    if not ctx.is_resubmission:
        return FactorResult.neutral("is_resubmission")

    factor = get_factor_adjustment("crl_resubmission", "is_resubmission")
    if factor is None:
        return FactorResult.neutral("is_resubmission", "팩터 정의 없음")

    return FactorResult.penalty(
        name="is_resubmission",
        value=factor.score,
        reason=f"재제출 기본 ({factor.score:.0%})",
    )
