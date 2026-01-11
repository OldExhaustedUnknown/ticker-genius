"""FDA Designations 적용 - Batch 15"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Oncology
    'PEPAXTO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'MELFLUFEN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'RYBREVANT': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'AMIVANTAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'IMDELLTRA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TARLATAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TUKYSA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'TUCATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'COSELA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TRILACICLIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NUVALENT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ZIDESAMTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'NVL-520': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # Immunology
    'OMALIZUMAB': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'XOLAIR': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'NUCALA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MEPOLIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FASENRA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BENRALIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DUPIXENT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DUPILUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ILARIS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CANAKINUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ARCALYST': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RILONACEPT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'KINERET': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ANAKINRA': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},

    # Neurology
    'OCREVUS': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'OCRELIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'KESIMPTA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'OFATUMUMAB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'MAYZENT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SIPONIMOD': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'ZEPOSIA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'OZANIMOD': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'GILENYA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'FINGOLIMOD': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TYSABRI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'NATALIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Gene Therapy
    'RP1': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VUSOLIMOGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ORUDOJENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Biosimilars
    'HUMIRA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ADALIMUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'AVASTIN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BEVACIZUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'HERCEPTIN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TRASTUZUMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'RITUXAN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'RITUXIMAB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
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

print(f'\nBatch 15 updated: {updated}')
