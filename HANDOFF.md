# Ticker-Genius V4 Handoff Document

**Date**: 2026-01-07  
**From**: Cursor Agent  
**To**: Claude Code  

---

## Project Overview

Biotech PDUFA approval probability analysis system rebuild.  
Focus: **Data Quality First**, then Analysis, then Trading.

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

### M5: Analysis Engine
```
PDUFAPredictor
- Uses only CONFIRMED/EMPTY data
- Warns on UNKNOWN fields
- Approval probability calculation
```

---

## Reference (Stock Repo)

Legacy repo for reference: `https://github.com/OldExhaustedUnknown/Stock`

Key files to reference:
- `data/ml/pdufa_ml_dataset_v12.json` - Current ML dataset
- `docs/archive/tf_meetings/` - TF meeting history
- `docs/DATA_SCHEMA.md` - CRL Class definitions

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

---

## File Structure (Target)

```
ticker-genius/
├── src/tickergenius/
│   ├── schemas/          # ✅ Done
│   ├── data/
│   │   ├── validators/   # M2
│   │   └── collectors/   # M3-M4
│   └── analysis/         # M5
├── data/
│   ├── pipelines/
│   │   └── by_ticker/    # M1 output
│   ├── events/           # By year
│   └── manufacturing/    # By ticker
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
