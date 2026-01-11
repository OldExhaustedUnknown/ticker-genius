# M3 Blueprint v3: 통합 아키텍처 재설계

**작성일**: 2026-01-10
**버전**: 3.0
**상태**: ✅ 구현 완료 (2026-01-11)
**이전 버전**: M3_BLUEPRINT_v2.md (SUPERSEDED)

---

## 1. 프로젝트 목적

### 핵심 목표
1. **FDA PDUFA 승인 확률 예측**: P(Approval) 계산
2. **CRL 발생 확률 예측**: P(CRL) 계산 (리스크 판단)
3. **거래 신호 생성**: 제약 주식 투자 의사결정 지원
4. **MCP 도구 제공**: Claude와 연동하여 실시간 분석

### 핵심 원칙 (CLAUDE.md 준수)
```
1. 추론 금지: 데이터가 없으면 없다고 기록. 절대 추측/역산/가정하지 않음
2. 포기 금지: API 실패해도 웹서치로 찾아야 함
3. 검증된 데이터만: 출처가 명확한 데이터만 저장
4. "못 찾음" vs "없음" 구분: SearchStatus로 명확히 기록
```

---

## 2. 사용자 결정 사항

| 항목 | 결정 | 일시 |
|------|------|------|
| 데이터 단위 | 하이브리드 (enriched 유지 + 이벤트 뷰 추가) | 2026-01-10 |
| 예측 목표 | P(CRL) + P(Approval) 둘 다 | 2026-01-10 |
| MCP 개발 | 병행 개발 | 2026-01-10 |

---

## 3. 현재 상태 분석

### 3.1 발견된 문제점

| # | 문제 | 심각도 | 상태 |
|---|------|--------|------|
| 1 | 스키마 삼중 분리 (Pipeline, CollectedCase, PDUFAEvent) | 🔴 Critical | ✅ 해결 (from_enriched) |
| 2 | 파이프라인 단절 (enriched → AnalysisContext 변환 없음) | 🔴 Critical | ✅ 해결 (EventLoader) |
| 3 | 미사용 코드 (DataEnricher, EventStore 등) | 🟠 High | ✅ 정리 완료 |
| 4 | 스크립트 난립 (66개 중 45개 일회성) | 🟠 High | ✅ 아카이브 완료 |
| 5 | 문서 불일치 (STATUS.md 등) | 🟡 Medium | ✅ 업데이트 완료 |

### 3.2 현재 데이터 현황

```
data/enriched/*.json: 523건
- 필드 완성률: 72-100%
- StatusField 패턴 사용: 부분적 (일부 필드만)
- 스키마: 어떤 Pydantic/dataclass와도 불일치
```

### 3.3 현재 분석 시스템

```
analysis/pdufa/: 12개 레이어, 60+ 팩터
- 레이어 시스템: 잘 구현됨
- 입력: AnalysisContext (frozen dataclass)
- 출력: AnalysisResult
- 문제: enriched 데이터 → AnalysisContext 변환 없음
```

---

## 4. 목표 아키텍처

### 4.1 스키마 통합

```
[현재]                           [목표]
─────────────────────────────────────────────────────────
schemas/pipeline.py              → DEPRECATED (유지)
  Pipeline
  PDUFAEvent (5필드)

collection/models.py             → 유지 (수집용)
  CollectedCase
  FieldValue

collection/event_models.py       → 삭제
  PDUFAEvent (24필드)

analysis/_context.py             → 유지 + from_enriched() 추가
  AnalysisContext

[신규]
schemas/enriched.py              ← 실제 데이터 구조 반영
  EnrichedEvent
  StatusField[T]
  FDADesignations
  AdComInfo
  Enrollment
```

### 4.2 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           데이터 흐름                                    │
└─────────────────────────────────────────────────────────────────────────┘

[수집]
collector.py → collected/*.json → run_enrichment.py → enriched/*.json
                                                            │
[분석]                                                      ▼
                                                    EnrichedEvent.parse()
                                                            │
                                                            ▼
                                                    .to_analysis_context()
                                                            │
                                                            ▼
                                                    AnalysisContext
                                                            │
                                                            ▼
                                                    PDUFAAnalyzer.analyze()
                                                            │
                                                            ▼
                                                    AnalysisResult
                                                            │
                                                            ▼
                                                    enriched/*.json 업데이트
                                                    (analysis_result 필드)

[MCP]
MCP Server ← analyze_pdufa() ← AnalysisRunner
          ← get_trading_signals()
          ← get_pdufa_calendar()
```

### 4.3 목표 파일 구조

```
src/tickergenius/
├── schemas/
│   ├── enriched.py           ← [신규] 단일 진실 소스
│   ├── pipeline.py           ← [DEPRECATED]
│   ├── clinical.py
│   ├── manufacturing.py
│   ├── enums.py
│   └── base.py
│
├── analysis/
│   ├── runner.py             ← [신규] 분석 진입점
│   └── pdufa/                ← [유지]
│       ├── _analyzer.py
│       ├── _context.py       ← [수정] from_enriched() 추가
│       ├── _result.py
│       ├── _registry.py
│       └── _layers/
│
├── views/                    ← [신규]
│   └── event_view.py
│
├── mcp/                      ← [신규]
│   ├── server.py
│   └── tools/
│
├── collection/               ← [정리]
│   ├── api_clients.py
│   ├── collector.py
│   ├── models.py
│   ├── web_search.py
│   ├── search_chain.py
│   ├── fallback_chain.py
│   ├── batch_processor.py
│   ├── checkpoint.py
│   └── enrichment/
│
├── core/
└── repositories/

scripts/
├── run_enrichment.py
├── run_analysis.py           ← [신규]
├── enrich_with_ddg.py
└── archive/                  ← [신규] 일회성 스크립트

docs/
├── README.md                 ← [신규] 문서 가이드
├── M3_BLUEPRINT_v3.md        ← 이 문서
└── archive/                  ← [신규] 구 문서
```

---

## 5. 상세 스키마 설계

### 5.1 EnrichedEvent (단일 진실 소스)

```python
# src/tickergenius/schemas/enriched.py

from __future__ import annotations
from datetime import datetime
from typing import Optional, Generic, TypeVar, Union
from enum import Enum
from pydantic import BaseModel, Field

T = TypeVar("T")

class SearchStatus(str, Enum):
    """5가지 검색 상태."""
    FOUND = "found"
    CONFIRMED_NONE = "confirmed_none"
    NOT_APPLICABLE = "not_applicable"
    NOT_FOUND = "not_found"
    NOT_SEARCHED = "not_searched"

    @property
    def needs_retry(self) -> bool:
        return self in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @property
    def is_complete(self) -> bool:
        return self in (
            SearchStatus.FOUND,
            SearchStatus.CONFIRMED_NONE,
            SearchStatus.NOT_APPLICABLE,
        )

class StatusField(BaseModel, Generic[T]):
    """모든 검색 필드의 표준 래퍼."""
    status: SearchStatus
    value: Optional[T] = None
    source: Optional[str] = None
    confidence: float = 0.0
    tier: Optional[int] = None
    evidence: list[str] = Field(default_factory=list)
    searched_sources: list[str] = Field(default_factory=list)
    last_searched: Optional[datetime] = None
    error: Optional[str] = None
    note: Optional[str] = None

    @property
    def has_value(self) -> bool:
        return self.status == SearchStatus.FOUND and self.value is not None

class FDADesignations(BaseModel):
    """FDA 지정 정보."""
    breakthrough_therapy: bool = False
    fast_track: bool = False
    priority_review: bool = False
    orphan_drug: bool = False
    accelerated_approval: bool = False

    def count(self) -> int:
        return sum([
            self.breakthrough_therapy,
            self.fast_track,
            self.priority_review,
            self.orphan_drug,
            self.accelerated_approval,
        ])

    def has_any(self) -> bool:
        return self.count() > 0

class AdComInfo(BaseModel):
    """Advisory Committee 정보."""
    scheduled: bool = False
    held: bool = False
    outcome: Optional[str] = None
    vote: Optional[str] = None
    vote_ratio: Optional[float] = None

class Enrollment(BaseModel):
    """임상 등록 정보."""
    count: Optional[int] = None
    type: Optional[str] = None
    nct_id: Optional[str] = None
    source: Optional[str] = None
    fetched_at: Optional[datetime] = None

class AnalysisResultField(BaseModel):
    """분석 결과 필드."""
    p_crl: float
    p_approval: float
    confidence_score: float
    risk_level: str
    top_factors: list[dict] = Field(default_factory=list)
    analyzed_at: Optional[datetime] = None
    analysis_version: str = "3.0"

class EnrichedEvent(BaseModel):
    """
    Enriched PDUFA 이벤트 - 단일 진실 소스.

    data/enriched/*.json의 실제 구조를 정확히 반영.
    """
    # 식별자
    event_id: str
    ticker: str
    company_name: str
    drug_name: str
    original_case_id: Optional[str] = None

    # PDUFA 정보
    pdufa_date: str
    result: str
    days_to_pdufa: Optional[int] = None
    pdufa_status: Optional[str] = None
    risk_tier: Optional[str] = None

    # StatusField 패턴 필드
    approval_type: StatusField[str]
    indication: StatusField[str]
    generic_name: StatusField[str]
    therapeutic_area: StatusField[str]
    phase: StatusField[str]
    primary_endpoint_met: StatusField[bool]
    p_value: StatusField[str]
    effect_size: StatusField[str]
    safety_signal: StatusField[bool]
    has_prior_crl: StatusField[bool]
    prior_crl_reason: Optional[StatusField[str]] = None
    is_resubmission: StatusField[Union[int, bool]]
    pai_passed: StatusField[bool]
    warning_letter: StatusField[bool]

    # 직접 값 필드
    phase3_study_names: list[str] = Field(default_factory=list)
    nct_ids: list[str] = Field(default_factory=list)
    p_value_numeric: Optional[float] = None
    mechanism_of_action: Optional[str] = None

    # 중첩 객체 필드
    fda_designations: FDADesignations = Field(default_factory=FDADesignations)
    adcom_info: AdComInfo = Field(default_factory=AdComInfo)
    enrollment: Optional[Enrollment] = None

    # 분석 결과 (분석 후 추가)
    analysis_result: Optional[AnalysisResultField] = None

    # 메타데이터
    data_quality_score: float = 0.0
    collected_at: Optional[datetime] = None
    enriched_at: Optional[datetime] = None
    days_calculated_at: Optional[datetime] = None
    needs_manual_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    # 변환 메서드
    def to_analysis_context(self) -> "AnalysisContext":
        """EnrichedEvent → AnalysisContext 변환."""
        from tickergenius.analysis.pdufa._context import (
            AnalysisContext,
            FDADesignations as CtxFDADesignations,
            AdComInfo as CtxAdComInfo,
            ClinicalInfo,
            ManufacturingInfo,
        )
        from tickergenius.schemas.enums import ApprovalType

        # FDA 지정 변환
        fda_designations = CtxFDADesignations(
            breakthrough_therapy=self.fda_designations.breakthrough_therapy,
            priority_review=self.fda_designations.priority_review,
            fast_track=self.fda_designations.fast_track,
            orphan_drug=self.fda_designations.orphan_drug,
            accelerated_approval=self.fda_designations.accelerated_approval,
        )

        # AdCom 변환
        adcom = CtxAdComInfo(
            was_held=self.adcom_info.held,
            vote_ratio=self.adcom_info.vote_ratio,
            outcome=self.adcom_info.outcome,
        )

        # 임상 정보 변환
        clinical = ClinicalInfo(
            phase=self.phase.value or "phase3",
            primary_endpoint_met=self.primary_endpoint_met.value,
            nct_id=self.nct_ids[0] if self.nct_ids else None,
        )

        # 제조 정보 변환
        manufacturing = ManufacturingInfo(
            pai_passed=self.pai_passed.value or False,
            has_warning_letter=self.warning_letter.value or False,
        )

        # 날짜 파싱
        pdufa_date = self._parse_pdufa_date()

        # is_resubmission 정규화
        is_resub = self.is_resubmission.value
        if isinstance(is_resub, int):
            is_resub = bool(is_resub)

        return AnalysisContext(
            ticker=self.ticker,
            drug_name=self.drug_name,
            pdufa_date=pdufa_date,
            days_to_pdufa=self.days_to_pdufa,
            is_resubmission=is_resub or False,
            fda_designations=fda_designations,
            adcom=adcom,
            clinical=clinical,
            manufacturing=manufacturing,
        )

    def _parse_pdufa_date(self):
        """PDUFA 날짜 파싱 (다양한 형식 지원)."""
        from datetime import date

        if not self.pdufa_date:
            return None

        # YYYYMMDD 형식
        if len(self.pdufa_date) == 8 and self.pdufa_date.isdigit():
            return date(
                int(self.pdufa_date[:4]),
                int(self.pdufa_date[4:6]),
                int(self.pdufa_date[6:8]),
            )

        # ISO 형식
        try:
            return date.fromisoformat(self.pdufa_date[:10])
        except ValueError:
            return None

    @classmethod
    def parse_file(cls, file_path) -> "EnrichedEvent":
        """JSON 파일에서 파싱."""
        import json
        from pathlib import Path

        with open(Path(file_path), "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)

    def save(self, file_path):
        """JSON 파일로 저장."""
        import json
        from pathlib import Path

        with open(Path(file_path), "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
```

---

## 6. 구현 계획

### Wave 1: 스키마 통합 (즉시)

| Task | 파일 | 내용 | 상태 |
|------|------|------|------|
| 1.1 | `schemas/enriched.py` | EnrichedEvent 스키마 정의 | ⏳ |
| 1.2 | `schemas/enriched.py` | StatusField[T] 제네릭 | ⏳ |
| 1.3 | `analysis/_context.py` | `from_enriched()` 메서드 추가 | ⏳ |
| 1.4 | `tests/` | enriched 파일 파싱 검증 | ⏳ |

**완료 조건**:
- [ ] EnrichedEvent.parse_file() 동작
- [ ] 523개 파일 모두 파싱 성공
- [ ] AnalysisContext.from_enriched() 동작

### Wave 2: 파이프라인 연결 (단기)

| Task | 파일 | 내용 | 상태 |
|------|------|------|------|
| 2.1 | `analysis/runner.py` | AnalysisRunner 클래스 | ⏳ |
| 2.2 | `analysis/runner.py` | 배치 분석 지원 | ⏳ |
| 2.3 | `analysis/runner.py` | 결과 저장 (enriched 업데이트) | ⏳ |
| 2.4 | `scripts/run_analysis.py` | CLI 진입점 | ⏳ |

**완료 조건**:
- [ ] AnalysisRunner.analyze_enriched_file() 동작
- [ ] 523개 파일 분석 성공
- [ ] 분석 결과 enriched 파일에 저장

### Wave 3: MCP 도구 (중기)

| Task | 파일 | 내용 | 상태 |
|------|------|------|------|
| 3.1 | `mcp/__init__.py` | 모듈 초기화 | ⏳ |
| 3.2 | `mcp/server.py` | MCP 서버 기본 구조 | ⏳ |
| 3.3 | `mcp/tools/analyze.py` | analyze_pdufa 도구 | ⏳ |
| 3.4 | `mcp/tools/data.py` | get_drug_info, get_pdufa_calendar | ⏳ |
| 3.5 | `mcp/tools/trading.py` | get_trading_signals | ⏳ |

**완료 조건**:
- [ ] MCP 서버 시작
- [ ] Claude와 연동 테스트

### Wave 4: 정리 (지속)

| Task | 대상 | 내용 | 상태 |
|------|------|------|------|
| 4.1 | `collection/` | 미사용 코드 삭제 | ⏳ |
| 4.2 | `scripts/` | 일회성 스크립트 → archive/ | ⏳ |
| 4.3 | `docs/` | 문서 업데이트 | ⏳ |
| 4.4 | `schemas/pipeline.py` | DEPRECATED 표시 | ⏳ |

---

## 7. MCP 도구 상세

### 7.1 도구 목록

| 도구 | 우선순위 | 설명 |
|------|---------|------|
| `analyze_pdufa` | P0 | 단일 약물 PDUFA 분석 |
| `get_drug_info` | P0 | 약물 상세 정보 조회 |
| `get_pdufa_calendar` | P1 | PDUFA 캘린더 조회 |
| `get_trading_signals` | P1 | 거래 신호 생성 |
| `analyze_batch` | P2 | 다중 약물 배치 분석 |
| `search_drugs` | P2 | 약물 검색 |

### 7.2 도구 스키마

```yaml
analyze_pdufa:
  input:
    ticker: string (required)
    drug_name: string (optional)
  output:
    probability: float
    p_crl: float
    risk_level: string
    confidence: float
    factors: list[FactorResult]

get_trading_signals:
  input:
    min_probability: float (default: 0.7)
    max_days_to_pdufa: int (default: 30)
  output:
    signals: list[TradingSignal]
```

---

## 8. 삭제/정리 대상

### 8.1 삭제 대상 코드

```
collection/
├── data_enricher.py           ← 삭제 (미사용)
├── clinical_data_enricher.py  ← 삭제 (미사용)
├── event_store.py             ← 삭제 (migration.py에서만 사용)
├── event_extractor.py         ← 삭제 (migration.py에서만 사용)
└── event_models.py            ← 삭제 (PDUFAEvent 중복)
```

### 8.2 아카이브 대상 스크립트

```
scripts/ → scripts/archive/
├── apply_fda_batch*.py (18개)
├── apply_nct_batch*.py (8개)
├── apply_moa_batch*.py (10개)
├── fix_*.py (5개)
├── derive_*.py (3개)
├── migrate_*.py (2개)
└── 기타 일회성 (10개+)
```

### 8.3 아카이브 대상 문서

```
docs/ → docs/archive/
├── M3_PLAN.md (SUPERSEDED)
├── M3_REVIEW.md (SUPERSEDED)
└── M3_BLUEPRINT_v2.md (SUPERSEDED by v3)
```

---

## 9. 검증 체크리스트

### 전체 완료 조건

```
Wave 1 (스키마):
[ ] EnrichedEvent 523개 파일 파싱 성공
[ ] to_analysis_context() 변환 성공
[ ] 타입 검증 통과

Wave 2 (파이프라인):
[ ] AnalysisRunner 동작
[ ] P(CRL) + P(Approval) 계산
[ ] 결과 저장

Wave 3 (MCP):
[ ] MCP 서버 시작
[ ] 6개 도구 동작
[ ] Claude 연동

Wave 4 (정리):
[ ] 미사용 코드 삭제
[ ] 스크립트 15개 이하
[ ] 문서 최신화
```

---

## 10. 참고

- 이 문서는 5회 페르소나 토론을 거쳐 합의된 내용입니다.
- v2 대비 핵심 변경점: 스키마 통합, 파이프라인 연결, MCP 병행 개발
- 이전 문서들(M3_PLAN.md, M3_REVIEW.md, M3_BLUEPRINT_v2.md)은 SUPERSEDED 상태입니다.
