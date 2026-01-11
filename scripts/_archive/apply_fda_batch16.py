"""FDA Designations 적용 - Batch 16"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Cell Therapy
    'OMIDUBICEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NICORD': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OMISIRGE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RYONCIL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REMESTEMCEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'HUMACYTE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Liver Disease
    'ELAFIBRANOR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OCALIVA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OBETICHOLIC': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OCA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LINERIXIBAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Oncology
    'AVASOPASEM': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZEPZELCA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'LURBINECTEDIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'SURUFATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EXDENSUR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Respiratory
    'DEPEMOKIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'YUTREPIA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TREPROSTINIL': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Vaccine
    'PENMENVY': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # HIV
    'VOCABRIA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TIVICAY': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'DOLUTEGRAVIR': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Pain
    'ZYNRELEF': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'HTX-011': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'HTX-019': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'APREPITANT': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},

    # Gout
    'KRYSTEXXA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PEGLOTICASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Ophthalmology
    'AVACINCAPTAD': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Dermatology
    'OPZELURA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NEXOBRID': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ANACAULASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # GI
    'LINZESS': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'LINACLOTIDE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SER-109': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VOWST': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Diabetes
    'LYUMJEV': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TLANDO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SOTAGLIFLOZIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'INPEFA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Wound
    'EPIOXA': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'EPI-ON': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_fda = data.get('fda_designations', {})
    if existing_fda:
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

print(f'\nBatch 16 updated: {updated}')
