# -*- coding: utf-8 -*-
"""
Manufacturing schemas for Ticker-Genius V4

제조시설 정보 (DESIGN_DATA_COLLECTION_ROADMAP_v2.md):
- Tier 2.5로 승격 (CMC CRL 분석에 필수)
- SEC 10-K에서 시설 목록 추출
- FDA 483 검색으로 품질 이슈 확인
- Warning Letter 확인

TF 히스토리:
- TF 59차: CMC 피처 정의 (facility_warning_letter, fda_483_count 등)
- TF 긴급회의: 제조시설 데이터 수집 필요성 확인
"""

from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, computed_field

from .base import StatusField


class ManufacturingSite(BaseModel):
    """
    제조 시설
    
    소스: SEC 10-K "Item 2. Properties" 또는 "Manufacturing" 섹션
    """
    site_id: str  # {TICKER}_SITE_{NNN}
    site_name: str
    address: str
    city: Optional[str] = None
    country: Optional[str] = None  # TF 59차: manufacturing_country
    
    site_type: Literal["primary", "secondary", "cmo", "unknown"] = Field(
        default="unknown",
        description="시설 유형 (자체 primary/secondary 또는 CMO)"
    )
    
    # CMO 정보 (TF 59차)
    is_cmo: bool = Field(
        default=False,
        description="CDMO 시설 여부"
    )
    cmo_name: Optional[str] = Field(
        default=None,
        description="CMO 회사명 (is_cmo=True인 경우)"
    )
    
    # 생산 제품
    products: List[str] = Field(
        default_factory=list,
        description="이 시설에서 생산하는 약물 목록"
    )
    
    # 상태
    status: Literal["active", "inactive", "unknown"] = "unknown"
    
    # 출처
    source: str
    source_date: Optional[date] = None


class FDA483(BaseModel):
    """
    FDA Form 483 (관찰 사항)
    
    TF 59차 피처:
    - fda_483_count: 관찰사항 수
    - fda_483_critical: 심각도 (0=none, 1=moderate, 2=critical)
    
    소스: FDA.gov Inspection Database, FDAtracker.ai
    """
    form_483_id: str  # {TICKER}_483_{YEAR}_{NNN}
    site_id: str  # 연결된 시설
    
    issue_date: date
    observations: int = Field(
        ge=0,
        description="총 관찰사항 수"
    )
    critical_observations: int = Field(
        default=0,
        ge=0,
        description="심각한 관찰사항 수"
    )
    
    # TF 59차: 심각도 분류
    severity_level: Literal[0, 1, 2] = Field(
        default=0,
        description="0=none/minor, 1=moderate, 2=critical"
    )
    
    # 상태
    status: Literal["open", "resolved", "unknown"] = "unknown"
    resolution_date: Optional[date] = None
    
    # 연결된 파이프라인 (CMC CRL 분석용)
    related_pipelines: List[str] = Field(
        default_factory=list,
        description="관련 파이프라인 ID 목록"
    )
    
    # 출처
    source: str  # "FDA Inspection Database", "FDAtracker.ai"
    notes: Optional[str] = None


class WarningLetter(BaseModel):
    """
    FDA Warning Letter
    
    TF 59차: facility_warning_letter 피처
    - 최근 2년 내 Warning Letter 존재 여부가 CRL 예측에 중요
    """
    letter_id: str
    issue_date: date
    subject: str
    
    # 연결된 시설
    related_sites: List[str] = Field(
        default_factory=list,
        description="관련 시설 ID 목록"
    )
    
    # 상태
    status: Literal["active", "closed", "unknown"] = "active"
    close_date: Optional[date] = None
    
    # 출처
    source: str = "FDA Warning Letters Database"
    letter_url: Optional[str] = None


class ManufacturingInfo(BaseModel):
    """
    티커의 제조 정보 전체
    
    파일 구조: data/manufacturing/{TICKER}_manufacturing.json
    
    TF 59차 CMC 피처 계산:
    - facility_warning_letter: warning_letters가 있고 최근 2년 이내
    - fda_483_count: 총 483 관찰사항 수
    - fda_483_critical: 최고 심각도
    - cdmo_used: CMO 시설 존재 여부
    """
    ticker: str
    company: str
    last_updated: str
    
    # 시설 목록
    manufacturing_sites: List[ManufacturingSite] = Field(default_factory=list)
    
    # FDA 483 이력
    fda_483_history: List[FDA483] = Field(default_factory=list)
    
    # Warning Letters
    warning_letters: List[WarningLetter] = Field(default_factory=list)
    
    @computed_field
    @property
    def total_sites(self) -> int:
        return len(self.manufacturing_sites)
    
    @computed_field
    @property
    def owned_sites(self) -> int:
        """자체 시설 수"""
        return len([s for s in self.manufacturing_sites if not s.is_cmo])
    
    @computed_field
    @property
    def cmo_sites(self) -> int:
        """CMO 시설 수"""
        return len([s for s in self.manufacturing_sites if s.is_cmo])
    
    @computed_field
    @property
    def active_483_count(self) -> int:
        """미해결 483 수"""
        return len([f for f in self.fda_483_history if f.status == "open"])
    
    @computed_field
    @property
    def historical_483_count(self) -> int:
        """전체 483 수 (해결 포함)"""
        return len(self.fda_483_history)
    
    @computed_field
    @property
    def total_483_observations(self) -> int:
        """총 483 관찰사항 수 (TF 59차: fda_483_count)"""
        return sum(f.observations for f in self.fda_483_history)
    
    @computed_field
    @property
    def max_483_severity(self) -> int:
        """최고 483 심각도 (TF 59차: fda_483_critical)"""
        if not self.fda_483_history:
            return 0
        return max(f.severity_level for f in self.fda_483_history)
    
    @computed_field
    @property
    def has_warning_letter(self) -> bool:
        """Warning Letter 존재 여부"""
        return len(self.warning_letters) > 0
    
    @computed_field
    @property
    def cdmo_used(self) -> bool:
        """CMO 사용 여부 (TF 59차: cdmo_used)"""
        return any(s.is_cmo for s in self.manufacturing_sites)
    
    @computed_field
    @property
    def manufacturing_risk(self) -> Literal["low", "medium", "high"]:
        """
        제조 리스크 등급
        
        TF 59차 기준:
        - high: Warning Letter 또는 active 483 >= 3
        - medium: active 483 >= 1
        - low: 나머지
        """
        if self.has_warning_letter or self.active_483_count >= 3:
            return "high"
        elif self.active_483_count >= 1:
            return "medium"
        return "low"
    
    def has_recent_warning_letter(self, within_years: int = 2) -> bool:
        """
        최근 N년 내 Warning Letter 여부 (TF 59차: facility_warning_letter)
        """
        if not self.warning_letters:
            return False
        
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=within_years * 365)
        
        return any(wl.issue_date >= cutoff for wl in self.warning_letters)
    
    def get_related_483_for_crl(self, crl_date: date, lookback_days: int = 730) -> List[FDA483]:
        """
        CRL 관련 483 찾기 (CMC CRL 분석용)
        
        DESIGN_DATA_COLLECTION_ROADMAP_v2.md:
        - CRL 전 2년 이내 483을 관련으로 간주
        """
        from datetime import timedelta
        cutoff = crl_date - timedelta(days=lookback_days)
        
        return [
            f for f in self.fda_483_history
            if cutoff < f.issue_date < crl_date
        ]
