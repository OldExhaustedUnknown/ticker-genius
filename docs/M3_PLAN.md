# M3: PDUFA 분석 모듈 상세 계획

**작성일**: 2026-01-08
**레거시 분석 기반**

---

## 사용자 관점 설계

**사용자 요청**: "OMER 분석해"
**기대 결과**: 확률, 요인, 신호 등 종합 분석

```
사용자 ─────────────────────────────────────────────────────────
    │
    │ "OMER 분석해"
    ▼
┌─────────────────────────────────────────────────────────────┐
│  M4: MCP 도구 (입구)                                        │
│  analyze_pdufa(ticker="OMER")                              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  M3: PDUFAAnalyzer.analyze("OMER")                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 내부 복잡도 (숨김)                                   │   │
│  │ - probability.py: 확률 계산                         │   │
│  │ - _factors.py: FDA 지정, AdCom 조정                 │   │
│  │ - _crl.py: CRL 이력 분석                            │   │
│  │ - _constants.py: 통계 상수                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  결과: Pipeline 스키마                                      │
│  - approval_probability: 72%                               │
│  - factors: {btd: +8%, priority: +5%, crl: -15%}          │
│  - timing_signal: HOLD                                     │
│  - confidence_level: 0.85                                  │
└─────────────────────────────────────────────────────────────┘
```

**원칙**: 내부는 복잡해도 됨. 입구(API)는 단순해야 함.

---

## MCP 도구 설계 옵션

### 옵션 A: 단일 도구 (권장)

```python
# 사용자: "OMER 분석해"
# → Claude가 도구 1개만 호출

@mcp.tool()
def analyze_pdufa(ticker: str) -> Pipeline:
    """PDUFA 종합 분석 - 확률, 요인, 신호 모두 포함"""
    return PDUFAAnalyzer().analyze(ticker)
```

**장점**: 단순함, 한 번에 결과
**단점**: 세부 분석 어려움

### 옵션 B: 다중 도구

```python
@mcp.tool()
def get_pdufa_probability(ticker: str) -> float:
    """승인 확률만 조회"""

@mcp.tool()
def get_probability_factors(ticker: str) -> dict:
    """확률 조정 요인 상세"""

@mcp.tool()
def get_crl_history(ticker: str) -> list:
    """CRL 이력 조회"""
```

**장점**: 세부 분석 가능, Claude가 필요한 것만 선택
**단점**: 복잡, 여러 번 호출 필요

### 결정: 하이브리드

```python
# 메인 도구 (대부분의 경우)
@mcp.tool()
def analyze_pdufa(ticker: str) -> Pipeline:
    """PDUFA 종합 분석"""

# 보조 도구 (상세 분석 필요 시)
@mcp.tool()
def explain_probability(ticker: str) -> str:
    """확률 계산 과정 설명 (왜 72%인지)"""
```

사용자가 "OMER 분석해" → `analyze_pdufa` 1회
사용자가 "왜 72%야?" → `explain_probability` 추가 호출

---

## 복잡한 확률 계산 분해

### 문제: 확률 계산이 복잡함

```
기본 확률 (phase3: 59%)
    + FDA 지정 보너스 (BTD: +8%, Priority: +5%)
    + AdCom 결과 (긍정: +10%)
    - CRL 페널티 (Class 2: -15%)
    - 지연 페널티 (2년+: -8%)
    = 최종 확률 (cap 적용)
```

### 해결: 파이프라인 패턴

```python
class ProbabilityCalculator:
    def calculate(self, features: dict) -> ApprovalProbability:
        # 1. 기본 확률 (검증된 상수에서)
        base = self._get_base_rate(features)

        # 2. 팩터 적용 (순차적, 독립적)
        adjusted = base
        adjusted = apply_fda_designation(adjusted, features)
        adjusted = apply_adcom_result(adjusted, features)
        adjusted = apply_crl_adjustment(adjusted, features)

        # 3. 상한 적용
        capped = min(adjusted, self._get_cap(features))

        # 4. 결과 + 설명
        return ApprovalProbability(
            base_probability=base,
            adjusted_probability=capped,
            factors=self._collect_factors(),  # 어떤 팩터가 적용되었는지
        )
```

### 설계 원칙

1. **각 팩터는 독립적**: `_factors.py`의 함수들은 서로 의존 안 함
2. **순서 명확**: base → designation → adcom → crl → cap
3. **추적 가능**: 어떤 팩터가 얼마나 기여했는지 기록
4. **테스트 가능**: 각 팩터 함수를 개별 테스트

---

## ⚠️ 데이터 원칙

> **리빌딩 이유**: 레거시 데이터셋이 오염되어 있음.

1. **레거시 상수 = 참조용**. 그대로 복사 금지.
2. **모든 통계는 원본 소스에서 재검증** 필요.
3. **검증되지 않은 값은 UNKNOWN 상태**로 처리.

---

## 설계 원칙: 스파게티 방지

### 레거시 문제
```
pdufa_analyzer.py (53K 토큰, 3000줄+)
├── PDUFAAnalyzer
├── ApprovalProbabilityModel
├── BinaryRiskCalculator
└── 순환 의존성 → lazy import 남발 → 입구 불명확
```

### 신규 설계 원칙

**1. 파일 크기 제한**
- 각 파일 **500줄 이하** (~10K 토큰)
- 읽기 한도(25K) 내에서 충분히 파악 가능

**2. 명확한 입구 (Public API)**
```python
# __init__.py가 유일한 입구
from tickergenius.analysis.pdufa import PDUFAAnalyzer
from tickergenius.analysis.pdufa import calculate_probability

# 내부 구현은 접근 불가
# from tickergenius.analysis.pdufa._constants import ...  # ❌
```

**3. 내부 구현 숨김**
```
analysis/pdufa/
├── __init__.py         # Public API (입구) - 50줄
├── _constants.py       # 내부용 (언더스코어) - 200줄
├── _factors.py         # 내부용 - 150줄
├── _crl.py             # 내부용 - 150줄
├── probability.py      # Public - 300줄
└── analyzer.py         # Public (Facade) - 200줄
                        # 총합: ~1000줄 (레거시 1/3)
```

**4. 의존성 방향 (단방향, 순환 금지)**
```
__init__.py
    ↓
analyzer.py (Facade)
    ↓
probability.py
    ↓
_factors.py, _crl.py
    ↓
_constants.py (최하위, 의존성 없음)
```

### 레거시 분석 방법
```
1. Grep으로 클래스/함수 시그니처 추출
2. 오프셋+리밋으로 청크 단위 읽기
3. 핵심 로직만 선별 (전체 복사 금지)
4. 신규 구조에 맞게 재배치
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
├── __init__.py         # Public API (입구) - 50줄
├── _constants.py       # 내부: 통계 상수 (RED 재검증) - 200줄
├── _factors.py         # 내부: 조정 요인 - 150줄
├── _crl.py             # 내부: CRL 분석 - 150줄
├── probability.py      # Public: 확률 계산 - 300줄
└── analyzer.py         # Public: Facade - 200줄
```

**언더스코어 규칙**: `_xxx.py` = 모듈 내부용, 외부에서 직접 import 금지

---

## 파일별 포팅 명세

### 1. _constants.py (RED - 재검증 필요, 내부용)

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
    - analysis/pdufa/__init__.py   (Public API)
    - analysis/pdufa/_constants.py (내부용)
    - analysis/pdufa/_factors.py   (내부용)
    - analysis/pdufa/_crl.py       (내부용)
    - analysis/pdufa/probability.py
    - analysis/pdufa/analyzer.py
□ 파일 크기 제한 확인
    - 각 파일 500줄 이하
□ Import 테스트 (Public API만)
    - from tickergenius.analysis.pdufa import PDUFAAnalyzer ✓
    - from tickergenius.analysis.pdufa._constants import ... ✗ (금지)
□ 의존성 방향 검증
    - 순환 의존성 없음
    - 단방향 흐름
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

---

## 페르소나 토론 기록

### 참여자
- **A (Architect)**: 전체 구조, 확장성
- **B (Data Expert)**: 데이터 검증, 오염 방지
- **C (MCP Specialist)**: 도구 설계, Claude 연동
- **D (Trading Risk)**: 실사용 의사결정
- **E (SRE)**: 운영, 에러 처리

---

### 토론 1: 도구 설계 - 단일 vs 다중

**C (MCP)**: 하이브리드로 결정했는데, 구체적으로 몇 개?

**A (Architect)**: 너무 많으면 스파게티. 원칙 제안:
- **메인 도구 1개**: `analyze_pdufa` - 90%의 사용 케이스 커버
- **보조 도구 최대 2개**: 정말 필요한 것만

**D (Trading)**: 실사용 관점에서 필요한 질문들:
1. "OMER 분석해" → 종합 분석
2. "왜 72%야?" → 확률 설명
3. "CRL 이력 뭐야?" → 상세 조회
4. "지금 사야 해?" → 신호/타이밍

**C (MCP)**: 4번은 위험. 매수/매도 직접 추천은 안 돼.

**D (Trading)**: 맞아. "신호"로 표현. BUY/SELL 아니라 BULLISH/BEARISH/NEUTRAL.

**결론**:
```python
# 메인 (필수)
analyze_pdufa(ticker) → Pipeline  # 모든 정보 포함

# 보조 (선택적, M4에서 결정)
# explain_probability(ticker) → str  # 필요 시 추가
```

---

### 토론 2: 확장성 - 다른 분석 모듈 추가되면?

**A (Architect)**: M3는 PDUFA만. 나중에 추가될 것들:
- `analyze_clinical` (임상 시험)
- `analyze_market` (시장 데이터)
- `analyze_sentiment` (뉴스/SNS)

**E (SRE)**: 각각 독립 모듈? 아니면 통합?

**A (Architect)**: 독립 모듈 + 공통 인터페이스.

```python
# 공통 인터페이스 (M3에서는 아직 구현 안 함, 설계만)
class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, ticker: str) -> BaseResult:
        pass

# M3: PDUFA 분석기
class PDUFAAnalyzer(BaseAnalyzer):
    def analyze(self, ticker: str) -> Pipeline:
        ...

# 미래: 다른 분석기들
class ClinicalAnalyzer(BaseAnalyzer):
    def analyze(self, ticker: str) -> ClinicalResult:
        ...
```

**B (Data)**: 결과 스키마도 공통 베이스 필요?

**A (Architect)**: 이미 M1에서 `VersionedSchema` 있음. 확장 가능.

**결론**:
- M3는 `PDUFAAnalyzer`만 구현
- `BaseAnalyzer` 인터페이스는 M3 완료 후 리팩터링 시 고려
- 지금은 과도한 추상화 피함 (YAGNI)

---

### 토론 3: 데이터 오염 방지

**B (Data)**: 레거시 상수 검증 어떻게?

**A (Architect)**: StatusField 3-state 쓰기로 했잖아.

**B (Data)**: 그건 "표시"일 뿐. 실제 검증 프로세스는?

**D (Trading)**: 실사용에서 UNKNOWN 상태면 어떻게 해?

**토론**:
1. UNKNOWN 상태 값 → 사용 가능하지만 경고 표시
2. 검증 프로세스: 원본 소스 URL + 날짜 + 검증자 기록
3. 주기적 재검증 필요 (연 1회?)

**B (Data)**: 구체적으로:
```python
@dataclass
class VerifiedConstant:
    value: float
    status: DataStatus
    source_url: str           # 원본 소스 URL
    source_citation: str      # "Wong et al. (2018)"
    verified_date: date       # 검증 날짜
    verified_by: str          # "TF-31" 또는 "manual"
    next_review: date         # 재검증 예정일
```

**A (Architect)**: 오버엔지니어링 아니야?

**B (Data)**: 데이터 오염 때문에 리빌딩하는 거잖아. 이번엔 제대로 해야지.

**E (SRE)**: 최소한 `source_url`과 `verified_date`는 필수.

**결론**:
```python
# _constants.py
PHASE3_APPROVAL_RATE = StatusField(
    value=0.59,
    status=DataStatus.UNKNOWN,  # 검증 전
    source="Wong et al. (2018) https://pmc.ncbi.nlm.nih.gov/articles/PMC6409418/",
    updated_at=None,  # 검증되면 채워짐
)
```

---

### 토론 4: 에러 처리 및 실패 모드

**E (SRE)**: 분석 실패하면 어떻게?

**D (Trading)**: 부분 실패도 있어. 확률은 계산됐는데 CRL 조회 실패.

**A (Architect)**: 실패 모드 정의 필요:
1. **완전 실패**: 티커 없음, 네트워크 에러 → 예외 발생
2. **부분 실패**: 일부 데이터 없음 → 결과에 표시, 계속 진행
3. **데이터 부족**: 확률 계산 불가 → `confidence_level` 낮게

**C (MCP)**: MCP 도구에서 예외 발생하면 Claude가 처리 못 해.

**E (SRE)**: 예외 대신 결과에 에러 상태 포함:
```python
class Pipeline:
    # ... 기존 필드 ...
    errors: list[str] = []        # 발생한 에러들
    warnings: list[str] = []      # 경고들
    data_completeness: float      # 0.0 ~ 1.0
```

**결론**:
- 예외는 최소화
- 부분 결과라도 반환
- `errors`, `warnings` 필드로 문제 표시

---

### 토론 5: 성능 및 캐싱

**E (SRE)**: 분석 한 번에 얼마나 걸려?

**A (Architect)**: 예상:
- 로컬 계산: <100ms
- 외부 API 호출 (FDA, 시장 데이터): 1-5초

**E (SRE)**: 캐싱 전략?

**B (Data)**: M2 `DiskCache` 있음. TTL 설정 필요.

**결론**:
```python
# 캐싱 TTL 정책
CACHE_TTL = {
    "pdufa_analysis": 3600,      # 1시간 (자주 변하지 않음)
    "market_data": 300,          # 5분 (실시간성 필요)
    "fda_calendar": 86400,       # 24시간 (드물게 변경)
}
```

---

### 토론 6: 팩터 간 복잡한 관계 (핵심)

**B (Data)**: 레거시에서 팩터 적용 방식이 복잡했음:
- TF 안건 1: 요인 간 중복 조정
- TF 안건 8: 중복 팩터 그룹핑

**A (Architect)**: 구체적으로 어떤 문제?

**B (Data)**:
```
문제 1: 단순 덧셈의 함정
- BTD: +8%
- Priority Review: +5%
- Orphan Drug: +4%
- 전부 있으면: +17%? → 과대 추정

문제 2: 상호 배타적 팩터
- Phase 2 기본률 vs Phase 3 기본률 → 동시 적용 안 됨
- CRL Class 1 vs Class 2 → 동시 적용 안 됨

문제 3: 조건부 팩터
- AdCom 결과가 있으면 → 기본 확률 자체가 달라짐
- CRL 있으면 → base_rate가 resubmission으로 변경
```

**D (Trading)**: 레거시는 어떻게 해결했어?

**B (Data)**: 스파게티로 해결함. if-else 난무.

**A (Architect)**: 새 설계 제안 - **팩터 그룹 + 적용 순서**:

```
┌─────────────────────────────────────────────────────────────┐
│  1단계: 기본률 결정 (상호 배타적)                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ phase1 | phase2 | phase3 | nda_bla | resubmission  │   │
│  │         (하나만 선택됨)                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2단계: FDA 지정 보너스 (중복 허용, 상한 있음)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ BTD | Priority | Orphan | FastTrack | AA           │   │
│  │ 개별 적용 후 그룹 상한: max +15%                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3단계: AdCom 결과 (있으면 적용)                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ positive: +10% | negative: -25% | none: 0%         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  4단계: CRL 조정 (resubmission인 경우만)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ CRL 유형: CMC_MINOR(-8%) | EFFICACY(-25%) | ...    │   │
│  │ 지연 기간: <1년(0%) | 1-2년(-5%) | 2-3년(-8%) | ... │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  5단계: 최종 상한 적용                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ phase3_cap: 80% | nda_bla_cap: 85% | ...           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**C (MCP)**: 이거 코드로 어떻게?

**A (Architect)**:
```python
# _factors.py
class FactorGroup(Enum):
    BASE_RATE = "base_rate"           # 상호 배타적
    FDA_DESIGNATION = "fda_designation"  # 중복 허용, 그룹 상한
    ADCOM = "adcom"                   # 단일
    CRL = "crl"                       # 조건부
    CAP = "cap"                       # 최종

@dataclass
class Factor:
    name: str
    group: FactorGroup
    value: float
    condition: Optional[Callable] = None  # 적용 조건

# 그룹별 상한
GROUP_CAPS = {
    FactorGroup.FDA_DESIGNATION: 0.15,  # 지정 보너스 합계 최대 15%
}
```

**B (Data)**: 팩터 적용 로직:
```python
def apply_factors(base: float, features: dict) -> tuple[float, list[Factor]]:
    applied = []
    result = base

    # 2단계: FDA 지정 (그룹 상한 적용)
    designation_total = 0
    for factor in get_fda_designation_factors(features):
        designation_total += factor.value
        applied.append(factor)
    designation_total = min(designation_total, GROUP_CAPS[FactorGroup.FDA_DESIGNATION])
    result += designation_total

    # 3단계: AdCom
    if adcom := get_adcom_factor(features):
        result += adcom.value
        applied.append(adcom)

    # 4단계: CRL (조건부)
    if features.get("is_resubmission"):
        for factor in get_crl_factors(features):
            result += factor.value
            applied.append(factor)

    return result, applied
```

**D (Trading)**: 이렇게 하면 어떤 팩터가 적용됐는지 추적 가능해.

**E (SRE)**: 결과에 `applied_factors` 포함시키면 디버깅도 쉬워.

**결론**:
1. **5단계 순서**: base → designation → adcom → crl → cap
2. **그룹 상한**: FDA 지정 보너스 합계 최대 15%
3. **조건부 적용**: CRL은 resubmission일 때만
4. **추적 가능**: 적용된 팩터 목록 반환

---

### 최종 설계 결정 요약

| 항목 | 결정 | 근거 |
|------|------|------|
| MCP 도구 개수 | 1개 (analyze_pdufa) | 90% 케이스 커버, 단순함 |
| 확장성 | 독립 모듈, 인터페이스는 나중에 | YAGNI, 과도한 추상화 피함 |
| 데이터 검증 | StatusField + source URL 필수 | 오염 방지 |
| 에러 처리 | 예외 최소화, errors/warnings 필드 | MCP 호환성 |
| 캐싱 | M2 DiskCache, TTL 정책 | 성능 |

---

### 스파게티 방지 체크리스트 (구현 시 확인)

```
□ 파일당 500줄 이하
□ 순환 의존성 없음
□ Public API는 __init__.py만
□ 모든 상수에 source URL 있음
□ errors/warnings 필드 구현
□ 캐싱 TTL 설정
□ 단위 테스트 커버리지 80%+
```
