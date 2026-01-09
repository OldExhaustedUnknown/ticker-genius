# 검색 시스템 개선 설계

**작성일**: 2026-01-09
**상태**: Phase 1-2 구현 완료
**최종 수정**: 2026-01-09

---

## 구현 상태

| Phase | 상태 | 파일 |
|-------|------|------|
| Phase 1: 기반 구조 | ✅ 완료 | `search_utils.py`, `models.py` |
| Phase 2: 웹서치 구현 | ✅ 완료 | `web_search.py`, `search_chain.py` |
| Phase 3: 기존 클라이언트 개선 | 🔄 일부 | `api_clients.py` (DesignationSearchClient) |
| Phase 4: 통합 및 검증 | ⏳ 대기 | - |

---

## 핵심 원칙

### 절대 금지
1. **추론 금지**: 데이터가 없으면 없다고 기록. 절대 추측/역산/가정하지 않음
2. **포기 금지**: API 실패해도 웹서치로 찾아야 함

### 필수 원칙
1. **다중 폴백**: API → 웹서치 → FDA 공식 → 뉴스 검색
2. **검증된 데이터만**: 출처가 명확한 데이터만 저장
3. **단일 책임**: 각 클라이언트는 하나의 소스만 담당
4. **"못 찾음" vs "없음" 구분**: 검색 상태 명확히 기록

---

## 검색 상태 정의

### 상태 구분 (중요)

| 상태 | 의미 | 재시도 | 예시 |
|------|------|--------|------|
| `found` | 검색해서 찾음 | 불필요 | CRL 날짜 발견 |
| `confirmed_none` | 확인 결과 없음 | 불필요 | FDA DB에서 CRL 이력 없음 확인 |
| `not_applicable` | 해당 필드 적용 안됨 | 불필요 | original에서 prior_crl_reason |
| `not_found` | 검색했지만 못 찾음 | **필요** | SEC 검색 실패, 다른 소스 시도해야 함 |
| `not_searched` | 아직 검색 안함 | **필요** | 초기 상태 |

### 상태별 처리

```python
class SearchStatus(str, Enum):
    FOUND = "found"                    # 찾음
    CONFIRMED_NONE = "confirmed_none"  # 확인 결과 없음 (재시도 불필요)
    NOT_APPLICABLE = "not_applicable"  # 해당 안됨 (재시도 불필요)
    NOT_FOUND = "not_found"            # 못 찾음 (재시도 필요)
    NOT_SEARCHED = "not_searched"      # 검색 안함

@dataclass
class SearchResult:
    status: SearchStatus
    value: Optional[Any] = None
    source: Optional[str] = None       # 출처
    searched_sources: list[str] = field(default_factory=list)  # 검색한 소스들
    timestamp: str = ""                # 검색 시간
```

### "없음" 확인 기준

**CRL 이력**:
- `confirmed_none`: FDA 공식 DB에서 해당 약물 승인 이력만 있고 CRL 없음
- `not_found`: SEC/뉴스 검색 실패 (다른 소스에서 찾을 가능성 있음)

**FDA 지정 (BTD, Orphan 등)**:
- `confirmed_none`: FDA 공식 목록에 없음 확인
- `not_found`: API 오류로 확인 못함

**AdCom**:
- `confirmed_none`: FDA 캘린더에 해당 약물 없음
- `not_found`: 검색 실패

---

## 스키마 개선

### 현재 문제점

```python
# 현재 FieldValue
@dataclass
class FieldValue:
    value: Any              # None이면 뭔지 모름
    sources: list[SourceInfo]
    confidence: float

# 문제: value가 None일 때 아래 중 어떤 상태인지 구분 불가
# 1. 아직 검색 안함
# 2. 검색했지만 못 찾음
# 3. 확인 결과 없음
```

### 개선된 FieldValue

```python
class SearchStatus(str, Enum):
    """검색 상태."""
    FOUND = "found"                    # 값을 찾음
    CONFIRMED_NONE = "confirmed_none"  # 확인 결과 없음 (재시도 불필요)
    NOT_APPLICABLE = "not_applicable"  # 해당 안됨 (재시도 불필요)
    NOT_FOUND = "not_found"            # 검색했지만 못 찾음 (재시도 필요)
    NOT_SEARCHED = "not_searched"      # 아직 검색 안함

@dataclass
class FieldValue:
    """검색 상태를 포함한 필드 값."""
    value: Any
    status: SearchStatus = SearchStatus.NOT_SEARCHED
    sources: list[SourceInfo] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)  # 검색 시도한 소스들
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

### 사용 예시

```python
# 검색 결과가 있는 경우
btd = FieldValue(
    value=True,
    status=SearchStatus.FOUND,
    sources=[SourceInfo(name="fda_btd_list", tier=SourceTier.TIER1)],
    searched_sources=["fda_btd_list", "sec_8k"],
    confidence=0.95
)

# 검색했지만 못 찾은 경우 (재시도 필요)
btd = FieldValue(
    value=None,
    status=SearchStatus.NOT_FOUND,
    searched_sources=["sec_8k", "biospace"],  # 여기서 찾아봤지만 없었음
)

# 확인 결과 없는 경우 (재시도 불필요)
btd = FieldValue(
    value=False,  # 명시적 False
    status=SearchStatus.CONFIRMED_NONE,
    sources=[SourceInfo(name="fda_btd_list", tier=SourceTier.TIER1)],  # 공식 DB에서 확인
    searched_sources=["fda_btd_list"],
)

# 아직 검색 안한 경우
btd = FieldValue(
    value=None,
    status=SearchStatus.NOT_SEARCHED,
)

# 해당 안되는 경우 (예: original submission에서 prior_crl_reason)
prior_crl_reason = FieldValue(
    value=None,
    status=SearchStatus.NOT_APPLICABLE,
)
```

### PDUFAEvent 메타데이터 추가

```python
@dataclass
class PDUFAEvent:
    # ... 기존 필드들 ...

    # === 검색 메타데이터 ===
    search_metadata: dict = field(default_factory=dict)
    # 예: {
    #   "btd": {"status": "found", "sources": ["fda_btd_list"], "searched": ["fda_btd_list", "sec_8k"]},
    #   "adcom_date": {"status": "not_found", "searched": ["fda_calendar", "sec_8k"]},
    # }

    def get_fields_needing_retry(self) -> list[str]:
        """재시도가 필요한 필드 목록."""
        return [
            field for field, meta in self.search_metadata.items()
            if meta.get("status") in ("not_found", "not_searched")
        ]
```

---

## 현재 문제점

### 1. 검색 실패 시 추론으로 폴백
```python
# 현재 (문제)
if not sec_results:
    estimated_events = self._estimate_crl_events(case)  # 180일 추론
```

### 2. 웹서치 폴백 없음
- SEC 검색 실패 → 포기 또는 추론
- 웹서치로 쉽게 찾을 수 있는 정보도 누락

### 3. 약물명 검색 단순화
```python
# 현재 (문제)
brand_name = drug_name.split()[0]  # "Opdivo Plus" → "Opdivo"만
```

### 4. API 차단 시 대응 부족
- SEC EFTS: 403 차단 → 문서 제목만 필터링 (부정확)
- ClinicalTrials v2: 403 차단 → Classic API (느림)

---

## 페르소나 토론

### 참여자
- **A (Architect)**: 전체 구조, 확장성
- **B (Data Expert)**: 데이터 품질, 검증
- **D (Trading Risk)**: 실사용 신뢰도
- **W (Web Specialist)**: 웹 검색, 스크래핑

---

### 토론 1: 검색 폴백 전략

**A**: 현재 SEC 검색 실패 시 추론으로 폴백하는데, 이건 데이터 오염의 원인이다.

**W**: 웹서치로 폴백하면 된다. CRL 발표는 보통 뉴스에 나오니까.

**B**: 웹서치 결과도 검증이 필요하다. 어떤 소스를 신뢰할 건지 정해야 해.

**D**: 트레이딩에서는 틀린 데이터보다 없는 게 낫다. 웹서치도 신뢰 티어가 있어야 한다.

#### 합의: 검색 체인

```
1. SEC 8-K 본문 검색 (Tier 1)
   ↓ 실패
2. FDA 공식 웹페이지 검색 (Tier 1)
   ↓ 실패
3. 뉴스 웹서치 - BioSpace, FiercePharma, Reuters (Tier 2)
   ↓ 실패
4. 일반 웹서치 (Tier 3)
   ↓ 실패
5. 데이터 없음으로 기록 (절대 추론 안함)
```

---

### 토론 2: 웹서치 클라이언트 설계

**W**: 웹서치는 단순한 HTTP 요청이 아니다. 검색 쿼리 구성, 결과 파싱, 날짜 추출이 필요하다.

**A**: 별도 클라이언트로 분리하자. `WebSearchClient`로.

**B**: 쿼리 템플릿이 중요하다. "ticker drug CRL FDA"로 검색하면 노이즈가 많다.

**W**: 도메인 제한 검색이 효과적이다:
- `site:biospace.com OMER CRL`
- `site:fda.gov OMIDRIA complete response`

#### 합의: WebSearchClient 인터페이스

```python
class WebSearchClient:
    """웹 검색 클라이언트."""

    def search_crl_event(
        self,
        ticker: str,
        drug_name: str,
        before_date: str = None
    ) -> list[dict]:
        """
        CRL 이벤트 검색.

        검색 순서:
        1. site:fda.gov "{drug_name}" "complete response letter"
        2. site:biospace.com "{ticker}" CRL
        3. site:fiercepharma.com "{drug_name}" FDA rejection
        4. 일반 검색 "{ticker} {drug_name} FDA CRL PDUFA"

        Returns:
            [{"date": "20240115", "source": "biospace.com", "url": "...", "confidence": 0.85}]
        """
        pass

    def search_designation(
        self,
        ticker: str,
        drug_name: str,
        designation_type: str  # "btd", "orphan", "priority"
    ) -> Optional[dict]:
        """FDA 지정 정보 검색."""
        pass

    def search_adcom(
        self,
        ticker: str,
        drug_name: str
    ) -> Optional[dict]:
        """AdCom 정보 검색."""
        pass
```

---

### 토론 3: 검색 쿼리 최적화

**B**: 약물명 검색이 너무 단순하다. 다중 변형이 필요하다.

**W**: 검색 쿼리 변형 전략:

```python
def generate_drug_queries(drug_name: str, ticker: str) -> list[str]:
    """약물명 검색 쿼리 변형 생성."""
    queries = []

    # 1. 전체 이름
    queries.append(f'"{drug_name}"')

    # 2. 첫 단어 (브랜드명)
    brand = drug_name.split()[0]
    queries.append(f'"{brand}"')

    # 3. plus/combo 처리
    if " plus " in drug_name.lower():
        base = drug_name.lower().split(" plus ")[0]
        queries.append(f'"{base}"')

    # 4. ticker + 약물 조합
    queries.append(f'{ticker} "{brand}"')

    # 5. 괄호 안 제네릭명 추출
    import re
    generic_match = re.search(r'\(([^)]+)\)', drug_name)
    if generic_match:
        queries.append(f'"{generic_match.group(1)}"')

    return list(dict.fromkeys(queries))  # 중복 제거
```

**A**: 이건 모든 검색 클라이언트에서 공통으로 사용해야 한다. 유틸리티로 분리하자.

#### 합의: 공통 쿼리 생성 유틸리티

```python
# search_utils.py (신규)
class SearchQueryBuilder:
    """검색 쿼리 빌더."""

    @staticmethod
    def drug_name_variants(drug_name: str) -> list[str]:
        """약물명 변형 생성."""
        pass

    @staticmethod
    def build_crl_query(ticker: str, drug_name: str) -> str:
        """CRL 검색 쿼리 생성."""
        pass

    @staticmethod
    def build_designation_query(
        ticker: str,
        drug_name: str,
        designation: str
    ) -> str:
        """FDA 지정 검색 쿼리 생성."""
        pass
```

---

### 토론 4: 검색 결과 검증

**B**: 웹서치 결과는 노이즈가 많다. 검증 로직이 필수.

**D**: False Positive가 치명적이다. 없는 CRL을 있다고 하면 매매 손실.

**W**: 날짜 검증, 약물명 매칭, 출처 신뢰도 체크가 필요하다.

#### 합의: 결과 검증 파이프라인

```python
class SearchResultValidator:
    """검색 결과 검증기."""

    def validate_crl_result(
        self,
        result: dict,
        expected_ticker: str,
        expected_drug: str,
        max_date: str = None
    ) -> ValidationResult:
        """
        CRL 검색 결과 검증.

        검증 항목:
        1. 날짜 형식 유효성
        2. 날짜 범위 (max_date 이전)
        3. 약물명 매칭 (fuzzy matching)
        4. 출처 신뢰도
        5. 중복 체크

        Returns:
            ValidationResult(
                is_valid=True/False,
                confidence=0.0-1.0,
                issues=["약물명 불일치", ...]
            )
        """
        pass
```

---

### 토론 5: SEC 8-K 본문 검색 강화

**A**: EFTS가 403 차단되니까 다른 방법이 필요하다.

**W**: 8-K 문서 직접 다운로드해서 본문 검색하면 된다.

**B**: 모든 8-K를 다운로드하면 너무 느리다. 필터링이 필요하다.

#### 합의: SEC 검색 2단계 전략

```python
class EnhancedSECClient:
    """강화된 SEC 검색 클라이언트."""

    def search_8k_with_content(
        self,
        ticker: str,
        keywords: list[str],
        limit: int = 20
    ) -> list[dict]:
        """
        8-K 본문 포함 검색.

        단계:
        1. Submissions API로 최근 8-K 목록 조회 (빠름)
        2. 제목/날짜로 1차 필터링
        3. 후보 문서 본문 다운로드 (병렬)
        4. 본문 키워드 검색

        최적화:
        - 최대 20개 문서만 다운로드
        - 본문 20KB까지만 읽기
        - 병렬 다운로드 (5개 동시)
        """
        pass
```

---

### 토론 6: AACT DB 우선 사용

**A**: ClinicalTrials API가 불안정하다. AACT DB를 우선 사용하자.

**B**: AACT는 읽기 전용 공개 DB다. Rate limit 없고 안정적이다.

**W**: 단점은 실시간 업데이트가 아니다. 며칠 딜레이 있음.

#### 합의: 임상시험 검색 우선순위

```
1. AACT DB (안정, 구조화)
   ↓ 못 찾으면
2. ClinicalTrials Classic API (느리지만 실시간)
   ↓ 못 찾으면
3. PubMed (NCT ID 추출)
   ↓ 못 찾으면
4. 웹서치 (site:clinicaltrials.gov)
```

---

## 구현 계획

### Phase 1: 기반 구조 (즉시)
1. `search_utils.py` 생성 - 공통 쿼리 빌더
2. `WebSearchClient` 인터페이스 정의
3. `SearchResultValidator` 정의

### Phase 2: 웹서치 구현
1. FDA 공식 페이지 검색
2. 뉴스 사이트 검색 (BioSpace, FiercePharma)
3. 일반 웹서치 폴백

### Phase 3: 기존 클라이언트 개선
1. SEC 8-K 본문 검색 강화
2. AACT DB 우선순위 적용
3. 약물명 다중 변형 검색

### Phase 4: 통합 및 검증
1. 검색 체인 통합
2. 검증 파이프라인 연결
3. 추론 로직 완전 제거

---

## 파일 구조 (구현 완료)

```
src/tickergenius/collection/
├── api_clients.py          # 기존 API 클라이언트 + DesignationSearchClient
├── web_search.py           # ✅ 웹서치 클라이언트 (구현 완료)
├── search_utils.py         # ✅ 공통 유틸리티 (구현 완료)
├── search_chain.py         # ✅ 검색 체인 오케스트레이터 (구현 완료)
├── models.py               # ✅ SearchStatus enum, FieldValue 개선
├── event_models.py         # ✅ PDUFAEvent.search_metadata 추가
├── event_extractor.py      # ✅ 추론 로직 제거, 검색 체인 연동
└── data_enricher.py        # 데이터 보강기 (Phase 3 대상)
```

---

## 구현된 클래스 요약

### search_utils.py
- `SearchQueryBuilder`: 약물명 변형 생성, 검색 쿼리 빌더
- `SearchResultValidator`: 검색 결과 검증, 소스 티어 판정
- `ValidationResult`: 검증 결과 데이터 클래스
- `extract_date_from_text()`: 텍스트에서 날짜 추출

### web_search.py
- `WebSearchClient`: DuckDuckGo 기반 웹 검색
  - `search_crl_event()`: CRL 이벤트 검색
  - `search_designation()`: BTD/Orphan/Priority Review 검색
  - `search_adcom()`: Advisory Committee 검색
  - `search_primary_endpoint()`: 임상시험 결과 검색
- `WebSearchResult`: 웹 검색 결과 데이터 클래스

### search_chain.py
- `SearchChainOrchestrator`: API → 웹서치 폴백 체인 관리
  - `search_btd()`, `search_orphan_drug()`, `search_priority_review()`
  - `search_crl_events()`: CRL 이벤트 체인 검색
  - `search_all_designations()`: 모든 지정 한번에 검색
- `SearchChainResult`: 체인 검색 결과 (SearchStatus 통합)
- `create_search_chain()`: 팩토리 함수

---

## 다음 단계 (TODO)

### Phase 3: 기존 클라이언트 개선
- [ ] AACT DB 우선순위 적용 (ClinicalTrials API 403 대응)
- [ ] 약물명 다중 변형 검색을 기존 클라이언트에 확대 적용
- [ ] AACTClient에 SearchQueryBuilder.drug_name_variants() 연동

### Phase 4: 통합 및 검증
- [ ] data_enricher.py에 SearchChainOrchestrator 연동
- [ ] 기존 706개 이벤트에 search_metadata 채우기 스크립트
- [ ] NOT_FOUND/NOT_SEARCHED 필드 자동 재검색 배치
- [ ] 검색 완료율 리포트 생성

### Phase 5: 테스트 및 검증
- [ ] 검색 체인 단위 테스트 작성
- [ ] 웹 검색 결과 정확도 검증
- [ ] 기존 데이터와 신규 검색 결과 비교

---

## 참조 문서

- [M3_BLUEPRINT_v2.md](M3_BLUEPRINT_v2.md) - 전체 아키텍처
- [DESIGN_REVIEW.md](DESIGN_REVIEW.md) - 설계 검토 결과
