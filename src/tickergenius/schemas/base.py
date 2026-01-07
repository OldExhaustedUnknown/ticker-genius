# -*- coding: utf-8 -*-
"""
Base types for Ticker-Genius V4

핵심 설계 (DESIGN_FUNDAMENTALS.md):
- 3분류 상태: CONFIRMED / EMPTY / UNKNOWN
- null vs 공집합 문제 해결
- 모든 필드에 출처와 검증 정보 포함

TF 히스토리:
- TF 46차: CRL 필드의 상태 구분 필요성 확인
- TF 56차: 피처별 "PDUFA 이전 확인 가능" 여부 정의
- TF 긴급회의: 플래깅 방식으로 data_quality 필드 도입
"""

from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator

T = TypeVar('T')


class DataStatus(str, Enum):
    """
    데이터 상태 3분류
    
    CONFIRMED: 값이 있고, 검증됨
        예: adcom_vote_ratio = 0.85, source = "FDA transcript"
        
    EMPTY: 값이 없는 것이 정상 (해당없음, 공집합)
        예: AdCom 미개최 → adcom_vote_ratio는 "해당없음"
        예: Accelerated Approval → phase3_count는 "해당없음"
        
    UNKNOWN: 있을 수도 있고 없을 수도 있음 (미확인)
        예: AdCom 개최 여부 자체를 모름
        예: 아직 검증되지 않은 데이터
    """
    CONFIRMED = "CONFIRMED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


class StatusField(BaseModel, Generic[T]):
    """
    상태가 있는 필드
    
    기존 JSON의 null 문제 해결:
    - null이 "없음"인지 "모름"인지 구분 불가
    - 이제 status로 명시적 구분
    
    사용 예:
        # 검증된 값
        field = StatusField.confirmed(True, "FDA press release")
        
        # 해당없음 (AdCom 미개최 등)
        field = StatusField.empty("AdCom not held")
        
        # 미확인
        field = StatusField.unknown("Not yet verified")
    """
    value: Optional[T] = None
    status: DataStatus = DataStatus.UNKNOWN
    source: Optional[str] = None
    verified_at: Optional[datetime] = None
    reason: Optional[str] = None  # EMPTY/UNKNOWN인 경우 사유
    
    class Config:
        # Generic type을 JSON schema에서 지원
        json_schema_extra = {
            "examples": [
                {
                    "value": True,
                    "status": "CONFIRMED",
                    "source": "FDA press release",
                    "verified_at": "2026-01-07T12:00:00Z"
                },
                {
                    "value": None,
                    "status": "EMPTY",
                    "reason": "AdCom not held"
                },
                {
                    "value": None,
                    "status": "UNKNOWN",
                    "reason": "Not yet verified"
                }
            ]
        }
    
    @classmethod
    def confirmed(cls, value: T, source: str, verified_at: Optional[datetime] = None) -> "StatusField[T]":
        """검증된 값 생성"""
        return cls(
            value=value,
            status=DataStatus.CONFIRMED,
            source=source,
            verified_at=verified_at or datetime.utcnow()
        )
    
    @classmethod
    def empty(cls, reason: str) -> "StatusField[T]":
        """해당없음 (공집합) 생성"""
        return cls(
            value=None,
            status=DataStatus.EMPTY,
            reason=reason
        )
    
    @classmethod
    def unknown(cls, reason: str = "Not yet verified") -> "StatusField[T]":
        """미확인 생성"""
        return cls(
            value=None,
            status=DataStatus.UNKNOWN,
            reason=reason
        )
    
    @classmethod
    def from_legacy(cls, value: Any, field_name: str) -> "StatusField":
        """
        기존 데이터에서 변환 (마이그레이션용)
        
        TF 긴급회의 결정:
        - 값 있음 → CONFIRMED (source: "legacy_data")
        - 값 없음 → UNKNOWN (검증 필요)
        """
        if value is not None and value != "" and value != "unknown":
            return cls.confirmed(value, "legacy_data")
        return cls.unknown(f"{field_name} not verified in legacy data")
    
    @property
    def is_confirmed(self) -> bool:
        """검증된 값인지"""
        return self.status == DataStatus.CONFIRMED
    
    @property
    def is_empty(self) -> bool:
        """해당없음(공집합)인지"""
        return self.status == DataStatus.EMPTY
    
    @property
    def is_unknown(self) -> bool:
        """미확인인지"""
        return self.status == DataStatus.UNKNOWN
    
    @property
    def is_usable(self) -> bool:
        """
        분석에 사용 가능 여부
        
        CONFIRMED: 검증된 값이므로 사용 가능
        EMPTY: 해당없음이 확정되었으므로 사용 가능 (0이나 False로 처리)
        UNKNOWN: 검증 안 됐으므로 사용 불가
        """
        return self.status in (DataStatus.CONFIRMED, DataStatus.EMPTY)
    
    def __bool__(self) -> bool:
        """
        Boolean 컨텍스트에서의 동작
        
        주의: is_usable과 다름!
        - CONFIRMED + value=True → True
        - CONFIRMED + value=False → False
        - EMPTY → False
        - UNKNOWN → False
        """
        if self.status == DataStatus.CONFIRMED:
            return bool(self.value)
        return False


# Type aliases for common StatusField types
StatusBool = StatusField[bool]
StatusStr = StatusField[str]
StatusInt = StatusField[int]
StatusFloat = StatusField[float]
StatusDate = StatusField[date]
