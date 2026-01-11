"""FDA Designations 적용 - Batch 14"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Cardiovascular
    'NEXLETOL': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'NEXLIZET': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'BEMPEDOIC': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'BIVALIRUDIN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'KANGIO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Epilepsy
    'ZONISAMIDE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TOPIRAMATE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Contraception/Women
    'PHEXXI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # GI
    'GIMOTI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'METOCLOPRAMIDE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Oncology
    'PEMFEXY': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'PEMETREXED': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Ophthalmology
    'MYDCOMBI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'MICROSTAT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TRAVOPROST': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'IDOSE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'CLOBETASOL': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Rare Disease
    'CUTX-101': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'COPPER HISTIDINATE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AT-GAA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CIPAGLUCOSIDASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'POMBILITI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RYTELO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IMETELSTAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GRN163L': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Liver
    'LIVDELZI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SELADELPAR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Imaging
    'CERIANNA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'FLUOROESTRADIOL': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Autoimmune
    'FILGOTINIB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'JYSELECA': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Antiviral
    'VEKLURY': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'REMDESIVIR': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Steroid
    'HYDROCORTISONE': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'KHINDIVI': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ALCOHOL INJECTION': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'DEHYDRATED ALCOHOL': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # More drugs
    'FABHALTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IPTACOPAN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BRIUMVI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'UBLITUXIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SUSVIMO': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RANIBIZUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VABYSMO': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'FARICIMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BEOVU': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BROLUCIZUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
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

print(f'\nBatch 14 updated: {updated}')
