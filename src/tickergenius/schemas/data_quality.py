# -*- coding: utf-8 -*-
"""
Data Quality schemas for Ticker-Genius V4

데이터 품질 추적 (TF 긴급회의 결정):
- 무작정 삭제 금지, 플래깅 방식
- data_quality 필드로 품질 상태 추적
- 검증 출처와 이슈 기록

TF 히스토리:
- TF 56차: 데이터 품질 이슈 발견 (PDUFA 날짜 오류 등)
- TF 긴급회의: CRL 매칭 오류 136개+ 발견
- 원칙: 오류 데이터도 이력으로 보존, 플래깅
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class DataQualityIssue(BaseModel):
    """
    개별 데이터 품질 이슈
    
    TF 긴급회의에서 발견된 이슈 유형:
    - wrong_drug_match: CRL이 잘못된 약물에 매칭됨
    - company_level_crl: 회사 레벨 CRL이 약물에 매칭됨
    - duplicate_date: 동일 티커 내 중복 CRL 날짜
    - abnormal_interval: CRL-PDUFA 간격 비정상 (>365일)
    - date_format_error: 날짜 형식 오류
    - missing_source: 출처 누락
    """
    issue_type: Literal[
        "wrong_drug_match",
        "company_level_crl",
        "duplicate_date",
        "abnormal_interval",
        "date_format_error",
        "missing_source",
        "unverified_data",
        "legacy_migration",
        "other"
    ]
    
    severity: Literal["error", "warning", "info"] = "warning"
    
    description: str
    
    field_name: Optional[str] = Field(
        default=None,
        description="이슈가 있는 필드명"
    )
    
    detected_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    detected_by: Optional[str] = Field(
        default=None,
        description="발견자 (TF 회의, 스크립트명 등)"
    )


class DataQuality(BaseModel):
    """
    데이터 품질 상태 (TF 긴급회의)
    
    모든 파이프라인/이벤트에 포함되어
    데이터 신뢰도를 추적
    
    사용 예:
    {
        "status": "flagged",
        "issues": [
            {"issue_type": "wrong_drug_match", "description": "CRL belongs to donanemab"}
        ],
        "verification_status": "pending"
    }
    """
    
    # 전체 상태
    status: Literal["verified", "flagged", "unknown"] = Field(
        default="unknown",
        description="verified=검증완료, flagged=이슈있음, unknown=미검증"
    )
    
    # 품질 점수 (0.0 ~ 1.0)
    quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="품질 점수 (CONFIRMED 필드 비율)"
    )
    
    # 등급 (연도별 목표)
    grade: Optional[Literal["gold", "silver", "bronze"]] = Field(
        default=None,
        description="gold=90%+, silver=70-90%, bronze=50-70%"
    )
    
    # 이슈 목록
    issues: List[DataQualityIssue] = Field(default_factory=list)
    
    # 검증 상태
    verification_status: Literal[
        "not_started",
        "in_progress", 
        "completed",
        "pending_review"
    ] = "not_started"
    
    last_verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    
    # TF 긴급회의: 오류 케이스의 실제 정보
    actual_crl_drug: Optional[str] = Field(
        default=None,
        description="CRL이 실제로 해당하는 약물 (오류 케이스)"
    )
    
    verification_source: Optional[str] = Field(
        default=None,
        description="검증에 사용된 출처 URL"
    )
    
    # 통계 제외 여부
    exclude_from_statistics: bool = Field(
        default=False,
        description="통계 계산에서 제외할지 (플래그된 케이스)"
    )
    
    # 메타데이터
    notes: Optional[str] = None
    flagged_date: Optional[datetime] = None
    flagged_reason: Optional[str] = None
    
    def add_issue(
        self,
        issue_type: str,
        description: str,
        severity: str = "warning",
        field_name: Optional[str] = None,
        detected_by: Optional[str] = None
    ) -> None:
        """이슈 추가"""
        self.issues.append(DataQualityIssue(
            issue_type=issue_type,
            severity=severity,
            description=description,
            field_name=field_name,
            detected_by=detected_by
        ))
        
        # error 이슈가 있으면 상태를 flagged로
        if severity == "error":
            self.status = "flagged"
            self.exclude_from_statistics = True
    
    def mark_verified(self, verified_by: str, source: Optional[str] = None) -> None:
        """검증 완료 표시"""
        self.status = "verified"
        self.verification_status = "completed"
        self.last_verified_at = datetime.utcnow()
        self.verified_by = verified_by
        if source:
            self.verification_source = source
    
    def mark_flagged(self, reason: str) -> None:
        """플래그 표시"""
        self.status = "flagged"
        self.flagged_date = datetime.utcnow()
        self.flagged_reason = reason
        self.exclude_from_statistics = True
    
    @property
    def has_errors(self) -> bool:
        """error 수준 이슈가 있는지"""
        return any(i.severity == "error" for i in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """warning 수준 이슈가 있는지"""
        return any(i.severity == "warning" for i in self.issues)
    
    @property
    def is_usable_for_ml(self) -> bool:
        """
        ML 학습에 사용 가능한지
        
        TF 56차 기준:
        - verified 또는 unknown (flagged는 제외)
        - error 이슈 없음
        """
        if self.status == "flagged":
            return False
        if self.has_errors:
            return False
        if self.exclude_from_statistics:
            return False
        return True


class QualityReport(BaseModel):
    """
    전체 데이터 품질 리포트
    
    M2 검증 시스템의 출력물
    """
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 요약
    total_pipelines: int = 0
    total_events: int = 0
    
    # 상태별 카운트
    verified_count: int = 0
    flagged_count: int = 0
    unknown_count: int = 0
    
    # 품질 등급별
    gold_count: int = 0
    silver_count: int = 0
    bronze_count: int = 0
    
    # 평균 품질 점수
    average_quality_score: float = 0.0
    
    # 연도별 통계
    by_year: dict = Field(default_factory=dict)
    
    # 주요 이슈
    top_issues: List[dict] = Field(default_factory=list)
    
    # ML 사용 가능 케이스
    ml_usable_count: int = 0
    ml_usable_ratio: float = 0.0
