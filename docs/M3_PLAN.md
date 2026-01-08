# M3: PDUFA 분석 모듈 상세 계획

**작성일**: 2026-01-08
**레거시 분석 기반**

---

## 레거시 분석 결과

### 문제점
```
D:\Stock\modules\pdufa_analyzer.py
├── 3000줄+ 모놀리스 파일
├── PDUFAAnalyzer (line 81)
├── ApprovalProbabilityModel (line 1416)
└── BinaryRiskCalculator (line 2991)

D:\Stock\modules\pdufa\
├── analyzer.py      # lazy import Facade (순환 의존성 회피용)
├── probability.py   # lazy import Facade
├── enums.py         # → M1에서 이미 포팅 완료
└── models.py
```

**핵심 문제**: 순환 의존성으로 인한 lazy import 남발, 테스트 어려움

---

## 신규 구조 설계

```
src/tickergenius/analysis/pdufa/
├── __init__.py         # Public API
├── constants.py        # 검증된 통계 상수 (GREEN)
├── probability.py      # 확률 계산 모델 (YELLOW)
├── factors.py          # 조정 요인들 (YELLOW)
├── crl.py              # CRL 분석 (YELLOW)
└── analyzer.py         # PDUFAAnalyzer Facade (YELLOW)
```

---

## 파일별 포팅 명세

### 1. constants.py (GREEN - 그대로 포팅)

**소스**: `pdufa_analyzer.py:1472-1565`

```python
# 포팅 대상 상수
BASE_APPROVAL_RATES = {
    "phase1": 0.14,
    "phase2": 0.21,
    "phase3": 0.59,
    "nda_bla": 0.70,
    "resubmission": 0.619,
    "class1_resubmission": 0.50,
    "class2_resubmission": 0.6506,
    ...
}

PHASE_PROBABILITY_CAPS = {...}
CRL_TYPE_ADJUSTMENTS = {...}
CRL_DELAY_ADJUSTMENTS = {...}
BIOSIMILAR_FACTORS = {...}

# probability.py에서 분리
CLASS1_APPROVAL_RATE = 0.857
CLASS1_CMC_ONLY_RATE = 1.0
CLASS2_APPROVAL_RATE = 0.673
ADCOM_POSITIVE_APPROVAL_RATE = 0.966
...
```

### 2. probability.py (YELLOW - 리팩터링)

**소스**: `pdufa_analyzer.py:1416-2990` (ApprovalProbabilityModel)

```python
from tickergenius.schemas import ApprovalProbability, Pipeline
from .constants import BASE_APPROVAL_RATES, PHASE_PROBABILITY_CAPS

class ProbabilityCalculator:
    """FDA 승인확률 계산기 (ApprovalProbabilityModel 포팅)"""

    def calculate(self, features: dict) -> ApprovalProbability:
        """
        확률 계산 → Pydantic 스키마 반환
        """
        base = self._get_base_rate(features)
        adjusted = self._apply_factors(base, features)
        capped = self._apply_cap(adjusted, features)

        return ApprovalProbability(
            base_probability=base,
            adjusted_probability=capped,
            confidence_level=self._calc_confidence(features),
            factors=self._extract_factors(features),
        )
```

**핵심 메서드 포팅**:
- `calculate_probability()` → `calculate()`
- `_get_base_rate()`
- `_apply_factors()`
- `_apply_cap()`

### 3. factors.py (YELLOW)

**소스**: `pdufa_analyzer.py` 내 팩터 적용 로직

```python
# FDA 지정 팩터
FDA_DESIGNATION_FACTORS = {
    "breakthrough_therapy": +0.08,
    "priority_review": +0.05,
    "orphan_drug": +0.04,
    "fast_track": +0.03,
    "accelerated_approval": +0.06,
}

# AdCom 팩터
ADCOM_FACTORS = {
    "positive_vote": +0.10,  # 96.6% 승인
    "negative_vote": -0.25,  # 33.3% 승인
}

def apply_fda_designation(base: float, features: dict) -> float:
    """FDA 지정 보너스 적용"""
    ...

def apply_adcom_result(base: float, adcom_result: str) -> float:
    """AdCom 결과 조정"""
    ...
```

### 4. crl.py (YELLOW)

**소스**: `pdufa_analyzer.py:1544-1565` (CRL 조정)

```python
from tickergenius.schemas.enums import CRLType, CRLDelayCategory

def calculate_crl_adjustment(
    crl_type: CRLType,
    delay_category: CRLDelayCategory,
    is_cmc_only: bool = False
) -> float:
    """CRL 유형 및 지연 기간에 따른 확률 조정"""
    ...

def analyze_crl_history(crl_list: list) -> dict:
    """CRL 이력 분석"""
    ...
```

### 5. analyzer.py (YELLOW - Facade)

**소스**: `pdufa_analyzer.py:81-1415` (PDUFAAnalyzer)

```python
from tickergenius.schemas import Pipeline, ApprovalProbability
from .probability import ProbabilityCalculator
from .factors import apply_fda_designation
from .crl import calculate_crl_adjustment

class PDUFAAnalyzer:
    """PDUFA 분석 Facade"""

    def __init__(self, data_provider=None):
        self.calculator = ProbabilityCalculator()
        self.data_provider = data_provider

    def analyze(self, ticker: str) -> Pipeline:
        """
        티커 분석 → Pipeline 스키마 반환
        """
        # 1. 데이터 수집
        # 2. 피처 추출
        # 3. 확률 계산
        # 4. Pipeline 생성 및 반환
        ...
```

---

## 의존성

```
M1 (schemas)  ──┐
                ├──► M3 (pdufa)
M2 (core)     ──┘
```

- `Pipeline`, `ApprovalProbability` from M1
- `CRLType`, `CRLDelayCategory` from M1 enums
- `Config`, `DataProvider` from M2

---

## DoD 체크리스트

```
□ constants.py 작성 (검증된 통계)
□ probability.py 작성 (ProbabilityCalculator)
□ factors.py 작성 (팩터 적용)
□ crl.py 작성 (CRL 분석)
□ analyzer.py 작성 (PDUFAAnalyzer Facade)
□ __init__.py Public API 노출
□ Import 테스트 통과
□ 레거시 확률과 ±0.05 일치 검증
□ Git 커밋 + 태그 (M3-complete)
□ STATUS.md 업데이트
```

---

## 검증 방법

```python
# 레거시와 비교 테스트
legacy_prob = 0.72  # 레거시 결과
new_prob = analyzer.analyze("TICKER").get_probability()
assert abs(legacy_prob - new_prob) <= 0.05
```

---

## 구현 순서

1. constants.py (상수 분리) - 30분
2. factors.py (팩터 로직) - 30분
3. crl.py (CRL 분석) - 30분
4. probability.py (확률 계산) - 1시간
5. analyzer.py (Facade) - 1시간
6. 테스트 및 검증 - 1시간

---

**M3 진행 승인 대기 중**
