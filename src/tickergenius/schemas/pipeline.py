# -*- coding: utf-8 -*-
"""
Pipeline schemas for Ticker-Genius V4

파이프라인 기반 데이터 모델 (DESIGN_DATA_STRUCTURE.md):
- 1 Ticker → N Pipelines (약물+적응증 조합)
- 1 Pipeline → N PDUFA Events (재제출 이력)
- 1 PDUFA Event → 0~1 CRL (CRL인 경우만)

TF 히스토리:
- TF 46차: crl_class (class1/class2), is_cmc_only 정의
- TF 47차: program_status, crl_history 배열, 다중 CRL 처리
- TF 59차: phase3_count, spa_agreed 등 Trial Design 피처
- DATA_SCHEMA.md: 타임라인 필드, 정합성 규칙

ID 체계:
- Pipeline ID: {TICKER}_{DRUG}_{INDICATION_CODE}
- Event ID: {YEAR}_{PIPELINE_ID}_SEQ{N}
"""

from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, computed_field, field_validator

from .base import StatusField, DataStatus


# ============================================================================
# CRL 관련 스키마 (TF 46차, 47차)
# ============================================================================

class CRLHistoryEntry(BaseModel):
    """
    다중 CRL 히스토리 엔트리 (TF 47차)
    
    한 약물이 CRL을 여러 번 받는 경우:
    예: AGIO Opaganib - 3번의 CRL 후 프로그램 중단
    """
    crl_date: date
    crl_reason: Optional[str] = None
    crl_class: Optional[Literal["class1", "class2"]] = None
    crl_category: Optional[Literal["clinical", "manufacturing", "labeling", "other"]] = None
    resolved: bool = False
    resolution_date: Optional[date] = None


class CRLDetail(BaseModel):
    """
    CRL 상세 정보 (TF 46차)
    
    핵심 개념 분리:
    - crl_class: FDA 검토 필요 시간 (Class 1 < 60일, Class 2 >= 60일)
    - is_cmc_only: CRL 사유가 CMC(제조)만인지
    
    조합 가능:
    - Class 1 + CMC-only = 가장 유리 (빠른 검토 + 제조만)
    - Class 2 + Non-CMC = 가장 불리 (긴 검토 + 효능/안전성)
    """
    crl_date: date
    
    # TF 46차: Class 정의
    crl_class: StatusField[Literal["class1", "class2"]] = Field(
        default_factory=StatusField.unknown,
        description="FDA 재제출 분류. class1=60일 미만, class2=60일 이상"
    )
    
    # TF 46차: CMC-only 정의
    is_cmc_only: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="CRL 사유가 CMC(제조)만인지. FDA가 'no efficacy/safety concerns' 명시 필요"
    )
    
    # CRL 사유 상세
    crl_reason: StatusField[str] = Field(
        default_factory=StatusField.unknown,
        description="CRL 주요 사유 (SEC 8-K에서 추출)"
    )
    
    crl_reason_secondary: Optional[List[str]] = Field(
        default=None,
        description="부수 사유들"
    )
    
    crl_category: StatusField[Literal["clinical", "manufacturing", "labeling", "other"]] = Field(
        default_factory=StatusField.unknown,
        description="CRL 카테고리 (ML 피처용)"
    )
    
    # TF 59차: 제조시설 연동
    related_483: List[str] = Field(
        default_factory=list,
        description="관련 FDA 483 ID 목록 (CMC CRL 분석용)"
    )
    
    manufacturing_risk_score: Optional[float] = Field(
        default=None,
        description="제조시설 리스크 점수 (0.0~1.0)"
    )


# ============================================================================
# Application 스키마
# ============================================================================

class Application(BaseModel):
    """
    FDA 신청 정보
    
    NDA/BLA 번호를 primary key로 사용 (TF 긴급회의 결정)
    """
    application_type: Literal["NDA", "BLA", "sNDA", "sBLA", "ANDA"]
    application_number: Optional[str] = None  # FDA application number
    is_supplement: bool = False
    is_biosimilar: bool = False
    original_approval_date: Optional[date] = None  # 원래 승인일 (supplement인 경우)


# ============================================================================
# FDA 지정 스키마
# ============================================================================

class FDADesignations(BaseModel):
    """
    FDA 특별 지정
    
    기존 데이터: fda_designation_count로 합산
    새 구조: 각각 개별 필드로 상태 추적
    
    TF 56차: PDUFA 이전에 확인 가능한 피처들
    """
    breakthrough_therapy: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Breakthrough Therapy Designation"
    )
    fast_track: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Fast Track Designation"
    )
    priority_review: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Priority Review"
    )
    orphan_drug: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Orphan Drug Designation"
    )
    accelerated_approval: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Accelerated Approval pathway"
    )
    
    @computed_field
    @property
    def designation_count(self) -> int:
        """확인된 지정 수 (기존 fda_designation_count 대응)"""
        count = 0
        for field in [self.breakthrough_therapy, self.fast_track, 
                     self.priority_review, self.orphan_drug, self.accelerated_approval]:
            if field.is_confirmed and field.value:
                count += 1
        return count


# ============================================================================
# AdCom 스키마
# ============================================================================

class AdComInfo(BaseModel):
    """
    자문위원회 정보
    
    TF 56차: PDUFA 이전에 확인 가능
    TF 검증: VNDA Tradipitant AdCom 미개최 등 케이스 반영
    
    EMPTY vs UNKNOWN 구분 중요:
    - held=False (CONFIRMED) → vote_ratio는 EMPTY (해당없음)
    - held=UNKNOWN → vote_ratio도 UNKNOWN (확인 필요)
    """
    held: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="AdCom 개최 여부"
    )
    adcom_date: Optional[date] = Field(
        default=None,
        description="AdCom 개최일"
    )
    vote_yes: StatusField[int] = Field(
        default_factory=StatusField.unknown,
        description="찬성 투표 수"
    )
    vote_no: StatusField[int] = Field(
        default_factory=StatusField.unknown,
        description="반대 투표 수"
    )
    vote_abstain: StatusField[int] = Field(
        default_factory=lambda: StatusField.empty("Rarely reported"),
        description="기권 투표 수"
    )
    vote_ratio: StatusField[float] = Field(
        default_factory=StatusField.unknown,
        description="찬성 비율 (0.0~1.0)"
    )
    outcome: StatusField[Literal["favorable", "unfavorable", "mixed"]] = Field(
        default_factory=StatusField.unknown,
        description="AdCom 결과 해석"
    )
    transcript_url: Optional[str] = None
    
    @field_validator('vote_ratio', mode='before')
    @classmethod
    def validate_vote_ratio(cls, v):
        """vote_ratio 범위 검증"""
        if isinstance(v, StatusField):
            if v.is_confirmed and v.value is not None:
                if not 0.0 <= v.value <= 1.0:
                    raise ValueError("vote_ratio must be between 0.0 and 1.0")
        elif isinstance(v, (int, float)):
            if not 0.0 <= v <= 1.0:
                raise ValueError("vote_ratio must be between 0.0 and 1.0")
        return v


# ============================================================================
# 특수 상황 / 법적 이슈 스키마
# ============================================================================

# 표준화된 연기 사유
DELAY_REASONS = Literal[
    "covid_fda_shutdown",      # 코로나 FDA 셧다운 (2020)
    "covid_inspection_delay",  # 코로나 현장실사 불가
    "sponsor_request",         # 스폰서 요청 (추가 데이터 등)
    "fda_request",            # FDA 요청 (추가 정보)
    "manufacturing_issue",     # 제조 이슈
    "clinical_hold",          # 임상 홀드
    "citizen_petition",       # 시민청원 대응
    "litigation",             # 소송
    "other",                  # 기타
]

# 특수 상황 태그
SPECIAL_CIRCUMSTANCES = Literal[
    "covid_impact",           # 코로나 영향
    "multiple_crl",           # 다중 CRL (2회 이상)
    "citizen_petition",       # 시민청원
    "patent_litigation",      # 특허 소송
    "antitrust_issue",        # 반독점 이슈
    "manufacturing_warning",  # 제조시설 Warning Letter
    "adcom_negative",         # AdCom 부정적 (<50%)
    "accelerated_withdrawn",  # Accelerated Approval 철회
    "rems_required",          # REMS 요구
    "pediatric_extension",    # 소아 연장
]

# Pending 상태 세분화
PENDING_STATUS = Literal[
    "not_yet_submitted",       # 아직 FDA 미제출
    "submitted_filing_review", # 제출됨, Filing 검토 중 (RTF 판정 대기)
    "filed_under_review",      # Filing 완료, FDA 검토 중
    "awaiting_pdufa_date",     # PDUFA 날짜 확정 대기
    "pdufa_scheduled",         # PDUFA 날짜 확정됨
    "pdufa_imminent",          # PDUFA 30일 이내
    "delayed_new_date_pending",# 연기됨, 새 날짜 미정
    "post_crl_preparing",      # CRL 후 재제출 준비 중
    "post_crl_submitted",      # CRL 후 재제출 완료, 검토 중
]


class LegalIssue(BaseModel):
    """
    법적 이슈 (소송, 시민청원 등)
    
    예: 
    - AQST: 시민청원으로 PDUFA 지연
    - VNDA: FDA와 소송으로 장기 지연
    - 특허 소송으로 시장독점권 영향
    """
    issue_type: Literal[
        "citizen_petition",     # 시민청원
        "fda_litigation",       # FDA와 직접 소송 (VNDA 케이스)
        "patent_litigation",    # 특허 소송
        "antitrust",           # 반독점
        "sec_investigation",   # SEC 조사
        "doj_investigation",   # DOJ 조사
        "whistleblower",       # 내부고발
        "congressional_inquiry",# 의회 조사
        "other",
    ]
    filed_date: Optional[date] = None
    status: Literal["filed", "pending", "resolved", "dismissed", "unknown"] = "unknown"
    resolution_date: Optional[date] = None
    
    impact: Optional[Literal[
        "pdufa_delay",         # PDUFA 연기
        "approval_blocked",    # 승인 차단
        "label_change",        # 라벨 변경
        "market_exclusivity",  # 시장독점권 영향
        "no_impact",           # 영향 없음
        "unknown",
    ]] = "unknown"
    
    description: Optional[str] = None
    source: Optional[str] = None


# ============================================================================
# PDUFA Event 스키마
# ============================================================================

class PDUFAEvent(BaseModel):
    """
    PDUFA 이벤트
    
    핵심 설계:
    - sequence: 재제출 횟수 (1부터 시작)
    - is_resubmission: 이전 CRL 후 재제출인지
    - pending_status: Pending 상태 세분화
    
    TF 46차 타임라인 규칙:
    - crl_date < resubmission_date < decision_date
    - Class 1: 재제출까지 60일 미만
    - Class 2: 재제출까지 60일 이상
    """
    event_id: str  # {YEAR}_{PIPELINE_ID}_SEQ{N}
    sequence: int = Field(ge=1, description="PDUFA 시퀀스 (1부터)")
    
    # 핵심 날짜
    pdufa_date: date
    pdufa_date_original: Optional[date] = Field(
        default=None,
        description="연기 전 원래 PDUFA 날짜"
    )
    
    decision_date: StatusField[date] = Field(
        default_factory=StatusField.unknown,
        description="FDA 결정일"
    )
    
    # 결과
    result: StatusField[Literal["approved", "crl", "pending", "withdrawn"]] = Field(
        default_factory=StatusField.unknown,
        description="FDA 결정 결과"
    )
    
    # Pending 상태 세분화 (result가 pending일 때)
    pending_status: Optional[PENDING_STATUS] = Field(
        default=None,
        description="Pending 세부 상태 (재제출 대기, 접수완료 대기, PDUFA 대기 등)"
    )
    
    # 재제출 정보 (TF 46차)
    is_resubmission: bool = Field(
        default=False,
        description="이전 CRL 후 재제출인지"
    )
    resubmission_date: Optional[date] = Field(
        default=None,
        description="NDA/BLA 재제출일"
    )
    days_since_crl: Optional[int] = Field(
        default=None,
        description="CRL부터 재제출까지 일수"
    )
    
    # CRL 상세 (result가 crl인 경우만)
    crl: Optional[CRLDetail] = None
    
    # 연기 정보 (개선됨)
    delay_reason: Optional[DELAY_REASONS] = Field(
        default=None,
        description="PDUFA 연기 사유 (표준화)"
    )
    delay_days: Optional[int] = Field(
        default=None,
        description="연기 일수 (pdufa_date - pdufa_date_original)"
    )
    delay_description: Optional[str] = Field(
        default=None,
        description="연기 사유 상세 설명"
    )
    
    # 메타데이터
    data_source: Optional[str] = None
    source_confidence: Optional[Literal["high", "medium", "low"]] = None
    
    @computed_field
    @property
    def days_from_pdufa(self) -> Optional[int]:
        """decision_date - pdufa_date (음수 가능: 조기 결정)"""
        if self.decision_date.is_confirmed and self.decision_date.value:
            return (self.decision_date.value - self.pdufa_date).days
        return None
    
    @computed_field
    @property
    def is_delayed(self) -> bool:
        """연기된 이벤트인지"""
        return self.pdufa_date_original is not None


# ============================================================================
# Pipeline 스키마
# ============================================================================

class Pipeline(BaseModel):
    """
    파이프라인 (약물 + 적응증 조합)
    
    핵심 설계:
    - pipeline_id: {TICKER}_{DRUG}_{INDICATION_CODE}
    - 하나의 파이프라인에 여러 PDUFA 이벤트 가능 (재제출)
    
    TF 47차: program_status 추가
    TF 59차: Trial Design 피처 추가
    """
    pipeline_id: str  # {TICKER}_{DRUG}_{INDICATION_CODE}
    ticker: str
    company: str
    drug_name: str
    generic_name: Optional[str] = None
    indication: str
    indication_code: str  # 간략화된 코드 (BLADDER, LUNG 등)
    
    therapeutic_area: StatusField[str] = Field(
        default_factory=StatusField.unknown,
        description="치료 영역 (oncology, rare_disease 등)"
    )
    
    # Application 정보
    application: Application
    
    # FDA 지정
    fda_designations: FDADesignations = Field(default_factory=FDADesignations)
    
    # PDUFA 이벤트들 (시간순)
    pdufa_events: List[PDUFAEvent] = Field(default_factory=list)
    
    # AdCom
    adcom: AdComInfo = Field(default_factory=AdComInfo)
    
    # TF 47차: Program Status (CRL 후 상태)
    program_status: StatusField[Literal[
        "discontinued",           # 회사 공식 중단 발표
        "de_facto_abandoned",     # 24개월+ 무응답
        "preparing_resubmission", # 재제출 예정
        "resubmitted",           # 재제출 완료, FDA 검토 중
        "approved"               # 최종 승인
    ]] = Field(
        default_factory=StatusField.unknown,
        description="CRL 후 프로그램 상태"
    )
    
    # TF 47차: 다중 CRL 히스토리
    crl_count: Optional[int] = Field(
        default=None,
        description="총 CRL 횟수"
    )
    crl_history: List[CRLHistoryEntry] = Field(
        default_factory=list,
        description="CRL 이력 (다중 CRL 케이스)"
    )
    
    # TF 59차: Trial Design 피처
    phase3_count: StatusField[int] = Field(
        default_factory=StatusField.unknown,
        description="Phase 3 시험 수"
    )
    phase2_skipped: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Phase 2 없이 Phase 3 진행"
    )
    spa_agreed: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="SPA(Special Protocol Assessment) 합의 여부"
    )
    spa_rescinded: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="SPA 취소 여부"
    )
    confirmatory_trial_exists: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Confirmatory trial 존재 여부"
    )
    
    # 임상 결과 (TF 56차: PDUFA 이전 확인 가능)
    primary_endpoint_met: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="Primary endpoint 달성 여부"
    )
    
    # TF 59차: First-in-Class
    is_first_in_class: StatusField[bool] = Field(
        default_factory=StatusField.unknown,
        description="First-in-Class 여부"
    )
    
    # 특수 상황 (코로나, 다중CRL, 소송 등)
    special_circumstances: List[SPECIAL_CIRCUMSTANCES] = Field(
        default_factory=list,
        description="특수 상황 태그 (covid_impact, multiple_crl, citizen_petition 등)"
    )
    
    # 법적 이슈 (소송, 시민청원 등)
    legal_issues: List[LegalIssue] = Field(
        default_factory=list,
        description="법적 이슈 목록"
    )
    
    # 메타데이터
    last_updated: Optional[str] = None
    data_quality: Optional[dict] = None
    notes: Optional[str] = None
    
    # Clinical trials 참조 (별도 파일)
    clinical_trial_refs: List[str] = Field(
        default_factory=list,
        description="관련 NCT ID 목록"
    )
    
    @computed_field
    @property
    def latest_event(self) -> Optional[PDUFAEvent]:
        """가장 최근 PDUFA 이벤트"""
        if not self.pdufa_events:
            return None
        return max(self.pdufa_events, key=lambda e: e.pdufa_date)
    
    @computed_field
    @property
    def total_crl_count(self) -> int:
        """총 CRL 횟수 (이벤트에서 계산)"""
        return sum(1 for e in self.pdufa_events if e.crl is not None)
    
    @computed_field
    @property
    def final_result(self) -> Optional[str]:
        """최종 결과"""
        latest = self.latest_event
        if latest and latest.result.is_confirmed:
            return latest.result.value
        return None
    
    @computed_field
    @property
    def is_resubmission_case(self) -> bool:
        """재제출 케이스인지 (어느 이벤트라도)"""
        return any(e.is_resubmission for e in self.pdufa_events)


# ============================================================================
# Ticker Pipelines 스키마
# ============================================================================

class TickerPipelines(BaseModel):
    """
    티커의 모든 파이프라인
    
    파일 구조: data/pipelines/by_ticker/{TICKER}.json
    """
    ticker: str
    company: str
    sector: Optional[str] = None
    last_updated: str
    
    pipelines: List[Pipeline] = Field(default_factory=list)
    
    # 제조시설 참조 (별도 파일)
    manufacturing_ref: Optional[str] = Field(
        default=None,
        description="제조시설 파일 경로 (manufacturing/{TICKER}_manufacturing.json)"
    )
    
    @computed_field
    @property
    def pipeline_count(self) -> int:
        return len(self.pipelines)
    
    @computed_field
    @property
    def total_events(self) -> int:
        return sum(len(p.pdufa_events) for p in self.pipelines)
