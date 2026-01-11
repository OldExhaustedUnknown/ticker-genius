"""FDA Designations 적용 - Batch 8"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Pain/Anesthesia
    'BARHEMSYS': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'AMISULPRIDE': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'BYFAVO': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'REMIMAZOLAM': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'ANJESO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'MELOXICAM': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ZIMHI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'NARCAN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TRUDHESA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Dermatology/Acne
    'AKLIEF': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TRIFAROTENE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'AMZEEQ': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SEYSARA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SARECYCLINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'WINLEVI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CLASCOTERONE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'EPSOLAY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'QBREXZA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'GLYCOPYRRONIUM': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BRYHALI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'DUOBRII': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ENSTILAR': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ZILXI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'MINOCYCLINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Eye drops/Simple products
    'OLEOGEL': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'XIPERE': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'TRIAMCINOLONE': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},

    # Medical gases
    'NITROGEN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'OXYGEN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Vaccines
    'HEPLISAV': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'AREXVY': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ABRYSVO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PENBRAYA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Biosimilars
    'TYRUKO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TOFIDENCE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'WEZLANA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CIMERLI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'VEGZELMA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TYENNE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'YUFLYMA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'HADLIMA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'HYRIMOZ': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CYLTEZO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'HULIO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'IDACIO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'REXTOVY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'UNLOXCYT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'COSIBELIMAB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'LOQTORZI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TORIPALIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Emergency/Critical Care
    'ANAPHYLM': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'EPINEPHRINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'LIBERVANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'DIAZEPAM': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Pediatric
    'PEDMARK': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SODIUM THIOSULFATE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ALKINDI': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Other
    'KIMMTRAK': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TEBENTAFUSP': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ANKTIVA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'N-803': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TAZVERIK': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TAZEMETOSTAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'BIZENGRI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ZENOCUTUZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

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

print(f'\nBatch 8 updated: {updated}')
