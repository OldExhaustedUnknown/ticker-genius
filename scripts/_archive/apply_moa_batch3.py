"""MOA (Mechanism of Action) 적용 - Batch 3"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # GLP-1/GIP Agonists
    'OZEMPIC': 'GLP-1 receptor agonist',
    'SEMAGLUTIDE': 'GLP-1 receptor agonist',
    'WEGOVY': 'GLP-1 receptor agonist',
    'RYBELSUS': 'GLP-1 receptor agonist',
    'MOUNJARO': 'GLP-1/GIP receptor agonist',
    'TIRZEPATIDE': 'GLP-1/GIP receptor agonist',
    'ZEPBOUND': 'GLP-1/GIP receptor agonist',
    'TRULICITY': 'GLP-1 receptor agonist',
    'DULAGLUTIDE': 'GLP-1 receptor agonist',
    'VICTOZA': 'GLP-1 receptor agonist',
    'LIRAGLUTIDE': 'GLP-1 receptor agonist',
    'SAXENDA': 'GLP-1 receptor agonist',
    'BYDUREON': 'GLP-1 receptor agonist',
    'EXENATIDE': 'GLP-1 receptor agonist',

    # SGLT2 Inhibitors
    'JARDIANCE': 'SGLT2 inhibitor',
    'EMPAGLIFLOZIN': 'SGLT2 inhibitor',
    'FARXIGA': 'SGLT2 inhibitor',
    'DAPAGLIFLOZIN': 'SGLT2 inhibitor',
    'INVOKANA': 'SGLT2 inhibitor',
    'CANAGLIFLOZIN': 'SGLT2 inhibitor',
    'STEGLATRO': 'SGLT2 inhibitor',
    'ERTUGLIFLOZIN': 'SGLT2 inhibitor',
    'SOTAGLIFLOZIN': 'SGLT1/2 inhibitor',
    'INPEFA': 'SGLT1/2 inhibitor',

    # DPP-4 Inhibitors
    'JANUVIA': 'DPP-4 inhibitor',
    'SITAGLIPTIN': 'DPP-4 inhibitor',
    'TRADJENTA': 'DPP-4 inhibitor',
    'LINAGLIPTIN': 'DPP-4 inhibitor',
    'ONGLYZA': 'DPP-4 inhibitor',
    'SAXAGLIPTIN': 'DPP-4 inhibitor',
    'NESINA': 'DPP-4 inhibitor',
    'ALOGLIPTIN': 'DPP-4 inhibitor',

    # PCSK9 Inhibitors
    'REPATHA': 'PCSK9 inhibitor',
    'EVOLOCUMAB': 'PCSK9 inhibitor',
    'PRALUENT': 'PCSK9 inhibitor',
    'ALIROCUMAB': 'PCSK9 inhibitor',
    'LEQVIO': 'PCSK9 siRNA',
    'INCLISIRAN': 'PCSK9 siRNA',

    # Heart Failure
    'ENTRESTO': 'Neprilysin/ARB inhibitor',
    'SACUBITRIL': 'Neprilysin/ARB inhibitor',
    'VERQUVO': 'sGC stimulator',
    'VERICIGUAT': 'sGC stimulator',
    'CAMZYOS': 'Myosin inhibitor',
    'MAVACAMTEN': 'Myosin inhibitor',
    'MYQORZO': 'Myosin activator',
    'OMECAMTIV': 'Myosin activator',

    # Anticoagulants
    'ELIQUIS': 'Factor Xa inhibitor',
    'APIXABAN': 'Factor Xa inhibitor',
    'XARELTO': 'Factor Xa inhibitor',
    'RIVAROXABAN': 'Factor Xa inhibitor',
    'PRADAXA': 'Thrombin inhibitor',
    'DABIGATRAN': 'Thrombin inhibitor',
    'SAVAYSA': 'Factor Xa inhibitor',
    'EDOXABAN': 'Factor Xa inhibitor',

    # Lipid-lowering
    'NEXLETOL': 'ACL inhibitor',
    'BEMPEDOIC': 'ACL inhibitor',
    'NEXLIZET': 'ACL inhibitor + ezetimibe',
    'LIVMARLI': 'IBAT inhibitor',
    'MARALIXIBAT': 'IBAT inhibitor',
    'BYLVAY': 'IBAT inhibitor',
    'ODEVIXIBAT': 'IBAT inhibitor',

    # NASH/Liver
    'REZDIFFRA': 'Thyroid hormone receptor beta agonist',
    'RESMETIROM': 'Thyroid hormone receptor beta agonist',
    'LIVDELZI': 'PPARδ agonist',
    'SELADELPAR': 'PPARδ agonist',
    'OCALIVA': 'FXR agonist',
    'OBETICHOLIC': 'FXR agonist',

    # Pulmonary Arterial Hypertension
    'UPTRAVI': 'IP receptor agonist',
    'SELEXIPAG': 'IP receptor agonist',
    'TYVASO': 'Prostacyclin analogue',
    'TREPROSTINIL': 'Prostacyclin analogue',
    'YUTREPIA': 'Prostacyclin analogue',
    'WINREVAIR': 'Activin signaling inhibitor',
    'SOTATERCEPT': 'Activin signaling inhibitor',

    # Migraine
    'AIMOVIG': 'CGRP receptor antagonist',
    'ERENUMAB': 'CGRP receptor antagonist',
    'AJOVY': 'CGRP antagonist',
    'FREMANEZUMAB': 'CGRP antagonist',
    'EMGALITY': 'CGRP antagonist',
    'GALCANEZUMAB': 'CGRP antagonist',
    'VYEPTI': 'CGRP antagonist',
    'EPTINEZUMAB': 'CGRP antagonist',
    'NURTEC': 'CGRP receptor antagonist',
    'RIMEGEPANT': 'CGRP receptor antagonist',
    'UBRELVY': 'CGRP receptor antagonist',
    'UBROGEPANT': 'CGRP receptor antagonist',
    'QULIPTA': 'CGRP receptor antagonist',
    'ATOGEPANT': 'CGRP receptor antagonist',

    # Asthma/Allergy
    'XOLAIR': 'IgE inhibitor',
    'OMALIZUMAB': 'IgE inhibitor',
    'TEZSPIRE': 'TSLP inhibitor',
    'TEZEPELUMAB': 'TSLP inhibitor',

    # Cystic Fibrosis
    'TRIKAFTA': 'CFTR modulator',
    'KALYDECO': 'CFTR potentiator',
    'IVACAFTOR': 'CFTR potentiator',
    'SYMDEKO': 'CFTR modulator',
    'ORKAMBI': 'CFTR modulator',
    'ALYFTREK': 'CFTR modulator',
    'VANZACAFTOR': 'CFTR modulator',
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

print(f'\nBatch 3 updated: {updated}')
