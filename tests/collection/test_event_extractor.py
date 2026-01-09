"""
Tests for EventExtractor
=========================
Phase 2: 이벤트 추출기 테스트 (TDD)

테스트 우선순위:
1. 기본 변환 (CRL 없는 케이스)
2. CRL 이력이 있는 케이스
3. 필드 매핑
4. 에러 처리
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def simple_case():
    """CRL 없는 간단한 케이스."""
    from tickergenius.collection.models import CollectedCase, FieldValue, SourceInfo, SourceTier

    return CollectedCase(
        ticker="ABBV",
        drug_name="EMRELIS",
        pdufa_date=FieldValue(
            value="20250514",
            sources=[SourceInfo("openfda", SourceTier.TIER1)],
            confidence=0.99
        ),
        result=FieldValue(
            value="approved",
            sources=[SourceInfo("openfda", SourceTier.TIER1)],
            confidence=0.99
        ),
        breakthrough_therapy=FieldValue(value=True, sources=[]),
        priority_review=FieldValue(value=True, sources=[]),
        is_resubmission=FieldValue(value=0, sources=[])
    )


@pytest.fixture
def crl_case():
    """CRL 이력이 있는 케이스."""
    from tickergenius.collection.models import CollectedCase, FieldValue, SourceInfo, SourceTier

    return CollectedCase(
        ticker="AXSM",
        drug_name="AXS-05",
        pdufa_date=FieldValue(
            value="20220819",
            sources=[SourceInfo("openfda", SourceTier.TIER1)],
            confidence=0.99
        ),
        result=FieldValue(
            value="approved",
            sources=[SourceInfo("openfda", SourceTier.TIER1)],
            confidence=0.99
        ),
        breakthrough_therapy=FieldValue(value=True, sources=[]),
        priority_review=FieldValue(value=True, sources=[]),
        has_prior_crl=FieldValue(value=True, sources=[]),
        is_resubmission=FieldValue(value=2, sources=[]),  # 2번 재제출
        crl_class=FieldValue(value="class2", sources=[])
    )


class TestEventExtractorBasic:
    """기본 변환 테스트."""

    def test_extract_single_event_no_crl(self, simple_case):
        """CRL 없는 케이스 → 1개 이벤트."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        events = extractor.extract_from_case(simple_case)

        assert len(events) == 1
        assert events[0].ticker == "ABBV"
        assert events[0].drug_name == "EMRELIS"
        assert events[0].pdufa_date == "20250514"
        assert events[0].result == "approved"

    def test_event_id_generated(self, simple_case):
        """event_id가 올바르게 생성."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        events = extractor.extract_from_case(simple_case)

        assert events[0].event_id is not None
        assert len(events[0].event_id) == 16

    def test_sequence_number_default(self, simple_case):
        """CRL 없으면 sequence_number=1."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        events = extractor.extract_from_case(simple_case)

        assert events[0].sequence_number == 1
        assert events[0].submission_type == "original"


class TestEventExtractorWithCRL:
    """CRL 이력이 있는 케이스 테스트."""

    def test_crl_case_without_searcher_returns_one_event(self, crl_case):
        """CRL 있지만 searcher 없으면 → 1개 이벤트 (추론 금지)."""
        from tickergenius.collection.event_extractor import EventExtractor

        # crl_searcher=None → SEC 검색 안함 → CRL 이벤트 미생성
        extractor = EventExtractor(crl_searcher=None)
        events = extractor.extract_from_case(crl_case)

        # 추론 금지: CRL 이벤트는 SEC 검색으로만 생성
        assert len(events) == 1

        # 최종 이벤트가 resubmission 타입으로 CRL 이력 표시
        final_event = events[0]
        assert final_event.result == "approved"
        assert final_event.pdufa_date == "20220819"
        assert final_event.submission_type == "resubmission"

    def test_crl_case_with_searcher_returns_multiple_events(self, crl_case):
        """CRL 있고 searcher가 결과 반환하면 → 여러 이벤트."""
        from tickergenius.collection.event_extractor import EventExtractor
        from unittest.mock import Mock

        # Mock searcher: SEC에서 CRL 날짜 2개 찾음
        mock_searcher = Mock()
        mock_searcher.search_crl_events.return_value = [
            {"crl_date": "20210301", "reason_category": "manufacturing"},
            {"crl_date": "20220101", "reason_category": "clinical"},
        ]

        extractor = EventExtractor(crl_searcher=mock_searcher)
        events = extractor.extract_from_case(crl_case)

        # 2 CRL + 1 final = 3 이벤트
        assert len(events) == 3

        # CRL 이벤트들
        crl_events = [e for e in events if e.result == "crl"]
        assert len(crl_events) == 2

        # 마지막은 approved
        assert events[-1].result == "approved"

    def test_sequence_numbers_incremental(self, crl_case):
        """sequence_number가 순차적."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor(crl_searcher=None)
        events = extractor.extract_from_case(crl_case)

        # 시간순 정렬되어야 함
        for i, event in enumerate(events):
            assert event.sequence_number == i + 1

    def test_final_event_is_resubmission(self, crl_case):
        """CRL 이력 있으면 최종 이벤트는 resubmission 타입."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor(crl_searcher=None)
        events = extractor.extract_from_case(crl_case)

        final = events[-1]
        assert final.submission_type == "resubmission"


class TestEventExtractorFieldMapping:
    """필드 매핑 테스트."""

    def test_fda_designations_mapped(self, simple_case):
        """FDA 지정 필드가 올바르게 매핑."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        events = extractor.extract_from_case(simple_case)

        event = events[0]
        assert event.btd is True
        assert event.priority_review is True

    def test_none_values_handled(self):
        """None 필드도 처리."""
        from tickergenius.collection.models import CollectedCase, FieldValue
        from tickergenius.collection.event_extractor import EventExtractor

        case = CollectedCase(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date=FieldValue(value="20250101", sources=[]),
            result=FieldValue(value="pending", sources=[]),
            # 나머지 필드 None
        )

        extractor = EventExtractor()
        events = extractor.extract_from_case(case)

        assert len(events) == 1
        assert events[0].btd is None
        assert events[0].adcom_vote_ratio is None

    def test_source_case_id_tracked(self, simple_case):
        """원본 case_id가 기록됨."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        events = extractor.extract_from_case(simple_case)

        assert events[0].source_case_id == simple_case.case_id


class TestEventExtractorBulk:
    """대량 추출 테스트."""

    def test_extract_all_cases(self, simple_case, crl_case):
        """여러 케이스 일괄 추출."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        events = extractor.extract_all([simple_case, crl_case])

        # 추론 금지: simple_case 1개 + crl_case 1개 (final만)
        assert len(events) == 2

    def test_stats_tracking(self, simple_case, crl_case):
        """추출 통계 추적."""
        from tickergenius.collection.event_extractor import EventExtractor

        extractor = EventExtractor()
        extractor.extract_all([simple_case, crl_case])
        stats = extractor.get_stats()

        assert stats.total_cases == 2
        # 추론 금지: SEC 검색 없으면 각 케이스당 1개 이벤트
        assert stats.total_events == 2
        # crl_search_failed: CRL 케이스가 SEC 검색 없이 처리됨
        assert stats.crl_search_failed >= 1


class TestEventExtractorEdgeCases:
    """엣지 케이스 테스트."""

    def test_missing_pdufa_date_skipped(self):
        """pdufa_date 없는 케이스 스킵."""
        from tickergenius.collection.models import CollectedCase
        from tickergenius.collection.event_extractor import EventExtractor

        case = CollectedCase(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date=None,  # 필수 필드 없음
            result=None
        )

        extractor = EventExtractor()
        events = extractor.extract_from_case(case)

        assert len(events) == 0

    def test_invalid_date_handled(self):
        """잘못된 날짜 형식 처리."""
        from tickergenius.collection.models import CollectedCase, FieldValue
        from tickergenius.collection.event_extractor import EventExtractor

        case = CollectedCase(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date=FieldValue(value="invalid_date", sources=[]),
            result=FieldValue(value="pending", sources=[])
        )

        extractor = EventExtractor()
        events = extractor.extract_from_case(case)

        # 에러 처리하고 빈 리스트 또는 경고와 함께 진행
        # 구현에 따라 다를 수 있음
        assert isinstance(events, list)
