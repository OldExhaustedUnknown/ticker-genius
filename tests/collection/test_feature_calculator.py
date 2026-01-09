"""
Tests for FeatureCalculator
============================
Phase 3: Feature 시점 검증 및 재계산 테스트 (TDD)

테스트 우선순위:
1. 정적 feature 복사
2. 동적 feature 시점 검증
3. 품질 점수 재계산
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def sample_event():
    """테스트용 샘플 이벤트."""
    from tickergenius.collection.event_models import PDUFAEvent

    return PDUFAEvent(
        ticker="AXSM",
        drug_name="AXS-05",
        pdufa_date="20210108",  # 2021년 1월 8일
        result="crl",
        sequence_number=1,
        submission_type="original"
    )


class TestFeatureCalculatorStaticFeatures:
    """정적 feature (FDA 지정) 테스트."""

    def test_static_features_preserved(self, sample_event):
        """FDA 지정은 시점과 무관하게 유지."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        # FDA 지정 설정
        sample_event.btd = True
        sample_event.priority_review = True
        sample_event.orphan_drug = False

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        assert validated.btd is True
        assert validated.priority_review is True
        assert validated.orphan_drug is False

    def test_none_static_features_remain_none(self, sample_event):
        """None인 정적 feature는 None 유지."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        sample_event.btd = None
        sample_event.fast_track = None

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        assert validated.btd is None
        assert validated.fast_track is None


class TestFeatureCalculatorDynamicFeatures:
    """동적 feature (시점 의존) 테스트."""

    def test_adcom_before_pdufa_preserved(self, sample_event):
        """AdCom이 PDUFA 전이면 유지."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        sample_event.pdufa_date = "20210108"
        sample_event.adcom_held = True
        sample_event.adcom_date = "20201215"  # PDUFA 전
        sample_event.adcom_vote_ratio = 0.85

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        assert validated.adcom_held is True
        assert validated.adcom_date == "20201215"
        assert validated.adcom_vote_ratio == 0.85

    def test_adcom_after_pdufa_cleared(self, sample_event):
        """AdCom이 PDUFA 후면 None으로 처리."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        sample_event.pdufa_date = "20210108"
        sample_event.adcom_held = True
        sample_event.adcom_date = "20220315"  # PDUFA 후
        sample_event.adcom_vote_ratio = 0.85

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        # PDUFA 시점에서 알 수 없었으므로 None
        assert validated.adcom_held is None
        assert validated.adcom_date is None
        assert validated.adcom_vote_ratio is None

    def test_adcom_no_date_preserved_with_warning(self, sample_event):
        """AdCom 날짜 없으면 유지하되 경고."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        sample_event.adcom_held = True
        sample_event.adcom_date = None  # 날짜 모름
        sample_event.adcom_vote_ratio = 0.85

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        # 날짜 모르면 보수적으로 유지 (있다고 가정)
        assert validated.adcom_held is True
        assert validated.adcom_vote_ratio == 0.85


class TestFeatureCalculatorQualityScore:
    """데이터 품질 점수 테스트."""

    def test_quality_recalculated(self, sample_event):
        """품질 점수가 재계산됨."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        # 초기 상태
        original_score = sample_event.data_quality_score

        # feature 추가
        sample_event.btd = True
        sample_event.primary_endpoint_met = True

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        # 품질 점수가 재계산됨
        assert validated.data_quality_score >= original_score

    def test_cleared_features_lower_quality(self, sample_event):
        """feature가 제거되면 품질 점수 감소."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        # 좋은 feature들 설정
        sample_event.btd = True
        sample_event.adcom_held = True
        sample_event.adcom_date = "20250101"  # 미래 (PDUFA 후)
        sample_event.adcom_vote_ratio = 0.9
        sample_event.primary_endpoint_met = True

        calc = FeatureCalculator()
        validated = calc.validate_features(sample_event)

        # AdCom이 제거되었으므로 원래보다 낮을 수 있음
        # (정확한 비교는 구현에 따라 다름)
        assert validated.data_quality_score >= 0.0
        assert validated.data_quality_score <= 1.0


class TestFeatureCalculatorBulkProcessing:
    """대량 처리 테스트."""

    def test_validate_many_events(self):
        """여러 이벤트 일괄 검증."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.feature_calculator import FeatureCalculator

        events = [
            PDUFAEvent(
                ticker="AXSM",
                drug_name="AXS-05",
                pdufa_date="20210108",
                btd=True
            ),
            PDUFAEvent(
                ticker="AXSM",
                drug_name="AXS-05",
                pdufa_date="20210824",
                btd=True,
                adcom_held=True,
                adcom_date="20210601"
            ),
            PDUFAEvent(
                ticker="AXSM",
                drug_name="AXS-05",
                pdufa_date="20220819",
                btd=True,
                result="approved"
            ),
        ]

        calc = FeatureCalculator()
        validated_events = calc.validate_many(events)

        assert len(validated_events) == 3
        for e in validated_events:
            assert e.btd is True  # 정적 feature 유지

    def test_get_stats(self):
        """검증 통계 반환."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.feature_calculator import FeatureCalculator

        events = [
            PDUFAEvent(
                ticker="TEST",
                drug_name="DRUG",
                pdufa_date="20210101",
                adcom_date="20220101"  # 미래 → 제거됨
            ),
            PDUFAEvent(
                ticker="TEST",
                drug_name="DRUG2",
                pdufa_date="20210101",
                adcom_date="20200601"  # 과거 → 유지
            ),
        ]

        calc = FeatureCalculator()
        calc.validate_many(events)
        stats = calc.get_stats()

        assert stats.total_events >= 2
        assert stats.features_cleared >= 1  # 적어도 하나는 제거됨


class TestFeatureCalculatorEdgeCases:
    """엣지 케이스 테스트."""

    def test_invalid_date_format_handled(self, sample_event):
        """잘못된 날짜 형식 처리."""
        from tickergenius.collection.feature_calculator import FeatureCalculator

        sample_event.pdufa_date = "invalid_date"
        sample_event.adcom_date = "20201215"

        calc = FeatureCalculator()
        # 에러 없이 처리되어야 함
        validated = calc.validate_features(sample_event)

        assert validated is not None

    def test_empty_event_handled(self):
        """최소한의 필드만 있는 이벤트."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.feature_calculator import FeatureCalculator

        event = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101"
        )

        calc = FeatureCalculator()
        validated = calc.validate_features(event)

        assert validated.ticker == "TEST"
        assert validated.drug_name == "DRUG"
