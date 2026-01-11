"""
Event Extractor
================
Phase 2: CollectedCase → PDUFAEvent 변환기

단일 책임: 약물 단위 데이터를 이벤트 단위로 변환
- API 호출은 crl_searcher에 위임
- 파일 저장은 EventStore에 위임

참조: docs/M3_BLUEPRINT_v2.md
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from .event_models import PDUFAEvent
from .models import CollectedCase, FieldValue

if TYPE_CHECKING:
    from .api_clients import DesignationSearchClient

logger = logging.getLogger(__name__)


@dataclass
class ExtractionStats:
    """추출 통계."""
    total_cases: int = 0
    total_events: int = 0
    final_events: int = 0
    crl_events_found: int = 0      # SEC 검색으로 찾은 CRL
    crl_search_failed: int = 0     # SEC 검색 실패 (추론 금지로 이벤트 미생성)
    skipped_cases: int = 0
    errors: list[str] = field(default_factory=list)


class EventExtractor:
    """
    CollectedCase에서 PDUFAEvent를 추출하는 변환기.

    하나의 CollectedCase(약물)에서 여러 PDUFAEvent를 생성할 수 있습니다.
    - CRL 이력이 없으면: 1개 이벤트 (최종 PDUFA)
    - CRL 이력이 있으면: N개 이벤트 (과거 CRL + 최종)

    Usage:
        extractor = EventExtractor()
        events = extractor.extract_from_case(case)
        all_events = extractor.extract_all(cases)
        stats = extractor.get_stats()
    """

    def __init__(self, crl_searcher: "DesignationSearchClient" = None):
        """
        Args:
            crl_searcher: CRL 검색용 클라이언트 (None이면 추론만 사용)
        """
        self.crl_searcher = crl_searcher
        self._stats = ExtractionStats()

    def extract_from_case(self, case: CollectedCase) -> list[PDUFAEvent]:
        """
        단일 CollectedCase에서 PDUFAEvent 목록 추출.

        Args:
            case: 원본 CollectedCase

        Returns:
            PDUFAEvent 리스트 (시간순 정렬)
        """
        self._stats.total_cases += 1

        # 필수 필드 검증
        if not self._validate_case(case):
            self._stats.skipped_cases += 1
            return []

        events = []

        # 1. 과거 CRL 이벤트 추출 (있는 경우)
        if self._has_prior_crl(case):
            crl_events = self._extract_crl_events(case)
            events.extend(crl_events)

        # 2. 최종 이벤트 생성
        final_event = self._create_final_event(case, len(events) + 1)
        events.append(final_event)
        self._stats.final_events += 1

        # 3. 시간순 정렬 및 sequence_number 재할당
        events = self._sort_and_number_events(events)

        self._stats.total_events += len(events)
        logger.debug(f"Extracted {len(events)} events from {case.ticker}/{case.drug_name}")

        return events

    def extract_all(self, cases: list[CollectedCase]) -> list[PDUFAEvent]:
        """
        여러 CollectedCase에서 일괄 추출.

        Args:
            cases: CollectedCase 리스트

        Returns:
            모든 PDUFAEvent 리스트
        """
        all_events = []

        for case in cases:
            try:
                events = self.extract_from_case(case)
                all_events.extend(events)
            except Exception as e:
                error_msg = f"Failed to extract from {case.ticker}/{case.drug_name}: {e}"
                logger.error(error_msg)
                self._stats.errors.append(error_msg)

        logger.info(f"Extracted {len(all_events)} events from {len(cases)} cases")
        return all_events

    def get_stats(self) -> ExtractionStats:
        """추출 통계 반환."""
        return self._stats

    def reset_stats(self):
        """통계 초기화."""
        self._stats = ExtractionStats()

    # ==================== Internal Methods ====================

    def _validate_case(self, case: CollectedCase) -> bool:
        """케이스 유효성 검증."""
        # pdufa_date 필수
        if not case.pdufa_date or not self._get_field_value(case.pdufa_date):
            logger.warning(f"Skipping {case.ticker}/{case.drug_name}: missing pdufa_date")
            return False

        # 날짜 형식 검증
        pdufa_str = self._get_field_value(case.pdufa_date)
        if not self._is_valid_date(pdufa_str):
            logger.warning(f"Skipping {case.ticker}/{case.drug_name}: invalid date format '{pdufa_str}'")
            return False

        return True

    def _has_prior_crl(self, case: CollectedCase) -> bool:
        """CRL 이력 존재 여부."""
        has_crl = self._get_field_value(case.has_prior_crl)
        is_resub = self._get_field_value(case.is_resubmission)

        # has_prior_crl이 True이거나 is_resubmission > 0
        if has_crl:
            return True
        if is_resub and (is_resub is True or (isinstance(is_resub, (int, float)) and is_resub > 0)):
            return True

        return False

    def _extract_crl_events(self, case: CollectedCase) -> list[PDUFAEvent]:
        """
        과거 CRL 이벤트 추출.

        원칙: 추론 금지. SEC 검색으로 찾지 못하면 CRL 이벤트 생성하지 않음.
        CRL 이력이 있다는 사실만 최종 이벤트에 기록됨.
        """
        crl_events = []

        # SEC 검색 시도 (구현되어 있으면)
        if self.crl_searcher:
            try:
                sec_results = self._search_crl_via_sec(case)
                if sec_results:
                    crl_events = self._create_events_from_sec_results(case, sec_results)
                    self._stats.crl_events_found += len(crl_events)
                    return crl_events
            except Exception as e:
                logger.warning(f"SEC CRL search failed for {case.ticker}: {e}")

        # 추론 금지: SEC에서 못 찾으면 빈 리스트 반환
        # CRL 이력은 최종 이벤트의 has_prior_crl로만 기록됨
        self._stats.crl_search_failed += 1
        logger.debug(f"No CRL events found via SEC for {case.ticker}/{case.drug_name}, skipping CRL event creation")
        return crl_events

    def _search_crl_via_sec(self, case: CollectedCase) -> list[dict]:
        """SEC 8-K에서 CRL 검색."""
        if not self.crl_searcher:
            return []

        final_date = self._get_field_value(case.pdufa_date)

        # search_crl_events 메서드가 있으면 호출
        if hasattr(self.crl_searcher, 'search_crl_events'):
            return self.crl_searcher.search_crl_events(
                ticker=case.ticker,
                drug_name=case.drug_name,
                before_date=final_date
            )

        return []

    def _create_events_from_sec_results(self, case: CollectedCase, sec_results: list[dict]) -> list[PDUFAEvent]:
        """SEC 검색 결과를 PDUFAEvent로 변환."""
        events = []

        for i, result in enumerate(sec_results):
            event = PDUFAEvent(
                ticker=case.ticker,
                drug_name=case.drug_name,
                pdufa_date=result.get("crl_date", ""),
                result="crl",
                sequence_number=i + 1,
                submission_type="original" if i == 0 else "resubmission",
                prior_crl_reason=result.get("reason_category"),
                source_case_id=case.case_id,
            )
            # FDA 지정 복사 (CRL 시점에도 동일했을 것으로 가정)
            self._copy_static_features(case, event)
            events.append(event)

        return events

    def _estimate_crl_events(self, case: CollectedCase) -> list[PDUFAEvent]:
        """
        CRL 날짜 추론 기반 이벤트 생성.

        가정:
        - 각 CRL→재제출 주기 ≈ 180일 (6개월)
        - is_resubmission 값으로 CRL 횟수 추정
        """
        events = []

        # 재제출 횟수 결정
        resub_count = self._get_resubmission_count(case)
        if resub_count == 0:
            return events

        # 최종 PDUFA 날짜에서 역산
        final_date_str = self._get_field_value(case.pdufa_date)
        final_date = self._parse_date(final_date_str)
        if not final_date:
            return events

        # CRL 사유 (있으면)
        crl_reason = self._get_field_value(case.crl_class)

        # 각 CRL 이벤트 생성
        current_date = final_date
        for i in range(resub_count):
            # 약 6개월 전으로 추정
            crl_date = current_date - timedelta(days=180)

            event = PDUFAEvent(
                ticker=case.ticker,
                drug_name=case.drug_name,
                pdufa_date=crl_date.strftime("%Y%m%d"),
                result="crl",
                sequence_number=resub_count - i,  # 역순으로 번호 매김
                submission_type="original" if i == resub_count - 1 else "resubmission",
                prior_crl_reason=crl_reason if i == 0 else None,  # 마지막 CRL 사유만
                source_case_id=case.case_id,
            )
            self._copy_static_features(case, event)
            events.insert(0, event)  # 시간순 정렬

            current_date = crl_date

        logger.debug(f"Estimated {len(events)} CRL events for {case.ticker}/{case.drug_name}")
        return events

    def _get_resubmission_count(self, case: CollectedCase) -> int:
        """재제출 횟수 추출."""
        resub = self._get_field_value(case.is_resubmission)

        if resub is None:
            return 0
        if isinstance(resub, bool):
            return 1 if resub else 0
        if isinstance(resub, (int, float)):
            return int(resub)
        if isinstance(resub, str) and resub.isdigit():
            return int(resub)

        return 0

    def _create_final_event(self, case: CollectedCase, sequence: int) -> PDUFAEvent:
        """최종 PDUFA 이벤트 생성."""
        has_prior = self._has_prior_crl(case)

        event = PDUFAEvent(
            ticker=case.ticker,
            drug_name=case.drug_name,
            pdufa_date=self._get_field_value(case.pdufa_date),
            result=self._get_field_value(case.result),
            sequence_number=sequence,
            submission_type="resubmission" if has_prior else "original",
            source_case_id=case.case_id,
        )

        # 모든 feature 복사
        self._copy_static_features(case, event)
        self._copy_dynamic_features(case, event)

        return event

    def _copy_static_features(self, case: CollectedCase, event: PDUFAEvent):
        """정적 feature 복사 (FDA 지정 등)."""
        event.btd = self._get_field_value(case.breakthrough_therapy)
        event.priority_review = self._get_field_value(case.priority_review)
        event.fast_track = self._get_field_value(case.fast_track)
        event.orphan_drug = self._get_field_value(case.orphan_drug)
        event.accelerated_approval = self._get_field_value(case.accelerated_approval)

    def _copy_dynamic_features(self, case: CollectedCase, event: PDUFAEvent):
        """동적 feature 복사 (임상, AdCom, 제조 등)."""
        # 임상
        event.primary_endpoint_met = self._get_field_value(case.primary_endpoint_met)
        event.phase = self._get_field_value(case.phase)
        event.nct_id = self._get_field_value(case.nct_id)

        # AdCom
        event.adcom_held = self._get_field_value(case.adcom_held)
        event.adcom_date = self._get_field_value(case.adcom_date)
        event.adcom_vote_ratio = self._get_field_value(case.adcom_vote_ratio)

        # 제조
        event.pai_passed = self._get_field_value(case.pai_passed)
        event.warning_letter_active = self._get_field_value(case.has_warning_letter)

    def _sort_and_number_events(self, events: list[PDUFAEvent]) -> list[PDUFAEvent]:
        """시간순 정렬 및 sequence_number 재할당."""
        # 날짜순 정렬
        events.sort(key=lambda e: e.pdufa_date or "")

        # sequence_number 재할당
        for i, event in enumerate(events):
            event.sequence_number = i + 1
            # 여러 이벤트일 때만 submission_type 재설정
            # 단일 이벤트면 기존 submission_type 유지 (CRL 이력 보존)
            if len(events) > 1:
                if i == 0:
                    event.submission_type = "original"
                else:
                    event.submission_type = "resubmission"

        return events

    # ==================== Utility Methods ====================

    @staticmethod
    def _get_field_value(field: Optional[FieldValue]):
        """FieldValue에서 실제 값 추출."""
        if field is None:
            return None
        if isinstance(field, FieldValue):
            return field.value
        return field

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """날짜 문자열 유효성 검사."""
        if not date_str:
            return False

        # 여러 형식 지원
        formats = ["%Y%m%d", "%Y-%m-%d"]
        for fmt in formats:
            try:
                datetime.strptime(str(date_str).replace("-", "")[:8], "%Y%m%d")
                return True
            except ValueError:
                continue

        return False

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
