# M3: PDUFA 분석 모듈 상세 계획

**작성일**: 2026-01-08
**레거시 분석 기반**

---

## ⚠️ 핵심 원칙

> **리빌딩 이유**: 레거시 데이터셋이 오염되어 있음. 상수/확률 값을 무조건 신뢰하면 안 됨.

1. **레거시 상수 = 참조용**. 그대로 복사 금지.
2. **모든 통계는 원본 소스에서 재검증** 필요.
3. **검증되지 않은 값은 UNKNOWN 상태**로 처리.

---

## 대용량 파일 처리 전략

**문제**: `pdufa_analyzer.py` = 53K 토큰 (읽기 한도 초과)

**해결책**:
```
1. Grep으로 클래스/함수 시그니처 추출
2. 오프셋+리밋으로 청크 단위 읽기
3. 핵심 로직만 선별 포팅 (전체 복사 금지)
4. 포팅 시 M1 스키마로 재설계
```

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

### 1. constants.py (RED - 재검증 필요)

**⚠️ 주의**: 레거시 값을 그대로 복사하면 안 됨. 원본 소스에서 재검증.

**레거시 참조**: `pdufa_analyzer.py:1472-1565`

**검증 필요 상수 목록**:
| 상수 | 레거시 값 | 원본 소스 | 검증 상태 |
|------|-----------|-----------|-----------|
| phase3 승인률 | 0.59 | Wong et al. (2018) | □ 미검증 |
| nda_bla 승인률 | 0.70 | 수집 데이터 428건 | □ 미검증 |
| class1_resubmission | 0.50 | CRL DB 22건 | □ 미검증 |
| class2_resubmission | 0.6506 | CRL DB 83건 | □ 미검증 |
| ADCOM_POSITIVE | 0.966 | JAMA 2023 | □ 미검증 |

**구현 방식**:
```python
from tickergenius.schemas.base import StatusField, DataStatus

# 검증 전: UNKNOWN 상태로 시작
BASE_APPROVAL_RATES = {
    "phase3": StatusField(
        value=0.59,
        status=DataStatus.UNKNOWN,  # 검증 전
        source="Wong et al. (2018) - 재검증 필요"
    ),
    ...
}

# 검증 후: CONFIRMED로 변경
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
□ 파일 구조 생성
    - analysis/pdufa/__init__.py
    - analysis/pdufa/constants.py
    - analysis/pdufa/probability.py
    - analysis/pdufa/factors.py
    - analysis/pdufa/crl.py
    - analysis/pdufa/analyzer.py
□ Import 테스트 통과
□ 데이터 검증 (M3의 핵심)
    - 원본 소스에서 통계 재확인
    - 검증된 값만 CONFIRMED 상태
    - 미검증 값은 UNKNOWN 유지
□ Pipeline 스키마 연동 확인
□ 단위 테스트 통과
□ Git 커밋 + 태그 (M3-complete)
□ STATUS.md 업데이트
```

**주의**: "레거시와 ±0.05 일치" 삭제함.
오염된 데이터와 일치하는 것은 검증이 아님.

---

## 검증 방법

**잘못된 방법 (삭제됨)**:
```python
# ❌ 오염된 레거시와 비교하면 안 됨
# legacy_prob = 0.72
# assert abs(legacy_prob - new_prob) <= 0.05
```

**올바른 방법**:
```python
# ✅ 원본 소스에서 직접 검증
# 1. Wong et al. (2018) 논문에서 Phase 3 승인률 확인
# 2. FDA openFDA API에서 실제 승인 데이터 조회
# 3. JAMA Health Forum 2023에서 AdCom 통계 확인

# 검증된 값만 CONFIRMED
from tickergenius.schemas.base import DataStatus

rate = get_approval_rate("phase3")
assert rate.status == DataStatus.CONFIRMED
assert rate.source != ""  # 출처 필수
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
