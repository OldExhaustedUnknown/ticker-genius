"""FDA Designations 적용 - Batch 12"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # AML/MDS
    'ONUREG': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AZACITIDINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PACRITINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'VONJO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'LYMPHIR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DENILEUKIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'I/ONTAK': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'E7777': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Anticoagulant
    'ELIQUIS': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'APIXABAN': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # GIST/Mastocytosis
    'AVAPRITINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'AYVAKIT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'QINLOCK': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RIPRETINIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Cell Therapy
    'DERAMIOCEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CAP-1002': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AVACOPAN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TAVNEOS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # IgA Nephropathy
    'NEFECON': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TARPEYO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # HAE/Rare
    'AURLUMYN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FIRDAPSE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AMIFAMPRIDINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VAMOROLONE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AGAMREE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DEFENCATH': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TAUROLIDINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Chemo Protectant
    'PLINABULIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Biosimilar/Follow-on
    'UDENYCA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'PEGFILGRASTIM': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CHS-201': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CHS-1420': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Endocrine
    'PALSONIFY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PALTUSOTINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RELACORILANT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MODEYSO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DORDAVIPRONE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Cardio
    'OMECAMTIV': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'MECARBIL': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Dermatology
    'QWO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'COLLAGENASE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'XACIATO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'DARE-BV1': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'MYQORZO': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Liver
    'HEPZATO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MELPHALAN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Enzyme replacement
    'TIVIDENOFUSP': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DNL310': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Anthrax vaccine
    'CYFENDUS': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'AV7909': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Critical Care
    'VASOPRESSIN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
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

print(f'\nBatch 12 updated: {updated}')
