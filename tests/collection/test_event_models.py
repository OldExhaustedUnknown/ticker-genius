"""
Tests for PDUFAEvent Model
===========================
Phase 1: 이벤트 모델 테스트 (TDD)

테스트 우선순위:
1. event_id 생성 로직
2. 품질 점수 계산
3. 직렬화/역직렬화
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestPDUFAEventCreation:
    """PDUFAEvent 생성 테스트."""

    def test_event_id_auto_generation(self):
        """event_id가 자동 생성되는지 확인."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819"
        )

        assert event.event_id is not None
        assert len(event.event_id) == 16  # MD5 해시 16자
        assert event.event_id != ""

    def test_event_id_deterministic(self):
        """같은 입력이면 같은 event_id 생성."""
        from tickergenius.collection.event_models import PDUFAEvent

        event1 = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819"
        )
        event2 = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819"
        )

        assert event1.event_id == event2.event_id

    def test_event_id_different_for_different_dates(self):
        """다른 PDUFA 날짜면 다른 event_id."""
        from tickergenius.collection.event_models import PDUFAEvent

        event1 = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20210108"  # 첫 번째 PDUFA
        )
        event2 = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819"  # 두 번째 PDUFA
        )

        assert event1.event_id != event2.event_id

    def test_event_id_case_insensitive(self):
        """ticker/drug_name 대소문자 무관하게 같은 ID."""
        from tickergenius.collection.event_models import PDUFAEvent

        event1 = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819"
        )
        event2 = PDUFAEvent(
            ticker="axsm",
            drug_name="axs-05",
            pdufa_date="20220819"
        )

        assert event1.event_id == event2.event_id


class TestPDUFAEventQualityScore:
    """데이터 품질 점수 테스트."""

    def test_minimal_event_has_base_score(self):
        """필수 필드만 있으면 기본 점수."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101"
        )

        # 필수 필드만 있으면 기본 점수 (0.3)
        assert event.data_quality_score >= 0.3
        assert event.data_quality_score < 0.5

    def test_quality_increases_with_important_fields(self):
        """중요 필드가 채워질수록 점수 증가."""
        from tickergenius.collection.event_models import PDUFAEvent

        minimal = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101"
        )

        with_btd = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101",
            btd=True
        )

        with_more = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101",
            btd=True,
            primary_endpoint_met=True,
            priority_review=True
        )

        assert with_btd.data_quality_score > minimal.data_quality_score
        assert with_more.data_quality_score > with_btd.data_quality_score

    def test_quality_score_max_is_one(self):
        """품질 점수 최대값은 1.0."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101",
            result="approved",
            btd=True,
            priority_review=True,
            fast_track=True,
            orphan_drug=True,
            accelerated_approval=True,
            primary_endpoint_met=True,
            adcom_vote_ratio=0.9,
            pai_passed=True
        )

        assert event.data_quality_score <= 1.0


class TestPDUFAEventSerialization:
    """직렬화/역직렬화 테스트."""

    def test_to_dict_contains_all_fields(self):
        """to_dict()가 모든 필드를 포함."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819",
            result="approved",
            btd=True,
            sequence_number=3
        )

        d = event.to_dict()

        assert d["event_id"] == event.event_id
        assert d["ticker"] == "AXSM"
        assert d["drug_name"] == "AXS-05"
        assert d["pdufa_date"] == "20220819"
        assert d["result"] == "approved"
        assert d["btd"] is True
        assert d["sequence_number"] == 3

    def test_from_dict_round_trip(self):
        """to_dict → from_dict 왕복 시 동일."""
        from tickergenius.collection.event_models import PDUFAEvent

        original = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819",
            result="approved",
            btd=True,
            priority_review=True,
            sequence_number=3,
            submission_type="resubmission"
        )

        d = original.to_dict()
        restored = PDUFAEvent.from_dict(d)

        assert restored.event_id == original.event_id
        assert restored.ticker == original.ticker
        assert restored.drug_name == original.drug_name
        assert restored.pdufa_date == original.pdufa_date
        assert restored.result == original.result
        assert restored.btd == original.btd
        assert restored.sequence_number == original.sequence_number

    def test_to_dict_handles_none_values(self):
        """None 값이 올바르게 직렬화."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101"
            # 나머지는 None
        )

        d = event.to_dict()

        assert d["result"] is None
        assert d["btd"] is None
        assert d["adcom_vote_ratio"] is None


class TestPDUFAEventSubmissionContext:
    """제출 컨텍스트 테스트."""

    def test_default_is_original_submission(self):
        """기본값은 최초 제출."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101"
        )

        assert event.sequence_number == 1
        assert event.submission_type == "original"

    def test_resubmission_context(self):
        """재제출 컨텍스트 설정."""
        from tickergenius.collection.event_models import PDUFAEvent

        event = PDUFAEvent(
            ticker="AXSM",
            drug_name="AXS-05",
            pdufa_date="20220819",
            sequence_number=3,
            submission_type="resubmission",
            prior_crl_reason="cmc"
        )

        assert event.sequence_number == 3
        assert event.submission_type == "resubmission"
        assert event.prior_crl_reason == "cmc"
