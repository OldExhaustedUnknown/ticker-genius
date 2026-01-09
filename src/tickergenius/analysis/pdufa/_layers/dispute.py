"""
Dispute Layer - FDA Dispute Resolution Factors
===============================================
Handles FDA dispute resolution outcomes.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="dispute_resolution",
    layer="dispute",
    order=10,
    version="1.0",
    description="FDA 분쟁 해결 결과",
)
def apply_dispute_result(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply adjustment based on FDA dispute resolution outcome.

    Dispute outcomes:
    - won_fully: Company won the dispute (+10%)
    - partial: Partial resolution (-5%)
    - lost_fully: Company lost the dispute (-20%)
    """
    if not ctx.dispute.has_dispute:
        return FactorResult.neutral("dispute_resolution")

    result = ctx.dispute.dispute_result
    if not result:
        return FactorResult.neutral("dispute_resolution", "분쟁 결과 불명")

    # Map result to factor key
    result_map = {
        "won_fully": ("dispute_won_fully", True),
        "partial": ("dispute_partial", False),
        "lost_fully": ("dispute_lost_fully", False),
    }

    if result not in result_map:
        return FactorResult.neutral("dispute_resolution", f"알 수 없는 분쟁 결과: {result}")

    factor_key, is_bonus = result_map[result]
    factor = get_factor_adjustment("dispute", factor_key)

    if factor is None:
        return FactorResult.neutral("dispute_resolution", "팩터 정의 없음")

    result_labels = {
        "won_fully": "완전 승리",
        "partial": "부분 승리",
        "lost_fully": "완전 패배",
    }

    if is_bonus:
        return FactorResult.bonus(
            name="dispute_resolution",
            value=factor.score,
            reason=f"FDA 분쟁 {result_labels[result]} (+{factor.score:.0%})",
        )
    else:
        return FactorResult.penalty(
            name="dispute_resolution",
            value=factor.score,
            reason=f"FDA 분쟁 {result_labels[result]} ({factor.score:.0%})",
        )
