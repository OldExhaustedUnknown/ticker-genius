# M3 청사진 v2: PDUFA 이벤트 기반 CRL 예측

**작성일**: 2026-01-09
**버전**: 2.1
**상태**: 구현 진행 중 (Phase 1-2 완료)
**최종 수정**: 2026-01-09

---

## 핵심 관점 전환

### 기존 (v1) vs 신규 (v2)

| 구분 | v1 (기존) | v2 (신규) |
|------|-----------|-----------|
| **케이스 단위** | 약물 (ticker + drug_name) | PDUFA 이벤트 (ticker + drug + pdufa_date) |
| **예측 목표** | 최종 승인 확률 | 각 PDUFA에서 CRL 발생 확률 |
| **CRL 횟수** | 승인률에 반영 (feature) | 독립 사건, feature 제외 |
| **학습 데이터** | 523건 (약물 단위) | ~650건 (이벤트 단위) |

### 핵심 원칙

```
1. 각 PDUFA 이벤트는 독립 사건
   - 이전 CRL 횟수 ≠ 이번 승인 확률에 영향
   - 각 제출은 해당 시점의 feature로만 평가

2. 예측 목표 = CRL 발생 여부
   - P(CRL) 예측 → 리스크 판단
   - CRL 전에 미리 포착하는 것이 목적

3. 주가 영향과 승인 확률은 분리
   - CRL 횟수 → 주가에 영향 (심리적)
   - CRL 횟수 → 승인 확률에 무관 (FDA 독립 심사)
```

---

## 데이터 모델

### PDUFAEvent (신규)

```python
@dataclass
class PDUFAEvent:
    """단일 PDUFA 이벤트 (예측 단위)."""

    # 식별자
    event_id: str              # hash(ticker + drug + pdufa_date)
    ticker: str
    drug_name: str
    pdufa_date: str            # YYYYMMDD

    # 타겟 변수
    result: str                # "approved", "crl", "pending"

    # 제출 컨텍스트
    submission_type: str       # "original", "resubmission"
    sequence_number: int       # 1, 2, 3... (몇 번째 제출)
    prior_crl_reason: str      # 이전 CRL 사유 (재제출 시)
    issues_addressed: bool     # 이전 이슈 해결 여부

    # FDA 지정 (해당 시점 기준)
    btd: Optional[FieldValue]
    priority_review: Optional[FieldValue]
    fast_track: Optional[FieldValue]
    orphan_drug: Optional[FieldValue]
    accelerated_approval: Optional[FieldValue]

    # 임상 (해당 시점 기준)
    primary_endpoint_met: Optional[FieldValue]
    phase: Optional[FieldValue]
    nct_id: Optional[FieldValue]

    # AdCom (해당 PDUFA 전)
    adcom_held: Optional[FieldValue]
    adcom_date: Optional[FieldValue]
    adcom_vote_ratio: Optional[FieldValue]

    # 제조 (해당 시점 기준)
    pai_passed: Optional[FieldValue]
    warning_letter_active: Optional[FieldValue]

    # 메타데이터
    collected_at: datetime
    data_quality_score: float  # 0-1
```

### 저장 구조

```
data/
├── collected/                 # 기존 (유지)
│   ├── raw/
│   └── processed/
│
├── events/                    # 신규
│   ├── by_event/              # 이벤트 단위 파일
│   │   ├── axsm_axs05_20210108.json
│   │   ├── axsm_axs05_20210824.json
│   │   └── axsm_axs05_20220819.json
│   │
│   ├── by_drug/               # 약물별 이벤트 목록
│   │   └── axsm_axs05.json    # [event_ids...]
│   │
│   └── manifest.json          # 전체 이벤트 현황
│
└── pipelines/                 # 기존 (유지)
```

---

## Feature 설계

### 예측에 사용되는 Feature

```yaml
# 핵심 Feature (예측력 높음)
critical_features:
  - primary_endpoint_met      # 1차 평가변수 충족 (가장 중요)
  - adcom_vote_ratio          # AdCom 투표 결과
  - safety_signals            # 안전성 우려
  - pai_passed                # PAI 통과 여부

# 주요 Feature (예측력 중간)
major_features:
  - btd                       # BTD 지정
  - priority_review           # 우선심사
  - warning_letter_active     # Warning Letter 활성
  - phase                     # 임상 단계

# 보조 Feature (컨텍스트)
auxiliary_features:
  - indication_category       # 적응증 분류
  - first_in_class            # 최초 기전
  - orphan_drug               # 희귀의약품
  - fast_track                # Fast Track

# 제외 Feature (독립 사건 원칙)
excluded_features:
  - prior_crl_count           # 이전 CRL 횟수
  - days_since_first_crl      # 첫 CRL 이후 경과일
  - total_review_time         # 총 심사 기간
```

### CRL 사유 분류 (재제출 시 참고)

```yaml
crl_reason_categories:
  clinical:
    - endpoint_not_met
    - insufficient_efficacy
    - safety_concern
    - subgroup_analysis_issue

  manufacturing:
    - cmc_deficiency
    - facility_issue
    - stability_data
    - supply_chain

  regulatory:
    - labeling_issue
    - rems_required
    - additional_study_needed
    - postmarket_commitment

# 재제출 시 사용
resubmission_features:
  - prior_crl_reason_category   # 어떤 사유였는지
  - issues_addressed            # 해결됐는지 (boolean)
  # 주의: 이것은 "이번 제출의 품질"을 나타내는 feature
  #       "과거에 몇 번 CRL 받았는지"와 다름
```

---

## 시스템 아키텍처

### 유지되는 컴포넌트

```
[유지] API 클라이언트
├── OpenFDAClient          # FDA 승인 정보
├── SECEdgarClient         # SEC 공시 검색
├── ClinicalTrialsClient   # 임상시험 정보
└── DesignationSearchClient # SEC 8-K 본문 검색

[유지] 검증 시스템
├── VerificationRunner     # 검증 실행
├── DataContaminationGuard # 오염 방지
└── SourceTier             # 소스 신뢰도

[유지] 분석 레이어
├── FactorRegistry         # 팩터 등록
├── Layer System           # 8개 레이어
└── Cap/Floor 규칙         # 확률 제한
```

### 추가되는 컴포넌트

```
[신규] 이벤트 처리
├── EventExtractor         # 약물 → 이벤트 추출
│   ├── extract_from_drug()
│   └── search_prior_crl_events()
│
├── EventStore             # 이벤트 저장소
│   ├── save_event()
│   ├── load_event()
│   └── list_by_drug()
│
└── CRLSearchClient        # CRL 검색 (SEC 8-K 확장)
    └── search_crl_events()

[신규] 예측 인터페이스
├── PDUFAPredictor         # CRL 예측
│   ├── predict_crl(event)
│   └── explain_prediction()
│
└── RiskClassifier         # 리스크 분류
    └── classify_risk(prediction)
```

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 약물 데이터 수집 (기존)                                      │
│     OpenFDA, SEC, CT → collected/processed/*.json               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 이벤트 추출 (신규)                                           │
│     EventExtractor                                               │
│     - 최종 PDUFA 이벤트 생성                                     │
│     - SEC 8-K에서 과거 CRL 검색                                  │
│     - 과거 PDUFA 이벤트 생성                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 이벤트별 Feature 계산 (신규)                                 │
│     각 PDUFA 시점 기준으로:                                      │
│     - FDA 지정 상태                                             │
│     - 임상 결과                                                  │
│     - AdCom 결과                                                │
│     - 제조 상태                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CRL 예측 (수정)                                              │
│     PDUFAPredictor.predict_crl(event)                           │
│     - Rule-based screening (극단 케이스)                        │
│     - ML 모델 (불확실 케이스)                                    │
│     → P(CRL), risk_level, factors                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 구현 계획

### Phase 1: 데이터 모델 확장

```
작업:
1. PDUFAEvent 클래스 정의 (models.py)
2. EventStore 구현 (event_store.py)
3. 저장 구조 생성 (data/events/)

결과물:
- PDUFAEvent dataclass
- save_event(), load_event(), list_events() 함수
- events/ 디렉토리 구조
```

### Phase 2: 이벤트 추출기

```
작업:
1. EventExtractor 구현
2. CRL 검색 로직 (SEC 8-K → 웹서치 → 뉴스)
3. 과거 CRL 날짜 검색 체인

⚠️ 추론 금지 원칙:
- 검색으로 못 찾으면 NOT_FOUND로 기록
- 절대 날짜를 역산/추측하지 않음
- 없으면 없는 대로 기록

결과물:
- extract_events_from_drug() 함수
- search_crl_events() 메서드 (다중 소스 폴백)
- 검색된 CRL만 이벤트 생성 (추론 이벤트 없음)
```

### Phase 3: Feature 재계산

```
작업:
1. 이벤트별 시점 기준 feature 계산
2. 검증 상태 업데이트
3. 데이터 품질 점수 계산

결과물:
- 각 이벤트의 feature 값 (시점 기준)
- data_quality_score 계산
- 검증 현황 리포트
```

### Phase 4: 예측 모듈 연동

```
작업:
1. PDUFAPredictor 구현
2. 기존 레이어 시스템과 연동
3. RiskClassifier 구현

결과물:
- predict_crl() → P(CRL), confidence
- explain_prediction() → factors
- classify_risk() → HIGH/ELEVATED/MODERATE/LOW
```

---

## 데이터 품질 목표

### 이벤트 수 목표

| 구분 | 예상 건수 |
|------|----------|
| 기존 약물 케이스 | 523건 |
| 추출된 과거 CRL 이벤트 | +100~150건 |
| **총 PDUFA 이벤트** | **~650건** |

### 필드 완성률 목표

| 필드 | 목표 | 비고 |
|------|------|------|
| event_id, ticker, drug_name, pdufa_date | 100% | 필수 |
| result | 100% | 필수 (pending 허용) |
| btd, priority_review, orphan_drug | 95% | FDA 공식 소스 |
| primary_endpoint_met | 80% | 임상시험 결과 |
| adcom_vote_ratio | 100% (있는 경우) | FDA Calendar |
| crl_reason (CRL 시) | 70% | SEC 8-K 추출 |

### 필드 상태 원칙

```
모든 필드는 다음 5가지 상태 중 하나:

1. FOUND - 값 있음 (출처 포함)
   예: btd=True, source="fda_btd_list"

2. CONFIRMED_NONE - 공식 소스에서 없음 확인 (재시도 불필요)
   예: FDA 공식 목록에서 해당 약물 BTD 없음 확인

3. NOT_APPLICABLE - 해당 케이스에 적용 안됨 (재시도 불필요)
   예: original submission인데 prior_crl_reason 필드

4. NOT_FOUND - 검색했지만 못 찾음 (재시도 필요)
   예: SEC에서 못 찾음 → 웹서치 시도해야 함

5. NOT_SEARCHED - 아직 검색 안함 (재시도 필요)
   예: 초기 상태

금지:
- NOT_FOUND/NOT_SEARCHED 상태로 장기 방치
- 추론으로 값 채우기 (절대 금지)
- "못 찾음"과 "없음 확인"을 혼동
```

---

## 기존 코드와의 유기적 연결

### 재사용 코드

| 모듈 | 파일 | 재사용 방식 |
|------|------|------------|
| API 클라이언트 | api_clients.py | 그대로 사용 |
| 검증 러너 | verification_runner.py | 확장하여 사용 |
| 소스 티어 | source_tier.py | 그대로 사용 |
| 팩터 레지스트리 | _registry.py | 그대로 사용 |
| 레이어 시스템 | _layers/*.py | 입력만 변경 |

### 수정 필요 코드

| 모듈 | 파일 | 수정 내용 |
|------|------|----------|
| 데이터 모델 | models.py | PDUFAEvent 클래스 추가 |
| 분석 컨텍스트 | _context.py | 이벤트 단위 입력 지원 |
| 결과 객체 | _result.py | CRL 확률 필드 추가 |

### 신규 코드

| 모듈 | 파일 | 설명 | 상태 |
|------|------|------|------|
| 이벤트 추출 | event_extractor.py | 약물 → 이벤트 변환 | ✅ 완료 |
| 이벤트 저장 | event_store.py | 이벤트 CRUD | ✅ 완료 |
| 이벤트 모델 | event_models.py | PDUFAEvent 클래스 | ✅ 완료 |
| 검색 유틸 | search_utils.py | 쿼리 빌더, 검증기 | ✅ 완료 |
| 웹 검색 | web_search.py | DuckDuckGo 기반 검색 | ✅ 완료 |
| 검색 체인 | search_chain.py | API→웹서치 폴백 오케스트레이터 | ✅ 완료 |
| CRL 예측 | predictor.py | 예측 인터페이스 | ⏳ 대기 |

> 상세 설계: [SEARCH_IMPROVEMENT_DESIGN.md](SEARCH_IMPROVEMENT_DESIGN.md)

---

## 검증 체크리스트

### 모델 검증

- [ ] 각 PDUFA 이벤트가 독립적으로 저장되는가?
- [ ] prior_crl_count가 예측 feature에서 제외되었는가?
- [ ] 시점 기준 feature가 올바르게 계산되는가?

### 데이터 검증

- [ ] 모든 이벤트에 필수 필드가 있는가?
- [ ] 빈 필드 없이 상태가 명시되어 있는가?
- [ ] 과거 CRL 이벤트가 올바르게 추출되었는가?

### 시스템 검증

- [ ] 기존 API 클라이언트가 정상 작동하는가?
- [ ] 기존 검증 시스템이 이벤트에도 적용되는가?
- [ ] 기존 레이어 시스템이 이벤트 입력을 처리하는가?

---

---

## 스파게티 방지 가이드

### 원칙 1: 단일 책임

```
각 모듈은 하나의 명확한 책임만 가짐:

event_extractor.py  → 약물 → 이벤트 변환만
event_store.py      → 이벤트 CRUD만
predictor.py        → CRL 예측만
api_clients.py      → 외부 API 호출만

금지:
- event_extractor에서 직접 예측하기
- predictor에서 직접 API 호출하기
- 한 함수에서 3개 이상의 외부 의존성
```

### 원칙 2: 명확한 경계

```
데이터 흐름 방향:

[수집 계층]
    │
    ▼ (DTO: CollectedCase)
[이벤트 계층]
    │
    ▼ (DTO: PDUFAEvent)
[분석 계층]
    │
    ▼ (DTO: AnalysisContext)
[예측 계층]
    │
    ▼ (DTO: PDUFAPrediction)

규칙:
- 상위 계층은 하위 계층을 알지 못함
- 계층 간 통신은 DTO로만
- 직접 import 금지 (인터페이스 통해서만)
```

### 원칙 3: 점진적 구현

```
각 Phase 완료 후 체크포인트:

Phase 1 완료 체크:
□ PDUFAEvent 클래스가 독립적으로 테스트 가능한가?
□ EventStore가 기존 코드에 영향 없이 동작하는가?
□ 기존 테스트가 모두 통과하는가?

Phase 2 완료 체크:
□ EventExtractor가 이벤트를 올바르게 추출하는가?
□ 기존 API 클라이언트 수정 없이 확장됐는가?
□ CRL 검색이 기존 검색 로직과 충돌 없는가?

실패 시:
- 해당 Phase 롤백
- 문제 원인 분석
- 설계 재검토 후 재시도
```

### 원칙 4: 환각 방지

```
문서 참조 우선순위:
1. M3_BLUEPRINT_v2.md (이 문서) - 최신, 권위
2. DATA_COLLECTION_DESIGN.md - 수집 파이프라인 (부분 유효)
3. M3_PLAN.md - SUPERSEDED, 레이어 구조만 참조
4. M3_REVIEW.md - SUPERSEDED, 팩터 흐름도만 참조

금지:
- SUPERSEDED 문서의 데이터 모델 사용
- SUPERSEDED 문서의 예측 방식 사용
- 문서 없이 "기존에 이랬던 것 같다" 추측

권장:
- 코드 구현 전 이 문서 해당 섹션 재확인
- 불명확하면 문서 업데이트 먼저
- 문서와 코드 불일치 시 문서 우선
```

### 원칙 5: 테스트 우선

```
새 코드 작성 순서:
1. 테스트 케이스 작성
2. 인터페이스 정의
3. 구현
4. 테스트 통과 확인
5. 통합 테스트

테스트 커버리지 요구:
- 새 클래스: 최소 3개 테스트
- 새 함수: 최소 2개 테스트 (정상/예외)
- 버그 수정: 해당 버그 재현 테스트 필수
```

---

## 참고

- 이 문서는 페르소나 토론 3회를 거쳐 합의된 내용입니다.
- v1 대비 핵심 변경점: 예측 단위를 "약물"에서 "PDUFA 이벤트"로 전환
- 기존 구현의 대부분(API 클라이언트, 레이어 시스템)은 유지됩니다.
- 기존 문서(M3_PLAN.md, M3_REVIEW.md)는 SUPERSEDED 상태입니다.
