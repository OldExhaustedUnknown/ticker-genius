"""MOA (Mechanism of Action) 적용 - Batch 10 (Final)"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # Remaining oncology
    'PACLITAXEL': 'Microtubule inhibitor',
    'CABAZITAXEL': 'Microtubule inhibitor',
    'PEMETREXED': 'Antifolate',
    'ROMIDEPSIN': 'HDAC inhibitor',
    'MICAFUNGIN': 'Echinocandin antifungal',
    'CYCLOPHOSPHAMIDE': 'Alkylating agent',
    'MITOMYCIN': 'Alkylating agent',
    'JELMYTO': 'Alkylating agent',
    'ZUSDURI': 'Alkylating agent',
    'PLINABULIN': 'Tubulin inhibitor',
    'ONUREG': 'DNA methyltransferase inhibitor',
    'AZACITIDINE': 'DNA methyltransferase inhibitor',
    'AYVAKIT': 'KIT/PDGFRA inhibitor',
    'AVAPRITINIB': 'KIT/PDGFRA inhibitor',
    'QINLOCK': 'Kinase inhibitor',
    'RIPRETINIB': 'Kinase inhibitor',
    'EXKIVITY': 'EGFR exon 20 inhibitor',
    'MOBOCERTINIB': 'EGFR exon 20 inhibitor',
    'POZIOTINIB': 'HER2/EGFR inhibitor',
    'OJEMDA': 'RAF inhibitor',
    'TOVORAFENIB': 'RAF inhibitor',
    'BIZENGRI': 'HER2/HER3 bispecific',
    'ZENOCUTUZUMAB': 'HER2/HER3 bispecific',
    'MARGENZA': 'HER2 inhibitor',
    'MARGETUXIMAB': 'HER2 inhibitor',
    'PATRITUMAB': 'HER3-targeted ADC',
    'HER3-DXD': 'HER3-targeted ADC',
    'SARCLISA': 'CD38 inhibitor',
    'ISATUXIMAB': 'CD38 inhibitor',
    'DARZALEX': 'CD38 inhibitor',
    'DARATUMUMAB': 'CD38 inhibitor',
    'LYMPHIR': 'IL-2 receptor targeted toxin',
    'DENILEUKIN': 'IL-2 receptor targeted toxin',
    'VICINEUM': 'EpCAM-targeted immunotoxin',
    'HEPZATO': 'Liver-directed therapy',

    # Rare disease
    'ACORAMIDIS': 'TTR stabilizer',
    'TAFAMIDIS': 'TTR stabilizer',
    'VYNDAQEL': 'TTR stabilizer',
    'VYNDAMAX': 'TTR stabilizer',
    'TIVIDENOFUSP': 'Enzyme transport',
    'DNL310': 'Enzyme transport',
    'AT-GAA': 'Enzyme replacement therapy',
    'CIPAGLUCOSIDASE': 'Enzyme replacement therapy',
    'VATIQUINONE': 'NQO1 substrate',
    'PTC743': 'NQO1 substrate',
    'BEREMAGENE': 'Gene therapy (topical)',
    'VYJUVEK': 'Gene therapy (topical)',
    'B-VEC': 'Gene therapy (topical)',
    'CUTX-101': 'Copper histidinate',
    'BARDOXOLONE': 'Nrf2 activator',
    'NEFECON': 'Budesonide',
    'TARPEYO': 'Budesonide',
    'SPARSENTAN': 'AT1R antagonist/ETA antagonist',
    'FILSPARI': 'AT1R antagonist/ETA antagonist',
    'DCCR': 'KATP channel opener',
    'DIAZOXIDE': 'KATP channel opener',
    'VEVERIMER': 'Acid binder',
    'OXYLANTHANUM': 'Phosphate binder',
    'LOVO-CEL': 'Gene therapy (autologous)',
    'LYFGENIA': 'Gene therapy (autologous)',

    # CNS
    'TRAMADOL': 'Opioid agonist',
    'QDOLO': 'Opioid agonist',
    'LUMRYZ': 'GHB receptor agonist',
    'FT218': 'GHB receptor agonist',
    'ZONISAMIDE': 'Sodium channel blocker',
    'TOPIRAMATE': 'Sodium channel blocker',
    'QALSODY': 'ASO (SOD1)',
    'TOFERSEN': 'ASO (SOD1)',
    'ROLUPERIDONE': '5-HT2A/sigma-2 antagonist',
    'TRADIPITANT': 'NK1 receptor antagonist',
    'MILSAPERIDONE': 'D2/5-HT2A antagonist',
    'BYSANTI': 'D2/5-HT2A antagonist',
    'FANAPT': 'D2/5-HT2A antagonist',
    'ILOPERIDONE': 'D2/5-HT2A antagonist',
    'TONMYA': 'Muscle relaxant',
    'CYCLOBENZAPRINE': 'Muscle relaxant',
    'ATZUMI': 'Triptan',
    'STS101': 'Triptan',

    # Cardio
    'ETRIPAMIL': 'Calcium channel blocker',
    'CARDAMYST': 'Calcium channel blocker',
    'BIVALIRUDIN': 'Direct thrombin inhibitor',
    'KANGIO': 'Direct thrombin inhibitor',
    'VASOPRESSIN': 'V1 receptor agonist',
    'RYANODEX': 'Ryanodine receptor antagonist',
    'DANTROLENE': 'Ryanodine receptor antagonist',
    'TEPEZZA': 'IGF-1R inhibitor',
    'TEPROTUMUMAB': 'IGF-1R inhibitor',

    # Ophthalmology
    'ACECLIDINE': 'Muscarinic agonist',
    'VIZZ': 'Muscarinic agonist',
    'EPIOXA': 'Corneal crosslinking',
    'EPI-ON': 'Corneal crosslinking',
    'ATROPINE': 'Muscarinic antagonist',
    'CLOBETASOL': 'Corticosteroid',
    'MYDCOMBI': 'Mydriatic combination',
    'MICROSTAT': 'Mydriatic combination',
    'FLUORESCEIN': 'Diagnostic agent',
    'BENOXINATE': 'Local anesthetic',
    'NARSOPLIMAB': 'MASP-2 inhibitor',
    'YARTEMLEA': 'MASP-2 inhibitor',

    # GI/Other
    'PANTOPRAZOLE': 'Proton pump inhibitor',
    'GIMOTI': 'Dopamine antagonist',
    'METOCLOPRAMIDE': 'Dopamine antagonist',
    'ELAFIBRANOR': 'PPARα/δ agonist',
    'DEFENCATH': 'Catheter lock solution',
    'TAUROLIDINE': 'Catheter lock solution',
    'NEXOBRID': 'Enzymatic debridement',
    'HUMACYTE': 'Bioengineered blood vessel',
    'AVANCE': 'Nerve allograft',
    'PALSONIFY': 'Somatostatin receptor agonist',
    'PALTUSOTINE': 'Somatostatin receptor agonist',
    'LYUMJEV': 'Rapid-acting insulin',
    'TLANDO': 'Testosterone',
    'TESTOSTERONE': 'Androgen',
    'TESAMORELIN': 'GHRH analogue',
    'EGRIFTA': 'GHRH analogue',
    'FEXINIDAZOLE': 'Antiprotozoal',
    'CHENODIOL': 'Bile acid',
    'CTEXLI': 'Bile acid',
    'FUROSEMIDE': 'Loop diuretic',
    'FUROSCIX': 'Loop diuretic',
    'FAMOTIDINE': 'H2 receptor antagonist',
    'ELYXYB': 'COX-2 inhibitor',
    'CELECOXIB': 'COX-2 inhibitor',
    'WYOST': 'Osteoporosis treatment',
    'ENZEEVU': 'Ophthalmology',
    'FILGOTINIB': 'JAK1 inhibitor',
    'JYSELECA': 'JAK1 inhibitor',
    'YEZTUGO': 'Capsid inhibitor',
    'ERMEZA': 'Antifungal',
    'ROLONTIS': 'G-CSF',
    'EFLAPEGRASTIM': 'G-CSF',
    'AMELUZ': 'Photodynamic therapy',
    'VELIGROTUG': 'Gene therapy',
    'IMAAVY': 'Antibody',
    'CABTREO': 'Combination product',
    'TASCENSO': 'Topiramate',
    'XHANCE': 'Corticosteroid',
    'FLUTICASONE': 'Corticosteroid',
    'MOMETASONE': 'Corticosteroid',
    'TRIUMEQ': 'Antiretroviral',
    'TIVICAY': 'Integrase inhibitor',
    'DOLUTEGRAVIR': 'Integrase inhibitor',
    'DEHYDRATED ALCOHOL': 'Ablation agent',
    'ALCOHOL INJECTION': 'Ablation agent',
    'TRIFERIC': 'Iron replacement',
    'FERRIC PYROPHOSPHATE': 'Iron replacement',
    'CYFENDUS': 'Anthrax vaccine',
    'AV7909': 'Anthrax vaccine',
    'PEMFEXY': 'Antifolate (generic)',
    'AURLUMYN': 'Neurological',
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_moa = data.get('mechanism_of_action', '')
    if existing_moa and existing_moa.strip():
        continue

    drug = data.get('drug_name', '').upper()
    matched_moa = None

    for key, moa in moa_data.items():
        if key.upper() in drug:
            matched_moa = moa
            break

    if matched_moa:
        data['mechanism_of_action'] = matched_moa
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'{data.get("ticker")}: {drug[:25]} -> {matched_moa}')
        updated += 1

print(f'\nBatch 10 updated: {updated}')
