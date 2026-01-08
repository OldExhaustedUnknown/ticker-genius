# Phase 3: New Architecture Blueprint

**작성일**: 2026-01-07
**작성자**: 5인 전문가 팀 (A: 아키텍트, B: 데이터, C: MCP, D: 트레이딩, E: SRE)

---

## 3.1 설계 원칙

### 핵심 원칙: Anti-Pollution Architecture

> **"일회용 스크립트 양산 구조를 원하지 않는다"** - 사용자 요구사항

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANTI-POLLUTION PRINCIPLES                     │
├─────────────────────────────────────────────────────────────────┤
│ 1. 모든 기능은 반드시 모듈 내에 존재                            │
│ 2. 스크립트는 CLI 진입점만 제공 (로직 금지)                      │
│ 3. 문서는 코드와 동기화된 버전 관리                              │
│ 4. 미사용 코드는 자동 탐지 및 경고                              │
│ 5. 실험 코드는 별도 브랜치, 머지 전 정리 필수                    │
└─────────────────────────────────────────────────────────────────┘
```

### 5인 전문가 합의 원칙

| 원칙 | 설명 | 담당 전문가 |
|------|------|------------|
| **Single Source of Truth** | 버전, 설정, 스키마는 단일 소스에서만 정의 | A (아키텍트) |
| **Schema-First Development** | 데이터 구조 변경은 반드시 스키마 먼저 | B (데이터) |
| **Tool Contract Specification** | 모든 MCP 도구는 명세서 필수 | C (MCP) |
| **Safety by Default** | 트레이딩은 Paper 모드 기본, 실거래 명시적 활성화 | D (트레이딩) |
| **Observable Everything** | 모든 동작은 로깅, 모니터링 가능 | E (SRE) |

---

## 3.2 문서-코드 버전 동기화 시스템

### 3.2.1 버전 정의 구조

```
src/tickergenius/__version__.py  ← 단일 버전 소스 (Single Source of Truth)
├── __version__ = "4.0.0"
├── __schema_version__ = "1.0.0"
└── __api_version__ = "v1"
```

### 3.2.2 버전 자동 동기화 메커니즘

```python
# pyproject.toml에서 동적 버전 읽기
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/tickergenius/__version__.py"
```

### 3.2.3 문서 버전 헤더 규칙

모든 기술 문서는 다음 헤더를 포함:

```markdown
---
doc_version: "1.0.0"
code_version: "4.0.0"  # 이 문서가 설명하는 코드 버전
last_sync: "2026-01-07"
status: current | outdated | deprecated
---
```

### 3.2.4 버전 불일치 탐지 (CI/CD)

```yaml
# .github/workflows/doc-sync-check.yml
- name: Check doc-code version sync
  run: |
    python scripts/ci/check_doc_versions.py
    # 문서의 code_version과 실제 코드 버전 비교
    # 불일치 시 PR 차단
```

---

## 3.3 디렉토리 구조

```
d:\ticker-genius\
├── src/
│   └── tickergenius/
│       ├── __init__.py
│       ├── __version__.py          # 단일 버전 소스
│       │
│       ├── schemas/                 # Pydantic 스키마 (M1 완료)
│       │   ├── __init__.py
│       │   ├── base.py             # StatusField 3-state
│       │   ├── pipeline.py         # Pipeline, PDUFAEvent
│       │   ├── manufacturing.py    # Manufacturing 스키마
│       │   ├── clinical.py         # ClinicalTrial 스키마
│       │   └── data_quality.py     # DataQuality 스키마
│       │
│       ├── core/                    # 핵심 인프라
│       │   ├── __init__.py
│       │   ├── config.py           # 설정 관리
│       │   ├── cache.py            # 디스크 캐시
│       │   ├── http.py             # HTTP 클라이언트
│       │   └── logging.py          # 구조화 로깅
│       │
│       ├── data/                    # 데이터 계층
│       │   ├── __init__.py
│       │   ├── yfinance.py         # yfinance 래퍼
│       │   ├── sec.py              # SEC EDGAR 클라이언트
│       │   ├── clinical.py         # ClinicalTrials.gov
│       │   └── repository.py       # 데이터 저장소 인터페이스
│       │
│       ├── analysis/                # 분석 모듈
│       │   ├── __init__.py
│       │   └── pdufa/              # PDUFA 분석 (우선순위 1)
│       │       ├── __init__.py
│       │       ├── enums.py        # Enum 정의
│       │       ├── probability.py  # 확률 계산
│       │       └── analyzer.py     # 분석기 Facade
│       │
│       ├── ml/                      # 머신러닝
│       │   ├── __init__.py
│       │   ├── features.py         # 피처 스토어
│       │   ├── bayesian.py         # 베이지안 업데이트
│       │   └── trainer.py          # 모델 학습기
│       │
│       ├── mcp/                     # MCP 서버
│       │   ├── __init__.py
│       │   ├── server.py           # FastMCP 서버 (진입점)
│       │   ├── tools/              # MCP 도구들
│       │   │   ├── __init__.py
│       │   │   ├── _registry.py    # 도구 레지스트리
│       │   │   ├── fda.py          # FDA 도구
│       │   │   ├── market.py       # 시장 데이터 도구
│       │   │   ├── backtest.py     # 백테스팅 도구
│       │   │   └── meme.py         # 밈주 분석 도구
│       │   └── prompts/            # 프롬프트 템플릿
│       │       └── __init__.py
│       │
│       └── trading/                 # 트레이딩 (별도 활성화)
│           ├── __init__.py
│           ├── _safety.py          # 안전장치 (Kill Switch)
│           ├── paper.py            # Paper Trading
│           ├── risk.py             # 리스크 관리
│           └── alpaca/             # Alpaca 연동 (별도 모듈)
│               ├── __init__.py
│               └── client.py
│
├── scripts/                         # CLI 진입점만 (로직 금지!)
│   ├── ci/                         # CI/CD 스크립트
│   │   ├── check_doc_versions.py
│   │   └── find_unused_code.py
│   └── cli/                        # CLI 명령
│       ├── migrate.py              # 마이그레이션 CLI
│       └── server.py               # MCP 서버 실행
│
├── tests/                           # 테스트
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/                            # 문서
│   ├── PHASE1_ANALYSIS.md
│   ├── PHASE2_ISSUE_PORTING.md
│   ├── PHASE3_ARCHITECTURE.md      # 이 문서
│   ├── api/                        # API 문서 (자동 생성)
│   └── tools/                      # 도구별 명세서
│       └── TOOL_SPEC_TEMPLATE.md
│
├── data/                            # 데이터 (코드 아님)
│   └── pipelines/
│       └── by_ticker/
│
├── pyproject.toml                   # 프로젝트 설정
├── CHANGELOG.md                     # 변경 이력
└── README.md
```

---

## 3.4 스크립트 양산 방지 정책

### 3.4.1 스크립트 규칙

```
┌─────────────────────────────────────────────────────────────────┐
│                      SCRIPT POLICY                              │
├─────────────────────────────────────────────────────────────────┤
│ 허용되는 스크립트:                                               │
│   ✓ CLI 진입점 (argparse + 모듈 호출)                           │
│   ✓ CI/CD 자동화 스크립트                                        │
│   ✓ 일회성 마이그레이션 (완료 후 삭제)                           │
│                                                                 │
│ 금지되는 스크립트:                                               │
│   ✗ 비즈니스 로직 포함                                           │
│   ✗ 데이터 처리 로직 포함                                        │
│   ✗ 분석 알고리즘 포함                                           │
│   ✗ "임시" 수정 코드                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4.2 스크립트 템플릿

```python
#!/usr/bin/env python
# scripts/cli/example.py
"""
CLI Entry Point - 로직 없음, 호출만.

Usage:
    python -m scripts.cli.example --ticker AAPL
"""
import argparse
from tickergenius.analysis.pdufa import PDUFAAnalyzer  # 실제 로직은 모듈에

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args()

    # 모듈 호출만, 로직 없음
    analyzer = PDUFAAnalyzer()
    result = analyzer.analyze(args.ticker)
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
```

### 3.4.3 미사용 코드 탐지

```python
# scripts/ci/find_unused_code.py
# CI에서 주기적 실행, 미사용 모듈/함수 탐지

# 탐지 대상:
# 1. import되지 않는 모듈
# 2. 호출되지 않는 public 함수
# 3. 테스트되지 않는 코드 경로

# 결과: PR 코멘트로 경고, 2주 미조치 시 삭제 후보 등록
```

---

## 3.5 MCP 도구 설계

### 3.5.1 도구 레지스트리 패턴

```python
# src/tickergenius/mcp/tools/_registry.py
from typing import Dict, Callable
from dataclasses import dataclass

@dataclass
class ToolSpec:
    """도구 명세서 - 모든 도구는 이 형식 필수"""
    name: str
    description: str
    version: str
    category: str  # fda | market | analysis | trading
    input_schema: dict
    output_schema: dict
    doc_path: str  # 문서 경로

TOOL_REGISTRY: Dict[str, ToolSpec] = {}

def register_tool(spec: ToolSpec):
    """도구 등록 데코레이터"""
    def decorator(func: Callable):
        TOOL_REGISTRY[spec.name] = spec
        func._tool_spec = spec
        return func
    return decorator
```

### 3.5.2 도구 명세서 템플릿

```markdown
# docs/tools/TOOL_SPEC_TEMPLATE.md

---
tool_name: "analyze_pdufa"
tool_version: "1.0.0"
code_version: "4.0.0"
category: "fda"
status: active
---

## 목적
PDUFA 날짜 기반 FDA 승인 확률 분석

## 입력 스키마
```json
{
  "ticker": "string (required)",
  "include_history": "boolean (default: true)"
}
```

## 출력 스키마
```json
{
  "ticker": "string",
  "probability": "float (0-1)",
  "factors": "array<Factor>",
  "confidence": "string (high|medium|low)"
}
```

## 의존성
- `tickergenius.analysis.pdufa.analyzer`
- `tickergenius.data.sec`

## 사용 예시
```
analyze_pdufa(ticker="FBIO", include_history=true)
```

## 변경 이력
| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0.0 | 2026-01-07 | 초기 버전 |
```

### 3.5.3 MCP 도구 목록

> **상세 내용**: [Phase 5: 도구 로드맵](./PHASE5_TOOL_ROADMAP.md) 참조
>
> Phase 5 문서에서 레거시 55개 도구를 분석하여 25개로 통폐합한 전체 로드맵을 확인할 수 있습니다.

#### 핵심 도구 요약 (M3 기준)

| 도구명 | Tier | 설명 | 우선순위 |
|--------|------|------|----------|
| `get_ticker_info` | READ | 통합 티커 정보 (yfinance→FMP→Polygon 폴백) | P0 |
| `get_pipeline` | READ | 파이프라인 데이터 조회 (신규 스키마) | P0 |
| `get_crl_history` | READ | CRL 이력 조회 | P0 |
| `calculate_pdufa_probability` | ANALYSIS | PDUFA 승인 확률 (rule/ml/hybrid 통합) | P0 |
| `analyze_biotech` | ANALYSIS | 바이오텍 종합 분석 | P1 |
| `scan_stocks` | READ | 통합 스캐너 (meme/biotech/general) | P1 |
| `self_check` | READ | 시스템 진단 | P0 |

#### 도구 분류 체계 (3-Tier)

- **Tier 1 (READ)**: 데이터 조회만, 부작용 없음, 캐시 활용
- **Tier 2 (ANALYSIS)**: 계산/분석, CPU 집약적, 결과 캐시 가능
- **Tier 3 (ACTION)**: 외부 효과 발생, 확인 필요, 감사 로깅

---

## 3.6 데이터 무결성 정책

### 3.6.1 StatusField 3-State System (M1 확립)

```
CONFIRMED ─── 출처 명시, 검증 완료
EMPTY ─────── 해당 없음 (예: AdCom 미개최)
UNKNOWN ───── 미확인, 추가 조사 필요
```

### 3.6.2 데이터 변경 규칙

```python
# 데이터 변경 시 반드시 준수

class DataMutationPolicy:
    """
    1. 모든 변경은 source 필드 필수
    2. CONFIRMED → UNKNOWN 전환 금지 (데이터 품질 하락)
    3. 변경 이력은 별도 로그 테이블에 보존
    """

    @staticmethod
    def validate_transition(old_status: str, new_status: str) -> bool:
        # CONFIRMED에서 UNKNOWN으로 전환 방지
        if old_status == "CONFIRMED" and new_status == "UNKNOWN":
            raise ValueError("Cannot downgrade CONFIRMED to UNKNOWN")
        return True
```

### 3.6.3 스키마 버전 마이그레이션

```python
# 스키마 변경 시 마이그레이션 스크립트 필수

SCHEMA_VERSION = "1.0.0"

def migrate_v1_to_v2(data: dict) -> dict:
    """
    v1 → v2 마이그레이션

    변경 사항:
    - field_a → field_b 이름 변경
    - new_field 추가 (기본값: null)
    """
    # 마이그레이션 로직
    pass
```

---

## 3.7 트레이딩 안전 설계

### 3.7.1 안전 계층 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                     TRADING SAFETY LAYERS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: ENVIRONMENT CHECK                                     │
│  ─────────────────────────────                                  │
│  TRADING_MODE 환경변수 확인                                      │
│  - 미설정 시: PAPER (기본값)                                     │
│  - "LIVE" 명시 시에만 실거래                                     │
│                                                                 │
│  Layer 2: CONFIRMATION                                          │
│  ─────────────────────────                                      │
│  실거래 모드 진입 시 2단계 확인                                   │
│  - 환경변수 LIVE_TRADING_CONFIRMED="yes-i-understand"            │
│  - 코드 내 explicit enable 호출                                  │
│                                                                 │
│  Layer 3: KILL SWITCH                                           │
│  ───────────────────────                                        │
│  - 일일 손실 한도 초과 시 자동 정지                              │
│  - 포지션 한도 초과 시 신규 주문 차단                            │
│  - 수동 Kill Switch API 제공                                     │
│                                                                 │
│  Layer 4: DRY-RUN                                               │
│  ─────────────────────                                          │
│  - 모든 주문 로직 실행, 실제 전송만 생략                         │
│  - 로그에 "[DRY-RUN]" 표시                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.7.2 트레이딩 모듈 구조

```python
# src/tickergenius/trading/_safety.py

import os
from enum import Enum

class TradingMode(Enum):
    PAPER = "paper"      # 기본값
    DRY_RUN = "dry_run"  # 로직 실행, 전송 생략
    LIVE = "live"        # 실거래

def get_trading_mode() -> TradingMode:
    """환경변수에서 트레이딩 모드 결정"""
    mode = os.getenv("TRADING_MODE", "paper").lower()

    if mode == "live":
        # 2단계 확인
        confirmed = os.getenv("LIVE_TRADING_CONFIRMED")
        if confirmed != "yes-i-understand":
            raise RuntimeError(
                "LIVE trading requires LIVE_TRADING_CONFIRMED='yes-i-understand'"
            )
        return TradingMode.LIVE

    if mode == "dry_run":
        return TradingMode.DRY_RUN

    return TradingMode.PAPER  # 기본값

class KillSwitch:
    """비상 정지 스위치"""

    def __init__(self, daily_loss_limit: float = 1000.0):
        self.daily_loss_limit = daily_loss_limit
        self._is_killed = False
        self._daily_loss = 0.0

    def check(self) -> bool:
        """거래 가능 여부 확인"""
        if self._is_killed:
            return False
        if self._daily_loss >= self.daily_loss_limit:
            self._is_killed = True
            return False
        return True

    def kill(self):
        """수동 Kill Switch 활성화"""
        self._is_killed = True
```

### 3.7.3 트레이딩 Issue 해결 (TRADE-001, 002, 003)

| Issue | 해결 방안 |
|-------|----------|
| TRADE-001 (S0) | `TradingMode.PAPER` 기본값 + 2단계 확인 |
| TRADE-002 (S1) | `KillSwitch` 클래스 구현 |
| TRADE-003 (S1) | `daily_loss_limit`, `position_limit` 하드코딩 |

---

## 3.8 로깅 및 모니터링

### 3.8.1 구조화 로깅

```python
# src/tickergenius/core/logging.py

import logging
import json
from datetime import datetime

class StructuredLogger:
    """MCP 환경 호환 구조화 로깅"""

    def __init__(self, name: str, log_file: str = None):
        self.logger = logging.getLogger(name)

        # 파일 핸들러 (MCP의 stdio 제약 회피)
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(self._get_json_formatter())
            self.logger.addHandler(handler)

    def _get_json_formatter(self):
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                return json.dumps({
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "module": record.module,
                    "message": record.getMessage(),
                    "extra": getattr(record, "extra", {})
                })
        return JsonFormatter()

    def info(self, message: str, **extra):
        self.logger.info(message, extra={"extra": extra})
```

### 3.8.2 Issue 해결 (OPS-001)

```
문제: 로깅이 stderr로 출력 (MCP 환경)
해결: 파일 로깅 + 구조화 JSON 포맷
```

---

## 3.9 구현 우선순위

### Phase 1 구현 범위 (즉시)

```
Priority 0 (P0): 핵심 인프라
├── __version__.py 단일 소스
├── core/config.py
├── core/cache.py
├── core/logging.py
└── schemas/ (M1 완료)

Priority 1 (P1): PDUFA 분석
├── analysis/pdufa/enums.py
├── analysis/pdufa/probability.py
├── analysis/pdufa/analyzer.py
└── data/repository.py

Priority 2 (P2): MCP 도구
├── mcp/server.py
├── mcp/tools/fda.py
└── mcp/tools/market.py
```

### Phase 2 구현 범위 (이후)

```
Priority 3 (P3): ML 모듈
├── ml/features.py
├── ml/bayesian.py
└── ml/trainer.py

Priority 4 (P4): 추가 도구
├── mcp/tools/backtest.py
└── mcp/tools/meme.py
```

### Phase 3 구현 범위 (별도 검증 후)

```
Priority 5 (P5): 트레이딩
├── trading/_safety.py
├── trading/paper.py
├── trading/risk.py
└── trading/alpaca/
```

---

## 3.10 검증 체크리스트

### 코드 머지 전 필수 확인

- [ ] 버전 동기화: `__version__.py`와 문서 `code_version` 일치
- [ ] 스키마 변경 시 마이그레이션 스크립트 포함
- [ ] MCP 도구 추가 시 명세서 포함 (`docs/tools/`)
- [ ] 스크립트 신규 생성 시 로직 없음 확인
- [ ] 테스트 커버리지 80% 이상
- [ ] 트레이딩 코드 변경 시 Safety Layer 영향 분석

### 주기적 검증 (주간)

- [ ] 미사용 코드 탐지 스크립트 실행
- [ ] 문서 outdated 상태 확인
- [ ] 의존성 취약점 스캔

---

## 3.11 5인 전문가 서명

| 전문가 | 역할 | 주요 기여 | 승인 |
|--------|------|----------|------|
| A | 아키텍트 | 전체 구조, 버전 동기화 | ✓ |
| B | 데이터 | 스키마 정책, 데이터 무결성 | ✓ |
| C | MCP | 도구 레지스트리, 명세서 템플릿 | ✓ |
| D | 트레이딩 | Safety Layer, Kill Switch | ✓ |
| E | SRE | 로깅, 모니터링, CI/CD | ✓ |

---

## 3.12 모듈 인터페이스 계약 (Module Contracts)

### 3.12.1 계층 의존성 규칙

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY FLOW (단방향)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   mcp/tools/     ──────────►  analysis/     ──────────►  core/  │
│   (최상위)                    (중간)                    (최하위)│
│       │                          │                         │    │
│       │                          ▼                         │    │
│       └─────────────────►    data/     ◄───────────────────┘    │
│                             (데이터 계층)                        │
│                                                                 │
│   금지: core/ → analysis/ (역방향 의존 금지)                     │
│   금지: schemas/ → 다른 모듈 (스키마는 독립)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.12.2 schemas/ 계약

```python
# schemas/는 다른 모듈에 의존하지 않음 (순수 데이터 정의)
# 모든 모듈은 schemas/를 import 가능

# 입력/출력 타입으로만 사용
class PDUFAAnalyzer:
    def analyze(self, ticker: str) -> Pipeline:  # schemas.Pipeline 반환
        pass
```

### 3.12.3 core/ 계약

```python
# core/config.py
class Config:
    """설정 관리 - 환경변수 우선"""
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any: ...
    @classmethod
    def require(cls, key: str) -> Any: ...  # 없으면 예외

# core/cache.py
class DiskCache:
    """티커별 디스크 캐시"""
    def get(self, ticker: str, key: str) -> Optional[dict]: ...
    def set(self, ticker: str, key: str, value: dict, ttl: int = 3600): ...
    def invalidate(self, ticker: str, key: str = None): ...

# core/http.py
class HTTPClient:
    """재시도, 레이트리밋 내장 HTTP 클라이언트"""
    async def get(self, url: str, **kwargs) -> Response: ...
    async def post(self, url: str, **kwargs) -> Response: ...

# core/logging.py
class StructuredLogger:
    """JSON 구조화 로거"""
    def info(self, message: str, **context): ...
    def error(self, message: str, exc: Exception = None, **context): ...
    def audit(self, action: str, **context): ...  # 감사 로그
```

### 3.12.4 data/ 계약

```python
# data/repository.py
class PipelineRepository:
    """파이프라인 데이터 저장소"""
    def get_by_ticker(self, ticker: str) -> Optional[Pipeline]: ...
    def save(self, pipeline: Pipeline): ...
    def list_tickers(self) -> list[str]: ...
    def search(self, **filters) -> list[Pipeline]: ...

# data/sec.py
class SECClient:
    """SEC EDGAR API 클라이언트"""
    async def get_filings(self, ticker: str, form_type: str = None) -> list[Filing]: ...
    async def get_filing_content(self, accession: str) -> str: ...

# data/yfinance.py
class MarketDataClient:
    """시장 데이터 클라이언트 (yfinance 래핑)"""
    def get_price(self, ticker: str) -> Price: ...
    def get_history(self, ticker: str, period: str = "1y") -> pd.DataFrame: ...
```

### 3.12.5 analysis/ 계약

```python
# analysis/pdufa/analyzer.py
class PDUFAAnalyzer:
    """PDUFA 분석기 - Facade 패턴"""

    def __init__(self, repo: PipelineRepository = None):
        self.repo = repo or PipelineRepository()

    def analyze(self, ticker: str) -> Pipeline:
        """단일 티커 분석"""
        ...

    def calculate_probability(self, event: PDUFAEvent) -> float:
        """승인 확률 계산 (0.0 ~ 1.0)"""
        ...

    def get_factors(self, ticker: str) -> list[Factor]:
        """확률 영향 요인 목록"""
        ...
```

### 3.12.6 mcp/tools/ 계약

```python
# mcp/tools/fda.py
# 각 도구는 ToolSpec과 함께 등록

@register_tool(ToolSpec(
    name="analyze_pdufa",
    description="PDUFA 승인 확률 분석",
    version="1.0.0",
    category="fda",
    input_schema={
        "ticker": {"type": "string", "required": True},
        "include_history": {"type": "boolean", "default": True}
    },
    output_schema={
        "ticker": "string",
        "probability": "float",
        "confidence": "string",
        "factors": "array<Factor>"
    },
    doc_path="docs/tools/analyze_pdufa.md"
))
async def analyze_pdufa(ticker: str, include_history: bool = True) -> dict:
    """
    계약:
    - 입력: ticker (필수), include_history (선택, 기본 True)
    - 출력: 표준 응답 dict (model_dump 형식)
    - 에러: TickerNotFoundError, DataFetchError
    """
    analyzer = PDUFAAnalyzer()
    result = analyzer.analyze(ticker)
    return result.model_dump()
```

---

## 3.13 에러 처리 전략

### 3.13.1 예외 계층 구조

```python
# src/tickergenius/core/exceptions.py

class TickerGeniusError(Exception):
    """베이스 예외 - 모든 커스텀 예외의 부모"""
    pass

# 데이터 관련
class DataError(TickerGeniusError):
    """데이터 계층 에러"""
    pass

class TickerNotFoundError(DataError):
    """티커를 찾을 수 없음"""
    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Ticker not found: {ticker}")

class DataFetchError(DataError):
    """외부 데이터 조회 실패"""
    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"Failed to fetch from {source}: {reason}")

# 설정 관련
class ConfigError(TickerGeniusError):
    """설정 에러"""
    pass

class MissingAPIKeyError(ConfigError):
    """필수 API 키 누락"""
    def __init__(self, key_name: str):
        self.key_name = key_name
        super().__init__(f"Missing required API key: {key_name}")

# 트레이딩 관련
class TradingError(TickerGeniusError):
    """트레이딩 에러"""
    pass

class KillSwitchActiveError(TradingError):
    """Kill Switch 활성화 상태"""
    pass

class InsufficientFundsError(TradingError):
    """자금 부족"""
    pass
```

### 3.13.2 에러 처리 규칙

```
┌─────────────────────────────────────────────────────────────────┐
│                      ERROR HANDLING RULES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CATCH EARLY, THROW LATE                                     │
│     - 최하위 계층에서 원인 파악, 상위 계층에서 처리 결정        │
│                                                                 │
│  2. NEVER SWALLOW EXCEPTIONS                                    │
│     - except: pass 금지                                         │
│     - 반드시 로깅 또는 재발생                                    │
│                                                                 │
│  3. SPECIFIC EXCEPTIONS                                         │
│     - Exception 직접 catch 금지                                 │
│     - 구체적인 예외 타입만 catch                                 │
│                                                                 │
│  4. MCP TOOL ERROR FORMAT                                       │
│     - 도구는 항상 dict 반환 (에러 시에도)                        │
│     - {"error": true, "code": "...", "message": "..."}           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.13.3 MCP 도구 에러 응답 표준

```python
# MCP 도구에서 에러 반환 시 표준 형식

def tool_error_response(code: str, message: str, details: dict = None) -> dict:
    return {
        "error": True,
        "code": code,
        "message": message,
        "details": details or {}
    }

# 사용 예시
@register_tool(...)
async def analyze_pdufa(ticker: str) -> dict:
    try:
        result = analyzer.analyze(ticker)
        return result.model_dump()
    except TickerNotFoundError as e:
        return tool_error_response(
            code="TICKER_NOT_FOUND",
            message=str(e),
            details={"ticker": ticker}
        )
    except DataFetchError as e:
        return tool_error_response(
            code="DATA_FETCH_ERROR",
            message=str(e),
            details={"source": e.source}
        )
```

---

## 3.14 테스트 전략

### 3.14.1 테스트 계층

```
┌─────────────────────────────────────────────────────────────────┐
│                        TEST PYRAMID                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                          /\                                     │
│                         /  \       E2E Tests (10%)              │
│                        /────\      - Claude Desktop 연동        │
│                       /      \     - 실제 API 호출              │
│                      /────────\                                 │
│                     /          \   Integration Tests (30%)      │
│                    /────────────\  - 모듈 간 상호작용           │
│                   /              \ - Mock 외부 API              │
│                  /────────────────\                             │
│                 /                  \ Unit Tests (60%)           │
│                /────────────────────\- 함수/클래스 단위         │
│               /                      \- 완전 격리               │
│              ────────────────────────────                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.14.2 테스트 파일 구조

```
tests/
├── unit/
│   ├── schemas/
│   │   └── test_pipeline.py
│   ├── core/
│   │   ├── test_config.py
│   │   └── test_cache.py
│   ├── analysis/
│   │   └── pdufa/
│   │       ├── test_probability.py
│   │       └── test_analyzer.py
│   └── mcp/
│       └── tools/
│           └── test_fda.py
│
├── integration/
│   ├── test_pdufa_pipeline.py     # 분석 → 저장 → 조회
│   ├── test_mcp_tools.py          # MCP 도구 통합
│   └── test_data_sources.py       # SEC, yfinance 연동
│
├── e2e/
│   └── test_claude_desktop.py     # Claude Desktop 실제 연동
│
├── fixtures/
│   ├── pipelines/                 # 샘플 파이프라인 데이터
│   ├── responses/                 # Mock API 응답
│   └── conftest.py                # pytest fixtures
│
└── conftest.py                    # 전역 fixtures
```

### 3.14.3 테스트 명명 규칙

```python
# test_<module>_<scenario>_<expected_result>.py

# 예시: test_analyzer.py
def test_analyze_valid_ticker_returns_pipeline():
    """정상 티커 분석 시 Pipeline 반환"""
    pass

def test_analyze_unknown_ticker_raises_not_found():
    """미등록 티커 분석 시 TickerNotFoundError 발생"""
    pass

def test_calculate_probability_with_adcom_positive_increases():
    """AdCom 긍정 결과 시 확률 증가"""
    pass
```

### 3.14.4 커버리지 기준

| 모듈 | 최소 커버리지 | 비고 |
|------|--------------|------|
| schemas/ | 95% | 데이터 모델 핵심 |
| core/ | 90% | 인프라 신뢰성 |
| analysis/ | 85% | 비즈니스 로직 |
| data/ | 80% | 외부 API 제외 |
| mcp/tools/ | 80% | 통합 테스트 보완 |
| trading/ | 95% | Safety Critical |

---

## 3.15 의존성 규칙

### 3.15.1 외부 의존성 정책

```
┌─────────────────────────────────────────────────────────────────┐
│                   DEPENDENCY POLICY                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TIER 1: 필수 (항상 설치)                                        │
│  ─────────────────────────                                      │
│  - pydantic >= 2.0                                              │
│  - httpx (async HTTP)                                           │
│  - mcp (FastMCP)                                                │
│                                                                 │
│  TIER 2: 기능별 (선택적)                                         │
│  ─────────────────────────                                      │
│  - yfinance (시장 데이터)                                        │
│  - scipy (베이지안, 없으면 순수 Python)                          │
│  - xgboost (ML, 없으면 비활성)                                   │
│                                                                 │
│  TIER 3: 트레이딩 (별도 설치)                                    │
│  ─────────────────────────                                      │
│  - alpaca-trade-api (실거래 시에만)                              │
│                                                                 │
│  금지 의존성:                                                    │
│  - 버전 미고정 (항상 >= 또는 ~= 사용)                            │
│  - 유지보수 중단 패키지                                          │
│  - 보안 취약점 있는 버전                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.15.2 pyproject.toml 의존성 구조

```toml
[project]
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.24",
    "mcp>=0.9",
]

[project.optional-dependencies]
market = ["yfinance>=0.2"]
ml = ["scipy>=1.10", "xgboost>=2.0"]
trading = ["alpaca-trade-api>=3.0"]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "ruff>=0.1"]
all = ["tickergenius[market,ml,trading,dev]"]
```

### 3.15.3 Optional Import 패턴

```python
# 선택적 의존성 처리

def _try_import_scipy():
    try:
        import scipy.stats
        return scipy.stats
    except ImportError:
        return None

SCIPY_STATS = _try_import_scipy()

class BayesianUpdater:
    def update(self, prior: float, evidence: float) -> float:
        if SCIPY_STATS:
            # scipy 사용 (정밀)
            return self._update_with_scipy(prior, evidence)
        else:
            # 순수 Python 대체 (근사)
            return self._update_pure_python(prior, evidence)
```

---

## 3.16 성능 가이드라인

### 3.16.1 캐싱 전략

```python
# 캐시 대상 및 TTL

CACHE_POLICY = {
    "pipeline_data": {
        "ttl": 3600,        # 1시간
        "strategy": "disk", # 디스크 캐시
    },
    "market_price": {
        "ttl": 60,          # 1분
        "strategy": "memory",
    },
    "sec_filings": {
        "ttl": 86400,       # 24시간
        "strategy": "disk",
    },
    "probability_calc": {
        "ttl": 300,         # 5분
        "strategy": "memory",
    },
}
```

### 3.16.2 배치 처리

```python
# 다중 티커 처리 시 배치

class PDUFAAnalyzer:
    async def analyze_batch(
        self,
        tickers: list[str],
        concurrency: int = 5
    ) -> list[Pipeline]:
        """
        동시 처리 제한으로 API 레이트리밋 방지
        """
        semaphore = asyncio.Semaphore(concurrency)
        async def limited_analyze(ticker):
            async with semaphore:
                return await self.analyze_async(ticker)

        return await asyncio.gather(*[
            limited_analyze(t) for t in tickers
        ])
```

---

## 3.17 보안 체크리스트

### 3.17.1 API 키 관리

```
✓ 환경변수 또는 .env 파일에서만 로드
✓ 로그에 API 키 마스킹 (앞 4자리만 표시)
✓ .gitignore에 .env 포함
✓ 예시 파일은 .env.example로 제공
```

### 3.17.2 입력 검증

```python
# 모든 외부 입력은 Pydantic으로 검증

from pydantic import BaseModel, field_validator

class AnalyzeRequest(BaseModel):
    ticker: str
    include_history: bool = True

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.upper().strip()
        if not v.isalnum() or len(v) > 10:
            raise ValueError("Invalid ticker format")
        return v
```

### 3.17.3 트레이딩 보안

```
✓ TRADING_MODE 기본값 paper
✓ LIVE 모드 진입 시 2중 확인
✓ 일일 손실 한도 하드코딩
✓ 모든 주문 로그 기록 (감사 추적)
```

---

## 3.18 5인 전문가 최종 검토

### A (아키텍트) 검토

> 계층 분리, 의존성 방향, 인터페이스 계약 승인.
> 스크립트 양산 방지 정책 적절함.

### B (데이터 전문가) 검토

> StatusField 3-state 유지됨.
> 스키마 독립성 확보됨.
> 데이터 무결성 정책 적절함.

### C (MCP 전문가) 검토

> 도구 레지스트리 패턴 승인.
> ToolSpec 필수 필드 적절함.
> 에러 응답 표준화 완료.

### D (트레이딩 전문가) 검토

> Safety Layer 4단계 구조 승인.
> Kill Switch 구현 명세 적절함.
> 테스트 커버리지 95% 요구 확인.

### E (SRE) 검토

> 로깅 전략 승인.
> 테스트 피라미드 구조 적절함.
> CI/CD 버전 동기화 검증 포함됨.

---

**Phase 3 완료. 다음 단계: Phase 4 - 이행 계획 (Migration Plan)**
