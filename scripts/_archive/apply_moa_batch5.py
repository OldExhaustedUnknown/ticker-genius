"""MOA (Mechanism of Action) 적용 - Batch 5"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # Neurology / CNS
    'NUPLAZID': 'Serotonin 5-HT2A inverse agonist',
    'PIMAVANSERIN': 'Serotonin 5-HT2A inverse agonist',
    'DAYBUE': 'IGF-1 analogue',
    'TROFINETIDE': 'IGF-1 analogue',
    'EPIDIOLEX': 'Cannabinoid',
    'CANNABIDIOL': 'Cannabinoid',
    'FINTEPLA': 'Serotonin 5-HT2 agonist',
    'FENFLURAMINE': 'Serotonin 5-HT2 agonist',
    'ZTALMY': 'GABA-A receptor modulator',
    'GANAXOLONE': 'GABA-A receptor modulator',
    'XYWAV': 'GHB receptor agonist',
    'XYREM': 'GHB receptor agonist',
    'WAKIX': 'Histamine H3 receptor antagonist',
    'PITOLISANT': 'Histamine H3 receptor antagonist',
    'INGREZZA': 'VMAT2 inhibitor',
    'VALBENAZINE': 'VMAT2 inhibitor',
    'AUSTEDO': 'VMAT2 inhibitor',
    'DEUTETRABENAZINE': 'VMAT2 inhibitor',
    'CAPLYTA': 'Serotonin 5-HT2A/D2 receptor modulator',
    'LUMATEPERONE': 'Serotonin 5-HT2A/D2 receptor modulator',
    'COBENFY': 'Muscarinic M1/M4 agonist',
    'XANOMELINE': 'Muscarinic M1/M4 agonist',
    'IGALMI': 'Alpha-2 adrenergic agonist',
    'DEXMEDETOMIDINE': 'Alpha-2 adrenergic agonist',
    'BXCL501': 'Alpha-2 adrenergic agonist',
    'EXXUA': '5-HT1A receptor agonist',
    'GEPIRONE': '5-HT1A receptor agonist',
    'REXULTI': 'D2/5-HT1A partial agonist',
    'BREXPIPRAZOLE': 'D2/5-HT1A partial agonist',
    'VRAYLAR': 'D3/D2 partial agonist',
    'CARIPRAZINE': 'D3/D2 partial agonist',
    'LYBALVI': 'D2/5-HT2A antagonist',
    'UZEDY': 'D2 antagonist',
    'QELBREE': 'Norepinephrine reuptake inhibitor',
    'VILOXAZINE': 'Norepinephrine reuptake inhibitor',
    'ZURANOLONE': 'GABA-A receptor modulator',
    'ZURZUVAE': 'GABA-A receptor modulator',

    # Alzheimer's
    'LEQEMBI': 'Anti-amyloid antibody',
    'LECANEMAB': 'Anti-amyloid antibody',
    'KISUNLA': 'Anti-amyloid antibody',
    'DONANEMAB': 'Anti-amyloid antibody',
    'ADUHELM': 'Anti-amyloid antibody',
    'ADUCANUMAB': 'Anti-amyloid antibody',

    # Parkinson's
    'ONGENTYS': 'COMT inhibitor',
    'OPICAPONE': 'COMT inhibitor',
    'NOURIANZ': 'Adenosine A2A receptor antagonist',
    'ISTRADEFYLLINE': 'Adenosine A2A receptor antagonist',
    'CREXONT': 'Dopamine precursor',
    'APOMORPHINE': 'Dopamine agonist',
    'ONAPGO': 'Dopamine agonist',

    # Sleep
    'QUVIVIQ': 'Orexin receptor antagonist',
    'DARIDOREXANT': 'Orexin receptor antagonist',
    'BELSOMRA': 'Orexin receptor antagonist',
    'SUVOREXANT': 'Orexin receptor antagonist',
    'DAYVIGO': 'Orexin receptor antagonist',
    'LEMBOREXANT': 'Orexin receptor antagonist',
    'HETLIOZ': 'Melatonin receptor agonist',
    'TASIMELTEON': 'Melatonin receptor agonist',

    # Pain
    'JOURNAVX': 'Nav1.8 sodium channel inhibitor',
    'SUZETRIGINE': 'Nav1.8 sodium channel inhibitor',
    'VX-548': 'Nav1.8 sodium channel inhibitor',
    'OLINVYK': 'Mu-opioid receptor agonist',
    'OLICERIDINE': 'Mu-opioid receptor agonist',
    'EXPAREL': 'Local anesthetic',
    'BUPIVACAINE': 'Local anesthetic',
    'ZYNRELEF': 'Local anesthetic',

    # Epilepsy
    'FYCOMPA': 'AMPA receptor antagonist',
    'PERAMPANEL': 'AMPA receptor antagonist',
    'BRIVIACT': 'SV2A modulator',
    'BRIVARACETAM': 'SV2A modulator',
    'XCOPRI': 'Sodium channel inhibitor',
    'CENOBAMATE': 'Sodium channel inhibitor',

    # Rare Disease - Enzyme Replacement
    'FABRAZYME': 'Enzyme replacement therapy',
    'AGALSIDASE': 'Enzyme replacement therapy',
    'CEREZYME': 'Enzyme replacement therapy',
    'IMIGLUCERASE': 'Enzyme replacement therapy',
    'VPRIV': 'Enzyme replacement therapy',
    'VELAGLUCERASE': 'Enzyme replacement therapy',
    'ELELYSO': 'Enzyme replacement therapy',
    'TALIGLUCERASE': 'Enzyme replacement therapy',
    'MYOZYME': 'Enzyme replacement therapy',
    'ALGLUCOSIDASE': 'Enzyme replacement therapy',
    'LUMIZYME': 'Enzyme replacement therapy',
    'NEXVIAZYME': 'Enzyme replacement therapy',
    'AVALGLUCOSIDASE': 'Enzyme replacement therapy',
    'NAGLAZYME': 'Enzyme replacement therapy',
    'GALSULFASE': 'Enzyme replacement therapy',
    'ELAPRASE': 'Enzyme replacement therapy',
    'IDURSULFASE': 'Enzyme replacement therapy',
    'ALDURAZYME': 'Enzyme replacement therapy',
    'LARONIDASE': 'Enzyme replacement therapy',
    'MEPSEVII': 'Enzyme replacement therapy',
    'VESTRONIDASE': 'Enzyme replacement therapy',
    'LAMZEDE': 'Enzyme replacement therapy',
    'VELMANASE': 'Enzyme replacement therapy',
    'BRINEURA': 'Enzyme replacement therapy',
    'CERLIPONASE': 'Enzyme replacement therapy',
    'ELFABRIO': 'Enzyme replacement therapy',
    'PEGUNIGALSIDASE': 'Enzyme replacement therapy',
    'GALAFOLD': 'Pharmacological chaperone',
    'MIGALASTAT': 'Pharmacological chaperone',
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

print(f'\nBatch 5 updated: {updated}')
