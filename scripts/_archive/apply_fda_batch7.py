"""FDA Designations 적용 - Batch 7"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Infectious Disease
    'PREVYMIS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LETERMOVIR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TEMBEXA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BRINCIDOFOVIR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ENFLONSIA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'CLESROVIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'MRESVIA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'DIFICID': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'FIDAXOMICIN': {'btd': False, 'ft': True, 'pr': False, 'od': False, 'aa': False},
    'XACDURO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SULBACTAM': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REZZAYO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REZAFUNGIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NUZOLVENCE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZOLIFLODACIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RECARBRIO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FETROJA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CEFIDEROCOL': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Liver/GI
    'TERLIVAZ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TERLIPRESSIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LIVMARLI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MARALIXIBAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BYLVAY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ODEVIXIBAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REZDIFFRA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'RESMETIROM': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VOQUEZNA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'VONOPRAZAN': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'XERMELO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TELOTRISTAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'XPHOZAH': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TENAPANOR': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'OMVOH': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'MIRIKIZUMAB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Endocrine/Metabolism
    'NGENLA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SOMATROGON': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SOGROYA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SOMAPACITAN': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SKYCLARYS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OMAVELOXOLONE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SKYSONA': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'NEXVIAZYME': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AVALGLUCOSIDASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # CNS/Neurology
    'DAYBUE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZTALMY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GANAXOLONE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FINTEPLA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FENFLURAMINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EPIDIOLEX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CANNABIDIOL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NUPLAZID': {'btd': True, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'PIMAVANSERIN': {'btd': True, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'IGALMI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'DEXMEDETOMIDINE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BXCL501': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'EXXUA': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'GEPIRONE': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PONVORY': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'PONESIMOD': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Hereditary Angioedema
    'EKTERLY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SEBETRALSTAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DAWNZERA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DONIDALORSEN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Cardiovascular
    'TRYNGOLZA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OLEZARSEN': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EPLONTERSEN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'WAINUA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CARDAMYST': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ETRIPAMIL': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
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

print(f'\nBatch 7 updated: {updated}')
