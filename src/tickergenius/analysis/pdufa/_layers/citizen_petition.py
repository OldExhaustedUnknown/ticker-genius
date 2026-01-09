"""
Citizen Petition Layer - FDA Citizen Petition Factors
======================================================
Handles citizen petitions filed against drug approvals.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="citizen_petition_status",
    layer="citizen_petition",
    order=10,
    version="1.0",
    description="시민 청원 상태",
)
def apply_citizen_petition(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply adjustment based on citizen petition status.

    Citizen petitions can delay or block drug approvals:
    - filed: Petition submitted, outcome pending (-8%)
    - denied: FDA denied the petition (+5%)
    - granted: FDA granted the petition (-25%)
    """
    if not ctx.citizen_petition.has_petition:
        return FactorResult.neutral("citizen_petition_status")

    status = ctx.citizen_petition.petition_status
    if not status:
        # Has petition but status unknown - assume negative
        factor = get_factor_adjustment("citizen_petition", "petition_filed")
        if factor is None:
            return FactorResult.neutral("citizen_petition_status", "팩터 정의 없음")

        return FactorResult.penalty(
            name="citizen_petition_status",
            value=factor.score,
            reason=f"시민 청원 제출됨 (결과 불명) ({factor.score:.0%})",
        )

    # Map status to factor
    status_map = {
        "filed": ("petition_filed", False, "제출됨"),
        "denied": ("petition_denied", True, "기각됨"),
        "granted": ("petition_granted", False, "수용됨"),
    }

    if status not in status_map:
        return FactorResult.neutral("citizen_petition_status", f"알 수 없는 청원 상태: {status}")

    factor_key, is_bonus, label = status_map[status]
    factor = get_factor_adjustment("citizen_petition", factor_key)

    if factor is None:
        return FactorResult.neutral("citizen_petition_status", "팩터 정의 없음")

    # Add petitioner info if available
    reason_parts = [f"시민 청원 {label}"]
    if ctx.citizen_petition.petitioner:
        reason_parts.append(f"({ctx.citizen_petition.petitioner})")

    if is_bonus:
        return FactorResult.bonus(
            name="citizen_petition_status",
            value=factor.score,
            reason=f"{' '.join(reason_parts)} (+{factor.score:.0%})",
        )
    else:
        return FactorResult.penalty(
            name="citizen_petition_status",
            value=factor.score,
            reason=f"{' '.join(reason_parts)} ({factor.score:.0%})",
        )
