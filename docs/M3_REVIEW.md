# M3 구현 검토 및 설계 분석

> **⚠️ SUPERSEDED**: 이 문서는 M3_BLUEPRINT_v2.md로 대체되었습니다.
> - **핵심 변경**: 예측 단위가 "약물"에서 "PDUFA 이벤트"로 변경
> - **참고용**: 팩터 계산 흐름도, 레이어 구조 참조 가능
> - **금지**: CRL 횟수를 승인률 feature로 사용하는 로직

**작성일**: 2026-01-08
**상태**: ~~활성~~ → **SUPERSEDED by M3_BLUEPRINT_v2.md**
**컴팩트 후 재검토**

---

## 페르소나 팀 재검토

### 참여자
- **A (Architect)**: 전체 구조, 확장성
- **B (Data Expert)**: 데이터 검증, 오염 방지
- **C (MCP Specialist)**: 도구 설계, Claude 연동
- **D (Trading Risk)**: 실사용 의사결정
- **E (SRE)**: 운영, 에러 처리

---

## 현재 구현 상태 분석

### 구현된 파일 목록

```
src/tickergenius/
├── data/constants/
│   ├── factor_adjustments.json   # 팩터 점수 (103줄)
│   ├── base_rates.json           # 기본 승인률 (116줄)
│   └── cap_rules.json            # Cap 규칙 (62줄)
│
├── repositories/
│   ├── __init__.py
│   └── constants.py              # JSON 로더 (343줄)
│
└── analysis/
    ├── __init__.py               # Public API 노출
    └── pdufa/
        ├── __init__.py           # Public API
        ├── _context.py           # AnalysisContext (274줄)
        ├── _registry.py          # FactorRegistry (373줄)
        ├── _result.py            # AnalysisResult
        ├── _analyzer.py          # PDUFAAnalyzer Facade
        └── _layers/
            ├── __init__.py       # LAYER_ORDER 정의
            ├── base.py           # 기본 확률 (1개 팩터)
            ├── designation.py    # FDA 지정 (5개 팩터)
            ├── adcom.py          # AdCom (3개 팩터)
            ├── crl.py            # CRL (4개 팩터)
            ├── clinical.py       # 임상 (5개 팩터)
            ├── manufacturing.py  # 제조 (4개 팩터)
            ├── special.py        # 특수 (4개 팩터)
            └── cap.py            # Cap/Floor (7개 팩터)
```

**총 등록 팩터: 33개** (8개 레이어)

---

## 팩터 계산 흐름도

```
┌─────────────────────────────────────────────────────────────────────┐
│  AnalysisContext 생성                                                │
│  (ticker, drug_name, fda_designations, adcom, crl_history,          │
│   clinical, manufacturing, spa_agreed, spa_rescinded, ...)          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: BASE (order=100)                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ base_rate: 기본 승인률 결정                                   │   │
│  │   - biosimilar? → 85%                                        │   │
│  │   - class1 resubmission? → 50%                               │   │
│  │   - class2 resubmission? → 65%                               │   │
│  │   - nda_bla? → 70% (기본값)                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: 0.70 (예시)                                                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: DESIGNATION (order: 10-50)                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ breakthrough_therapy: +8% (if True)                          │   │
│  │ priority_review: +5% (if True)                               │   │
│  │ fast_track: +5% (if True)                                    │   │
│  │ orphan_drug: +4% (if True)                                   │   │
│  │ accelerated_approval: +6% (if True)                          │   │
│  │                                                              │   │
│  │ ⚠️ 문제: 레거시는 max_only 그룹핑 (최대값만)                  │   │
│  │    현재: 모든 팩터 누적 적용 (스택)                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: 0.70 + 0.08 + 0.05 = 0.83 (모두 적용 시)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: ADCOM (order: 10-30)                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ adcom_vote_positive: +8% (vote_ratio > 0.5)                  │   │
│  │ adcom_vote_negative: -20% (0 < vote_ratio <= 0.5)            │   │
│  │ adcom_waived: +4% (waived)                                   │   │
│  │                                                              │   │
│  │ ✅ OK: 상호 배타적 (한 번에 하나만 적용)                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: prev ± adjustment                                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4: CRL (order: 10-40)                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ crl_class1_bonus: +9% (class1 resubmission)                  │   │
│  │ crl_class2_bonus: +8% (class2 resubmission)                  │   │
│  │ new_app_got_crl: -20% (has prior CRL, not resubmission)      │   │
│  │ is_resubmission: -9.1% (base penalty)                        │   │
│  │                                                              │   │
│  │ ⚠️ 문제: class1_bonus + is_resubmission 동시 적용?           │   │
│  │    현재: 둘 다 적용됨 (+9% - 9.1% ≈ 0)                       │   │
│  │    의도: class bonus가 base penalty 상쇄?                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: prev + adjustments                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 5: CLINICAL (order: 10-50)                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ primary_endpoint_not_met: -70% (catastrophic)                │   │
│  │ single_arm_trial: -7%                                        │   │
│  │ rwe_external_control: -15%                                   │   │
│  │ trial_region_china_only: -50% (critical)                     │   │
│  │ clinical_hold_history: -8%                                   │   │
│  │                                                              │   │
│  │ ⚠️ 문제: single_arm + rwe_external_control 동시 가능?        │   │
│  │    현재: 둘 다 적용되면 -22% 누적                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: prev - penalties                                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 6: MANUFACTURING (order: 10-40)                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ facility_pai_passed: +12%                                    │   │
│  │ facility_warning_letter: -30% (severe cap trigger)           │   │
│  │ fda_483_observations: -5%/-10%/-10% (by severity)            │   │
│  │ cdmo_high_risk: -8%                                          │   │
│  │                                                              │   │
│  │ ⚠️ 문제: pai_passed + warning_letter 동시 가능?              │   │
│  │    현재: 둘 다 적용되면 +12% - 30% = -18%                    │   │
│  │    실제: PAI 통과 후 별도 Warning Letter는 드묾              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: prev ± adjustments                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 7: SPECIAL (order: 10-40)                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ first_in_class: +5%                                          │   │
│  │ supplement_application: +5%                                   │   │
│  │ spa_agreed: +8%                                              │   │
│  │ spa_rescinded: -30%                                          │   │
│  │                                                              │   │
│  │ ✅ OK: spa_agreed 적용 시 spa_rescinded 체크됨               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: prev + bonuses                                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 8: CAP (order: 10-100)                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ hard_cap_catastrophic: max 5% (primary_endpoint_not_met)     │   │
│  │ hard_cap_critical: max 15% (china_only)                      │   │
│  │ hard_cap_severe: max 25% (warning_letter)                    │   │
│  │ hard_cap_moderate: max 40% (adcom_negative)                  │   │
│  │ floor_fda_designation: min 15% (has any designation)         │   │
│  │ floor_spa_agreed: min 20% (spa agreed)                       │   │
│  │ probability_bounds: 10%-90% (final clamp)                    │   │
│  │                                                              │   │
│  │ ✅ 수정됨: catastrophic cap이 floor보다 우선                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  OUTPUT: clamped probability                                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  최종 결과: AnalysisResult                                          │
│  - probability: 0.72                                                │
│  - base_probability: 0.70                                           │
│  - factors: [FactorResult, ...]                                     │
│  - layers: [LayerSummary, ...]                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 페르소나 팀 검토 토론

### A (Architect): 구조 검토

**발견된 문제점:**

1. **팩터 그룹핑 미구현**
   ```
   레거시: FDA 지정은 max_only (최대값만 적용)
   현재: 모든 FDA 지정 누적 적용

   영향: BTD+Priority+Orphan = +17% (현재)
   레거시: BTD만 = +8% (max_only)

   차이: +9% 과대평가 가능
   ```

2. **컨텍스트 상호작용 미구현**
   ```
   레거시: 특정 조합 시 페널티 감소
   예: BTD + Orphan + First-in-Class → 페널티 75% 감소

   현재: 이 로직 없음
   ```

3. **레이어 순서 문제**
   ```
   현재 LAYER_ORDER:
   ["base", "designation", "adcom", "crl",
    "clinical", "manufacturing", "special", "context", "cap"]

   "context" 레이어 미구현됨!
   ```

### B (Data): 데이터 검토

**발견된 문제점:**

1. **팩터 점수 출처 불명확**
   ```json
   // factor_adjustments.json
   "breakthrough_therapy": {
     "score": 0.08,
     "verification_status": "UNKNOWN"  // 모두 UNKNOWN!
   }
   ```

2. **base_rates와 factor_adjustments 중복**
   ```
   base_rates.json: resubmission.class1 = 0.50
   factor_adjustments.json: class1_resubmission = +0.09

   의도: 50% 기본 + 9% 보너스 = 59%?
   또는: 둘 중 하나만 사용?
   ```

3. **레거시 v12 데이터와 매핑 부재**
   ```
   레거시 필드 103개 중 현재 매핑된 것:
   - fda_designations: 6개 중 5개 ✓
   - adcom: 6개 중 3개 △
   - crl: 12개 중 4개 △
   - manufacturing: 16개 중 4개 △
   - clinical: 22개 중 5개 △

   누락: mental_health_type, dispute_result,
         earnings_call_signals, citizen_petition, etc.
   ```

### C (MCP): API 검토

**발견된 문제점:**

1. **Pipeline 연동 미완성**
   ```python
   # _context.py:from_pipeline()
   fda_designations = FDADesignations()  # 빈 객체!
   # TODO: Pipeline에서 FDA 지정 추출 로직 필요
   ```

2. **explain 기능 부재**
   ```
   사용자: "왜 72%야?"
   현재: result.summary() 있지만 MCP 도구 미구현
   ```

### D (Trading): 실사용 검토

**발견된 문제점:**

1. **타이밍 신호 미구현**
   ```python
   # AnalysisResult에 없음:
   timing_signal: TimingSignal  # BUY/HOLD/SELL
   signal_reasons: list[str]
   ```

2. **리스크 레벨 미구현**
   ```python
   # AnalysisResult에 없음:
   risk_level: str  # LOW/MEDIUM/HIGH
   risk_factors: list[str]
   ```

3. **confidence_score 계산 로직 없음**
   ```python
   # _result.py
   confidence_score: float = 1.0  # 항상 1.0 고정
   # 실제: 데이터 품질에 따라 변해야 함
   ```

### E (SRE): 운영 검토

**발견된 문제점:**

1. **로깅 부족**
   ```python
   # 현재: logger.info/debug만 있음
   # 필요: 구조화된 로깅 (JSON format)
   ```

2. **에러 복구 미흡**
   ```python
   # _registry.py:apply_layer()
   except Exception as e:
       logger.error(f"Error applying factor '{factor.name}': {e}")
       results.append(FactorResult.neutral(factor.name, f"Error: {e}"))
   # 에러 발생해도 계속 진행 - 좋음
   # 하지만 에러 카운트, 알림 없음
   ```

3. **메트릭 수집 없음**
   ```
   필요:
   - 분석 소요 시간
   - 팩터별 적용 빈도
   - 에러 빈도
   ```

---

## 우선순위별 개선 목록

### P0 (Critical - 계산 정확도 영향)

| # | 문제 | 해결책 | 영향 |
|---|------|--------|------|
| 1 | FDA 지정 그룹핑 없음 | max_only 로직 추가 | 최대 +9% 오차 |
| 2 | CRL bonus/penalty 중복 | 로직 명확화 | 재제출 계산 오류 |
| 3 | context 레이어 미구현 | 상호작용 로직 추가 | 복합 조건 미반영 |

### P1 (High - 기능 누락)

| # | 문제 | 해결책 |
|---|------|--------|
| 4 | Pipeline 연동 미완성 | from_pipeline() 보완 |
| 5 | 누락 팩터들 | mental_health, dispute, earnings 등 |
| 6 | timing_signal 없음 | TimingAnalyzer 구현 |

### P2 (Medium - 품질)

| # | 문제 | 해결책 |
|---|------|--------|
| 7 | confidence_score 고정 | 데이터 품질 기반 계산 |
| 8 | 검증 상태 모두 UNKNOWN | 점진적 검증 |
| 9 | 로깅/메트릭 부족 | 구조화된 로깅 추가 |

---

## 개선된 설계 제안

### 1. 팩터 그룹 처리 (P0)

```python
# _registry.py에 추가

class FactorGroup(str, Enum):
    """팩터 그룹 유형."""
    INDEPENDENT = "independent"    # 독립 (모두 적용)
    EXCLUSIVE = "exclusive"        # 배타적 (첫 번째만)
    MAX_ONLY = "max_only"          # 최대값만

@dataclass
class FactorInfo:
    # ... 기존 필드 ...
    group: Optional[str] = None    # 그룹 이름
    group_type: FactorGroup = FactorGroup.INDEPENDENT

# 등록 예시
@FactorRegistry.register(
    name="breakthrough_therapy",
    layer="designation",
    order=10,
    group="fda_designation",       # 그룹 지정
    group_type=FactorGroup.MAX_ONLY,  # 최대값만
)
def apply_btd_bonus(...):
    ...
```

### 2. 컨텍스트 상호작용 레이어 (P0)

```python
# _layers/context.py (신규)

CONTEXT_INTERACTIONS = {
    "strong_designation_combo": {
        "conditions": ["breakthrough_therapy", "orphan_drug", "first_in_class"],
        "min_count": 3,
        "effect": "penalty_reduction",
        "value": 0.75,  # 페널티 75% 감소
    },
    "clinical_support": {
        "conditions": ["spa_agreed", "adcom_vote_positive"],
        "min_count": 2,
        "effect": "bonus",
        "value": 0.05,  # 추가 5% 보너스
    },
}

@FactorRegistry.register(
    name="context_interaction",
    layer="context",
    order=10,
)
def apply_context_interaction(ctx: AnalysisContext, current_prob: float) -> FactorResult:
    """팩터 조합에 따른 상호작용 효과."""
    ...
```

### 3. 개선된 레이어 순서

```python
# _layers/__init__.py

LAYER_ORDER = [
    "base",           # 1. 기본 확률
    "designation",    # 2. FDA 지정 (max_only 그룹)
    "adcom",          # 3. AdCom (exclusive)
    "crl",            # 4. CRL
    "clinical",       # 5. 임상
    "manufacturing",  # 6. 제조
    "special",        # 7. 특수
    "context",        # 8. 상호작용 ← 추가
    "cap",            # 9. Cap/Floor
]
```

---

## 진행 상황 (2026-01-08 업데이트)

### 완료된 작업

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 1 | 팩터 그룹핑 (MAX_ONLY) | ✅ 완료 | FDA 지정 최대값만 적용 |
| 2 | context interaction 레이어 | ✅ 완료 | 3개 상호작용 정의 |
| 3 | 데이터 오염 플래그 | ✅ 완료 | class1=50% 문제 기록 |
| 4 | 누락 팩터 추가 | ✅ 완료 | temporal, mental_health |
| 5 | confidence_score 계산 | ✅ 완료 | 데이터 품질 기반 |

### 추가된 기능

1. **Temporal-aware 팩터**
   - Warning Letter: 오래된 것(>365일) 50% 감소, PAI 후 발생 시 25% 증가
   - FDA 483: 오래된 것 감소, 날짜 표시
   - AnalysisContext에 이벤트 일자 필드 추가

2. **Mental Health 팩터**
   - MDD, PTSD, Anxiety 등 적응증별 플라시보 반응 페널티
   - ClinicalInfo에 is_mental_health, mental_health_type 추가

3. **Confidence Score**
   - 데이터 완전성 (40%)
   - 데이터 최신성 (30%)
   - 팩터 신뢰도 (30%)
   - 0.1-1.0 범위로 정규화

### 테스트 현황

- 총 27개 테스트 통과
- TestTemporalFactors: 2개
- TestConfidenceScore: 3개

---

## 다음 단계

1. ~~**P0 이슈 수정**~~ ✅ 완료
2. **데이터셋 구축** - v12 기반 600건 티커별 검증 (별도 작업)
3. **누락 팩터 확장** - dispute_result, citizen_petition, earnings_call 등
4. **MCP 도구 연동** - explain, scenario 분석
5. **통합 테스트 강화** - 실제 사례 기반 테스트
