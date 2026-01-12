# Ticker-Genius 데이터셋 심층 분석 보고서

**작성일**: 2026-01-12
**작성자**: Claude (Opus 4.5) + 사용자 협업
**상태**: 연구 완료, 구현 대기

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [현재 데이터셋 현황](#2-현재-데이터셋-현황)
3. [발견된 문제점](#3-발견된-문제점)
4. [근본 원인 분석](#4-근본-원인-분석)
5. [연구 결과: FDA 공식 데이터](#5-연구-결과-fda-공식-데이터)
6. [연구 결과: 데이터 수집 가능성](#6-연구-결과-데이터-수집-가능성)
7. [Pending 케이스 분석](#7-pending-케이스-분석)
8. [해결 방향](#8-해결-방향)
9. [구현 계획](#9-구현-계획)
10. [핵심 원칙 재확인](#10-핵심-원칙-재확인)

---

## 1. 프로젝트 개요

### 1.1 목적
FDA PDUFA (Prescription Drug User Fee Act) 승인 확률 예측 및 제약 주식 거래 신호 시스템

### 1.2 현재 마일스톤
- **M1**: Pydantic 스키마 ✅ 완료
- **M2**: Core 인프라 ✅ 완료
- **M3**: PDUFA 분석 모듈 ⏳ 90% (현재 진행)
- **M4**: MCP 서버 + 도구 ⏳ 대기
- **M5**: ML 모듈 ⏳ 대기

### 1.3 핵심 아키텍처

```
data/enriched/*.json (523개 이벤트)
        ↓
AnalysisContext.from_enriched()
        ↓
    EventLoader
        ↓
   PDUFAAnalyzer (12개 레이어)
        ↓
    확률 계산 (0.0 ~ 1.0)
```

### 1.4 분석 레이어 순서
1. base - 기본 승인률
2. designation - FDA 지정 (BTD, PR, FT, OD, AA)
3. adcom - Advisory Committee
4. crl - CRL 이력
5. clinical - 임상 요인
6. manufacturing - 제조 시설
7. special - 특수 지정
8. context - 상호작용
9. cap - 상한/하한
10. dispute - FDA 분쟁
11. earnings_call - 경영진 발언
12. citizen_petition - 시민청원

---

## 2. 현재 데이터셋 현황

### 2.1 데이터 분포

| 상태 | 개수 | 비율 |
|------|------|------|
| **Approved** | 477 | 91.2% |
| **CRL** | 27 | 5.2% |
| **Pending** | 17 | 3.3% |
| **Withdrawn** | 2 | 0.4% |
| **총계** | 523 | 100% |

### 2.2 필드 완성률

| 필드 | 완성률 | 상태 |
|------|--------|------|
| event_id, ticker, drug_name | 100% | ✅ |
| indication, pdufa_date | 100% | ✅ |
| primary_endpoint_met | 100% | ✅ |
| fda_designations | 100% | ✅ |
| adcom_info | 100% | ✅ |
| nct_ids | 97.1% | ✅ |
| pai_passed | 91.2% | ✅ |
| **is_resubmission** | 100% | ⚠️ **검증 안됨** |
| **has_prior_crl** | 99.8% | ⚠️ **검증 안됨** |
| **prior_crl_reason** | 5.5% | ❌ 불완전 |

### 2.3 백테스트 결과

| 방법 | 정확도 | CRL Recall |
|------|--------|------------|
| Simple Rule (endpoint_met ∧ pai_passed) | 96.0% | 52% |
| PDUFAAnalyzer (12 레이어) | 92.5% | 33% |

### 2.4 핵심 예측 인자 분석

| 필드 | Approved 비율 | CRL 비율 | Gap |
|------|--------------|---------|-----|
| endpoint_met=True | 99% | 70% | +29% |
| pai_passed=True | 100% | 74% | +26% |
| prior_crl=True | 35% | 56% | -21% |

**발견**: endpoint_met과 pai_passed가 가장 강력한 예측 인자

---

## 3. 발견된 문제점

### 3.1 핵심 문제: 타임라인 부재

```
현재 구조의 근본 한계:

┌─────────────────────────────────────────────────────┐
│  523개 독립된 "이벤트" (스냅샷)                      │
│                                                     │
│  GILD_xxx.json - Filgotinib 2020년 CRL              │
│  FGEN_yyy.json - Roxadustat 2021년 CRL              │
│  ...                                                │
│                                                     │
│  문제:                                              │
│  - 같은 약물의 여러 이벤트 연결 불가                 │
│  - CRL 후 재제출 여부 확인 불가                     │
│  - PDUFA 날짜 변경 이력 추적 불가                   │
│  - 타임라인 없이 is_resubmission 검증 불가          │
└─────────────────────────────────────────────────────┘
```

### 3.2 is_resubmission 필드 오염

**발견된 사실**:
- CRL 27건 **전부** is_resubmission=1로 표시됨
- 이는 통계적으로 불가능 (첫 CRL도 재제출로 표시)
- 원인: `derive_prior_crl.py` 스크립트의 순환 논리

**문제의 스크립트** (`scripts/_archive/derive_prior_crl.py`):
```python
# 라인 51-73: 순환 논리
if result == 'crl':
    derived_value = is_resub  # ← is_resubmission 자체가 오염됨
    source = 'derived_from_crl_context'
    confidence = 0.7
elif result == 'approved':
    if is_resub:
        derived_value = True  # ← 오염된 값 기반 파생
```

### 3.3 has_prior_crl 필드 오염

**오염 경로**:
```
is_resubmission (legacy_v12, 미검증)
        ↓
has_prior_crl (is_resubmission에서 파생)
        ↓
crl_history (has_prior_crl에서 파생)
        ↓
분석 결과 오염
```

### 3.4 prior_crl_reason 필드명 오류

**발견**: `prior_crl_reason`은 실제로 **현재 CRL 사유**를 저장
- 29건 중 대부분이 result=crl인 이벤트의 CRL 사유
- 필드명이 "prior"지만 실제로는 "current" CRL 사유

### 3.5 Derived 데이터가 Found로 위장

**문제 패턴**:
```python
# compute_has_prior_crl.py - 실제 코드
data['has_prior_crl'] = {
    'status': 'found',              # ← 파생인데 'found'로 위장
    'value': derived_value,
    'source': 'derived_from_first_submission',
    'confidence': 0.85,
}
```

**source 필드 분포**:
| source | 개수 | 문제 |
|--------|------|------|
| websearch | 291 | ✅ 실제 수집 |
| (empty) | 199 | ❌ 출처 불명 |
| legacy_v12 | 62 | ❌ 검증 불가 |
| derived_* | 46+ | ❌ 추론 |
| inferred_* | 46+ | ❌ 추론 |

---

## 4. 근본 원인 분석

### 4.1 데이터 모델 문제

```
현재 모델: Event-Centric (이벤트 중심)
┌─────────────┐
│   Event     │  ← 각 이벤트가 독립적
│ - event_id  │  ← 자체 생성 ID
│ - drug_name │
│ - pdufa_date│
│ - result    │
└─────────────┘

필요한 모델: Application-Centric (신청 중심)
┌─────────────┐
│ Application │  ← FDA ApplNo 기준
│ - appl_no   │  ← FDA 공식 ID
│ - drug_name │
│ - timeline  │───→ [Event1, Event2, ...]
└─────────────┘
```

### 4.2 FDA 공식 식별자 부재

- 현재: 자체 생성 `event_id` (예: `GILD_abc123`)
- 필요: FDA 공식 `ApplNo` (예: `NDA212526`)
- ApplNo 없이는 FDA 공식 데이터와 연결 불가

### 4.3 search_status 의미 혼란

| 값 | 원래 의미 | 실제 사용 |
|----|----------|----------|
| FOUND | 검색해서 찾음 | 파생 데이터도 FOUND로 표시 |
| NOT_VERIFIED | 값 있으나 미검증 | 거의 사용 안 함 |
| NOT_SEARCHED | 미검색 | 정상 사용 |

### 4.4 레거시 데이터 무분별 사용

- `legacy_v12` source의 62개 레코드
- 원본 소스 불명확
- 검증 없이 분석에 사용됨

---

## 5. 연구 결과: FDA 공식 데이터

### 5.1 FDA Drugs@FDA 데이터베이스

**핵심 테이블 구조**:
```
Applications (신청)
├── ApplNo [char](6)        - NDA/BLA 번호 (Primary Key)
├── ApplType [char](5)      - NDA, BLA, ANDA
└── SponsorName [char](500) - 스폰서명

Submissions (제출)
├── ApplNo [char](6)        - 신청 번호 (FK)
├── SubmissionType [char](10) - ORIG, SUPPL
├── SubmissionNo [int]      - 제출 순번
├── SubmissionStatus [char](2) - AP(승인), TA(임시)
└── SubmissionStatusDate    - 상태 날짜
```

**핵심 발견**:
- `ApplNo`로 모든 submission 연결 가능
- 하지만 **CRL 날짜는 DrugsFDA에 없음** (최종 승인만 기록)
- **Resubmission이 별도 레코드로 기록되지 않음**

### 5.2 OpenFDA CRL API (2025년 신규)

**엔드포인트**: `https://api.fda.gov/transparency/crl.json`

**제공 정보**:
```json
{
  "application_number": ["NDA 210730"],
  "letter_date": "11/02/2018",
  "letter_type": "COMPLETE RESPONSE",
  "approval_status": "Approved",
  "company_name": "Company Inc.",
  "text": "... CRL 전문 (결함 사유 포함) ..."
}
```

**현황** (2026-01-09 기준):
- 총 CRL 수: 402개
- 승인됨: 295개 (73%)
- 미승인: 107개 (27%)

**한계**:
- 2025년 7월부터 공개 시작 (역사적 데이터 제한)
- 우리 CRL 케이스 27개 중 대부분 **찾을 수 없음**

### 5.3 ApplNo 수집 가능성 테스트

| 케이스 | 개수 | OpenFDA | 가능 여부 |
|--------|------|---------|-----------|
| **Approved** | 477 | DrugsFDA API | ✅ 100% 가능 |
| **CRL** | 27 | 없음 | ❌ 불가능 |
| **Pending** | 17 | 없음 | ❌ 불가능 |

**테스트 결과**:
```
승인된 약물:
- brand_name 검색: 100% 성공
- generic_name 검색: 100% 성공
- ApplNo 반환됨

CRL 케이스:
- Filgotinib: NOT_FOUND
- Roxadustat: NOT_FOUND
- 전부 NOT_FOUND (DrugsFDA에 없음)
```

**결론**:
- 승인된 477개 → ApplNo 수집 가능
- CRL/Pending 44개 → FDA 공식 데이터로 수집 불가 (SEC 8-K, 회사 PR 필요)

---

## 6. 연구 결과: 데이터 수집 가능성

### 6.1 PDUFA 캘린더 소스

| 소스 | is_resubmission | prior_crl | 비용 |
|------|-----------------|-----------|------|
| **SEC 8-K** | ✅ 명시적 | ✅ CRL 발표 | 무료 |
| **회사 PR** | ✅ 명시적 | ✅ 과거 PR | 무료 |
| **OpenFDA CRL API** | - | ✅ 2025년~ | 무료 |
| **BioPharmCatalyst** | ✅ | ✅ | 무료/유료 |
| **FDA Tracker** | ✅ | ✅ | 무료/유료 |

### 6.2 SEC 8-K에서 수집 가능한 정보

**명시적으로 확인 가능**:
- "NDA/BLA Resubmission Accepted by FDA"
- "PDUFA target action date of [날짜]"
- "Received Complete Response Letter"
- Resubmission Class (1 or 2)

**예시** (실제 8-K 공시):
```
"The Company announced that the FDA has accepted for filing
its BLA resubmission for KRESLADI. The PDUFA target action
date is March 28, 2026."
```

### 6.3 is_resubmission 검증 방법

```
현재: 추론 기반 (신뢰 불가)
┌─────────────────────────────────────┐
│ is_resubmission = derived_from_... │
│ source = "legacy_v12"              │
│ confidence = 0.75                  │
└─────────────────────────────────────┘

개선: SEC 8-K 기반 (검증됨)
┌─────────────────────────────────────┐
│ is_resubmission = True             │
│ source = "sec_8k:2025-10-15"       │
│ evidence = "BLA Resubmission..."   │
│ verified = True                    │
└─────────────────────────────────────┘
```

### 6.4 학술 연구 참고

**MIT 연구 (2019)** - FDA 승인 예측:
- AUC 0.78-0.81 달성
- 중요 예측 변수:
  - 임상시험 결과 (trial outcomes)
  - 시험 상태 (trial status)
  - 스폰서 과거 실적 (sponsor track records)
  - 다른 적응증 사전 승인 여부

**BIO Report (2011-2020)** - Phase별 성공률:
- Phase 1: 54%
- Phase 2: 34% (가장 어려운 단계)
- Phase 3: 70%
- Submission → Launch: 91%

---

## 7. Pending 케이스 분석

### 7.1 Pending의 중요성

```
Pending = 실제 예측 대상
- Approved/CRL = 과거 데이터 (학습용)
- Pending = 미래 예측 (실제 사용 목적)
```

### 7.2 Pending 17개 현황

| 항목 | 상태 | 문제 |
|------|------|------|
| 임상 데이터 | 94-100% 완전 | ✅ |
| is_resubmission | 100% 채움 | ⚠️ 검증 안됨 |
| has_prior_crl | 100% 채움 | ⚠️ 검증 안됨 |
| pai_passed | <5% | ❌ 심각 |
| FDA designations | 35% | ⚠️ 불완전 |

### 7.3 재제출 분포 (Pending)

| 상태 | 개수 | 비율 |
|------|------|------|
| 재제출 (is_resubmission=True) | 10 | 59% |
| 초기 제출 | 7 | 41% |

**해석**: Pending은 CRL 후 재도전하는 케이스가 많음

### 7.4 데이터 오류 발견

| 케이스 | 문제 |
|--------|------|
| ZEAL (Dasiglucagon) | PDUFA 2023-12-30인데 pending. 실제로 2021년 승인됨 |
| UNCY (Oxylanthanum) | PDUFA 2025-06-28 지남 (-196일), 여전히 pending |
| ALDX | primary_endpoint_met=False인데 pending |

### 7.5 예측에 사용 가능한 필드

**Tier 1: 확실히 사용 가능**
- primary_endpoint_met (ClinicalTrials.gov)
- designations (FDA 공식)
- adcom_info (FDA 캘린더)
- indication (회사 PR)

**Tier 2: 검증 후 사용 가능**
- is_resubmission (SEC 8-K로 검증 필요)
- prior_crl_reason (OpenFDA CRL API)

**Tier 3: 수집 어려움**
- pai_passed (FDA 비공개)
- warning_letter (과거 데이터만)
- manufacturing_issues (비공개)

---

## 8. 해결 방향

### 8.1 즉시 조치 (Phase 1)

**데이터 무수정, 코드만 수정**

```python
# from_enriched() 수정
DEPRECATED_FIELDS = ['is_resubmission', 'has_prior_crl', 'prior_history']

def from_enriched(data: dict) -> AnalysisContext:
    # 미신뢰 필드 제외
    prior_crl = None           # 항상 None
    is_resubmission = None     # 항상 None
    crl_history = ()           # 비움

    return AnalysisContext(
        # 신뢰 필드만 사용
        primary_endpoint_met=get_value(data.get("primary_endpoint_met")),
        pai_passed=get_value(data.get("pai_passed")),
        designations=get_designations(data),
        ...
    )
```

### 8.2 단기 조치 (Phase 2)

**SEC 8-K 기반 검증 시스템**

```python
# SEC 8-K 검색 → is_resubmission 확인
def verify_resubmission(ticker: str, drug_name: str) -> SubmissionInfo:
    # 1. SEC EDGAR 검색
    filings = search_sec_8k(ticker, keywords=["resubmission", "NDA", "BLA"])

    # 2. 키워드 추출
    for filing in filings:
        if "resubmission accepted" in filing.text.lower():
            return SubmissionInfo(
                is_resubmission=True,
                source=f"sec_8k:{filing.date}",
                evidence=extract_quote(filing.text),
                verified=True
            )

    return SubmissionInfo(is_resubmission=None, verified=False)
```

### 8.3 중기 조치 (Phase 3)

**OpenFDA CRL API 연동**

```python
# CRL 이력 조회
def get_crl_history(company_name: str, drug_name: str) -> list[CRLRecord]:
    response = openfda_query(f'company_name:"{company_name}"')

    crls = []
    for record in response.results:
        if drug_name.lower() in record.text.lower():
            crls.append(CRLRecord(
                date=parse_date(record.letter_date),
                reason=extract_reason(record.text),
                category=categorize_reason(record.text),  # cmc, efficacy, safety
            ))

    return sorted(crls, key=lambda x: x.date)
```

### 8.4 장기 조치 (Phase 4)

**Application-Centric 모델로 전환**

```python
@dataclass
class Application:
    """FDA 신청 단위 (ApplNo 기준)"""
    appl_no: str                    # NDA212345, BLA761126
    appl_type: str                  # NDA, BLA, ANDA
    drug_name: str
    generic_name: str
    sponsor: str

    timeline: list[TimelineEvent]   # 시간순 이벤트들

@dataclass
class TimelineEvent:
    """타임라인 내 개별 이벤트"""
    date: date
    event_type: EventType           # SUBMISSION, CRL, APPROVAL, WITHDRAWN
    details: dict
```

---

## 9. 구현 계획

### 9.1 로드맵

| 단계 | 작업 | 기간 | 데이터 변경 |
|------|------|------|-------------|
| **Phase 1** | from_enriched() 수정, deprecated 필드 제외 | 1-2일 | ❌ |
| **Phase 1** | 백테스트 재실행 | 1일 | ❌ |
| **Phase 2** | SEC 8-K 검색 모듈 개발 | 1주 | ❌ |
| **Phase 2** | OpenFDA CRL API 연동 | 1주 | ❌ |
| **Phase 3** | 자동 데이터 수집 파이프라인 | 2주 | ✅ 신규만 |
| **Phase 4** | Application-Centric 마이그레이션 | 4주+ | ✅ 전체 |

### 9.2 우선순위

1. **긴급**: from_enriched()에서 deprecated 필드 무시
2. **높음**: 백테스트 재실행으로 실제 정확도 확인
3. **중간**: SEC 8-K 검증 시스템 구축
4. **낮음**: 전체 데이터 모델 재설계

### 9.3 파일 변경 목록

```
수정 예정:
├── src/tickergenius/analysis/pdufa/_context.py
│   └── from_enriched() 수정
│
├── src/tickergenius/analysis/pdufa/_field_validator.py (신규)
│   └── is_field_safe(), UNSAFE_SOURCES 정의
│
└── docs/
    ├── SCHEMA_V2.md (이미 작성됨)
    └── DATASET_ANALYSIS_2026_01_12.md (현재 문서)
```

---

## 10. 핵심 원칙 재확인

### 10.1 데이터 원칙 (CLAUDE.md 기반)

| 원칙 | 현재 위반 | 개선 방향 |
|------|----------|-----------|
| **추론 금지** | derived 값을 found로 저장 | origin=DERIVED → tier 4 |
| **출처 명확** | 199개 empty source | source 필수화 |
| **검증된 데이터만** | legacy 그대로 사용 | legacy → NOT_VERIFIED |

### 10.2 CRL 관련 결론

```
"CRL 카운트는 승인 확률에 영향을 주지 않아야 함"

이유:
1. FDA는 각 제출을 독립적으로 평가
2. 과거 CRL 횟수 ≠ 현재 제출 품질
3. prior_crl 필드 자체가 오염되어 신뢰 불가

결론:
- prior_crl, is_resubmission 필드 → 분석에서 완전 제외
- 향후 수집 시에도 이 필드들은 "참고용"으로만 저장
- 확률 계산에는 사용하지 않음
```

### 10.3 예측에 사용할 필드 최종 확정

**사용 (신뢰)**:
- ✅ primary_endpoint_met
- ✅ pai_passed
- ✅ fda_designations (BTD, PR, FT, OD, AA)
- ✅ adcom_info
- ✅ indication / therapeutic_area

**제외 (미신뢰)**:
- ❌ is_resubmission (legacy 오염)
- ❌ has_prior_crl (is_resubmission에서 파생)
- ❌ prior_history.* (타임라인 데이터 부재)
- ❌ prior_crl_reason (필드명 오류, 실제로는 current)

### 10.4 Tier 시스템 재정의

| Tier | 소스 | 신뢰도 | 분석 사용 |
|------|------|--------|-----------|
| **1** | FDA 공식 (OpenFDA, CDER 목록) | 99% | ✅ |
| **2** | SEC EDGAR, ClinicalTrials.gov | 90% | ✅ |
| **3** | 회사 PR, 뉴스 | 75% | ⚠️ 주의 |
| **4** | 추론, 파생, Legacy | 50% | ❌ 제외 |

---

## 부록 A: 관련 파일 경로

| 항목 | 경로 |
|------|------|
| 메인 분석기 | `src/tickergenius/analysis/pdufa/_analyzer.py` |
| 컨텍스트 | `src/tickergenius/analysis/pdufa/_context.py` |
| 이벤트 로더 | `src/tickergenius/analysis/pdufa/event_loader.py` |
| 핵심 데이터 | `data/enriched/` (523개 파일) |
| 스키마 v2 | `docs/SCHEMA_V2.md` |
| 상태 문서 | `docs/STATUS.md` |
| 품질 리포트 | `docs/DATA_QUALITY_REPORT.md` |

---

## 부록 B: 문제 스크립트 목록 (아카이브됨)

| 스크립트 | 위치 | 문제 |
|----------|------|------|
| `derive_prior_crl.py` | `scripts/_archive/` | 순환 논리로 has_prior_crl 파생 |
| `compute_has_prior_crl.py` | `scripts/_archive/` | 데이터 부재를 False로 가정 |
| `auto_derive_fields.py` | `scripts/_archive/` | derived를 found로 위장 |

---

## 부록 C: FDA API 엔드포인트

| API | 엔드포인트 | 용도 |
|-----|-----------|------|
| DrugsFDA | `https://api.fda.gov/drug/drugsfda.json` | 승인 약물 정보 |
| CRL | `https://api.fda.gov/transparency/crl.json` | CRL 이력 |
| OpenFDA | `https://open.fda.gov/` | 통합 FDA 데이터 |

---

## 부록 D: 용어 정의

| 용어 | 정의 |
|------|------|
| **PDUFA** | Prescription Drug User Fee Act - FDA 심사 목표일 |
| **CRL** | Complete Response Letter - FDA의 추가 요청 (승인 거부 아님) |
| **ApplNo** | FDA Application Number (예: NDA212345) |
| **BTD** | Breakthrough Therapy Designation |
| **PR** | Priority Review |
| **FT** | Fast Track |
| **OD** | Orphan Drug Designation |
| **AA** | Accelerated Approval |
| **AdCom** | Advisory Committee - FDA 자문위원회 |
| **PAI** | Pre-Approval Inspection - 승인 전 시설 검사 |

---

**문서 끝**

*이 문서는 2026-01-12 세션에서 진행된 모든 연구, 토론, 분석 결과를 종합한 것입니다.*
*다음 세션에서 이 문서를 참고하여 구현을 진행하시면 됩니다.*
