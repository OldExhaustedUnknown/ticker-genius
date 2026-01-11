#!/usr/bin/env python3
"""
Clean Duplicate Fields Script

Removes duplicate individual fields that are now consolidated into unified dicts:
- btd, priority_review, fast_track, orphan_drug, accelerated_approval -> fda_designations
- adcom_held, adcom_date, adcom_vote_favorable, adcom_recommendation -> adcom_info

IMPORTANT: Before removing any field, verifies data is preserved in the unified dict.
Creates backup of original structure before modification.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


# Define the duplicate fields to remove
FDA_DESIGNATION_FIELDS = ['btd', 'priority_review', 'fast_track', 'orphan_drug', 'accelerated_approval']
ADCOM_FIELDS = ['adcom_held', 'adcom_date', 'adcom_vote_favorable', 'adcom_recommendation']

# Mapping from individual field names to fda_designations keys
FDA_FIELD_MAPPING = {
    'btd': 'breakthrough_therapy',
    'priority_review': 'priority_review',
    'fast_track': 'fast_track',
    'orphan_drug': 'orphan_drug',
    'accelerated_approval': 'accelerated_approval'
}

# Mapping from individual field names to adcom_info keys
ADCOM_FIELD_MAPPING = {
    'adcom_held': 'held',
    'adcom_date': 'date',
    'adcom_vote_favorable': 'vote',
    'adcom_recommendation': 'outcome'
}


def get_field_value(data: dict, field: str) -> Any:
    """Extract value from a field, handling StatusInfo wrapper objects."""
    value = data.get(field)
    if value is None:
        return None
    if isinstance(value, dict) and 'value' in value:
        return value.get('value')
    return value


def verify_fda_designations(data: dict) -> dict:
    """
    Verify fda_designations dict has all designation data.
    Returns dict with verification status and any discrepancies.
    """
    result = {
        'has_unified_dict': 'fda_designations' in data and data['fda_designations'] is not None,
        'discrepancies': [],
        'preserved_data': {}
    }

    fda_designations = data.get('fda_designations', {}) or {}

    for individual_field, unified_key in FDA_FIELD_MAPPING.items():
        individual_value = get_field_value(data, individual_field)
        unified_value = fda_designations.get(unified_key)

        # Check if individual field exists
        if individual_field not in data:
            continue

        # Record the original data for preservation
        if individual_field in data:
            result['preserved_data'][individual_field] = data[individual_field]

        # Check for discrepancies (only if both have values)
        if individual_value is not None and unified_value is not None:
            # Convert to bool for comparison
            individual_bool = bool(individual_value) if individual_value is not None else None
            unified_bool = bool(unified_value) if unified_value is not None else None

            if individual_bool != unified_bool:
                result['discrepancies'].append({
                    'field': individual_field,
                    'individual_value': individual_value,
                    'unified_key': unified_key,
                    'unified_value': unified_value
                })

    return result


def verify_adcom_info(data: dict) -> dict:
    """
    Verify adcom_info dict has all AdCom data.
    Returns dict with verification status and any discrepancies.
    """
    result = {
        'has_unified_dict': 'adcom_info' in data and data['adcom_info'] is not None,
        'discrepancies': [],
        'preserved_data': {}
    }

    adcom_info = data.get('adcom_info', {}) or {}

    for individual_field, unified_key in ADCOM_FIELD_MAPPING.items():
        individual_value = get_field_value(data, individual_field)
        unified_value = adcom_info.get(unified_key)

        # Check if individual field exists
        if individual_field not in data:
            continue

        # Record the original data for preservation
        if individual_field in data:
            result['preserved_data'][individual_field] = data[individual_field]

        # Check for discrepancies (only if both have non-None values)
        if individual_value is not None and unified_value is not None:
            if individual_value != unified_value:
                result['discrepancies'].append({
                    'field': individual_field,
                    'individual_value': individual_value,
                    'unified_key': unified_key,
                    'unified_value': unified_value
                })

    return result


def ensure_data_preserved(data: dict) -> tuple[dict, list]:
    """
    Ensure data is properly preserved in unified dicts before removal.
    Updates unified dicts if data is missing.
    Returns (updated_data, migration_actions).
    """
    migration_actions = []

    # Ensure fda_designations exists
    if 'fda_designations' not in data or data['fda_designations'] is None:
        data['fda_designations'] = {}
        migration_actions.append('Created fda_designations dict')

    # Migrate FDA designation values if missing in unified dict
    for individual_field, unified_key in FDA_FIELD_MAPPING.items():
        individual_value = get_field_value(data, individual_field)
        unified_value = data['fda_designations'].get(unified_key)

        if individual_value is not None and unified_value is None:
            data['fda_designations'][unified_key] = bool(individual_value)
            migration_actions.append(f'Migrated {individual_field}={individual_value} to fda_designations.{unified_key}')

    # Ensure adcom_info exists
    if 'adcom_info' not in data or data['adcom_info'] is None:
        data['adcom_info'] = {
            'scheduled': False,
            'held': False,
            'outcome': None,
            'vote': None
        }
        migration_actions.append('Created adcom_info dict')

    # Migrate AdCom values if missing in unified dict
    for individual_field, unified_key in ADCOM_FIELD_MAPPING.items():
        individual_value = get_field_value(data, individual_field)
        unified_value = data['adcom_info'].get(unified_key)

        if individual_value is not None and unified_value is None:
            data['adcom_info'][unified_key] = individual_value
            migration_actions.append(f'Migrated {individual_field}={individual_value} to adcom_info.{unified_key}')

    return data, migration_actions


def clean_file(file_path: Path, backup_dir: Path, dry_run: bool = False) -> dict:
    """
    Clean duplicate fields from a single JSON file.
    Returns a report of actions taken.
    """
    report = {
        'file': file_path.name,
        'status': 'success',
        'fda_verification': None,
        'adcom_verification': None,
        'migration_actions': [],
        'removed_fields': [],
        'discrepancies': [],
        'errors': []
    }

    try:
        # Read original data
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Create backup
        if not dry_run:
            backup_path = backup_dir / file_path.name
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        # Verify FDA designations
        fda_result = verify_fda_designations(data)
        report['fda_verification'] = {
            'has_unified_dict': fda_result['has_unified_dict'],
            'discrepancy_count': len(fda_result['discrepancies'])
        }

        if fda_result['discrepancies']:
            report['discrepancies'].extend(fda_result['discrepancies'])

        # Verify AdCom info
        adcom_result = verify_adcom_info(data)
        report['adcom_verification'] = {
            'has_unified_dict': adcom_result['has_unified_dict'],
            'discrepancy_count': len(adcom_result['discrepancies'])
        }

        if adcom_result['discrepancies']:
            report['discrepancies'].extend(adcom_result['discrepancies'])

        # Ensure data is preserved (migrate if needed)
        data, migration_actions = ensure_data_preserved(data)
        report['migration_actions'] = migration_actions

        # Remove duplicate FDA designation fields
        for field in FDA_DESIGNATION_FIELDS:
            if field in data:
                if not dry_run:
                    del data[field]
                report['removed_fields'].append(field)

        # Remove duplicate AdCom fields
        for field in ADCOM_FIELDS:
            if field in data:
                if not dry_run:
                    del data[field]
                report['removed_fields'].append(field)

        # Save cleaned data
        if not dry_run and report['removed_fields']:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        report['status'] = 'error'
        report['errors'].append(str(e))

    return report


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Clean duplicate fields from enriched JSON files')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    args = parser.parse_args()

    # Setup paths
    data_dir = Path(__file__).parent.parent / 'data' / 'enriched'
    backup_dir = Path(__file__).parent.parent / 'data' / 'backup_before_cleanup'

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return 1

    # Create backup directory
    if not args.dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"Backup directory: {backup_dir}")

    # Get all JSON files
    json_files = sorted(data_dir.glob('*.json'))
    print(f"Found {len(json_files)} JSON files to process")

    if args.dry_run:
        print("\n[DRY RUN MODE - No files will be modified]\n")

    # Process each file
    reports = []
    total_removed = 0
    total_migrations = 0
    total_discrepancies = 0
    files_with_errors = []

    for file_path in json_files:
        report = clean_file(file_path, backup_dir, dry_run=args.dry_run)
        reports.append(report)

        total_removed += len(report['removed_fields'])
        total_migrations += len(report['migration_actions'])
        total_discrepancies += len(report['discrepancies'])

        if report['status'] == 'error':
            files_with_errors.append(report)

        if args.verbose:
            print(f"\n{report['file']}:")
            if report['migration_actions']:
                print(f"  Migrations: {report['migration_actions']}")
            if report['removed_fields']:
                print(f"  Removed fields: {report['removed_fields']}")
            if report['discrepancies']:
                print(f"  Discrepancies: {report['discrepancies']}")
            if report['errors']:
                print(f"  Errors: {report['errors']}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(json_files)}")
    print(f"Total fields removed: {total_removed}")
    print(f"Total migrations: {total_migrations}")
    print(f"Total discrepancies: {total_discrepancies}")
    print(f"Files with errors: {len(files_with_errors)}")

    if total_discrepancies > 0:
        print("\n[WARNING] Discrepancies found between individual fields and unified dicts.")
        print("The unified dict values were preserved. Review the discrepancies above.")

    if files_with_errors:
        print("\nFiles with errors:")
        for report in files_with_errors:
            print(f"  - {report['file']}: {report['errors']}")

    if not args.dry_run:
        print(f"\nOriginal files backed up to: {backup_dir}")

    # Save detailed report
    if not args.dry_run:
        report_path = backup_dir / 'cleanup_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'files_processed': len(json_files),
                    'total_removed': total_removed,
                    'total_migrations': total_migrations,
                    'total_discrepancies': total_discrepancies,
                    'files_with_errors': len(files_with_errors)
                },
                'reports': reports
            }, f, indent=2, ensure_ascii=False)
        print(f"Detailed report saved to: {report_path}")

    return 0 if not files_with_errors else 1


if __name__ == '__main__':
    exit(main())
