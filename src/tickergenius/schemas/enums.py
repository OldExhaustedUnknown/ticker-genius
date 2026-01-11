"""
Ticker-Genius Enums
===================
M1: All enumeration types for the application.

Based on legacy modules/pdufa/enums.py with Pydantic v2 compatibility.
"""

from enum import Enum


# =============================================================================
# Data Collection Enums (Wave 2 - 2026-01-10)
# =============================================================================

class SearchStatus(str, Enum):
    """
    검색 상태 - 필드 값의 검색/확인 상태를 나타냄.

    5가지 상태:
    - FOUND: 값을 찾음 (재시도 불필요)
    - CONFIRMED_NONE: 공식 소스에서 없음 확인 (재시도 불필요)
    - NOT_APPLICABLE: 해당 케이스에 적용 안됨 (재시도 불필요)
    - NOT_FOUND: 검색했지만 못 찾음 (재시도 필요)
    - NOT_SEARCHED: 아직 검색 안함 (재시도 필요)
    """
    FOUND = "found"
    CONFIRMED_NONE = "confirmed_none"
    NOT_APPLICABLE = "not_applicable"
    NOT_FOUND = "not_found"
    NOT_SEARCHED = "not_searched"


class SourceTier(int, Enum):
    """
    소스 신뢰도 티어.

    - TIER1 (99%): FDA CDER 공식 목록, OpenFDA API
    - TIER2 (90%): SEC EDGAR 8-K, ClinicalTrials.gov
    - TIER3 (75%): 회사 PR, 뉴스 기사
    - TIER4 (50%): 애널리스트 리포트, 추론 기반
    """
    TIER1 = 1
    TIER2 = 2
    TIER3 = 3
    TIER4 = 4


class TrialRegion(str, Enum):
    """임상시험 지역 분류."""
    US_ONLY = "us_only"
    GLOBAL = "global"
    EX_US = "ex_us"
    CHINA_ONLY = "china_only"
    UNKNOWN = "unknown"


class CRLReasonType(str, Enum):
    """CRL 사유 유형."""
    CMC = "cmc"
    EFFICACY = "efficacy"
    SAFETY = "safety"
    LABELING = "labeling"
    UNKNOWN = "unknown"


# =============================================================================
# Core Analysis Enums
# =============================================================================

class TimingSignal(str, Enum):
    """Entry timing signal for trades."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    CAUTION = "CAUTION"
    AVOID = "AVOID"


class StrategyType(str, Enum):
    """PDUFA investment strategy types."""
    RUN_UP_EXIT = "run_up_exit"          # Exit D-7 to D-3 (low risk)
    HOLD_THROUGH = "hold_through"         # Hold through PDUFA (high risk/reward)
    STRANGLE_HEDGE = "strangle_hedge"     # Options hedge (neutral)
    POST_APPROVAL = "post_approval"       # Enter after approval
    AVOID = "avoid"                       # Avoid entry


# =============================================================================
# CRL (Complete Response Letter) Enums
# =============================================================================

class CRLType(str, Enum):
    """CRL classification types."""
    LABELING = "labeling"                      # Labeling issues (minor)
    CMC_MINOR = "cmc_minor"                    # Minor CMC (facility improvement)
    CMC_MAJOR = "cmc_major"                    # Major CMC (facility change)
    CDMO_THIRD_PARTY = "cdmo_third_party"      # CDMO third-party facility
    SAFETY_REMS = "safety_rems"                # Safety/REMS requirements
    EFFICACY_SUPPLEMENT = "efficacy_supplement" # Efficacy supplement (more data)
    EFFICACY_NEW_TRIAL = "efficacy_new_trial"  # Efficacy failure (new trial needed)
    TRIAL_DESIGN = "trial_design"              # Trial design defects (worst)
    STATISTICAL = "statistical"                # Statistical methodology issues


class CRLDelayCategory(str, Enum):
    """Time to resubmission after CRL."""
    UNDER_1_YEAR = "under_1_year"
    ONE_TO_TWO_YEARS = "1_to_2_years"
    TWO_TO_THREE_YEARS = "2_to_3_years"
    OVER_3_YEARS = "over_3_years"


class DisputeResolutionResult(str, Enum):
    """FDA Dispute Resolution results."""
    WON_FULLY = "won_fully"
    PARTIAL_ALTERNATIVE = "partial_alternative"
    LOST_FULLY = "lost_fully"
    NO_DISPUTE = "no_dispute"


# =============================================================================
# Clinical Trial Enums
# =============================================================================

class EndpointType(str, Enum):
    """Clinical trial endpoint types."""
    SURVIVAL = "survival"                    # Most objective
    OBJECTIVE_RESPONSE = "objective_response"  # ORR, CR, etc.
    BIOMARKER = "biomarker"                  # Semi-objective
    FUNCTIONAL = "functional"                # Functional assessment (6MWT, etc.)
    PATIENT_REPORTED = "patient_reported"    # PRO (subjective)
    COMPOSITE = "composite"                  # Composite endpoint


class ClinicalQualityTier(str, Enum):
    """Clinical quality classification."""
    # P-value grades
    PVALUE_HIGHLY_SIGNIFICANT = "pvalue_highly_significant"  # p < 0.001
    PVALUE_SIGNIFICANT = "pvalue_significant"                # p < 0.01
    PVALUE_MARGINAL = "pvalue_marginal"                      # 0.01 <= p < 0.05
    PVALUE_BORDERLINE = "pvalue_borderline"                  # 0.04 <= p < 0.05

    # Sample size grades
    SAMPLE_LARGE = "sample_large"          # N > 500
    SAMPLE_ADEQUATE = "sample_adequate"    # 200 <= N <= 500
    SAMPLE_SMALL = "sample_small"          # N < 200
    SAMPLE_VERY_SMALL = "sample_very_small"  # N < 100

    # Effect size
    EFFECT_CLINICALLY_MEANINGFUL = "effect_clinically_meaningful"
    EFFECT_MODEST = "effect_modest"
    EFFECT_MARGINAL = "effect_marginal"


class MentalHealthIndication(str, Enum):
    """Mental health indication subtypes (high placebo response)."""
    MDD = "mdd"                      # Major Depressive Disorder (hardest)
    PTSD = "ptsd"                    # Post-Traumatic Stress Disorder
    SOCIAL_ANXIETY = "social_anxiety"
    BIPOLAR = "bipolar"
    SCHIZOPHRENIA = "schizophrenia"
    OTHER = "other"


# =============================================================================
# Manufacturing/PAI Enums
# =============================================================================

class PAIStatus(str, Enum):
    """Pre-Approval Inspection status."""
    PASSED = "passed"           # PAI passed -> approval imminent
    SCHEDULED = "scheduled"     # PAI scheduled (in progress)
    PENDING = "pending"         # PAI pending (not yet scheduled)
    FAILED = "failed"           # PAI failed -> CRL certain
    REMEDIATION = "remediation"  # Remediation in progress


# =============================================================================
# Drug Classification Enums
# =============================================================================

class DrugClassification(str, Enum):
    """Drug innovation classification."""
    FIC = "first_in_class"           # First-in-Class
    BIC = "best_in_class"            # Best-in-Class
    ME_TOO = "me_too"                # Me-too drug
    GENERIC = "generic"              # Generic
    BIOSIMILAR = "biosimilar"        # Biosimilar
    SNDA_EXPANSION = "snda_expansion"  # sNDA expansion
    FORMULATION = "formulation"      # Formulation change


class ApprovalType(str, Enum):
    """FDA approval application types."""
    NDA = "nda"                     # New Drug Application
    BLA = "bla"                     # Biologics License Application
    SNDA = "snda"                   # Supplemental NDA
    SBLA = "sbla"                   # Supplemental BLA
    ANDA = "anda"                   # Abbreviated NDA (Generic)
    NDA_505B2 = "505b2"             # 505(b)(2) Hybrid
    BIOSIMILAR_BLA = "biosimilar"   # Biosimilar BLA
    RESUBMISSION = "resubmission"   # Resubmission (Class 1/2)


class DrugType(str, Enum):
    """Drug application types."""
    NME = "nme"                    # New Molecular Entity
    BLA = "bla"                    # Biologics
    SNDA_INDICATION = "snda_indication"  # Indication expansion
    SNDA_FORMULATION = "snda_formulation"  # Formulation change
    NDA_505B2 = "505b2"            # 505(b)(2)
    BIOSIMILAR = "biosimilar"
    GENERIC = "generic"


# =============================================================================
# Market Analysis Enums
# =============================================================================

class MarketSize(str, Enum):
    """Market size classification."""
    BLOCKBUSTER = "blockbuster"        # $10B+ market
    LARGE = "large"                    # $1-10B market
    MEDIUM = "medium"                  # $100M-1B market
    NICHE = "niche"                    # <$100M market (rare disease)


# =============================================================================
# Citizen Petition Enums
# =============================================================================

class CitizenPetitionTiming(str, Enum):
    """Citizen petition submission timing."""
    BEFORE_NDA_ACCEPTANCE = "before_nda"
    DURING_REVIEW_PRE_ADCOM = "during_pre_adcom"
    AFTER_ADCOM_POSITIVE = "after_adcom_positive"
    AFTER_ADCOM_NEGATIVE = "after_adcom_negative"
    AFTER_ADCOM_NOT_REQUIRED = "after_no_adcom"


class CitizenPetitionQuality(str, Enum):
    """Citizen petition quality grades."""
    HIGH = "high"      # KOL support + new data + third party
    MEDIUM = "medium"  # Partial support or reanalysis
    LOW = "low"        # Competitor only + existing data


class CitizenPetitionFDAResponse(str, Enum):
    """FDA response to citizen petition."""
    NO_RESPONSE = "no_response"
    ACKNOWLEDGED_REVIEWING = "reviewing"
    REQUESTED_ADDITIONAL_DATA = "additional_data"
    REQUESTED_ADCOM = "requested_adcom"
    DENIED = "denied"
    PARTIALLY_ACCEPTED = "partial"


__all__ = [
    # Data Collection (Wave 2)
    "SearchStatus",
    "SourceTier",
    "TrialRegion",
    "CRLReasonType",
    # Core
    "TimingSignal",
    "StrategyType",
    # CRL
    "CRLType",
    "CRLDelayCategory",
    "DisputeResolutionResult",
    # Clinical
    "EndpointType",
    "ClinicalQualityTier",
    "MentalHealthIndication",
    # Manufacturing
    "PAIStatus",
    # Drug
    "DrugClassification",
    "ApprovalType",
    "DrugType",
    # Market
    "MarketSize",
    # Citizen Petition
    "CitizenPetitionTiming",
    "CitizenPetitionQuality",
    "CitizenPetitionFDAResponse",
]
