"""FDA Designations 적용 - Batch 18 (Final)"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fda_data = {
    # Gene/Cell Therapy
    'LENMELDY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ATIDARSAGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OTL-200': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BEQVEZ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'FIDANACOGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PAPZIMEOS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZOPAPOGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ETRANACOGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AMT-061': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'UX111': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ABO-102': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RGX-121': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MARNETEGRAGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Rare Disease
    'PEGUNIGALSIDASE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ELFABRIO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PRX-102': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VATIQUINONE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PTC743': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MIPLYFFA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ARIMOCLOMOL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'XOLREMDI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MAVORIXAFOR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Oncology
    'PLUVICTO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LUTETIUM': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VIJOICE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ALPELISIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SCEMBLIX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ASCIMINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RHAPSIDO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'REVUFORJ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'REVUMENIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'IBTROZI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TALETRECTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'POZIOTINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'GOMEKLI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MIRDAMETINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DANYELZA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'NAXITAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'OMBURTAMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'AVMAPKI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'FAKZYNJA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'AVUTOMETINIB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'PATRITUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'HER3-DXD': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # Immunology
    'COSENTYX': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'SECUKINUMAB': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'ENTYVIO': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VEDOLIZUMAB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'XELJANZ': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TOFACITINIB': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Hematology
    'ALHEMO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CONCIZUMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'HYMPAVZI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MARSTACIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EFANESOCTOCOG': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VANRAFIA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SPARSENTAN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'FILSPARI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},

    # Respiratory
    'TYVASO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Cystic Fibrosis
    'TRIKAFTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'KALYDECO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IVACAFTOR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ALYFTREK': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VANZACAFTOR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EXAGAMGLOGENE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EXA-CEL': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Pain
    'JOURNAVX': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'SUZETRIGINE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VX-548': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'OLINVYK': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'OLICERIDINE': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Endocrine
    'RECORLEV': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LEVOKETOCONAZOLE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DASIGLUCAGON': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZEGALOGUE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CRENESSITY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CRINECERFONT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Ophthalmology
    'DEXTENZA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'OC-01': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'VARENICLINE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TYRVAYA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TP-03': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'LOTILANER': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'UPNEEQ': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'NARSOPLIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'YARTEMLEA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Vaccine
    'CAPVAXIVE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'V116': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'MNEXSPIKE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'MRNA-1283': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'NOVAVAX': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PREVNAR': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'SCI-B-VAC': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'IXCHIQ': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'VLA1553': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'PAXLOVID': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'NIRMATRELVIR': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'NIRSEVIMAB': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'BEYFORTUS': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Infectious Disease
    'FEXINIDAZOLE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TEBIPENEM': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CONTEPO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},

    # Psychiatry
    'ROLUPERIDONE': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'TRADIPITANT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'HETLIOZ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TASIMELTEON': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MILSAPERIDONE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BYSANTI': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'QELBREE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'VILOXAZINE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'FANAPT': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'ILOPERIDONE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},

    # Dermatology
    'BERDAZIMER': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'VP-102': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'YCANTH': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'DAXIBOTULINUM': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'DAXXIFY': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # GI
    'VICINEUM': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DCCR': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DIAZOXIDE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'VELIGROTUG': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZUSDURI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MITOMYCIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'JELMYTO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BIJUVA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'GOZETOTIDE': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'GALLIUM': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Anesthesia
    'EXPAREL': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'NEFFY': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},

    # Oncology chemo
    'ROMIDEPSIN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ISTODAX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'MICAFUNGIN': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'CABAZITAXEL': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'JEVTANA': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},

    # Biosimilar/Other
    'SEMGLEE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'NYVEPRIA': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'FAMOTIDINE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'MOMETASONE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'XHANCE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'FLUTICASONE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'TAUVID': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'FLORTAUCIPIR': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'TRIFERIC': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'CTEXLI': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'CHENODIOL': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ELYXYB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'CELECOXIB': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'FUROSCIX': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'FUROSEMIDE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'WYOST': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'ENZEEVU': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ONAPGO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'APOMORPHINE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SPN-830': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'APITEGROMAB': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SRK-015': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'STS101': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'ATZUMI': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'ROLONTIS': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'EFLAPEGRASTIM': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'VYONDYS': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'GOLODIRSEN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'CYCLOPHOSPHAMIDE': {'btd': False, 'ft': False, 'pr': False, 'od': False, 'aa': False},
    'BARDOXOLONE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OXYLANTHANUM': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'TESAMORELIN': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'EGRIFTA': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'VEVERIMER': {'btd': False, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'ERMEZA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
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

print(f'\nBatch 18 updated: {updated}')
