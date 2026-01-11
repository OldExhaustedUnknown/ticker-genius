"""FDA Designations 적용 - Batch 6"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Oncology - small molecule
    'LUMAKRAS': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'SOTORASIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'KRAZATI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'ADAGRASIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'RETEVMO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'SELPERCATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'GAVRETO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'PRALSETINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TABRECTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'CAPMATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'EXKIVITY': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'MOBOCERTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'TEPMETKO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TEPOTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'PEMAZYRE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'PEMIGATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TRUSELTIQ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'INFIGRATINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TIBSOVO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IVOSIDENIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'REZLIDHIA': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OLUTASIDENIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FOTIVDA': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'TIVOZANIB': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'WELIREG': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'BELZUTIFAN': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'VORANIGO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VORASIDENIB': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Oncology - ADC
    'ELAHERE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'MIRVETUXIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'ZYNLONTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'LONCASTUXIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TIVDAK': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TISOTUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # Oncology - bispecifics
    'TALVEY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TALQUETAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TECVAYLI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TECLISTAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'LUNSUMIO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'MOSUNETUZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'COLUMVI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'GLOFITAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'EPKINLY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'EPCORITAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ELREXFIO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'ELRANATAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # Oncology - other
    'OJEMDA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TOVORAFENIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AUGTYRO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'REPOTRECTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'JAYPIRCA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'PIRTOBRUTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'OGSIVEO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NIROGACESTAT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ORSERDU': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ELACESTRANT': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Immunology/Inflammation
    'VYVGART': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EFGARTIGIMOD': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RYSTIGGO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ROZANOLIXIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'UPLIZNA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'INEBILIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ENSPRYNG': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SATRALIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'JOENJA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LENIOLISIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Respiratory
    'OHTUVAYRE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ENSIFENTRINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'LYFNUA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'GEFAPIXANT': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TEZSPIRE': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TEZEPELUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BRINSUPRI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BRENSOCATIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
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

print(f'\nBatch 6 updated: {updated}')
