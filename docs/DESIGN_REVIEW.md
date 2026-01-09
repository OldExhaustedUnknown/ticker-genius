# 설계 종합 검토

**작성일**: 2026-01-09
**목적**: M3_BLUEPRINT_v2.md, SEARCH_IMPROVEMENT_DESIGN.md, 스키마 일관성 검토
**상태**: 액션 아이템 대부분 완료
**최종 수정**: 2026-01-09

---

## 1. 문서 간 충돌 발견

### 1.1 "추론" 관련 충돌

| 문서 | 내용 | 문제 |
|------|------|------|
| M3_BLUEPRINT_v2.md | Phase 2: "과거 CRL 날짜 **추론** 로직" | **추론 금지 원칙 위반** |
| SEARCH_IMPROVEMENT | "추론 금지: 절대 추측/역산/가정하지 않음" | 올바름 |

**수정 필요**: M3_BLUEPRINT_v2.md Phase 2에서 "추론"을 "웹서치/검색"으로 변경

### 1.2 빈 필드 상태 용어 불일치

| M3_BLUEPRINT_v2 | SEARCH_IMPROVEMENT | 의미 |
|-----------------|-------------------|------|
| `verified/legacy` | `found` | 값 있음 |
| `not_found` | `not_found` | 못 찾음 (재시도 필요) |
| `not_applicable` | ❌ 없음 | 해당 안됨 |
| ❌ 없음 | `confirmed_none` | 확인 결과 없음 |
| ❌ 없음 | `not_searched` | 검색 안함 |

**문제**: 두 문서의 상태 정의가 다름

### 1.3 스키마 불일치

| 위치 | M3_BLUEPRINT_v2 정의 | 실제 event_models.py |
|------|---------------------|---------------------|
| btd | `Optional[FieldValue]` | `Optional[bool]` |
| priority_review | `Optional[FieldValue]` | `Optional[bool]` |
| 기타 FDA 지정 | `Optional[FieldValue]` | `Optional[bool]` |

**문제**: 청사진과 실제 코드가 다름

---

## 2. 통합 상태 정의 (제안)

### 5가지 상태로 통합

```python
class SearchStatus(str, Enum):
    """검색 상태 (통합 정의)."""

    # 값이 있는 상태
    FOUND = "found"
    # 값: 검색해서 찾은 데이터
    # 재시도: 불필요
    # 예: btd=True (FDA 공식 목록에서 확인)

    # 값이 없음이 확인된 상태
    CONFIRMED_NONE = "confirmed_none"
    # 값: False 또는 None (명시적으로 없음)
    # 재시도: 불필요
    # 예: btd=False (FDA 공식 목록에서 해당 약물 없음 확인)

    # 해당 필드가 적용되지 않는 상태
    NOT_APPLICABLE = "not_applicable"
    # 값: None
    # 재시도: 불필요
    # 예: adcom_vote_ratio (AdCom을 열지 않은 경우)

    # 검색했지만 못 찾은 상태
    NOT_FOUND = "not_found"
    # 값: None
    # 재시도: **필요** (다른 소스에서)
    # 예: SEC에서 못 찾음 → 웹서치 시도 필요

    # 아직 검색하지 않은 상태
    NOT_SEARCHED = "not_searched"
    # 값: None
    # 재시도: **필요**
    # 예: 초기 상태
```

### 상태 간 관계

```
                    ┌─────────────────┐
                    │  NOT_SEARCHED   │ (초기 상태)
                    └────────┬────────┘
                             │
                      검색 실행
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌──────────────┐
        │  FOUND   │  │ NOT_FOUND │  │ NOT_APPLICABLE│
        └──────────┘  └─────┬─────┘  └──────────────┘
                            │
                     다른 소스에서 재시도
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌───────────────┐  (계속 NOT_FOUND)
        │  FOUND   │  │ CONFIRMED_NONE│
        └──────────┘  └───────────────┘
```

### 상태별 판단 기준

| 상태 | 언제 사용? | 예시 |
|------|-----------|------|
| `FOUND` | Tier 1-2 소스에서 값 확인 | FDA DB에서 BTD=True 확인 |
| `CONFIRMED_NONE` | Tier 1 소스에서 "없음" 확인 | FDA 공식 목록에 없음 |
| `NOT_APPLICABLE` | 필드 자체가 해당 케이스에 무관 | original submission인데 prior_crl_reason |
| `NOT_FOUND` | 검색했지만 찾지 못함, 다른 소스 가능 | SEC에서 못 찾음, 뉴스에서 찾을 수 있음 |
| `NOT_SEARCHED` | 아직 검색 시도 안함 | 초기 상태 |

---

## 3. 스키마 통합 제안

### 3.1 통합 FieldValue

```python
@dataclass
class FieldValue:
    """검색 상태를 포함한 필드 값."""

    # 핵심 필드
    value: Any                                      # 실제 값
    status: SearchStatus = SearchStatus.NOT_SEARCHED  # 검색 상태

    # 출처 추적
    sources: list[SourceInfo] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)

    # 메타데이터
    confidence: float = 1.0
    last_searched: Optional[datetime] = None
    needs_manual_review: bool = False
    conflicts: list[str] = field(default_factory=list)

    @property
    def needs_retry(self) -> bool:
        """재시도 필요 여부."""
        return self.status in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @property
    def is_complete(self) -> bool:
        """검색 완료 여부 (값 있든 없든)."""
        return self.status in (
            SearchStatus.FOUND,
            SearchStatus.CONFIRMED_NONE,
            SearchStatus.NOT_APPLICABLE
        )
```

### 3.2 PDUFAEvent 스키마 수정

```python
@dataclass
class PDUFAEvent:
    """단일 PDUFA 이벤트."""

    # === 식별자 (필수, 단순 타입) ===
    ticker: str
    drug_name: str
    pdufa_date: str  # YYYYMMDD
    event_id: str = ""

    # === 타겟 변수 ===
    result: Optional[str] = None  # "approved", "crl", "pending"

    # === 제출 컨텍스트 ===
    sequence_number: int = 1
    submission_type: str = "original"
    prior_crl_reason: Optional[str] = None

    # === Feature 필드 (FieldValue로 변경) ===
    # FDA 지정
    btd: Optional[FieldValue] = None
    priority_review: Optional[FieldValue] = None
    fast_track: Optional[FieldValue] = None
    orphan_drug: Optional[FieldValue] = None
    accelerated_approval: Optional[FieldValue] = None

    # 임상
    primary_endpoint_met: Optional[FieldValue] = None
    phase: Optional[FieldValue] = None
    nct_id: Optional[FieldValue] = None

    # AdCom
    adcom_held: Optional[FieldValue] = None
    adcom_date: Optional[FieldValue] = None
    adcom_vote_ratio: Optional[FieldValue] = None

    # 제조
    pai_passed: Optional[FieldValue] = None
    warning_letter_active: Optional[FieldValue] = None

    # === 메타데이터 ===
    source_case_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    data_quality_score: float = 0.0

    def get_fields_needing_retry(self) -> list[str]:
        """재시도 필요한 필드 목록."""
        fields_to_check = [
            ('btd', self.btd),
            ('priority_review', self.priority_review),
            ('fast_track', self.fast_track),
            ('orphan_drug', self.orphan_drug),
            ('accelerated_approval', self.accelerated_approval),
            ('primary_endpoint_met', self.primary_endpoint_met),
            ('phase', self.phase),
            ('nct_id', self.nct_id),
            ('adcom_held', self.adcom_held),
            ('adcom_date', self.adcom_date),
            ('adcom_vote_ratio', self.adcom_vote_ratio),
            ('pai_passed', self.pai_passed),
            ('warning_letter_active', self.warning_letter_active),
        ]
        return [name for name, fv in fields_to_check if fv and fv.needs_retry]

    def get_completion_rate(self) -> float:
        """검색 완료율."""
        fields = [
            self.btd, self.priority_review, self.fast_track,
            self.orphan_drug, self.accelerated_approval,
            self.primary_endpoint_met, self.adcom_held,
        ]
        completed = sum(1 for f in fields if f and f.is_complete)
        return completed / len(fields) if fields else 0.0
```

---

## 4. M3_BLUEPRINT_v2 수정 필요 사항

### 4.1 Phase 2 수정

**현재**:
```
Phase 2: 이벤트 추출기
작업:
...
3. 과거 CRL 날짜 추론 로직
```

**수정**:
```
Phase 2: 이벤트 추출기
작업:
...
3. 과거 CRL 날짜 검색 로직 (SEC → 웹서치 → 뉴스)
   주의: 추론 금지. 검색으로 못 찾으면 NOT_FOUND로 기록
```

### 4.2 빈 필드 원칙 수정

**현재**:
```
모든 필드는 다음 중 하나의 상태를 가져야 함:
1. 값이 있음 (verified/legacy)
2. 검색했으나 없음 (not_found)
3. 해당 없음 (not_applicable)
```

**수정**:
```
모든 필드는 다음 중 하나의 상태를 가져야 함:
1. FOUND - 값 있음 (출처 포함)
2. CONFIRMED_NONE - 공식 소스에서 없음 확인
3. NOT_APPLICABLE - 해당 케이스에 적용 안됨
4. NOT_FOUND - 검색했지만 못 찾음 (재시도 필요)
5. NOT_SEARCHED - 아직 검색 안함 (재시도 필요)

금지:
- NOT_FOUND/NOT_SEARCHED 상태로 장기 방치
- 추론으로 값 채우기
```

### 4.3 스키마 정의 수정

청사진의 PDUFAEvent 정의를 위 3.2의 통합 스키마로 교체

---

## 5. 액션 아이템

### 즉시 (문서)
- [x] M3_BLUEPRINT_v2.md Phase 2 "추론" → "검색" 수정 ✅
- [x] M3_BLUEPRINT_v2.md 빈 필드 원칙 5가지 상태로 수정 ✅
- [ ] M3_BLUEPRINT_v2.md 스키마를 FieldValue 포함하도록 수정 (PDUFAEvent는 search_metadata dict 방식 채택)
- [x] SEARCH_IMPROVEMENT_DESIGN.md에 NOT_APPLICABLE 추가 ✅

### 다음 (코드)
- [x] models.py에 SearchStatus enum 추가 ✅
- [x] models.py FieldValue에 status 필드 추가 ✅
- [x] event_models.py PDUFAEvent.search_metadata 필드 추가 ✅
- [ ] 기존 데이터 마이그레이션 스크립트 작성 (필요 시)

### 신규 완료 (검색 시스템)
- [x] search_utils.py 생성 (SearchQueryBuilder, SearchResultValidator) ✅
- [x] web_search.py 생성 (WebSearchClient) ✅
- [x] search_chain.py 생성 (SearchChainOrchestrator) ✅

---

## 6. 최종 문서 관계

```
M3_BLUEPRINT_v2.md (메인 청사진)
├── 예측 단위: PDUFA 이벤트
├── 데이터 모델: PDUFAEvent
├── 검색 상태: 5가지 (FOUND, CONFIRMED_NONE, NOT_APPLICABLE, NOT_FOUND, NOT_SEARCHED)
└── 추론 금지 원칙

SEARCH_IMPROVEMENT_DESIGN.md (검색 시스템)
├── 검색 체인: SEC → FDA → 뉴스 → 웹서치
├── 폴백 전략: API 실패 시 웹서치
├── 검색 상태와 연동
└── 웹서치 클라이언트 설계

models.py / event_models.py (스키마)
├── SearchStatus enum
├── FieldValue (status 포함)
└── PDUFAEvent (FieldValue 타입 필드)
```
