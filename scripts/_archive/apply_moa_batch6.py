"""MOA (Mechanism of Action) 적용 - Batch 6"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # Ophthalmology
    'EYLEA': 'VEGF trap',
    'AFLIBERCEPT': 'VEGF trap',
    'LUCENTIS': 'VEGF inhibitor',
    'RANIBIZUMAB': 'VEGF inhibitor',
    'VABYSMO': 'VEGF/Ang-2 inhibitor',
    'FARICIMAB': 'VEGF/Ang-2 inhibitor',
    'BEOVU': 'VEGF inhibitor',
    'BROLUCIZUMAB': 'VEGF inhibitor',
    'IZERVAY': 'C5 inhibitor',
    'AVACINCAPTAD': 'C5 inhibitor',
    'VUITY': 'Miotic agent (muscarinic)',
    'PILOCARPINE': 'Miotic agent (muscarinic)',
    'XDEMVY': 'Antiparasitic',
    'LOTILANER': 'Antiparasitic',
    'TP-03': 'Antiparasitic',
    'UPNEEQ': 'Alpha-1 adrenergic agonist',
    'OXYMETAZOLINE': 'Alpha-1 adrenergic agonist',
    'DEXTENZA': 'Corticosteroid',
    'EYSUVIS': 'Corticosteroid',
    'LOTEPREDNOL': 'Corticosteroid',
    'REPROXALAP': 'RASP inhibitor',
    'ADX-2191': 'Antimetabolite',
    'METHOTREXATE': 'Antimetabolite',
    'TRAVOPROST': 'Prostaglandin analogue',
    'IDOSE': 'Prostaglandin analogue',
    'DURYSTA': 'Prostaglandin analogue',
    'BIMATOPROST': 'Prostaglandin analogue',
    'MIEBO': 'Lipid-based therapy',
    'OC-01': 'Nicotinic receptor agonist',
    'TYRVAYA': 'Nicotinic receptor agonist',
    'VARENICLINE': 'Nicotinic receptor agonist',

    # Dermatology
    'ZORYVE': 'PDE4 inhibitor',
    'ROFLUMILAST': 'PDE4 inhibitor',
    'ARQ-151': 'PDE4 inhibitor',
    'ARQ-154': 'PDE4 inhibitor',
    'VTAMA': 'AhR agonist',
    'TAPINAROF': 'AhR agonist',
    'ZILXI': 'Antibiotic (tetracycline)',
    'MINOCYCLINE': 'Antibiotic (tetracycline)',
    'BERDAZIMER': 'Nitric oxide-releasing agent',
    'VP-102': 'Antimitotic agent',
    'YCANTH': 'Antimitotic agent',
    'CANTHARIDIN': 'Antimitotic agent',
    'DAXXIFY': 'Neurotoxin',
    'DAXIBOTULINUM': 'Neurotoxin',
    'BOTOX': 'Neurotoxin',
    'LETYBO': 'Neurotoxin',
    'LETIBOTULINUMTOXIN': 'Neurotoxin',
    'QWO': 'Collagenase',
    'COLLAGENASE': 'Collagenase',

    # Infectious Disease - Antibiotics
    'XACDURO': 'Beta-lactam/beta-lactamase inhibitor',
    'SULBACTAM': 'Beta-lactam/beta-lactamase inhibitor',
    'DURLOBACTAM': 'Beta-lactam/beta-lactamase inhibitor',
    'FETROJA': 'Siderophore cephalosporin',
    'CEFIDEROCOL': 'Siderophore cephalosporin',
    'RECARBRIO': 'Carbapenem/beta-lactamase inhibitor',
    'RELEBACTAM': 'Carbapenem/beta-lactamase inhibitor',
    'NUZYRA': 'Tetracycline antibiotic',
    'OMADACYCLINE': 'Tetracycline antibiotic',
    'XERAVA': 'Tetracycline antibiotic',
    'ERAVACYCLINE': 'Tetracycline antibiotic',
    'ZEMDRI': 'Aminoglycoside antibiotic',
    'PLAZOMICIN': 'Aminoglycoside antibiotic',
    'ARIKAYCE': 'Aminoglycoside antibiotic',
    'AMIKACIN': 'Aminoglycoside antibiotic',
    'DIFICID': 'Macrolide antibiotic',
    'FIDAXOMICIN': 'Macrolide antibiotic',
    'REZZAYO': 'Echinocandin antifungal',
    'REZAFUNGIN': 'Echinocandin antifungal',
    'BREXAFEMME': 'Triterpenoid antifungal',
    'IBREXAFUNGERP': 'Triterpenoid antifungal',
    'NUZOLVENCE': 'Spiropyrimidinetrione antibiotic',
    'ZOLIFLODACIN': 'Spiropyrimidinetrione antibiotic',
    'BLUJEPA': 'Triazaacenaphthylene antibiotic',
    'GEPOTIDACIN': 'Triazaacenaphthylene antibiotic',
    'ORLYNVAH': 'Penem antibiotic',
    'SULOPENEM': 'Penem antibiotic',
    'TEBIPENEM': 'Carbapenem antibiotic',
    'CONTEPO': 'Carbapenem antibiotic',

    # Infectious Disease - Antiviral
    'VEKLURY': 'RNA polymerase inhibitor',
    'REMDESIVIR': 'RNA polymerase inhibitor',
    'PAXLOVID': 'Protease inhibitor',
    'NIRMATRELVIR': 'Protease inhibitor',
    'LAGEVRIO': 'Nucleoside analogue',
    'MOLNUPIRAVIR': 'Nucleoside analogue',
    'PREVYMIS': 'CMV terminase inhibitor',
    'LETERMOVIR': 'CMV terminase inhibitor',
    'TEMBEXA': 'Viral DNA polymerase inhibitor',
    'BRINCIDOFOVIR': 'Viral DNA polymerase inhibitor',
    'SUNLENCA': 'Capsid inhibitor',
    'LENACAPAVIR': 'Capsid inhibitor',
    'RUKOBIA': 'Attachment inhibitor',
    'FOSTEMSAVIR': 'Attachment inhibitor',
    'TROGARZO': 'CD4-directed post-attachment inhibitor',
    'IBALIZUMAB': 'CD4-directed post-attachment inhibitor',
    'CABENUVA': 'Integrase inhibitor + NNRTI',
    'CABOTEGRAVIR': 'Integrase inhibitor',
    'VOCABRIA': 'Integrase inhibitor',

    # RSV
    'ENFLONSIA': 'RSV F protein inhibitor',
    'CLESROVIMAB': 'RSV F protein inhibitor',
    'BEYFORTUS': 'RSV F protein inhibitor',
    'NIRSEVIMAB': 'RSV F protein inhibitor',
    'MRESVIA': 'mRNA vaccine',
    'AREXVY': 'RSV vaccine',
    'ABRYSVO': 'RSV vaccine',
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

print(f'\nBatch 6 updated: {updated}')
