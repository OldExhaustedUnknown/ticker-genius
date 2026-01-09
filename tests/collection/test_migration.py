"""
Tests for Data Migration
=========================
Step B: CollectedCase → PDUFAEvent 마이그레이션 테스트

테스트 우선순위:
1. JSON 로딩 및 파싱
2. 이벤트 추출
3. 저장 및 통계
"""

import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """임시 디렉토리."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_collected_json():
    """샘플 수집 데이터 JSON."""
    return {
        "case_id": "test123",
        "ticker": "TEST",
        "drug_name": "DRUG-01",
        "pdufa_date": {
            "value": "20250101",
            "confidence": 0.99,
            "sources": ["openfda"],
            "needs_review": False,
            "conflicts": []
        },
        "result": {
            "value": "approved",
            "confidence": 0.99,
            "sources": ["openfda"],
            "needs_review": False,
            "conflicts": []
        },
        "breakthrough_therapy": {
            "value": True,
            "confidence": 0.75,
            "sources": ["legacy_v12"],
            "needs_review": True,
            "conflicts": []
        },
        "priority_review": {
            "value": True,
            "confidence": 0.75,
            "sources": ["legacy_v12"],
            "needs_review": True,
            "conflicts": []
        },
        "fast_track": None,
        "orphan_drug": None,
        "accelerated_approval": None,
        "phase": None,
        "primary_endpoint_met": None,
        "nct_id": None,
        "adcom_held": None,
        "adcom_date": None,
        "adcom_vote_ratio": None,
        "has_prior_crl": None,
        "crl_class": None,
        "is_resubmission": {
            "value": 0,
            "confidence": 0.75,
            "sources": ["legacy_v12"],
            "needs_review": False,
            "conflicts": []
        },
        "pai_passed": None,
        "has_warning_letter": None,
        "warning_letter_date": None,
        "collected_at": "2026-01-09T00:00:00",
        "collection_version": "1.0"
    }


@pytest.fixture
def sample_crl_case_json():
    """CRL 이력이 있는 샘플."""
    return {
        "case_id": "crl123",
        "ticker": "AXSM",
        "drug_name": "AXS-05",
        "pdufa_date": {
            "value": "20220819",
            "confidence": 0.99,
            "sources": ["openfda"],
            "needs_review": False,
            "conflicts": []
        },
        "result": {
            "value": "approved",
            "confidence": 0.99,
            "sources": ["openfda"],
            "needs_review": False,
            "conflicts": []
        },
        "breakthrough_therapy": {"value": True, "confidence": 0.9, "sources": ["sec"], "needs_review": False, "conflicts": []},
        "priority_review": {"value": True, "confidence": 0.9, "sources": ["sec"], "needs_review": False, "conflicts": []},
        "fast_track": None,
        "orphan_drug": None,
        "accelerated_approval": None,
        "phase": None,
        "primary_endpoint_met": {"value": True, "confidence": 0.8, "sources": ["sec"], "needs_review": False, "conflicts": []},
        "nct_id": None,
        "adcom_held": None,
        "adcom_date": None,
        "adcom_vote_ratio": None,
        "has_prior_crl": {"value": True, "confidence": 0.9, "sources": ["sec"], "needs_review": False, "conflicts": []},
        "crl_class": {"value": 2, "confidence": 0.75, "sources": ["legacy_v12"], "needs_review": False, "conflicts": []},
        "is_resubmission": {"value": 2, "confidence": 0.9, "sources": ["sec"], "needs_review": False, "conflicts": []},
        "pai_passed": None,
        "has_warning_letter": None,
        "warning_letter_date": None,
        "collected_at": "2026-01-09T00:00:00",
        "collection_version": "1.0"
    }


class TestMigrationLoader:
    """JSON 로딩 테스트."""

    def test_load_single_json(self, temp_dir, sample_collected_json):
        """단일 JSON 파일 로드."""
        from tickergenius.collection.migration import MigrationRunner

        # JSON 파일 생성
        json_file = temp_dir / "TEST_test123.json"
        with open(json_file, "w") as f:
            json.dump(sample_collected_json, f)

        runner = MigrationRunner(source_dir=temp_dir)
        cases = runner.load_cases()

        assert len(cases) == 1
        assert cases[0].ticker == "TEST"
        assert cases[0].drug_name == "DRUG-01"

    def test_load_multiple_jsons(self, temp_dir, sample_collected_json):
        """여러 JSON 파일 로드."""
        from tickergenius.collection.migration import MigrationRunner

        # 여러 JSON 파일 생성
        for i in range(3):
            data = sample_collected_json.copy()
            data["case_id"] = f"test{i}"
            data["drug_name"] = f"DRUG-{i:02d}"
            json_file = temp_dir / f"TEST_test{i}.json"
            with open(json_file, "w") as f:
                json.dump(data, f)

        runner = MigrationRunner(source_dir=temp_dir)
        cases = runner.load_cases()

        assert len(cases) == 3

    def test_fieldvalue_parsing(self, temp_dir, sample_collected_json):
        """FieldValue 형식 파싱."""
        from tickergenius.collection.migration import MigrationRunner

        json_file = temp_dir / "TEST_test123.json"
        with open(json_file, "w") as f:
            json.dump(sample_collected_json, f)

        runner = MigrationRunner(source_dir=temp_dir)
        cases = runner.load_cases()

        case = cases[0]
        # FieldValue 형식이 올바르게 파싱되었는지
        assert case.pdufa_date is not None
        assert case.pdufa_date.value == "20250101"
        assert case.breakthrough_therapy.value is True


class TestMigrationExtraction:
    """이벤트 추출 테스트."""

    def test_extract_simple_case(self, temp_dir, sample_collected_json):
        """단순 케이스 (CRL 없음) 추출."""
        from tickergenius.collection.migration import MigrationRunner

        json_file = temp_dir / "TEST_test123.json"
        with open(json_file, "w") as f:
            json.dump(sample_collected_json, f)

        runner = MigrationRunner(source_dir=temp_dir, target_dir=temp_dir / "events")
        events = runner.extract_events()

        # CRL 없으면 1개 이벤트
        assert len(events) == 1
        assert events[0].ticker == "TEST"
        assert events[0].result == "approved"

    def test_extract_crl_case(self, temp_dir, sample_crl_case_json):
        """CRL 케이스 추출 (추론 금지 → 1개 이벤트)."""
        from tickergenius.collection.migration import MigrationRunner

        json_file = temp_dir / "AXSM_crl123.json"
        with open(json_file, "w") as f:
            json.dump(sample_crl_case_json, f)

        runner = MigrationRunner(source_dir=temp_dir, target_dir=temp_dir / "events")
        events = runner.extract_events()

        # 추론 금지: SEC 검색 없으면 CRL 이벤트 미생성
        # is_resubmission=2 이더라도 1개 이벤트 (final만)
        assert len(events) == 1

        # 최종 이벤트는 approved, submission_type="resubmission"으로 CRL 이력 표시
        final = events[0]
        assert final.result == "approved"
        assert final.submission_type == "resubmission"


class TestMigrationSave:
    """저장 테스트."""

    def test_save_events_to_store(self, temp_dir, sample_collected_json):
        """이벤트 저장."""
        from tickergenius.collection.migration import MigrationRunner

        json_file = temp_dir / "TEST_test123.json"
        with open(json_file, "w") as f:
            json.dump(sample_collected_json, f)

        events_dir = temp_dir / "events"
        runner = MigrationRunner(source_dir=temp_dir, target_dir=events_dir)

        stats = runner.run()

        # 저장 확인
        assert (events_dir / "by_event").exists()
        assert stats.events_saved >= 1


class TestMigrationStats:
    """통계 테스트."""

    def test_migration_stats(self, temp_dir, sample_collected_json, sample_crl_case_json):
        """마이그레이션 통계."""
        from tickergenius.collection.migration import MigrationRunner

        # 여러 파일 생성
        with open(temp_dir / "TEST_test123.json", "w") as f:
            json.dump(sample_collected_json, f)
        with open(temp_dir / "AXSM_crl123.json", "w") as f:
            json.dump(sample_crl_case_json, f)

        runner = MigrationRunner(source_dir=temp_dir, target_dir=temp_dir / "events")
        stats = runner.run()

        assert stats.cases_loaded == 2
        # 추론 금지: SEC 검색 없으면 각 케이스마다 1개 이벤트
        assert stats.events_extracted == 2  # 1 simple + 1 CRL (final only)
        assert stats.events_saved == 2

    def test_get_report(self, temp_dir, sample_collected_json):
        """리포트 생성."""
        from tickergenius.collection.migration import MigrationRunner

        with open(temp_dir / "TEST_test123.json", "w") as f:
            json.dump(sample_collected_json, f)

        runner = MigrationRunner(source_dir=temp_dir, target_dir=temp_dir / "events")
        runner.run()

        report = runner.get_report()

        assert isinstance(report, str)
        assert "cases" in report.lower() or "케이스" in report
