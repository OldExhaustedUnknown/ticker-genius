"""FDA Designations 적용 - Batch 17"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # More Oncology
    'SAREPTAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'POSEIDA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'KITE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TAFINLAR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'DABRAFENIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'MEKINIST': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TRAMETINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'BRAFTOVI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ENCORAFENIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'MEKTOVI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'BINIMETINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'COTELLIC': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'COBIMETINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZELBORAF': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VEMURAFENIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TAGRISSO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'OSIMERTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'LORBRENA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'LORLATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ALECENSA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ALECTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'XALKORI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'CRIZOTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ZYKADIA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'CERITINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'BRIGATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ALUNBRIG': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # Misc
    'YEZTUGO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'LANTIDRA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DONISLECEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SOTATERCEPT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'WINREVAIR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EFLORNITHINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DIFLUOROMETHYLORNITHINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AGTORIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IVOSIDENIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TIBSOVO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ENASIDENIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IDHIFA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GLASDEGIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DAURISMO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MIDOSTAURIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RYDAPT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'QUIZARTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VANFLYTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
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

print(f'\nBatch 17 updated: {updated}')
