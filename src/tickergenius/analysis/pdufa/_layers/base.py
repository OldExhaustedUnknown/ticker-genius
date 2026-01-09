"""
Base Layer - Base Approval Rate
================================
Determines the starting probability based on application type and phase.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import ConstantsLoader


@FactorRegistry.register(
    name="base_rate",
    layer="base",
    order=0,
    version="1.0",
    description="기본 승인률 결정 (신청 유형, 임상 단계 기반)",
)
def apply_base_rate(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Determine base approval rate.

    Priority:
    1. Biosimilar rates (if biosimilar)
    2. Resubmission rates (if resubmission)
    3. Application type rates (NDA/BLA)
    4. Phase-based rates
    5. Default rate
    """
    loader = ConstantsLoader.instance()

    # Biosimilar
    if ctx.is_biosimilar:
        if ctx.is_resubmission:
            rate = loader.get_base_rate("biosimilar.resubmission")
            if rate:
                return FactorResult(
                    name="base_rate",
                    adjustment=rate.rate - current_prob,
                    reason=f"바이오시밀러 재제출 기본률: {rate.rate:.1%}",
                )
        rate = loader.get_base_rate("biosimilar.bla")
        if rate:
            return FactorResult(
                name="base_rate",
                adjustment=rate.rate - current_prob,
                reason=f"바이오시밀러 BLA 기본률: {rate.rate:.1%}",
            )

    # Resubmission by class
    if ctx.is_resubmission:
        if ctx.is_class1_resubmission:
            if ctx.is_cmc_only_crl:
                rate = loader.get_base_rate("resubmission.class1_cmc_only")
            else:
                rate = loader.get_base_rate("resubmission.class1")
        elif ctx.is_class2_resubmission:
            if ctx.is_cmc_only_crl:
                rate = loader.get_base_rate("resubmission.class2_cmc_only")
            else:
                rate = loader.get_base_rate("resubmission.class2")
        else:
            rate = loader.get_base_rate("resubmission.base")

        if rate:
            return FactorResult(
                name="base_rate",
                adjustment=rate.rate - current_prob,
                reason=f"재제출 기본률: {rate.rate:.1%}",
            )

    # By application type
    rate = loader.get_base_rate("nda_bla")
    if rate:
        return FactorResult(
            name="base_rate",
            adjustment=rate.rate - current_prob,
            reason=f"NDA/BLA 기본률: {rate.rate:.1%}",
        )

    # Default
    default_rate = loader.get_default_base_rate()
    return FactorResult(
        name="base_rate",
        adjustment=default_rate - current_prob,
        reason=f"기본률: {default_rate:.1%}",
    )
