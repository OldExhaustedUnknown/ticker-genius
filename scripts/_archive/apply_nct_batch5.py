"""NCT ID 추가 적용 - 5차 (남은 약물들)"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

nct_map = {
    # From agent searches - Batch A
    'ADX-2191': ['NCT03413111'],
    'Reproxalap': ['NCT04712045'],
    'HEPLISAV': ['NCT02117934'],
    'TEMBEXA': ['NCT01769170'],
    'brincidofovir': ['NCT01769170'],
    'BARHEMSYS': ['NCT03265340'],
    'amisulpride': ['NCT03265340'],
    'BYFAVO': ['NCT03684278'],
    'remimazolam': ['NCT03684278'],
    'TAZVERIK': ['NCT02601950'],
    'tazemetostat': ['NCT02601950'],
    'ALKINDI': ['NCT02778542'],
    'WAKIX': ['NCT01067222', 'NCT01480596'],
    'pitolisant': ['NCT01067222'],
    'UPLIZNA': ['NCT02200770'],
    'inebilizumab': ['NCT02200770'],
    'Tebentafusp': ['NCT03070392'],
    'KIMMTRAK': ['NCT03070392'],
    'TRUDHESA': ['NCT03557333'],

    # Batch B
    'ANKTIVA': ['NCT03022825'],
    'N-803': ['NCT03022825'],
    'PEMAZYRE': ['NCT02924376'],
    'pemigatinib': ['NCT02924376'],
    'BRINSUPRI': ['NCT04594369'],
    'brensocatib': ['NCT04594369'],
    'XACDURO': ['NCT03894046'],
    'sulbactam': ['NCT03894046'],
    'TERLIVAZ': ['NCT02770716'],
    'terlipressin': ['NCT02770716'],
    'PREVYMIS': ['NCT02137772'],
    'letermovir': ['NCT02137772'],
    'LYFNUA': ['NCT03449134'],
    'gefapixant': ['NCT03449134'],
    'ENFLONSIA': ['NCT04767373'],
    'clesrovimab': ['NCT04767373'],
    'DIFICID': ['NCT00314951'],
    'fidaxomicin': ['NCT00314951'],
    'mRESVIA': ['NCT05127434'],
    'mRNA-1345': ['NCT05127434'],
    'Ganaxolone': ['NCT03572933'],
    'ZTALMY': ['NCT03572933'],
    'BIZENGRI': ['NCT02912949'],
    'zenocutuzumab': ['NCT02912949'],
    'MYFEMBREE': ['NCT03049735'],
    'relugolix': ['NCT03049735'],
    'OHTUVAYRE': ['NCT04542057', 'NCT04535986'],
    'ensifentrine': ['NCT04542057'],
    'RYSTIGGO': ['NCT03971422'],
    'rozanolixizumab': ['NCT03971422'],

    # Batch C
    'Leniolisib': ['NCT02435173'],
    'JOENJA': ['NCT02435173'],
    'VOQUEZNA': ['NCT03462849'],
    'vonoprazan': ['NCT03462849'],
    'Vatiquinone': ['NCT04577352'],
    'PTC743': ['NCT04577352'],
    'Omaveloxolone': ['NCT02255435'],
    'SKYCLARYS': ['NCT02255435'],
    'KRESLADI': ['NCT03882437'],
    'Odronextamab': ['NCT03888105'],
    'RP1': ['NCT03767348'],
    'vusolimogene': ['NCT03767348'],
    'UZEDY': ['NCT04010291'],
    'Veverimer': ['NCT03710291'],
    'EGRIFTA': ['NCT00391638'],
    'tesamorelin': ['NCT00391638'],
    'BIJUVA': ['NCT02323841'],
    'ZUSDURI': ['NCT05021718'],
    'OGSIVEO': ['NCT03785964'],
    'nirogacestat': ['NCT03785964'],
    'ORSERDU': ['NCT03778931'],
    'elacestrant': ['NCT03778931'],
    'EXXUA': ['NCT03347279'],
    'gepirone': ['NCT03347279'],

    # Batch D
    'NARCAN': ['NCT02289040'],
    'XYOSTED': ['NCT02159469'],
    'LOQTORZI': ['NCT02915432'],
    'toripalimab': ['NCT02915432'],
    'ZYNYZ': ['NCT03599713'],
    'retifanlimab': ['NCT03599713'],
    'WEZLANA': ['NCT03512613'],
    'PHELINUN': ['NCT02372643'],
    'ZILXI': ['NCT03276286'],
    'DNL310': ['NCT04251026'],
    'tividenofusp': ['NCT04251026'],
    'NIKTIMVO': ['NCT04710576'],
    'axatilimab': ['NCT04710576'],
    'Etripamil': ['NCT03464019'],
    'CARDAMYST': ['NCT03464019'],

    # Batch E
    'PONVORY': ['NCT02425644'],
    'ponesimod': ['NCT02425644'],
    'XYWAV': ['NCT03030599'],
    'IMVEXXY': ['NCT02253173'],
    'INTRAROSA': ['NCT02013544'],
    'prasterone': ['NCT02013544'],
    'VEOZAH': ['NCT04003155'],
    'fezolinetant': ['NCT04003155'],
    'WINLEVI': ['NCT02608450'],
    'clascoterone': ['NCT02608450'],
    'AKLIEF': ['NCT02491554'],
    'trifarotene': ['NCT02491554'],
    'AMZEEQ': ['NCT03145480'],
    'SEYSARA': ['NCT02320149'],
    'sarecycline': ['NCT02320149'],
    'EPSOLAY': ['NCT02809976'],
    'QBREXZA': ['NCT02553798'],
    'glycopyrronium': ['NCT02553798'],
    'BRYHALI': ['NCT02514577'],
    'DUOBRII': ['NCT02462070'],
    'ENSTILAR': ['NCT02132936'],

    # Batch F
    'REZDIFFRA': ['NCT03900429'],
    'resmetirom': ['NCT03900429'],
    'XERMELO': ['NCT01677910'],
    'telotristat': ['NCT01677910'],
    'NGENLA': ['NCT02968004'],
    'somatrogon': ['NCT02968004'],
    'SOGROYA': ['NCT02229851'],
    'somapacitan': ['NCT02229851'],
    'MYCAPSSA': ['NCT02685709'],
    'SIGNIFOR': ['NCT00600886'],
    'pasireotide': ['NCT00600886'],
    'BYNFEZIA': ['NCT03252353'],
    'INCRELEX': ['NCT00375622'],
    'mecasermin': ['NCT00375622'],
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
