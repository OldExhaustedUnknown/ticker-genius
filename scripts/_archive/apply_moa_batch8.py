"""MOA (Mechanism of Action) 적용 - Batch 8"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # More Oncology
    'LUMAKRAS': 'KRAS G12C inhibitor',
    'SOTORASIB': 'KRAS G12C inhibitor',
    'KRAZATI': 'KRAS G12C inhibitor',
    'ADAGRASIB': 'KRAS G12C inhibitor',
    'MRTX849': 'KRAS G12C inhibitor',
    'VORANIGO': 'IDH1 inhibitor',
    'VORASIDENIB': 'IDH1 inhibitor',
    'TIBSOVO': 'IDH1 inhibitor',
    'IVOSIDENIB': 'IDH1 inhibitor',
    'REVUFORJ': 'Menin inhibitor',
    'REVUMENIB': 'Menin inhibitor',
    'KOMZIFTI': 'Menin inhibitor',
    'ZIFTOMENIB': 'Menin inhibitor',
    'AUGTYRO': 'ROS1/NTRK inhibitor',
    'REPOTRECTINIB': 'ROS1/NTRK inhibitor',
    'ROZLYTREK': 'ROS1/NTRK inhibitor',
    'ENTRECTINIB': 'ROS1/NTRK inhibitor',
    'VITRAKVI': 'NTRK inhibitor',
    'LAROTRECTINIB': 'NTRK inhibitor',
    'IBTROZI': 'ROS1 inhibitor',
    'TALETRECTINIB': 'ROS1 inhibitor',
    'RETEVMO': 'RET inhibitor',
    'SELPERCATINIB': 'RET inhibitor',
    'GAVRETO': 'RET inhibitor',
    'PRALSETINIB': 'RET inhibitor',
    'TABRECTA': 'MET inhibitor',
    'CAPMATINIB': 'MET inhibitor',
    'TEPMETKO': 'MET inhibitor',
    'TEPOTINIB': 'MET inhibitor',
    'FRUZAQLA': 'VEGFR inhibitor',
    'FRUQUINTINIB': 'VEGFR inhibitor',
    'LYTGOBI': 'FGFR inhibitor',
    'FUTIBATINIB': 'FGFR inhibitor',
    'PEMAZYRE': 'FGFR inhibitor',
    'PEMIGATINIB': 'FGFR inhibitor',
    'BALVERSA': 'FGFR inhibitor',
    'ERDAFITINIB': 'FGFR inhibitor',
    'NIROGACESTAT': 'Gamma secretase inhibitor',
    'OGSIVEO': 'Gamma secretase inhibitor',
    'ZYNYZ': 'PD-1 inhibitor',
    'RETIFANLIMAB': 'PD-1 inhibitor',
    'TEVIMBRA': 'PD-1 inhibitor',
    'TISLELIZUMAB': 'PD-1 inhibitor',
    'TORIPALIMAB': 'PD-1 inhibitor',
    'LOQTORZI': 'PD-1 inhibitor',
    'UNLOXCYT': 'PD-L1 inhibitor',
    'COSIBELIMAB': 'PD-L1 inhibitor',
    'WELIREG': 'HIF-2α inhibitor',
    'BELZUTIFAN': 'HIF-2α inhibitor',
    'KOSELUGO': 'MEK inhibitor',
    'SELUMETINIB': 'MEK inhibitor',
    'GOMEKLI': 'MEK inhibitor',
    'MIRDAMETINIB': 'MEK inhibitor',
    'AVMAPKI': 'MEK/RAF inhibitor',
    'AVUTOMETINIB': 'MEK/RAF inhibitor',
    'FAKZYNJA': 'MEK/RAF inhibitor',
    'TAZVERIK': 'EZH2 inhibitor',
    'TAZEMETOSTAT': 'EZH2 inhibitor',
    'REZLIDHIA': 'IDH1 inhibitor',
    'OLUTASIDENIB': 'IDH1 inhibitor',
    'ORSERDU': 'SERD',
    'ELACESTRANT': 'SERD',
    'PLUVICTO': 'Radioligand therapy (PSMA)',
    'LU177': 'Radioligand therapy (PSMA)',
    'DANYELZA': 'GD2 inhibitor',
    'NAXITAMAB': 'GD2 inhibitor',
    'OMBURTAMAB': 'B7-H3 antibody',
    'SCEMBLIX': 'STAMP inhibitor',
    'ASCIMINIB': 'STAMP inhibitor',
    'VIJOICE': 'PIK3CA inhibitor',
    'ALPELISIB': 'PIK3CA inhibitor',
    'RHAPSIDO': 'Radionuclide',
    'NIKTIMVO': 'CSF-1R inhibitor',
    'AXATILIMAB': 'CSF-1R inhibitor',
    'BRINSUPRI': 'DPP1 inhibitor',
    'BRENSOCATIB': 'DPP1 inhibitor',

    # Immunology / Autoimmune
    'TAVNEOS': 'C5aR inhibitor',
    'AVACOPAN': 'C5aR inhibitor',
    'VOYDEYA': 'Factor D inhibitor',
    'DANICOPAN': 'Factor D inhibitor',

    # Neuromuscular
    'RELYVRIO': 'Sodium phenylbutyrate/taurursodiol',
    'AMX0035': 'Sodium phenylbutyrate/taurursodiol',
    'RADICAVA': 'Free radical scavenger',
    'EDARAVONE': 'Free radical scavenger',
    'VYGLXIA': 'Glutamate modulator',
    'TRORILUZOLE': 'Glutamate modulator',
    'RILUZOLE': 'Glutamate modulator',
    'RILUTEK': 'Glutamate modulator',
    'APITEGROMAB': 'Myostatin inhibitor',
    'SRK-015': 'Myostatin inhibitor',
    'VAMOROLONE': 'Dissociative corticosteroid',

    # Others
    'VADADUSTAT': 'HIF-PHI',
    'VAFSEO': 'HIF-PHI',
    'JESDUVROQ': 'HIF-PHI',
    'DAPRODUSTAT': 'HIF-PHI',
    'ROXADUSTAT': 'HIF-PHI',
    'EVRENZO': 'HIF-PHI',
    'LENIOLISIB': 'PI3Kδ inhibitor',
    'JOENJA': 'PI3Kδ inhibitor',
    'PHELINUN': 'Alkylating agent',
    'MELPHALAN': 'Alkylating agent',
    'ZIMHI': 'Opioid antagonist',
    'NALOXONE': 'Opioid antagonist',
    'NARCAN': 'Opioid antagonist',
    'NEFFY': 'Epinephrine',
    'ANAPHYLM': 'Epinephrine',
    'EPINEPHRINE': 'Epinephrine',
    'AUVI-Q': 'Epinephrine',
    'EPIPEN': 'Epinephrine',
    'GEFAPIXANT': 'P2X3 receptor antagonist',
    'LYFNUA': 'P2X3 receptor antagonist',
    'LIBERVANT': 'GABA-A receptor modulator',
    'DIAZEPAM': 'GABA-A receptor modulator',
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

print(f'\nBatch 8 updated: {updated}')
