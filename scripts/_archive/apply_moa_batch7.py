"""MOA (Mechanism of Action) 적용 - Batch 7"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # Hematology
    'HEMLIBRA': 'Bispecific antibody (FIXa/FX)',
    'EMICIZUMAB': 'Bispecific antibody (FIXa/FX)',
    'ALHEMO': 'TFPI inhibitor',
    'CONCIZUMAB': 'TFPI inhibitor',
    'HYMPAVZI': 'TFPI inhibitor',
    'MARSTACIMAB': 'TFPI inhibitor',
    'REBLOZYL': 'TGF-β ligand trap',
    'LUSPATERCEPT': 'TGF-β ligand trap',
    'EFANESOCTOCOG': 'Factor VIII replacement',
    'ALTUVIIIO': 'Factor VIII replacement',
    'ROCTAVIAN': 'Factor VIII gene therapy',
    'VALOCTOCOGENE': 'Factor VIII gene therapy',
    'HEMGENIX': 'Factor IX gene therapy',
    'BEQVEZ': 'Factor IX gene therapy',
    'FIDANACOGENE': 'Factor IX gene therapy',
    'EKTERLY': 'Kallikrein inhibitor',
    'SEBETRALSTAT': 'Kallikrein inhibitor',
    'TAKHZYRO': 'Kallikrein inhibitor',
    'LANADELUMAB': 'Kallikrein inhibitor',
    'ORLADEYO': 'Kallikrein inhibitor',
    'BEROTRALSTAT': 'Kallikrein inhibitor',
    'PYRUKYND': 'Pyruvate kinase activator',
    'MITAPIVAT': 'Pyruvate kinase activator',
    'RYTELO': 'Telomerase inhibitor',
    'IMETELSTAT': 'Telomerase inhibitor',
    'VANRAFIA': 'Plasma kallikrein inhibitor',
    'PACRITINIB': 'JAK2/FLT3 inhibitor',
    'VONJO': 'JAK2/FLT3 inhibitor',
    'NPLATE': 'Thrombopoietin mimetic',
    'ROMIPLOSTIM': 'Thrombopoietin mimetic',
    'PROMACTA': 'Thrombopoietin receptor agonist',
    'ELTROMBOPAG': 'Thrombopoietin receptor agonist',

    # Rare Disease - Other
    'SKYCLARYS': 'Nrf2 activator',
    'OMAVELOXOLONE': 'Nrf2 activator',
    'VOXZOGO': 'CNP analogue',
    'VOSORITIDE': 'CNP analogue',
    'PALYNZIQ': 'Enzyme substitution therapy',
    'PEGVALIASE': 'Enzyme substitution therapy',
    'IMCIVREE': 'MC4R agonist',
    'SETMELANOTIDE': 'MC4R agonist',
    'CYSTARAN': 'Cystine depleting agent',
    'CYSTEAMINE': 'Cystine depleting agent',
    'PROCYSBI': 'Cystine depleting agent',
    'OLPRUVA': 'Nitrogen scavenger',
    'ACER-001': 'Nitrogen scavenger',
    'SODIUM BENZOATE': 'Nitrogen scavenger',
    'PHENYLBUTYRATE': 'Nitrogen scavenger',
    'RAVICTI': 'Nitrogen scavenger',
    'GLYCEROL PHENYLBUTYRATE': 'Nitrogen scavenger',
    'FIRDAPSE': 'Potassium channel blocker',
    'AMIFAMPRIDINE': 'Potassium channel blocker',
    'XERMELO': 'TPH inhibitor',
    'TELOTRISTAT': 'TPH inhibitor',
    'GOVORESTAT': 'Glycogen synthase kinase inhibitor',
    'MIPLYFFA': 'HSP70 co-inducer',
    'ARIMOCLOMOL': 'HSP70 co-inducer',
    'XOLREMDI': 'CXCR4 antagonist',
    'MAVORIXAFOR': 'CXCR4 antagonist',

    # Endocrine
    'RECORLEV': '11β-hydroxylase inhibitor',
    'LEVOKETOCONAZOLE': '11β-hydroxylase inhibitor',
    'ISTURISA': '11β-hydroxylase inhibitor',
    'OSILODROSTAT': '11β-hydroxylase inhibitor',
    'SIGNIFOR': 'Somatostatin analogue',
    'PASIREOTIDE': 'Somatostatin analogue',
    'MYCAPSSA': 'Somatostatin analogue',
    'OCTREOTIDE': 'Somatostatin analogue',
    'NGENLA': 'Growth hormone',
    'SOMATROGON': 'Growth hormone',
    'SOGROYA': 'Growth hormone',
    'SOMAPACITAN': 'Growth hormone',
    'YORVIPATH': 'PTH replacement',
    'TRANSCON PTH': 'PTH replacement',
    'NATPARA': 'PTH replacement',
    'PARATHYROID HORMONE': 'PTH replacement',
    'CRENESSITY': 'CRF1 antagonist',
    'CRINECERFONT': 'CRF1 antagonist',
    'TZIELD': 'CD3-directed antibody',
    'TEPLIZUMAB': 'CD3-directed antibody',
    'DASIGLUCAGON': 'Glucagon receptor agonist',
    'ZEGALOGUE': 'Glucagon receptor agonist',

    # GI
    'OMVOH': 'IL-23 inhibitor',
    'MIRIKIZUMAB': 'IL-23 inhibitor',
    'VOQUEZNA': 'P-CAB',
    'VONOPRAZAN': 'P-CAB',
    'XPHOZAH': 'NHE3 inhibitor',
    'TENAPANOR': 'NHE3 inhibitor',
    'LINZESS': 'GC-C agonist',
    'LINACLOTIDE': 'GC-C agonist',
    'TRULANCE': 'GC-C agonist',
    'PLECANATIDE': 'GC-C agonist',
    'SER-109': 'Microbiome therapeutic',
    'VOWST': 'Microbiome therapeutic',
    'REBYOTA': 'Microbiome therapeutic',
    'TERLIVAZ': 'V1 receptor agonist',
    'TERLIPRESSIN': 'V1 receptor agonist',

    # Women's Health
    'ORIAHNN': 'GnRH antagonist',
    'ELAGOLIX': 'GnRH antagonist',
    'ORILISSA': 'GnRH antagonist',
    'MYFEMBREE': 'GnRH antagonist',
    'RELUGOLIX': 'GnRH antagonist',
    'ORGOVYX': 'GnRH antagonist',
    'VEOZAH': 'NK3 receptor antagonist',
    'FEZOLINETANT': 'NK3 receptor antagonist',
    'TWIRLA': 'Hormonal contraceptive',
    'PHEXXI': 'Vaginal pH regulator',
    'BIJUVA': 'Hormone replacement therapy',

    # Bone
    'EVENITY': 'Sclerostin inhibitor',
    'ROMOSOZUMAB': 'Sclerostin inhibitor',
    'TYMLOS': 'PTHrP analogue',
    'ABALOPARATIDE': 'PTHrP analogue',
    'PROLIA': 'RANKL inhibitor',
    'DENOSUMAB': 'RANKL inhibitor',
    'XGEVA': 'RANKL inhibitor',
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

print(f'\nBatch 7 updated: {updated}')
