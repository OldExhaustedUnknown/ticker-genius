"""MOA (Mechanism of Action) 적용 - Batch 9"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # Biosimilars - give generic MOA
    'RIABNI': 'CD20 inhibitor (biosimilar)',
    'AVT05': 'CD20 inhibitor (biosimilar)',
    'OZILTUS': 'HER2 inhibitor (biosimilar)',
    'BONCRESA': 'Insulin (biosimilar)',
    'BREKIYA': 'IL-17A inhibitor (biosimilar)',
    'NYVEPRIA': 'G-CSF (biosimilar)',
    'SEMGLEE': 'Insulin (biosimilar)',
    'TOFIDENCE': 'IL-6R inhibitor (biosimilar)',
    'UDENYCA': 'G-CSF (biosimilar)',
    'CHS-201': 'TNF inhibitor (biosimilar)',
    'CHS-1420': 'TNF inhibitor (biosimilar)',
    'HUMIRA BIOSIM': 'TNF inhibitor (biosimilar)',
    'HULIO': 'TNF inhibitor (biosimilar)',
    'IDACIO': 'TNF inhibitor (biosimilar)',
    'HADLIMA': 'TNF inhibitor (biosimilar)',
    'HYRIMOZ': 'TNF inhibitor (biosimilar)',
    'CYLTEZO': 'TNF inhibitor (biosimilar)',
    'YUSIMRY': 'TNF inhibitor (biosimilar)',
    'ABRILADA': 'TNF inhibitor (biosimilar)',
    'SIMLANDI': 'TNF inhibitor (biosimilar)',
    'MVASI': 'VEGF inhibitor (biosimilar)',
    'ZIRABEV': 'VEGF inhibitor (biosimilar)',
    'VEGZELMA': 'VEGF inhibitor (biosimilar)',
    'LYTENAVA': 'VEGF inhibitor (biosimilar)',
    'ONS-5010': 'VEGF inhibitor (biosimilar)',
    'RUXIENCE': 'CD20 inhibitor (biosimilar)',
    'TRUXIMA': 'CD20 inhibitor (biosimilar)',
    'RIXIMYO': 'CD20 inhibitor (biosimilar)',
    'OGIVRI': 'HER2 inhibitor (biosimilar)',
    'HERZUMA': 'HER2 inhibitor (biosimilar)',
    'KANJINTI': 'HER2 inhibitor (biosimilar)',
    'ONTRUZANT': 'HER2 inhibitor (biosimilar)',
    'TRAZIMERA': 'HER2 inhibitor (biosimilar)',

    # Growth hormones
    'TRANSCON HGH': 'Growth hormone',
    'SKYTROFA': 'Growth hormone',
    'LONAPEGSOMATROPIN': 'Growth hormone',
    'TRANSCON CNP': 'CNP analogue',
    'NAVEPEGRITIDE': 'CNP analogue',

    # Gene therapy / Cell therapy - additional
    'ZEVASKYN': 'Autologous T cell therapy',
    'PRADEMAGENE': 'Autologous T cell therapy',
    'PZ-CEL': 'Autologous T cell therapy',
    'TABELECLEUCEL': 'Allogeneic T cell therapy',
    'EBVALLO': 'Allogeneic T cell therapy',
    'OMIDUBICEL': 'Expanded cord blood',
    'NICORD': 'Expanded cord blood',
    'RYONCIL': 'MSC therapy',
    'REMESTEMCEL': 'MSC therapy',
    'DERAMIOCEL': 'Cell therapy',
    'CAP-1002': 'Cell therapy',
    'KRESLADI': 'Gene therapy',
    'MARNETEGRAGENE': 'Gene therapy',
    'PAPZIMEOS': 'Gene therapy',
    'ZOPAPOGENE': 'Gene therapy',

    # Vaccines
    'PREVNAR': 'Pneumococcal vaccine',
    'VAXNEUVANCE': 'Pneumococcal vaccine',
    'CAPVAXIVE': 'Pneumococcal vaccine',
    'V116': 'Pneumococcal vaccine',
    'PENBRAYA': 'Meningococcal vaccine',
    'PENMENVY': 'Meningococcal vaccine',
    'HEPLISAV': 'Hepatitis B vaccine',
    'SCI-B-VAC': 'Hepatitis B vaccine',
    'IXCHIQ': 'Chikungunya vaccine',
    'VLA1553': 'Chikungunya vaccine',
    'NOVAVAX': 'COVID-19 vaccine',
    'COVOVAX': 'COVID-19 vaccine',
    'NUVAXOVID': 'COVID-19 vaccine',
    'MNEXSPIKE': 'COVID-19 mRNA vaccine',
    'MRNA-1283': 'COVID-19 mRNA vaccine',
    'AREXVY': 'RSV vaccine',
    'ABRYSVO': 'RSV vaccine',

    # Misc drugs
    'EMRELIS': 'TNF inhibitor',
    'ADALIMUMAB': 'TNF inhibitor',
    'EMBLAVEO': 'JAK1 inhibitor',
    'ZUNVEYL': 'Antipsychotic',
    'OLANZAPINE': 'Antipsychotic',
    'OXYGEN': 'Supplemental oxygen',
    'NITROGEN': 'Inert gas',
    'REXTOVY': 'Hyaluronidase + rituximab',
    'OLEOGEL-S10': 'Wound healing',
    'TADALAFIL': 'PDE5 inhibitor',
    'MODEYSO': 'PI3Kδ inhibitor',
    'DORDAVIPRONE': 'PI3Kδ inhibitor',
    'RELACORILANT': 'GR antagonist',
    'AVASOPASEM': 'Dismutase mimetic',
    'LINERIXIBAT': 'IBAT inhibitor',
    'DEPEMOKIMAB': 'IL-5 inhibitor',
    'EXDENSUR': 'GnRH antagonist',
    'SURUFATINIB': 'Multi-kinase inhibitor',
    'HTX-019': 'NK1 receptor antagonist',
    'BARHEMSYS': 'D2 receptor antagonist',
    'BYFAVO': 'GABA-A receptor modulator',
    'REMIMAZOLAM': 'GABA-A receptor modulator',
    'ANJESO': 'COX-2 inhibitor',
    'MELOXICAM': 'COX-2 inhibitor',
    'XIPERE': 'Corticosteroid',
    'TRIAMCINOLONE': 'Corticosteroid',
    'ALKINDI': 'Corticosteroid',
    'HYDROCORTISONE': 'Corticosteroid',
    'KHINDIVI': 'Corticosteroid',
    'PEDMARK': 'Otoprotectant',
    'SODIUM THIOSULFATE': 'Otoprotectant',
    'ANKTIVA': 'IL-15 superagonist',
    'N-803': 'IL-15 superagonist',
    'TRUDHESA': 'Ergot alkaloid',
    'DIHYDROERGOTAMINE': 'Ergot alkaloid',
    'INP104': 'Ergot alkaloid',
    'SYMBRAVO': 'NSAID + triptan',
    'AXS-07': 'NSAID + triptan',
    'AIRSUPRA': 'Bronchodilator',
    'ALBUTEROL': 'Bronchodilator',
    'BREZTRI': 'Triple inhaler',
    'SYMBICORT': 'ICS/LABA',
    'CERIANNA': 'Diagnostic agent',
    'TAUVID': 'Diagnostic agent',
    'FLORTAUCIPIR': 'Diagnostic agent',
    'GALLIUM': 'Diagnostic agent',
    'GOZETOTIDE': 'Diagnostic agent',
    'PYRIDOSTIGMINE': 'Acetylcholinesterase inhibitor',
    'ENSIFENTRINE': 'PDE3/4 inhibitor',
    'OHTUVAYRE': 'PDE3/4 inhibitor',
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

print(f'\nBatch 9 updated: {updated}')
