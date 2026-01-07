# -*- coding: utf-8 -*-
"""
Pydantic 스키마 테스트

TF 히스토리 반영 검증:
- StatusField 3분류 동작
- CRL 관련 필드 정합성
- 데이터 품질 플래깅
"""

import pytest
from datetime import date, datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tickergenius.schemas.base import DataStatus, StatusField
from tickergenius.schemas.pipeline import (
    Pipeline, TickerPipelines, PDUFAEvent, CRLDetail,
    CRLHistoryEntry, Application, FDADesignations, AdComInfo
)
from tickergenius.schemas.manufacturing import (
    ManufacturingSite, FDA483, WarningLetter, ManufacturingInfo
)
from tickergenius.schemas.data_quality import DataQuality, DataQualityIssue


class TestStatusField:
    """StatusField 3분류 테스트"""
    
    def test_confirmed_value(self):
        """CONFIRMED 상태 테스트"""
        field = StatusField.confirmed(True, "FDA press release")
        
        assert field.is_confirmed
        assert field.is_usable
        assert field.value == True
        assert field.source == "FDA press release"
        assert field.verified_at is not None
    
    def test_empty_value(self):
        """EMPTY (해당없음) 상태 테스트"""
        field = StatusField.empty("AdCom not held")
        
        assert field.is_empty
        assert field.is_usable  # EMPTY도 사용 가능
        assert field.value is None
        assert field.reason == "AdCom not held"
    
    def test_unknown_value(self):
        """UNKNOWN (미확인) 상태 테스트"""
        field = StatusField.unknown("Not yet verified")
        
        assert field.is_unknown
        assert not field.is_usable  # UNKNOWN은 사용 불가
        assert field.value is None
    
    def test_from_legacy_with_value(self):
        """기존 데이터 변환 - 값 있음"""
        field = StatusField.from_legacy(0.85, "adcom_vote_ratio")
        
        assert field.is_confirmed
        assert field.value == 0.85
        assert field.source == "legacy_data"
    
    def test_from_legacy_without_value(self):
        """기존 데이터 변환 - 값 없음"""
        field = StatusField.from_legacy(None, "adcom_vote_ratio")
        
        assert field.is_unknown
        assert "not verified" in field.reason.lower()
    
    def test_bool_context(self):
        """Boolean 컨텍스트 테스트"""
        # CONFIRMED + True
        assert bool(StatusField.confirmed(True, "test"))
        
        # CONFIRMED + False
        assert not bool(StatusField.confirmed(False, "test"))
        
        # EMPTY
        assert not bool(StatusField.empty("N/A"))
        
        # UNKNOWN
        assert not bool(StatusField.unknown())


class TestFDADesignations:
    """FDA 지정 스키마 테스트"""
    
    def test_designation_count(self):
        """지정 수 계산"""
        designations = FDADesignations(
            breakthrough_therapy=StatusField.confirmed(True, "FDA"),
            fast_track=StatusField.confirmed(True, "FDA"),
            priority_review=StatusField.empty("Not granted"),
            orphan_drug=StatusField.unknown(),
            accelerated_approval=StatusField.confirmed(False, "FDA")
        )
        
        # True인 것만 카운트
        assert designations.designation_count == 2


class TestCRLDetail:
    """CRL 상세 정보 테스트 (TF 46차)"""
    
    def test_crl_class_combinations(self):
        """CRL Class + CMC 조합 테스트"""
        # Class 1 + CMC-only (가장 유리)
        crl = CRLDetail(
            crl_date=date(2025, 9, 30),
            crl_class=StatusField.confirmed("class1", "SEC 8-K"),
            is_cmc_only=StatusField.confirmed(True, "SEC 8-K"),
            crl_reason=StatusField.confirmed("CMC facility update", "SEC 8-K")
        )
        
        assert crl.crl_class.value == "class1"
        assert crl.is_cmc_only.value == True
        assert crl.crl_class.is_confirmed
    
    def test_crl_unknown_class(self):
        """CRL Class 미검증 테스트"""
        crl = CRLDetail(
            crl_date=date(2025, 6, 15),
            crl_class=StatusField.unknown("SEC 8-K not found"),
            is_cmc_only=StatusField.unknown()
        )
        
        assert crl.crl_class.is_unknown
        assert not crl.crl_class.is_usable


class TestPDUFAEvent:
    """PDUFA 이벤트 테스트"""
    
    def test_basic_event(self):
        """기본 이벤트"""
        event = PDUFAEvent(
            event_id="2026_FBIO_CUTX101_MENKES_SEQ1",
            sequence=1,
            pdufa_date=date(2026, 1, 14),
            decision_date=StatusField.unknown(),
            result=StatusField.unknown(),
            is_resubmission=True,
            resubmission_date=date(2025, 11, 14),
            days_since_crl=45
        )
        
        assert event.sequence == 1
        assert event.is_resubmission
        assert event.days_since_crl == 45
    
    def test_event_with_crl(self):
        """CRL 이벤트"""
        event = PDUFAEvent(
            event_id="2025_FBIO_CUTX101_MENKES_SEQ0",
            sequence=1,
            pdufa_date=date(2025, 9, 30),
            decision_date=StatusField.confirmed(date(2025, 9, 30), "FDA"),
            result=StatusField.confirmed("crl", "SEC 8-K"),
            crl=CRLDetail(
                crl_date=date(2025, 9, 30),
                crl_class=StatusField.confirmed("class1", "SEC 8-K"),
                is_cmc_only=StatusField.confirmed(True, "SEC 8-K")
            )
        )
        
        assert event.result.value == "crl"
        assert event.crl is not None
        assert event.crl.crl_class.value == "class1"


class TestPipeline:
    """파이프라인 테스트 (TF 47차)"""
    
    def test_pipeline_with_multiple_events(self):
        """다중 이벤트 파이프라인"""
        pipeline = Pipeline(
            pipeline_id="FBIO_CUTX101_MENKES",
            ticker="FBIO",
            company="Fortress Biotech",
            drug_name="CUTX-101",
            indication="Menkes Disease",
            indication_code="MENKES",
            application=Application(
                application_type="NDA",
                application_number="N214143"
            ),
            pdufa_events=[
                PDUFAEvent(
                    event_id="2025_FBIO_CUTX101_MENKES_SEQ1",
                    sequence=1,
                    pdufa_date=date(2025, 9, 30),
                    result=StatusField.confirmed("crl", "SEC 8-K"),
                    crl=CRLDetail(
                        crl_date=date(2025, 9, 30),
                        crl_class=StatusField.confirmed("class1", "SEC 8-K")
                    )
                ),
                PDUFAEvent(
                    event_id="2026_FBIO_CUTX101_MENKES_SEQ2",
                    sequence=2,
                    pdufa_date=date(2026, 1, 14),
                    is_resubmission=True
                )
            ],
            program_status=StatusField.confirmed("resubmitted", "SEC 8-K")
        )
        
        assert len(pipeline.pdufa_events) == 2
        assert pipeline.total_crl_count == 1
        assert pipeline.is_resubmission_case
        assert pipeline.latest_event.sequence == 2
    
    def test_crl_history(self):
        """다중 CRL 히스토리 (TF 47차)"""
        pipeline = Pipeline(
            pipeline_id="AGIO_OPAGANIB_ONCOLOGY",
            ticker="AGIO",
            company="Agios",
            drug_name="Opaganib",
            indication="Cancer",
            indication_code="ONCOLOGY",
            application=Application(application_type="NDA"),
            crl_count=3,
            crl_history=[
                CRLHistoryEntry(crl_date=date(2022, 1, 31), crl_reason="efficacy"),
                CRLHistoryEntry(crl_date=date(2023, 10, 15), crl_reason="additional_data", crl_class="class2"),
                CRLHistoryEntry(crl_date=date(2024, 9, 1), crl_reason="safety", crl_class="class2")
            ],
            program_status=StatusField.confirmed("discontinued", "PR")
        )
        
        assert pipeline.crl_count == 3
        assert len(pipeline.crl_history) == 3


class TestManufacturing:
    """제조시설 테스트 (TF 59차)"""
    
    def test_manufacturing_info(self):
        """제조 정보 전체"""
        info = ManufacturingInfo(
            ticker="ALVO",
            company="Allovir",
            last_updated="2026-01-07",
            manufacturing_sites=[
                ManufacturingSite(
                    site_id="ALVO_SITE_001",
                    site_name="Main Facility",
                    address="100 Main St",
                    country="United States",
                    is_cmo=False,
                    source="SEC 10-K"
                ),
                ManufacturingSite(
                    site_id="ALVO_SITE_002",
                    site_name="CMO Partner",
                    address="200 Industrial Ave",
                    country="Germany",
                    is_cmo=True,
                    cmo_name="Lonza",
                    source="SEC 10-K"
                )
            ],
            fda_483_history=[
                FDA483(
                    form_483_id="ALVO_483_2025_001",
                    site_id="ALVO_SITE_001",
                    issue_date=date(2025, 6, 15),
                    observations=3,
                    critical_observations=1,
                    severity_level=2,
                    status="open",
                    source="FDA Inspection Database"
                )
            ]
        )
        
        assert info.total_sites == 2
        assert info.owned_sites == 1
        assert info.cmo_sites == 1
        assert info.cdmo_used
        assert info.active_483_count == 1
        assert info.max_483_severity == 2
        assert info.manufacturing_risk == "medium"  # 1 active 483 = medium


class TestDataQuality:
    """데이터 품질 테스트 (TF 긴급회의)"""
    
    def test_flagged_case(self):
        """플래그된 케이스"""
        quality = DataQuality(status="unknown")
        
        # 이슈 추가
        quality.add_issue(
            issue_type="wrong_drug_match",
            description="CRL belongs to donanemab, not Zepbound",
            severity="error",
            field_name="crl_date",
            detected_by="TF 긴급회의"
        )
        
        assert quality.status == "flagged"
        assert quality.exclude_from_statistics
        assert quality.has_errors
        assert not quality.is_usable_for_ml
    
    def test_verified_case(self):
        """검증된 케이스"""
        quality = DataQuality(status="unknown")
        quality.mark_verified("TF 검증팀", "https://sec.gov/8k/...")
        
        assert quality.status == "verified"
        assert quality.verification_status == "completed"
        assert quality.verification_source is not None
        assert quality.is_usable_for_ml


class TestSerialization:
    """JSON 직렬화 테스트"""
    
    def test_pipeline_to_json(self):
        """파이프라인 JSON 변환"""
        pipeline = Pipeline(
            pipeline_id="TEST_DRUG_IND",
            ticker="TEST",
            company="Test Corp",
            drug_name="TestDrug",
            indication="Test Indication",
            indication_code="IND",
            application=Application(application_type="NDA"),
            fda_designations=FDADesignations(
                breakthrough_therapy=StatusField.confirmed(True, "FDA")
            )
        )
        
        json_data = pipeline.model_dump_json()
        
        # 역직렬화
        loaded = Pipeline.model_validate_json(json_data)
        
        assert loaded.pipeline_id == "TEST_DRUG_IND"
        assert loaded.fda_designations.breakthrough_therapy.is_confirmed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
