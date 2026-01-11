# PDUFA Prediction Backtest Report

Generated: 2026-01-11 12:59:25

## Summary

| Metric | Value |
|--------|-------|
| Total Events | 504 |
| Approved | 477 |
| CRL | 27 |
| Errors | 0 |

## Prediction Accuracy

| Metric | Value |
|--------|-------|
| Accuracy | 92.9% |
| Precision (Approval) | 96.2% |
| Recall (Approval) | 96.2% |
| F1 Score | 0.962 |
| ROC-AUC | 0.901 |

## Confusion Matrix

|  | Predicted Approved | Predicted CRL |
|--|-------------------|---------------|
| **Actual Approved** | 459 (TP) | 18 (FN) |
| **Actual CRL** | 18 (FP) | 9 (TN) |

## Probability Distribution

| Actual Result | Avg Probability | Min | Max | Count |
|---------------|-----------------|-----|-----|-------|
| Approved | 78.8% | 0.0% | 90.0% | 477 |
| CRL | 45.8% | 5.0% | 72.8% | 27 |

**Probability Separation**: 33.0% (Approved avg - CRL avg)

## Probability Buckets

| Probability Bucket | Total | Approved | CRL | Approval Rate |
|-------------------|-------|----------|-----|---------------|
| Low (0-30%) | 27 | 18 | 9 | 66.7% |
| Medium-Low (30-50%) | 0 | 0 | 0 | N/A |
| Medium-High (50-70%) | 99 | 85 | 14 | 85.9% |
| High (70-90%) | 342 | 338 | 4 | 98.8% |
| Very High (90%+) | 36 | 36 | 0 | 100.0% |

## False Positives (Predicted Approved but CRL)

Events where model predicted >50% approval but received CRL:

| Ticker | Drug | PDUFA Date | Predicted | Key Factors |
|--------|------|------------|-----------|-------------|
| BYSI | Plinabulin | 2021-11-30 | 72.8% | base_rate, breakthrough_therapy, is_resubmission |
| CORT | Relacorilant | 2025-12-31 | 72.8% | base_rate, breakthrough_therapy, is_resubmission |
| CYTK | Omecamtiv Mecarbil | 2023-02-28 | 72.8% | base_rate, breakthrough_therapy, is_resubmission |
| ICPT | OCA/Ocaliva | 2023-06-01 | 72.8% | base_rate, breakthrough_therapy, is_resubmission |
| AMYT | Oleogel-S10 | 2022-02-28 | 69.8% | base_rate, priority_review, is_resubmission |
| FGEN | Roxadustat | 2021-08-11 | 69.8% | base_rate, priority_review, is_resubmission |
| GILD | Filgotinib | 2020-08-01 | 69.8% | base_rate, priority_review, is_resubmission |
| ALVO | AVT05 | 2025-12-31 | 65.9% | base_rate, is_resubmission |
| BPMC | Avapritinib 4L GIST | 2020-05-15 | 65.8% | base_rate, breakthrough_therapy, is_resubmission |
| HCM | Surufatinib | 2022-04-30 | 65.8% | base_rate, breakthrough_therapy, is_resubmission |
| SPPI | Poziotinib | 2022-11-24 | 65.8% | base_rate, breakthrough_therapy, is_resubmission |
| YMAB | Omburtamab monoclonal antibody | 2022-11-30 | 65.8% | base_rate, breakthrough_therapy, is_resubmission |
| EGRX | Kangio/Bivalirudin RTU | 2016-03-18 | 64.8% | base_rate, is_resubmission, facility_pai_passed |
| CAPR | Deramiocel CAP-1002 | 2025-07-09 | 60.8% | base_rate, breakthrough_therapy, is_resubmission |
| SRRK | Apitegromab SRK-015 | 2025-09-22 | 60.8% | base_rate, breakthrough_therapy, is_resubmission |

## False Negatives (Predicted CRL but Approved)

Events where model predicted <50% approval but was approved:

| Ticker | Drug | PDUFA Date | Predicted | Key Factors |
|--------|------|------------|-----------|-------------|
| EVOK | GIMOTI | 2021-01-14 | 0.0% | base_rate, is_resubmission, primary_endpoint_not_met |
| ALDX | Topical ocular reproxalap | 2019-02-13 | 5.0% | base_rate, fast_track, is_resubmission |
| FOLD | AT-GAA | 2023-09-30 | 5.0% | base_rate, breakthrough_therapy, primary_endpoint_not_met |
| IONS | QALSODY Tofersen | 2023-04-25 | 5.0% | base_rate, accelerated_approval, primary_endpoint_not_met |
| PTCT | Vatiquinone PTC743 | 2024-11-13 | 5.0% | base_rate, breakthrough_therapy, primary_endpoint_not_met |
| TAK | EXKIVITY | 2021-09-15 | 5.0% | base_rate, breakthrough_therapy, primary_endpoint_not_met |
| VNDA | Tradipitant | 2025-12-30 | 5.0% | base_rate, breakthrough_therapy, is_resubmission |
| ADMP | ZIMHI | 2021-10-15 | 14.8% | base_rate, is_resubmission, trial_region_china_only |
| AMPH | REXTOVY | 2023-03-07 | 14.8% | base_rate, is_resubmission, trial_region_china_only |
| AQST | Tadalafil oral film | 2023-03-03 | 14.8% | base_rate, is_resubmission, trial_region_china_only |
| ATEK | QDOLO | 2020-09-01 | 15.0% | base_rate, trial_region_china_only, facility_pai_passed |
| AUTL | AUCATZYL Obecabtagene autoleuc | 2024-11-16 | 15.0% | base_rate, breakthrough_therapy, single_arm_trial |
| CHRS | Toripalimab | 2022-04-30 | 15.0% | base_rate, breakthrough_therapy, is_resubmission |
| CMRX | Modeyso dordaviprone | 2025-08-06 | 15.0% | base_rate, breakthrough_therapy, single_arm_trial |
| HRTX | HTX-019 | 2022-09-17 | 15.0% | base_rate, fast_track, trial_region_china_only |

## True Negatives (Correctly Predicted CRL)

| Ticker | Drug | PDUFA Date | Predicted | Key Factors |
|--------|------|------------|-----------|-------------|
| APLT | Govorestat | 2024-11-28 | 5.0% | base_rate, priority_review, is_resubmission |
| BHVN | VYGLXIA troriluzole | 2025-11-04 | 5.0% | base_rate, priority_review, is_resubmission |
| INCY | QD Ruxolitinib XR | 2023-03-23 | 5.0% | base_rate, priority_review, is_resubmission |
| MRK | Gefapixant (LYFNUA) | 2023-12-27 | 5.0% | base_rate, priority_review, is_resubmission |
| NERV | Roluperidone 5-HT2A antagonist | 2024-02-26 | 5.0% | base_rate, breakthrough_therapy, is_resubmission |
| RETA | Bardoxolone | 2022-02-25 | 5.0% | base_rate, breakthrough_therapy, is_resubmission |
| SESN | Vicineum | 2021-09-01 | 5.0% | base_rate, breakthrough_therapy, is_resubmission |
| TCDA | Veverimer | 2020-08-21 | 5.0% | base_rate, priority_review, is_resubmission |
| ALDX | ADX-2191 (methotrexate intravi | 2023-06-21 | 15.0% | base_rate, priority_review, is_resubmission |

## Factor Impact Analysis

### Most Common Factors

| Factor | Count | Avg Adjustment | Direction |
|--------|-------|----------------|----------|
| base_rate | 504 | +68.7% | + |
| facility_pai_passed | 497 | +12.0% | + |
| breakthrough_therapy | 287 | +8.0% | + |
| is_resubmission | 175 | -9.1% | - |
| single_arm_trial | 130 | -7.0% | - |
| priority_review | 109 | +5.0% | + |
| probability_bounds | 52 | -10.2% | - |
| primary_endpoint_not_met | 15 | -70.0% | - |
| floor_fda_designation | 14 | +15.2% | + |
| trial_region_china_only | 12 | -50.0% | - |
| hard_cap_critical | 9 | -17.2% | - |
| accelerated_approval | 6 | +6.0% | + |
| fast_track | 5 | +5.0% | + |
| hard_cap_catastrophic | 4 | -12.7% | - |
| orphan_drug | 1 | +4.0% | + |

## Model Insights

### Calibration Analysis

The model assigns probabilities that should correlate with actual approval rates:

- **Good separation**: Approved events average 78.8% vs CRL events 45.8%

### Class Imbalance

- Dataset is heavily imbalanced: 477 approved (94.6%) vs 27 CRL (5.4%)
- This makes CRL prediction particularly challenging
- False positive rate (predicted approved but CRL): 66.7%

---

*Report generated by scripts/backtest.py*
