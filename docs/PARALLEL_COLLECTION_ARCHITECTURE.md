# 병렬 수집 아키텍처 설계

## 1. 현재 문제점 분석

### 1.1 collect_fda_designations.py 이슈

```python
# 문제 1: OpenFDA에 없는 정보를 찾으려 함
designations = {
    "breakthrough_therapy": False,  # OpenFDA에 없음!
    "fast_track": False,           # OpenFDA에 없음!
    ...
}

# 문제 2: 못 찾으면 False로 저장 (NOT_FOUND가 아님)
for field in ["breakthrough_therapy", ...]:
    event[field] = create_status_field(
        value=False,  # 잘못됨! None이어야 함
        status="confirmed_none",  # 잘못됨! 확인 안됐음
        ...
    )

# 문제 3: 기존 SearchChainOrchestrator 미활용
# WebSearchClient.search_designation() 있지만 사용 안함
```

### 1.2 웹서치 실패 원인

```python
# 현재 DuckDuckGo 검색 결과가 부실
# KEYTRUDA breakthrough therapy 검색 시:
# - DuckDuckGo HTML 파싱이 불완전
# - Rate limit으로 결과 누락
# - 검색 쿼리 최적화 필요
```

### 1.3 Race Condition (이전 발생)

```
Agent 1 (BTD) → 파일 저장
Agent 2 (AdCom) → 같은 파일 덮어쓰기 (BTD 데이터 소실!)
Agent 3 (Small Gaps) → 같은 파일 덮어쓰기
```

## 2. 해결 아키텍처

### 2.1 3단계 수집 파이프라인

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Stage 1: Reference Data Collection               │
│                         (1회성, 공유 데이터)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│   │ FDA BTD List  │  │ FDA OD List   │  │ FDA AA/FT     │           │
│   │ (Wikipedia)   │  │ (OOPD DB)     │  │ (PDF Parse)   │           │
│   └───────┬───────┘  └───────┬───────┘  └───────┬───────┘           │
│           │                  │                  │                    │
│           └──────────────────┼──────────────────┘                    │
│                              ▼                                       │
│                    data/reference/*.json                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Stage 2: Matching (병렬 가능)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   for event in events:                                               │
│       match_btd(event, btd_reference)     # O(1) lookup              │
│       match_orphan(event, od_reference)   # O(1) lookup              │
│       match_aa(event, aa_reference)       # O(1) lookup              │
│       match_ft(event, ft_reference)       # O(1) lookup              │
│                                                                      │
│   Output: matched_events.json, unmatched_events.json                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Stage 3: WebSearch Fallback (순차)                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   for event in unmatched_events:                                     │
│       result = SearchChainOrchestrator.search_all_designations()     │
│       if result.status == FOUND:                                     │
│           mark as found                                              │
│       else:                                                          │
│           mark as NOT_FOUND (NOT confirmed_none!)                    │
│                                                                      │
│       await asyncio.sleep(1.5)  # Rate limit                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Stage 4: Final Merge                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Load all results:                                                  │
│   - matched_events.json                                              │
│   - websearch_results.json                                           │
│                                                                      │
│   For each event:                                                    │
│       Merge fields with proper status                                │
│       Save to data/enriched/*.json                                   │
│                                                                      │
│   NO RACE CONDITION: Single writer, atomic merge                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 서브에이전트 구조 (Claude Code Task Tool)

```python
# 메인 오케스트레이터
async def run_parallel_collection():
    """Claude Code Task tool로 병렬 수집."""

    # Phase 1: Reference 수집 (병렬)
    tasks = [
        Task("collect_btd_reference", subagent_type="Bash"),
        Task("collect_od_reference", subagent_type="Bash"),
        Task("collect_aa_ft_reference", subagent_type="Bash"),
    ]
    await asyncio.gather(*[t.run() for t in tasks])

    # Phase 2: Matching (단일 스크립트, 빠름)
    await Task("match_all_events", subagent_type="Bash").run()

    # Phase 3: WebSearch (순차, Rate Limit)
    await Task("websearch_unmatched", subagent_type="Bash").run()

    # Phase 4: Merge
    await Task("merge_results", subagent_type="Bash").run()
```

### 2.3 Race Condition 방지 전략

```python
# 전략 1: 결과 파일 분리
"""
data/temp/
├── btd_results.json       # Agent 1 전용
├── od_results.json        # Agent 2 전용
├── aa_results.json        # Agent 3 전용
├── ft_results.json        # Agent 4 전용
└── websearch_results.json # WebSearch 전용

→ 최종 병합 시 단일 프로세스가 처리
"""

# 전략 2: Field-level 업데이트
class SafeEventUpdater:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def update_field(self, event_id: str, field: str, value: dict):
        async with self.lock:
            event = load_event(event_id)
            event[field] = value
            event['enriched_at'] = datetime.now().isoformat()
            save_event(event)

# 전략 3: 순차 실행 (가장 안전)
# 각 에이전트가 끝난 후 다음 에이전트 실행
# 느리지만 데이터 무결성 보장
```

## 3. Reference 데이터 수집 상세

### 3.1 Breakthrough Therapy (BTD)

```python
# scripts/collect_btd_reference.py

import re
import httpx
from bs4 import BeautifulSoup

async def collect_from_wikipedia():
    """Wikipedia BTD 목록 스크래핑."""
    url = "https://en.wikipedia.org/wiki/List_of_drugs_granted_breakthrough_therapy_designation"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, follow_redirects=True)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 테이블 파싱
        tables = soup.find_all('table', class_='wikitable')

        btd_drugs = []
        for table in tables:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    drug_name = cols[0].get_text(strip=True)
                    sponsor = cols[1].get_text(strip=True)
                    indication = cols[2].get_text(strip=True)

                    btd_drugs.append({
                        "drug_name": drug_name,
                        "sponsor": sponsor,
                        "indication": indication,
                        "source": "wikipedia",
                    })

        return btd_drugs

async def collect_from_fda():
    """FDA 공식 BTD 목록 (PDF → 파싱 필요)."""
    # TODO: FDA PDF 다운로드 및 파싱
    pass

def save_reference(drugs: list, filename: str):
    """Reference 데이터 저장."""
    # Normalize for lookup
    lookup = {}
    for drug in drugs:
        name_upper = drug['drug_name'].upper()
        lookup[name_upper] = drug

        # 약어 및 변형도 추가
        # KEYTRUDA -> PEMBROLIZUMAB
        # etc.

    with open(f'data/reference/{filename}', 'w') as f:
        json.dump({
            "drugs": drugs,
            "lookup": lookup,
            "collected_at": datetime.now().isoformat(),
        }, f, indent=2)
```

### 3.2 Orphan Drug (OD)

```python
# scripts/collect_od_reference.py

async def collect_from_fda_oopd():
    """FDA OOPD 데이터베이스 수집."""

    # FDA OOPD는 검색 API가 없어서 전체 다운로드 필요
    # 방법 1: 수동으로 Excel 다운로드 후 파싱
    # 방법 2: 웹 검색으로 개별 약물 확인

    # 여기서는 웹서치 기반 수집
    from tickergenius.collection.web_search import WebSearchClient

    client = WebSearchClient()

    # 알려진 orphan drugs (시드 데이터)
    KNOWN_ORPHAN_DRUGS = [
        "SPINRAZA", "ZOLGENSMA", "LUXTURNA", "ONPATTRO", "GIVLAARI",
        "OXLUMO", "SKYSONA", "VOXZOGO", "ROCTAVIAN", "HEMGENIX",
        # ... 더 추가
    ]

    orphan_drugs = []
    for drug in KNOWN_ORPHAN_DRUGS:
        result = client.search_designation("", drug, "orphan")
        if result.found and result.value:
            orphan_drugs.append({
                "drug_name": drug,
                "source": result.source,
                "evidence": result.evidence,
            })

    return orphan_drugs
```

### 3.3 Accelerated Approval (AA) & Fast Track (FT)

```python
# scripts/collect_aa_ft_reference.py

# FDA PDF 파싱 (PyMuPDF 사용)
import fitz  # PyMuPDF

def parse_fda_aa_pdf(pdf_path: str) -> list:
    """FDA Accelerated Approval PDF 파싱."""
    doc = fitz.open(pdf_path)

    aa_drugs = []
    for page in doc:
        text = page.get_text()
        # 테이블 구조 파싱
        # ...

    return aa_drugs
```

## 4. 웹서치 개선 전략

### 4.1 쿼리 최적화

```python
# 현재 (비효율적)
query = f'{ticker} "{brand}" FDA {keywords[0]} granted received'

# 개선
OPTIMIZED_QUERIES = {
    "btd": [
        # 1. 정확한 표현 우선
        f'"{drug_name}" "breakthrough therapy designation" FDA granted',
        f'"{drug_name}" BTD FDA',
        # 2. 회사명 포함
        f'"{company}" "{drug_name}" breakthrough therapy',
        # 3. 뉴스 소스 지정
        f'site:biospace.com "{drug_name}" breakthrough',
        f'site:fiercepharma.com "{drug_name}" breakthrough',
    ],
    "orphan": [
        f'"{drug_name}" "orphan drug designation" FDA',
        f'site:accessdata.fda.gov "{drug_name}" orphan',
        f'"{drug_name}" rare disease designation',
    ],
}
```

### 4.2 결과 검증 강화

```python
def validate_btd_result(result: dict, drug_name: str) -> bool:
    """BTD 검색 결과 검증."""
    text = f"{result['title']} {result['snippet']}".upper()

    # 필수 조건
    must_have = [
        drug_name.upper() in text,
        any(kw in text for kw in ["BREAKTHROUGH", "BTD"]),
    ]

    # 긍정적 표현
    positive = any(term in text for term in [
        "GRANTED", "RECEIVED", "AWARDED", "DESIGNATED", "OBTAINS"
    ])

    # 부정적 표현 (제외)
    negative = any(term in text for term in [
        "DENIED", "REJECTED", "FAILED", "NOT GRANTED"
    ])

    return all(must_have) and positive and not negative
```

### 4.3 Fallback 체인

```
1. DuckDuckGo HTML (현재)
   ↓ 실패 시
2. Google Custom Search API (유료, 정확도 높음)
   ↓ 실패 시
3. Bing Search API (유료)
   ↓ 실패 시
4. NOT_FOUND로 기록 (False 아님!)
```

## 5. 구현 스크립트

### 5.1 전체 실행 스크립트

```python
# scripts/run_designation_collection.py

"""
FDA Designation 전체 수집 파이프라인

Usage:
    python scripts/run_designation_collection.py --phase all
    python scripts/run_designation_collection.py --phase reference
    python scripts/run_designation_collection.py --phase match
    python scripts/run_designation_collection.py --phase websearch
    python scripts/run_designation_collection.py --phase merge
"""

import asyncio
import argparse
from pathlib import Path

async def phase_reference():
    """Phase 1: Reference 데이터 수집."""
    print("=== Phase 1: Collecting Reference Data ===")

    # BTD
    from scripts.collect_btd_reference import collect_btd
    await collect_btd()

    # Orphan
    from scripts.collect_od_reference import collect_orphan
    await collect_orphan()

    # AA/FT
    from scripts.collect_aa_ft_reference import collect_aa_ft
    await collect_aa_ft()

async def phase_match():
    """Phase 2: Reference 매칭."""
    print("=== Phase 2: Matching Events ===")
    from scripts.match_designations import match_all
    await match_all()

async def phase_websearch():
    """Phase 3: WebSearch 폴백."""
    print("=== Phase 3: WebSearch for Unmatched ===")
    from scripts.websearch_designations import search_unmatched
    await search_unmatched()

async def phase_merge():
    """Phase 4: 결과 병합."""
    print("=== Phase 4: Merging Results ===")
    from scripts.merge_designation_results import merge_all
    await merge_all()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["all", "reference", "match", "websearch", "merge"], default="all")
    args = parser.parse_args()

    if args.phase == "all":
        await phase_reference()
        await phase_match()
        await phase_websearch()
        await phase_merge()
    elif args.phase == "reference":
        await phase_reference()
    elif args.phase == "match":
        await phase_match()
    elif args.phase == "websearch":
        await phase_websearch()
    elif args.phase == "merge":
        await phase_merge()

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 매칭 스크립트

```python
# scripts/match_designations.py

import json
from pathlib import Path

def load_reference(filename: str) -> dict:
    """Reference lookup 로드."""
    path = Path(f"data/reference/{filename}")
    if not path.exists():
        return {}
    return json.loads(path.read_text())

def match_drug(drug_name: str, generic_name: str, reference: dict) -> bool:
    """약물이 reference에 있는지 확인."""
    lookup = reference.get("lookup", {})

    # Brand name 매칭
    if drug_name.upper() in lookup:
        return True

    # Generic name 매칭
    if generic_name and generic_name.upper() in lookup:
        return True

    # Partial 매칭 (KEYTRUDA + X → KEYTRUDA)
    for ref_name in lookup:
        if ref_name in drug_name.upper() or drug_name.upper() in ref_name:
            return True

    return False

async def match_all():
    """모든 이벤트에 대해 매칭 수행."""

    # Reference 로드
    btd_ref = load_reference("btd_list.json")
    od_ref = load_reference("orphan_list.json")
    aa_ref = load_reference("aa_list.json")
    ft_ref = load_reference("ft_list.json")

    # 이벤트 로드
    events = []
    for f in Path("data/enriched").glob("*.json"):
        events.append(json.loads(f.read_text()))

    # 매칭 결과
    results = {
        "matched": [],
        "unmatched": [],
    }

    for event in events:
        drug_name = event.get("drug_name", "")
        generic_name = event.get("generic_name", {}).get("value", "")

        matched = {}

        # BTD 매칭
        if match_drug(drug_name, generic_name, btd_ref):
            matched["breakthrough_therapy"] = True

        # OD 매칭
        if match_drug(drug_name, generic_name, od_ref):
            matched["orphan_drug"] = True

        # AA 매칭
        if match_drug(drug_name, generic_name, aa_ref):
            matched["accelerated_approval"] = True

        # FT 매칭
        if match_drug(drug_name, generic_name, ft_ref):
            matched["fast_track"] = True

        if matched:
            results["matched"].append({
                "event_id": event["event_id"],
                "drug_name": drug_name,
                "designations": matched,
            })
        else:
            results["unmatched"].append(event["event_id"])

    # 결과 저장
    Path("data/temp").mkdir(exist_ok=True)
    Path("data/temp/match_results.json").write_text(
        json.dumps(results, indent=2)
    )

    print(f"Matched: {len(results['matched'])}")
    print(f"Unmatched: {len(results['unmatched'])}")
```

## 6. 검증 및 테스트

### 6.1 검증 데이터셋

```python
# Known ground truth
VALIDATION_SET = {
    "KEYTRUDA": {
        "breakthrough_therapy": True,
        "priority_review": True,
        "orphan_drug": False,
        "accelerated_approval": True,  # 일부 적응증
    },
    "SPINRAZA": {
        "orphan_drug": True,
        "breakthrough_therapy": True,
        "fast_track": True,
    },
    "OPDIVO": {
        "breakthrough_therapy": True,
        "priority_review": True,
    },
    # ... 최소 20개 약물
}
```

### 6.2 수집 후 검증

```bash
# 검증 스크립트 실행
python scripts/validate_designations.py

# 예상 출력:
# KEYTRUDA.breakthrough_therapy: expected=True, actual=True [OK]
# KEYTRUDA.orphan_drug: expected=False, actual=False [OK]
# SPINRAZA.orphan_drug: expected=True, actual=True [OK]
# ...
# Validation: 20/20 passed (100%)
```

## 7. 실행 계획

### Day 1: 인프라 구축
1. Reference 수집 스크립트 작성 (BTD, OD, AA, FT)
2. 매칭 스크립트 작성
3. 병합 스크립트 작성

### Day 2: 데이터 수집
1. Reference 데이터 수집 실행
2. 매칭 실행
3. WebSearch 폴백 실행 (Rate limit으로 시간 소요)

### Day 3: 검증 및 수정
1. 검증 실행
2. 문제 수정
3. 최종 데이터 확인
