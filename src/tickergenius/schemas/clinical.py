# -*- coding: utf-8 -*-
"""
Clinical Trial schemas for Ticker-Genius V4

임상시험 정보 (TF 59차):
- ClinicalTrials.gov API v2.0에서 수집
- phase3_count, trial_region 등 ML 피처

TF 히스토리:
- TF 56차: trial_region 96.6% 누락 확인
- TF 59차: phase3_count, phase2_skipped 피처 정의
- ML 데이터셋: 507건 NCT matched
"""

from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from .base import StatusField


class ClinicalTrial(BaseModel):
    """
    임상시험 정보
    
    소스: ClinicalTrials.gov API v2.0
    URL: https://clinicaltrials.gov/api/v2/studies
    """
    nct_id: str  # NCT00000000 형식
    
    # 기본 정보
    brief_title: Optional[str] = None
    official_title: Optional[str] = None
    
    # 상태
    phase: StatusField[Literal["1", "2", "3", "4", "1/2", "2/3"]] = Field(
        default_factory=StatusField.unknown,
        description="임상 단계"
    )
    status: StatusField[Literal[
        "not_yet_recruiting",
        "recruiting", 
        "enrolling_by_invitation",
        "active_not_recruiting",
        "completed",
        "suspended",
        "terminated",
        "withdrawn"
    ]] = Field(
        default_factory=StatusField.unknown,
        description="시험 상태"
    )
    
    # 등록
    enrollment: StatusField[int] = Field(
        default_factory=StatusField.unknown,
        description="등록 환자 수"
    )
    enrollment_type: Optional[Literal["actual", "estimated"]] = None
    
    # 결과 (TF 56차: PDUFA 이전 확인 가능)
    primary_endpoint_met: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Primary endpoint 달성 여부"
    )
    
    # 지역 (TF 56차: 96.6% 누락 필드)
    trial_region: StatusField[Literal["us", "eu", "asia", "global", "other"]] = Field(
        default_factory=StatusField.unknown,
        description="시험 지역"
    )
    countries: List[str] = Field(
        default_factory=list,
        description="시험 진행 국가 목록"
    )
    
    # 날짜
    start_date: Optional[date] = None
    completion_date: Optional[date] = None
    primary_completion_date: Optional[date] = None
    
    # 연결 정보
    pipeline_id: Optional[str] = Field(
        default=None,
        description="연결된 파이프라인 ID"
    )
    drug_name: Optional[str] = None
    indication: Optional[str] = None
    
    # 스폰서
    sponsor: Optional[str] = None
    sponsor_type: Optional[Literal["industry", "academic", "government", "other"]] = None
    
    # 출처
    source: str = "ClinicalTrials.gov"
    last_updated: Optional[str] = None
    
    def determine_region(self) -> str:
        """
        국가 목록에서 지역 판단
        
        TF 59차 ClinicalTrialsCollector._determine_region() 로직
        """
        if not self.countries:
            return "unknown"
        
        countries_set = set(self.countries)
        
        us = "United States" in countries_set
        eu = any(c in countries_set for c in [
            "Germany", "France", "United Kingdom", "Spain", "Italy", 
            "Netherlands", "Belgium", "Poland", "Sweden", "Austria"
        ])
        asia = any(c in countries_set for c in [
            "China", "Japan", "Korea, Republic of", "India", "Taiwan"
        ])
        
        if us and (eu or asia):
            return "global"
        elif us:
            return "us"
        elif eu:
            return "eu"
        elif asia:
            return "asia"
        return "other"


class ClinicalTrialSummary(BaseModel):
    """
    파이프라인에 연결된 임상시험 요약
    
    Pipeline.clinical_trial_refs로 NCT ID 참조 후
    실제 데이터는 별도 파일이나 캐시에서 로드
    """
    pipeline_id: str
    
    # 요약 통계
    total_trials: int = 0
    phase3_count: int = 0  # TF 59차 피처
    phase2_count: int = 0
    
    # 결과
    completed_count: int = 0
    endpoint_met_count: int = 0
    
    # 지역
    has_us_trial: bool = False
    has_global_trial: bool = False
    primary_region: Optional[str] = None
    
    # 참조
    nct_ids: List[str] = Field(default_factory=list)
