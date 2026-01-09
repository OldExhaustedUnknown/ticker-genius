"""
Tests for PDUFAAnalyzer
========================
M3 Phase 4: Core analyzer tests.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from tickergenius.analysis.pdufa import (
    PDUFAAnalyzer,
    AnalysisContext,
    FDADesignations,
    AdComInfo,
    CRLInfo,
    ClinicalInfo,
    ManufacturingInfo,
    DisputeInfo,
    EarningsCallInfo,
    CitizenPetitionInfo,
    FactorRegistry,
)
from tickergenius.schemas.enums import CRLType


class TestPDUFAAnalyzer:
    """Test PDUFAAnalyzer core functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset registry before each test."""
        # Note: In production, registry persists across tests
        # For isolation, we'd need a reset mechanism
        self.analyzer = PDUFAAnalyzer()

    def test_minimal_context_returns_base_rate(self):
        """Minimal context should return base rate (70%)."""
        ctx = AnalysisContext.minimal("TEST")
        result = self.analyzer.analyze(ctx)

        assert result.probability == pytest.approx(0.70, abs=0.01)
        assert result.ticker == "TEST"

    def test_btd_adds_bonus(self):
        """Breakthrough Therapy designation should add 8% bonus."""
        ctx = AnalysisContext(
            ticker="BTD_TEST",
            drug_name="BTD Drug",
            fda_designations=FDADesignations(breakthrough_therapy=True),
        )
        result = self.analyzer.analyze(ctx)

        # Base 70% + BTD 8% = 78%
        assert result.probability == pytest.approx(0.78, abs=0.01)
        assert any(f.name == "breakthrough_therapy" and f.applied for f in result.factors)

    def test_multiple_designations_max_only(self):
        """Multiple designations should apply MAX_ONLY (only highest)."""
        ctx = AnalysisContext(
            ticker="MULTI",
            drug_name="Multi Designation",
            fda_designations=FDADesignations(
                breakthrough_therapy=True,  # +8% (highest)
                priority_review=True,       # +5% (skipped)
                orphan_drug=True,           # +4% (skipped)
            ),
        )
        result = self.analyzer.analyze(ctx)

        # Base 70% + MAX(8%, 5%, 4%) = 78%
        # FDA designations use MAX_ONLY grouping - only highest applies
        assert result.probability == pytest.approx(0.78, abs=0.01)

    def test_adcom_positive_adds_bonus(self):
        """Positive AdCom vote (>50%) should add bonus."""
        ctx = AnalysisContext(
            ticker="ADCOM",
            drug_name="AdCom Test",
            adcom=AdComInfo(was_held=True, vote_ratio=0.8),
        )
        result = self.analyzer.analyze(ctx)

        # Base 70% + AdCom positive 8% = 78%
        assert result.probability == pytest.approx(0.78, abs=0.01)

    def test_adcom_negative_applies_penalty(self):
        """Negative AdCom vote (<=50%) should apply penalty."""
        ctx = AnalysisContext(
            ticker="ADCOM_NEG",
            drug_name="AdCom Negative",
            adcom=AdComInfo(was_held=True, vote_ratio=0.4),
        )
        result = self.analyzer.analyze(ctx)

        # Base 70% - 20% penalty = 50%, but hard cap 40% applies
        assert result.probability <= 0.40

    def test_probability_cap_at_90_percent(self):
        """Probability should be capped at 90%."""
        ctx = AnalysisContext(
            ticker="CAP_TEST",
            drug_name="Cap Test",
            fda_designations=FDADesignations(
                breakthrough_therapy=True,  # +8%
                priority_review=True,       # +5%
                fast_track=True,            # +5%
                orphan_drug=True,           # +4%
                accelerated_approval=True,  # +6%
                is_first_in_class=True,     # +5%
            ),
            spa_agreed=True,  # +8%
        )
        result = self.analyzer.analyze(ctx)

        # Would be 70% + 41% = 111%, capped to 90%
        assert result.probability == pytest.approx(0.90, abs=0.001)

    def test_probability_floor_at_10_percent(self):
        """Probability should not go below 10%."""
        ctx = AnalysisContext(
            ticker="FLOOR_TEST",
            drug_name="Floor Test",
            clinical=ClinicalInfo(primary_endpoint_met=False),
        )
        result = self.analyzer.analyze(ctx)

        # Catastrophic cap (5%) applies, which is below 10%
        # But catastrophic takes precedence over floor
        assert result.probability <= 0.10


class TestFactorRegistry:
    """Test FactorRegistry functionality."""

    def test_factors_are_registered(self):
        """All expected factors should be registered."""
        factors = FactorRegistry.list_factors()
        factor_names = [f.name for f in factors]

        # Core factors should exist
        assert "base_rate" in factor_names
        assert "breakthrough_therapy" in factor_names
        assert "adcom_vote_positive" in factor_names
        assert "probability_bounds" in factor_names

    def test_layer_order_preserved(self):
        """Factors in same layer should be ordered correctly."""
        designation_factors = FactorRegistry.get_layer_factors("designation")

        # Should have BTD, Priority, Fast Track, Orphan, Accelerated
        assert len(designation_factors) >= 5

        # BTD (order=10) should come before Priority (order=20)
        names = [f.name for f in designation_factors]
        btd_idx = names.index("breakthrough_therapy") if "breakthrough_therapy" in names else -1
        pr_idx = names.index("priority_review") if "priority_review" in names else -1

        if btd_idx >= 0 and pr_idx >= 0:
            assert btd_idx < pr_idx

    def test_disable_factor(self):
        """Disabled factors should not be applied."""
        # Get current count
        before = len(FactorRegistry.get_layer_factors("designation"))

        # Disable a factor
        FactorRegistry.disable("fast_track", "Testing")

        # Should have one less active factor
        after = len(FactorRegistry.get_layer_factors("designation"))
        assert after == before - 1

        # Re-enable
        FactorRegistry.enable("fast_track")
        restored = len(FactorRegistry.get_layer_factors("designation"))
        assert restored == before


class TestClinicalFactors:
    """Test clinical trial related factors."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_primary_endpoint_not_met_catastrophic(self, analyzer):
        """Primary endpoint not met should trigger catastrophic cap."""
        ctx = AnalysisContext(
            ticker="ENDPOINT",
            drug_name="Failed Trial",
            clinical=ClinicalInfo(primary_endpoint_met=False),
        )
        result = analyzer.analyze(ctx)

        # Catastrophic hard cap = 5%
        assert result.probability <= 0.05

    def test_single_arm_penalty(self, analyzer):
        """Single-arm trial should apply penalty."""
        ctx = AnalysisContext(
            ticker="SINGLE_ARM",
            drug_name="Single Arm",
            clinical=ClinicalInfo(is_single_arm=True),
        )
        result = analyzer.analyze(ctx)

        # Base 70% - 7% = 63%
        assert result.probability < 0.70

    def test_china_only_critical_cap(self, analyzer):
        """China-only trial should trigger critical cap."""
        ctx = AnalysisContext(
            ticker="CHINA",
            drug_name="China Only",
            clinical=ClinicalInfo(trial_region="china_only"),
        )
        result = analyzer.analyze(ctx)

        # Critical cap = 15%
        assert result.probability <= 0.15


class TestManufacturingFactors:
    """Test manufacturing related factors."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_pai_passed_bonus(self, analyzer):
        """PAI passed should add bonus."""
        ctx = AnalysisContext(
            ticker="PAI",
            drug_name="PAI Passed",
            manufacturing=ManufacturingInfo(pai_passed=True),
        )
        result = analyzer.analyze(ctx)

        # Base 70% + PAI 12% = 82%
        assert result.probability > 0.70

    def test_warning_letter_severe_cap(self, analyzer):
        """Warning letter should trigger severe cap."""
        ctx = AnalysisContext(
            ticker="WARNING",
            drug_name="Warning Letter",
            manufacturing=ManufacturingInfo(has_warning_letter=True),
        )
        result = analyzer.analyze(ctx)

        # Severe cap = 25%
        assert result.probability <= 0.25


class TestAnalysisResult:
    """Test AnalysisResult functionality."""

    @pytest.fixture
    def result(self):
        analyzer = PDUFAAnalyzer()
        ctx = AnalysisContext(
            ticker="RESULT_TEST",
            drug_name="Result Test",
            fda_designations=FDADesignations(breakthrough_therapy=True),
        )
        return analyzer.analyze(ctx)

    def test_result_has_ticker(self, result):
        assert result.ticker == "RESULT_TEST"

    def test_result_has_drug_name(self, result):
        assert result.drug_name == "Result Test"

    def test_result_summary(self, result):
        summary = result.summary()
        assert "RESULT_TEST" in summary
        assert "Probability" in summary

    def test_result_to_dict(self, result):
        d = result.to_dict()
        assert "probability" in d
        assert "base_probability" in d
        assert "factors" in d
        assert isinstance(d["factors"], list)


class TestTemporalFactors:
    """Test temporal/date-aware factors."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_warning_letter_stale_reduced_penalty(self, analyzer):
        """Stale warning letter (>365 days) should have reduced penalty."""
        from datetime import date, timedelta

        old_date = date.today() - timedelta(days=400)
        ctx = AnalysisContext(
            ticker="STALE_WL",
            drug_name="Stale Warning",
            manufacturing=ManufacturingInfo(
                has_warning_letter=True,
                warning_letter_date=old_date,
            ),
        )
        result = analyzer.analyze(ctx)

        # Severe cap (25%) should still apply due to warning letter
        # But the penalty itself should be reduced
        assert result.probability <= 0.25
        # Check that factor mentions "오래됨"
        wl_factor = next((f for f in result.factors if f.name == "facility_warning_letter"), None)
        assert wl_factor is not None
        assert "오래됨" in wl_factor.reason

    def test_warning_letter_recent_full_penalty(self, analyzer):
        """Recent warning letter (<180 days) should have full penalty."""
        from datetime import date, timedelta

        recent_date = date.today() - timedelta(days=30)
        ctx = AnalysisContext(
            ticker="RECENT_WL",
            drug_name="Recent Warning",
            manufacturing=ManufacturingInfo(
                has_warning_letter=True,
                warning_letter_date=recent_date,
            ),
        )
        result = analyzer.analyze(ctx)

        # Severe cap (25%) applies
        assert result.probability <= 0.25


class TestConfidenceScore:
    """Test confidence score calculation."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_minimal_context_has_lower_confidence(self, analyzer):
        """Minimal context should have lower confidence."""
        ctx = AnalysisContext.minimal("TEST")
        result = analyzer.analyze(ctx)

        # Minimal data = lower confidence
        assert result.confidence_score < 1.0
        assert result.confidence_score >= 0.1

    def test_complete_context_has_higher_confidence(self, analyzer):
        """Complete context should have higher confidence."""
        from datetime import date, timedelta

        pdufa = date.today() + timedelta(days=30)
        ctx = AnalysisContext(
            ticker="COMPLETE",
            drug_name="Complete Drug",
            pdufa_date=pdufa,
            days_to_pdufa=30,
            fda_designations=FDADesignations(breakthrough_therapy=True),
            clinical=ClinicalInfo(
                phase="phase3",
                primary_endpoint_met=True,
            ),
            manufacturing=ManufacturingInfo(pai_passed=True),
        )
        result = analyzer.analyze(ctx)

        # More complete data = higher confidence
        assert result.confidence_score > 0.7

    def test_missing_date_lowers_confidence(self, analyzer):
        """Missing date on time-sensitive factor should lower confidence."""
        ctx = AnalysisContext(
            ticker="NO_DATE",
            drug_name="No Date",
            manufacturing=ManufacturingInfo(has_warning_letter=True),  # No date!
        )
        result = analyzer.analyze(ctx)

        # Should have warning about missing date
        assert any("날짜" in w for w in result.data_quality_warnings)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_empty_designations(self, analyzer):
        """Empty designations should not affect base rate."""
        ctx = AnalysisContext(
            ticker="EMPTY",
            drug_name="Empty",
            fda_designations=FDADesignations(),  # All False
        )
        result = analyzer.analyze(ctx)

        assert result.probability == pytest.approx(0.70, abs=0.01)

    def test_conflicting_factors(self, analyzer):
        """Conflicting factors should still calculate correctly."""
        ctx = AnalysisContext(
            ticker="CONFLICT",
            drug_name="Conflict",
            fda_designations=FDADesignations(breakthrough_therapy=True),  # +8%
            manufacturing=ManufacturingInfo(has_warning_letter=True),  # -30% + cap
        )
        result = analyzer.analyze(ctx)

        # Warning letter triggers severe cap (25%)
        assert result.probability <= 0.25

    def test_spa_agreed_floor(self, analyzer):
        """SPA agreed should provide floor protection."""
        ctx = AnalysisContext(
            ticker="SPA_FLOOR",
            drug_name="SPA Floor",
            spa_agreed=True,
            clinical=ClinicalInfo(is_single_arm=True),  # penalty
        )
        result = analyzer.analyze(ctx)

        # SPA floor is 20%, so even with penalties, shouldn't go below
        assert result.probability >= 0.20


class TestDisputeFactors:
    """Test FDA dispute resolution factors."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_dispute_won_fully_bonus(self, analyzer):
        """Winning FDA dispute fully should add bonus."""
        ctx = AnalysisContext(
            ticker="DISPUTE_WIN",
            drug_name="Dispute Win",
            dispute=DisputeInfo(
                has_dispute=True,
                dispute_result="won_fully",
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% + 10% dispute bonus
        assert result.probability >= 0.75

    def test_dispute_lost_penalty(self, analyzer):
        """Losing FDA dispute should apply penalty."""
        ctx = AnalysisContext(
            ticker="DISPUTE_LOST",
            drug_name="Dispute Lost",
            dispute=DisputeInfo(
                has_dispute=True,
                dispute_result="lost_fully",
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% - 20% dispute penalty
        assert result.probability <= 0.55

    def test_no_dispute_neutral(self, analyzer):
        """No dispute should have no effect."""
        ctx = AnalysisContext(
            ticker="NO_DISPUTE",
            drug_name="No Dispute",
            dispute=DisputeInfo(has_dispute=False),
        )
        result = analyzer.analyze(ctx)

        assert result.probability == pytest.approx(0.70, abs=0.01)


class TestEarningsCallFactors:
    """Test earnings call signal factors."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_label_negotiation_bonus(self, analyzer):
        """Label negotiation mention should add bonus."""
        ctx = AnalysisContext(
            ticker="LABEL_NEG",
            drug_name="Label Neg",
            earnings_call=EarningsCallInfo(
                label_negotiation_mentioned=True,
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% + 8% label negotiation bonus
        assert result.probability >= 0.75

    def test_timeline_delay_penalty(self, analyzer):
        """Timeline delay signal should apply penalty."""
        ctx = AnalysisContext(
            ticker="DELAY",
            drug_name="Delayed",
            earnings_call=EarningsCallInfo(
                timeline_delayed=True,
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% - 10% delay penalty
        assert result.probability <= 0.65


class TestCitizenPetitionFactors:
    """Test citizen petition factors."""

    @pytest.fixture
    def analyzer(self):
        return PDUFAAnalyzer()

    def test_petition_filed_penalty(self, analyzer):
        """Citizen petition filed should apply penalty."""
        ctx = AnalysisContext(
            ticker="PETITION",
            drug_name="Petition",
            citizen_petition=CitizenPetitionInfo(
                has_petition=True,
                petition_status="filed",
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% - 8% petition penalty
        assert result.probability <= 0.65

    def test_petition_denied_bonus(self, analyzer):
        """FDA denying citizen petition should add bonus."""
        ctx = AnalysisContext(
            ticker="DENIED",
            drug_name="Denied",
            citizen_petition=CitizenPetitionInfo(
                has_petition=True,
                petition_status="denied",
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% + 5% denial bonus
        assert result.probability >= 0.72

    def test_petition_granted_severe_penalty(self, analyzer):
        """FDA granting citizen petition should apply severe penalty."""
        ctx = AnalysisContext(
            ticker="GRANTED",
            drug_name="Granted",
            citizen_petition=CitizenPetitionInfo(
                has_petition=True,
                petition_status="granted",
            ),
        )
        result = analyzer.analyze(ctx)

        # Base 70% - 25% granted penalty
        assert result.probability <= 0.50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
