"""
Designation Layer - FDA Designations
=====================================
Handles FDA designation bonuses (BTD, Priority Review, etc.)

NOTE: FDA designations use MAX_ONLY group - only highest applies.
This matches legacy behavior where designations don't stack.
"""

from tickergenius.analysis.pdufa._context import AnalysisContext
from tickergenius.analysis.pdufa._registry import (
    FactorRegistry,
    FactorResult,
    FactorGroupType,
)
from tickergenius.repositories.constants import get_factor_adjustment


# Group name and type for FDA designations
FDA_DESIGNATION_GROUP = "fda_designation"
FDA_DESIGNATION_GROUP_TYPE = FactorGroupType.MAX_ONLY


@FactorRegistry.register(
    name="breakthrough_therapy",
    layer="designation",
    order=10,
    version="1.0",
    description="Breakthrough Therapy 지정 보너스",
    group=FDA_DESIGNATION_GROUP,
    group_type=FDA_DESIGNATION_GROUP_TYPE,
)
def apply_btd(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Breakthrough Therapy Designation bonus."""
    if not ctx.fda_designations.breakthrough_therapy:
        return FactorResult.neutral("breakthrough_therapy")

    factor = get_factor_adjustment("fda_designations", "breakthrough_therapy")
    if factor is None:
        return FactorResult.neutral("breakthrough_therapy", "팩터 정의 없음")

    return FactorResult.bonus(
        name="breakthrough_therapy",
        value=factor.score,
        reason=f"Breakthrough Therapy 지정 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="priority_review",
    layer="designation",
    order=20,
    version="1.0",
    description="Priority Review 지정 보너스",
    group=FDA_DESIGNATION_GROUP,
    group_type=FDA_DESIGNATION_GROUP_TYPE,
)
def apply_priority_review(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Priority Review bonus."""
    if not ctx.fda_designations.priority_review:
        return FactorResult.neutral("priority_review")

    factor = get_factor_adjustment("fda_designations", "priority_review")
    if factor is None:
        return FactorResult.neutral("priority_review", "팩터 정의 없음")

    return FactorResult.bonus(
        name="priority_review",
        value=factor.score,
        reason=f"Priority Review 지정 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="fast_track",
    layer="designation",
    order=30,
    version="1.0",
    description="Fast Track 지정 보너스",
    group=FDA_DESIGNATION_GROUP,
    group_type=FDA_DESIGNATION_GROUP_TYPE,
)
def apply_fast_track(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Fast Track bonus."""
    if not ctx.fda_designations.fast_track:
        return FactorResult.neutral("fast_track")

    factor = get_factor_adjustment("fda_designations", "fast_track")
    if factor is None:
        return FactorResult.neutral("fast_track", "팩터 정의 없음")

    return FactorResult.bonus(
        name="fast_track",
        value=factor.score,
        reason=f"Fast Track 지정 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="orphan_drug",
    layer="designation",
    order=40,
    version="1.0",
    description="Orphan Drug 지정 보너스",
    group=FDA_DESIGNATION_GROUP,
    group_type=FDA_DESIGNATION_GROUP_TYPE,
)
def apply_orphan_drug(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Orphan Drug bonus."""
    if not ctx.fda_designations.orphan_drug:
        return FactorResult.neutral("orphan_drug")

    factor = get_factor_adjustment("fda_designations", "orphan_drug")
    if factor is None:
        return FactorResult.neutral("orphan_drug", "팩터 정의 없음")

    return FactorResult.bonus(
        name="orphan_drug",
        value=factor.score,
        reason=f"Orphan Drug 지정 (+{factor.score:.0%})",
    )


@FactorRegistry.register(
    name="accelerated_approval",
    layer="designation",
    order=50,
    version="1.0",
    description="Accelerated Approval 보너스",
    group=FDA_DESIGNATION_GROUP,
    group_type=FDA_DESIGNATION_GROUP_TYPE,
)
def apply_accelerated_approval(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """Apply Accelerated Approval bonus."""
    if not ctx.fda_designations.accelerated_approval:
        return FactorResult.neutral("accelerated_approval")

    factor = get_factor_adjustment("fda_designations", "accelerated_approval")
    if factor is None:
        return FactorResult.neutral("accelerated_approval", "팩터 정의 없음")

    return FactorResult.bonus(
        name="accelerated_approval",
        value=factor.score,
        reason=f"Accelerated Approval (+{factor.score:.0%})",
    )


# First-in-Class is NOT in the FDA designation group
# It's an independent factor that stacks with designations
@FactorRegistry.register(
    name="first_in_class",
    layer="designation",
    order=60,
    version="1.0",
    description="First-in-Class 보너스 (독립)",
)
def apply_first_in_class(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """
    Apply First-in-Class bonus.

    Note: This is NOT grouped with FDA designations.
    First-in-Class is an independent factor that stacks.
    """
    if not ctx.fda_designations.is_first_in_class:
        return FactorResult.neutral("first_in_class")

    factor = get_factor_adjustment("special", "first_in_class")
    if factor is None:
        return FactorResult.neutral("first_in_class", "팩터 정의 없음")

    return FactorResult.bonus(
        name="first_in_class",
        value=factor.score,
        reason=f"First-in-Class (+{factor.score:.0%})",
    )
