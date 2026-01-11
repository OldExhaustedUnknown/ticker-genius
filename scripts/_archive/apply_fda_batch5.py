"""FDA Designations 적용 - Batch 5"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Neurology/Psychiatry
    'VUITY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'WAKIX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'XYWAV': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'CAPLYTA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'INGREZZA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'AUSTEDO': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},

    # Rare Disease
    'MITAPIVAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PYRUKYND': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DAYBUE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TROFINETIDE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OLPRUVA': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ACER-001': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'EVRYSDI': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OXLUMO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GIVLAARI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GALAFOLD': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'IMCIVREE': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'PALYNZIQ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Ophthalmology
    'REPROXALAP': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'ADX-2191': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SYFOVRE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'IZERVAY': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'XDEMVY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'EYLEA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'EYSUVIS': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'PEGCETACOPLAN': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Cardiovascular
    'REPATHA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PRALUENT': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'LEQVIO': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ENTRESTO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'CAMZYOS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VADADUSTAT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'VAFSEO': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'JESDUVROQ': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'DAPRODUSTAT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'ROXADUSTAT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Biosimilars (typically no special designations)
    'RIABNI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'AVT05': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'OZILTUS': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BONCRESA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BREKIYA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Dermatology
    'ROFLUMILAST': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ZORYVE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ARQ-151': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ARQ-154': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'VTAMA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TAPINAROF': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Parkinsons
    'ONGENTYS': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CREXONT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Womens Health
    'ORIAHNN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TWIRLA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'MYFEMBREE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'VEOZAH': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Hematology
    'FITUSIRAN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'QFITLIA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REBLOZYL': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EMPAVELI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Gene/Cell Therapy
    'AFAMI-CEL': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},
    'ZEVASKYN': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'AMTAGVI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'LIFILEUCEL': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Skip if already has FDA designations with any True values
    existing_fda = data.get('fda_designations', {})
    if existing_fda and any(v == True for v in existing_fda.values()):
        continue

    drug = data.get('drug_name', '').upper()
    matched = None

    for key, desig in fda_data.items():
        if key.upper() in drug:
            matched = desig
            break

    if matched:
        data['fda_designations'] = {
            'breakthrough_therapy': matched['btd'],
            'fast_track': matched['ft'],
            'priority_review': matched['pr'],
            'orphan_drug': matched['od'],
            'accelerated_approval': matched['aa'],
        }
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'{data.get("ticker")}: {drug[:30]}')
        updated += 1

print(f'\nBatch 5 updated: {updated}')
