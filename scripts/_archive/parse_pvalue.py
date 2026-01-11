#!/usr/bin/env python
"""
Parse p_value text fields into p_value_numeric in enriched JSON files.

Handles patterns:
- Plain numbers: "0.001", "0.0001"
- Less than: "<0.001", "<0.0001", "p<0.001"
- Less than or equal: "<=0.01", "p<=0.001"
- Equals: "p=0.023", "p=0.001"
- Greater than: "p>0.05" (stored as the threshold value)
- Complex: "p=0.057 (missed), p=0.031 (24wk)" -> takes first value
- Special cases: "NS" (not significant), text descriptions -> None
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

# Pattern priority order (checked in sequence)
PATTERNS = [
    # p<value, p < value, p<=value
    (r'[pP]\s*[<≤]\s*(\d+\.?\d*(?:[eE][+-]?\d+)?)', 'less_than'),
    # p=value
    (r'[pP]\s*=\s*(\d+\.?\d*(?:[eE][+-]?\d+)?)', 'equals'),
    # p>value (not significant if > threshold)
    (r'[pP]\s*>\s*(\d+\.?\d*(?:[eE][+-]?\d+)?)', 'greater_than'),
    # <value or <=value (without p prefix)
    (r'^[<≤]\s*(\d+\.?\d*(?:[eE][+-]?\d+)?)', 'less_than'),
    # <=value
    (r'^<=\s*(\d+\.?\d*(?:[eE][+-]?\d+)?)', 'less_than_eq'),
    # Plain number
    (r'^(\d+\.?\d*(?:[eE][+-]?\d+)?)$', 'equals'),
]

# Values that indicate "not significant" or unparseable
NOT_PARSEABLE = {'ns', 'n.s.', 'not significant', 'na', 'n/a', 'none', 'null'}


def parse_pvalue(text: str) -> Tuple[Optional[float], str]:
    """
    Parse p-value text into numeric value.

    Returns:
        Tuple of (numeric_value, parse_info)
        - numeric_value: float or None if unparseable
        - parse_info: description of what was parsed
    """
    if text is None:
        return None, "null_input"

    text = str(text).strip()

    if not text:
        return None, "empty_string"

    # Check for "not significant" type values
    if text.lower() in NOT_PARSEABLE:
        return None, "not_significant"

    # Try each pattern
    for pattern, ptype in PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                value = float(match.group(1))
                return value, f"{ptype}:{match.group(0)}"
            except ValueError:
                continue

    # Handle complex cases with multiple p-values (take first)
    # e.g., "p=0.057 (missed), p=0.031 (24wk)"
    multi_match = re.search(r'[pP]\s*=\s*(\d+\.?\d*)', text)
    if multi_match:
        try:
            value = float(multi_match.group(1))
            return value, f"first_of_multiple:{multi_match.group(0)}"
        except ValueError:
            pass

    # Handle "p=0.881 (ITT), p<0.05 (subgroup)" - take first
    first_pval = re.search(r'(\d+\.?\d*)', text)
    if first_pval:
        try:
            value = float(first_pval.group(1))
            # Only accept if it looks like a p-value (0-1 range)
            if 0 <= value <= 1:
                return value, f"extracted_number:{first_pval.group(0)}"
        except ValueError:
            pass

    return None, f"unparseable:{text[:50]}"


def process_file(filepath: Path, dry_run: bool = False) -> Tuple[bool, str, Optional[float], Optional[float]]:
    """
    Process a single JSON file.

    Returns:
        Tuple of (changed, status_message, old_value, new_value)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return False, f"read_error:{e}", None, None

    # Get p_value field
    p_value_field = data.get('p_value')
    old_numeric = data.get('p_value_numeric')

    if not p_value_field or not isinstance(p_value_field, dict):
        return False, "no_p_value_field", old_numeric, None

    text_value = p_value_field.get('value')
    if text_value is None:
        return False, "p_value_is_null", old_numeric, None

    # Parse the text value
    new_numeric, parse_info = parse_pvalue(text_value)

    # Check if update is needed
    if old_numeric == new_numeric:
        return False, f"unchanged:{parse_info}", old_numeric, new_numeric

    if new_numeric is None and old_numeric is not None:
        # Don't overwrite existing numeric with None unless it's clearly wrong
        return False, f"kept_existing:{parse_info}", old_numeric, old_numeric

    # Update the value
    if not dry_run:
        data['p_value_numeric'] = new_numeric
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return True, f"updated:{parse_info}", old_numeric, new_numeric


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Parse p_value text to numeric values')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show details for each file')
    args = parser.parse_args()

    enriched_dir = Path('data/enriched')
    if not enriched_dir.exists():
        print(f"ERROR: Directory not found: {enriched_dir}")
        sys.exit(1)

    json_files = list(enriched_dir.glob('*.json'))
    if not json_files:
        print(f"ERROR: No JSON files found in {enriched_dir}")
        sys.exit(1)

    print(f"Processing {len(json_files)} files...")
    if args.dry_run:
        print("(DRY RUN - no files will be modified)")
    print()

    # Counters
    stats = {
        'total': len(json_files),
        'updated': 0,
        'unchanged': 0,
        'errors': 0,
        'no_pvalue': 0,
        'kept_existing': 0,
    }

    # Track parse patterns for summary
    parse_patterns = {}
    updates = []

    for filepath in sorted(json_files):
        changed, status, old_val, new_val = process_file(filepath, args.dry_run)

        # Extract pattern type from status
        pattern_type = status.split(':')[0]
        parse_patterns[pattern_type] = parse_patterns.get(pattern_type, 0) + 1

        if changed:
            stats['updated'] += 1
            updates.append((filepath.name, old_val, new_val, status))
            if args.verbose:
                print(f"  UPDATED: {filepath.name}: {old_val} -> {new_val} ({status})")
        elif 'error' in status:
            stats['errors'] += 1
            if args.verbose:
                print(f"  ERROR: {filepath.name}: {status}")
        elif 'no_p_value' in status or 'null' in status:
            stats['no_pvalue'] += 1
        elif 'kept_existing' in status:
            stats['kept_existing'] += 1
        else:
            stats['unchanged'] += 1

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total files:        {stats['total']}")
    print(f"Updated:            {stats['updated']}")
    print(f"Unchanged:          {stats['unchanged']}")
    print(f"Kept existing:      {stats['kept_existing']}")
    print(f"No p_value field:   {stats['no_pvalue']}")
    print(f"Errors:             {stats['errors']}")

    print("\n" + "-"*60)
    print("Parse Pattern Breakdown:")
    print("-"*60)
    for pattern, count in sorted(parse_patterns.items(), key=lambda x: -x[1]):
        print(f"  {pattern}: {count}")

    if updates:
        print("\n" + "-"*60)
        print(f"Files {'that would be ' if args.dry_run else ''}updated ({len(updates)}):")
        print("-"*60)
        for name, old, new, status in updates[:20]:
            old_str = f"{old}" if old is not None else "None"
            new_str = f"{new}" if new is not None else "None"
            print(f"  {name}: {old_str} -> {new_str}")
        if len(updates) > 20:
            print(f"  ... and {len(updates) - 20} more")

    print("\n" + "="*60)
    if args.dry_run:
        print("DRY RUN complete. Run without --dry-run to apply changes.")
    else:
        print(f"COMPLETE. {stats['updated']} files updated.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
