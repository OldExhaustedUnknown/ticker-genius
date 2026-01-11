# FDA Designation 데이터 수집 종합 계획

## 1. 문제 분석

### 1.1 현재 이슈
| 필드 | 현재 상태 | 문제점 |
|------|----------|--------|
| breakthrough_therapy | 523 found, 0 True | OpenFDA에 해당 정보 없음, 모두 False로 잘못 기록 |
| fast_track | 523 found, 0 True | 동일 |
| orphan_drug | 523 found, 0 True | 동일 |
| accelerated_approval | 523 found, 0 True | 동일 |
| warning_letter | 504 found, 0 True | 검토 필요 (대부분 없는게 맞을 수 있음) |

### 1.2 검증 결과 (알려진 약물)
```
KEYTRUDA: BTD expected=True, actual=False [WRONG]
OPDIVO: BTD expected=True, actual=False [WRONG]
SPINRAZA: Orphan expected=True, actual=False [WRONG]
OXLUMO: Orphan expected=True, actual=False [WRONG]
```

## 2. 대안 데이터 소스

### 2.1 Breakthrough Therapy (BTD)

| 소스 | URL | 형식 | 신뢰도 |
|------|-----|------|--------|
| FDA 공식 | https://www.fda.gov/drugs/nda-and-bla-approvals/breakthrough-therapy-approvals | PDF | Tier 1 |
| Wikipedia | https://en.wikipedia.org/wiki/List_of_drugs_granted_breakthrough_therapy_designation | HTML Table | Tier 2 |
| Friends of Cancer Research | https://friendsofcancerresearch.org/breakthrough-therapies/ | Interactive DB | Tier 2 |

**수집 전략:**
1. FDA PDF 다운로드 → 파싱
2. Wikipedia 테이블 스크래핑
3. 웹서치 폴백: `"{drug_name}" breakthrough therapy designation FDA`

### 2.2 Orphan Drug Designation (OD)

| 소스 | URL | 형식 | 신뢰도 |
|------|-----|------|--------|
| FDA OOPD Database | https://www.accessdata.fda.gov/scripts/opdlisting/oopd/ | Searchable, Excel export | Tier 1 |

**수집 전략:**
1. FDA OOPD 검색 API 시뮬레이션 (form POST)
2. 약물명으로 검색 → 결과 파싱
3. 웹서치 폴백: `"{drug_name}" orphan drug designation FDA`

### 2.3 Accelerated Approval (AA)

| 소스 | URL | 형식 | 신뢰도 |
|------|-----|------|--------|
| FDA CDER Report | https://www.fda.gov/drugs/nda-and-bla-approvals/accelerated-approvals | PDF (분기 업데이트) | Tier 1 |
| FDA Cancer AA List | https://www.fda.gov/drugs/resources-information-approved-drugs/ongoing-cancer-accelerated-approvals | HTML | Tier 1 |

**수집 전략:**
1. FDA PDF 다운로드 → 파싱
2. 웹서치: `"{drug_name}" accelerated approval FDA`

### 2.4 Fast Track (FT)

| 소스 | URL | 형식 | 신뢰도 |
|------|-----|------|--------|
| FDA Fast Track | https://www.fda.gov/drugs/nda-and-bla-approvals/fast-track-approvals | PDF | Tier 1 |

**수집 전략:**
1. FDA PDF 다운로드 → 파싱
2. 웹서치: `"{drug_name}" fast track designation FDA`

## 3. 웹서치 활용 전략

### 3.1 쿼리 템플릿

```python
SEARCH_QUERIES = {
    "breakthrough_therapy": [
        '"{drug_name}" breakthrough therapy designation FDA',
        '"{drug_name}" BTD FDA granted',
        '"{company}" "{drug_name}" breakthrough',
    ],
    "orphan_drug": [
        '"{drug_name}" orphan drug designation FDA',
        '"{drug_name}" orphan designation granted',
        'site:accessdata.fda.gov "{drug_name}" orphan',
    ],
    "accelerated_approval": [
        '"{drug_name}" accelerated approval FDA',
        '"{drug_name}" surrogate endpoint FDA approval',
    ],
    "fast_track": [
        '"{drug_name}" fast track designation FDA',
        '"{drug_name}" fast track granted',
    ],
}
```

### 3.2 결과 파싱 로직

```python
def parse_designation_from_search(results: list, designation_type: str) -> bool:
    """검색 결과에서 designation 여부 추출."""

    POSITIVE_PATTERNS = {
        "breakthrough_therapy": [
            r"granted? breakthrough therapy",
            r"received? breakthrough therapy",
            r"BTD designation",
            r"breakthrough therapy designation for",
        ],
        "orphan_drug": [
            r"granted? orphan drug",
            r"received? orphan drug",
            r"orphan designation",
            r"rare disease designation",
        ],
        "accelerated_approval": [
            r"accelerated approval",
            r"surrogate endpoint",
            r"conditional approval",
        ],
        "fast_track": [
            r"granted? fast track",
            r"received? fast track",
            r"fast track designation",
        ],
    }

    for result in results:
        text = (result.get('title', '') + ' ' + result.get('snippet', '')).lower()
        for pattern in POSITIVE_PATTERNS.get(designation_type, []):
            if re.search(pattern, text, re.IGNORECASE):
                return True
    return None  # 확인 안됨 (False가 아님!)
```

### 3.3 Confidence 계산

```python
def calculate_confidence(sources_found: list, designation_type: str) -> float:
    """소스 기반 신뢰도 계산."""

    SOURCE_WEIGHTS = {
        "fda.gov": 0.95,
        "accessdata.fda.gov": 0.95,
        "drugs.com": 0.85,
        "biospace.com": 0.80,
        "fiercepharma.com": 0.80,
        "wikipedia": 0.75,
        "news": 0.70,
    }

    max_confidence = 0.0
    for source in sources_found:
        for key, weight in SOURCE_WEIGHTS.items():
            if key in source.lower():
                max_confidence = max(max_confidence, weight)

    return max_confidence or 0.6  # 기본값
```

## 4. 서브에이전트 병렬 구조

### 4.1 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                             │
│  - 이벤트 로드                                                    │
│  - 작업 분배                                                      │
│  - 결과 병합 & 저장                                               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Agent 1     │ │   Agent 2     │ │   Agent 3     │ │   Agent 4     │
│   BTD 수집    │ │   OD 수집     │ │   AA 수집     │ │   FT 수집     │
│               │ │               │ │               │ │               │
│ - FDA PDF     │ │ - OOPD API    │ │ - FDA PDF     │ │ - FDA PDF     │
│ - Wikipedia   │ │ - WebSearch   │ │ - WebSearch   │ │ - WebSearch   │
│ - WebSearch   │ │               │ │               │ │               │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
```

### 4.2 에이전트별 책임

| Agent | 담당 필드 | Primary Source | Fallback | Rate Limit |
|-------|----------|----------------|----------|------------|
| Agent 1 | breakthrough_therapy | Wikipedia/FDA PDF | WebSearch | 1 req/sec |
| Agent 2 | orphan_drug | FDA OOPD | WebSearch | 1 req/sec |
| Agent 3 | accelerated_approval | FDA PDF | WebSearch | 1 req/sec |
| Agent 4 | fast_track | FDA PDF | WebSearch | 1 req/sec |

### 4.3 병렬 실행 전략

```python
async def parallel_designation_collection():
    """4개 에이전트 병렬 실행."""

    events = load_events()

    # 1. Reference 데이터 먼저 로드 (공유)
    btd_reference = await load_btd_reference()  # FDA PDF + Wikipedia
    od_reference = await load_orphan_reference()  # FDA OOPD
    aa_reference = await load_aa_reference()  # FDA PDF
    ft_reference = await load_ft_reference()  # FDA PDF

    # 2. 이벤트별 매칭 (병렬)
    async with asyncio.TaskGroup() as tg:
        for event in events:
            tg.create_task(match_btd(event, btd_reference))
            tg.create_task(match_od(event, od_reference))
            tg.create_task(match_aa(event, aa_reference))
            tg.create_task(match_ft(event, ft_reference))

    # 3. 매칭 안된 이벤트 → 웹서치 (순차, Rate Limit)
    unmatched = [e for e in events if not e.get('_btd_matched')]
    for event in unmatched:
        await websearch_designations(event)
        await asyncio.sleep(1.5)  # Rate limit
```

### 4.4 Race Condition 방지

```python
# 문제: 이전에 병렬 스크립트들이 같은 파일을 덮어씀

# 해결책 1: Field-level locking
class EventUpdater:
    def __init__(self):
        self.locks = defaultdict(asyncio.Lock)

    async def update_field(self, event_id: str, field: str, value: dict):
        async with self.locks[event_id]:
            event = load_event(event_id)
            event[field] = value
            save_event(event)

# 해결책 2: 각 에이전트가 별도 파일에 저장 후 최종 병합
# Agent 1 → data/temp/btd_results.json
# Agent 2 → data/temp/od_results.json
# Final   → merge into data/enriched/*.json
```

## 5. 구현 계획

### Phase 1: Reference 데이터 수집 (1회성)

| Task | 소스 | 출력 | 예상 시간 |
|------|------|------|----------|
| 1.1 | FDA BTD PDF 파싱 | `data/reference/btd_list.json` | 10분 |
| 1.2 | Wikipedia BTD 스크래핑 | `data/reference/btd_wiki.json` | 5분 |
| 1.3 | FDA OOPD 전체 다운로드 | `data/reference/orphan_list.json` | 15분 |
| 1.4 | FDA AA PDF 파싱 | `data/reference/aa_list.json` | 10분 |
| 1.5 | FDA FT PDF 파싱 | `data/reference/ft_list.json` | 10분 |

### Phase 2: 매칭 (병렬)

```python
# scripts/match_designations.py
async def main():
    # Reference 로드
    btd_ref = json.load(open('data/reference/btd_list.json'))
    od_ref = json.load(open('data/reference/orphan_list.json'))

    events = load_events()
    results = {
        'btd_matched': [],
        'od_matched': [],
        'needs_websearch': [],
    }

    for event in events:
        drug_name = event.get('drug_name', '').upper()
        generic_name = event.get('generic_name', {}).get('value', '').upper()

        # BTD 매칭
        if drug_name in btd_ref or generic_name in btd_ref:
            results['btd_matched'].append(event['event_id'])

        # OD 매칭
        if drug_name in od_ref or generic_name in od_ref:
            results['od_matched'].append(event['event_id'])
```

### Phase 3: 웹서치 폴백 (순차)

```python
# scripts/websearch_designations.py
async def websearch_unmatched(event: dict):
    """Reference에서 매칭 안된 이벤트 웹서치."""

    drug_name = event.get('drug_name')

    for designation in ['breakthrough_therapy', 'orphan_drug', 'accelerated_approval', 'fast_track']:
        if event.get(f'_{designation}_matched'):
            continue

        queries = SEARCH_QUERIES[designation]
        for query in queries:
            results = await websearch(query.format(drug_name=drug_name))
            found = parse_designation_from_search(results, designation)

            if found is True:
                event[designation] = create_status_field(
                    value=True,
                    status="found",
                    source="websearch",
                    confidence=0.8,
                )
                break
        else:
            # 모든 쿼리 시도 후에도 못 찾음
            event[designation] = create_status_field(
                value=None,  # False가 아님!
                status="not_found",
                source="websearch",
                confidence=0.5,
            )
```

## 6. 스크립트 구조

```
scripts/
├── collect_reference_data.py      # Phase 1: Reference 수집
│   ├── download_fda_btd_pdf()
│   ├── scrape_wikipedia_btd()
│   ├── download_fda_oopd()
│   └── download_fda_aa_ft()
│
├── match_designations.py          # Phase 2: Reference 매칭
│   └── match_all_events()
│
├── websearch_designations.py      # Phase 3: 웹서치 폴백
│   └── websearch_unmatched()
│
└── merge_designation_results.py   # 최종 병합
    └── merge_all()
```

## 7. 검증 체크리스트

### 수집 후 검증
```python
KNOWN_DESIGNATIONS = {
    "KEYTRUDA": {"btd": True, "priority_review": True},
    "OPDIVO": {"btd": True},
    "SPINRAZA": {"orphan": True},
    "OXLUMO": {"orphan": True},
    "TAGRISSO": {"btd": True},
    # ... 더 추가
}

def validate_collection():
    events = load_events()
    errors = []

    for drug, expected in KNOWN_DESIGNATIONS.items():
        found = [e for e in events if drug in e.get('drug_name', '').upper()]
        for e in found:
            for field, expected_val in expected.items():
                actual = e.get(field, {}).get('value')
                if actual != expected_val:
                    errors.append(f"{drug}.{field}: expected={expected_val}, actual={actual}")

    return errors
```

## 8. 주의사항

### 8.1 "False"와 "Not Found" 구분
```python
# 잘못된 방식 (현재)
event['breakthrough_therapy'] = {'value': False, 'status': 'found'}

# 올바른 방식
# Case 1: 확실히 BTD 아님 (FDA 목록에 없음 + 웹서치에도 없음)
event['breakthrough_therapy'] = {'value': False, 'status': 'confirmed_none'}

# Case 2: 확인 못함 (정보 부족)
event['breakthrough_therapy'] = {'value': None, 'status': 'not_found'}

# Case 3: 확실히 BTD임
event['breakthrough_therapy'] = {'value': True, 'status': 'found'}
```

### 8.2 Rate Limit
- FDA 사이트: 보수적으로 2초 간격
- 웹서치: 1.5초 간격
- OOPD: 1초 간격

### 8.3 캐싱
```python
# Reference 데이터는 한 번만 다운로드
# data/reference/에 저장 후 재사용
# 유효기간: 30일 (FDA 분기 업데이트 기준)
```
