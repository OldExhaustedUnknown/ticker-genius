"""has_prior_crl 필드 자동 파생 - is_resubmission 기반"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

data_dir = Path('data/enriched')
updated = 0
skipped = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if already has has_prior_crl
    prior_crl = data.get('has_prior_crl')
    has_value = False
    if isinstance(prior_crl, dict):
        if prior_crl.get('status') == 'found':
            has_value = True
        elif prior_crl.get('status') == 'not_applicable':
            has_value = True
    elif prior_crl is not None:
        has_value = True

    if has_value:
        skipped += 1
        continue

    # Get is_resubmission value
    resub = data.get('is_resubmission')
    if isinstance(resub, dict):
        resub = resub.get('value')

    # Normalize to boolean
    is_resub = resub in [True, 1, '1', 'True', 'true']

    # Get result
    result = data.get('result', '')

    # Derive has_prior_crl
    derived_value = None
    source = None
    confidence = 0.0

    if result == 'crl':
        # For CRL events, assume no prior CRL unless explicitly known
        # (If this was a repeat CRL, it would likely be marked as resubmission)
        derived_value = is_resub  # If resubmission, there was a prior CRL
        source = 'derived_from_crl_context'
        confidence = 0.7
    elif result == 'approved':
        if is_resub:
            # Resubmission + approved = likely had prior CRL
            derived_value = True
            source = 'derived_from_resubmission'
            confidence = 0.85
        else:
            # First submission + approved = no prior CRL
            derived_value = False
            source = 'derived_from_first_submission'
            confidence = 0.95
    elif result == 'pending':
        if is_resub:
            derived_value = True
            source = 'derived_from_resubmission'
            confidence = 0.85
        else:
            derived_value = False
            source = 'derived_from_first_submission'
            confidence = 0.90
    elif result == 'withdrawn':
        derived_value = False
        source = 'derived_from_withdrawn'
        confidence = 0.70

    if derived_value is not None:
        data['has_prior_crl'] = {
            'status': 'found',
            'value': derived_value,
            'source': source,
            'confidence': confidence,
            'tier': 2
        }
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        label = 'Yes' if derived_value else 'No'
        print(f'{data.get("ticker")}: {data.get("drug_name", "")[:30]} -> {label} ({source})')
        updated += 1
    else:
        print(f'[SKIP] {data.get("ticker")}: result={result}, resub={resub}')

print(f'\nhas_prior_crl 자동 파생 완료')
print(f'Updated: {updated}')
print(f'Already had value: {skipped}')
