"""
PDUFA Prediction Backtest Script
=================================
Analyzes prediction accuracy on historical PDUFA events.

Usage:
    python scripts/backtest.py
    python scripts/backtest.py --output docs/BACKTEST_REPORT.md
"""

import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tickergenius.analysis.pdufa import PDUFAAnalyzer, AnalysisContext
from tickergenius.analysis.pdufa._context import (
    FDADesignations,
    AdComInfo,
    ClinicalInfo,
    ManufacturingInfo,
    CRLInfo,
)
from tickergenius.schemas.enums import CRLType


# -----------------------------------------------------------------------------
# Data Structures
# -----------------------------------------------------------------------------

@dataclass
class PredictionResult:
    """Single event prediction result."""
    event_id: str
    ticker: str
    drug_name: str
    pdufa_date: str
    actual_result: str  # "approved" or "crl"
    predicted_prob: float
    base_prob: float
    confidence: float
    factors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def predicted_approved(self) -> bool:
        """Predict approved if prob > 50%."""
        return self.predicted_prob > 0.5

    @property
    def is_correct(self) -> bool:
        """Check if prediction matches actual result."""
        if self.actual_result == "approved":
            return self.predicted_approved
        elif self.actual_result == "crl":
            return not self.predicted_approved
        return False

    @property
    def is_true_positive(self) -> bool:
        """Predicted approved and was approved."""
        return self.predicted_approved and self.actual_result == "approved"

    @property
    def is_false_positive(self) -> bool:
        """Predicted approved but was CRL."""
        return self.predicted_approved and self.actual_result == "crl"

    @property
    def is_true_negative(self) -> bool:
        """Predicted CRL and was CRL."""
        return not self.predicted_approved and self.actual_result == "crl"

    @property
    def is_false_negative(self) -> bool:
        """Predicted CRL but was approved."""
        return not self.predicted_approved and self.actual_result == "approved"


@dataclass
class BacktestMetrics:
    """Aggregated backtest metrics."""
    total_events: int = 0
    approved_count: int = 0
    crl_count: int = 0
    error_count: int = 0

    # Accuracy
    correct_predictions: int = 0

    # Confusion matrix
    true_positives: int = 0  # Predicted approved, was approved
    false_positives: int = 0  # Predicted approved, was CRL
    true_negatives: int = 0  # Predicted CRL, was CRL
    false_negatives: int = 0  # Predicted CRL, was approved

    # Probability distributions
    approved_probs: list[float] = field(default_factory=list)
    crl_probs: list[float] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        """Overall prediction accuracy."""
        if self.total_events == 0:
            return 0.0
        return self.correct_predictions / self.total_events

    @property
    def precision(self) -> float:
        """Precision for approval prediction (TP / (TP + FP))."""
        total = self.true_positives + self.false_positives
        if total == 0:
            return 0.0
        return self.true_positives / total

    @property
    def recall(self) -> float:
        """Recall for approval prediction (TP / (TP + FN))."""
        total = self.true_positives + self.false_negatives
        if total == 0:
            return 0.0
        return self.true_positives / total

    @property
    def f1_score(self) -> float:
        """F1 score for approval prediction."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def avg_approved_prob(self) -> float:
        """Average probability for approved events."""
        if not self.approved_probs:
            return 0.0
        return sum(self.approved_probs) / len(self.approved_probs)

    @property
    def avg_crl_prob(self) -> float:
        """Average probability for CRL events."""
        if not self.crl_probs:
            return 0.0
        return sum(self.crl_probs) / len(self.crl_probs)

    @property
    def prob_separation(self) -> float:
        """Separation between approved and CRL average probabilities."""
        return self.avg_approved_prob - self.avg_crl_prob


# -----------------------------------------------------------------------------
# Event Conversion (from test_analysis_e2e.py)
# -----------------------------------------------------------------------------

def get_field_value(data: dict, field_name: str, default=None):
    """Extract value from StatusField structure."""
    field_data = data.get(field_name, {})
    if isinstance(field_data, dict):
        if field_data.get("status") == "found":
            return field_data.get("value", default)
    return default


def event_to_context(event: dict) -> AnalysisContext:
    """Convert enriched event JSON to AnalysisContext."""

    # Basic info
    ticker = event.get("ticker", "UNKNOWN")
    drug_name = event.get("drug_name", "Unknown Drug")

    # PDUFA date
    pdufa_date_str = event.get("pdufa_date")
    if pdufa_date_str:
        pdufa_date = date.fromisoformat(pdufa_date_str)
    else:
        pdufa_date = date.today()

    # FDA Designations - check both formats
    fda_desig = event.get("fda_designations", {})
    if isinstance(fda_desig, dict) and "breakthrough_therapy" in fda_desig:
        # New format: nested dict
        fda_designations = FDADesignations(
            breakthrough_therapy=fda_desig.get("breakthrough_therapy", False) or False,
            priority_review=fda_desig.get("priority_review", False) or False,
            fast_track=fda_desig.get("fast_track", False) or False,
            orphan_drug=fda_desig.get("orphan_drug", False) or False,
            accelerated_approval=fda_desig.get("accelerated_approval", False) or False,
        )
    else:
        # Legacy format: individual fields
        fda_designations = FDADesignations(
            breakthrough_therapy=get_field_value(event, "breakthrough_therapy", False) or False,
            priority_review=get_field_value(event, "priority_review", False) or False,
            fast_track=get_field_value(event, "fast_track", False) or False,
            orphan_drug=get_field_value(event, "orphan_drug", False) or False,
            accelerated_approval=get_field_value(event, "accelerated_approval", False) or False,
        )

    # AdCom - check nested format first
    adcom_info = event.get("adcom_info", {})
    if isinstance(adcom_info, dict) and ("held" in adcom_info or "scheduled" in adcom_info):
        adcom_held = adcom_info.get("held", False) or adcom_info.get("scheduled", False)
        vote_for = adcom_info.get("vote_for")
        vote_against = adcom_info.get("vote_against")
        if vote_for is not None and vote_against is not None:
            total = vote_for + vote_against
            vote_ratio = vote_for / total if total > 0 else None
        else:
            vote_ratio = None
        adcom = AdComInfo(
            was_held=adcom_held or False,
            vote_ratio=vote_ratio,
            vote_for=vote_for,
            vote_against=vote_against,
            outcome=adcom_info.get("outcome"),
        )
    else:
        adcom_held = get_field_value(event, "adcom_scheduled", False)
        adcom_vote = get_field_value(event, "adcom_vote_ratio")
        adcom = AdComInfo(
            was_held=adcom_held or False,
            vote_ratio=adcom_vote if adcom_vote else None,
        )

    # Clinical
    is_single_arm = get_field_value(event, "is_single_arm", False)
    if is_single_arm is None:
        is_single_arm_data = event.get("is_single_arm", {})
        if isinstance(is_single_arm_data, dict):
            is_single_arm = is_single_arm_data.get("value", False) or False
        else:
            is_single_arm = False

    trial_region = get_field_value(event, "trial_region", "global")
    if trial_region is None:
        trial_region_data = event.get("trial_region", {})
        if isinstance(trial_region_data, dict):
            trial_region = trial_region_data.get("value", "global")
        else:
            trial_region = "global"

    primary_met = get_field_value(event, "primary_endpoint_met", True)
    if primary_met is None:
        primary_met_data = event.get("primary_endpoint_met", {})
        if isinstance(primary_met_data, dict):
            primary_met = primary_met_data.get("value", True)
        else:
            primary_met = True  # Default True if unknown

    # Phase
    phase_data = event.get("phase", {})
    if isinstance(phase_data, dict):
        phase = phase_data.get("value", "phase3") or "phase3"
    else:
        phase = phase_data if phase_data else "phase3"

    clinical_hold = get_field_value(event, "clinical_hold_history", False)
    if clinical_hold is None:
        clinical_hold_data = event.get("clinical_hold_history", {})
        if isinstance(clinical_hold_data, dict):
            clinical_hold = clinical_hold_data.get("value", False) or False
        else:
            clinical_hold = False

    clinical = ClinicalInfo(
        phase=phase,
        primary_endpoint_met=primary_met,
        is_single_arm=is_single_arm or False,
        trial_region=trial_region,
        has_clinical_hold_history=clinical_hold or False,
    )

    # Manufacturing
    pai_passed = get_field_value(event, "pai_passed", False)
    if pai_passed is None:
        pai_data = event.get("pai_passed", {})
        if isinstance(pai_data, dict):
            pai_passed = pai_data.get("value", False) or False
        else:
            pai_passed = False

    warning_letter_date = get_field_value(event, "warning_letter_date")
    if warning_letter_date is None:
        wl_data = event.get("warning_letter_date", {})
        if isinstance(wl_data, dict):
            warning_letter_date = wl_data.get("value")

    fda_483_date = get_field_value(event, "fda_483_date")
    fda_483_obs = get_field_value(event, "fda_483_observations", 0) or 0

    manufacturing = ManufacturingInfo(
        pai_passed=pai_passed or False,
        has_warning_letter=warning_letter_date is not None,
        warning_letter_date=warning_letter_date,
        fda_483_date=fda_483_date,
        fda_483_observations=fda_483_obs,
    )

    # CRL History - check if already has CRL
    crl_history = []
    is_resubmission = get_field_value(event, "is_resubmission", False)
    if is_resubmission is None:
        is_resub_data = event.get("is_resubmission", {})
        if isinstance(is_resub_data, dict):
            is_resubmission = is_resub_data.get("value", False) or False
        else:
            is_resubmission = False

    has_prior_crl = get_field_value(event, "has_prior_crl", False)
    if has_prior_crl is None:
        has_prior_data = event.get("has_prior_crl", {})
        if isinstance(has_prior_data, dict):
            has_prior_crl = has_prior_data.get("value", False) or False
        else:
            has_prior_crl = False

    if is_resubmission or has_prior_crl:
        crl_reason = get_field_value(event, "crl_reason_type", "unknown")
        prior_crl_reason = event.get("prior_crl_reason")
        if prior_crl_reason:
            crl_reason = prior_crl_reason

        if crl_reason and "cmc" in str(crl_reason).lower():
            crl_type = CRLType.CMC_MINOR
        else:
            crl_type = CRLType.EFFICACY_NEW_TRIAL

        crl_history.append(CRLInfo(crl_type=crl_type))

    # Biosimilar
    is_biosimilar = get_field_value(event, "is_biosimilar", False)
    if is_biosimilar is None:
        biosim_data = event.get("is_biosimilar", {})
        if isinstance(biosim_data, dict):
            is_biosimilar = biosim_data.get("value", False) or False
        else:
            is_biosimilar = False

    return AnalysisContext(
        ticker=ticker,
        drug_name=drug_name,
        pdufa_date=pdufa_date,
        pdufa_confirmed=True,
        is_biosimilar=is_biosimilar or False,
        fda_designations=fda_designations,
        adcom=adcom,
        clinical=clinical,
        manufacturing=manufacturing,
        crl_history=tuple(crl_history),
        is_resubmission=len(crl_history) > 0 or is_resubmission,
    )


# -----------------------------------------------------------------------------
# Backtest Engine
# -----------------------------------------------------------------------------

def load_events(data_dir: Path) -> list[dict]:
    """Load all enriched events."""
    events = []
    for path in data_dir.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                event = json.load(f)
            event["_path"] = str(path)
            events.append(event)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return events


def analyze_event(event: dict, analyzer: PDUFAAnalyzer) -> PredictionResult:
    """Analyze a single event and return prediction result."""
    event_id = event.get("event_id", "unknown")
    ticker = event.get("ticker", "UNKNOWN")
    drug_name = event.get("drug_name", "Unknown")
    pdufa_date = event.get("pdufa_date", "")
    actual_result = event.get("result", "pending")

    try:
        context = event_to_context(event)
        result = analyzer.analyze(context)

        factors = [
            {
                "name": f.name,
                "adjustment": f.adjustment,
                "reason": f.reason,
            }
            for f in result.factors
            if f.adjustment != 0
        ]

        return PredictionResult(
            event_id=event_id,
            ticker=ticker,
            drug_name=drug_name,
            pdufa_date=pdufa_date,
            actual_result=actual_result,
            predicted_prob=result.probability,
            base_prob=result.base_probability,
            confidence=result.confidence_score,
            factors=factors,
            warnings=result.data_quality_warnings,
        )
    except Exception as e:
        return PredictionResult(
            event_id=event_id,
            ticker=ticker,
            drug_name=drug_name,
            pdufa_date=pdufa_date,
            actual_result=actual_result,
            predicted_prob=0.5,
            base_prob=0.5,
            confidence=0.0,
            error=str(e),
        )


def run_backtest(data_dir: Path) -> tuple[list[PredictionResult], BacktestMetrics]:
    """Run backtest on all events."""
    events = load_events(data_dir)
    analyzer = PDUFAAnalyzer()

    results = []
    metrics = BacktestMetrics()

    # Filter to approved and CRL only
    valid_results = ["approved", "crl"]
    filtered_events = [e for e in events if e.get("result") in valid_results]

    print(f"Total events: {len(events)}")
    print(f"Valid for backtest (approved + CRL): {len(filtered_events)}")
    print("-" * 60)

    for i, event in enumerate(filtered_events):
        result = analyze_event(event, analyzer)
        results.append(result)

        # Update metrics
        metrics.total_events += 1

        if result.error:
            metrics.error_count += 1
            continue

        if result.actual_result == "approved":
            metrics.approved_count += 1
            metrics.approved_probs.append(result.predicted_prob)
        else:
            metrics.crl_count += 1
            metrics.crl_probs.append(result.predicted_prob)

        if result.is_correct:
            metrics.correct_predictions += 1

        if result.is_true_positive:
            metrics.true_positives += 1
        elif result.is_false_positive:
            metrics.false_positives += 1
        elif result.is_true_negative:
            metrics.true_negatives += 1
        elif result.is_false_negative:
            metrics.false_negatives += 1

        # Progress
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(filtered_events)} events...")

    return results, metrics


def calculate_roc_auc(results: list[PredictionResult]) -> Optional[float]:
    """Calculate ROC-AUC if possible."""
    try:
        # Simple AUC calculation without sklearn
        # Sort by probability descending
        sorted_results = sorted(results, key=lambda x: x.predicted_prob, reverse=True)

        positives = sum(1 for r in sorted_results if r.actual_result == "approved")
        negatives = sum(1 for r in sorted_results if r.actual_result == "crl")

        if positives == 0 or negatives == 0:
            return None

        # Calculate AUC using trapezoidal rule
        tpr_points = []
        fpr_points = []

        tp = 0
        fp = 0

        for r in sorted_results:
            if r.actual_result == "approved":
                tp += 1
            else:
                fp += 1
            tpr_points.append(tp / positives)
            fpr_points.append(fp / negatives)

        # Calculate AUC
        auc = 0.0
        for i in range(1, len(fpr_points)):
            auc += (fpr_points[i] - fpr_points[i-1]) * (tpr_points[i] + tpr_points[i-1]) / 2

        return auc
    except Exception as e:
        print(f"Error calculating AUC: {e}")
        return None


# -----------------------------------------------------------------------------
# Report Generation
# -----------------------------------------------------------------------------

def generate_report(
    results: list[PredictionResult],
    metrics: BacktestMetrics,
    roc_auc: Optional[float],
) -> str:
    """Generate markdown backtest report."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# PDUFA Prediction Backtest Report

Generated: {now}

## Summary

| Metric | Value |
|--------|-------|
| Total Events | {metrics.total_events} |
| Approved | {metrics.approved_count} |
| CRL | {metrics.crl_count} |
| Errors | {metrics.error_count} |

## Prediction Accuracy

| Metric | Value |
|--------|-------|
| Accuracy | {metrics.accuracy:.1%} |
| Precision (Approval) | {metrics.precision:.1%} |
| Recall (Approval) | {metrics.recall:.1%} |
| F1 Score | {metrics.f1_score:.3f} |
| ROC-AUC | {f'{roc_auc:.3f}' if roc_auc else 'N/A'} |

## Confusion Matrix

|  | Predicted Approved | Predicted CRL |
|--|-------------------|---------------|
| **Actual Approved** | {metrics.true_positives} (TP) | {metrics.false_negatives} (FN) |
| **Actual CRL** | {metrics.false_positives} (FP) | {metrics.true_negatives} (TN) |

## Probability Distribution

| Actual Result | Avg Probability | Min | Max | Count |
|---------------|-----------------|-----|-----|-------|
| Approved | {metrics.avg_approved_prob:.1%} | {min(metrics.approved_probs):.1%} | {max(metrics.approved_probs):.1%} | {len(metrics.approved_probs)} |
| CRL | {metrics.avg_crl_prob:.1%} | {min(metrics.crl_probs):.1%} | {max(metrics.crl_probs):.1%} | {len(metrics.crl_probs)} |

**Probability Separation**: {metrics.prob_separation:.1%} (Approved avg - CRL avg)

## Probability Buckets

"""

    # Create probability buckets
    buckets = [
        (0.0, 0.3, "Low (0-30%)"),
        (0.3, 0.5, "Medium-Low (30-50%)"),
        (0.5, 0.7, "Medium-High (50-70%)"),
        (0.7, 0.9, "High (70-90%)"),
        (0.9, 1.01, "Very High (90%+)"),
    ]

    report += "| Probability Bucket | Total | Approved | CRL | Approval Rate |\n"
    report += "|-------------------|-------|----------|-----|---------------|\n"

    for low, high, label in buckets:
        bucket_results = [r for r in results if low <= r.predicted_prob < high]
        if bucket_results:
            approved = sum(1 for r in bucket_results if r.actual_result == "approved")
            crl = sum(1 for r in bucket_results if r.actual_result == "crl")
            rate = approved / len(bucket_results)
            report += f"| {label} | {len(bucket_results)} | {approved} | {crl} | {rate:.1%} |\n"
        else:
            report += f"| {label} | 0 | 0 | 0 | N/A |\n"

    # False positives (predicted approved but CRL)
    false_positives = [r for r in results if r.is_false_positive]
    if false_positives:
        report += "\n## False Positives (Predicted Approved but CRL)\n\n"
        report += "Events where model predicted >50% approval but received CRL:\n\n"
        report += "| Ticker | Drug | PDUFA Date | Predicted | Key Factors |\n"
        report += "|--------|------|------------|-----------|-------------|\n"

        for r in sorted(false_positives, key=lambda x: x.predicted_prob, reverse=True)[:15]:
            factors_str = ", ".join([f"{f['name']}" for f in r.factors[:3]]) if r.factors else "None"
            report += f"| {r.ticker} | {r.drug_name[:30]} | {r.pdufa_date} | {r.predicted_prob:.1%} | {factors_str} |\n"

    # False negatives (predicted CRL but approved)
    false_negatives = [r for r in results if r.is_false_negative]
    if false_negatives:
        report += "\n## False Negatives (Predicted CRL but Approved)\n\n"
        report += "Events where model predicted <50% approval but was approved:\n\n"
        report += "| Ticker | Drug | PDUFA Date | Predicted | Key Factors |\n"
        report += "|--------|------|------------|-----------|-------------|\n"

        for r in sorted(false_negatives, key=lambda x: x.predicted_prob)[:15]:
            factors_str = ", ".join([f"{f['name']}" for f in r.factors[:3]]) if r.factors else "None"
            report += f"| {r.ticker} | {r.drug_name[:30]} | {r.pdufa_date} | {r.predicted_prob:.1%} | {factors_str} |\n"

    # Low-confidence correct predictions for CRL
    true_negatives = [r for r in results if r.is_true_negative]
    if true_negatives:
        report += "\n## True Negatives (Correctly Predicted CRL)\n\n"
        report += "| Ticker | Drug | PDUFA Date | Predicted | Key Factors |\n"
        report += "|--------|------|------------|-----------|-------------|\n"

        for r in sorted(true_negatives, key=lambda x: x.predicted_prob)[:10]:
            factors_str = ", ".join([f"{f['name']}" for f in r.factors[:3]]) if r.factors else "None"
            report += f"| {r.ticker} | {r.drug_name[:30]} | {r.pdufa_date} | {r.predicted_prob:.1%} | {factors_str} |\n"

    # Factor impact analysis
    report += "\n## Factor Impact Analysis\n\n"

    # Count factor occurrences
    factor_counts = Counter()
    factor_adjustments = {}

    for r in results:
        for f in r.factors:
            name = f["name"]
            factor_counts[name] += 1
            if name not in factor_adjustments:
                factor_adjustments[name] = []
            factor_adjustments[name].append(f["adjustment"])

    report += "### Most Common Factors\n\n"
    report += "| Factor | Count | Avg Adjustment | Direction |\n"
    report += "|--------|-------|----------------|----------|\n"

    for name, count in factor_counts.most_common(20):
        adjs = factor_adjustments[name]
        avg_adj = sum(adjs) / len(adjs)
        direction = "+" if avg_adj > 0 else "-"
        report += f"| {name} | {count} | {avg_adj:+.1%} | {direction} |\n"

    # Model insights
    report += "\n## Model Insights\n\n"
    report += "### Calibration Analysis\n\n"
    report += "The model assigns probabilities that should correlate with actual approval rates:\n\n"

    # Check if probabilities are well-calibrated
    if metrics.prob_separation > 0.30:
        report += f"- **Good separation**: Approved events average {metrics.avg_approved_prob:.1%} vs CRL events {metrics.avg_crl_prob:.1%}\n"
    else:
        report += f"- **Poor separation**: Approved events average {metrics.avg_approved_prob:.1%} vs CRL events {metrics.avg_crl_prob:.1%}\n"
        report += f"- Model needs better discriminating factors\n"

    # Class imbalance note
    report += f"\n### Class Imbalance\n\n"
    report += f"- Dataset is heavily imbalanced: {metrics.approved_count} approved ({metrics.approved_count/metrics.total_events:.1%}) vs {metrics.crl_count} CRL ({metrics.crl_count/metrics.total_events:.1%})\n"
    report += f"- This makes CRL prediction particularly challenging\n"

    if metrics.false_positives > 0:
        fp_rate = metrics.false_positives / (metrics.false_positives + metrics.true_negatives) if (metrics.false_positives + metrics.true_negatives) > 0 else 0
        report += f"- False positive rate (predicted approved but CRL): {fp_rate:.1%}\n"

    report += "\n---\n\n"
    report += "*Report generated by scripts/backtest.py*\n"

    return report


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="PDUFA Prediction Backtest")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/enriched",
        help="Directory containing enriched event JSONs",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/BACKTEST_REPORT.md",
        help="Output report path",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)

    print("=" * 60)
    print("PDUFA Prediction Backtest")
    print("=" * 60)
    print(f"Data directory: {data_dir}")
    print(f"Output: {args.output}")
    print()

    # Run backtest
    results, metrics = run_backtest(data_dir)

    # Calculate ROC-AUC
    roc_auc = calculate_roc_auc(results)

    # Print summary
    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"Total events analyzed: {metrics.total_events}")
    print(f"Approved: {metrics.approved_count}, CRL: {metrics.crl_count}")
    print()
    print(f"Accuracy: {metrics.accuracy:.1%}")
    print(f"Precision (Approval): {metrics.precision:.1%}")
    print(f"Recall (Approval): {metrics.recall:.1%}")
    print(f"F1 Score: {metrics.f1_score:.3f}")
    if roc_auc:
        print(f"ROC-AUC: {roc_auc:.3f}")
    print()
    print("Confusion Matrix:")
    print(f"  TP (Approved correctly): {metrics.true_positives}")
    print(f"  FP (Predicted approved, was CRL): {metrics.false_positives}")
    print(f"  TN (CRL correctly): {metrics.true_negatives}")
    print(f"  FN (Predicted CRL, was approved): {metrics.false_negatives}")
    print()
    print(f"Avg probability for Approved: {metrics.avg_approved_prob:.1%}")
    print(f"Avg probability for CRL: {metrics.avg_crl_prob:.1%}")
    print(f"Separation: {metrics.prob_separation:.1%}")

    # Generate report
    report = generate_report(results, metrics, roc_auc)

    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print()
    print(f"Report written to: {output_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
