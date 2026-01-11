"""FDA Designations 적용 - Batch 13"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Antibiotics/Anti-infective
    'RECARBRIO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IMIPENEM': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RELEBACTAM': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CONTEMPO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NUZYRA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OMADACYCLINE': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'XERAVA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ERAVACYCLINE': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ARIKAYCE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AMIKACIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZEMDRI': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PLAZOMICIN': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # HIV/Antiviral
    'CABENUVA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'CABOTEGRAVIR': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'APRETUDE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'SUNLENCA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'LENACAPAVIR': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BIKTARVY': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'DOVATO': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TRIUMEQ': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TROGARZO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IBALIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RUKOBIA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FOSTEMSAVIR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Diabetes/Obesity
    'MOUNJARO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TIRZEPATIDE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ZEPBOUND': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'WEGOVY': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SEMAGLUTIDE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'OZEMPIC': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'RYBELSUS': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TZIELD': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TEPLIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Osteoporosis/Bone
    'EVENITY': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ROMOSOZUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TYMLOS': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ABALOPARATIDE': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PROLIA': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'DENOSUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'XGEVA': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Muscle
    'RYANODEX': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'DANTROLENE': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},

    # Sleep
    'QUVIVIQ': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'DARIDOREXANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BELSOMRA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SUVOREXANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'DAYVIGO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'LEMBOREXANT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Psychiatry
    'REXULTI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BREXPIPRAZOLE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'VRAYLAR': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CARIPRAZINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'LYBALVI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ABILIFY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ARIPIPRAZOLE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'COBENFY': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'XANOMELINE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
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

print(f'\nBatch 13 updated: {updated}')
