"""FDA Designations 적용 - Batch 11"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Oncology/Hematology
    'SARCLISA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ISATUXIMAB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MONJUVI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TAFASITAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'XOSPATA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GILTERITINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VENCLEXTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'VENETOCLAX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'IBRANCE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'PALBOCICLIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'KISQALI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RIBOCICLIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VERZENIO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ABEMACICLIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RUBRACA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'RUCAPARIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'LYNPARZA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'OLAPARIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'CALQUENCE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ACALABRUTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'IMBRUVICA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'IBRUTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'BRUKINSA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZANUBRUTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Autoimmune/Inflammatory
    'SKYRIZI': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'RISANKIZUMAB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TREMFYA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'GUSELKUMAB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'RINVOQ': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'UPADACITINIB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SOTYKTU': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'DEUCRAVACITINIB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'CIBINQO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ABROCITINIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'OLUMIANT': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'BARICITINIB': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'SAPHNELO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ANIFROLUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BENLYSTA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BELIMUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Cardiology
    'VERQUVO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VERICIGUAT': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'FARXIGA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'DAPAGLIFLOZIN': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'JARDIANCE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'EMPAGLIFLOZIN': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Migraine
    'UBRELVY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'UBROGEPANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'NURTEC': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'RIMEGEPANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'QULIPTA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ATOGEPANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'VYEPTI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'EPTINEZUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'AIMOVIG': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ERENUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'AJOVY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'FREMANEZUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'EMGALITY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'GALCANEZUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
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

print(f'\nBatch 11 updated: {updated}')
