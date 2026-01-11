"""
Data Migration
===============
Step B: CollectedCase → PDUFAEvent 마이그레이션

단일 책임: 기존 수집 데이터를 이벤트 기반 구조로 변환
- processed/*.json 로드
- CollectedCase 파싱
- EventExtractor로 이벤트 추출
- EventStore로 저장

참조: docs/M3_BLUEPRINT_v2.md
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import CollectedCase, FieldValue, SourceInfo, SourceTier
from .event_models import PDUFAEvent
from .event_extractor import EventExtractor
from .event_store import EventStore
from .feature_calculator import FeatureCalculator

logger = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    """마이그레이션 통계."""
    cases_loaded: int = 0
    cases_skipped: int = 0
    events_extracted: int = 0
    events_saved: int = 0
    crl_events: int = 0
    final_events: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """실행 시간 (초)."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class MigrationRunner:
    """
    데이터 마이그레이션 실행기.

    기존 collected/processed/*.json 파일을 읽어서
    events/ 디렉토리에 PDUFAEvent로 저장합니다.

    Usage:
        runner = MigrationRunner()
        stats = runner.run()
        print(runner.get_report())
    """

    def __init__(
        self,
        source_dir: Path = None,
        target_dir: Path = None,
    ):
        """
        Args:
            source_dir: 소스 디렉토리 (기본: data/collected/processed)
            target_dir: 대상 디렉토리 (기본: data/events)
        """
        self.source_dir = Path(source_dir) if source_dir else Path("data/collected/processed")
        self.target_dir = Path(target_dir) if target_dir else Path("data/events")

        self._extractor = EventExtractor()
        self._store = EventStore(base_dir=self.target_dir)
        self._calculator = FeatureCalculator()
        self._stats = MigrationStats()
        self._cases: list[CollectedCase] = []
        self._events: list[PDUFAEvent] = []

    def run(self) -> MigrationStats:
        """
        전체 마이그레이션 실행.

        Returns:
            MigrationStats
        """
        logger.info(f"Starting migration from {self.source_dir} to {self.target_dir}")
        self._stats = MigrationStats()

        # 1. 케이스 로드
        self._cases = self.load_cases()
        self._stats.cases_loaded = len(self._cases)

        # 2. 이벤트 추출
        self._events = self.extract_events()
        self._stats.events_extracted = len(self._events)

        # 3. Feature 검증
        self._events = self._calculator.validate_many(self._events)

        # 4. 저장
        saved_count = self.save_events()
        self._stats.events_saved = saved_count

        # 통계 마무리
        self._stats.end_time = datetime.now()
        extractor_stats = self._extractor.get_stats()
        self._stats.crl_events = extractor_stats.crl_events_found
        self._stats.final_events = extractor_stats.final_events

        logger.info(f"Migration complete: {self._stats.events_saved} events saved")
        return self._stats

    def load_cases(self) -> list[CollectedCase]:
        """
        소스 디렉토리에서 케이스 로드.

        Returns:
            CollectedCase 리스트
        """
        cases = []

        if not self.source_dir.exists():
            logger.warning(f"Source directory not found: {self.source_dir}")
            return cases

        json_files = list(self.source_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")

        for json_file in json_files:
            try:
                case = self._load_single_case(json_file)
                if case:
                    cases.append(case)
            except Exception as e:
                error_msg = f"Failed to load {json_file.name}: {e}"
                logger.error(error_msg)
                self._stats.errors.append(error_msg)
                self._stats.cases_skipped += 1

        return cases

    def extract_events(self) -> list[PDUFAEvent]:
        """
        로드된 케이스에서 이벤트 추출.

        Returns:
            PDUFAEvent 리스트
        """
        if not self._cases:
            self._cases = self.load_cases()

        return self._extractor.extract_all(self._cases)

    def save_events(self) -> int:
        """
        이벤트를 저장소에 저장.

        Returns:
            저장된 이벤트 수
        """
        if not self._events:
            self._events = self.extract_events()

        return self._store.save_many(self._events)

    def get_report(self) -> str:
        """
        마이그레이션 리포트 생성.

        Returns:
            리포트 문자열
        """
        lines = [
            "=" * 50,
            "데이터 마이그레이션 리포트",
            "=" * 50,
            "",
            f"소스: {self.source_dir}",
            f"대상: {self.target_dir}",
            "",
            "--- 통계 ---",
            f"로드된 케이스: {self._stats.cases_loaded}",
            f"스킵된 케이스: {self._stats.cases_skipped}",
            f"추출된 이벤트: {self._stats.events_extracted}",
            f"  - CRL 이벤트: {self._stats.crl_events}",
            f"  - 최종 이벤트: {self._stats.final_events}",
            f"저장된 이벤트: {self._stats.events_saved}",
            "",
            f"실행 시간: {self._stats.duration_seconds:.2f}초",
        ]

        if self._stats.errors:
            lines.extend([
                "",
                "--- 에러 ---",
                *[f"  - {e}" for e in self._stats.errors[:10]],
            ])
            if len(self._stats.errors) > 10:
                lines.append(f"  ... 외 {len(self._stats.errors) - 10}건")

        lines.append("=" * 50)

        return "\n".join(lines)

    def get_events(self) -> list[PDUFAEvent]:
        """추출된 이벤트 반환."""
        return self._events

    def get_stats(self) -> MigrationStats:
        """통계 반환."""
        return self._stats

    # ==================== Internal Methods ====================

    def _load_single_case(self, json_file: Path) -> Optional[CollectedCase]:
        """
        단일 JSON 파일에서 CollectedCase 로드.

        Args:
            json_file: JSON 파일 경로

        Returns:
            CollectedCase 또는 None
        """
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 필수 필드 확인
        if "ticker" not in data or "drug_name" not in data:
            logger.warning(f"Missing required fields in {json_file.name}")
            return None

        # CollectedCase 생성
        case = CollectedCase(
            ticker=data["ticker"],
            drug_name=data["drug_name"],
            case_id=data.get("case_id", ""),
        )

        # FieldValue 필드 파싱
        case.pdufa_date = self._parse_field_value(data.get("pdufa_date"))
        case.result = self._parse_field_value(data.get("result"))
        case.breakthrough_therapy = self._parse_field_value(data.get("breakthrough_therapy"))
        case.priority_review = self._parse_field_value(data.get("priority_review"))
        case.fast_track = self._parse_field_value(data.get("fast_track"))
        case.orphan_drug = self._parse_field_value(data.get("orphan_drug"))
        case.accelerated_approval = self._parse_field_value(data.get("accelerated_approval"))
        case.phase = self._parse_field_value(data.get("phase"))
        case.primary_endpoint_met = self._parse_field_value(data.get("primary_endpoint_met"))
        case.nct_id = self._parse_field_value(data.get("nct_id"))
        case.adcom_held = self._parse_field_value(data.get("adcom_held"))
        case.adcom_date = self._parse_field_value(data.get("adcom_date"))
        case.adcom_vote_ratio = self._parse_field_value(data.get("adcom_vote_ratio"))
        case.has_prior_crl = self._parse_field_value(data.get("has_prior_crl"))
        case.crl_class = self._parse_field_value(data.get("crl_class"))
        case.is_resubmission = self._parse_field_value(data.get("is_resubmission"))
        case.pai_passed = self._parse_field_value(data.get("pai_passed"))
        case.has_warning_letter = self._parse_field_value(data.get("has_warning_letter"))
        case.warning_letter_date = self._parse_field_value(data.get("warning_letter_date"))

        return case

    def _parse_field_value(self, data: Optional[dict]) -> Optional[FieldValue]:
        """
        JSON 딕셔너리를 FieldValue로 파싱.

        Args:
            data: {"value": ..., "confidence": ..., ...} 형식

        Returns:
            FieldValue 또는 None
        """
        if data is None:
            return None

        if not isinstance(data, dict):
            # 단순 값이면 FieldValue로 래핑
            return FieldValue(value=data)

        if "value" not in data:
            return None

        # 소스 정보 파싱
        sources = []
        source_names = data.get("sources", [])
        for name in source_names:
            tier = self._get_source_tier(name)
            sources.append(SourceInfo(name=name, tier=tier))

        return FieldValue(
            value=data["value"],
            sources=sources,
            confidence=data.get("confidence", 1.0),
            needs_manual_review=data.get("needs_review", False),
            conflicts=data.get("conflicts", []),
        )

    @staticmethod
    def _get_source_tier(source_name: str) -> SourceTier:
        """소스 이름에서 티어 추론."""
        tier_map = {
            "openfda": SourceTier.TIER1,
            "fda": SourceTier.TIER1,
            "sec": SourceTier.TIER2,
            "clinicaltrials": SourceTier.TIER2,
            "legacy_v12": SourceTier.TIER3,
            "pr": SourceTier.TIER3,
        }

        name_lower = source_name.lower()
        for key, tier in tier_map.items():
            if key in name_lower:
                return tier

        return SourceTier.TIER4


def run_migration(
    source_dir: str = None,
    target_dir: str = None,
    dry_run: bool = False,
) -> MigrationStats:
    """
    마이그레이션 실행 편의 함수.

    Args:
        source_dir: 소스 디렉토리
        target_dir: 대상 디렉토리
        dry_run: True면 저장하지 않고 통계만 반환

    Returns:
        MigrationStats
    """
    source = Path(source_dir) if source_dir else None
    target = Path(target_dir) if target_dir else None

    runner = MigrationRunner(source_dir=source, target_dir=target)

    if dry_run:
        runner.load_cases()
        runner.extract_events()
        return runner.get_stats()
    else:
        return runner.run()


__all__ = ["MigrationRunner", "MigrationStats", "run_migration"]
