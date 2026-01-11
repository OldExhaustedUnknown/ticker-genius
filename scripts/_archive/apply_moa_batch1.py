"""MOA (Mechanism of Action) 적용 - Batch 1"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Drug name -> MOA mapping
moa_data = {
    # Oncology - Kinase Inhibitors
    'KEYTRUDA': 'PD-1 inhibitor',
    'PEMBROLIZUMAB': 'PD-1 inhibitor',
    'OPDIVO': 'PD-1 inhibitor',
    'NIVOLUMAB': 'PD-1 inhibitor',
    'TECENTRIQ': 'PD-L1 inhibitor',
    'ATEZOLIZUMAB': 'PD-L1 inhibitor',
    'IMFINZI': 'PD-L1 inhibitor',
    'DURVALUMAB': 'PD-L1 inhibitor',
    'BAVENCIO': 'PD-L1 inhibitor',
    'AVELUMAB': 'PD-L1 inhibitor',
    'LIBTAYO': 'PD-1 inhibitor',
    'CEMIPLIMAB': 'PD-1 inhibitor',
    'JEMPERLI': 'PD-1 inhibitor',
    'DOSTARLIMAB': 'PD-1 inhibitor',

    # BTK Inhibitors
    'IMBRUVICA': 'BTK inhibitor',
    'IBRUTINIB': 'BTK inhibitor',
    'CALQUENCE': 'BTK inhibitor',
    'ACALABRUTINIB': 'BTK inhibitor',
    'BRUKINSA': 'BTK inhibitor',
    'ZANUBRUTINIB': 'BTK inhibitor',
    'JAYPIRCA': 'BTK inhibitor',
    'PIRTOBRUTINIB': 'BTK inhibitor',

    # BCL-2 Inhibitors
    'VENCLEXTA': 'BCL-2 inhibitor',
    'VENETOCLAX': 'BCL-2 inhibitor',

    # CDK4/6 Inhibitors
    'IBRANCE': 'CDK4/6 inhibitor',
    'PALBOCICLIB': 'CDK4/6 inhibitor',
    'KISQALI': 'CDK4/6 inhibitor',
    'RIBOCICLIB': 'CDK4/6 inhibitor',
    'VERZENIO': 'CDK4/6 inhibitor',
    'ABEMACICLIB': 'CDK4/6 inhibitor',

    # PARP Inhibitors
    'LYNPARZA': 'PARP inhibitor',
    'OLAPARIB': 'PARP inhibitor',
    'RUBRACA': 'PARP inhibitor',
    'RUCAPARIB': 'PARP inhibitor',
    'ZEJULA': 'PARP inhibitor',
    'NIRAPARIB': 'PARP inhibitor',
    'TALZENNA': 'PARP inhibitor',
    'TALAZOPARIB': 'PARP inhibitor',

    # EGFR Inhibitors
    'TAGRISSO': 'EGFR inhibitor',
    'OSIMERTINIB': 'EGFR inhibitor',
    'IRESSA': 'EGFR inhibitor',
    'GEFITINIB': 'EGFR inhibitor',
    'TARCEVA': 'EGFR inhibitor',
    'ERLOTINIB': 'EGFR inhibitor',
    'GILOTRIF': 'EGFR inhibitor',
    'AFATINIB': 'EGFR inhibitor',
    'VIZIMPRO': 'EGFR inhibitor',
    'DACOMITINIB': 'EGFR inhibitor',

    # ALK Inhibitors
    'XALKORI': 'ALK inhibitor',
    'CRIZOTINIB': 'ALK inhibitor',
    'ALECENSA': 'ALK inhibitor',
    'ALECTINIB': 'ALK inhibitor',
    'ZYKADIA': 'ALK inhibitor',
    'CERITINIB': 'ALK inhibitor',
    'ALUNBRIG': 'ALK inhibitor',
    'BRIGATINIB': 'ALK inhibitor',
    'LORBRENA': 'ALK inhibitor',
    'LORLATINIB': 'ALK inhibitor',

    # BRAF/MEK Inhibitors
    'TAFINLAR': 'BRAF inhibitor',
    'DABRAFENIB': 'BRAF inhibitor',
    'ZELBORAF': 'BRAF inhibitor',
    'VEMURAFENIB': 'BRAF inhibitor',
    'BRAFTOVI': 'BRAF inhibitor',
    'ENCORAFENIB': 'BRAF inhibitor',
    'MEKINIST': 'MEK inhibitor',
    'TRAMETINIB': 'MEK inhibitor',
    'COTELLIC': 'MEK inhibitor',
    'COBIMETINIB': 'MEK inhibitor',
    'MEKTOVI': 'MEK inhibitor',
    'BINIMETINIB': 'MEK inhibitor',

    # HER2 Targeted
    'HERCEPTIN': 'HER2 inhibitor',
    'TRASTUZUMAB': 'HER2 inhibitor',
    'PERJETA': 'HER2 inhibitor',
    'PERTUZUMAB': 'HER2 inhibitor',
    'KADCYLA': 'HER2-targeted ADC',
    'ENHERTU': 'HER2-targeted ADC',
    'TUKYSA': 'HER2 kinase inhibitor',
    'TUCATINIB': 'HER2 kinase inhibitor',
    'NERLYNX': 'HER2 kinase inhibitor',
    'NERATINIB': 'HER2 kinase inhibitor',

    # VEGF/Angiogenesis
    'AVASTIN': 'VEGF inhibitor',
    'BEVACIZUMAB': 'VEGF inhibitor',
    'CYRAMZA': 'VEGFR2 inhibitor',
    'RAMUCIRUMAB': 'VEGFR2 inhibitor',
    'EYLEA': 'VEGF trap',
    'AFLIBERCEPT': 'VEGF trap',

    # Multi-kinase Inhibitors
    'SUTENT': 'Multi-kinase inhibitor',
    'SUNITINIB': 'Multi-kinase inhibitor',
    'NEXAVAR': 'Multi-kinase inhibitor',
    'SORAFENIB': 'Multi-kinase inhibitor',
    'STIVARGA': 'Multi-kinase inhibitor',
    'REGORAFENIB': 'Multi-kinase inhibitor',
    'VOTRIENT': 'Multi-kinase inhibitor',
    'PAZOPANIB': 'Multi-kinase inhibitor',
    'CABOMETYX': 'Multi-kinase inhibitor',
    'CABOZANTINIB': 'Multi-kinase inhibitor',
    'LENVIMA': 'Multi-kinase inhibitor',
    'LENVATINIB': 'Multi-kinase inhibitor',

    # FLT3 Inhibitors
    'XOSPATA': 'FLT3 inhibitor',
    'GILTERITINIB': 'FLT3 inhibitor',
    'RYDAPT': 'FLT3 inhibitor',
    'MIDOSTAURIN': 'FLT3 inhibitor',
    'VANFLYTA': 'FLT3 inhibitor',
    'QUIZARTINIB': 'FLT3 inhibitor',

    # IDH Inhibitors
    'TIBSOVO': 'IDH1 inhibitor',
    'IVOSIDENIB': 'IDH1 inhibitor',
    'IDHIFA': 'IDH2 inhibitor',
    'ENASIDENIB': 'IDH2 inhibitor',
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Skip if already has MOA
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

print(f'\nBatch 1 updated: {updated}')
