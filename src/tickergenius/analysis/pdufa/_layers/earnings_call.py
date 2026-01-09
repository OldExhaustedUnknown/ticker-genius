"""
Earnings Call Layer - Management Commentary Signals
====================================================
Handles earnings call signals that may indicate approval likelihood.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="label_negotiation_signal",
    layer="earnings_call",
    order=10,
    version="1.0",
    description="라벨 협상 진행 언급 (긍정 시그널)",
)
def apply_label_negotiation(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply bonus when management mentions label negotiation.

    Label negotiation typically indicates FDA is moving toward approval
    and is discussing final labeling details.
    """
    if not ctx.earnings_call.label_negotiation_mentioned:
        return FactorResult.neutral("label_negotiation_signal")

    factor = get_factor_adjustment("earnings_call", "label_negotiation")
    if factor is None:
        return FactorResult.neutral("label_negotiation_signal", "팩터 정의 없음")

    return FactorResult.bonus(
        name="label_negotiation_signal",
        value=factor.score,
        reason=f"경영진 라벨 협상 진행 언급 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="timeline_delay_signal",
    layer="earnings_call",
    order=20,
    version="1.0",
    description="타임라인 지연 암시 (부정 시그널)",
)
def apply_timeline_delay(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty when management hints at timeline delays.

    Timeline delay hints suggest potential issues with FDA review
    or additional requirements before approval.
    """
    if not ctx.earnings_call.timeline_delayed:
        return FactorResult.neutral("timeline_delay_signal")

    factor = get_factor_adjustment("earnings_call", "timeline_delayed")
    if factor is None:
        return FactorResult.neutral("timeline_delay_signal", "팩터 정의 없음")

    return FactorResult.penalty(
        name="timeline_delay_signal",
        value=factor.score,
        reason=f"경영진 타임라인 지연 암시 ({factor.score:.0%})",
    )


@FactorRegistry.register(
    name="management_confidence_signal",
    layer="earnings_call",
    order=30,
    version="1.0",
    description="경영진 승인 자신감",
)
def apply_management_confidence(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply adjustment based on management confidence level.

    Confident statements suggest inside knowledge of positive FDA interactions.
    Cautious statements may indicate ongoing concerns.
    """
    # Confident signal (positive)
    if ctx.earnings_call.management_confident:
        factor = get_factor_adjustment("earnings_call", "management_confident")
        if factor is None:
            return FactorResult.neutral("management_confidence_signal", "팩터 정의 없음")

        return FactorResult.bonus(
            name="management_confidence_signal",
            value=factor.score,
            reason=f"경영진 승인 자신감 표명 (+{factor.score:.0%})",
        )

    # Cautious signal (negative)
    if ctx.earnings_call.management_cautious:
        factor = get_factor_adjustment("earnings_call", "management_cautious")
        if factor is None:
            return FactorResult.neutral("management_confidence_signal", "팩터 정의 없음")

        return FactorResult.penalty(
            name="management_confidence_signal",
            value=factor.score,
            reason=f"경영진 불확실성 강조 ({factor.score:.0%})",
        )

    return FactorResult.neutral("management_confidence_signal")
