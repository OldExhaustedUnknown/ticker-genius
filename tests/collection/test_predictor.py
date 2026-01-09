"""
Tests for PDUFAPredictor and RiskClassifier
============================================
Phase 4: CRL 예측 모듈 테스트 (TDD)

테스트 우선순위:
1. 이벤트 → 컨텍스트 변환
2. CRL 확률 예측
3. 리스크 분류
"""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def sample_event():
    """테스트용 샘플 이벤트."""
    from tickergenius.collection.event_models import PDUFAEvent

    return PDUFAEvent(
        ticker="AXSM",
        drug_name="AXS-05",
        pdufa_date="20220819",
        result="approved",
        btd=True,
        priority_review=True,
        primary_endpoint_met=True,
        sequence_number=3,
        submission_type="resubmission"
    )


@pytest.fixture
def high_risk_event():
    """CRL 위험이 높은 이벤트."""
    from tickergenius.collection.event_models import PDUFAEvent

    return PDUFAEvent(
        ticker="HIGH",
        drug_name="RISK-01",
        pdufa_date="20250101",
        result=None,  # pending
        btd=False,
        priority_review=False,
        primary_endpoint_met=False,  # 엔드포인트 미충족
        adcom_held=True,
        adcom_vote_ratio=0.3,  # 낮은 투표 비율
        pai_passed=False,
        warning_letter_active=True
    )


class TestEventToContext:
    """이벤트 → 컨텍스트 변환 테스트."""

    def test_basic_fields_mapped(self, sample_event):
        """기본 필드가 올바르게 매핑되는지."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        context = predictor._event_to_context(sample_event)

        assert context.ticker == "AXSM"
        assert context.drug_name == "AXS-05"

    def test_fda_designations_mapped(self, sample_event):
        """FDA 지정이 올바르게 매핑되는지."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        context = predictor._event_to_context(sample_event)

        assert context.fda_designations.breakthrough_therapy is True
        assert context.fda_designations.priority_review is True

    def test_clinical_info_mapped(self, sample_event):
        """임상 정보가 올바르게 매핑되는지."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        context = predictor._event_to_context(sample_event)

        assert context.clinical.primary_endpoint_met is True

    def test_adcom_info_mapped(self):
        """AdCom 정보가 올바르게 매핑되는지."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.predictor import PDUFAPredictor

        event = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101",
            adcom_held=True,
            adcom_date="20241215",
            adcom_vote_ratio=0.85
        )

        predictor = PDUFAPredictor()
        context = predictor._event_to_context(event)

        assert context.adcom.was_held is True
        assert context.adcom.vote_ratio == 0.85

    def test_resubmission_mapped(self, sample_event):
        """재제출 정보가 올바르게 매핑되는지."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        context = predictor._event_to_context(sample_event)

        assert context.is_resubmission is True


class TestCRLPrediction:
    """CRL 예측 테스트."""

    def test_predict_returns_prediction(self, sample_event):
        """예측 결과가 PDUFAPrediction 타입인지."""
        from tickergenius.collection.predictor import PDUFAPredictor, PDUFAPrediction

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        assert isinstance(prediction, PDUFAPrediction)

    def test_prediction_has_probability(self, sample_event):
        """예측 결과에 확률이 포함되는지."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        assert 0.0 <= prediction.crl_probability <= 1.0

    def test_prediction_has_confidence(self, sample_event):
        """예측 결과에 신뢰도가 포함되는지."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        assert 0.0 <= prediction.confidence <= 1.0

    def test_good_event_low_crl_probability(self, sample_event):
        """좋은 이벤트는 낮은 CRL 확률."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        # BTD + Priority + Endpoint Met = 좋은 징후
        assert prediction.crl_probability < 0.5

    def test_bad_event_high_crl_probability(self, high_risk_event):
        """나쁜 이벤트는 높은 CRL 확률."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(high_risk_event)

        # Endpoint 미충족 + 낮은 AdCom 투표 = 나쁜 징후
        assert prediction.crl_probability > 0.3


class TestRiskClassifier:
    """리스크 분류 테스트."""

    def test_high_risk_classification(self):
        """HIGH 리스크 분류."""
        from tickergenius.collection.predictor import RiskClassifier

        classifier = RiskClassifier()
        level = classifier.classify(0.55)

        assert level == "HIGH"

    def test_elevated_risk_classification(self):
        """ELEVATED 리스크 분류."""
        from tickergenius.collection.predictor import RiskClassifier

        classifier = RiskClassifier()
        level = classifier.classify(0.35)

        assert level == "ELEVATED"

    def test_moderate_risk_classification(self):
        """MODERATE 리스크 분류."""
        from tickergenius.collection.predictor import RiskClassifier

        classifier = RiskClassifier()
        level = classifier.classify(0.20)

        assert level == "MODERATE"

    def test_low_risk_classification(self):
        """LOW 리스크 분류."""
        from tickergenius.collection.predictor import RiskClassifier

        classifier = RiskClassifier()
        level = classifier.classify(0.10)

        assert level == "LOW"

    def test_edge_case_50_percent(self):
        """경계값 50% 처리."""
        from tickergenius.collection.predictor import RiskClassifier

        classifier = RiskClassifier()
        level = classifier.classify(0.50)

        # 50% 이상은 HIGH
        assert level == "HIGH"

    def test_edge_case_30_percent(self):
        """경계값 30% 처리."""
        from tickergenius.collection.predictor import RiskClassifier

        classifier = RiskClassifier()
        level = classifier.classify(0.30)

        # 30% 이상은 ELEVATED
        assert level == "ELEVATED"


class TestPredictionIntegration:
    """통합 테스트."""

    def test_predict_includes_risk_level(self, sample_event):
        """예측 결과에 리스크 등급 포함."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        assert prediction.risk_level in ["HIGH", "ELEVATED", "MODERATE", "LOW"]

    def test_predict_includes_factors(self, sample_event):
        """예측 결과에 요인 목록 포함."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        assert isinstance(prediction.factors, list)

    def test_explain_prediction(self, sample_event):
        """예측 설명 생성."""
        from tickergenius.collection.predictor import PDUFAPredictor

        predictor = PDUFAPredictor()
        prediction = predictor.predict(sample_event)

        explanation = predictor.explain(prediction)

        assert isinstance(explanation, str)
        assert len(explanation) > 0
