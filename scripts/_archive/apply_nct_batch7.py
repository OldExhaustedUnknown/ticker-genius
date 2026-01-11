"""NCT ID 최종 배치 적용 - 7차"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

nct_map = {
    # Remaining specific drugs
    'APHEXDA': ['NCT03395977'],  # motixafortide
    'motixafortide': ['NCT03395977'],
    'VOXZOGO': ['NCT03197766'],
    'vosoritide': ['NCT03197766'],
    'Repotrectinib': ['NCT03093116'],
    'AUGTYRO': ['NCT03093116'],
    'ONUREG': ['NCT01757535'],
    'azacitidine': ['NCT01757535'],
    'ELIQUIS': ['NCT00412984'],
    'apixaban': ['NCT00412984'],
    'AURLUMYN': ['NCT03005587'],
    'IGALMI': ['NCT03829748'],
    'BXCL501': ['NCT03829748'],
    'dexmedetomidine': ['NCT03829748'],
    'ANJESO': ['NCT02977689'],
    'meloxicam': ['NCT02977689'],
    'Plinabulin': ['NCT02504489'],
    'Nefecon': ['NCT03643965'],
    'TARPEYO': ['NCT03643965'],
    'Deramiocel': ['NCT04229758'],
    'CAP-1002': ['NCT04229758'],
    'Rezafungin': ['NCT03667690'],
    'REZZAYO': ['NCT03667690'],
    'UDENYCA': ['NCT02491866'],
    'pegfilgrastim': ['NCT02491866'],
    'CHS-1420': ['NCT03210259'],
    'UNLOXCYT': ['NCT03620123'],
    'cosibelimab': ['NCT03620123'],
    'XIPERE': ['NCT02595398'],
    'triamcinolone': ['NCT02595398'],
    'Modeyso': ['NCT04556669'],
    'dordaviprone': ['NCT04556669'],
    'QWO': ['NCT03529786'],
    'collagenase': ['NCT03529786'],
    'XACIATO': ['NCT03541681'],
    'clindamycin': ['NCT03541681'],
    'OJEMDA': ['NCT04775485'],
    'tovorafenib': ['NCT04775485'],
    'Hepzato': ['NCT02953457'],
    'CYFENDUS': ['NCT03877926'],
    'AV7909': ['NCT03877926'],
    'Vasopressin': ['NCT02855736'],
    'RYANODEX': ['NCT01547026'],
    'dantrolene': ['NCT01547026'],
    'Bivalirudin': ['NCT00786474'],
    'Zonisamide': ['NCT00190801'],
    'Topiramate': ['NCT00210392'],
    'PHEXXI': ['NCT03243305'],
    'Govorestat': ['NCT03787186'],

    # More oncology
    'PADCEV': ['NCT03474107'],
    'enfortumab': ['NCT03474107'],
    'TALVEY': ['NCT03399799'],
    'talquetamab': ['NCT03399799'],

    # More rare disease
    'LAMZEDE': ['NCT01681953'],
    'velmanase': ['NCT01681953'],
    'MEPSEVII': ['NCT01856218'],
    'vestronidase': ['NCT01856218'],
    'BRINEURA': ['NCT01907087'],
    'cerliponase': ['NCT01907087'],

    # Dermatology
    'VTAMA': ['NCT03956355'],
    'tapinarof': ['NCT03956355'],

    # Additional
    'FYARRO': ['NCT03439150'],
    'sirolimus': ['NCT03439150'],
    'STIMUFEND': ['NCT02472236'],
    'NYVEPRIA': ['NCT02472236'],
    'RELEUKO': ['NCT03195010'],
    'filgrastim': ['NCT03195010'],
    'GRANIX': ['NCT00838370'],
    'ZIEXTENZO': ['NCT02472236'],
    'FYLNETRA': ['NCT02472236'],
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
