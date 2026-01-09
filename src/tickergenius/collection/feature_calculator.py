"""
Feature Calculator
==================
Phase 3: Feature 시점 검증 및 재계산

단일 책임: 이벤트의 feature 시점 유효성 검증
- 정적 feature (FDA 지정): 시점 무관하게 유지
- 동적 feature (AdCom, 임상): 시점 검증 후 처리
- 데이터 품질 점수 재계산

참조: docs/M3_BLUEPRINT_v2.md
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from copy import deepcopy

from .event_models import PDUFAEvent

logger = logging.getLogger(__name__)


@dataclass
class CalculatorStats:
    """계산기 통계."""
    total_events: int = 0
    features_cleared: int = 0
    features_preserved: int = 0
    validation_errors: int = 0
    errors: list[str] = field(default_factory=list)


class FeatureCalculator:
    """
    Feature 시점 검증 및 재계산기.

    각 PDUFA 이벤트의 feature가 해당 시점에 유효한지 검증합니다.

    원칙:
    - 정적 feature (FDA 지정): 한 번 부여되면 유지되므로 시점 무관
    - 동적 feature (AdCom, 임상결과): 특정 시점에 발생하므로 검증 필요

    Usage:
        calc = FeatureCalculator()
        validated_event = calc.validate_features(event)
        validated_events = calc.validate_many(events)
        stats = calc.get_stats()
    """

    # 정적 feature 목록 (시점 검증 불필요)
    STATIC_FEATURES = [
        'btd',
        'priority_review',
        'fast_track',
        'orphan_drug',
        'accelerated_approval',
    ]

    # 동적 feature 목록 (시점 검증 필요)
    DYNAMIC_FEATURES = [
        ('adcom_held', 'adcom_date'),
        ('adcom_vote_ratio', 'adcom_date'),
        # primary_endpoint_met은 발표일 정보가 없으면 검증 어려움
        # 현재는 보수적으로 유지
    ]

    def __init__(self):
        """초기화."""
        self._stats = CalculatorStats()

    def validate_features(self, event: PDUFAEvent) -> PDUFAEvent:
        """
        이벤트의 feature 시점 유효성 검증.

        Args:
            event: 원본 PDUFAEvent

        Returns:
            검증된 PDUFAEvent (새 인스턴스)
        """
        self._stats.total_events += 1

        # 원본 보존을 위해 깊은 복사
        validated = self._copy_event(event)

        # PDUFA 날짜 파싱
        pdufa_date = self._parse_date(event.pdufa_date)

        if pdufa_date is None:
            # 날짜 파싱 실패 시 원본 그대로 반환
            self._stats.validation_errors += 1
            logger.warning(f"Invalid pdufa_date for {event.ticker}/{event.drug_name}: {event.pdufa_date}")
            return validated

        # 동적 feature 시점 검증
        self._validate_adcom_features(validated, pdufa_date)

        # 품질 점수 재계산
        validated.data_quality_score = validated._calculate_quality()

        return validated

    def validate_many(self, events: list[PDUFAEvent]) -> list[PDUFAEvent]:
        """
        여러 이벤트 일괄 검증.

        Args:
            events: PDUFAEvent 리스트

        Returns:
            검증된 PDUFAEvent 리스트
        """
        validated_events = []

        for event in events:
            try:
                validated = self.validate_features(event)
                validated_events.append(validated)
            except Exception as e:
                error_msg = f"Validation failed for {event.ticker}/{event.drug_name}: {e}"
                logger.error(error_msg)
                self._stats.errors.append(error_msg)
                # 실패해도 원본 추가
                validated_events.append(event)

        return validated_events

    def get_stats(self) -> CalculatorStats:
        """통계 반환."""
        return self._stats

    def reset_stats(self):
        """통계 초기화."""
        self._stats = CalculatorStats()

    # ==================== Internal Methods ====================

    def _copy_event(self, event: PDUFAEvent) -> PDUFAEvent:
        """이벤트 복사."""
        return PDUFAEvent(
            event_id=event.event_id,
            ticker=event.ticker,
            drug_name=event.drug_name,
            pdufa_date=event.pdufa_date,
            result=event.result,
            sequence_number=event.sequence_number,
            submission_type=event.submission_type,
            prior_crl_reason=event.prior_crl_reason,
            btd=event.btd,
            priority_review=event.priority_review,
            fast_track=event.fast_track,
            orphan_drug=event.orphan_drug,
            accelerated_approval=event.accelerated_approval,
            primary_endpoint_met=event.primary_endpoint_met,
            phase=event.phase,
            nct_id=event.nct_id,
            adcom_held=event.adcom_held,
            adcom_date=event.adcom_date,
            adcom_vote_ratio=event.adcom_vote_ratio,
            pai_passed=event.pai_passed,
            warning_letter_active=event.warning_letter_active,
            source_case_id=event.source_case_id,
            created_at=event.created_at,
        )

    def _validate_adcom_features(self, event: PDUFAEvent, pdufa_date: datetime):
        """
        AdCom 관련 feature 시점 검증.

        AdCom이 PDUFA 이후에 열렸다면 해당 시점에서는 알 수 없으므로 제거.
        """
        if event.adcom_date is None:
            # 날짜 정보 없으면 보수적으로 유지
            self._stats.features_preserved += 1
            return

        adcom_date = self._parse_date(event.adcom_date)

        if adcom_date is None:
            # 파싱 실패 시 유지
            self._stats.features_preserved += 1
            return

        if adcom_date > pdufa_date:
            # AdCom이 PDUFA 이후 → 해당 시점에서 알 수 없음
            logger.debug(
                f"Clearing AdCom features for {event.ticker}/{event.drug_name}: "
                f"AdCom {event.adcom_date} > PDUFA {event.pdufa_date}"
            )
            event.adcom_held = None
            event.adcom_date = None
            event.adcom_vote_ratio = None
            self._stats.features_cleared += 1
        else:
            # AdCom이 PDUFA 이전 → 유지
            self._stats.features_preserved += 1

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """날짜 문자열 파싱."""
        if not date_str:
            return None

        # 하이픈 제거 및 정규화
        normalized = str(date_str).replace("-", "")[:8]

        try:
            return datetime.strptime(normalized, "%Y%m%d")
        except ValueError:
            return None
