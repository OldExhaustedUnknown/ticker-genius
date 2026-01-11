"""NCT ID 누락 케이스 수정"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 추가 NCT ID 매핑
ADDITIONAL_NCT = {
    # Vonoprazen (오타) -> Vonoprazan과 동일
    'VONOPRAZEN': ['NCT02743949', 'NCT05195528', 'NCT04028466', 'NCT04124926', 'NCT04799158'],

    # 백신
    'PENBRAYA': ['NCT04440163', 'NCT05388162', 'NCT04502979'],  # Meningococcal ABCWY
    'IXCHIQ': ['NCT04546724', 'NCT04838444'],  # Chikungunya vaccine
    'VLA1553': ['NCT04546724', 'NCT04838444'],
    'SCI-B-VAC': ['NCT02137772', 'NCT04032080'],  # Hep B vaccine

    # 기타
    'NEFFY': ['NCT04280523', 'NCT04036552'],  # Epinephrine nasal
    'KHINDIVI': [],  # 505(b)(2) - no efficacy NCT needed
    'BYSANTI': [],  # Phase 3 not completed
    'MILSAPERIDONE': [],  # Phase 3 not completed
}

# NCT 불필요 카테고리
NCT_NOT_APPLICABLE = [
    'NITROGEN',
    'OXYGEN',
    'FLUORESCEIN',
    'BENOXINATE',
    'DEHYDRATED ALCOHOL',
    'MICROSTAT',
    'TAUVID',
    'SEMGLEE',  # Biosimilar
    'ERMEZA',   # 505(b)(2)
]

data_dir = Path('data/enriched')
updated = 0
na_count = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nct = data.get('nct_ids', [])
    if nct and len(nct) > 0:
        continue

    drug = data.get('drug_name', '').upper()
    modified = False

    # Check if NCT not applicable
    is_na = False
    for na_term in NCT_NOT_APPLICABLE:
        if na_term in drug:
            is_na = True
            break

    if is_na:
        data['nct_ids'] = []
        data['nct_status'] = 'not_applicable'
        print(f'[N/A] {data.get("ticker")}: {drug[:30]}')
        na_count += 1
        modified = True
    else:
        # Try to find matching NCT
        for key, ncts in ADDITIONAL_NCT.items():
            if key in drug:
                if ncts:
                    data['nct_ids'] = ncts
                    print(f'[NCT] {data.get("ticker")}: {drug[:30]} -> {len(ncts)} NCTs')
                else:
                    data['nct_ids'] = []
                    data['nct_status'] = 'not_found'
                    print(f'[NOT FOUND] {data.get("ticker")}: {drug[:30]}')
                modified = True
                break

    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        updated += 1

print(f'\n=== 결과 ===')
print(f'NCT 추가: {updated - na_count}건')
print(f'N/A 처리: {na_count}건')
print(f'총 수정: {updated}건')
