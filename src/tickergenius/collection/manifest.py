"""
Manifest Generator
===================
Generate manifest file summarizing collected data.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import Counter


def generate_manifest(data_dir: str = "data/collected") -> dict:
    """
    Generate manifest file for collected data.

    Returns:
        Manifest dictionary with collection statistics.
    """
    data_path = Path(data_dir)
    processed_dir = data_path / "processed"
    validation_dir = data_path / "validation_log"

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0",
        "statistics": {
            "total_cases": 0,
            "validated": 0,
            "needs_review": 0,
            "by_ticker": {},
        },
        "data_quality": {
            "tier1_coverage": 0.0,
            "tier2_coverage": 0.0,
            "tier3_coverage": 0.0,
            "fields_with_conflicts": [],
        },
        "cases": [],
    }

    if not processed_dir.exists():
        return manifest

    # Process each case file
    ticker_counts = Counter()
    validation_status = Counter()
    tier_counts = {1: 0, 2: 0, 3: 0}
    total_fields = 0

    for file_path in processed_dir.glob("*.json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                case = json.load(f)

            manifest["cases"].append({
                "case_id": case.get("case_id"),
                "ticker": case.get("ticker"),
                "drug_name": case.get("drug_name"),
            })

            ticker = case.get("ticker", "UNKNOWN")
            ticker_counts[ticker] += 1

            # Check validation status
            val_file = validation_dir / f"{case.get('case_id')}_validation.json"
            if val_file.exists():
                with open(val_file, encoding="utf-8") as f:
                    val = json.load(f)
                validation_status[val.get("status", "unknown")] += 1
            else:
                validation_status["no_validation"] += 1

            # Count source tiers
            for field_name in ["pdufa_date", "result", "breakthrough_therapy", "priority_review"]:
                field = case.get(field_name)
                if field and field.get("value") is not None:
                    total_fields += 1
                    sources = field.get("sources", [])
                    if "openfda" in sources:
                        tier_counts[1] += 1
                    elif "clinicaltrials.gov" in sources or "sec_edgar" in sources:
                        tier_counts[2] += 1
                    else:
                        tier_counts[3] += 1

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    # Calculate statistics
    manifest["statistics"]["total_cases"] = len(manifest["cases"])
    manifest["statistics"]["validated"] = validation_status.get("valid", 0)
    manifest["statistics"]["needs_review"] = validation_status.get("needs_review", 0)
    manifest["statistics"]["by_ticker"] = dict(ticker_counts.most_common(20))

    if total_fields > 0:
        manifest["data_quality"]["tier1_coverage"] = tier_counts[1] / total_fields
        manifest["data_quality"]["tier2_coverage"] = tier_counts[2] / total_fields
        manifest["data_quality"]["tier3_coverage"] = tier_counts[3] / total_fields

    return manifest


def save_manifest(data_dir: str = "data/collected"):
    """Generate and save manifest to file."""
    manifest = generate_manifest(data_dir)

    output_path = Path(data_dir) / "manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest saved to {output_path}")
    print(f"Total cases: {manifest['statistics']['total_cases']}")
    print(f"Validated: {manifest['statistics']['validated']}")
    print(f"Needs review: {manifest['statistics']['needs_review']}")
    print(f"Tier 1 coverage: {manifest['data_quality']['tier1_coverage']:.1%}")

    return manifest


if __name__ == "__main__":
    save_manifest()
