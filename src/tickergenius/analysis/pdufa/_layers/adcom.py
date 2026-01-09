"""
AdCom Layer - Advisory Committee Results
==========================================
Handles Advisory Committee vote outcomes.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="adcom_vote_positive",
    layer="adcom",
    order=10,
    version="1.0",
    description="AdCom 긍정 투표 보너스 (>50%)",
)
def apply_adcom_positive(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply AdCom positive vote bonus."""
    if not ctx.adcom.was_held:
        return FactorResult.neutral("adcom_vote_positive", "AdCom 미개최")

    if ctx.adcom.was_waived:
        return FactorResult.neutral("adcom_vote_positive", "AdCom 면제")

    if not ctx.adcom_vote_positive:
        return FactorResult.neutral("adcom_vote_positive")

    factor = get_factor_adjustment("adcom", "vote_positive")
    if factor is None:
        return FactorResult.neutral("adcom_vote_positive", "팩터 정의 없음")

    vote_pct = (ctx.adcom.vote_ratio or 0) * 100
    return FactorResult.bonus(
        name="adcom_vote_positive",
        value=factor.score,
        reason=f"AdCom 긍정 투표 ({vote_pct:.0f}%) (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="adcom_vote_negative",
    layer="adcom",
    order=20,
    version="1.0",
    description="AdCom 부정 투표 페널티 (≤50%)",
)
def apply_adcom_negative(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply AdCom negative vote penalty."""
    if not ctx.adcom.was_held:
        return FactorResult.neutral("adcom_vote_negative", "AdCom 미개최")

    if ctx.adcom.was_waived:
        return FactorResult.neutral("adcom_vote_negative", "AdCom 면제")

    if not ctx.adcom_vote_negative:
        return FactorResult.neutral("adcom_vote_negative")

    factor = get_factor_adjustment("adcom", "vote_negative")
    if factor is None:
        return FactorResult.neutral("adcom_vote_negative", "팩터 정의 없음")

    vote_pct = (ctx.adcom.vote_ratio or 0) * 100
    return FactorResult.penalty(
        name="adcom_vote_negative",
        value=factor.score,
        reason=f"AdCom 부정 투표 ({vote_pct:.0f}%) ({factor.score:.0%})",
    )


@FactorRegistry.register(
    name="adcom_waived",
    layer="adcom",
    order=30,
    version="1.0",
    description="AdCom 면제 보너스",
)
def apply_adcom_waived(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply AdCom waived bonus (FDA confidence signal)."""
    if not ctx.adcom.was_waived:
        return FactorResult.neutral("adcom_waived")

    factor = get_factor_adjustment("adcom", "waived")
    if factor is None:
        return FactorResult.neutral("adcom_waived", "팩터 정의 없음")

    return FactorResult.bonus(
        name="adcom_waived",
        value=factor.score,
        reason=f"AdCom 면제 (FDA 신뢰 신호) (+{factor.score:.0%})",
    )
