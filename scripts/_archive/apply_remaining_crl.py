"""나머지 7건 CRL 사유 적용"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ADDITIONAL_CRL = {
    'KANGIO': {'reason': 'CMC_ISSUE', 'detail': 'Impurity characterization required', 'pai': False, 'safety': False},
    'BIVALIRUDIN': {'reason': 'CMC_ISSUE', 'detail': 'Impurity characterization required', 'pai': False, 'safety': False},
    'ROXADUSTAT': {'reason': 'SAFETY_CONCERN', 'detail': 'CV safety MACE events, ADCOM 12-2 against', 'pai': False, 'safety': True},
    'FILGOTINIB': {'reason': 'SAFETY_CONCERN', 'detail': 'Testicular toxicity concerns', 'pai': False, 'safety': True},
    'SURUFATINIB': {'reason': 'CLINICAL_DATA', 'detail': 'Multiregional trial with US population required', 'pai': False, 'safety': False},
    'OCA': {'reason': 'SAFETY_CONCERN', 'detail': 'DILI risk, higher deaths, ADCOM 12-4 against', 'pai': False, 'safety': True},
    'OCALIVA': {'reason': 'SAFETY_CONCERN', 'detail': 'DILI risk, higher deaths, ADCOM 12-4 against', 'pai': False, 'safety': True},
    'RUXOLITINIB': {'reason': 'CLINICAL_DATA', 'detail': 'Additional requirements beyond bioequivalence', 'pai': False, 'safety': False},
    'GEFAPIXANT': {'reason': 'CLINICAL_DATA', 'detail': 'Cough methodology issues, ADCOM 12-1 against', 'pai': False, 'safety': False},
    'LYFNUA': {'reason': 'CLINICAL_DATA', 'detail': 'Cough methodology issues, ADCOM 12-1 against', 'pai': False, 'safety': False},
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = data.get('result', '')
    if result != 'crl':
        continue

    reason = data.get('prior_crl_reason', {})
    if isinstance(reason, dict) and reason.get('status') == 'found':
        continue

    drug = data.get('drug_name', '').upper()
    ticker = data.get('ticker', '')

    matched = None
    for key, info in ADDITIONAL_CRL.items():
        if key in drug:
            matched = info
            break

    if matched:
        data['prior_crl_reason'] = {
            'status': 'found',
            'value': matched['detail'],
            'source': 'web_search',
            'category': matched['reason'],
            'confidence': 0.90,
            'tier': 2
        }
        data['pai_passed'] = {
            'status': 'found',
            'value': not matched['pai'],
            'source': 'derived_from_crl_reason',
            'confidence': 0.85,
            'tier': 2
        }
        data['safety_signal'] = {
            'status': 'found',
            'value': matched['safety'],
            'source': 'derived_from_crl_reason',
            'confidence': 0.85,
            'tier': 2
        }
        data['warning_letter'] = {
            'status': 'found',
            'value': False,
            'source': 'derived_from_crl_reason',
            'confidence': 0.75,
            'tier': 2
        }

        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f'{ticker}: {drug[:30]} -> {matched["reason"]} | Safety:{matched["safety"]}')
        updated += 1

print(f'\nUpdated: {updated}건')
