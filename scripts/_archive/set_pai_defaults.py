"""PAI/Warning Letter/Safety Signal 기본값 설정

대부분의 FDA 승인 약물은:
- PAI 통과 (제조시설 검사 통과)
- Warning Letter 없음
- 심각한 Safety Signal 없음

CRL인 경우에는 이유가 다양하므로 not_searched로 유지
"""
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

    result = data.get('result', '')
    modified = False

    # PAI passed
    pai = data.get('pai_passed')
    if isinstance(pai, dict) and pai.get('status') == 'not_searched':
        if result == 'approved':
            # Approved drugs passed PAI by definition
            data['pai_passed'] = {
                'status': 'found',
                'value': True,
                'source': 'derived_from_approval',
                'confidence': 0.95,
                'tier': 1,
                'note': 'Approved drugs must have passed PAI'
            }
            modified = True
        elif result == 'pending':
            # Pending - PAI status unknown
            data['pai_passed'] = {
                'status': 'not_searched',
                'value': None,
                'source': None,
                'confidence': 0.0,
                'tier': 0
            }
        elif result == 'crl':
            # CRL - could be PAI failure or other reasons
            data['pai_passed'] = {
                'status': 'not_searched',
                'value': None,
                'source': None,
                'confidence': 0.0,
                'tier': 0,
                'note': 'CRL may or may not be PAI related'
            }

    # Warning letter
    wl = data.get('warning_letter')
    if isinstance(wl, dict) and wl.get('status') == 'not_searched':
        if result == 'approved':
            # Most approved drugs don't have recent warning letters
            data['warning_letter'] = {
                'status': 'found',
                'value': False,
                'source': 'default_for_approved',
                'confidence': 0.85,
                'tier': 2,
                'note': 'No known warning letters at approval time'
            }
            modified = True
        else:
            data['warning_letter'] = {
                'status': 'not_searched',
                'value': None,
                'source': None,
                'confidence': 0.0,
                'tier': 0
            }

    # Safety signal
    ss = data.get('safety_signal')
    if isinstance(ss, dict) and ss.get('status') == 'not_searched':
        if result == 'approved':
            # Approved drugs don't have blocking safety signals
            data['safety_signal'] = {
                'status': 'found',
                'value': False,
                'source': 'default_for_approved',
                'confidence': 0.90,
                'tier': 1,
                'note': 'No blocking safety signals at approval'
            }
            modified = True
        elif result == 'crl':
            # CRL might have safety issues
            data['safety_signal'] = {
                'status': 'not_searched',
                'value': None,
                'source': None,
                'confidence': 0.0,
                'tier': 0
            }
        else:
            data['safety_signal'] = {
                'status': 'not_searched',
                'value': None,
                'source': None,
                'confidence': 0.0,
                'tier': 0
            }

    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        updated += 1
    else:
        skipped += 1

print(f'PAI/Warning/Safety 기본값 설정 완료')
print(f'Updated: {updated}')
print(f'Skipped: {skipped}')
