"""NCT ID 추가 적용 스크립트 - 2차"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 추가 NCT ID 매핑
nct_map = {
    # More oncology drugs
    'VERZENIO': ['NCT02107703', 'NCT02246621'],
    'abemaciclib': ['NCT02107703'],
    'KISQALI': ['NCT01958021', 'NCT02278120'],
    'ribociclib': ['NCT01958021'],
    'IBRANCE': ['NCT01740427', 'NCT02028507'],
    'palbociclib': ['NCT01740427'],
    'XPOVIO': ['NCT02336815', 'NCT03110562'],
    'selinexor': ['NCT02336815'],
    'SARCLISA': ['NCT02990338', 'NCT03275285'],
    'isatuximab': ['NCT02990338'],
    'ZYNLONTA': ['NCT02669017'],
    'loncastuximab': ['NCT02669017'],
    'MONJUVI': ['NCT02399085'],
    'LIBTAYO': ['NCT02760498', 'NCT03088540'],
    'cemiplimab': ['NCT02760498'],
    'BAVENCIO': ['NCT02603432', 'NCT02952586'],
    'avelumab': ['NCT02603432'],
    'JEMPERLI': ['NCT03981796'],
    'dostarlimab': ['NCT03981796'],
    'TIVDAK': ['NCT03438396'],
    'tisotumab': ['NCT03438396'],
    'TRODELVY': ['NCT02574455', 'NCT03901339'],

    # Hematology
    'BESREMI': ['NCT02669849'],
    'ropeginterferon': ['NCT02669849'],
    'PYRUKYND': ['NCT03548220'],
    'ESPEROCT': ['NCT02957370'],
    'turoctocog': ['NCT02957370'],
    'HEMLIBRA': ['NCT02622321', 'NCT02795767'],
    'emicizumab': ['NCT02622321'],
    'ONPATTRO': ['NCT01960348', 'NCT02510261'],
    'patisiran': ['NCT01960348'],
    'GIVLAARI': ['NCT03338816'],
    'givosiran': ['NCT03338816'],
    'LEQVIO': ['NCT03399370', 'NCT03400800'],
    'inclisiran': ['NCT03399370'],

    # Neurology
    'SPINRAZA': ['NCT02193074'],
    'QALSODY': ['NCT02623699'],
    'tofersen': ['NCT02623699'],
    'RADICAVA': ['NCT01492686'],
    'edaravone': ['NCT01492686'],
    'NUEDEXTA': ['NCT00573443'],
    'VYEPTI': ['NCT02974153', 'NCT02559895'],
    'eptinezumab': ['NCT02974153'],
    'AJOVY': ['NCT02629861', 'NCT02621931'],
    'fremanezumab': ['NCT02629861'],
    'EMGALITY': ['NCT02614183', 'NCT02614196'],
    'galcanezumab': ['NCT02614183'],
    'AIMOVIG': ['NCT02456740', 'NCT02483585'],
    'erenumab': ['NCT02456740'],
    'NURTEC': ['NCT03461757', 'NCT03777059'],
    'rimegepant': ['NCT03461757'],
    'QULIPTA': ['NCT03700320', 'NCT04660071'],
    'atogepant': ['NCT03700320'],
    'UBRELVY': ['NCT02828020', 'NCT02867709'],
    'ubrogepant': ['NCT02828020'],
    'REYVOW': ['NCT02439320', 'NCT02605174'],
    'lasmiditan': ['NCT02439320'],

    # Ophthalmology
    'EYLEA': ['NCT00509795', 'NCT00637377'],
    'aflibercept': ['NCT00509795'],
    'BEOVU': ['NCT02307682', 'NCT02434328'],
    'brolucizumab': ['NCT02307682'],
    'VABYSMO': ['NCT03823287', 'NCT03622580'],
    'faricimab': ['NCT03823287'],
    'SUSVIMO': ['NCT03677934'],
    'LUCENTIS': ['NCT00056836'],
    'ranibizumab': ['NCT00056836'],
    'SYFOVRE': ['NCT03525613', 'NCT03525600'],

    # Dermatology
    'OPZELURA': ['NCT03745638', 'NCT03745651'],
    'ruxolitinib': ['NCT03745638'],
    'LIVTENCITY': ['NCT02931539', 'NCT02927067'],
    'maribavir': ['NCT02931539'],
    'VTAMA': ['NCT03956355'],
    'tapinarof': ['NCT03956355'],
    'ARAZLO': ['NCT03168321'],
    'tazarotene': ['NCT03168321'],

    # Respiratory
    'TEZSPIRE': ['NCT02528214', 'NCT03347279'],
    'tezepelumab': ['NCT02528214'],
    'NUCALA': ['NCT01691508', 'NCT01691521'],
    'mepolizumab': ['NCT01691508'],
    'FASENRA': ['NCT02075255', 'NCT02258542'],
    'benralizumab': ['NCT02075255'],
    'XOLAIR': ['NCT00314574'],
    'omalizumab': ['NCT00314574'],
    'CINQAIR': ['NCT01287039', 'NCT01285323'],
    'reslizumab': ['NCT01287039'],
    'TRELEGY': ['NCT02345161', 'NCT02164513'],

    # Gastroenterology
    'LINZESS': ['NCT01880424', 'NCT01714310'],
    'linaclotide': ['NCT01880424'],
    'TRULANCE': ['NCT02609814'],
    'plecanatide': ['NCT02609814'],
    'MOTEGRITY': ['NCT02425774', 'NCT02493647'],
    'prucalopride': ['NCT02425774'],
    'IBSRELA': ['NCT02493869', 'NCT02621892'],
    'tenapanor': ['NCT02493869'],
    'XPHOZAH': ['NCT03675100'],

    # Endocrine
    'THYROGEN': ['NCT00117767'],
    'KRYSTEXXA': ['NCT00325195'],
    'pegloticase': ['NCT00325195'],

    # Rare diseases
    'GALAFOLD': ['NCT01218659'],
    'migalastat': ['NCT01218659'],
    'DOJOLVI': ['NCT03021526'],
    'triheptanoin': ['NCT03021526'],
    'XENPOZYME': ['NCT02004704'],
    'olipudase': ['NCT02004704'],
    'MEPSEVII': ['NCT01856218'],
    'vestronidase': ['NCT01856218'],
    'BRINEURA': ['NCT01907087'],
    'cerliponase': ['NCT01907087'],
    'KANUMA': ['NCT01371825'],
    'sebelipase': ['NCT01371825'],
    'NEXVIAZYME': ['NCT02782741'],
    'avalglucosidase': ['NCT02782741'],
    'FABRAZYME': ['NCT00074984'],
    'agalsidase': ['NCT00074984'],
    'CERDELGA': ['NCT00358150'],
    'eliglustat': ['NCT00358150'],
    'LAMZEDE': ['NCT01681953'],
    'velmanase': ['NCT01681953'],
    'RETHYMIC': ['NCT01319812'],
    'PALYNZIQ': ['NCT01819727', 'NCT01889862'],
    'pegvaliase': ['NCT01819727'],

    # Vaccines/Immunology
    'PREVNAR': ['NCT00427895'],
    'SHINGRIX': ['NCT01165177', 'NCT01165229'],
    'AREXVY': ['NCT04886596'],
    'ABRYSVO': ['NCT04424316'],
    'VAXNEUVANCE': ['NCT03950622'],
    'BEYFORTUS': ['NCT03979313'],
    'nirsevimab': ['NCT03979313'],

    # Anti-infectives
    'CABENUVA': ['NCT02938520', 'NCT02951052'],
    'cabotegravir': ['NCT02938520'],
    'RUKOBIA': ['NCT02362503'],
    'fostemsavir': ['NCT02362503'],
    'BIKTARVY': ['NCT02607930', 'NCT02607956'],
    'DESCOVY': ['NCT02842086'],
    'DOVATO': ['NCT03299049', 'NCT02946957'],
    'JULUCA': ['NCT02429791'],
    'PAXLOVID': ['NCT04960202'],
    'nirmatrelvir': ['NCT04960202'],
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
