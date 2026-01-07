# Ticker-Genius Complete - Handoff Document

**Date**: 2026-01-07  
**From**: Cursor Agent  
**To**: Claude Code  

---

## Project Overview

Comprehensive stock analysis & trading system rebuild.

---

## Modules (Planned)

### 1. Analysis Modules

| Module | Description | Legacy File |
|--------|-------------|-------------|
| **Biotech/PDUFA** | FDA 승인확률, CRL 분석 (현재 포커스) | `pdufa_analyzer.py` |
| **Surge Detection** | 급등주 실시간 탐지, 거래량 급증 | `surge_strategies.py` |
| **Meme Scanner** | 밈주 탐지, 펌프 신호 | `meme_scanner.py` |
| **Accumulation** | 매집 포착, 세력 매집 패턴 (OBV+횡보) | `meme_scanner.py` |
| **Bottom Fishing** | 하따 전략 (RSI 20→30, 급락 반등) | `surge_strategies.py` |
| **Technical** | 기술적 분석 (MACD, RSI, BB) | `technical_analysis.py` |
| **Momentum** | 모멘텀 지표 (스토캐스틱, DMI, 일목) | `momentum_indicators.py` |
| **Short Interest** | 공매도 분석, 숏스퀴즈 | `short_interest.py` |
| **Institutional** | 기관 매매 추적 | `institutional_tracker.py` |
| **Dilution** | 주식 희석 분석 | `dilution_analyzer.py` |
| **Options** | 옵션 분석 | `options_analysis.py` |
| **Sentiment** | 감성 분석 (뉴스, SNS) | `sentiment_analysis.py` |
| **Financial** | 재무 분석 | `financial_analysis.py` |
| **Organic** | 유기적 성장 분석 | `organic_analyzer.py` |
| **Earnings** | 실적 발표 파싱 | `earnings_call_parser.py` |
| **Clinical** | 임상 단계 분석 | `clinical_phase_analyzer.py` |
| **CMO** | CMO/제조사 분석 | `cmo_analyzer.py` |

### 2. Trading Strategies

| Strategy | Description | Signal |
|----------|-------------|--------|
| **삼박자** | 스토캐스틱 + DMI + RSI | Triple Signal |
| **삼신기** | 삼박자 + MACD | Triple Divine |
| **하따** | 과매도 반등 (RSI 20→30) | Bottom Fishing |
| **돌파매매** | 저항선 돌파 | Breakout |
| **240분봉** | 중기 스윙 | 4H Strategy |

### 3. Markets

| Market | APIs | Legacy |
|--------|------|--------|
| **US Stocks** | Alpaca, Polygon, FinnHub, FMP | `alpaca_client.py` |
| **Korean Stocks** | KIS API, pykrx | `kis_client.py` |

### 4. Trading Infrastructure

| Component | Description | Legacy |
|-----------|-------------|--------|
| **OrderManager** | 주문 관리 | `order_manager.py` |
| **RiskGuard** | 리스크 규칙 | `risk_guard.py` |
| **CircuitBreaker** | 거래 차단기 | `circuit_breaker.py` |
| **PositionTracker** | 포지션 추적 | `position_tracker.py` |
| **PaperTrading** | 모의 거래 | `paper_trading.py` |

### 5. ML/Prediction

| Component | Description | Legacy |
|-----------|-------------|--------|
| **XGBoost** | 기본 예측 모델 | `trainer.py` |
| **Bayesian** | 확률 보정 | `bayesian.py` |
| **Hybrid Ensemble** | 복합 앙상블 | `hybrid_ensemble.py` |
| **Multi-Agent** | 에이전트 오케스트레이션 | `multi_agent_system.py` |

### 6. Real-time & Calendar

| Component | Description | Legacy |
|-----------|-------------|--------|
| **FDA Poller** | FDA 이벤트 폴링 | `fda_poller.py` |
| **SEC Poller** | SEC 8-K 폴링 | `sec_poller_v2.py` |
| **Halt Monitor** | 거래정지 모니터링 | `halt_monitor.py` |
| **Real-time Monitor** | 실시간 모니터 | `realtime_monitor.py` |
| **Notifications** | Discord, Telegram 알림 | `discord_notifier.py` |

### 7. Backend/Frontend

| Component | Description | Legacy |
|-----------|-------------|--------|
| **FastAPI** | REST API 서버 | `web/backend/` |
| **MCP Server** | Claude MCP 도구 | `server.py` |
| **React/Next.js** | 프론트엔드 | `web/frontend/` |
| **Dashboard** | 대시보드 | `dashboard/` |

### 8. Tools (MCP)

| Tool | Description | Legacy |
|------|-------------|--------|
| `surge_tools` | 급등주 분석 도구 | `tools/surge_tools.py` |
| `meme_tools` | 밈주 분석 도구 | `tools/meme_tools.py` |
| `organic_tools` | 유기적 분석 | `tools/organic_tools.py` |
| `fda_tools` | FDA 분석 | `tools/fda_tools.py` |
| `korea_market` | 한국 시장 | `tools/korea_market.py` |
| `dilution_tools` | 희석 분석 | `tools/dilution_tools.py` |
| `watchlist` | 관심종목 | `tools/watchlist.py` |
| `backtesting` | 백테스트 | `tools/backtesting.py` |

---

## Completed (M0)

### Pydantic Schemas
Location: `src/tickergenius/schemas/`

| File | Purpose |
|------|---------|
| `base.py` | `StatusField` 3-state (CONFIRMED/EMPTY/UNKNOWN) |
| `pipeline.py` | Pipeline, PDUFAEvent, CRLDetail, LegalIssue |
| `manufacturing.py` | ManufacturingSite, FDA483, WarningLetter |
| `clinical.py` | ClinicalTrial |
| `data_quality.py` | DataQuality, DataQualityIssue |

**Tests**: `tests/test_schemas.py` - 17 tests passing

### Key Design Decisions

1. **3-State Data Classification**
   - `CONFIRMED`: Value verified with source
   - `EMPTY`: N/A (e.g., AdCom not held)
   - `UNKNOWN`: Not yet verified

2. **Pipeline-based Structure**
   - 1 Ticker → N Pipelines (drug + indication)
   - 1 Pipeline → N PDUFA Events (resubmissions)

3. **Edge Cases Handled**
   - Multiple CRLs: `crl_history` array
   - COVID delays: `delay_reason`, `special_circumstances`
   - Litigation: `legal_issues` (VNDA FDA lawsuit, AQST citizen petition)
   - Pending states: `pending_status` (9 sub-states)

---

## Next Steps (M1-M5)

### M1: Migration Script (NEXT)
```
pdufa_ml_dataset_v12.json → Pipeline structure
- Filter: 2020+ only
- Convert null → StatusField.unknown()
- Group by ticker/drug/indication
- Output: data/pipelines/by_ticker/{TICKER}.json
```

### M2: Validation System
```
AutoValidator
- Quality score calculation
- UNKNOWN field listing
- "Needs verification" reports
```

### M3-M4: Data Collection
```
Tiered collection:
- Tier 1: FDA Drugs@FDA (automated)
- Tier 2: SEC 8-K, ClinicalTrials.gov
- Tier 2.5: Manufacturing/483 (mandatory for CMC CRL)
- Tier 3: Manual verification
```

### M5: Analysis Engine (PDUFA First)
```
PDUFAPredictor
- Uses only CONFIRMED/EMPTY data
- Warns on UNKNOWN fields
- Approval probability calculation
```

### M6-M7: Additional Analysis Modules
```
- Surge/Meme Scanner rebuild
- Technical/Momentum indicators
- Short Interest analyzer
```

### M8: Trading System
```
- SafeOrderManager (from OrderManager)
- RiskGuard rules
- Paper → Live transition
```

### M9: Infrastructure
```
- FastAPI backend rebuild
- MCP Tools rebuild
- Frontend rebuild
```

---

## Reference (Stock Repo)

Legacy repo: `https://github.com/OldExhaustedUnknown/Stock`

### Key Files to Reference

**Data:**
- `data/ml/pdufa_ml_dataset_v12.json` - ML dataset

**Docs:**
- `docs/archive/tf_meetings/` - TF meeting history
- `docs/DATA_SCHEMA.md` - CRL Class definitions

**Analysis Modules:**
- `modules/surge_strategies.py` - 급등주 전략
- `modules/meme_scanner.py` - 밈주/매집 스캐너
- `modules/momentum_indicators.py` - 모멘텀 지표
- `modules/technical_analysis.py` - 기술적 분석
- `modules/short_interest.py` - 공매도

**Trading:**
- `trading/order_manager.py` - 주문관리
- `trading/risk_guard.py` - 리스크 가드
- `trading/alpaca_client.py` - 미국 거래
- `trading/kis_client.py` - 한국 거래

**Note**: Reference only. Don't copy code blindly - rebuild with quality focus.

---

## User Requirements (Priority)

| Priority | Requirement |
|----------|-------------|
| P0 | Data Quality - null vs empty distinction |
| P1 | Analysis - approval probability, CRL, clinical |
| P2 | Pipeline structure - drug + indication |
| P3 | 2020+ data only |
| P4 | Manufacturing/483 for CMC CRL |
| P5 | File split by ticker/year |
| P6 | Surge/Meme/Accumulation analysis |
| P7 | Korean stock support |
| P8 | Frontend/Backend rebuild |

---

## File Structure (Target)

```
ticker-genius/
├── src/tickergenius/
│   ├── schemas/          # ✅ Done (Pydantic models)
│   ├── data/
│   │   ├── validators/   # M2 - AutoValidator
│   │   └── collectors/   # M3-M4 - Data collectors
│   ├── analysis/
│   │   ├── pdufa/        # M5 - PDUFAPredictor
│   │   ├── surge/        # M6 - Surge strategies
│   │   ├── meme/         # M6 - Meme scanner
│   │   ├── technical/    # M6 - Technical analysis
│   │   └── short/        # M6 - Short interest
│   ├── trading/          # M8 - OrderManager, RiskGuard
│   └── brokers/          # M8 - Alpaca, KIS adapters
│
├── server/               # M9 - Backend
│   ├── api/              # FastAPI routes
│   ├── mcp/              # MCP Server
│   └── websocket/        # Real-time updates
│
├── web/                  # M9 - Frontend
│   ├── frontend/         # React/Next.js
│   └── components/       # Dashboard components
│
├── tools/                # M9 - MCP Tools
│   ├── surge_tools.py
│   ├── meme_tools.py
│   ├── fda_tools.py
│   └── korea_market.py
│
├── data/
│   ├── pipelines/by_ticker/  # M1 output
│   ├── events/               # By year
│   ├── manufacturing/        # By ticker
│   └── price_history/        # US + KR
│
├── tests/
│   └── test_schemas.py   # ✅ Done
└── pyproject.toml
```

---

## Commands

```bash
# Run tests
pytest tests/test_schemas.py -v

# Python version
Python 3.11+
```

---

**Status**: Ready for M1 (Migration Script)
