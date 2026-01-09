"""
Incremental Data Verifier
==========================
점진적으로 각 필드를 검증하고 채워가는 시스템.

핵심 원칙:
1. 레거시 데이터를 신뢰하지 않음
2. 공식 소스에서 확인된 것만 "verified"로 표시
3. 한 번에 전부 X → 없는 것 하나씩 채워가기
4. 데이터 오염 방지 (소스 충돌 감지)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """필드 검증 상태."""
    UNVERIFIED = "unverified"  # 아직 검증 안됨
    VERIFIED = "verified"      # 공식 소스에서 확인됨
    CONFLICTED = "conflicted"  # 소스간 충돌
    NOT_FOUND = "not_found"    # 검색했으나 없음
    LEGACY = "legacy"          # 레거시 데이터 (신뢰 안함)


class SourceTier(Enum):
    """소스 신뢰도 등급."""
    TIER1_OFFICIAL = 1    # FDA CDER, OpenFDA (99% 신뢰)
    TIER2_REGULATED = 2   # SEC EDGAR, ClinicalTrials (90% 신뢰)
    TIER3_PUBLIC = 3      # 회사 PR, 뉴스 (75% 신뢰)
    TIER4_INFERRED = 4    # 애널리스트, 추론 (50% 신뢰)
    LEGACY = 99           # 레거시 데이터 (신뢰 안함)


@dataclass
class VerifiedValue:
    """검증된 값과 그 출처."""
    value: Any
    status: VerificationStatus
    source_name: str
    source_tier: SourceTier
    source_url: Optional[str] = None
    verified_at: datetime = field(default_factory=datetime.now)
    raw_data: Optional[dict] = None  # 원본 데이터 보존

    # 충돌 추적
    conflicting_values: list = field(default_factory=list)

    @property
    def is_verified(self) -> bool:
        return self.status == VerificationStatus.VERIFIED

    @property
    def needs_verification(self) -> bool:
        return self.status in (VerificationStatus.UNVERIFIED, VerificationStatus.LEGACY)

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "status": self.status.value,
            "source_name": self.source_name,
            "source_tier": self.source_tier.value,
            "source_url": self.source_url,
            "verified_at": self.verified_at.isoformat(),
            "conflicting_values": self.conflicting_values,
        }


@dataclass
class VerifiableCase:
    """검증 가능한 PDUFA 케이스."""
    case_id: str
    ticker: str
    drug_name: str

    # 필드별 검증 상태
    fields: dict[str, VerifiedValue] = field(default_factory=dict)

    # 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    last_verified_at: Optional[datetime] = None
    verification_attempts: int = 0

    def get_unverified_fields(self) -> list[str]:
        """검증 필요한 필드 목록."""
        return [name for name, val in self.fields.items() if val.needs_verification]

    def get_verification_progress(self) -> dict:
        """검증 진행률 반환."""
        total = len(self.fields)
        verified = sum(1 for v in self.fields.values() if v.is_verified)
        legacy = sum(1 for v in self.fields.values() if v.status == VerificationStatus.LEGACY)

        return {
            "total_fields": total,
            "verified": verified,
            "legacy": legacy,
            "unverified": total - verified - legacy,
            "progress_pct": (verified * 100 // total) if total else 0,
            "legacy_free": legacy == 0,
        }

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "ticker": self.ticker,
            "drug_name": self.drug_name,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "created_at": self.created_at.isoformat(),
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "verification_attempts": self.verification_attempts,
            "progress": self.get_verification_progress(),
        }


class IncrementalVerifier:
    """
    점진적 검증 시스템.

    각 필드를 순차적으로 검증하며, 검증된 값만 신뢰함.
    """

    # 필드별 검증 소스 매핑
    VERIFICATION_SOURCES = {
        "pdufa_date": [
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "company_pr", "tier": SourceTier.TIER3_PUBLIC, "method": "scrape"},
        ],
        "result": [
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
            {"name": "fda_approval_letter", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
        ],
        "breakthrough_therapy": [
            {"name": "fda_cder_btd_list", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
        ],
        "priority_review": [
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
            {"name": "fda_approval_letter", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
        ],
        "orphan_drug": [
            {"name": "fda_oopd_database", "tier": SourceTier.TIER1_OFFICIAL, "method": "download"},
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
        ],
        "fast_track": [
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "company_pr", "tier": SourceTier.TIER3_PUBLIC, "method": "scrape"},
        ],
        "accelerated_approval": [
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
            {"name": "fda_approval_letter", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
        ],
        "adcom_held": [
            {"name": "fda_advisory_calendar", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
        ],
        "adcom_date": [
            {"name": "fda_advisory_calendar", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
        ],
        "adcom_vote_ratio": [
            {"name": "fda_meeting_transcript", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
            {"name": "news", "tier": SourceTier.TIER3_PUBLIC, "method": "scrape"},
        ],
        "has_prior_crl": [
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
        ],
        "crl_class": [
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
        ],
        "nct_id": [
            {"name": "clinicaltrials_gov", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "pubmed", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "sec_filings", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
        ],
        "phase": [
            {"name": "clinicaltrials_gov", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "openfda", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
        ],
        "primary_endpoint_met": [
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
            {"name": "company_pr", "tier": SourceTier.TIER3_PUBLIC, "method": "scrape"},
        ],
        "pai_passed": [
            {"name": "sec_8k", "tier": SourceTier.TIER2_REGULATED, "method": "api"},
        ],
        "has_warning_letter": [
            {"name": "fda_enforcement", "tier": SourceTier.TIER1_OFFICIAL, "method": "api"},
            {"name": "fda_warning_letters_db", "tier": SourceTier.TIER1_OFFICIAL, "method": "scrape"},
        ],
    }

    def __init__(self, data_dir: str = "data/verified"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_case(self, case_id: str) -> Optional[VerifiableCase]:
        """저장된 케이스 로드."""
        case_file = self.data_dir / f"{case_id}.json"
        if not case_file.exists():
            return None

        with open(case_file, encoding="utf-8") as f:
            data = json.load(f)

        case = VerifiableCase(
            case_id=data["case_id"],
            ticker=data["ticker"],
            drug_name=data["drug_name"],
        )

        for field_name, field_data in data.get("fields", {}).items():
            case.fields[field_name] = VerifiedValue(
                value=field_data["value"],
                status=VerificationStatus(field_data["status"]),
                source_name=field_data["source_name"],
                source_tier=SourceTier(field_data["source_tier"]),
                source_url=field_data.get("source_url"),
                conflicting_values=field_data.get("conflicting_values", []),
            )

        return case

    def save_case(self, case: VerifiableCase):
        """케이스 저장."""
        case_file = self.data_dir / f"{case.case_id}.json"
        with open(case_file, "w", encoding="utf-8") as f:
            json.dump(case.to_dict(), f, indent=2, ensure_ascii=False)

    def import_from_collected(self, collected_case: dict) -> VerifiableCase:
        """
        수집된 케이스를 검증 가능한 케이스로 변환.

        레거시 데이터는 LEGACY 상태로 표시 (신뢰 안함).
        """
        case = VerifiableCase(
            case_id=collected_case.get("case_id", ""),
            ticker=collected_case.get("ticker", ""),
            drug_name=collected_case.get("drug_name", ""),
        )

        # 각 필드 변환
        field_mappings = [
            "pdufa_date", "result", "breakthrough_therapy", "priority_review",
            "fast_track", "orphan_drug", "accelerated_approval",
            "adcom_held", "adcom_date", "adcom_vote_ratio",
            "has_prior_crl", "crl_class", "is_resubmission",
            "nct_id", "phase", "primary_endpoint_met",
            "pai_passed", "has_warning_letter",
        ]

        for field_name in field_mappings:
            field_data = collected_case.get(field_name)

            if field_data is None or field_data.get("value") is None:
                # 값이 없는 경우 - UNVERIFIED
                case.fields[field_name] = VerifiedValue(
                    value=None,
                    status=VerificationStatus.UNVERIFIED,
                    source_name="none",
                    source_tier=SourceTier.LEGACY,
                )
            else:
                sources = field_data.get("sources", [])

                # 소스 분류
                if "openfda" in sources:
                    status = VerificationStatus.VERIFIED
                    source_tier = SourceTier.TIER1_OFFICIAL
                    source_name = "openfda"
                elif any(s in sources for s in ["sec_edgar", "clinicaltrials.gov", "pubmed"]):
                    status = VerificationStatus.VERIFIED
                    source_tier = SourceTier.TIER2_REGULATED
                    source_name = sources[0] if sources else "unknown"
                elif "legacy_v12" in sources:
                    # 레거시는 신뢰 안함 - 검증 필요
                    status = VerificationStatus.LEGACY
                    source_tier = SourceTier.LEGACY
                    source_name = "legacy_v12"
                else:
                    status = VerificationStatus.UNVERIFIED
                    source_tier = SourceTier.TIER4_INFERRED
                    source_name = sources[0] if sources else "unknown"

                case.fields[field_name] = VerifiedValue(
                    value=field_data["value"],
                    status=status,
                    source_name=source_name,
                    source_tier=source_tier,
                )

        return case

    def get_next_field_to_verify(self, case: VerifiableCase) -> Optional[tuple[str, list]]:
        """
        다음에 검증할 필드와 사용할 소스 목록 반환.

        우선순위:
        1. LEGACY 상태 필드 (레거시 데이터 대체 필요)
        2. UNVERIFIED 상태 필드
        """
        # 1. 레거시 필드 우선
        for field_name, val in case.fields.items():
            if val.status == VerificationStatus.LEGACY:
                sources = self.VERIFICATION_SOURCES.get(field_name, [])
                if sources:
                    return (field_name, sources)

        # 2. 미검증 필드
        for field_name, val in case.fields.items():
            if val.status == VerificationStatus.UNVERIFIED:
                sources = self.VERIFICATION_SOURCES.get(field_name, [])
                if sources:
                    return (field_name, sources)

        return None

    def update_field(
        self,
        case: VerifiableCase,
        field_name: str,
        value: Any,
        source_name: str,
        source_tier: SourceTier,
        source_url: Optional[str] = None,
        raw_data: Optional[dict] = None,
    ):
        """
        필드 값 업데이트 (검증된 값으로).

        충돌 감지: 기존 값과 다른 경우 conflicting_values에 기록.
        """
        existing = case.fields.get(field_name)

        # 충돌 감지
        conflicting_values = []
        if existing and existing.value is not None and existing.value != value:
            conflicting_values.append({
                "value": existing.value,
                "source": existing.source_name,
                "tier": existing.source_tier.value,
            })
            logger.warning(
                f"Value conflict for {field_name} in {case.case_id}: "
                f"{existing.value} ({existing.source_name}) vs {value} ({source_name})"
            )

        # 새 값으로 업데이트
        case.fields[field_name] = VerifiedValue(
            value=value,
            status=VerificationStatus.VERIFIED,
            source_name=source_name,
            source_tier=source_tier,
            source_url=source_url,
            raw_data=raw_data,
            conflicting_values=conflicting_values,
        )

        case.last_verified_at = datetime.now()
        case.verification_attempts += 1

    def mark_not_found(self, case: VerifiableCase, field_name: str, source_name: str):
        """검색했으나 찾지 못한 경우."""
        case.fields[field_name] = VerifiedValue(
            value=None,
            status=VerificationStatus.NOT_FOUND,
            source_name=source_name,
            source_tier=SourceTier.TIER1_OFFICIAL,
        )
        case.verification_attempts += 1

    def get_verification_summary(self) -> dict:
        """전체 검증 현황 요약."""
        case_files = list(self.data_dir.glob("*.json"))

        summary = {
            "total_cases": len(case_files),
            "fully_verified": 0,
            "legacy_free": 0,
            "by_field": {},
        }

        for case_file in case_files:
            case = self.load_case(case_file.stem)
            if case:
                progress = case.get_verification_progress()
                if progress["progress_pct"] == 100:
                    summary["fully_verified"] += 1
                if progress["legacy_free"]:
                    summary["legacy_free"] += 1

        return summary
