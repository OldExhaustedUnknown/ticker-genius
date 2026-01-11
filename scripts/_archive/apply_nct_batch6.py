"""NCT ID 최종 배치 적용"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

nct_map = {
    # Remaining specific drugs
    'AVT05': ['NCT02260791'],  # golimumab biosimilar
    'CREXONT': ['NCT03670953'],
    'BONCRESA': ['NCT03989349'],  # denosumab biosimilar
    'BREKIYA': ['NCT03557060'],
    'PYRIDOSTIGMINE': ['NCT00727025'],
    'OZILTUS': ['NCT02891824'],  # denosumab biosimilar
    'TADALAFIL': ['NCT00781716'],
    'PANTOPRAZOLE': ['NCT00132379'],
    'ATROPINE': ['NCT01438346'],
    'SYMBICORT': ['NCT00206154'],
    'CABTREO': ['NCT03564119'],

    # More oncology
    'OPDIVO': ['NCT02066636'],
    'BLINCYTO': ['NCT02013167'],
    'CYRAMZA': ['NCT01170663'],
    'ramucirumab': ['NCT01170663'],
    'PEMETREXED': ['NCT00102804'],
    'ROMIDEPSIN': ['NCT00426764'],
    'CABAZITAXEL': ['NCT00417079'],
    'MICAFUNGIN': ['NCT00106119'],

    # Rare disease
    'UX111': ['NCT02716246'],
    'ABO-102': ['NCT02716246'],
    'marnetegragene': ['NCT03825783'],
    'CYCLOPHOSPHAMIDE': ['NCT00000597'],

    # Cardiovascular
    'CAPVAXIVE': ['NCT03950622'],
    'V116': ['NCT03950622'],
    'Patritumab': ['NCT03260491'],

    # Medical gases - no clinical trials typically

    # Dermatology remaining
    'DFD-29': ['NCT03160339'],
    'minocycline': ['NCT03160339'],

    # Ophthalmology
    'TP-03': ['NCT03568331'],
    'lotilaner': ['NCT03568331'],

    # Other
    'GALLIUM': ['NCT02678351'],
    'GOZETOTIDE': ['NCT02678351'],
    'OLT-CART': ['NCT03682068'],
    'Oxylanthanum': ['NCT02634411'],
    'XYOSTED': ['NCT02159469'],
    'HTX-019': ['NCT02562365'],
    'Humacyte': ['NCT01872208'],
    'OCA': ['NCT02548351'],
    'Ocaliva': ['NCT02548351'],
    'Tonmya': ['NCT00581230'],
    'cyclobenzaprine': ['NCT00581230'],

    # Biosimilars additional
    'TYENNE': ['NCT03052621'],
    'VEGZELMA': ['NCT02364999'],
    'CIMERLI': ['NCT02842190'],
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if len(data.get('nct_ids', [])) > 0:
        continue

    drug = data.get('drug_name', '').upper()
    matched_ncts = []

    for key, ncts in nct_map.items():
        if key.upper() in drug:
            matched_ncts = ncts
            break

    if matched_ncts:
        data['nct_ids'] = matched_ncts
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'{data.get("ticker")}: {matched_ncts}')
        updated += 1

print(f'\nTotal updated: {updated}')
