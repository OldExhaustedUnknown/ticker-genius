"""
Cap Layer - Probability Bounds and Hard Caps
=============================================
Final layer that applies probability bounds and hard caps.

This layer runs LAST to ensure all factors are applied before
capping the final probability.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_probability_bounds, get_hard_cap


@FactorRegistry.register(
    name="hard_cap_catastrophic",
    layer="cap",
    order=10,
    version="1.0",
    description="치명적 문제 Hard Cap (5%)",
)
def apply_catastrophic_cap(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply catastrophic hard cap.

    Conditions: primary_endpoint_not_met, data_integrity_issue
    Max probability: 5%
    """
    # Primary endpoint not met
    if ctx.clinical.primary_endpoint_met is False:
        cap = get_hard_cap("catastrophic")
        if cap and current_prob > cap:
            adjustment = cap - current_prob
            return FactorResult(
                name="hard_cap_catastrophic",
                adjustment=adjustment,
                reason=f"1차 평가지표 미달성 Hard Cap ({cap:.0%})",
                applied=True,
                metadata={"cap_type": "catastrophic", "cap_value": cap},
            )

    return FactorResult.neutral("hard_cap_catastrophic")


@FactorRegistry.register(
    name="hard_cap_critical",
    layer="cap",
    order=20,
    version="1.0",
    description="심각한 문제 Hard Cap (15%)",
)
def apply_critical_cap(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply critical hard cap.

    Conditions: efficacy_crl, trial_region_china_only
    Max probability: 15%
    """
    is_critical = False
    reason = ""

    # China-only trial
    if ctx.clinical.trial_region == "china_only":
        is_critical = True
        reason = "중국 단독 임상"

    if not is_critical:
        return FactorResult.neutral("hard_cap_critical")

    cap = get_hard_cap("critical")
    if cap and current_prob > cap:
        adjustment = cap - current_prob
        return FactorResult(
            name="hard_cap_critical",
            adjustment=adjustment,
            reason=f"{reason} Hard Cap ({cap:.0%})",
            applied=True,
            metadata={"cap_type": "critical", "cap_value": cap},
        )

    return FactorResult.neutral("hard_cap_critical")


@FactorRegistry.register(
    name="hard_cap_severe",
    layer="cap",
    order=30,
    version="1.0",
    description="중대한 문제 Hard Cap (25%)",
)
def apply_severe_cap(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply severe hard cap.

    Conditions: safety_crl, facility_warning_letter
    Max probability: 25%
    """
    is_severe = False
    reason = ""

    # Warning letter
    if ctx.manufacturing.has_warning_letter:
        is_severe = True
        reason = "시설 Warning Letter"

    if not is_severe:
        return FactorResult.neutral("hard_cap_severe")

    cap = get_hard_cap("severe")
    if cap and current_prob > cap:
        adjustment = cap - current_prob
        return FactorResult(
            name="hard_cap_severe",
            adjustment=adjustment,
            reason=f"{reason} Hard Cap ({cap:.0%})",
            applied=True,
            metadata={"cap_type": "severe", "cap_value": cap},
        )

    return FactorResult.neutral("hard_cap_severe")


@FactorRegistry.register(
    name="hard_cap_moderate",
    layer="cap",
    order=40,
    version="1.0",
    description="보통 문제 Hard Cap (40%)",
)
def apply_moderate_cap(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply moderate hard cap.

    Conditions: adcom_vote_negative
    Max probability: 40%
    """
    is_moderate = False
    reason = ""

    # Negative AdCom vote
    if ctx.adcom_vote_negative:
        is_moderate = True
        reason = "AdCom 부정 투표"

    if not is_moderate:
        return FactorResult.neutral("hard_cap_moderate")

    cap = get_hard_cap("moderate")
    if cap and current_prob > cap:
        adjustment = cap - current_prob
        return FactorResult(
            name="hard_cap_moderate",
            adjustment=adjustment,
            reason=f"{reason} Hard Cap ({cap:.0%})",
            applied=True,
            metadata={"cap_type": "moderate", "cap_value": cap},
        )

    return FactorResult.neutral("hard_cap_moderate")


@FactorRegistry.register(
    name="floor_fda_designation",
    layer="cap",
    order=50,
    version="1.0",
    description="FDA 지정 Floor (15%)",
)
def apply_designation_floor(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply floor for FDA designations.

    If has any FDA designation, minimum probability is 15%.
    """
    if not ctx.fda_designations.has_any():
        return FactorResult.neutral("floor_fda_designation")

    floor = 0.15
    if current_prob < floor:
        adjustment = floor - current_prob
        return FactorResult(
            name="floor_fda_designation",
            adjustment=adjustment,
            reason=f"FDA 지정 Floor ({floor:.0%})",
            applied=True,
            metadata={"floor_type": "fda_designation", "floor_value": floor},
        )

    return FactorResult.neutral("floor_fda_designation")


@FactorRegistry.register(
    name="floor_spa_agreed",
    layer="cap",
    order=60,
    version="1.0",
    description="SPA 합의 Floor (20%)",
)
def apply_spa_floor(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply floor for SPA agreement.

    If SPA agreed (and not rescinded), minimum probability is 20%.
    """
    if not ctx.spa_agreed or ctx.spa_rescinded:
        return FactorResult.neutral("floor_spa_agreed")

    floor = 0.20
    if current_prob < floor:
        adjustment = floor - current_prob
        return FactorResult(
            name="floor_spa_agreed",
            adjustment=adjustment,
            reason=f"SPA 합의 Floor ({floor:.0%})",
            applied=True,
            metadata={"floor_type": "spa_agreed", "floor_value": floor},
        )

    return FactorResult.neutral("floor_spa_agreed")


@FactorRegistry.register(
    name="probability_bounds",
    layer="cap",
    order=100,  # Run last
    version="1.0",
    description="확률 범위 제한 (10-90%)",
)
def apply_probability_bounds(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply final probability bounds.

    Clamps probability to 10-90% range (TF 62차 합의).

    IMPORTANT: Hard caps take precedence over floor.
    - Catastrophic conditions (primary endpoint not met) → max 5%
    - Critical conditions (china-only) → max 15%
    - These caps prevent floor from raising probability above them.
    """
    bounds = get_probability_bounds()
    min_prob = bounds.get("min", 0.10)
    max_prob = bounds.get("max", 0.90)

    # Check for hard cap conditions that override the floor
    effective_max = max_prob

    # Catastrophic: primary endpoint not met → 5% max (overrides 10% floor)
    if ctx.clinical.primary_endpoint_met is False:
        catastrophic_cap = get_hard_cap("catastrophic")
        if catastrophic_cap:
            effective_max = min(effective_max, catastrophic_cap)
            # Don't apply floor - keep at or below catastrophic cap
            min_prob = 0.0

    # Critical: china-only trial → 15% max
    if ctx.clinical.trial_region == "china_only":
        critical_cap = get_hard_cap("critical")
        if critical_cap:
            effective_max = min(effective_max, critical_cap)

    # Severe: warning letter → 25% max
    if ctx.manufacturing.has_warning_letter:
        severe_cap = get_hard_cap("severe")
        if severe_cap:
            effective_max = min(effective_max, severe_cap)

    # Moderate: negative adcom → 40% max
    if ctx.adcom_vote_negative:
        moderate_cap = get_hard_cap("moderate")
        if moderate_cap:
            effective_max = min(effective_max, moderate_cap)

    # Apply bounds
    if current_prob > effective_max:
        adjustment = effective_max - current_prob
        return FactorResult(
            name="probability_bounds",
            adjustment=adjustment,
            reason=f"최대 확률 제한 ({effective_max:.0%})",
            applied=True,
            metadata={"bound_type": "max", "bound_value": effective_max},
        )
    elif current_prob < min_prob:
        adjustment = min_prob - current_prob
        return FactorResult(
            name="probability_bounds",
            adjustment=adjustment,
            reason=f"최소 확률 제한 ({min_prob:.0%})",
            applied=True,
            metadata={"bound_type": "min", "bound_value": min_prob},
        )

    return FactorResult.neutral("probability_bounds")
