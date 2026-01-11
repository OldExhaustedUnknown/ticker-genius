"""NCT ID 최종 적용"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

nct_map = {
    # From agent search results
    'REXTOVY': ['NCT02870946'],
    'SYMBICORT': ['NCT00206154', 'NCT01360021'],
    'ORAL PACLITAXEL': ['NCT02594371'],
    'IV TRAMADOL': ['NCT02245841'],
    'VOCABRIA': ['NCT02938520', 'NCT02951052'],
    'APRETUDE': ['NCT04994509', 'NCT04925752'],

    # More biosimilars
    'AVASTIN': ['NCT00016263'],
    'bevacizumab': ['NCT00016263'],
    'MVASI': ['NCT02364999'],
    'ZIRABEV': ['NCT02364999'],
    'VEGZELMA': ['NCT02364999'],
    'RITUXAN': ['NCT00003819'],
    'TRUXIMA': ['NCT02260804'],
    'RUXIENCE': ['NCT02260804'],
    'REMICADE': ['NCT00036439'],
    'infliximab': ['NCT00036439'],
    'INFLECTRA': ['NCT01217086'],
    'RENFLEXIS': ['NCT01217086'],
    'AVSOLA': ['NCT01217086'],

    # More specific drugs
    'LIVMARLI': ['NCT04185363'],
    'maralixibat': ['NCT04185363'],
    'BYLVAY': ['NCT03659916'],
    'odevixibat': ['NCT03659916'],
    'CHOLBAM': ['NCT01438411'],
    'cholic acid': ['NCT01438411'],
    'KEVEYIS': ['NCT02354339'],
    'dichlorphenamide': ['NCT02354339'],
    'FINTEPLA': ['NCT02682927', 'NCT02826863'],
    'fenfluramine': ['NCT02682927'],
    'EPIDIOLEX': ['NCT02091375', 'NCT02224690'],
    'cannabidiol': ['NCT02091375'],
    'DIACOMIT': ['NCT00490789'],
    'stiripentol': ['NCT00490789'],
    'ONTOZRY': ['NCT03650452'],
    'cenobamate': ['NCT03650452'],
    'XCOPRI': ['NCT01866111'],
    'FYCOMPA': ['NCT00699972', 'NCT00701102'],
    'perampanel': ['NCT00699972'],
    'BRIVIACT': ['NCT00490035'],
    'brivaracetam': ['NCT00490035'],
    'VIMPAT': ['NCT00136019'],
    'lacosamide': ['NCT00136019'],

    # Pain
    'OLINVYK': ['NCT02656875'],
    'oliceridine': ['NCT02656875'],
    'SEGLENTIS': ['NCT02920177'],
    'celecoxib/tramadol': ['NCT02920177'],
    'QUVIVIQ': ['NCT03545191'],
    'daridorexant': ['NCT03545191'],
    'DAYVIGO': ['NCT02783729'],
    'lemborexant': ['NCT02783729'],
    'BELSOMRA': ['NCT01021813'],
    'suvorexant': ['NCT01021813'],

    # Dermatology
    'EUCRISA': ['NCT02118766', 'NCT02118792'],
    'crisaborole': ['NCT02118766'],
    'ELIDEL': ['NCT00124267'],
    'pimecrolimus': ['NCT00124267'],
    'PROTOPIC': ['NCT00120510'],
    'tacrolimus': ['NCT00120510'],
    'ILUMYA': ['NCT02672852'],
    'tildrakizumab': ['NCT02672852'],
    'SILIQ': ['NCT01884557'],
    'brodalumab': ['NCT01884557'],
    'COSENTYX': ['NCT01365455', 'NCT01406938'],
    'secukinumab': ['NCT01365455'],
    'TALTZ': ['NCT01474512', 'NCT01597245'],
    'ixekizumab': ['NCT01474512'],
    'STELARA': ['NCT00267969'],
    'ustekinumab': ['NCT00267969'],

    # Cardiology
    'ENTRESTO': ['NCT01035255'],
    'CORLANOR': ['NCT00543855'],
    'ivabradine': ['NCT00543855'],
    'RANEXA': ['NCT00099788'],
    'ranolazine': ['NCT00099788'],
    'LIVALO': ['NCT00318058'],
    'pitavastatin': ['NCT00318058'],
    'NEXLETOL': ['NCT02993406'],
    'bempedoic': ['NCT02993406'],
    'NEXLIZET': ['NCT02988115'],

    # Diabetes
    'TZIELD': ['NCT03875729', 'NCT01030861'],
    'LANTIDRA': ['NCT00434811'],
    'LYUMJEV': ['NCT02961894'],
    'AFREZZA': ['NCT01445951'],
    'inhaled insulin': ['NCT01445951'],
    'TRESIBA': ['NCT01388361'],
    'degludec': ['NCT01388361'],
    'TOUJEO': ['NCT01499082'],
    'SOLIQUA': ['NCT02058160'],
    'XULTOPHY': ['NCT01952145'],
    'TRULICITY': ['NCT01394952', 'NCT01730534'],
    'dulaglutide': ['NCT01394952'],
    'VICTOZA': ['NCT00614120'],
    'liraglutide': ['NCT00614120'],
    'SAXENDA': ['NCT01272219'],
    'BYETTA': ['NCT00082407'],
    'exenatide': ['NCT00082407'],
    'BYDUREON': ['NCT00641056'],
    'ADLYXIN': ['NCT01175473'],
    'lixisenatide': ['NCT01175473'],
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if len(data.get('nct_ids', [])) > 0:
        continue

    drug = data.get('drug_name', '').upper()
    matched_ncts = []

    for key, ncts in nct_map.items():
        if key.upper() in drug:
            matched_ncts = ncts
            break

    if matched_ncts:
        data['nct_ids'] = matched_ncts
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'{data.get("ticker")}: {matched_ncts}')
        updated += 1

print(f'\nTotal updated: {updated}')
