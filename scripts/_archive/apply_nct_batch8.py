"""NCT ID 최종 배치 - 8차"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

nct_map = {
    # Remaining drugs
    'GIMOTI': ['NCT02624947'],
    'metoclopramide': ['NCT02624947'],
    'PEMFEXY': ['NCT03272503'],
    'MydCombi': ['NCT04393376'],
    'CUTX-101': ['NCT03029429'],
    'EYSUVIS': ['NCT03616899'],
    'loteprednol': ['NCT03616899'],
    'PEDMARK': ['NCT01947907'],
    'sodium thiosulfate': ['NCT01947907'],
    'Roxadustat': ['NCT02174627'],
    'AT-GAA': ['NCT03729362'],
    'cipaglucosidase': ['NCT03729362'],
    'CERIANNA': ['NCT02455453'],
    'fluoroestradiol': ['NCT02455453'],
    'Epioxa': ['NCT03442751'],
    'Daprodustat': ['NCT02879305'],
    'JESDUVROQ': ['NCT02879305'],
    'Linerixibat': ['NCT04167358'],
    'BREXAFEMME': ['NCT03734991'],
    'ibrexafungerp': ['NCT03734991'],
    'ZEJULA': ['NCT01847274'],
    'niraparib': ['NCT01847274'],
    'Penmenvy': ['NCT03698162'],
    'TRIUMEQ': ['NCT02096210'],
    'Gepotidacin': ['NCT04020341'],
    'Blujepa': ['NCT04020341'],
    'Depemokimab': ['NCT04718389'],
    'EXDENSUR': ['NCT04382040'],
    'Surufatinib': ['NCT02549937'],
    'FRUZAQLA': ['NCT04322539'],
    'fruquintinib': ['NCT04322539'],
    'NUZOLVENCE': ['NCT03959527'],
    'zoliflodacin': ['NCT03959527'],
    'TRYNGOLZA': ['NCT05079919'],
    'Eplontersen': ['NCT04136171'],
    'olezarsen': ['NCT05079919'],
    'DAWNZERA': ['NCT05120375'],
    'donidalorsen': ['NCT05120375'],
    'AMTAGVI': ['NCT03645928'],
    'Lifileucel': ['NCT03645928'],
    'Caplyta': ['NCT02600065'],
    'lumateperone': ['NCT02600065'],
    'ORLYNVAH': ['NCT03354598'],
    'Sulopenem': ['NCT03354598'],
    'ZIIHERA': ['NCT03929666'],
    'Zanidatamab': ['NCT03929666'],
    'IMAAVY': ['NCT03761303'],
    'EKTERLY': ['NCT04618497'],
    'sebetralstat': ['NCT04618497'],
    'KOMZIFTI': ['NCT04959526'],
    'ziftomenib': ['NCT04959526'],
    'VIZZ': ['NCT05401435'],
    'aceclidine': ['NCT05401435'],
    'Omvoh': ['NCT03518086'],
    'mirikizumab': ['NCT03518086'],
    'Kisunla': ['NCT03367403'],
    'donanemab': ['NCT03367403'],

    # More remaining
    'LOQTORZI': ['NCT02915432'],
    'toripalimab': ['NCT02915432'],
    'WINLEVI': ['NCT02608450'],
    'clascoterone': ['NCT02608450'],
    'RYZNEUTA': ['NCT04755582'],
    'efbemalenograstim': ['NCT04755582'],
    'AUCAZYL': ['NCT04374526'],
    'obecabtagene': ['NCT04374526'],
    'obe-cel': ['NCT04374526'],
    'LETYBO': ['NCT04048590'],
    'letibotulinumtoxin': ['NCT04048590'],
    'WELIREG': ['NCT02974738'],
    'belzutifan': ['NCT02974738'],
    'OJJAARA': ['NCT03662126'],
    'momelotinib': ['NCT03662126'],
    'TALZENNA': ['NCT02034916'],
    'talazoparib': ['NCT02034916'],
    'LITFULO': ['NCT03732807'],
    'ritlecitinib': ['NCT03732807'],
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
