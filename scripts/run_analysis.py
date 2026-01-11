#!/usr/bin/env python3
"""
PDUFA Batch Analysis Script
============================

Run PDUFAAnalyzer on all enriched events and save results.

Usage:
    python scripts/run_analysis.py                    # Analyze all 523 events
    python scripts/run_analysis.py --limit 10        # Analyze first 10 events
    python scripts/run_analysis.py --output-dir ./custom_results

Reference: test_analysis_e2e.py (working E2E test)
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tickergenius.analysis.pdufa import PDUFAAnalyzer, AnalysisContext
from tickergenius.analysis.pdufa._context import (
    FDADesignations,
    AdComInfo,
    ClinicalInfo,
    ManufacturingInfo,
    CRLInfo,
)
from tickergenius.schemas.enums import CRLType

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def get_field_value(data: dict, field: str, default=None):
    """
    Extract value from StatusField structure.

    StatusField structure:
        {
            "status": "found" | "not_found" | "confirmed_none" | ...,
            "value": <actual value>,
            ...
        }

    Args:
        data: Event dictionary
        field: Field name to extract
        default: Default value if not found

    Returns:
        Extracted value or default
    """
    field_data = data.get(field, {})

    # Handle StatusField structure
    if isinstance(field_data, dict):
        if field_data.get("status") == "found":
            return field_data.get("value", default)
        # Also check for direct value (some fields may be plain dict with "value")
        if "value" in field_data and field_data.get("value") is not None:
            return field_data.get("value")

    # Handle direct value (non-StatusField)
    if not isinstance(field_data, dict):
        return field_data if field_data is not None else default

    return default


def get_fda_designations(event: dict) -> FDADesignations:
    """
    Extract FDA designations from event.

    Handles both:
    - fda_designations dict (new format)
    - Individual StatusField fields (legacy format)
    """
    # Check for fda_designations dict (new format)
    fda_designations_dict = event.get("fda_designations")
    if isinstance(fda_designations_dict, dict):
        return FDADesignations(
            breakthrough_therapy=fda_designations_dict.get("breakthrough_therapy", False),
            priority_review=fda_designations_dict.get("priority_review", False),
            fast_track=fda_designations_dict.get("fast_track", False),
            orphan_drug=fda_designations_dict.get("orphan_drug", False),
            accelerated_approval=fda_designations_dict.get("accelerated_approval", False),
        )

    # Fallback to individual StatusField fields (legacy format)
    return FDADesignations(
        breakthrough_therapy=get_field_value(event, "breakthrough_therapy", False),
        priority_review=get_field_value(event, "priority_review", False),
        fast_track=get_field_value(event, "fast_track", False),
        orphan_drug=get_field_value(event, "orphan_drug", False),
        accelerated_approval=get_field_value(event, "accelerated_approval", False),
    )


def get_adcom_info(event: dict) -> AdComInfo:
    """
    Extract AdCom info from event.

    Handles both:
    - adcom_info dict (new format)
    - Individual StatusField fields (legacy format)
    """
    # Check for adcom_info dict (new format)
    adcom_info_dict = event.get("adcom_info")
    if isinstance(adcom_info_dict, dict):
        was_held = adcom_info_dict.get("held", False) or adcom_info_dict.get("scheduled", False)
        vote_for = adcom_info_dict.get("vote_for")
        vote_against = adcom_info_dict.get("vote_against")
        vote_ratio = None
        if vote_for is not None and vote_against is not None:
            total = vote_for + vote_against
            if total > 0:
                vote_ratio = vote_for / total
        return AdComInfo(
            was_held=was_held,
            vote_ratio=vote_ratio,
        )

    # Fallback to legacy format
    adcom_held = get_field_value(event, "adcom_scheduled", False)
    adcom_vote = get_field_value(event, "adcom_vote_ratio")
    return AdComInfo(
        was_held=adcom_held,
        vote_ratio=adcom_vote if adcom_vote else None,
    )


def get_clinical_info(event: dict) -> ClinicalInfo:
    """Extract clinical info from event."""
    # Extract phase - handle both "Phase 3" string and "phase3" formats
    phase_value = get_field_value(event, "phase", "phase3")
    if isinstance(phase_value, str):
        phase_value = phase_value.lower().replace(" ", "")

    # Extract is_single_arm
    is_single_arm = get_field_value(event, "is_single_arm", False)

    # Extract trial_region
    trial_region = get_field_value(event, "trial_region", "global")

    # Extract primary_endpoint_met
    primary_met = get_field_value(event, "primary_endpoint_met", True)

    # Extract clinical_hold_history
    has_clinical_hold = get_field_value(event, "clinical_hold_history", False)

    return ClinicalInfo(
        phase=phase_value,
        primary_endpoint_met=primary_met,
        is_single_arm=is_single_arm,
        trial_region=trial_region,
        has_clinical_hold_history=has_clinical_hold,
    )


def get_manufacturing_info(event: dict) -> ManufacturingInfo:
    """Extract manufacturing info from event."""
    pai_passed = get_field_value(event, "pai_passed", False)
    warning_letter_date = get_field_value(event, "warning_letter_date")
    fda_483_date = get_field_value(event, "fda_483_date")
    fda_483_obs = get_field_value(event, "fda_483_observations", 0)

    return ManufacturingInfo(
        pai_passed=pai_passed if pai_passed else False,
        has_warning_letter=warning_letter_date is not None,
        warning_letter_date=warning_letter_date,
        fda_483_date=fda_483_date,
        fda_483_observations=fda_483_obs if fda_483_obs else 0,
    )


def get_crl_history(event: dict) -> tuple[CRLInfo, ...]:
    """Extract CRL history from event."""
    crl_history = []

    # Check is_resubmission or has_prior_crl
    is_resubmission = get_field_value(event, "is_resubmission", False)
    has_prior_crl = get_field_value(event, "has_prior_crl", False)

    # Check if current result is CRL (for context)
    result = event.get("result", "pending")

    if is_resubmission or has_prior_crl:
        crl_reason = get_field_value(event, "crl_reason_type", "unknown")
        prior_crl_reason = event.get("prior_crl_reason")

        # Map CRL reason to CRLType
        if crl_reason == "cmc" or (isinstance(prior_crl_reason, str) and "cmc" in prior_crl_reason.lower()):
            crl_type = CRLType.CMC_MINOR
        elif crl_reason == "efficacy":
            crl_type = CRLType.EFFICACY_NEW_TRIAL
        elif crl_reason == "safety":
            crl_type = CRLType.SAFETY_NEW_TRIAL
        else:
            crl_type = CRLType.CMC_MINOR  # Default to CMC as most common

        crl_history.append(CRLInfo(crl_type=crl_type))

    return tuple(crl_history)


def event_to_context(event: dict) -> AnalysisContext:
    """
    Convert enriched event JSON to AnalysisContext.

    This function handles the full complexity of the enriched event format,
    including StatusField structures and nested dictionaries.

    Args:
        event: Enriched event dictionary

    Returns:
        AnalysisContext ready for PDUFAAnalyzer
    """
    # Basic info
    ticker = event.get("ticker", "UNKNOWN")
    drug_name = event.get("drug_name", "Unknown Drug")

    # PDUFA date
    pdufa_date_str = event.get("pdufa_date")
    if pdufa_date_str:
        pdufa_date = date.fromisoformat(pdufa_date_str)
    else:
        pdufa_date = date.today()

    # Extract all components
    fda_designations = get_fda_designations(event)
    adcom = get_adcom_info(event)
    clinical = get_clinical_info(event)
    manufacturing = get_manufacturing_info(event)
    crl_history = get_crl_history(event)

    # Biosimilar check
    is_biosimilar = get_field_value(event, "is_biosimilar", False)
    approval_type = get_field_value(event, "approval_type", "").lower()
    if "bla" in approval_type or "biosimilar" in approval_type:
        is_biosimilar = True

    return AnalysisContext(
        ticker=ticker,
        drug_name=drug_name,
        pdufa_date=pdufa_date,
        pdufa_confirmed=True,
        is_biosimilar=is_biosimilar if is_biosimilar else False,
        fda_designations=fda_designations,
        adcom=adcom,
        clinical=clinical,
        manufacturing=manufacturing,
        crl_history=crl_history,
        is_resubmission=len(crl_history) > 0,
    )


# =============================================================================
# Analysis Functions
# =============================================================================

def load_all_events(enriched_dir: Path) -> list[tuple[str, dict]]:
    """
    Load all enriched event JSON files.

    Args:
        enriched_dir: Path to enriched data directory

    Returns:
        List of (event_id, event_dict) tuples
    """
    events = []

    if not enriched_dir.exists():
        logger.error(f"Enriched directory not found: {enriched_dir}")
        return events

    json_files = sorted(enriched_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} event files in {enriched_dir}")

    for path in json_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                event = json.load(f)
            event_id = path.stem  # filename without extension
            events.append((event_id, event))
        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}")

    return events


def analyze_single_event(
    event_id: str,
    event: dict,
    analyzer: PDUFAAnalyzer,
) -> dict:
    """
    Analyze a single event.

    Args:
        event_id: Event identifier
        event: Event dictionary
        analyzer: PDUFAAnalyzer instance

    Returns:
        Analysis result dictionary
    """
    context = event_to_context(event)
    result = analyzer.analyze(context)

    return {
        "event_id": event_id,
        "ticker": context.ticker,
        "drug_name": context.drug_name,
        "pdufa_date": str(context.pdufa_date),
        "actual_result": event.get("result", "pending"),
        "probability": result.probability,
        "base_probability": result.base_probability,
        "confidence": result.confidence_score,
        "factors": [
            {
                "name": f.name,
                "adjustment": f.adjustment,
                "reason": f.reason,
            }
            for f in result.factors
            if f.adjustment != 0
        ],
        "warnings": result.data_quality_warnings,
        "is_resubmission": context.is_resubmission,
        "is_biosimilar": context.is_biosimilar,
        "fda_designations": {
            "breakthrough_therapy": context.fda_designations.breakthrough_therapy,
            "priority_review": context.fda_designations.priority_review,
            "fast_track": context.fda_designations.fast_track,
            "orphan_drug": context.fda_designations.orphan_drug,
            "accelerated_approval": context.fda_designations.accelerated_approval,
        },
        "analyzed_at": datetime.now().isoformat(),
    }


def run_batch_analysis(
    events: list[tuple[str, dict]],
    output_dir: Path,
    limit: Optional[int] = None,
) -> dict:
    """
    Run batch analysis on all events.

    Args:
        events: List of (event_id, event_dict) tuples
        output_dir: Output directory for results
        limit: Maximum number of events to process (for testing)

    Returns:
        Summary statistics
    """
    # Apply limit
    if limit is not None and limit > 0:
        events = events[:limit]
        logger.info(f"Limiting to {limit} events")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Initialize analyzer
    analyzer = PDUFAAnalyzer()

    # Track statistics
    stats = {
        "total": len(events),
        "success": 0,
        "error": 0,
        "by_result": {"approved": [], "crl": [], "pending": [], "withdrawn": []},
    }

    results = []

    for i, (event_id, event) in enumerate(events, 1):
        try:
            # Analyze
            result = analyze_single_event(event_id, event, analyzer)
            results.append(result)

            # Save individual result
            output_path = output_dir / f"{event_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Update stats
            stats["success"] += 1
            actual_result = result["actual_result"]
            if actual_result in stats["by_result"]:
                stats["by_result"][actual_result].append(result["probability"])

            # Progress
            if i % 50 == 0 or i == len(events):
                logger.info(f"Progress: {i}/{len(events)} ({i/len(events)*100:.1f}%)")

        except Exception as e:
            stats["error"] += 1
            logger.error(f"Error analyzing {event_id}: {e}")

    # Calculate summary statistics
    for result_type, probs in stats["by_result"].items():
        if probs:
            stats["by_result"][result_type] = {
                "count": len(probs),
                "avg_probability": sum(probs) / len(probs),
                "min_probability": min(probs),
                "max_probability": max(probs),
            }
        else:
            stats["by_result"][result_type] = {"count": 0}

    # Save summary
    summary_path = output_dir / "_summary.json"
    summary = {
        "analyzed_at": datetime.now().isoformat(),
        "total_events": stats["total"],
        "success_count": stats["success"],
        "error_count": stats["error"],
        "by_result": stats["by_result"],
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return stats


# =============================================================================
# Main
# =============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run PDUFA analysis on all enriched events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze all events
    python scripts/run_analysis.py

    # Analyze first 10 events (for testing)
    python scripts/run_analysis.py --limit 10

    # Custom output directory
    python scripts/run_analysis.py --output-dir ./my_results

    # Verbose logging
    python scripts/run_analysis.py -v
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of events to analyze (for testing)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for results (default: data/analysis_results)",
    )
    parser.add_argument(
        "--enriched-dir",
        type=str,
        default=None,
        help="Enriched data directory (default: data/enriched)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 60)
    print("PDUFA Batch Analysis")
    print("=" * 60)

    # Set directories
    enriched_dir = Path(args.enriched_dir) if args.enriched_dir else PROJECT_ROOT / "data" / "enriched"
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "data" / "analysis_results"

    print(f"Enriched data: {enriched_dir}")
    print(f"Output: {output_dir}")
    if args.limit:
        print(f"Limit: {args.limit} events")
    print()

    # Load events
    events = load_all_events(enriched_dir)
    if not events:
        print("No events found. Exiting.")
        sys.exit(1)

    print(f"Loaded {len(events)} events")
    print()

    # Run analysis
    print("Running analysis...")
    print("-" * 60)

    stats = run_batch_analysis(events, output_dir, limit=args.limit)

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total events: {stats['total']}")
    print(f"Success: {stats['success']}")
    print(f"Errors: {stats['error']}")
    print()

    print("By Actual Result:")
    for result_type, result_stats in stats["by_result"].items():
        if isinstance(result_stats, dict) and result_stats.get("count", 0) > 0:
            print(f"  {result_type.upper()}:")
            print(f"    Count: {result_stats['count']}")
            print(f"    Avg Probability: {result_stats['avg_probability']:.1%}")
            print(f"    Range: {result_stats['min_probability']:.1%} - {result_stats['max_probability']:.1%}")

    print()
    print(f"Results saved to: {output_dir}")
    print(f"Summary saved to: {output_dir / '_summary.json'}")


if __name__ == "__main__":
    main()
