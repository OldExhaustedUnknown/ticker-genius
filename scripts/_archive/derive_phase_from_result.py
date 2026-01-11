"""Phase 필드 자동 파생 - result 필드 기반"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Result -> Phase 매핑
RESULT_TO_PHASE = {
    'approved': 'Approved',
    'crl': 'Phase 3',  # CRL은 대부분 Phase 3 완료 후 발생
    'pending': 'Phase 3',  # Pending PDUFA는 Phase 3 완료 상태
    'withdrawn': 'Withdrawn',
}

data_dir = Path('data/enriched')
updated = 0
skipped = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if already has Phase
    phase = data.get('phase')
    has_phase = False
    if isinstance(phase, dict) and phase.get('value'):
        has_phase = True
    elif phase and not isinstance(phase, dict):
        has_phase = True

    if has_phase:
        skipped += 1
        continue

    # Derive Phase from result
    result = data.get('result', '').lower()
    derived_phase = RESULT_TO_PHASE.get(result)

    if derived_phase:
        data['phase'] = {
            'status': 'found',
            'value': derived_phase,
            'source': 'derived_from_result',
            'confidence': 0.95,
            'tier': 1,
            'searched_sources': ['result_field'],
            'last_searched': None,
            'error': None
        }
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'{data.get("ticker")}: {data.get("drug_name", "")[:30]} -> {derived_phase}')
        updated += 1
    else:
        print(f'[SKIP] {data.get("ticker")}: result={result}')

print(f'\nPhase 자동 파생 완료')
print(f'Updated: {updated}')
print(f'Already had phase: {skipped}')
