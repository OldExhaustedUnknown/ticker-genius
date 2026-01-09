"""
PDUFA Event Models
===================
Phase 1: 이벤트 기반 데이터 모델

이 모듈은 PDUFA 이벤트 단위의 데이터 구조를 정의합니다.
기존 CollectedCase(약물 단위)와 분리하여 예측 단위로 사용합니다.

핵심 원칙:
- 각 PDUFA 이벤트는 독립적인 예측 대상
- CRL 횟수는 feature에서 제외 (독립 사건)
- 해당 시점의 feature만 포함

참조: docs/M3_BLUEPRINT_v2.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
import hashlib
import json


@dataclass
class PDUFAEvent:
    """
    단일 PDUFA 이벤트 - CRL 예측의 기본 단위.

    같은 약물이라도 여러 PDUFA 날짜가 있으면 별개의 이벤트입니다.
    예: AXSM의 AXS-05는 3개의 PDUFA 이벤트를 가집니다.
        - 2021-01-08 (CRL)
        - 2021-08-24 (CRL)
        - 2022-08-19 (Approved)

    Attributes:
        event_id: 고유 식별자 (ticker + drug_name + pdufa_date 해시)
        ticker: 주식 티커
        drug_name: 약물 이름
        pdufa_date: PDUFA 날짜 (YYYYMMDD)
        result: 결과 (approved, crl, pending, None)
    """

    # === 식별자 (필수) ===
    ticker: str
    drug_name: str
    pdufa_date: str  # YYYYMMDD 형식
    event_id: str = ""  # 자동 생성됨

    # === 타겟 변수 ===
    result: Optional[str] = None  # "approved", "crl", "pending"

    # === 제출 컨텍스트 ===
    sequence_number: int = 1  # 1=최초, 2=재제출, 3=재재제출...
    submission_type: str = "original"  # "original", "resubmission"
    prior_crl_reason: Optional[str] = None  # 이전 CRL 사유 카테고리

    # === Feature: FDA 지정 (해당 시점 기준) ===
    btd: Optional[bool] = None  # Breakthrough Therapy
    priority_review: Optional[bool] = None
    fast_track: Optional[bool] = None
    orphan_drug: Optional[bool] = None
    accelerated_approval: Optional[bool] = None

    # === Feature: 임상 ===
    primary_endpoint_met: Optional[bool] = None
    phase: Optional[str] = None  # "1", "2", "3", "4"
    nct_id: Optional[str] = None  # ClinicalTrials.gov ID

    # === Feature: AdCom ===
    adcom_held: Optional[bool] = None
    adcom_date: Optional[str] = None  # YYYYMMDD
    adcom_vote_ratio: Optional[float] = None  # 0.0 ~ 1.0

    # === Feature: 제조 ===
    pai_passed: Optional[bool] = None
    warning_letter_active: Optional[bool] = None

    # === 메타데이터 ===
    source_case_id: Optional[str] = None  # 원본 CollectedCase ID
    created_at: datetime = field(default_factory=datetime.now)
    data_quality_score: float = 0.0

    def __post_init__(self):
        """event_id 자동 생성 및 품질 점수 계산."""
        if not self.event_id:
            self.event_id = self._generate_event_id()

        self.data_quality_score = self._calculate_quality()

    def _generate_event_id(self) -> str:
        """
        ticker + drug_name + pdufa_date를 해시하여 고유 ID 생성.

        대소문자 무관하게 동일한 ID를 생성합니다.
        """
        key = f"{self.ticker}_{self.drug_name}_{self.pdufa_date}".lower()
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _calculate_quality(self) -> float:
        """
        데이터 품질 점수 계산.

        점수 구성:
        - 기본 점수: 0.3 (필수 필드 있음)
        - 중요 필드 각 +0.15: primary_endpoint_met, btd, priority_review, adcom_vote_ratio
        - 최대: 1.0
        """
        # 필수 필드 확인
        if not all([self.ticker, self.drug_name, self.pdufa_date]):
            return 0.0

        score = 0.3  # 기본 점수

        # 중요 필드 가산
        important_fields = [
            self.primary_endpoint_met,
            self.btd,
            self.priority_review,
            self.adcom_vote_ratio,
        ]

        for f in important_fields:
            if f is not None:
                score += 0.15

        # 추가 필드 보너스 (낮은 가중치)
        optional_fields = [
            self.orphan_drug,
            self.fast_track,
            self.pai_passed,
            self.result,
        ]

        for f in optional_fields:
            if f is not None:
                score += 0.05

        return min(score, 1.0)

    def to_dict(self) -> dict:
        """
        딕셔너리로 변환 (JSON 직렬화용).

        datetime은 ISO 형식 문자열로 변환됩니다.
        """
        return {
            # 식별자
            "event_id": self.event_id,
            "ticker": self.ticker,
            "drug_name": self.drug_name,
            "pdufa_date": self.pdufa_date,

            # 타겟
            "result": self.result,

            # 제출 컨텍스트
            "sequence_number": self.sequence_number,
            "submission_type": self.submission_type,
            "prior_crl_reason": self.prior_crl_reason,

            # FDA 지정
            "btd": self.btd,
            "priority_review": self.priority_review,
            "fast_track": self.fast_track,
            "orphan_drug": self.orphan_drug,
            "accelerated_approval": self.accelerated_approval,

            # 임상
            "primary_endpoint_met": self.primary_endpoint_met,
            "phase": self.phase,
            "nct_id": self.nct_id,

            # AdCom
            "adcom_held": self.adcom_held,
            "adcom_date": self.adcom_date,
            "adcom_vote_ratio": self.adcom_vote_ratio,

            # 제조
            "pai_passed": self.pai_passed,
            "warning_letter_active": self.warning_letter_active,

            # 메타데이터
            "source_case_id": self.source_case_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "data_quality_score": self.data_quality_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PDUFAEvent":
        """
        딕셔너리에서 PDUFAEvent 생성.

        to_dict()의 역변환입니다.
        """
        # created_at 파싱
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            # 식별자
            event_id=data.get("event_id", ""),
            ticker=data["ticker"],
            drug_name=data["drug_name"],
            pdufa_date=data["pdufa_date"],

            # 타겟
            result=data.get("result"),

            # 제출 컨텍스트
            sequence_number=data.get("sequence_number", 1),
            submission_type=data.get("submission_type", "original"),
            prior_crl_reason=data.get("prior_crl_reason"),

            # FDA 지정
            btd=data.get("btd"),
            priority_review=data.get("priority_review"),
            fast_track=data.get("fast_track"),
            orphan_drug=data.get("orphan_drug"),
            accelerated_approval=data.get("accelerated_approval"),

            # 임상
            primary_endpoint_met=data.get("primary_endpoint_met"),
            phase=data.get("phase"),
            nct_id=data.get("nct_id"),

            # AdCom
            adcom_held=data.get("adcom_held"),
            adcom_date=data.get("adcom_date"),
            adcom_vote_ratio=data.get("adcom_vote_ratio"),

            # 제조
            pai_passed=data.get("pai_passed"),
            warning_letter_active=data.get("warning_letter_active"),

            # 메타데이터
            source_case_id=data.get("source_case_id"),
            created_at=created_at,
            # data_quality_score는 __post_init__에서 자동 계산됨
        )

    def __repr__(self) -> str:
        return (
            f"PDUFAEvent(event_id={self.event_id!r}, "
            f"ticker={self.ticker!r}, drug={self.drug_name!r}, "
            f"date={self.pdufa_date!r}, result={self.result!r})"
        )
