"""MOA (Mechanism of Action) 적용 - Batch 2"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # JAK Inhibitors
    'JAKAFI': 'JAK1/2 inhibitor',
    'RUXOLITINIB': 'JAK1/2 inhibitor',
    'XELJANZ': 'JAK inhibitor',
    'TOFACITINIB': 'JAK inhibitor',
    'OLUMIANT': 'JAK1/2 inhibitor',
    'BARICITINIB': 'JAK1/2 inhibitor',
    'RINVOQ': 'JAK1 inhibitor',
    'UPADACITINIB': 'JAK1 inhibitor',
    'CIBINQO': 'JAK1 inhibitor',
    'ABROCITINIB': 'JAK1 inhibitor',
    'OPZELURA': 'JAK1/2 inhibitor',
    'INREBIC': 'JAK2 inhibitor',
    'FEDRATINIB': 'JAK2 inhibitor',
    'OJJAARA': 'JAK1/2 inhibitor',
    'MOMELOTINIB': 'JAK1/2 inhibitor',
    'LITFULO': 'JAK3/TEC inhibitor',
    'RITLECITINIB': 'JAK3/TEC inhibitor',

    # IL Inhibitors
    'DUPIXENT': 'IL-4/IL-13 inhibitor',
    'DUPILUMAB': 'IL-4/IL-13 inhibitor',
    'ADBRY': 'IL-13 inhibitor',
    'TRALOKINUMAB': 'IL-13 inhibitor',
    'NUCALA': 'IL-5 inhibitor',
    'MEPOLIZUMAB': 'IL-5 inhibitor',
    'FASENRA': 'IL-5R inhibitor',
    'BENRALIZUMAB': 'IL-5R inhibitor',
    'CINQAIR': 'IL-5 inhibitor',
    'RESLIZUMAB': 'IL-5 inhibitor',
    'COSENTYX': 'IL-17A inhibitor',
    'SECUKINUMAB': 'IL-17A inhibitor',
    'TALTZ': 'IL-17A inhibitor',
    'IXEKIZUMAB': 'IL-17A inhibitor',
    'SILIQ': 'IL-17RA inhibitor',
    'BRODALUMAB': 'IL-17RA inhibitor',
    'SKYRIZI': 'IL-23 inhibitor',
    'RISANKIZUMAB': 'IL-23 inhibitor',
    'TREMFYA': 'IL-23 inhibitor',
    'GUSELKUMAB': 'IL-23 inhibitor',
    'ILUMYA': 'IL-23 inhibitor',
    'TILDRAKIZUMAB': 'IL-23 inhibitor',
    'STELARA': 'IL-12/23 inhibitor',
    'USTEKINUMAB': 'IL-12/23 inhibitor',
    'ILARIS': 'IL-1β inhibitor',
    'CANAKINUMAB': 'IL-1β inhibitor',
    'KINERET': 'IL-1 receptor antagonist',
    'ANAKINRA': 'IL-1 receptor antagonist',
    'ARCALYST': 'IL-1 trap',
    'RILONACEPT': 'IL-1 trap',
    'ACTEMRA': 'IL-6 receptor inhibitor',
    'TOCILIZUMAB': 'IL-6 receptor inhibitor',
    'KEVZARA': 'IL-6 receptor inhibitor',
    'SARILUMAB': 'IL-6 receptor inhibitor',

    # TNF Inhibitors
    'HUMIRA': 'TNF inhibitor',
    'ADALIMUMAB': 'TNF inhibitor',
    'ENBREL': 'TNF inhibitor',
    'ETANERCEPT': 'TNF inhibitor',
    'REMICADE': 'TNF inhibitor',
    'INFLIXIMAB': 'TNF inhibitor',
    'SIMPONI': 'TNF inhibitor',
    'GOLIMUMAB': 'TNF inhibitor',
    'CIMZIA': 'TNF inhibitor',
    'CERTOLIZUMAB': 'TNF inhibitor',

    # B-cell Targeted
    'RITUXAN': 'CD20 inhibitor',
    'RITUXIMAB': 'CD20 inhibitor',
    'GAZYVA': 'CD20 inhibitor',
    'OBINUTUZUMAB': 'CD20 inhibitor',
    'OCREVUS': 'CD20 inhibitor',
    'OCRELIZUMAB': 'CD20 inhibitor',
    'KESIMPTA': 'CD20 inhibitor',
    'OFATUMUMAB': 'CD20 inhibitor',
    'UBLITUXIMAB': 'CD20 inhibitor',
    'BRIUMVI': 'CD20 inhibitor',
    'BENLYSTA': 'BLyS inhibitor',
    'BELIMUMAB': 'BLyS inhibitor',
    'SAPHNELO': 'Type I interferon receptor inhibitor',
    'ANIFROLUMAB': 'Type I interferon receptor inhibitor',

    # Integrin Inhibitors
    'ENTYVIO': 'α4β7 integrin inhibitor',
    'VEDOLIZUMAB': 'α4β7 integrin inhibitor',
    'TYSABRI': 'α4 integrin inhibitor',
    'NATALIZUMAB': 'α4 integrin inhibitor',

    # S1P Modulators
    'GILENYA': 'S1P receptor modulator',
    'FINGOLIMOD': 'S1P receptor modulator',
    'MAYZENT': 'S1P receptor modulator',
    'SIPONIMOD': 'S1P receptor modulator',
    'ZEPOSIA': 'S1P receptor modulator',
    'OZANIMOD': 'S1P receptor modulator',
    'PONVORY': 'S1P receptor modulator',
    'PONESIMOD': 'S1P receptor modulator',

    # TYK2 Inhibitor
    'SOTYKTU': 'TYK2 inhibitor',
    'DEUCRAVACITINIB': 'TYK2 inhibitor',

    # Complement Inhibitors
    'SOLIRIS': 'C5 inhibitor',
    'ECULIZUMAB': 'C5 inhibitor',
    'ULTOMIRIS': 'C5 inhibitor',
    'RAVULIZUMAB': 'C5 inhibitor',
    'EMPAVELI': 'C3 inhibitor',
    'PEGCETACOPLAN': 'C3 inhibitor',
    'SYFOVRE': 'C3 inhibitor',
    'UPLIZNA': 'CD19 inhibitor',
    'INEBILIZUMAB': 'CD19 inhibitor',
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

print(f'\nBatch 2 updated: {updated}')
