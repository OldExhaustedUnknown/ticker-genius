#!/usr/bin/env python3
"""
Calculate days_to_pdufa field for all enriched PDUFA records.

Adds the following fields to each record:
- days_to_pdufa: int (can be negative for past dates)
- pdufa_status: "upcoming" (>30 days), "imminent" (0-30), "past" (<0)
- risk_tier: "HIGH" (<30 days), "MEDIUM" (30-90), "LOW" (>90)
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple
import re


# Reference date for calculation
TODAY = date(2026, 1, 10)

# Directory containing enriched JSON files
ENRICHED_DIR = Path(__file__).parent.parent / "data" / "enriched"


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse date string in various formats.

    Supported formats:
    - YYYY-MM-DD (ISO format)
    - YYYYMMDD (compact format)
    - MM/DD/YYYY
    - DD-MM-YYYY
    - Month DD, YYYY (e.g., "January 10, 2026")
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try ISO format first (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try compact format (YYYYMMDD) - common in the data
    try:
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        pass

    # Try MM/DD/YYYY
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except ValueError:
        pass

    # Try DD-MM-YYYY
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        pass

    # Try "Month DD, YYYY"
    try:
        return datetime.strptime(date_str, "%B %d, %Y").date()
    except ValueError:
        pass

    # Try "Mon DD, YYYY" (abbreviated month)
    try:
        return datetime.strptime(date_str, "%b %d, %Y").date()
    except ValueError:
        pass

    print(f"  [WARNING] Could not parse date: {date_str}")
    return None


def calculate_pdufa_status(days: int) -> str:
    """
    Determine PDUFA status based on days remaining.

    Returns:
    - "past": PDUFA date has passed (days < 0)
    - "imminent": PDUFA within 30 days (0 <= days <= 30)
    - "upcoming": PDUFA more than 30 days away (days > 30)
    """
    if days < 0:
        return "past"
    elif days <= 30:
        return "imminent"
    else:
        return "upcoming"


def calculate_risk_tier(days: int) -> str:
    """
    Determine risk tier based on days to PDUFA.

    Risk tiers (for trading purposes):
    - "HIGH": Less than 30 days to PDUFA (high volatility expected)
    - "MEDIUM": 30-90 days to PDUFA (moderate positioning window)
    - "LOW": More than 90 days to PDUFA (early monitoring)
    """
    if days < 30:
        return "HIGH"
    elif days <= 90:
        return "MEDIUM"
    else:
        return "LOW"


def process_file(filepath: Path) -> Tuple[bool, str]:
    """
    Process a single JSON file and add days_to_pdufa fields.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"JSON parse error: {e}"
    except Exception as e:
        return False, f"Read error: {e}"

    # Get pdufa_date
    pdufa_date_str = data.get("pdufa_date")
    if not pdufa_date_str:
        return False, "No pdufa_date field found"

    # Parse the date
    pdufa_date = parse_date(pdufa_date_str)
    if not pdufa_date:
        return False, f"Could not parse pdufa_date: {pdufa_date_str}"

    # Calculate days to PDUFA
    days_to_pdufa = (pdufa_date - TODAY).days

    # Determine status and risk tier
    pdufa_status = calculate_pdufa_status(days_to_pdufa)
    risk_tier = calculate_risk_tier(days_to_pdufa)

    # Add new fields
    data["days_to_pdufa"] = days_to_pdufa
    data["pdufa_status"] = pdufa_status
    data["risk_tier"] = risk_tier
    data["days_calculated_at"] = datetime.now().isoformat()

    # Write back
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return False, f"Write error: {e}"

    return True, f"days={days_to_pdufa}, status={pdufa_status}, risk={risk_tier}"


def main():
    """Main entry point."""
    print(f"Calculate Days to PDUFA")
    print(f"=" * 50)
    print(f"Reference date: {TODAY}")
    print(f"Enriched directory: {ENRICHED_DIR}")
    print()

    if not ENRICHED_DIR.exists():
        print(f"ERROR: Directory not found: {ENRICHED_DIR}")
        return 1

    # Get all JSON files
    json_files = sorted(ENRICHED_DIR.glob("*.json"))

    if not json_files:
        print("No JSON files found in enriched directory")
        return 1

    print(f"Found {len(json_files)} JSON files")
    print("-" * 50)

    # Process each file
    success_count = 0
    error_count = 0

    # Statistics by status and tier
    status_counts = {"past": 0, "imminent": 0, "upcoming": 0}
    tier_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for filepath in json_files:
        success, message = process_file(filepath)

        if success:
            success_count += 1
            # Extract status and tier from message
            parts = message.split(", ")
            for part in parts:
                if part.startswith("status="):
                    status = part.split("=")[1]
                    status_counts[status] = status_counts.get(status, 0) + 1
                elif part.startswith("risk="):
                    tier = part.split("=")[1]
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1
            print(f"[OK] {filepath.name}: {message}")
        else:
            error_count += 1
            print(f"[ERROR] {filepath.name}: {message}")

    # Summary
    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total files:  {len(json_files)}")
    print(f"Successful:   {success_count}")
    print(f"Errors:       {error_count}")
    print()
    print("By PDUFA Status:")
    print(f"  Past:      {status_counts.get('past', 0)}")
    print(f"  Imminent:  {status_counts.get('imminent', 0)}")
    print(f"  Upcoming:  {status_counts.get('upcoming', 0)}")
    print()
    print("By Risk Tier:")
    print(f"  HIGH:      {tier_counts.get('HIGH', 0)}")
    print(f"  MEDIUM:    {tier_counts.get('MEDIUM', 0)}")
    print(f"  LOW:       {tier_counts.get('LOW', 0)}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    exit(main())
