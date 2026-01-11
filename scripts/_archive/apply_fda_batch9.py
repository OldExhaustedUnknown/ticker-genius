"""FDA Designations 적용 - Batch 9"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Additional Oncology
    'FRUZAQLA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'FRUQUINTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'ZEJULA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NIRAPARIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TALZENNA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TALAZOPARIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ZYNYZ': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RETIFANLIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PHELINUN': {'btd': False, 'ft': False, 'pr': False, 'od': True, 'aa': False},
    'KOMZIFTI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ZIFTOMENIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ZIIHERA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ZANIDATAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'AUCATZYL': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},
    'OBE-CEL': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},
    'OBECABTAGENE': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},

    # Rare Disease Additional
    'MEPSEVII': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VESTRONIDASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LAMZEDE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VELMANASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BRINEURA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CERLIPONASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VOXZOGO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VOSORITIDE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FYARRO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NIKTIMVO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AXATILIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Alopecia
    'LITFULO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RITLECITINIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'LETRFYL': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RUXOLITINIB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Myelofibrosis
    'OJJAARA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MOMELOTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FEDRATINIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'INREBIC': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Anti-infective additional
    'BREXAFEMME': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IBREXAFUNGERP': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GEPOTIDACIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BLUJEPA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ORLYNVAH': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SULOPENEM': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Bone/Mobility
    'APHEXDA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MOTIXAFORTIDE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RYZNEUTA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'EFBEMALENOGRASTIM': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'LETYBO': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'LETIBOTULINUMTOXIN': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Other
    'VIZZ': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ACECLIDINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'IMAAVY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'KISUNLA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'DONANEMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'UZEDY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'RISPERIDONE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
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

print(f'\nBatch 9 updated: {updated}')
