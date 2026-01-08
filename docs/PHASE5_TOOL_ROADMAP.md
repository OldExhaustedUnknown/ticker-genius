# Phase 5: 도구 로드맵 + 통폐합 계획

**작성일**: 2026-01-08
**목적**: 누락/중복 도구 제거, 향후 도구 설계 명확화

---

## 5.1 레거시 도구 전체 인벤토리

### 총 55개 도구 (15개 파일)

| 파일 | 도구 수 | 도구 목록 |
|------|---------|-----------|
| `us_market.py` | 5 | ticker_overview, analyze_ticker, compare_tickers, scan_market, analyze_pdufa_catalyst |
| `korea_market.py` | 3 | analyze_korea_stock, scan_korea_biotech, compare_korea_stocks |
| `backtesting.py` | 2 | backtest_advanced, backtest_strategy |
| `admin.py` | 1 | self_check |
| `watchlist.py` | 2 | manage_watchlist, check_alerts |
| `fda_tools.py` | 8 | calculate_pdufa_probability (x4 버전), fda_drug_lookup, fda_adverse_events, fda_recalls, fda_biotech_analysis |
| `economic_tools.py` | 3 | market_economic_context, get_fed_rate, get_inflation_data |
| `market_data_tools.py` | 4 | get_intraday_chart, get_market_overview, get_ticker_info_massive, get_ticker_info_fmp |
| `portfolio_tools.py` | 2+ | portfolio_buy, portfolio_sell, ... |
| `meme_tools.py` | 4 | scan_meme_stocks, analyze_meme_signal, assess_dump_risk, calculate_trade_strategy |
| `visualization_tools.py` | 4 | generate_chart, generate_pdf_report, send_telegram_alert, generate_full_report |
| `fmp_tools.py` | 7 | fmp_press_releases, fmp_stock_news, fmp_earnings_calendar, fmp_sec_filings, fmp_ipo_calendar, fmp_sector_performance, fmp_screen_stocks |
| `surge_tools.py` | 7 | analyze_surge_signals, analyze_sambakja, analyze_samsingi, analyze_hatta, analyze_breakout, get_momentum_indicators, generate_trade_checklist |
| `dilution_tools.py` | 1 | analyze_dilution |
| `organic_tools.py` | 4 | organic_analyze, organic_recalculate, get_dependency_chain, list_organic_nodes |

---

## 5.2 문제점 분석 (5인 전문가 합의)

### 5.2.1 중복 도구 (DUPLICATE)

| 문제 | 레거시 상태 | 권장 조치 |
|------|------------|-----------|
| PDUFA 확률 4종 | `calculate_pdufa_probability`, `_v2`, `_ml`, `_ml_v2` | **1개로 통합**: `calculate_pdufa_probability(method="hybrid")` |
| 티커 정보 3종 | `ticker_overview`, `get_ticker_info_massive`, `get_ticker_info_fmp` | **1개로 통합**: `get_ticker_info(ticker, source="auto")` |
| 경제지표 3종 | `market_economic_context`, `get_fed_rate`, `get_inflation_data` | **1개로 통합**: `get_economic_indicators(indicators=["all"])` |
| 급등주 분석 5종 | `analyze_surge_signals`, `_sambakja`, `_samsingi`, `_hatta`, `_breakout` | **1개로 통합**: `analyze_surge(ticker, strategy="auto")` |

### 5.2.2 모호한 경계 (OVERLAPPING)

| 문제 | 설명 | 권장 조치 |
|------|------|-----------|
| `analyze_ticker` vs `fda_biotech_analysis` | 둘 다 바이오텍 분석 포함 | **역할 분리**: `analyze_ticker`=기본분석, `analyze_biotech`=FDA특화 |
| `scan_market` vs `scan_meme_stocks` vs `fmp_screen_stocks` | 3개 스캐너 혼재 | **1개로 통합**: `scan_stocks(filter_type="meme/biotech/general")` |
| `generate_full_report` vs 개별 차트/PDF | 종합 vs 개별 | **역할 명확화**: 개별 제거, `generate_report(components=[])` |

### 5.2.3 누락 도구 (MISSING)

| 누락 기능 | 필요 이유 | 신규 도구 제안 |
|----------|----------|----------------|
| 파이프라인 데이터 조회 | M1 스키마 활용 | `get_pipeline(ticker)` |
| CRL 이력 조회 | PDUFA 분석 핵심 | `get_crl_history(ticker)` |
| PAI 상태 조회 | 바이오텍 분석 핵심 | `get_pai_status(ticker)` |
| 희석 시뮬레이션 | 워런트 영향 분석 | `simulate_dilution(ticker, scenarios)` |
| 데이터 품질 조회 | StatusField 3-state | `check_data_quality(ticker)` |

### 5.2.4 불필요 도구 (DEPRECATED)

| 도구 | 제거 사유 |
|------|----------|
| `calculate_pdufa_probability` (v1) | v2/ML로 대체됨 |
| `calculate_pdufa_probability_v2` | ML hybrid로 통합 |
| `calculate_pdufa_probability_ml` (v1) | v2로 대체됨 |
| `backtest_advanced` vs `backtest_strategy` | 기능 중복, 1개로 통합 |
| `analyze_sambakja`, `analyze_samsingi`, `analyze_hatta` | 개별 전략 → `analyze_surge` 통합 |

---

## 5.3 신규 도구 아키텍처 (NEW REPO)

### 5.3.1 도구 분류 체계 (3-Tier)

```
┌─────────────────────────────────────────────────────────────┐
│                    Tier 1: READ-ONLY                        │
│  데이터 조회만 수행, 부작용 없음, 캐시 활용                 │
├─────────────────────────────────────────────────────────────┤
│  get_ticker_info          get_pipeline          scan_stocks │
│  get_economic_indicators  get_crl_history       get_news    │
│  get_pai_status           check_data_quality    self_check  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Tier 2: ANALYSIS                         │
│  계산/분석 수행, CPU 집약적, 결과 캐시 가능                 │
├─────────────────────────────────────────────────────────────┤
│  calculate_pdufa_probability    analyze_biotech             │
│  analyze_surge                  analyze_dilution            │
│  backtest_strategy              organic_analyze             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Tier 3: ACTION                           │
│  외부 효과 발생, 확인 필요, 감사 로깅                       │
├─────────────────────────────────────────────────────────────┤
│  manage_watchlist     send_alert      generate_report       │
│  portfolio_execute*   simulate_trade* update_pipeline*      │
└─────────────────────────────────────────────────────────────┘
                    * = Phase 9+ (Trading)
```

### 5.3.2 신규 도구 목록 (통폐합 후)

**총 25개 도구 (55개 → 25개, 55% 감소)**

#### Tier 1: READ-ONLY (10개)

| 도구 ID | 설명 | 레거시 대응 |
|---------|------|-------------|
| `get_ticker_info` | 통합 티커 정보 (yfinance→FMP→Polygon 폴백) | ticker_overview + get_ticker_info_massive + get_ticker_info_fmp |
| `get_pipeline` | 파이프라인 데이터 조회 (신규 스키마) | **신규** |
| `get_crl_history` | CRL 이력 조회 | **신규** |
| `get_pai_status` | PAI 상태 조회 | **신규** |
| `get_economic_indicators` | 통합 경제지표 | market_economic_context + get_fed_rate + get_inflation_data |
| `get_news` | 통합 뉴스/공시 | fmp_press_releases + fmp_stock_news + fmp_sec_filings |
| `get_calendar` | 통합 캘린더 (PDUFA/어닝/IPO) | fmp_earnings_calendar + fmp_ipo_calendar |
| `scan_stocks` | 통합 스캐너 | scan_market + scan_meme_stocks + fmp_screen_stocks |
| `check_data_quality` | 데이터 품질 3-state 확인 | **신규** |
| `self_check` | 시스템 진단 | self_check (유지) |

#### Tier 2: ANALYSIS (9개)

| 도구 ID | 설명 | 레거시 대응 |
|---------|------|-------------|
| `calculate_pdufa_probability` | 통합 PDUFA 확률 (rule/ml/hybrid) | 4개 버전 통합 |
| `analyze_biotech` | 바이오텍 종합 분석 | analyze_ticker + fda_biotech_analysis |
| `analyze_surge` | 급등주 분석 (삼박자/삼신기/하따 통합) | 5개 버전 통합 |
| `analyze_dilution` | 희석 분석 | analyze_dilution (유지) |
| `simulate_dilution` | 희석 시뮬레이션 (시나리오) | **신규** |
| `backtest_strategy` | 백테스팅 | backtest_advanced + backtest_strategy 통합 |
| `organic_analyze` | 유기적 분석 | organic_analyze (유지) |
| `compare_tickers` | 티커 비교 | compare_tickers + compare_korea_stocks 통합 |
| `assess_risk` | 리스크 평가 (덤프 등) | assess_dump_risk 확장 |

#### Tier 3: ACTION (6개)

| 도구 ID | 설명 | 레거시 대응 |
|---------|------|-------------|
| `manage_watchlist` | 워치리스트 관리 | manage_watchlist (유지) |
| `check_alerts` | 알림 확인 | check_alerts (유지) |
| `send_alert` | 알림 전송 (텔레그램 등) | send_telegram_alert |
| `generate_report` | 리포트 생성 (차트/PDF 통합) | generate_chart + generate_pdf_report + generate_full_report 통합 |
| `update_pipeline` | 파이프라인 데이터 업데이트 | **신규** |
| `export_data` | 데이터 내보내기 | **신규** |

---

## 5.4 도구 인터페이스 표준

### 5.4.1 ToolSpec 스키마

```python
@dataclass
class ToolSpec:
    """도구 명세"""
    tool_id: str                    # 고유 ID (snake_case)
    tier: Literal["read", "analysis", "action"]
    version: str                    # semver (1.0.0)

    # 입력
    required_params: list[str]
    optional_params: dict[str, Any]  # param: default_value

    # 출력
    output_schema: type[BaseModel]   # Pydantic 모델

    # 메타
    cache_ttl: int                   # 초 (0=캐시 안 함)
    rate_limit: str                  # "10/min" 형식
    dependencies: list[str]          # 의존 API 키

    # 문서
    description_ko: str
    description_en: str
    examples: list[dict]
```

### 5.4.2 도구 응답 표준

```python
class ToolResponse(BaseModel):
    """모든 도구의 표준 응답"""
    success: bool
    tool_id: str
    version: str
    timestamp: datetime

    # 데이터
    data: Optional[dict]

    # 메타
    cache_hit: bool = False
    execution_ms: int
    data_quality: Literal["CONFIRMED", "EMPTY", "UNKNOWN"]

    # 에러 (success=False일 때)
    error_code: Optional[str]
    error_message: Optional[str]
```

### 5.4.3 도구 등록 표준

```python
# tools/registry.py
from dataclasses import dataclass
from typing import Callable

TOOL_REGISTRY: dict[str, ToolSpec] = {}

def register_tool(spec: ToolSpec):
    """데코레이터로 도구 등록"""
    def decorator(func: Callable):
        TOOL_REGISTRY[spec.tool_id] = spec
        # FastMCP 등록
        return func
    return decorator

# 사용 예
@register_tool(ToolSpec(
    tool_id="get_ticker_info",
    tier="read",
    version="1.0.0",
    required_params=["ticker"],
    optional_params={"source": "auto"},
    output_schema=TickerInfoResponse,
    cache_ttl=300,
    rate_limit="60/min",
    dependencies=["FMP_API_KEY", "POLYGON_API_KEY"],
    description_ko="통합 티커 정보 조회",
    description_en="Get unified ticker information",
    examples=[{"ticker": "MRNA"}],
))
def get_ticker_info(ticker: str, source: str = "auto") -> TickerInfoResponse:
    ...
```

---

## 5.5 마일스톤별 도구 구현 계획

### M2: Core Infrastructure

| 도구 | 우선순위 | 의존성 |
|------|---------|--------|
| `self_check` | P0 | 없음 |
| `get_ticker_info` | P0 | DataProvider |
| `check_data_quality` | P1 | StatusField |

### M3: PDUFA Analysis

| 도구 | 우선순위 | 의존성 |
|------|---------|--------|
| `get_pipeline` | P0 | PipelineSchema |
| `get_crl_history` | P0 | CRLDetail |
| `get_pai_status` | P0 | ManufacturingFacility |
| `calculate_pdufa_probability` | P0 | 위 3개 |
| `analyze_biotech` | P1 | calculate_pdufa_probability |

### M4: MCP Integration

| 도구 | 우선순위 | 의존성 |
|------|---------|--------|
| `get_news` | P1 | FMP API |
| `get_calendar` | P1 | FMP API |
| `scan_stocks` | P1 | DataProvider |
| `get_economic_indicators` | P2 | Alpha Vantage |

### M5: ML Enhancement

| 도구 | 우선순위 | 의존성 |
|------|---------|--------|
| `organic_analyze` | P1 | ML 모델 |
| `analyze_surge` | P2 | ML 모델 |
| `analyze_dilution` | P2 | SEC 데이터 |
| `simulate_dilution` | P2 | analyze_dilution |

### MT: Trading (Phase 9+)

| 도구 | 우선순위 | 의존성 |
|------|---------|--------|
| `manage_watchlist` | P1 | DB |
| `check_alerts` | P1 | manage_watchlist |
| `send_alert` | P2 | 텔레그램 API |
| `generate_report` | P2 | 시각화 모듈 |
| `backtest_strategy` | P2 | 가격 데이터 |

---

## 5.6 통합 매핑 테이블

### 레거시 → 신규 매핑

| 레거시 도구 | 신규 도구 | 매핑 방식 |
|------------|----------|-----------|
| `ticker_overview` | `get_ticker_info` | 통합 |
| `get_ticker_info_massive` | `get_ticker_info` | source="polygon" |
| `get_ticker_info_fmp` | `get_ticker_info` | source="fmp" |
| `calculate_pdufa_probability` | `calculate_pdufa_probability` | method="rule" |
| `calculate_pdufa_probability_v2` | `calculate_pdufa_probability` | method="rule_v2" |
| `calculate_pdufa_probability_ml` | `calculate_pdufa_probability` | method="ml" |
| `calculate_pdufa_probability_ml_v2` | `calculate_pdufa_probability` | method="hybrid" (기본값) |
| `analyze_ticker` | `analyze_biotech` | focus="general" |
| `fda_biotech_analysis` | `analyze_biotech` | focus="fda" |
| `analyze_pdufa_catalyst` | `analyze_biotech` | focus="catalyst" |
| `market_economic_context` | `get_economic_indicators` | indicators=["all"] |
| `get_fed_rate` | `get_economic_indicators` | indicators=["fed_rate"] |
| `get_inflation_data` | `get_economic_indicators` | indicators=["cpi"] |
| `scan_market` | `scan_stocks` | filter_type="general" |
| `scan_meme_stocks` | `scan_stocks` | filter_type="meme" |
| `fmp_screen_stocks` | `scan_stocks` | filter_type="screener" |
| `analyze_surge_signals` | `analyze_surge` | strategy="auto" |
| `analyze_sambakja` | `analyze_surge` | strategy="sambakja" |
| `analyze_samsingi` | `analyze_surge` | strategy="samsingi" |
| `analyze_hatta` | `analyze_surge` | strategy="hatta" |
| `analyze_breakout` | `analyze_surge` | strategy="breakout" |
| `fmp_press_releases` | `get_news` | source="press" |
| `fmp_stock_news` | `get_news` | source="news" |
| `fmp_sec_filings` | `get_news` | source="sec" |
| `fmp_earnings_calendar` | `get_calendar` | type="earnings" |
| `fmp_ipo_calendar` | `get_calendar` | type="ipo" |
| `generate_chart` | `generate_report` | components=["chart"] |
| `generate_pdf_report` | `generate_report` | components=["pdf"] |
| `generate_full_report` | `generate_report` | components=["all"] |
| `send_telegram_alert` | `send_alert` | channel="telegram" |
| `backtest_advanced` | `backtest_strategy` | 통합 |
| `compare_tickers` | `compare_tickers` | market="us" |
| `compare_korea_stocks` | `compare_tickers` | market="korea" |
| `assess_dump_risk` | `assess_risk` | risk_type="dump" |

---

## 5.7 폐기 도구 목록 (DEPRECATED)

다음 도구는 신규 레포에서 **구현하지 않음**:

| 도구 | 폐기 사유 |
|------|----------|
| `calculate_pdufa_probability` (v1) | hybrid로 대체 |
| `calculate_pdufa_probability_v2` | hybrid로 대체 |
| `calculate_pdufa_probability_ml` (v1) | hybrid로 대체 |
| `backtest_advanced` | backtest_strategy로 통합 |
| `analyze_sambakja` | analyze_surge로 통합 |
| `analyze_samsingi` | analyze_surge로 통합 |
| `analyze_hatta` | analyze_surge로 통합 |
| `analyze_breakout` | analyze_surge로 통합 |
| `fmp_sector_performance` | get_economic_indicators로 통합 |
| `get_momentum_indicators` | analyze_surge에 포함 |
| `generate_trade_checklist` | analyze_surge에 포함 |
| `calculate_trade_strategy` | assess_risk + analyze_surge로 분리 |
| `organic_recalculate` | organic_analyze에 통합 |
| `get_dependency_chain` | 내부 유틸리티로 비노출 |
| `list_organic_nodes` | 문서화로 대체 |

---

## 5.8 도구 버전 관리

### 버전 정책

```
도구 버전 = MAJOR.MINOR.PATCH

MAJOR: 호환성 파괴 변경 (파라미터 제거, 응답 구조 변경)
MINOR: 기능 추가 (새 파라미터, 새 필드)
PATCH: 버그 수정, 성능 개선
```

### 호환성 유지

```python
# 레거시 호환 래퍼 (1년간 유지 후 제거)
@deprecated(version="2.0.0", replacement="get_ticker_info")
def ticker_overview(ticker: str) -> str:
    """DEPRECATED: Use get_ticker_info instead"""
    return get_ticker_info(ticker, source="auto").to_legacy_format()
```

---

## 5.9 5인 전문가 검토

### A (아키텍트)
> "55개 → 25개 통폐합 적절함. ToolSpec 표준화로 일관성 확보.
> 레거시 호환 래퍼는 M4 완료 후 1년간만 유지."

### B (데이터)
> "DataProvider 폴백 체인(yfinance→FMP→Polygon) 잘 반영됨.
> StatusField 3-state가 `check_data_quality`로 명시적 노출된 점 좋음."

### C (MCP)
> "Tier 분류(read/analysis/action) 명확함.
> rate_limit과 cache_ttl 표준화로 API 관리 용이."

### D (트레이딩 리스크)
> "Tier 3 ACTION 도구들 Safety Layer 적용 필요.
> `portfolio_execute`는 Phase 9+ 분리 유지."

### E (SRE/보안)
> "도구별 `dependencies` 필드로 API 키 검증 가능.
> 감사 로깅 Tier 3에만 적용 효율적."

---

## 5.10 체크리스트

### 구현 전 확인

- [ ] 모든 신규 도구에 ToolSpec 정의
- [ ] 입출력 Pydantic 스키마 작성
- [ ] 레거시 매핑 테스트 케이스 작성
- [ ] API 키 의존성 문서화

### 구현 후 확인

- [ ] 도구당 최소 3개 테스트 케이스
- [ ] 레거시 호환 래퍼 동작 확인
- [ ] 캐시 TTL 적절성 검증
- [ ] Rate limit 준수 확인

---

**다음 단계**: M2 구현 시작 (self_check, get_ticker_info, check_data_quality)
