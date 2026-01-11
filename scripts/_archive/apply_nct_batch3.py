"""NCT ID 추가 적용 스크립트 - 3차"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 추가 NCT ID 매핑 (남은 약물들)
nct_map = {
    # Specific remaining drugs
    'NUPLAZID': ['NCT01174004', 'NCT02035553'],
    'pimavanserin': ['NCT01174004'],
    'AMVUTTRA': ['NCT03759379'],
    'vutrisiran': ['NCT03759379'],
    'BLINCYTO': ['NCT02013167', 'NCT02393859'],
    'blinatumomab': ['NCT02013167'],
    'RIABNI': ['NCT02260804'],
    'rituximab': ['NCT02260804'],
    'REPATHA': ['NCT01764633', 'NCT02207634'],
    'evolocumab': ['NCT01764633'],
    'IMDELLTRA': ['NCT05060016'],
    'tarlatamab': ['NCT05060016'],
    'ONGENTYS': ['NCT01568073', 'NCT02847442'],
    'opicapone': ['NCT01568073'],
    'Oleogel': ['NCT02156531', 'NCT03068780'],
    'FILSUVEZ': ['NCT03068780'],
    'ZORYVE': ['NCT03638258', 'NCT03764475'],
    'roflumilast': ['NCT03638258'],
    'ARQ-151': ['NCT03638258'],
    'ARQ-154': ['NCT03764475'],
    'REDEMPLO': ['NCT05089084'],
    'plozasiran': ['NCT05089084'],
    'YORVIPATH': ['NCT04701203'],
    'palopegteriparatide': ['NCT04701203'],
    'TransCon': ['NCT03305016', 'NCT04085523'],
    'navepegritide': ['NCT04085523'],
    'QDOLO': ['NCT03804229'],
    'TASCENSO': ['NCT02932150'],
    'fingolimod': ['NCT02932150'],
    'CABTREO': ['NCT03564119'],
    'MIEBO': ['NCT05005559'],
    'perfluorohexyloctane': ['NCT05005559'],
    'VYGLXIA': ['NCT03701399'],
    'troriluzole': ['NCT03701399'],
    'TOFIDENCE': ['NCT03052621'],
    'EMRELIS': ['NCT02099058'],
    'telisotuzumab': ['NCT02099058'],
    'EMBLAVEO': ['NCT03329092'],
    'meropenem': ['NCT03329092'],

    # Biosimilars and generics
    'biosimilar': ['NCT02260804'],
    'BYOOVIZ': ['NCT02842190'],
    'CIMERLI': ['NCT02842190'],
    'YUSIMRY': ['NCT02480153'],
    'HADLIMA': ['NCT02480153'],
    'HYRIMOZ': ['NCT02480153'],
    'HULIO': ['NCT02480153'],
    'IDACIO': ['NCT02480153'],
    'adalimumab': ['NCT02480153'],

    # More specific drugs
    'REZLIDHIA': ['NCT02577406'],
    'olutasidenib': ['NCT02577406'],
    'KHAPZORY': ['NCT02500680'],
    'levoleucovorin': ['NCT02500680'],
    'TRUSELTIQ': ['NCT03052778'],
    'infigratinib': ['NCT03052778'],
    'UKONIQ': ['NCT02793583'],
    'umbralisib': ['NCT02793583'],
    'COPIKTRA': ['NCT02049515', 'NCT02004522'],
    'duvelisib': ['NCT02049515'],
    'MARGENZA': ['NCT02492711'],
    'margetuximab': ['NCT02492711'],
    'ENHERTU': ['NCT03248492', 'NCT03734029'],
    'trastuzumab deruxtecan': ['NCT03248492'],
    'PHESGO': ['NCT03493854'],
    'pertuzumab': ['NCT03493854'],
    'HERCEPTIN': ['NCT00688623'],
    'KANJINTI': ['NCT02472964'],
    'OGIVRI': ['NCT02472964'],
    'ONTRUZANT': ['NCT02472964'],
    'TRAZIMERA': ['NCT02472964'],
    'HERZUMA': ['NCT02472964'],

    # JAK inhibitors
    'CIBINQO': ['NCT03422822', 'NCT03627767'],
    'abrocitinib': ['NCT03422822'],
    'SOTYKTU': ['NCT04908202', 'NCT03611751'],

    # Cardiovascular
    'LEQVIO': ['NCT03399370', 'NCT03400800'],
    'VASCEPA': ['NCT01492361'],
    'icosapent': ['NCT01492361'],
    'OMTRYG': ['NCT01492361'],

    # Pain/Anesthesia
    'NERLYNX': ['NCT01808573', 'NCT02673398'],
    'neratinib': ['NCT01808573'],
    'EXPAREL': ['NCT01907100'],
    'bupivacaine': ['NCT01907100'],
    'ZYNRELEF': ['NCT03295721'],
    'ZILRETTA': ['NCT02116972'],
    'triamcinolone': ['NCT02116972'],

    # Anaphylx: ['NCT02592551'],
    'Anaphylm': ['NCT02592551'],
    'epinephrine': ['NCT02592551'],
    'AUVI-Q': ['NCT02592551'],
    'EPIPEN': ['NCT02592551'],
    'SYMJEPI': ['NCT02592551'],

    # Libervant
    'Libervant': ['NCT04205968'],
    'diazepam': ['NCT04205968'],

    # Avance
    'Avance': ['NCT02052778'],
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
