# 데이터셋 구축 설계 원칙

> **⚠️ PARTIAL UPDATE**: 이 문서의 수집 파이프라인은 유효하나, 데이터 모델은 M3_BLUEPRINT_v2.md 참조
> - **유효**: API 클라이언트, 수집 순서, 검증 로직, 소스 티어
> - **변경됨**: 케이스 단위 (약물 → PDUFA 이벤트)
> - **추가 필요**: 이벤트 추출 로직 (EventExtractor)

**작성일**: 2026-01-08
**상태**: 부분 업데이트 (M3_BLUEPRINT_v2.md와 함께 참조)

---

## 현황

### 기존 데이터셋
| 구분 | 건수 | 위치 |
|------|------|------|
| **v12 레거시** | 586 레코드 | `D:\Stock\data\ml\pdufa_ml_dataset_v12.json` |
| **마이그레이션 티커** | 245 고유 티커 | 현재 프로젝트 |
| **마이그레이션 케이스** | 582 케이스 | `data/pipelines/by_ticker/` |

### 문제점
1. 레거시 데이터는 검증 없이 복사됨
2. 일부 값 오염 (예: class1=50%)
3. 출처/검증 상태 불명확
4. 이벤트 일자 정보 부족

---

## 구축 원칙 (사전 설계 필수)

### 1. 페르소나 토론 통한 방식 설계

**참여자**:
- A (Architect): 전체 파이프라인 구조
- B (Data Expert): 검색/검증 로직
- C (MCP Specialist): 도구/API 설계
- D (Trading Risk): 필수 팩터 정의
- E (SRE): 에러 처리, 재시도

**토론 주제**:
1. 팩터별 데이터 소스 정의
2. 검증 기준 및 신뢰도 등급
3. 충돌 시 우선순위
4. 자동화 vs 수동 검증 경계

### 2. TDD 방식 - 테스트케이스 선행

```
각 팩터별:
1. 예상 값 범위 정의
2. 필수 출처 정의
3. 검증 로직 테스트 작성
4. 실제 수집 구현
5. 테스트 통과 확인
```

**예시: BTD 팩터**
```python
def test_btd_data_collection():
    """BTD 데이터 수집 검증."""
    # 1. FDA CDER 공식 목록 확인
    # 2. clinicaltrials.gov 교차 검증
    # 3. SEC 8-K 공시 확인
    # 4. 일자 범위 검증
    pass
```

### 3. 병렬/서브에이전트 구조

**티커별 수집 파이프라인**:
```
┌─────────────────────────────────────────────────┐
│  Master Coordinator                              │
│  - 586건 티커 목록 관리                          │
│  - 진행 상태 추적                                │
│  - 결과 병합                                    │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Parallel Batch (10-20개 동시)                   │
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      │
│  │Ticker1│ │Ticker2│ │Ticker3│ │...    │      │
│  └───────┘ └───────┘ └───────┘ └───────┘      │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Per-Ticker Sub-Agent                           │
│  1. FDA 데이터 검색 (OpenFDA, CDER)              │
│  2. SEC 공시 검색 (EDGAR)                        │
│  3. ClinicalTrials.gov 검색                     │
│  4. 뉴스/PR 검색                                │
│  5. 검증 및 충돌 해결                           │
│  6. 결과 저장                                   │
└─────────────────────────────────────────────────┘
```

### 4. 팩터별 수집 방식

| 팩터 | 주 소스 | 보조 소스 | 검증 방법 |
|------|---------|-----------|-----------|
| **BTD** | FDA CDER BTD List | SEC 8-K | 일자 교차 검증 |
| **Priority Review** | FDA Drug Approvals | Company PR | 승인일 확인 |
| **AdCom** | FDA Advisory Calendar | JAMA/BMJ | 투표 비율 확인 |
| **CRL** | FDA FOIA | SEC 8-K | CRL 유형 분류 |
| **PAI** | FDA Warning Letters | SEC filings | 시설 ID 매칭 |
| **Warning Letter** | FDA WL DB | 시설 검색 | 발행일 확인 |
| **Clinical Phase** | ClinicalTrials.gov | SEC S-1 | NCT ID 매칭 |

### 5. 에러 처리 및 재시도

```python
class DataCollectionPolicy:
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    timeout: int = 30

    # 소스별 fallback
    fallback_sources: dict = {
        "fda_cder": ["openfda", "sec_edgar"],
        "clinicaltrials": ["sec_filings", "company_pr"],
    }

    # 검증 실패 시
    on_validation_failure: str = "flag_for_manual_review"
```

---

## 예상 소요

| 단계 | 예상 작업 |
|------|-----------|
| 1. 방식 설계 | 페르소나 토론 |
| 2. 테스트케이스 작성 | 팩터별 검증 로직 |
| 3. 수집 도구 구현 | API 연동, 파싱 |
| 4. 병렬 실행 | 586건 처리 |
| 5. 검증 및 수정 | 충돌 해결 |

---

## 페르소나 토론 결과

**일시**: 2026-01-08
**참여자**: A (Architect), B (Data Expert), C (MCP Specialist), D (Trading Risk), E (SRE)

---

### 토론 1: 팩터별 데이터 소스 정의

**A (Architect)**: 팩터를 3가지 카테고리로 분류해야 합니다.
1. **공식 소스 필수** - BTD, Priority Review, AdCom (FDA 공식 데이터만 신뢰)
2. **공시 기반** - CRL, PAI, Warning Letter (SEC 8-K + FDA 확인)
3. **추론 가능** - Earnings Call 시그널, 경영진 자신감 (주관적 해석 필요)

**B (Data Expert)**: 각 소스별 신뢰도 등급을 정의하겠습니다.
- **Tier 1 (99% 신뢰)**: FDA CDER 공식 목록, OpenFDA API 결과
- **Tier 2 (90% 신뢰)**: SEC EDGAR 8-K 공시, ClinicalTrials.gov
- **Tier 3 (75% 신뢰)**: 회사 PR, 뉴스 기사
- **Tier 4 (50% 신뢰)**: 애널리스트 리포트, 추론 기반

**C (MCP Specialist)**: API 호출 순서 제안합니다.
1. OpenFDA → BTD, Orphan, Accelerated Approval 확인
2. ClinicalTrials.gov → NCT ID로 임상 정보 확인
3. SEC EDGAR → 8-K에서 PDUFA, CRL, AdCom 추출
4. FDA Calendar → AdCom 일정 확인

**D (Trading Risk)**: **절대 누락 불가 팩터**를 정의해야 합니다.
- PDUFA 날짜 (없으면 분석 불가)
- Primary Endpoint Met 여부 (Phase 3 필수)
- BTD/Priority Review 상태 (승인률 영향 큼)
- AdCom 결과 (있는 경우)
- CRL 이력 (재제출 시)

**E (SRE)**: API 실패 시 fallback 전략:
- OpenFDA 실패 → FDA CDER 웹 스크래핑
- SEC EDGAR 실패 → Company IR 페이지
- ClinicalTrials 실패 → PubMed 검색

---

### 토론 2: 검증 기준 및 충돌 해결

**A (Architect)**: 검증 단계를 3단계로 나눕니다.
1. **형식 검증**: 날짜 형식, 값 범위, 필수 필드
2. **교차 검증**: 2개 이상 소스에서 확인
3. **논리 검증**: 시간 순서 (CRL → 재제출 → PDUFA)

**B (Data Expert)**: 충돌 해결 규칙:
- **날짜 충돌**: FDA 공식 > SEC 공시 > 뉴스 기사
- **Boolean 충돌**: 긍정(True) 우선 (BTD=True가 한 곳이라도 있으면 True)
- **수치 충돌**: 범위 내 평균 또는 신뢰도 가중 평균

**C (MCP Specialist)**: 검증 실패 시 처리:
```json
{
  "field": "breakthrough_therapy",
  "value": true,
  "confidence": 0.85,
  "sources": ["openfda", "sec_8k"],
  "conflicts": [],
  "needs_manual_review": false
}
```

**D (Trading Risk)**: **Hard Failure 조건** (수동 검토 필수):
- PDUFA 날짜가 소스마다 30일 이상 차이
- AdCom 투표 결과가 소스마다 상반됨
- CRL 유형(class1/class2)이 불명확

**E (SRE)**: 검증 실패율 모니터링:
- 10% 이상 실패 시 알림
- 특정 소스 연속 3회 실패 시 fallback 자동 전환

---

### 토론 3: 수집 파이프라인 구조

**A (Architect)**: 2단계 파이프라인 제안:
1. **Stage 1: 대량 수집** - 586건 기본 정보 수집 (병렬 10건)
2. **Stage 2: 심층 검증** - 충돌/의심 건만 상세 검증

**B (Data Expert)**: 티커별 수집 순서:
1. `ticker` + `drug_name` → 기본 식별
2. PDUFA 날짜 확인 → 분석 가능 여부 판단
3. FDA 지정 (BTD, PR, FT, OD, AA) 일괄 수집
4. 임상 정보 (NCT ID, Phase, Endpoint)
5. AdCom 결과 (있는 경우)
6. 제조 시설 정보 (PAI, Warning Letter)
7. CRL 이력 (있는 경우)

**C (MCP Specialist)**: 병렬 처리 구조:
```python
async def collect_ticker_data(ticker: str) -> CollectedData:
    # 1. 기본 정보 (동기)
    basic = await get_basic_info(ticker)

    # 2. 병렬 수집
    fda_task = asyncio.create_task(get_fda_designations(ticker))
    clinical_task = asyncio.create_task(get_clinical_info(ticker))
    sec_task = asyncio.create_task(get_sec_filings(ticker))

    fda, clinical, sec = await asyncio.gather(fda_task, clinical_task, sec_task)

    # 3. 검증 및 병합
    return merge_and_validate(basic, fda, clinical, sec)
```

**D (Trading Risk)**: **최소 데이터 품질 기준**:
- 필수 필드 완성률 > 80%
- 교차 검증 성공률 > 70%
- 시간 순서 논리 검증 통과

**E (SRE)**: Rate Limiting 준수:
- OpenFDA: 240 req/min → 배치당 200건 후 1분 대기
- SEC EDGAR: 10 req/sec → 0.1초 간격
- ClinicalTrials: 제한 없음 (예의상 0.5초 간격)

---

### 토론 4: 데이터 무결성 보장

**A (Architect)**: **데이터 무결성 원칙**:
1. 원본 데이터 보존 (raw JSON 저장)
2. 변환 로그 기록 (어떤 필드가 어떻게 변환됐는지)
3. 버전 관리 (수집 일시, 버전 태그)

**B (Data Expert)**: 필드별 검증 규칙:
```yaml
pdufa_date:
  type: date
  format: "YYYY-MM-DD"
  range: ["2010-01-01", "2030-12-31"]
  required: true

breakthrough_therapy:
  type: boolean
  source_required: ["openfda", "sec_8k"]
  cross_validate: true

adcom_vote_ratio:
  type: float
  range: [0.0, 1.0]
  null_allowed: true
  condition: "adcom.was_held == true"
```

**C (MCP Specialist)**: 저장 구조:
```
data/collected/
├── raw/                    # 원본 API 응답
│   └── {ticker}/
│       ├── openfda.json
│       ├── sec_8k.json
│       └── clinicaltrials.json
├── processed/              # 검증/병합된 데이터
│   └── {ticker}.json
├── validation_log/         # 검증 로그
│   └── {ticker}_log.json
└── manifest.json           # 전체 수집 현황
```

**D (Trading Risk)**: **데이터 오염 방지**:
- 수집 전 기존 데이터 백업
- 검증 실패 시 기존 데이터 유지
- 수동 수정 시 변경 사유 기록

**E (SRE)**: 복구 전략:
- 매 100건 수집 후 체크포인트 저장
- 중단 시 마지막 체크포인트부터 재시작
- 실패 건 별도 큐에 보관 → 나중에 재시도

---

### 토론 결론: 합의된 수집 방식

**1. 수집 단위**: 티커별 (동일 티커 여러 약물은 drug_name으로 구분)

**2. 수집 순서**:
1. v12 레거시 데이터 로드 (기존 값 참조용)
2. FDA 공식 소스 우선 수집
3. SEC EDGAR 교차 검증
4. 충돌 시 Tier 1 소스 우선

**3. 검증 기준**:
- 필수 필드: ticker, drug_name, pdufa_date
- 교차 검증: BTD, Priority Review, AdCom
- 논리 검증: 날짜 순서 (CRL < 재제출 < PDUFA)

**4. 오류 처리**:
- Tier 1 실패 → Tier 2로 fallback
- 검증 실패 → needs_manual_review 플래그
- 연속 실패 → 해당 티커 스킵, 로그 기록

**5. 데이터 품질 목표**:
- 필수 필드 완성률: 95% 이상
- 교차 검증 일치율: 85% 이상
- 오염 데이터: 0건

---

## 수집 결과 (2026-01-09)

### 통계
| 항목 | 값 |
|------|-----|
| 총 수집 건수 | 523건 |
| 수집 성공률 | 100% |
| Tier 1 커버리지 | 33.2% |
| 검증 필요 | 523건 (100%) |
| 실패 | 0건 |
| 소요 시간 | 28분 |

### 주요 티커 분포
| 티커 | 케이스 수 |
|------|----------|
| MRK | 22 |
| BMY | 19 |
| GSK | 16 |
| PFE | 15 |
| NVS | 11 |
| BIIB | 8 |
| GILD | 8 |
| AMGN | 7 |

### 데이터 소스 현황
- **OpenFDA**: 정상 작동 (PDUFA 날짜, 승인 결과, 일부 지정 정보)
- **ClinicalTrials.gov**: 403 차단됨 (레거시 데이터로 대체)
- **SEC EDGAR**: 미구현 (레거시 데이터로 대체)

### 데이터 품질 이슈
1. 모든 케이스가 "검증 필요" 상태 (보수적 접근)
2. FDA 지정(BTD, PR, FT, OD, AA)은 주로 레거시 데이터(Tier 3)에서 추출
3. PDUFA 날짜와 승인 결과는 33% 케이스에서 Tier 1(OpenFDA) 확인됨

### 다음 단계
1. ClinicalTrials.gov API 우회 방안 검토
2. SEC EDGAR 8-K 파싱 구현
3. 수동 검토 프로세스 구축
4. 교차 검증 로직 강화

---

## DDG 기반 검색 전략 (2026-01-09 추가)

### 배경
- SEC EFTS Full-text Search: 403 Forbidden (봇 차단)
- ClinicalTrials.gov API: 403 Forbidden
- Python 기반 외부 API 접근이 대부분 봇으로 감지됨

### 해결책: DuckDuckGo Search 라이브러리
`ddgs` 패키지를 활용한 웹 검색 기반 데이터 수집

```python
from ddgs import DDGS

# 임상 결과 검색
results = DDGS().text(f"{ticker} {drug_name} phase 3 primary endpoint met", max_results=5)
```

### 검색 전략

**1. Primary Endpoint 검색**
```
쿼리: "{ticker} {drug_name} phase 3 primary endpoint met"
패턴: "met its primary endpoint", "achieved primary endpoint",
      "positive top-line results", "statistically significant"
```

**2. P-value 추출**
```
쿼리: "{drug_name} clinical trial results p-value"
패턴: "p<0.001", "p=0.0001", "p-value of 0.05"
```

**3. Approval Type 분류**
```
쿼리: "{ticker} {drug_name} FDA NDA BLA application filing"
패턴: "NDA", "BLA", "ANDA", "sNDA", "505(b)(2)"
```

### 구현 파일
- `src/tickergenius/collection/ddg_searcher.py` - DDG 검색 클라이언트
- `scripts/enrich_with_ddg.py` - DDG 기반 enrichment 스크립트

### 결과 저장
```json
{
  "primary_endpoint_met": {
    "status": "found",
    "value": true,
    "source": "ddg_search",
    "confidence": 0.8,
    "evidence": ["..."]
  }
}
```

### Fallback Chain (최종)
1. **SEC EDGAR Submissions API** - 8-K 목록 조회 (작동)
2. **DDG Web Search** - 임상 결과, approval type 검색
3. **OpenFDA API** - FDA 승인 정보 (부분 작동)
4. **Legacy Data** - 기존 수집 데이터 활용

### Rate Limit
- DDG: 2초 간격 (MIN_INTERVAL)
- 검색당 3개 쿼리 × 5개 결과 = 15건 파싱

---

## 참고

- 523건은 고유 PDUFA 케이스 (동일 티커 여러 약물 포함)
- v12 레거시에서 586건 중 523건이 유효 (63건은 중복 또는 무효)
- 일부 케이스는 역사적 데이터 (이미 결과 확정)
- 신규 케이스는 지속적 업데이트 필요
- **DDG 검색 기반 enrichment 진행 중** (2026-01-09)
