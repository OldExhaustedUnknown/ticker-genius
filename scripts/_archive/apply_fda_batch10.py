"""FDA Designations 적용 - Batch 10"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Gene Therapy
    'BETI-CEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LOVOTIBEGLOGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LOVO-CEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TABELECLEUCEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Rare Disease
    'PROCYSBI': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'CYSTEAMINE': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ORLADEYO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BEROTRALSTAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TASCENSO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'YORVIPATH': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TRANSCON PTH': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TRANSCON HGH': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'NAVEPEGRITIDE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TRANSCON CNP': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Alzheimer
    'LECANEMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'ADUCANUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'ADUHELM': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},

    # Depression/Anxiety
    'ZURANOLONE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BIIB125': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TRORILUZOLE': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VYGLXIA': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'AMX0035': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RELYVRIO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Oncology
    'TEVIMBRA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TISLELIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'KRESLADI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ODRONEXTAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ORAL PACLITAXEL': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Cardiovascular
    'ACORAMIDIS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ATTRUBY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PLOZASIRAN': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REDEMPLO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Respiratory
    'AIRSUPRA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SYMBICORT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'BREZTRI': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # GI
    'PANTOPRAZOLE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'GOVORESTAT': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MIEBO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Neuromuscular
    'PYRIDOSTIGMINE': {'btd': False, 'ft': False, 'pr': False, 'od': True, 'aa': False},

    # Dermatology
    'AMELUZ': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CABTREO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Ophthalmology
    'ATROPINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'FLUORESCEIN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BENOXINATE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Pain
    'QDOLO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TRAMADOL': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'AXS-07': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'SYMBRAVO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Other
    'AVANCE NERVE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TADALAFIL': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ZUNVEYL': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'EMRELIS': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'EMBLAVEO': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
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

print(f'\nBatch 10 updated: {updated}')
