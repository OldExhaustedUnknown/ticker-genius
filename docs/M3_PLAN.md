# M3: PDUFA 분석 모듈 상세 계획

> **⚠️ SUPERSEDED**: 이 문서는 M3_BLUEPRINT_v2.md로 대체되었습니다.
> - **핵심 변경**: 약물 단위 → PDUFA 이벤트 단위
> - **새 원칙**: CRL 횟수는 승인에 무관 (독립 사건)
> - **참고용**: 기존 레이어 시스템, API 구조 참조 가능
> - **금지**: 이 문서의 데이터 모델/예측 방식 사용 금지

**작성일**: 2026-01-08
**상태**: ~~활성~~ → **SUPERSEDED by M3_BLUEPRINT_v2.md**
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

> **Note**: 초기 설계. 토론 7-9에서 상세화됨.

```
src/tickergenius/
│
├── data/
│   ├── constants/              # Layer 1: Static (JSON)
│   │   ├── approval_rates.json
│   │   ├── factor_adjustments.json
│   │   └── cap_rules.json
│   └── db/                     # Layer 2-3: SQLite
│       └── tickergenius.db
│
├── repositories/               # 데이터 접근 레이어
│   ├── __init__.py
│   ├── constants.py            # JSON 로더 + 타입 래퍼
│   ├── pipeline_repo.py        # Pipeline Repository
│   └── price_repo.py           # Price Repository
│
└── analysis/pdufa/             # 분석 모듈
    ├── __init__.py             # Public API (입구)
    ├── _context.py             # AnalysisContext (입력 객체화)
    ├── _registry.py            # FactorRegistry (확장성)
    ├── _layers/                # 13개 확률 레이어
    │   ├── __init__.py
    │   ├── base.py             # 기본 승인률
    │   ├── designation.py      # FDA 지정
    │   ├── adcom.py            # AdCom 결과
    │   ├── crl.py              # CRL 이력
    │   ├── clinical.py         # 임상 요인
    │   ├── manufacturing.py    # 제조 요인
    │   ├── context.py          # 맥락 상호작용
    │   └── cap.py              # 상한 규칙
    ├── probability.py          # ProbabilityCalculator
    ├── analyzer.py             # PDUFAAnalyzer (Facade)
    ├── result.py               # AnalysisResult
    └── report.py               # ReportGenerator (선택적)
```

**규칙**:
- `_xxx.py` = 모듈 내부용, 외부에서 직접 import 금지
- `__init__.py`만 Public API
- 파일당 500줄 이하

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

> ⚠️ **구현 순서는 문서 하단 "구현 순서 (M3)" 섹션 참조** (토론 7-10 결과 반영)

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

### 토론 6: 팩터 간 복잡한 관계 (핵심) - 레거시 분석 기반

**B (Data)**: 레거시 `calculate_probability` 분석 완료. 생각보다 훨씬 복잡함.

**실제 레거시 구조** (pdufa_analyzer.py:2314-2513):

```
입력 파라미터만 20개+:
- ticker, phase, designations, adcom_result
- crl_count, crl_types, crl_delay
- dispute_result, mental_health_type
- external_control_quality, days_to_pdufa
- clinical_quality_tiers, endpoint_type
- pai_status, earnings_call_signals
- fda_reviewer_factors, citizen_petition_context
- pdufa_year, control_type, early_decision_days
- additional_factors (dict)
```

**A (Architect)**: 이건 스파게티가 아니라 도메인 자체가 복잡한 거야.

**B (Data)**: 맞아. 레거시의 팩터 처리 로직:

```python
# 레거시 _apply_factor_grouping (line 2204-2310)
# 두 가지 모드:
# 1. exclusive=True: 상호배타 (첫 번째만 적용)
# 2. max_only=True: 그룹 내 최대값만 적용

# 예: AdCom 그룹 (exclusive)
# - adcom_positive, adcom_negative, adcom_unanimous_positive
# - 동시에 있으면 첫 번째만 적용

# 예: FDA 지정 그룹 (max_only)
# - BTD(+8%), Priority(+5%), Orphan(+4%)
# - 동시에 있으면 최대값만 (+8%)
```

**D (Trading)**: Cap 규칙도 복잡하더라.

**B (Data)**:
```python
# 레거시 _apply_cap (line 2156-2202)
CAP_RULES = {
    "catastrophic": 0.05,   # 임상설계 치명결함, AdCom 만장일치 부결
    "critical": 0.15,       # PAI + cGMP 동시 실패
    "severe": 0.25,         # PAI 중대 실패, Phase 3 미달
    "moderate": 0.40,       # CRL 2회 이상, cGMP 실패
    "default": 0.85,        # 기본 상한
}
```

**E (SRE)**: 컨텍스트 상호작용도 있었어?

**B (Data)**: 있음. `_apply_context_interactions` (line 2111-2154):
```python
# 여러 팩터가 동시에 있을 때 특별 효과
# 예: BTD + Orphan + First-in-Class → 페널티 75% 감소
CONTEXT_INTERACTIONS = {
    "strong_designation_combo": {
        "condition": ["breakthrough_therapy", "orphan_drug", "first_in_class"],
        "effect": "penalty_reduction",
        "value": 0.75,  # 페널티 75% 감소
    },
    ...
}
```

---

**A (Architect)**: 정리하면, 레거시 복잡도는 **13개 레이어**:

```
┌─────────────────────────────────────────────────────────────┐
│  1. 기본 확률 (phase별 상호배타)                             │
│     phase1(14%) | phase2(21%) | phase3(59%) | nda_bla(70%) │
│     resubmission(62%) | class1(50%) | class2(65%)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. 팩터 그룹핑 (exclusive/max_only)                        │
│     FDA 지정, AdCom, Manufacturing 등 그룹별 처리           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. AdCom 결과                                              │
│     positive(+10%) | negative(-25%) | unanimous(±15%)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. CRL 유형별 조정                                         │
│     LABELING(-5%) | CMC_MINOR(-8%) | CMC_MAJOR(-18%)       │
│     SAFETY_REMS(-20%) | EFFICACY(-25%) | TRIAL_DESIGN(-50%)│
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  5. CRL 지연 시간                                           │
│     <1년(0%) | 1-2년(-5%) | 2-3년(-8%) | >3년(-12%)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  6. FDA Dispute Resolution                                  │
│     WON_FULLY(+10%) | PARTIAL(-5%) | LOST_FULLY(-20%)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  7. 정신건강 적응증 세분화                                   │
│     MDD(-8%) | PTSD(-5%) | BIPOLAR(-12%) | SCHIZO(-15%)    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  8. 외부대조군 품질 / Endpoint 유형                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  9. PAI 상태                                                │
│     PASSED(+5%) | FAILED(-30%)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  10. Earnings Call 시그널                                   │
│      label_negotiation(+8%) | timeline_delayed(-10%)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  11. 시민청원 컨텍스트 (TF 9차)                              │
│      timing × quality × fda_response 조합                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  12. 컨텍스트 상호작용                                       │
│      팩터 조합 → 페널티 감소 / cap 상향                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  13. 최종 Cap 적용                                          │
│      catastrophic(5%) | critical(15%) | severe(25%)        │
│      moderate(40%) | default(85%)                          │
└─────────────────────────────────────────────────────────────┘
```

---

**C (MCP)**: 이걸 어떻게 단순화해?

**A (Architect)**: **단순화하면 안 돼.** 복잡한 건 도메인이 복잡하기 때문.
대신 **구조화**해야 해:

```python
# 신규 설계: 레이어별 분리
analysis/pdufa/
├── _constants.py      # 모든 상수 (검증 필요)
├── _layer_base.py     # 1. 기본 확률
├── _layer_grouping.py # 2. 팩터 그룹핑
├── _layer_adcom.py    # 3. AdCom
├── _layer_crl.py      # 4-5. CRL
├── _layer_clinical.py # 6-10. 임상/제조
├── _layer_context.py  # 11-12. 시민청원/상호작용
├── _layer_cap.py      # 13. Cap
├── probability.py     # 레이어 조합
└── analyzer.py        # Facade
```

**D (Trading)**: 파일 너무 많아지는 거 아니야?

**A (Architect)**: 그럼 3개로 그룹화:

```python
analysis/pdufa/
├── _constants.py      # 모든 상수
├── _layers.py         # 모든 레이어 (13개 함수)
├── probability.py     # 레이어 조합 + 추적
└── analyzer.py        # Facade
```

**결론**:
1. **복잡도 존중**: 13개 레이어는 도메인 요구사항
2. **구조화**: 각 레이어를 독립 함수로 분리
3. **추적 가능**: 어떤 레이어에서 어떤 조정이 발생했는지 기록
4. **레거시 로직 보존**: 검증된 TF 결정사항 유지

---

### 토론 7: 확장성 설계 (핵심) - 스파게티 방지

**A (Architect)**: 레거시의 근본 문제를 짚어보자.

**B (Data)**: `calculate_probability(ticker, phase, designations, adcom_result, crl_count, crl_types, ...)` - 파라미터 20개+. 새 팩터 추가할 때마다 시그니처 변경.

**A (Architect)**: 이게 스파게티화의 원인. 해결책은 **입력 객체화 + 팩터 레지스트리**.

---

**설계 1: 입력 객체화**

```python
# 레거시 (문제)
def calculate_probability(
    ticker, phase, designations, adcom_result,
    crl_count, crl_types, crl_delay,
    dispute_result, mental_health_type,
    # ... 20개 더 추가될 때마다 변경
) -> ApprovalProbability:
    ...

# 신규 (해결)
@dataclass
class AnalysisContext:
    """분석에 필요한 모든 컨텍스트 (확장 가능)"""
    ticker: str
    phase: str

    # FDA 지정
    designations: list[str] = field(default_factory=list)

    # AdCom
    adcom_result: Optional[str] = None

    # CRL
    crl_types: list[CRLType] = field(default_factory=list)
    crl_delay: Optional[CRLDelayCategory] = None

    # 임상
    clinical_quality: Optional[ClinicalQualityTier] = None
    endpoint_type: Optional[EndpointType] = None

    # 제조
    pai_status: Optional[PAIStatus] = None

    # 추가 팩터 (확장용)
    extra_factors: dict[str, Any] = field(default_factory=dict)

def calculate_probability(ctx: AnalysisContext) -> ApprovalProbability:
    """파라미터 1개 - 시그니처 변경 불필요"""
    ...
```

**C (MCP)**: `extra_factors` dict가 핵심이네. 새 팩터 추가해도 시그니처 안 바뀜.

---

**설계 2: 팩터 레지스트리 패턴**

```python
# _layers.py

class FactorRegistry:
    """팩터 레지스트리 - 새 팩터 추가 시 기존 코드 수정 불필요"""

    _layers: list[Callable] = []

    @classmethod
    def register(cls, order: int):
        """레이어 등록 데코레이터"""
        def decorator(func):
            cls._layers.append((order, func))
            cls._layers.sort(key=lambda x: x[0])
            return func
        return decorator

    @classmethod
    def apply_all(cls, ctx: AnalysisContext, base: float) -> tuple[float, list[FactorResult]]:
        """모든 레이어 순차 적용"""
        result = base
        applied = []
        for order, layer_func in cls._layers:
            result, factors = layer_func(ctx, result)
            applied.extend(factors)
        return result, applied

# 레이어 등록 (순서 지정)
@FactorRegistry.register(order=1)
def apply_fda_designations(ctx: AnalysisContext, prob: float) -> tuple[float, list]:
    """FDA 지정 보너스"""
    ...

@FactorRegistry.register(order=2)
def apply_adcom(ctx: AnalysisContext, prob: float) -> tuple[float, list]:
    """AdCom 결과"""
    ...

@FactorRegistry.register(order=3)
def apply_crl(ctx: AnalysisContext, prob: float) -> tuple[float, list]:
    """CRL 조정"""
    ...

# 새 팩터 추가 시 - 기존 코드 수정 없이 등록만
@FactorRegistry.register(order=7)
def apply_new_factor_2026(ctx: AnalysisContext, prob: float) -> tuple[float, list]:
    """2026년에 추가된 새 팩터"""
    ...
```

**D (Trading)**: 이렇게 하면 새 팩터 추가가 쉬워지네. Open-Closed 원칙.

**E (SRE)**: 순서(order)로 레이어 실행 순서 보장되고.

---

**설계 3: 팩터 결과 추적**

```python
@dataclass
class FactorResult:
    """개별 팩터 적용 결과"""
    layer: str              # "fda_designation"
    factor_name: str        # "breakthrough_therapy"
    adjustment: float       # +0.08
    reason: str             # "BTD 지정"
    source: str             # "FDA 지정 목록"

@dataclass
class ProbabilityResult:
    """확률 계산 최종 결과"""
    base_probability: float
    adjusted_probability: float
    capped_probability: float
    applied_factors: list[FactorResult]
    cap_reason: Optional[str]
    confidence_level: float
    warnings: list[str]

    def explain(self) -> str:
        """확률 계산 과정 설명 (왜 72%인지)"""
        lines = [f"기본 확률: {self.base_probability:.0%}"]
        for f in self.applied_factors:
            lines.append(f"  {f.adjustment:+.0%} {f.reason}")
        if self.cap_reason:
            lines.append(f"  [Cap] {self.cap_reason}")
        lines.append(f"최종: {self.capped_probability:.0%}")
        return "\n".join(lines)
```

**C (MCP)**: `explain()` 메서드가 "왜 72%야?" 질문에 대한 답이 되겠네.

---

**최종 구조 결정**:

```
analysis/pdufa/
├── __init__.py         # Public API
│   - PDUFAAnalyzer
│   - AnalysisContext
│
├── _context.py         # AnalysisContext 정의 (~100줄)
│
├── _constants.py       # 모든 상수 (검증 필요) (~300줄)
│
├── _registry.py        # FactorRegistry 패턴 (~50줄)
│
├── _layers/            # 레이어별 분리 (각 ~100줄)
│   ├── __init__.py
│   ├── base.py         # 1. 기본 확률
│   ├── designation.py  # 2. FDA 지정 + 그룹핑
│   ├── adcom.py        # 3. AdCom
│   ├── crl.py          # 4-5. CRL
│   ├── clinical.py     # 6-8. 임상/제조
│   ├── context.py      # 9-12. 시민청원/상호작용
│   └── cap.py          # 13. Cap
│
├── probability.py      # ProbabilityCalculator (~150줄)
│
└── analyzer.py         # PDUFAAnalyzer Facade (~100줄)
```

**D (Trading)**: 파일이 많아졌는데?

**A (Architect)**: 각 파일이 100줄 내외로 작아짐. 읽기 쉽고, 테스트 쉽고, 확장 쉬움.

---

**설계 4: 팩터 추가/제거/비활성화**

**D (Trading)**: 팩터는 늘어날 수도, 줄어들 수도 있어.

**A (Architect)**: 맞아. 세 가지 시나리오:
1. **추가**: 새 팩터 등록 → 기존 코드 수정 없음 ✓
2. **제거**: 검증 실패한 팩터 삭제 → 등록 해제
3. **비활성화**: 일시적으로 끔 → 설정으로 제어

```python
class FactorRegistry:
    _layers: dict[str, LayerInfo] = {}  # name → info

    @dataclass
    class LayerInfo:
        func: Callable
        order: int
        enabled: bool = True  # 비활성화 가능
        version: str = "1.0"
        deprecated: bool = False

    @classmethod
    def register(cls, name: str, order: int, version: str = "1.0"):
        def decorator(func):
            cls._layers[name] = cls.LayerInfo(
                func=func, order=order, version=version
            )
            return func
        return decorator

    @classmethod
    def unregister(cls, name: str):
        """팩터 제거"""
        if name in cls._layers:
            del cls._layers[name]

    @classmethod
    def disable(cls, name: str):
        """팩터 비활성화 (일시적)"""
        if name in cls._layers:
            cls._layers[name].enabled = False

    @classmethod
    def enable(cls, name: str):
        """팩터 활성화"""
        if name in cls._layers:
            cls._layers[name].enabled = True

    @classmethod
    def deprecate(cls, name: str):
        """팩터 deprecated 표시 (경고만, 동작은 함)"""
        if name in cls._layers:
            cls._layers[name].deprecated = True

    @classmethod
    def apply_all(cls, ctx: AnalysisContext, base: float) -> tuple[float, list]:
        result = base
        applied = []
        warnings = []

        # 활성화된 레이어만, 순서대로
        active = sorted(
            [(n, l) for n, l in cls._layers.items() if l.enabled],
            key=lambda x: x[1].order
        )

        for name, layer_info in active:
            if layer_info.deprecated:
                warnings.append(f"[DEPRECATED] {name} 팩터는 곧 제거됩니다")
            result, factors = layer_info.func(ctx, result)
            applied.extend(factors)

        return result, applied, warnings
```

**E (SRE)**: `deprecated` 상태가 좋네. 바로 삭제 안 하고 경고 먼저.

**B (Data)**: 팩터 버전 관리도 되고. 검증 실패하면 unregister.

---

**결론**:
1. **입력 객체화**: `AnalysisContext` - 파라미터 폭발 방지
2. **팩터 레지스트리**: 추가/제거/비활성화/deprecated 지원
3. **결과 추적**: `FactorResult` - 디버깅/설명 가능
4. **레이어 분리**: `_layers/` 폴더 - 각 100줄 이하

---

### 토론 8: 데이터셋 구성 및 검증 매커니즘

**B (Data)**: 상수 데이터를 어떻게 저장하고 검증할 건지 정해야 해.

**A (Architect)**: 세 가지 고려사항:
1. **저장**: 어디에? Python dict? JSON? SQLite?
2. **검증**: 수동? 반자동? 자동?
3. **웹검색**: 토큰 절약하면서 정확하게 찾기

---

**설계 1: 데이터셋 저장 구조**

**B (Data)**: 제안 - JSON + Python 래퍼:

```
data/
├── constants/
│   ├── approval_rates.json      # 승인률 상수
│   ├── factor_adjustments.json  # 팩터 조정값
│   ├── cap_rules.json           # Cap 규칙
│   └── _schema.json             # JSON 스키마 (검증용)
│
└── verification/
    ├── sources.json             # 원본 소스 목록
    └── verification_log.json    # 검증 이력
```

**JSON 구조 예시**:
```json
// approval_rates.json
{
  "phase3": {
    "value": 0.59,
    "status": "CONFIRMED",
    "source": {
      "citation": "Wong et al. (2018)",
      "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6409418/",
      "retrieved_date": "2026-01-08",
      "relevant_quote": "Phase III to approval: 59.0%"
    },
    "verified_by": "TF-31",
    "verified_date": "2026-01-08",
    "next_review": "2027-01-08"
  },
  "nda_bla": {
    "value": 0.70,
    "status": "UNKNOWN",
    "source": {
      "citation": "수집 데이터 428건",
      "url": null,
      "note": "레거시 데이터 - 재검증 필요"
    }
  }
}
```

**A (Architect)**: JSON으로 하면:
- Git diff로 변경 추적 가능
- 사람이 읽기/수정 가능
- Python 래퍼로 타입 안전성 확보

---

**설계 2: 검증 워크플로우**

**E (SRE)**: 검증을 어떻게 자동화할 건지?

**B (Data)**: 3단계 워크플로우:

```
┌─────────────────────────────────────────────────────────────┐
│  1단계: 원본 소스 식별                                       │
│  - 논문: Wong et al., JAMA, Nature 등                       │
│  - 공식: FDA openFDA API, ClinicalTrials.gov               │
│  - 데이터: BioMedTracker, Citeline 등                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2단계: 웹검색으로 값 확인 (반자동)                          │
│  - 쿼리 템플릿 사용 (토큰 절약)                              │
│  - 결과 캐싱 (중복 검색 방지)                                │
│  - 사람이 최종 확인                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3단계: JSON 업데이트 + Git 커밋                             │
│  - status: UNKNOWN → CONFIRMED                              │
│  - source 정보 채움                                          │
│  - 변경 이력 자동 기록                                       │
└─────────────────────────────────────────────────────────────┘
```

---

**설계 3: 웹검색 최적화 (토큰 절약)**

**C (MCP)**: 웹검색 토큰 어떻게 줄여?

**B (Data)**: 핵심 전략:

**1. 쿼리 템플릿 (정확한 검색)**
```python
VERIFICATION_QUERIES = {
    "phase3_approval": {
        "query": "FDA Phase 3 clinical trial approval rate site:nih.gov OR site:fda.gov",
        "expected_source": "Wong et al. 2018 OR FDA statistics",
        "extract_pattern": r"(\d+\.?\d*)%.*Phase.*3.*approval",
    },
    "adcom_positive": {
        "query": "FDA Advisory Committee positive vote approval rate JAMA",
        "expected_source": "JAMA Health Forum 2023",
        "extract_pattern": r"positive.*(\d+\.?\d*)%.*approved",
    },
}
```

**2. 캐싱 (중복 방지)**
```python
# 검증 결과 캐싱 (24시간)
VERIFICATION_CACHE_TTL = 86400

def verify_constant(key: str) -> VerificationResult:
    cache_key = f"verification:{key}"

    # 캐시 확인
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 웹검색 실행
    query = VERIFICATION_QUERIES[key]
    result = web_search(query["query"])

    # 패턴 매칭으로 값 추출
    extracted = extract_value(result, query["extract_pattern"])

    # 캐시 저장
    cache.set(cache_key, extracted, ttl=VERIFICATION_CACHE_TTL)

    return extracted
```

**3. 배치 검증 (효율적)**
```python
def verify_batch(keys: list[str]) -> dict[str, VerificationResult]:
    """여러 상수 한 번에 검증 (세션당 1회)"""
    results = {}

    # 그룹화: 같은 소스에서 여러 값 추출
    by_source = group_by_source(keys)

    for source, source_keys in by_source.items():
        # 소스당 1회 검색
        page = fetch_source(source)

        for key in source_keys:
            results[key] = extract_from_page(page, key)

    return results
```

**D (Trading)**: 실제로 어떻게 동작해?

**B (Data)**: 예시 - Phase 3 승인률 검증:

```python
# 1. 검증 트리거 (수동 또는 스케줄)
result = verify_constant("phase3_approval")

# 2. 웹검색 실행
# Query: "FDA Phase 3 clinical trial approval rate site:nih.gov"
# → Wong et al. (2018) 논문 페이지 반환

# 3. 패턴 매칭
# 텍스트: "Phase III to approval transition probability was 59.0%"
# → 값: 0.59 추출

# 4. 레거시와 비교
legacy_value = 0.59
if abs(result.value - legacy_value) < 0.01:
    status = "CONFIRMED"
else:
    status = "MISMATCH"  # 사람 확인 필요

# 5. JSON 업데이트
update_constant("phase3", value=result.value, status=status, source=result.source)
```

---

**설계 4: 자동 검증 트리거**

**E (SRE)**: 언제 검증 실행해?

**A (Architect)**: 세 가지 트리거:

```python
# 1. 첫 사용 시 (Lazy verification)
def get_constant(key: str) -> VerifiedConstant:
    const = load_constant(key)
    if const.status == "UNKNOWN":
        # 첫 사용 시 검증 시도
        verify_and_update(key)
    return const

# 2. 만료 시 (TTL 기반)
def check_expired():
    for key, const in all_constants():
        if const.next_review < today():
            schedule_verification(key)

# 3. 수동 트리거
# CLI: python -m tickergenius verify-constants --all
# CLI: python -m tickergenius verify-constants phase3_approval
```

---

**설계 5: 검증 실패 처리**

**D (Trading)**: 검증 실패하면?

**B (Data)**: 상태별 처리:

```python
class VerificationStatus(Enum):
    CONFIRMED = "confirmed"      # 검증 완료, 값 일치
    UNKNOWN = "unknown"          # 미검증
    MISMATCH = "mismatch"        # 검증했으나 값 불일치 → 사람 확인
    SOURCE_UNAVAILABLE = "source_unavailable"  # 소스 접근 불가
    DEPRECATED = "deprecated"    # 더 이상 사용 안 함
```

```python
def get_constant_safe(key: str) -> tuple[float, list[str]]:
    """안전하게 상수 조회 (경고 포함)"""
    const = load_constant(key)
    warnings = []

    if const.status == "UNKNOWN":
        warnings.append(f"[경고] {key}: 미검증 값 사용 중")
    elif const.status == "MISMATCH":
        warnings.append(f"[주의] {key}: 값 불일치 - 수동 확인 필요")
    elif const.status == "SOURCE_UNAVAILABLE":
        warnings.append(f"[경고] {key}: 소스 확인 불가")

    return const.value, warnings
```

---

**최종 데이터 구조**:

```
src/tickergenius/
├── data/
│   ├── constants/
│   │   ├── approval_rates.json
│   │   ├── factor_adjustments.json
│   │   └── cap_rules.json
│   │
│   └── verification/
│       ├── queries.json         # 검증 쿼리 템플릿
│       ├── sources.json         # 원본 소스 목록
│       └── log.json             # 검증 이력
│
└── analysis/pdufa/
    ├── _constants.py            # JSON 로더 + 타입 래퍼
    └── _verification.py         # 검증 로직
```

**결론**:
1. **JSON 저장**: Git 추적 가능, 사람이 편집 가능
2. **반자동 검증**: 쿼리 템플릿 + 사람 최종 확인
3. **토큰 절약**: 캐싱 + 배치 + 정확한 쿼리
4. **실패 처리**: 상태별 경고, 서비스는 계속

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

---

## 토론 9: 데이터셋 확장성 및 참조 관계

> **의제**: 데이터셋이 성장하면서 어떻게 관리할 것인가? 확률 계산기와 데이터의 참조 관계는?

---

**A (Architect)**: 핵심 문제를 정리하자.

1. **데이터 종류가 다름**: 상수 vs 파이프라인 vs 주가
2. **성장 패턴이 다름**: 상수는 거의 고정, 파이프라인은 수백~수천, 주가는 무한 성장
3. **접근 패턴이 다름**: 상수는 자주 읽음, 파이프라인은 티커별 조회, 주가는 범위 쿼리

---

**설계 1: 데이터 레이어 분리**

**B (Data)**: 세 가지 레이어로 나눠야 해.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Static Constants (변동 거의 없음)                  │
│  - 저장: JSON 파일 (Git 추적)                                │
│  - 로딩: 앱 시작 시 메모리 캐시                              │
│  - 예: approval_rates, factor_adjustments, cap_rules        │
│  - 크기: ~100KB (성장 거의 없음)                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Pipeline Data (티커별, 중간 성장)                  │
│  - 저장: SQLite (로컬) / PostgreSQL (프로덕션)              │
│  - 인덱스: ticker_id (PK), pdufa_date, status               │
│  - 예: Pipeline 테이블, 각 티커의 파이프라인 정보           │
│  - 크기: ~1000개 티커 × 평균 2개 파이프라인 = ~2000행       │
│  - 성장: 연간 ~100-200개 신규 파이프라인                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Time Series Data (무한 성장)                       │
│  - 저장: 별도 테이블 (DailyPrice, IntradayPrice)            │
│  - 인덱스: (ticker_id, date) 복합 인덱스                    │
│  - 예: 일별 주가, 분별 주가                                  │
│  - 크기: 1000개 티커 × 365일 × 5년 = ~180만 행 (일별만)    │
│  - 성장: 매일 + 과거 데이터 백필                            │
└─────────────────────────────────────────────────────────────┘
```

---

**설계 2: 참조 관계 설계**

**A (Architect)**: 확률 계산기가 데이터를 어떻게 참조할지.

```
ProbabilityCalculator
    │
    ├──▶ ConstantLoader (Layer 1)
    │     │
    │     └── get_approval_rate(phase) → float
    │     └── get_factor_adjustment(factor_name) → float
    │     └── get_cap_rules() → dict
    │
    ├──▶ PipelineRepository (Layer 2)
    │     │
    │     └── get_by_ticker(ticker) → Pipeline
    │     └── get_active_pipelines() → list[Pipeline]
    │     └── search(filters) → list[Pipeline]
    │
    └──▶ PriceRepository (Layer 3) [선택적]
          │
          └── get_daily_prices(ticker, start, end) → list[DailyPrice]
          └── get_latest_price(ticker) → float
```

**핵심**: 각 레이어는 **독립적인 Repository**로 접근. 순환 참조 없음.

---

**설계 3: Pipeline 테이블 상세 설계**

**D (Trading)**: Pipeline이 중심 테이블이야. 여기서 모든 게 시작돼.

```sql
-- Pipeline 테이블 (중심)
CREATE TABLE pipelines (
    id INTEGER PRIMARY KEY,
    ticker_id INTEGER NOT NULL,        -- FK → tickers
    drug_name TEXT,
    indication TEXT,
    phase TEXT,                        -- Phase 1/2/3
    pdufa_date DATE,
    status TEXT,                       -- CONFIRMED/TENTATIVE/UNKNOWN

    -- FDA 지정 (JSON array)
    designations TEXT,                 -- ["BTD", "Priority", "FastTrack"]

    -- AdCom 정보
    adcom_date DATE,
    adcom_result TEXT,                 -- POSITIVE/MIXED/NEGATIVE
    adcom_vote_for INTEGER,
    adcom_vote_against INTEGER,

    -- CRL 이력 (JSON array)
    crl_history TEXT,                  -- [{type, date, resolved}]

    -- 메타
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    verification_status TEXT,          -- CONFIRMED/UNKNOWN
    source_url TEXT,

    FOREIGN KEY (ticker_id) REFERENCES tickers(id)
);

-- 인덱스
CREATE INDEX idx_pipelines_ticker ON pipelines(ticker_id);
CREATE INDEX idx_pipelines_pdufa_date ON pipelines(pdufa_date);
CREATE INDEX idx_pipelines_status ON pipelines(status);
```

**B (Data)**: JSON 필드로 designations, crl_history 넣은 이유:
1. 조회는 항상 Pipeline 단위 (파이프라인 하나 조회하면 모든 정보 필요)
2. 별도 테이블로 나누면 JOIN 필요 → 복잡성 증가
3. 검색은 주로 ticker_id, pdufa_date로 함 (designation으로 검색하는 경우 드묾)

---

**설계 4: 주가 데이터 분리**

**E (SRE)**: 주가 데이터는 절대 Pipeline과 합치면 안 돼.

```sql
-- 일별 주가 (별도 테이블)
CREATE TABLE daily_prices (
    id INTEGER PRIMARY KEY,
    ticker_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,

    UNIQUE(ticker_id, date),
    FOREIGN KEY (ticker_id) REFERENCES tickers(id)
);

CREATE INDEX idx_daily_prices_ticker_date ON daily_prices(ticker_id, date);
```

**이유**:
1. **성장률이 다름**: 파이프라인은 느리게 성장, 주가는 매일 성장
2. **접근 패턴이 다름**: 파이프라인은 단건 조회, 주가는 범위 쿼리
3. **보관 정책이 다름**: 파이프라인은 영구 보관, 주가는 오래된 건 아카이브 가능

---

**설계 5: 캐싱 전략**

**E (SRE)**: 레이어별 캐싱.

```python
# Layer 1: Static Constants - 앱 시작 시 로드, 메모리 상주
class ConstantLoader:
    _cache: dict = None  # 앱 수명 동안 유지

    @classmethod
    def load_all(cls):
        if cls._cache is None:
            cls._cache = {
                "approval_rates": load_json("approval_rates.json"),
                "factor_adjustments": load_json("factor_adjustments.json"),
                "cap_rules": load_json("cap_rules.json"),
            }
        return cls._cache

# Layer 2: Pipeline - LRU 캐시 with TTL
class PipelineRepository:
    def __init__(self, cache: DiskCache):
        self.cache = cache  # M2에서 구현한 DiskCache

    def get_by_ticker(self, ticker: str) -> Pipeline:
        cache_key = f"pipeline:{ticker}"

        # 캐시 체크 (TTL: 1시간)
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # DB 조회
        pipeline = self._query_db(ticker)
        self.cache.set(cache_key, pipeline, ttl=3600)
        return pipeline

# Layer 3: Price Data - 날짜 기반 캐싱
class PriceRepository:
    def get_daily_prices(self, ticker: str, start: date, end: date):
        # 오늘 데이터는 짧은 TTL (장중 변동)
        # 과거 데이터는 긴 TTL (변동 없음)
        ...
```

---

**설계 6: 확장 시나리오**

**A (Architect)**: 미래에 데이터가 커지면?

| 시나리오 | 대응 |
|----------|------|
| 티커 10,000개 | SQLite 충분. 인덱스만 잘 걸면 됨 |
| 주가 10년치 | 파티셔닝 (연도별 테이블 분리) 또는 시계열 DB (TimescaleDB) |
| 실시간 주가 | 별도 서비스로 분리, Redis 캐시 |
| 글로벌 확장 | PostgreSQL 마이그레이션, Read Replica |

**E (SRE)**: 현재 단계에서는 SQLite로 충분해. 과도한 설계 피하자.

---

**설계 7: 레거시 v12 데이터셋 분석 (실제 구조)**

**B (Data)**: 레거시 `pdufa_ml_dataset_v12.json` 분석 결과야.

```
레거시 v12 현황:
- 총 케이스: 586건
- 필드 수: 103개 (케이스당)
- 파일 크기: 2.4MB
- 문제: 잘못된 데이터 다수 포함 (오염됨)
```

**필드 카테고리 분류 (103개)**:

```
1. 기본 정보 (9개)
   ticker, company, drug_name, drug_id, indication, pdufa_date,
   decision_date, result, notes

2. 신청 정보 (5개)
   application_type, application_number, is_bla, is_supplement, is_biosimilar

3. FDA 지정 (8개)
   orphan_drug, priority_review, breakthrough_therapy, accelerated_approval,
   fast_track, fda_designation_count, is_first_in_class, approval_type

4. AdCom 정보 (6개)
   adcom_held, adcom_vote_ratio, adcom_outcome, adcom_waived,
   adcom_marginal, has_adcom_flag

5. CRL 정보 (12개)
   crl_class, crl_class_num, crl_reason, crl_reason_category, crl_count,
   is_resubmission, cmc_only_crl, is_cmc_only, is_cmc_major, is_cmc_minor,
   crl_despite_endpoint_met, days_resub_to_pdufa

6. 제조 정보 (16개)
   cdmo_used, cdmo_name, cdmo_china_flag, manufacturing_country,
   facility_483_exists, facility_fda_registered_long, facility_location_high_risk,
   facility_ownership_change, facility_pai_passed, facility_recent_approval,
   facility_warning_letter, fda_483_critical, fda_483_exists, fda_483_flag,
   fda_483_recent, pai_* (6개)

7. 임상시험 정보 (22개)
   primary_endpoint_met, primary_pvalue, sample_size, nct_number,
   is_randomized, is_open_label, has_placebo_arm, single_arm_flag,
   single_trial_flag, clinical_hold_history, ct_*, enrollment_*, phase3_count,
   trial_region, disease_*, is_cns, is_oncology, is_rare_disease, spa_*

8. 메타/플래그 (25개+)
   target, data_source, source_confidence, sources, feature_sources,
   data_quality, approval_date, original_pdufa_date, resubmission_accepted_date,
   citizen_petition, 각종 *_flag, *_risk 필드들
```

**D (Trading)**: 103개 필드가 한 테이블에 있으면 문제야.

**A (Architect)**: 맞아. 그리고 필드는 더 늘어날 수 있어. 유연하게 설계해야 해.

---

**설계 8: 스키마 진화 전략**

**A (Architect)**: 필드가 늘어나거나 구조가 바뀔 수 있다. 세 가지 전략.

**전략 A: JSON 필드 + 정규화 혼합 (권장)**

```sql
-- 핵심 필드만 컬럼으로, 나머지는 JSON
CREATE TABLE pipelines (
    -- 조회/인덱싱 필요한 필드만 컬럼
    id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL,
    drug_name TEXT,
    pdufa_date DATE,
    result TEXT,

    -- 카테고리별 JSON (필드 추가 용이)
    basic_info JSON,           -- 기본 정보 나머지
    fda_designations JSON,     -- FDA 지정 전체
    adcom_info JSON,           -- AdCom 전체
    crl_info JSON,             -- CRL 전체
    manufacturing_info JSON,   -- 제조 전체
    clinical_info JSON,        -- 임상 전체
    metadata JSON,             -- 메타 전체

    -- 검증 상태 (필드별)
    verification JSON,         -- {"fda_designations": "CONFIRMED", "adcom_info": "UNKNOWN", ...}

    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**장점**:
- 새 필드 추가 시 스키마 변경 불필요
- 카테고리별로 묶여서 관리 용이
- 필드별 검증 상태 추적 가능

**전략 B: EAV (Entity-Attribute-Value) 패턴**

```sql
-- 극단적 유연성, 쿼리 복잡
CREATE TABLE pipeline_attributes (
    pipeline_id INTEGER,
    attribute_name TEXT,
    attribute_value TEXT,
    verification_status TEXT,
    source_url TEXT,
    updated_at TIMESTAMP
);
```

**장점**: 무한 확장 가능
**단점**: 쿼리 복잡, 성능 저하

**전략 C: 카테고리별 테이블 분리**

```sql
-- 관심사 분리, JOIN 필요
CREATE TABLE pipelines (...);           -- 기본
CREATE TABLE pipeline_fda_designations (...);  -- FDA 지정
CREATE TABLE pipeline_adcom (...);      -- AdCom
CREATE TABLE pipeline_crl (...);        -- CRL
CREATE TABLE pipeline_manufacturing (...);  -- 제조
CREATE TABLE pipeline_clinical (...);   -- 임상
```

**장점**: 정규화, 독립적 진화
**단점**: JOIN 많음, 초기 복잡도

---

**결정: 전략 A (JSON 필드 + 정규화 혼합)**

**E (SRE)**: 전략 A가 균형 잡혔어.
- 자주 조회하는 필드: 컬럼 (인덱싱)
- 나머지: JSON (유연성)
- 나중에 필요하면 JSON → 컬럼으로 승격 가능

**마이그레이션 경로**:
```
Step 1: v12 JSON → Pipeline 테이블 (JSON 필드 활용)
Step 2: 검증 완료된 필드부터 컬럼으로 승격
Step 3: 필요시 카테고리별 테이블 분리 (전략 C로 진화)
```

---

**설계 9: 필드별 검증 상태 추적**

**B (Data)**: 레코드 단위가 아니라 **필드 단위** 검증이 필요해.

```python
# 검증 상태 구조
{
    "ticker": {
        "status": "CONFIRMED",
        "source": "SEC EDGAR",
        "verified_at": "2026-01-08"
    },
    "fda_designations": {
        "breakthrough_therapy": {
            "status": "CONFIRMED",
            "source": "FDA CDER database",
            "verified_at": "2026-01-07"
        },
        "priority_review": {
            "status": "UNKNOWN",  # 미검증
            "source": null,
            "verified_at": null
        }
    },
    "adcom_vote_ratio": {
        "status": "MISMATCH",  # 불일치 발견
        "source": "FDA AdCom transcript",
        "legacy_value": 0.75,
        "verified_value": 0.68,
        "verified_at": "2026-01-08"
    }
}
```

**이점**:
1. 어떤 필드가 검증됐는지 추적 가능
2. 불일치 발견 시 legacy vs verified 비교 가능
3. 점진적 검증 (전체 다 검증 안 해도 사용 가능)

---

**결론: 데이터 구조 최종안**

```
src/tickergenius/
├── data/
│   ├── constants/           # Layer 1: JSON (Git 추적)
│   │   ├── approval_rates.json
│   │   ├── factor_adjustments.json
│   │   └── cap_rules.json
│   │
│   └── db/                  # Layer 2, 3: SQLite
│       └── tickergenius.db
│           ├── tickers        (기본 정보)
│           ├── pipelines      (파이프라인)
│           └── daily_prices   (주가)
│
└── repositories/            # 데이터 접근 레이어
    ├── __init__.py
    ├── constants.py         # Layer 1 로더
    ├── pipeline_repo.py     # Layer 2 Repository
    └── price_repo.py        # Layer 3 Repository
```

**핵심 원칙**:
1. **레이어 분리**: Static, Pipeline, TimeSeries 섞지 않음
2. **Repository 패턴**: 직접 DB 접근 금지, Repository 통해서만
3. **캐싱 전략**: 레이어별 다른 TTL
4. **확장 준비**: SQLite → PostgreSQL 마이그레이션 쉽게

---

## 토론 10: 보고서 생성 연계 설계

> **의제**: M3 분석 결과가 보고서 생성 도구로 어떻게 연결되는가?

---

**C (MCP)**: 사용자 관점에서 시나리오 정리하자.

```
시나리오 1: "OMER 분석해"
→ analyze_pdufa(OMER) 호출
→ Pipeline + 확률 + 요인 반환
→ Claude가 텍스트로 설명

시나리오 2: "OMER 보고서 만들어"
→ analyze_pdufa(OMER) 호출 (데이터 수집)
→ generate_report(OMER) 호출 (보고서 생성)
→ 마크다운/PDF 반환

시나리오 3: "이번 달 PDUFA 종합 보고서"
→ get_upcoming_pdufas(month) 호출 (목록)
→ 각 티커별 analyze_pdufa() 호출
→ generate_summary_report() 호출 (종합 보고서)
```

---

**설계 1: 분석 결과 → 보고서 입력**

**A (Architect)**: M3 분석 결과가 보고서에 필요한 모든 데이터를 포함해야 해.

```python
@dataclass
class AnalysisResult:
    """M3 분석 결과 - 보고서 생성의 입력이 됨"""

    # 기본 정보
    ticker: str
    drug_name: str
    indication: str
    pdufa_date: date

    # 확률 분석
    approval_probability: float     # 72%
    confidence_level: float         # 0.85
    factors: list[FactorResult]     # 각 요인별 영향

    # 타이밍 분석
    timing_signal: TimingSignal     # BUY/HOLD/SELL/AVOID
    signal_reasons: list[str]       # 신호 이유

    # 리스크 분석
    risk_level: str                 # LOW/MEDIUM/HIGH
    risk_factors: list[str]         # 리스크 요인

    # 경고/에러
    warnings: list[str]
    errors: list[str]

    # 메타
    analyzed_at: datetime
    data_freshness: str             # "2시간 전 업데이트"
```

**핵심**: 보고서 생성기는 `AnalysisResult`만 받으면 됨. M3 내부 구현 몰라도 됨.

---

**설계 2: 보고서 생성 도구 (M4)**

**C (MCP)**: 보고서 도구는 M4에서 구현하지만, 인터페이스는 미리 정의.

```python
# M4에서 구현할 MCP 도구

@mcp.tool()
def generate_report(
    ticker: str,
    format: str = "markdown",  # markdown, html, json
    sections: list[str] = None  # ["summary", "probability", "risks", "recommendation"]
) -> str:
    """
    PDUFA 분석 보고서 생성

    1. analyze_pdufa(ticker) 호출하여 데이터 수집
    2. 템플릿에 데이터 적용
    3. 포맷에 맞게 변환
    """
    # 1. 분석
    result: AnalysisResult = analyze_pdufa(ticker)

    # 2. 템플릿 적용
    report = ReportGenerator(result).generate(
        format=format,
        sections=sections or ["summary", "probability", "risks", "recommendation"]
    )

    return report


@mcp.tool()
def generate_summary_report(
    start_date: date,
    end_date: date,
    min_probability: float = 0.0
) -> str:
    """
    기간 내 PDUFA 종합 보고서

    1. 기간 내 파이프라인 목록 조회
    2. 각각 analyze_pdufa() 호출
    3. 종합 테이블 + 요약 생성
    """
    ...
```

---

**설계 3: 보고서 템플릿 구조**

**D (Trading)**: 실제 보고서에 뭐가 들어가야 하냐면...

```markdown
# OMER PDUFA 분석 보고서

## 요약 (Summary)
- **티커**: OMER
- **약물**: Omidria
- **적응증**: 백내장 수술
- **PDUFA**: 2026-02-15
- **승인 확률**: 72% (신뢰도: 85%)
- **투자 신호**: HOLD

## 확률 분석 (Probability Breakdown)
| 요인 | 영향 | 설명 |
|------|------|------|
| 기본 승인률 | 65% | Phase 3 기준 |
| BTD 지정 | +8% | 희귀질환 |
| AdCom 긍정 | +5% | 12-2 통과 |
| CRL 이력 | -6% | 제조 문제 (해결됨) |
| **최종** | **72%** | |

## 리스크 요인
- 제조 시설 재검사 필요
- 경쟁사 동일 적응증 진입

## 투자 권고
현재 주가와 확률 대비 적정 수준.
PDUFA 2주 전 재평가 권장.

---
*생성: 2026-01-08 14:30*
*데이터: 2시간 전 업데이트*
```

---

**설계 4: 연계 아키텍처**

```
┌─────────────────────────────────────────────────────────────┐
│  사용자 요청                                                 │
│  "OMER 보고서 만들어"                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  M4: MCP Layer                                              │
│  generate_report(ticker="OMER")                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  M3: Analysis Layer                                         │
│  PDUFAAnalyzer.analyze("OMER") → AnalysisResult            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ - PipelineRepository.get("OMER")                    │   │
│  │ - ConstantLoader.get_rates()                        │   │
│  │ - ProbabilityCalculator.calculate()                 │   │
│  │ - TimingAnalyzer.analyze()                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  M3: Report Generator                                       │
│  ReportGenerator(result).generate(format="markdown")       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ - 템플릿 로드                                        │   │
│  │ - 섹션별 렌더링                                      │   │
│  │ - 포맷 변환                                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  결과: 마크다운 보고서                                       │
└─────────────────────────────────────────────────────────────┘
```

---

**설계 5: 확장 포인트**

**A (Architect)**: 나중에 추가될 수 있는 것들.

| 기능 | 위치 | 설계 |
|------|------|------|
| PDF 출력 | ReportGenerator | format="pdf" 추가 |
| 차트 포함 | ReportGenerator | matplotlib/plotly 연동 |
| 이메일 발송 | M4 MCP 도구 | send_report() 추가 |
| 정기 보고서 | M5 스케줄러 | 크론잡으로 generate_summary 호출 |
| 다국어 | ReportGenerator | 템플릿 다국어화 |

---

**설계 6: 인터페이스 계약**

**E (SRE)**: M3와 보고서 생성기 사이의 계약을 명확히.

```python
# M3가 제공하는 인터페이스 (analysis/pdufa/__init__.py)

def analyze(ticker: str) -> AnalysisResult:
    """
    티커의 PDUFA 분석 수행

    Returns:
        AnalysisResult - 보고서 생성에 필요한 모든 데이터 포함

    Raises:
        TickerNotFoundError - 티커 없음
        DataStaleError - 데이터 너무 오래됨 (경고와 함께 진행 가능)
    """
    ...

def analyze_batch(tickers: list[str]) -> list[AnalysisResult]:
    """
    여러 티커 일괄 분석 (병렬 처리)
    """
    ...

def get_upcoming(days: int = 30) -> list[AnalysisResult]:
    """
    N일 내 PDUFA 예정 파이프라인 분석
    """
    ...
```

**보고서 생성기가 이 인터페이스만 사용하면 됨. 내부 구현 변경해도 영향 없음.**

---

**결론**:

1. **AnalysisResult가 계약**: M3 출력 = 보고서 입력
2. **템플릿 기반**: 마크다운 템플릿으로 유연하게
3. **포맷 확장 쉽게**: markdown → html → pdf
4. **배치 지원**: analyze_batch()로 종합 보고서 지원
5. **인터페이스 안정**: 내부 변경해도 보고서 생성기 영향 없음

---

## 토론 컨센서스 정리

| 토론 | 핵심 결정 | 합의 내용 |
|------|-----------|-----------|
| **토론 1** | MCP 도구 설계 | 하이브리드: `analyze_pdufa` (메인) + `explain_probability` (보조) |
| **토론 2** | 모듈 확장성 | 독립 모듈 + 공통 인터페이스 (BaseAnalyzer). M3는 PDUFA만 |
| **토론 3** | 데이터 오염 방지 | StatusField 3-state (CONFIRMED/EMPTY/UNKNOWN) + source URL 필수 |
| **토론 4** | 에러 처리 | 예외 최소화, errors/warnings 필드로 반환. MCP 호환성 |
| **토론 5** | 캐싱 전략 | M2 DiskCache 활용. TTL: 상수(영구), 분석결과(1시간), 주가(10분) |
| **토론 6** | 확률 계산 복잡도 | 레거시 13개 레이어 파악. 복잡도 유지하되 확장성 확보 |
| **토론 7** | 확장성 패턴 | FactorRegistry (팩터 등록/비활성화) + AnalysisContext (입력 객체화) |
| **토론 8** | 상수 관리 | JSON 파일 + Python 래퍼. 검증 쿼리 템플릿 + 캐싱 |
| **토론 9** | 데이터셋 설계 | 3계층 (Static/Pipeline/TimeSeries). JSON+정규화 혼합. **필드 단위 검증** |
| **토론 10** | 보고서 연계 | AnalysisResult가 계약. ReportGenerator는 M3 내부 모름 |

**핵심 원칙 합의**:
1. 레거시 데이터는 **오염됨** - 무조건 재검증 필요
2. 파일당 **500줄 이하** - 스파게티 방지
3. **필드 단위** 검증 추적 - 점진적 정화
4. **확장성 우선** - FactorRegistry로 팩터 추가/제거 용이
5. **느슨한 결합** - Repository 패턴, 인터페이스 계약

---

## 최종 설계 결정 요약 (Final)

| 항목 | 결정 | 근거 | 출처 |
|------|------|------|------|
| MCP 도구 | 하이브리드 (analyze_pdufa + explain_probability) | 90% 단일 커버 + 상세 분석 | 토론 1 |
| 확장성 패턴 | FactorRegistry + AnalysisContext | 팩터 추가/제거/비활성화 용이 | 토론 7 |
| 데이터 레이어 | 3계층 (Static/Pipeline/TimeSeries) | 성장 패턴, 접근 패턴 다름 | 토론 9 |
| 스키마 전략 | JSON 필드 + 정규화 혼합 | 유연성 + 성능 균형 | 토론 9 설계 8 |
| 필드 수 대응 | 카테고리별 JSON 컬럼 (103+ 필드) | 스키마 진화 용이 | 토론 9 설계 7 |
| 데이터 검증 | **필드 단위** 검증 상태 추적 | 오염 데이터 점진적 정화 | 토론 9 설계 9 |
| 상수 관리 | JSON 파일 + Python 래퍼 | Git 추적 + 타입 안전 | 토론 8 |
| 에러 처리 | 예외 최소화, errors/warnings 필드 | MCP 호환성 | 토론 4 |
| 캐싱 | M2 DiskCache, 레이어별 TTL | 성능 | 토론 5 |
| 보고서 연계 | AnalysisResult → ReportGenerator | 느슨한 결합 | 토론 10 |

---

## 구현 순서 (M3)

```
Phase 0: 레거시 마이그레이션 준비
□ 레거시 v12 JSON → 새 스키마 매핑 정의
□ 필드 카테고리별 JSON 구조 설계
□ 검증 상태 초기화 (모든 필드 UNKNOWN)

Phase 1: 데이터 레이어
□ data/constants/*.json - 상수 JSON 파일들 (factor_adjustments, cap_rules 등)
□ repositories/constants.py - JSON 로더 + 타입 래퍼
□ repositories/pipeline_repo.py - Pipeline Repository (JSON 필드 활용)
□ 스키마 확인 및 업데이트 (M1과 정합성)

Phase 2: 확률 계산 엔진
□ analysis/pdufa/_context.py - AnalysisContext (입력 객체화)
□ analysis/pdufa/_registry.py - FactorRegistry (Open-Closed)
□ analysis/pdufa/_layers/*.py - 13개 레이어 (base, designation, adcom, crl, ...)
□ analysis/pdufa/probability.py - ProbabilityCalculator

Phase 3: Facade 및 보고서
□ analysis/pdufa/analyzer.py - PDUFAAnalyzer (Public API)
□ analysis/pdufa/result.py - AnalysisResult (보고서 연계용)
□ analysis/pdufa/report.py - ReportGenerator (선택적)

Phase 4: 테스트 및 검증
□ 단위 테스트 (레이어별)
□ 통합 테스트 (전체 파이프라인)
□ 레거시 결과 비교 테스트 (regression)
□ 에지 케이스 테스트

Phase 5: 데이터 정화 (점진적)
□ 레거시 v12 import
□ 필드별 웹 검증 (우선순위대로)
□ 검증 완료 필드 컬럼 승격 (필요시)
```

---

## 정합성 체크리스트

```
□ M1 스키마와 Pipeline 구조 일치
□ M2 DiskCache 참조 정확
□ FactorRegistry 팩터 목록과 레거시 13개 레이어 일치
□ AnalysisResult 필드와 보고서 템플릿 일치
□ JSON 필드 구조와 레거시 v12 카테고리 일치
□ 검증 상태 Enum과 토론 8 정의 일치
```

---

**M3 진행 승인 대기 중**
