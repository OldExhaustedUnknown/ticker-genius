# Ticker-Genius

Comprehensive stock analysis system.

## Scope

### Analysis Modules
- **Biotech/PDUFA**: FDA approval probability, CRL analysis
- **Momentum**: Surge detection, accumulation patterns
- **Tech**: Growth stock analysis
- **General**: Market analysis, short interest

### Markets
- **US**: NYSE, NASDAQ (Alpaca, Polygon)
- **Korea**: KOSPI, KOSDAQ (KIS API)

### Infrastructure
- **Backend**: FastAPI + MCP Server
- **Frontend**: React Dashboard
- **Trading**: Paper → Live (US + KR)

## Status

**Current Phase**: Schema Design Complete  
**Next**: Migration Script

## Key Features (Biotech Module)

- **3-State Data Classification**: CONFIRMED / EMPTY / UNKNOWN
- **Pipeline-based Structure**: Ticker → Pipelines → PDUFA Events
- **Edge Case Handling**: Multiple CRLs, COVID delays, Litigation

## Quick Start

```bash
# Install
pip install -e .

# Run tests
pytest tests/ -v
```

## Structure

```
src/tickergenius/schemas/
├── base.py           # StatusField 3-state
├── pipeline.py       # Pipeline, PDUFAEvent, CRLDetail
├── manufacturing.py  # ManufacturingSite, FDA483
├── clinical.py       # ClinicalTrial
└── data_quality.py   # DataQuality tracking
```

## Reference

See `HANDOFF.md` for full handoff documentation.

## License

MIT
