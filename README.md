# Ticker-Genius V4

Biotech PDUFA approval probability analysis system.

## Status

**Phase**: M0 Complete (Schemas)  
**Next**: M1 (Migration Script)

## Key Features

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
