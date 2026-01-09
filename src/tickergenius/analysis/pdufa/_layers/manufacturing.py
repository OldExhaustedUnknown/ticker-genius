"""
Manufacturing Layer - Facility/Manufacturing Factors
=====================================================
Handles manufacturing facility and PAI related factors.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import FactorRegistry, FactorResult
from tickergenius.repositories.constants import get_factor_adjustment


@FactorRegistry.register(
    name="facility_pai_passed",
    layer="manufacturing",
    order=10,
    version="1.0",
    description="PAI 통과 보너스",
)
def apply_pai_passed_bonus(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply bonus for PAI inspection passed."""
    if not ctx.manufacturing.pai_passed:
        return FactorResult.neutral("facility_pai_passed")

    factor = get_factor_adjustment("manufacturing", "facility_pai_passed")
    if factor is None:
        return FactorResult.neutral("facility_pai_passed", "팩터 정의 없음")

    return FactorResult.bonus(
        name="facility_pai_passed",
        value=factor.score,
        reason=f"PAI 통과 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="facility_warning_letter",
    layer="manufacturing",
    order=20,
    version="1.1",
    description="시설 Warning Letter 페널티 (temporal-aware)",
)
def apply_warning_letter_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty for facility warning letter.

    Temporal considerations:
    - Recent (<180 days): Full penalty
    - Stale (>365 days): Reduced penalty (50%)
    - After PAI: Amplified penalty (125%)
    """
    if not ctx.manufacturing.has_warning_letter:
        return FactorResult.neutral("facility_warning_letter")

    factor = get_factor_adjustment("manufacturing", "facility_warning_letter")
    if factor is None:
        return FactorResult.neutral("facility_warning_letter", "팩터 정의 없음")

    base_penalty = abs(factor.score)
    reason_parts = ["Warning Letter"]

    # Temporal adjustments
    if ctx.is_warning_letter_stale:
        # Old warning letter - might be resolved, reduce penalty
        base_penalty *= 0.5
        reason_parts.append("오래됨(50%감소)")
    elif ctx.warning_letter_after_pai:
        # Warning letter after PAI passed - more severe
        base_penalty *= 1.25
        reason_parts.append("PAI 후 발생(25%증가)")

    days = ctx.days_since_warning_letter
    if days is not None:
        reason_parts.append(f"{days}일 전")

    return FactorResult.penalty(
        name="facility_warning_letter",
        value=base_penalty,
        reason=f"{' '.join(reason_parts)} (-{base_penalty:.0%})",
    )


@FactorRegistry.register(
    name="fda_483_observations",
    layer="manufacturing",
    order=30,
    version="1.1",
    description="FDA 483 관찰사항 페널티 (temporal-aware)",
)
def apply_fda_483_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply penalty based on FDA 483 observation count.

    Severity levels:
    - Critical: >= 10 observations
    - Moderate: 4-9 observations
    - Minor: 1-3 observations

    Temporal adjustments:
    - Old 483 (>365 days): 50% penalty reduction (likely resolved)
    - Recent 483 (<90 days): Full penalty
    """
    from datetime import date

    obs_count = ctx.manufacturing.fda_483_observations

    if obs_count == 0:
        return FactorResult.neutral("fda_483_observations")

    # Determine severity level
    if obs_count >= 10:
        factor_key = "fda_483_critical"
        severity = "심각"
    elif obs_count >= 4:
        factor_key = "fda_483_moderate"
        severity = "보통"
    else:  # 1-3
        factor_key = "fda_483_minor"
        severity = "경미"

    factor = get_factor_adjustment("manufacturing", factor_key)
    if factor is None:
        return FactorResult.neutral("fda_483_observations", "팩터 정의 없음")

    base_penalty = abs(factor.score)
    reason_parts = [f"FDA 483 {severity} ({obs_count}건)"]

    # Temporal adjustment based on 483 date
    fda_483_date = ctx.manufacturing.fda_483_date
    if fda_483_date:
        days_since = (ctx.analysis_date - fda_483_date).days
        reason_parts.append(f"{days_since}일 전")

        if days_since > 365:
            # Old 483 - likely resolved or remediated
            base_penalty *= 0.5
            reason_parts.append("오래됨(50%감소)")
        elif days_since > 180:
            # Moderately old - partial reduction
            base_penalty *= 0.75
            reason_parts.append("일부 해결 추정(25%감소)")

    return FactorResult.penalty(
        name="fda_483_observations",
        value=base_penalty,
        reason=f"{' '.join(reason_parts)} (-{base_penalty:.0%})",
    )


@FactorRegistry.register(
    name="cdmo_high_risk",
    layer="manufacturing",
    order=40,
    version="1.0",
    description="고위험 CDMO 페널티",
)
def apply_cdmo_risk_penalty(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply penalty for high-risk CDMO."""
    if not ctx.manufacturing.is_high_risk_cdmo:
        return FactorResult.neutral("cdmo_high_risk")

    factor = get_factor_adjustment("manufacturing", "cdmo_high_risk")
    if factor is None:
        return FactorResult.neutral("cdmo_high_risk", "팩터 정의 없음")

    cdmo_name = ctx.manufacturing.cdmo_name or "Unknown"

    return FactorResult.penalty(
        name="cdmo_high_risk",
        value=factor.score,
        reason=f"고위험 CDMO: {cdmo_name} ({factor.score:.0%})",
    )
