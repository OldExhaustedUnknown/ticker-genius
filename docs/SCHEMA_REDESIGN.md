# 스키마 재설계 및 데이터 마이그레이션 계획

**작성일**: 2026-01-10
**상태**: 설계 확정

---

## 1. 현재 데이터 문제점

### 1.1 불일치 목록

| 필드 | 현재 상태 | 문제점 |
|------|----------|--------|
| `pdufa_date` | "20250130" / "2025-01-30" 혼용 | 형식 불일치 |
| `is_resubmission.value` | 0, 1, true 혼용 | 타입 불일치 |
| StatusField 패턴 | 14개 필드만 사용 | 불완전한 추적 |
| `fda_designations` | 직접 객체 | source 추적 없음 |
| `adcom_info` | 직접 객체 | source 추적 없음 |
| `enrollment` | 직접 객체 | StatusField 아님 |
| `p_value_numeric` | 별도 필드 | `p_value` 내부에 있어야 함 |
| `phase3_study_names` | 직접 리스트 | source 추적 없음 |
| `nct_ids` | 직접 리스트 | source 추적 없음 |

### 1.2 설계 원칙 위반

```
❌ "못 찾음" vs "없음" 구분 불가: fda_designations = {bt: false}
   → false가 "확인된 없음"인지 "검색 안함"인지 불명확

❌ 출처 추적 불가: nct_ids = ["NCT123"]
   → 어디서 찾았는지 모름

❌ 신뢰도 정보 없음: enrollment = {count: 302}
   → 얼마나 신뢰할 수 있는지 모름
```

---

## 2. 이상적인 스키마 설계

### 2.1 핵심 원칙

```python
# 원칙 1: 모든 "검색된" 필드는 StatusField 패턴
# 원칙 2: 날짜는 ISO 표준 (YYYY-MM-DD)
# 원칙 3: Boolean은 bool 타입만
# 원칙 4: 중첩 객체도 StatusField로 래핑
# 원칙 5: 파생 필드는 derived_ 접두사
# 원칙 6: 메타데이터는 별도 섹션
```

### 2.2 필드 분류

```
A. 식별자 (Identifiers) - 항상 존재, StatusField 불필요
   - event_id, ticker, company_name, drug_name

B. 검색 필드 (Searchable) - StatusField 패턴 필수
   - approval_type, indication, generic_name, therapeutic_area
   - phase, primary_endpoint_met, p_value, effect_size
   - fda_designations, adcom_info, enrollment
   - safety_signal, pai_passed, warning_letter
   - has_prior_crl, prior_crl_reason
   - nct_ids, phase3_study_names
   - mechanism_of_action

C. 파생 필드 (Derived) - 다른 필드에서 계산, derived_ 접두사
   - derived_is_resubmission (has_prior_crl에서 파생)
   - derived_days_to_pdufa (pdufa_date에서 계산)
   - derived_pdufa_status (days_to_pdufa에서 계산)
   - derived_risk_tier (분석 결과)

D. 분석 결과 (Analysis) - 분석 후 추가
   - analysis_result

E. 메타데이터 (Metadata)
   - data_quality_score, collected_at, enriched_at
   - needs_manual_review, review_reasons
```

### 2.3 새 스키마 정의

```python
# src/tickergenius/schemas/pdufa_event.py (신규)

from __future__ import annotations
from datetime import date, datetime
from typing import Optional, Generic, TypeVar, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class SearchStatus(str, Enum):
    """검색 상태 - 5가지."""
    FOUND = "found"                    # 찾음 (재시도 불필요)
    CONFIRMED_NONE = "confirmed_none"  # 공식적으로 없음 확인 (재시도 불필요)
    NOT_APPLICABLE = "not_applicable"  # 해당 안됨 (재시도 불필요)
    NOT_FOUND = "not_found"            # 못 찾음 (재시도 필요)
    NOT_SEARCHED = "not_searched"      # 검색 안함 (재시도 필요)


class SourceTier(int, Enum):
    """소스 신뢰도."""
    TIER1 = 1  # FDA 공식 (99%)
    TIER2 = 2  # SEC EDGAR, ClinicalTrials.gov (90%)
    TIER3 = 3  # 뉴스, PR (75%)
    TIER4 = 4  # 추론 (50%)


class StatusField(BaseModel, Generic[T]):
    """
    모든 검색 필드의 표준 래퍼.

    CLAUDE.md 원칙 준수:
    - "못 찾음" vs "없음" 구분
    - 출처 추적
    - 신뢰도 기록
    """
    status: SearchStatus
    value: Optional[T] = None
    source: Optional[str] = None
    tier: Optional[SourceTier] = None
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    searched_sources: list[str] = Field(default_factory=list)
    searched_at: Optional[datetime] = None
    error: Optional[str] = None
    note: Optional[str] = None

    @property
    def has_value(self) -> bool:
        return self.status == SearchStatus.FOUND and self.value is not None

    @property
    def needs_retry(self) -> bool:
        return self.status in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @property
    def is_complete(self) -> bool:
        return self.status in (
            SearchStatus.FOUND,
            SearchStatus.CONFIRMED_NONE,
            SearchStatus.NOT_APPLICABLE,
        )

    @classmethod
    def found(cls, value: T, source: str, tier: SourceTier = SourceTier.TIER2,
              confidence: float = 0.9, **kwargs) -> "StatusField[T]":
        """값을 찾았을 때."""
        return cls(
            status=SearchStatus.FOUND,
            value=value,
            source=source,
            tier=tier,
            confidence=confidence,
            searched_at=datetime.now(),
            **kwargs,
        )

    @classmethod
    def not_found(cls, searched_sources: list[str]) -> "StatusField[T]":
        """검색했지만 못 찾았을 때."""
        return cls(
            status=SearchStatus.NOT_FOUND,
            searched_sources=searched_sources,
            searched_at=datetime.now(),
        )

    @classmethod
    def confirmed_none(cls, source: str) -> "StatusField[T]":
        """공식적으로 없음 확인."""
        return cls(
            status=SearchStatus.CONFIRMED_NONE,
            source=source,
            searched_at=datetime.now(),
        )

    @classmethod
    def not_applicable(cls, reason: str = "") -> "StatusField[T]":
        """해당 안됨."""
        return cls(
            status=SearchStatus.NOT_APPLICABLE,
            note=reason,
        )

    @classmethod
    def not_searched(cls) -> "StatusField[T]":
        """아직 검색 안함."""
        return cls(status=SearchStatus.NOT_SEARCHED)


# ============================================================
# 중첩 타입 정의
# ============================================================

class FDADesignations(BaseModel):
    """FDA 지정 정보."""
    breakthrough_therapy: bool = False
    fast_track: bool = False
    priority_review: bool = False
    orphan_drug: bool = False
    accelerated_approval: bool = False


class AdComInfo(BaseModel):
    """Advisory Committee 정보."""
    held: bool = False
    vote_for: Optional[int] = None
    vote_against: Optional[int] = None
    vote_ratio: Optional[float] = None
    outcome: Optional[str] = None  # positive, negative, mixed
    date: Optional[date] = None


class Enrollment(BaseModel):
    """임상 등록 정보."""
    count: int
    type: str  # ACTUAL, ESTIMATED
    nct_id: Optional[str] = None


class PValue(BaseModel):
    """P-value 정보 (문자열 + 숫자 통합)."""
    text: str  # "<0.001", "0.002", "noninferiority"
    numeric: Optional[float] = None
    trial_name: Optional[str] = None


class CRLReason(BaseModel):
    """CRL 사유 정보."""
    category: str  # CLINICAL_DATA, CMC_ISSUE, SAFETY_CONCERN, PAI_FAILURE
    detail: str
    is_resolvable: Optional[bool] = None


class AnalysisResult(BaseModel):
    """분석 결과."""
    p_crl: float
    p_approval: float
    confidence_score: float
    risk_level: str  # LOW, MODERATE, HIGH, EXTREME
    top_positive_factors: list[dict] = Field(default_factory=list)
    top_negative_factors: list[dict] = Field(default_factory=list)
    analyzed_at: datetime
    analysis_version: str = "3.0"


# ============================================================
# 메인 스키마
# ============================================================

class PDUFAEvent(BaseModel):
    """
    PDUFA 이벤트 - 단일 진실 소스.

    모든 필드가 명확한 카테고리에 속함:
    - 식별자: 항상 존재
    - 검색 필드: StatusField 패턴
    - 파생 필드: derived_ 접두사
    - 분석 결과: 분석 후 추가
    - 메타데이터: 시스템 정보
    """

    # ========================================
    # A. 식별자 (Identifiers)
    # ========================================
    event_id: str
    ticker: str
    company_name: str
    drug_name: str
    pdufa_date: date  # ISO 표준 (YYYY-MM-DD)
    result: str  # approved, crl, pending, withdrawn

    # ========================================
    # B. 검색 필드 (StatusField 패턴)
    # ========================================
    # 기본 정보
    approval_type: StatusField[str]  # nda, bla, anda, snda, etc.
    indication: StatusField[str]
    generic_name: StatusField[str]
    therapeutic_area: StatusField[str]
    mechanism_of_action: StatusField[str]

    # 임상 정보
    phase: StatusField[str]  # Phase 1, Phase 2, Phase 3, Approved
    primary_endpoint_met: StatusField[bool]
    p_value: StatusField[PValue]  # 통합된 p-value
    effect_size: StatusField[str]
    nct_ids: StatusField[list[str]]  # StatusField로 래핑
    phase3_study_names: StatusField[list[str]]
    enrollment: StatusField[Enrollment]

    # FDA 정보
    fda_designations: StatusField[FDADesignations]  # StatusField로 래핑
    adcom_info: StatusField[AdComInfo]

    # 제조/안전성
    pai_passed: StatusField[bool]
    warning_letter: StatusField[bool]
    safety_signal: StatusField[bool]

    # CRL 관련
    has_prior_crl: StatusField[bool]
    prior_crl_reason: StatusField[CRLReason]

    # ========================================
    # C. 파생 필드 (Derived)
    # ========================================
    derived_is_resubmission: bool = False
    derived_days_to_pdufa: Optional[int] = None
    derived_pdufa_status: Optional[str] = None  # past, imminent, upcoming
    derived_risk_tier: Optional[str] = None  # HIGH, MEDIUM, LOW

    # ========================================
    # D. 분석 결과 (Analysis)
    # ========================================
    analysis_result: Optional[AnalysisResult] = None

    # ========================================
    # E. 메타데이터 (Metadata)
    # ========================================
    original_case_id: Optional[str] = None
    data_quality_score: float = 0.0
    collected_at: Optional[datetime] = None
    enriched_at: Optional[datetime] = None
    migrated_at: Optional[datetime] = None  # 마이그레이션 시점
    schema_version: str = "3.0"
    needs_manual_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    # ========================================
    # 검증
    # ========================================
    @field_validator("pdufa_date", mode="before")
    @classmethod
    def parse_pdufa_date(cls, v):
        """다양한 날짜 형식을 ISO로 변환."""
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # YYYYMMDD 형식
            if len(v) == 8 and v.isdigit():
                return date(int(v[:4]), int(v[4:6]), int(v[6:8]))
            # ISO 형식
            return date.fromisoformat(v[:10])
        return v

    # ========================================
    # 변환 메서드
    # ========================================
    def to_analysis_context(self) -> "AnalysisContext":
        """AnalysisContext로 변환."""
        from tickergenius.analysis.pdufa._context import (
            AnalysisContext,
            FDADesignations as CtxFDA,
            AdComInfo as CtxAdCom,
            ClinicalInfo,
            ManufacturingInfo,
        )

        # FDA 지정
        fda = self.fda_designations.value or FDADesignations()
        ctx_fda = CtxFDA(
            breakthrough_therapy=fda.breakthrough_therapy,
            priority_review=fda.priority_review,
            fast_track=fda.fast_track,
            orphan_drug=fda.orphan_drug,
            accelerated_approval=fda.accelerated_approval,
        )

        # AdCom
        adcom = self.adcom_info.value or AdComInfo()
        ctx_adcom = CtxAdCom(
            was_held=adcom.held,
            vote_ratio=adcom.vote_ratio,
            outcome=adcom.outcome,
            adcom_date=adcom.date,
        )

        # 임상
        nct_list = self.nct_ids.value or []
        ctx_clinical = ClinicalInfo(
            phase=self.phase.value or "phase3",
            primary_endpoint_met=self.primary_endpoint_met.value,
            nct_id=nct_list[0] if nct_list else None,
        )

        # 제조
        ctx_mfg = ManufacturingInfo(
            pai_passed=self.pai_passed.value or False,
            has_warning_letter=self.warning_letter.value or False,
        )

        return AnalysisContext(
            ticker=self.ticker,
            drug_name=self.drug_name,
            pdufa_date=self.pdufa_date,
            days_to_pdufa=self.derived_days_to_pdufa,
            is_resubmission=self.derived_is_resubmission,
            fda_designations=ctx_fda,
            adcom=ctx_adcom,
            clinical=ctx_clinical,
            manufacturing=ctx_mfg,
        )

    # ========================================
    # 파일 I/O
    # ========================================
    @classmethod
    def load(cls, file_path) -> "PDUFAEvent":
        """JSON 파일에서 로드."""
        import json
        from pathlib import Path
        with open(Path(file_path), "r", encoding="utf-8") as f:
            return cls.model_validate(json.load(f))

    def save(self, file_path):
        """JSON 파일로 저장."""
        import json
        from pathlib import Path
        with open(Path(file_path), "w", encoding="utf-8") as f:
            json.dump(
                self.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
```

---

## 3. 마이그레이션 계획

### 3.1 마이그레이션 단계

```
Stage 1: 새 스키마 생성
├── src/tickergenius/schemas/pdufa_event.py 작성
└── 테스트 작성

Stage 2: 마이그레이션 스크립트 작성
├── scripts/migrate_to_v3.py
├── 필드별 변환 로직
└── 검증 로직

Stage 3: 데이터 마이그레이션 실행
├── data/enriched/*.json 백업
├── 523건 변환
└── 검증

Stage 4: 구 스키마 정리
├── schemas/enriched.py 삭제 (신규 작성 안함)
├── collection/event_models.py 삭제
└── 문서 업데이트
```

### 3.2 필드별 변환 로직

```python
# scripts/migrate_to_v3.py

def migrate_event(old_data: dict) -> dict:
    """enriched/*.json → PDUFAEvent 형식 변환."""

    # 1. pdufa_date 정규화 (ISO 형식)
    pdufa_date = normalize_date(old_data["pdufa_date"])

    # 2. is_resubmission → derived_is_resubmission
    is_resub = old_data.get("is_resubmission", {})
    derived_is_resubmission = bool(is_resub.get("value", 0))

    # 3. fda_designations → StatusField[FDADesignations]
    fda_old = old_data.get("fda_designations", {})
    fda_designations = {
        "status": "found",
        "value": fda_old,
        "source": "legacy_migration",
        "tier": 3,
        "confidence": 0.75,
        "searched_at": datetime.now().isoformat(),
    }

    # 4. adcom_info → StatusField[AdComInfo]
    adcom_old = old_data.get("adcom_info", {})
    adcom_info = {
        "status": "found" if adcom_old.get("held") else "not_applicable",
        "value": {
            "held": adcom_old.get("held", False),
            "vote_for": None,
            "vote_against": None,
            "vote_ratio": adcom_old.get("vote_ratio"),
            "outcome": adcom_old.get("outcome"),
            "date": None,
        },
        "source": "legacy_migration",
        "tier": 3,
        "confidence": 0.75,
    }

    # 5. p_value + p_value_numeric → StatusField[PValue]
    p_old = old_data.get("p_value", {})
    p_numeric = old_data.get("p_value_numeric")
    p_value = {
        "status": p_old.get("status", "not_searched"),
        "value": {
            "text": p_old.get("value", ""),
            "numeric": p_numeric,
            "trial_name": p_old.get("trial"),
        } if p_old.get("status") == "found" else None,
        "source": p_old.get("source"),
        "confidence": p_old.get("confidence", 0),
    }

    # 6. nct_ids → StatusField[list[str]]
    nct_old = old_data.get("nct_ids", [])
    nct_ids = {
        "status": "found" if nct_old else "not_found",
        "value": nct_old,
        "source": "clinicaltrials.gov" if nct_old else None,
        "tier": 2,
        "confidence": 0.9 if nct_old else 0,
    }

    # 7. phase3_study_names → StatusField[list[str]]
    studies_old = old_data.get("phase3_study_names", [])
    phase3_study_names = {
        "status": "found" if studies_old else "not_found",
        "value": studies_old,
        "source": "clinicaltrials.gov" if studies_old else None,
        "tier": 2,
        "confidence": 0.9 if studies_old else 0,
    }

    # 8. enrollment → StatusField[Enrollment]
    enroll_old = old_data.get("enrollment")
    if enroll_old and enroll_old.get("count"):
        enrollment = {
            "status": "found",
            "value": {
                "count": enroll_old["count"],
                "type": enroll_old.get("type", "ACTUAL"),
                "nct_id": enroll_old.get("nct_id"),
            },
            "source": enroll_old.get("source", "clinicaltrials.gov"),
            "tier": 2,
            "confidence": 0.9,
        }
    else:
        enrollment = {"status": "not_searched"}

    # 9. mechanism_of_action → StatusField[str]
    moa_old = old_data.get("mechanism_of_action", "")
    mechanism_of_action = {
        "status": "found" if moa_old else "not_searched",
        "value": moa_old if moa_old else None,
        "source": "web_search",
        "tier": 3,
        "confidence": 0.75 if moa_old else 0,
    }

    # 10. prior_crl_reason → StatusField[CRLReason]
    crl_old = old_data.get("prior_crl_reason")
    if isinstance(crl_old, dict) and crl_old.get("status") == "found":
        prior_crl_reason = {
            "status": "found",
            "value": {
                "category": crl_old.get("category", "UNKNOWN"),
                "detail": crl_old.get("value", ""),
                "is_resolvable": None,
            },
            "source": crl_old.get("source"),
            "confidence": crl_old.get("confidence", 0),
        }
    else:
        prior_crl_reason = {"status": "not_applicable"}

    # 최종 변환
    return {
        # 식별자
        "event_id": old_data["event_id"],
        "ticker": old_data["ticker"],
        "company_name": old_data["company_name"],
        "drug_name": old_data["drug_name"],
        "pdufa_date": pdufa_date,
        "result": old_data["result"],

        # 검색 필드 (StatusField)
        "approval_type": old_data.get("approval_type", {"status": "not_searched"}),
        "indication": old_data.get("indication", {"status": "not_searched"}),
        "generic_name": old_data.get("generic_name", {"status": "not_searched"}),
        "therapeutic_area": old_data.get("therapeutic_area", {"status": "not_searched"}),
        "mechanism_of_action": mechanism_of_action,
        "phase": old_data.get("phase", {"status": "not_searched"}),
        "primary_endpoint_met": old_data.get("primary_endpoint_met", {"status": "not_searched"}),
        "p_value": p_value,
        "effect_size": old_data.get("effect_size", {"status": "not_searched"}),
        "nct_ids": nct_ids,
        "phase3_study_names": phase3_study_names,
        "enrollment": enrollment,
        "fda_designations": fda_designations,
        "adcom_info": adcom_info,
        "pai_passed": old_data.get("pai_passed", {"status": "not_searched"}),
        "warning_letter": old_data.get("warning_letter", {"status": "not_searched"}),
        "safety_signal": old_data.get("safety_signal", {"status": "not_searched"}),
        "has_prior_crl": old_data.get("has_prior_crl", {"status": "not_searched"}),
        "prior_crl_reason": prior_crl_reason,

        # 파생 필드
        "derived_is_resubmission": derived_is_resubmission,
        "derived_days_to_pdufa": old_data.get("days_to_pdufa"),
        "derived_pdufa_status": old_data.get("pdufa_status"),
        "derived_risk_tier": old_data.get("risk_tier"),

        # 분석 결과
        "analysis_result": None,

        # 메타데이터
        "original_case_id": old_data.get("original_case_id"),
        "data_quality_score": old_data.get("data_quality_score", 0),
        "collected_at": old_data.get("collected_at"),
        "enriched_at": old_data.get("enriched_at"),
        "migrated_at": datetime.now().isoformat(),
        "schema_version": "3.0",
        "needs_manual_review": old_data.get("needs_manual_review", False),
        "review_reasons": old_data.get("review_reasons", []),
    }


def normalize_date(date_str: str) -> str:
    """날짜를 ISO 형식(YYYY-MM-DD)으로 정규화."""
    if not date_str:
        return None

    # YYYYMMDD 형식
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # 이미 ISO 형식
    if len(date_str) >= 10 and date_str[4] == "-":
        return date_str[:10]

    return date_str
```

### 3.3 마이그레이션 실행 스크립트

```python
# scripts/migrate_to_v3.py

import json
import shutil
from pathlib import Path
from datetime import datetime

def main():
    """enriched 데이터를 v3 스키마로 마이그레이션."""

    enriched_dir = Path("data/enriched")
    backup_dir = Path("data/enriched_backup_v2")

    # 1. 백업
    print("1. 백업 중...")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(enriched_dir, backup_dir)
    print(f"   백업 완료: {backup_dir}")

    # 2. 마이그레이션
    print("2. 마이그레이션 중...")
    files = list(enriched_dir.glob("*.json"))
    success = 0
    failed = []

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            new_data = migrate_event(old_data)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)

            success += 1
        except Exception as e:
            failed.append((file_path.name, str(e)))

    # 3. 결과 출력
    print(f"\n=== 마이그레이션 완료 ===")
    print(f"성공: {success}건")
    print(f"실패: {len(failed)}건")

    if failed:
        print("\n실패 목록:")
        for name, error in failed:
            print(f"  - {name}: {error}")

    # 4. 검증
    print("\n3. 검증 중...")
    from tickergenius.schemas.pdufa_event import PDUFAEvent

    valid = 0
    invalid = []
    for file_path in files:
        try:
            PDUFAEvent.load(file_path)
            valid += 1
        except Exception as e:
            invalid.append((file_path.name, str(e)))

    print(f"검증 통과: {valid}건")
    print(f"검증 실패: {len(invalid)}건")

    if invalid:
        print("\n검증 실패 목록:")
        for name, error in invalid[:10]:  # 처음 10개만
            print(f"  - {name}: {error}")


if __name__ == "__main__":
    main()
```

---

## 4. 변경 요약

### 4.1 스키마 변경

| 항목 | Before | After |
|------|--------|-------|
| `pdufa_date` | str (혼용) | date (ISO) |
| `is_resubmission` | StatusField[int\|bool] | `derived_is_resubmission: bool` |
| `fda_designations` | 직접 객체 | StatusField[FDADesignations] |
| `adcom_info` | 직접 객체 | StatusField[AdComInfo] |
| `nct_ids` | list[str] | StatusField[list[str]] |
| `phase3_study_names` | list[str] | StatusField[list[str]] |
| `enrollment` | 직접 객체 | StatusField[Enrollment] |
| `p_value` + `p_value_numeric` | 별도 필드 | StatusField[PValue] (통합) |
| `mechanism_of_action` | str | StatusField[str] |

### 4.2 원칙 준수

```
✅ 모든 검색 필드 = StatusField 패턴
✅ 날짜 = ISO 표준
✅ Boolean = bool 타입만
✅ 출처 추적 = 모든 필드
✅ 파생 필드 = derived_ 접두사
```

---

## 5. 실행 순서

```
1. src/tickergenius/schemas/pdufa_event.py 생성
2. 테스트 작성 및 검증
3. scripts/migrate_to_v3.py 생성
4. 마이그레이션 실행 (백업 자동 생성)
5. 검증
6. 구 코드/문서 정리
```

---

## 6. 확률 계산 및 주가 예측 스키마

### 6.1 확률 계산용 필드 매핑

```python
# 확률 계산에 사용되는 필드 (12개 레이어)

PROBABILITY_FIELDS = {
    # Layer 1: Base
    "base_probability": {
        "fields": ["approval_type", "therapeutic_area"],
        "description": "신청 유형별 기본 승인률",
    },

    # Layer 2: Designation
    "designation_adjustment": {
        "fields": [
            "fda_designations.breakthrough_therapy",  # BTD: +12%
            "fda_designations.priority_review",       # PR: +8%
            "fda_designations.fast_track",            # FT: +5%
            "fda_designations.orphan_drug",           # OD: +6%
            "fda_designations.accelerated_approval",  # AA: +10%
        ],
        "description": "FDA 지정에 따른 승인률 조정",
    },

    # Layer 3: AdCom
    "adcom_adjustment": {
        "fields": [
            "adcom_info.held",
            "adcom_info.vote_ratio",
            "adcom_info.outcome",
        ],
        "description": "Advisory Committee 결과 반영",
        "rules": {
            "vote_ratio >= 0.7": "+8%",
            "vote_ratio 0.5-0.7": "+3%",
            "vote_ratio < 0.5": "-15%",
        },
    },

    # Layer 4: CRL History
    "crl_adjustment": {
        "fields": [
            "has_prior_crl",
            "prior_crl_reason",
            "derived_is_resubmission",
        ],
        "description": "CRL 이력 반영 (독립 사건으로 취급)",
        "rules": {
            "first_submission": "baseline",
            "resubmission_cmc_only": "+5% (CMC 문제는 해결 가능)",
            "resubmission_clinical": "-10% (임상 문제는 심각)",
        },
    },

    # Layer 5: Clinical
    "clinical_adjustment": {
        "fields": [
            "primary_endpoint_met",
            "p_value.numeric",
            "effect_size",
            "phase",
            "enrollment.count",
        ],
        "description": "임상 결과 반영",
    },

    # Layer 6: Manufacturing
    "manufacturing_adjustment": {
        "fields": [
            "pai_passed",
            "warning_letter",
            "safety_signal",
        ],
        "description": "제조 시설 상태 반영",
    },
}
```

### 6.2 주가 예측 스키마

```python
# src/tickergenius/schemas/price_models.py (신규)

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class PricePoint(BaseModel):
    """단일 주가 포인트."""
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int
    source: str = "yahoo"  # yahoo, alpha_vantage, polygon


class PriceHistory(BaseModel):
    """티커별 주가 히스토리."""
    ticker: str
    currency: str = "USD"
    exchange: str = ""
    last_updated: datetime
    prices: list[PricePoint] = Field(default_factory=list)

    def get_price_on(self, target_date: date) -> Optional[PricePoint]:
        """특정 날짜의 가격 조회."""
        for p in self.prices:
            if p.date == target_date:
                return p
        return None

    def get_range(self, start: date, end: date) -> list[PricePoint]:
        """기간 내 가격 조회."""
        return [p for p in self.prices if start <= p.date <= end]


class PDUFAPriceWindow(BaseModel):
    """
    PDUFA 이벤트 전후 주가 윈도우.

    주가 예측 및 백테스트에 사용됨.
    """
    event_id: str
    ticker: str
    pdufa_date: date
    result: str  # approved, crl

    # PDUFA 전 가격 (진입 시점 판단용)
    price_d_minus_30: Optional[PricePoint] = None  # 30일 전
    price_d_minus_7: Optional[PricePoint] = None   # 7일 전
    price_d_minus_1: Optional[PricePoint] = None   # 전날 (종가)

    # PDUFA 당일/후 가격 (결과 측정용)
    price_d_0: Optional[PricePoint] = None         # 당일
    price_d_plus_1: Optional[PricePoint] = None    # 다음날
    price_d_plus_7: Optional[PricePoint] = None    # 7일 후
    price_d_plus_30: Optional[PricePoint] = None   # 30일 후

    # 계산된 수익률
    return_d0_vs_d_minus_1: Optional[float] = None     # 당일 수익률
    return_d7_vs_d_minus_1: Optional[float] = None     # 7일 수익률
    return_d30_vs_d_minus_1: Optional[float] = None    # 30일 수익률

    # 변동성 지표
    volatility_30d: Optional[float] = None  # 30일 변동성
    avg_volume_30d: Optional[float] = None  # 30일 평균 거래량

    def calculate_returns(self):
        """수익률 계산."""
        if not self.price_d_minus_1:
            return

        base = float(self.price_d_minus_1.adj_close)

        if self.price_d_0:
            self.return_d0_vs_d_minus_1 = (
                float(self.price_d_0.adj_close) - base
            ) / base

        if self.price_d_plus_7:
            self.return_d7_vs_d_minus_1 = (
                float(self.price_d_plus_7.adj_close) - base
            ) / base

        if self.price_d_plus_30:
            self.return_d30_vs_d_minus_1 = (
                float(self.price_d_plus_30.adj_close) - base
            ) / base


class TradingSignal(BaseModel):
    """
    거래 신호 - 확률 계산 결과를 기반으로 생성.
    """
    event_id: str
    ticker: str
    pdufa_date: date
    generated_at: datetime

    # 확률
    p_approval: float
    p_crl: float
    confidence: float

    # 시장 가격
    current_price: Optional[Decimal] = None
    iv_rank: Optional[float] = None  # Implied Volatility Rank

    # 신호
    signal_type: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    signal_strength: float  # 0.0 ~ 1.0

    # 근거
    top_factors: list[dict] = Field(default_factory=list)
    risk_factors: list[dict] = Field(default_factory=list)

    # 추천 전략
    recommended_strategy: Optional[str] = None  # long_stock, call_spread, etc.
    entry_price_range: Optional[tuple[Decimal, Decimal]] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
```

### 6.3 확장된 PDUFAEvent 스키마 (주가 연동)

```python
# PDUFAEvent에 추가할 필드

class PDUFAEvent(BaseModel):
    # ... 기존 필드 ...

    # ========================================
    # F. 주가 관련 (Price Data)
    # ========================================
    price_window: Optional[PDUFAPriceWindow] = None
    trading_signal: Optional[TradingSignal] = None

    # 백테스트 결과 (과거 이벤트)
    backtest_result: Optional[BacktestResult] = None


class BacktestResult(BaseModel):
    """백테스트 결과."""
    strategy: str
    entry_date: date
    exit_date: date
    entry_price: Decimal
    exit_price: Decimal
    return_pct: float
    holding_days: int
    realized_pnl: Decimal
    slippage_cost: Decimal
    commission: Decimal
```

### 6.4 데이터베이스 설계 (SQLite/PostgreSQL)

```sql
-- 주가 히스토리 테이블 (티커별)
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    adj_close DECIMAL(12, 4),
    volume BIGINT,
    source VARCHAR(20) DEFAULT 'yahoo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker, date)
);

CREATE INDEX idx_price_ticker ON price_history(ticker);
CREATE INDEX idx_price_date ON price_history(date);
CREATE INDEX idx_price_ticker_date ON price_history(ticker, date);

-- PDUFA 이벤트 테이블
CREATE TABLE pdufa_events (
    event_id VARCHAR(16) PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(200),
    drug_name VARCHAR(200) NOT NULL,
    pdufa_date DATE NOT NULL,
    result VARCHAR(20),

    -- 검색 필드 (JSON으로 저장)
    approval_type JSON,
    indication JSON,
    fda_designations JSON,
    adcom_info JSON,
    phase JSON,
    primary_endpoint_met JSON,
    p_value JSON,
    nct_ids JSON,

    -- 파생 필드
    derived_is_resubmission BOOLEAN DEFAULT FALSE,
    derived_days_to_pdufa INTEGER,
    derived_risk_tier VARCHAR(10),

    -- 분석 결과
    analysis_result JSON,

    -- 메타데이터
    data_quality_score REAL DEFAULT 0,
    schema_version VARCHAR(10) DEFAULT '3.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ticker) REFERENCES tickers(ticker)
);

CREATE INDEX idx_event_ticker ON pdufa_events(ticker);
CREATE INDEX idx_event_date ON pdufa_events(pdufa_date);
CREATE INDEX idx_event_result ON pdufa_events(result);

-- PDUFA 주가 윈도우 테이블
CREATE TABLE pdufa_price_windows (
    event_id VARCHAR(16) PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    pdufa_date DATE NOT NULL,
    result VARCHAR(20),

    -- 가격 포인트 (JSON)
    price_d_minus_30 JSON,
    price_d_minus_7 JSON,
    price_d_minus_1 JSON,
    price_d_0 JSON,
    price_d_plus_1 JSON,
    price_d_plus_7 JSON,
    price_d_plus_30 JSON,

    -- 수익률
    return_d0 REAL,
    return_d7 REAL,
    return_d30 REAL,

    -- 변동성
    volatility_30d REAL,
    avg_volume_30d REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_id) REFERENCES pdufa_events(event_id)
);

-- 거래 신호 테이블
CREATE TABLE trading_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id VARCHAR(16) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    pdufa_date DATE NOT NULL,
    generated_at TIMESTAMP NOT NULL,

    p_approval REAL NOT NULL,
    p_crl REAL NOT NULL,
    confidence REAL NOT NULL,

    current_price DECIMAL(12, 4),
    iv_rank REAL,

    signal_type VARCHAR(20),
    signal_strength REAL,

    top_factors JSON,
    risk_factors JSON,
    recommended_strategy VARCHAR(50),

    FOREIGN KEY (event_id) REFERENCES pdufa_events(event_id)
);

CREATE INDEX idx_signal_ticker ON trading_signals(ticker);
CREATE INDEX idx_signal_date ON trading_signals(pdufa_date);
```

### 6.5 주가 수집 파이프라인

```python
# src/tickergenius/collection/price_collector.py (신규)

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import yfinance as yf

from tickergenius.schemas.price_models import (
    PricePoint,
    PriceHistory,
    PDUFAPriceWindow,
)


class PriceCollector:
    """티커별 주가 수집기."""

    def __init__(self, source: str = "yahoo"):
        self.source = source

    def fetch_history(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> PriceHistory:
        """기간 내 주가 히스토리 조회."""

        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
        )

        prices = []
        for idx, row in df.iterrows():
            prices.append(PricePoint(
                date=idx.date(),
                open=Decimal(str(row["Open"])),
                high=Decimal(str(row["High"])),
                low=Decimal(str(row["Low"])),
                close=Decimal(str(row["Close"])),
                adj_close=Decimal(str(row.get("Adj Close", row["Close"]))),
                volume=int(row["Volume"]),
                source=self.source,
            ))

        return PriceHistory(
            ticker=ticker,
            last_updated=datetime.now(),
            prices=prices,
        )

    def build_pdufa_window(
        self,
        ticker: str,
        pdufa_date: date,
        result: str,
        event_id: str,
    ) -> PDUFAPriceWindow:
        """PDUFA 이벤트 전후 주가 윈도우 생성."""

        # 60일 전 ~ 40일 후 데이터 조회
        start = pdufa_date - timedelta(days=60)
        end = pdufa_date + timedelta(days=40)

        history = self.fetch_history(ticker, start, end)

        def find_price(target: date) -> Optional[PricePoint]:
            # 해당 날짜 또는 가장 가까운 이전 거래일
            for delta in range(5):
                p = history.get_price_on(target - timedelta(days=delta))
                if p:
                    return p
            return None

        window = PDUFAPriceWindow(
            event_id=event_id,
            ticker=ticker,
            pdufa_date=pdufa_date,
            result=result,
            price_d_minus_30=find_price(pdufa_date - timedelta(days=30)),
            price_d_minus_7=find_price(pdufa_date - timedelta(days=7)),
            price_d_minus_1=find_price(pdufa_date - timedelta(days=1)),
            price_d_0=find_price(pdufa_date),
            price_d_plus_1=find_price(pdufa_date + timedelta(days=1)),
            price_d_plus_7=find_price(pdufa_date + timedelta(days=7)),
            price_d_plus_30=find_price(pdufa_date + timedelta(days=30)),
        )

        window.calculate_returns()
        return window
```

---

## 7. 스키마 관계도

```
┌─────────────────────────────────────────────────────────────────┐
│                        데이터베이스 관계도                       │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │   Ticker    │
    │  (ABBV)     │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌─────────┐  ┌─────────────┐
│ Price   │  │ PDUFAEvent  │
│ History │  │ (이벤트)    │
└─────────┘  └──────┬──────┘
    │               │
    │               │
    └───────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ PDUFAPrice   │
     │ Window       │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ Trading      │
     │ Signal       │
     └──────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                        데이터 플로우                            │
└─────────────────────────────────────────────────────────────────┘

    수집 → 보강 → 분석 → 신호 생성 → 백테스트

    [Collection]     [Enrichment]    [Analysis]     [Trading]
        │                │               │              │
        ▼                ▼               ▼              ▼
    PDUFAEvent      StatusField     P(CRL)         Signal
    (기본 정보)     (검색 결과)     P(Approval)    (매매 신호)
                                        │              │
                                        ▼              ▼
                                   PriceWindow    Backtest
                                   (주가 윈도우)   (검증)
```

---

---

## 9. 현실적 스키마 확장 (2026-01-10, 3회 검토 후)

### 9.1 수집 전략 분류

| 분류 | 전략 | 갱신 주기 |
|------|------|----------|
| **사전 수집** | enriched JSON에 저장 | 수집 시 1회 |
| **캐시 + 갱신** | 회사별 캐시 | 30일 |
| **분석 시 검색** | 확률 계산 시 실시간 | 매 요청 |

### 9.2 신규 필드 (12개)

```python
# === 사전 수집 (5개) - enriched JSON에 저장 ===

is_single_arm: StatusField[bool]
# 소스: ClinicalTrials.gov API designInfo.interventionModel
# 판별: "SINGLE_GROUP" 또는 allocation="NON_RANDOMIZED"

trial_region: StatusField[str]  # "us_only" | "global" | "ex_us"
# 소스: ClinicalTrials.gov API locations[].country 집계

is_biosimilar: StatusField[bool]
# 수집 순서: 웹서치 → FDA Purple Book API → 접미사 패턴(-xxxx)

is_first_in_class: StatusField[bool]
# 소스: FDA 연간 Novel Drug Approvals 보고서 웹서치

crl_reason_type: StatusField[str]  # "cmc" | "efficacy" | "safety" | "labeling" | "unknown"
# 소스: CRL 발표문 웹서치 (SEC 8-K, 회사 PR)


# === 캐시 + 30일 갱신 (4개) - 회사별 캐시 ===

warning_letter_date: StatusField[date]
# 소스: FDA Warning Letters DB (회사명 + 공장명 검색)

fda_483_date: StatusField[date]
# 소스: FDA 483 DB

fda_483_observations: StatusField[int]
# 소스: FDA 483 DB (관찰 수)

cdmo_name: StatusField[str]
# 소스: SEC 10-K "manufacturing agreement" 검색


# === 분석 시 검색 (3개) - 실시간 웹서치 ===

pai_passed: StatusField[bool]
# 소스: 웹서치 "{drug} PAI FDA passed"

pai_date: StatusField[date]
# 소스: 웹서치

clinical_hold_history: StatusField[bool]
# 소스: 웹서치 "{drug} {company} clinical hold FDA"
```

### 9.3 수집 로직

```python
# 바이오시밀러 판별 (우선순위)
async def detect_biosimilar(drug_name: str, company: str) -> StatusField[bool]:
    # 1. 웹서치
    result = await websearch(f"{drug_name} biosimilar FDA")
    if result.confidence > 0.8:
        return StatusField.found(result.is_biosimilar, "websearch")

    # 2. FDA Purple Book API
    purple_book = await fda_purple_book_search(drug_name)
    if purple_book.found:
        return StatusField.found(purple_book.is_biosimilar, "fda_purple_book")

    # 3. 접미사 패턴 (-xxxx)
    is_biosim = bool(re.search(r'-[a-z]{4}$', drug_name.lower()))
    return StatusField.found(is_biosim, "pattern_match", confidence=0.7)


# CRL 사유 판별
async def detect_crl_reason(company: str, drug: str) -> StatusField[str]:
    result = await websearch(f"{company} {drug} complete response letter reason")

    keywords = {
        "cmc": ["manufacturing", "CMC", "facility", "quality", "chemistry"],
        "efficacy": ["efficacy", "clinical", "endpoint", "data", "trial"],
        "safety": ["safety", "adverse", "risk", "black box", "side effect"],
        "labeling": ["labeling", "label", "indication", "REMS"],
    }

    for reason, words in keywords.items():
        if any(w.lower() in result.text.lower() for w in words):
            return StatusField.found(reason, "websearch_crl")

    return StatusField.not_found(["websearch_crl"])
```

### 9.4 파생 필드 (스키마 추가 불필요)

```python
# to_analysis_context()에서 기존 데이터로 파생

# 정신건강 적응증
is_mental_health = therapeutic_area.value in ["Psychiatry", "Neurology", "CNS"]
mental_health_type = extract_mental_health_type(indication.value)

# 신청 유형
is_supplement = approval_type.value in ["snda", "sbla"]

# CRL 세부 정보 (crl_reason_type에서 파생)
is_cmc_only = crl_reason_type.value == "cmc" if has_prior_crl else False
# resubmission_class는 별도 웹서치로 확인, 없으면 기본값

# RWE/외부 대조군 (is_single_arm에 포함)
# is_single_arm = True이면 RWE/external control 가능성 내포
```

### 9.5 StatusField Pydantic v2 수정

```python
from pydantic import computed_field

class StatusField(BaseModel, Generic[T]):
    # 기존 필드 유지...

    @computed_field
    @property
    def has_value(self) -> bool:
        return self.status == SearchStatus.FOUND and self.value is not None

    @computed_field
    @property
    def needs_retry(self) -> bool:
        return self.status in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @computed_field
    @property
    def is_complete(self) -> bool:
        return self.status in (SearchStatus.FOUND, SearchStatus.CONFIRMED_NONE, SearchStatus.NOT_APPLICABLE)
```

### 9.6 마이그레이션 스크립트 수정

```python
# 기존 데이터 변환 + 신규 12개 필드 초기화

# 1. adcom_info.vote → vote_ratio
vote_raw = adcom_old.get("vote")
if isinstance(vote_raw, dict):
    total = vote_raw.get("for", 0) + vote_raw.get("against", 0)
    vote_ratio = vote_raw["for"] / total if total > 0 else None

# 2. mechanism_of_action 문자열 → StatusField
if isinstance(moa_old, str):
    mechanism_of_action = StatusField.found(moa_old, "legacy_migration")

# 3. 신규 12개 필드 = not_searched 초기화
NEW_FIELDS = [
    "is_single_arm", "trial_region", "is_biosimilar", "is_first_in_class",
    "crl_reason_type", "warning_letter_date", "fda_483_date",
    "fda_483_observations", "cdmo_name", "pai_passed", "pai_date",
    "clinical_hold_history"
]
for field in NEW_FIELDS:
    data[field] = StatusField.not_searched()
```

### 9.7 검색 실패 시 폴백

```python
# 분석 시 검색 실패 처리
class AnalysisRunner:
    async def analyze(self, event: PDUFAEvent) -> AnalysisResult:
        # 제조 정보 검색 시도
        manufacturing = await self.searcher.search_manufacturing(event)

        # 실패 시 보수적 기본값 + 경고
        if not manufacturing.warning_letter_date.has_value:
            manufacturing.warning_letter_date = StatusField.not_found(["search_failed"])
            warnings.append("Warning letter 정보 검색 실패 - 기본값(없음) 사용")

        # 결과에 경고 포함
        return AnalysisResult(
            probability=prob,
            warnings=warnings,
            data_quality=self.assess_quality(event, manufacturing)
        )
```

### 9.8 최종 필드 수

| 카테고리 | 기존 | 추가 | 합계 |
|----------|------|------|------|
| 사전 수집 | 37 | 5 | 42 |
| 캐시 + 갱신 | 0 | 4 | 4 |
| 분석 시 검색 | 0 | 3 | 3 |
| **총계** | **37** | **12** | **49** |

### 9.9 알고리즘 수정 사항 (4명 페르소나 토론 결과)

#### 9.9.1 제거할 팩터

```python
# clinical.py - rwe_external_control 팩터 제거
# 이유: is_single_arm과 상관계수 0.85+, 중복 정보
# 대안: is_single_arm 패널티를 약간 증가 (-5% → -7%)

@FactorRegistry.register(name="rwe_external_control", ...)
def apply_rwe_external_control_penalty(...):
    # DEPRECATED: is_single_arm에 통합
    return FactorResult.neutral("rwe_external_control", "is_single_arm에 통합됨")


# manufacturing.py - cdmo_high_risk 팩터 제거
# 이유: CDMO 리스크 목록 유지 비용 대비 효과 낮음
# 대안: warning_letter가 CDMO 문제도 반영함

@FactorRegistry.register(name="cdmo_high_risk", ...)
def apply_cdmo_risk_penalty(...):
    # DEPRECATED: warning_letter로 대체
    return FactorResult.neutral("cdmo_high_risk", "warning_letter로 대체")
```

#### 9.9.2 수정할 팩터

```python
# clinical.py - single_arm 패널티 조정
# 변경: RWE/external control 포함하여 패널티 증가

SINGLE_ARM_PENALTY = -0.07  # 기존 -0.05에서 증가

@FactorRegistry.register(name="single_arm_trial", ...)
def apply_single_arm_penalty(ctx, current_prob):
    if not ctx.clinical.is_single_arm:
        return FactorResult.neutral("single_arm_trial")

    # RWE/external control 고려한 통합 패널티
    return FactorResult.penalty(
        name="single_arm_trial",
        value=SINGLE_ARM_PENALTY,
        reason=f"단일군/외부대조군 시험 ({SINGLE_ARM_PENALTY:.0%})",
    )
```

#### 9.9.3 Base Rate 파생 로직

```python
# base.py - crl_reason_type에서 파생

def get_resubmission_base_rate(ctx: AnalysisContext) -> float:
    """CRL 사유 기반 재제출 기본률 결정."""

    if not ctx.is_resubmission:
        return None

    crl_reason = ctx.crl_reason_type  # "cmc" | "efficacy" | "safety" | "labeling" | "unknown"

    # CMC 문제는 재승인율 높음
    if crl_reason == "cmc":
        return 0.82  # Class 1 CMC 재제출 기본률

    # 효능/안전성 문제는 재승인율 낮음
    elif crl_reason in ("efficacy", "safety"):
        return 0.45  # Class 2 재제출 기본률

    # 라벨링은 중간
    elif crl_reason == "labeling":
        return 0.70

    # 알 수 없으면 보수적 기본값
    else:
        return 0.55
```

#### 9.9.4 팩터 우선순위 정리

| 팩터 | 레이어 | 영향도 | 데이터 가용성 | 유지 |
|------|--------|--------|--------------|------|
| primary_endpoint_not_met | clinical | 치명적 | ✅ 높음 | ✅ |
| single_arm_trial | clinical | 높음 | ✅ 높음 | ✅ (RWE 포함) |
| trial_region_china_only | clinical | 높음 | ✅ 높음 | ✅ |
| clinical_hold_history | clinical | 중간 | △ 중간 | ✅ |
| warning_letter | manufacturing | 높음 | ✅ 높음 | ✅ |
| fda_483_observations | manufacturing | 중간 | △ 중간 | ✅ |
| pai_passed | manufacturing | 높음 | △ 낮음 | ✅ (조건부) |
| rwe_external_control | clinical | 중간 | ❌ 낮음 | ❌ 제거 |
| cdmo_high_risk | manufacturing | 낮음 | ❌ 낮음 | ❌ 제거 |

---

## 10. 관련 문서

- M3_BLUEPRINT_v3.md - 전체 아키텍처
- 이 문서가 스키마 상세 설계
- DATA_COLLECTION_DESIGN.md - 수집 파이프라인
