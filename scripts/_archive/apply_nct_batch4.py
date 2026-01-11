"""NCT ID 추가 적용 스크립트 - 4차 (희귀질환/유전자치료)"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

nct_map = {
    # Gene therapies
    'CASGEVY': ['NCT03745287', 'NCT04208529'],
    'exa-cel': ['NCT03745287'],
    'QARZIBA': ['NCT02743429'],
    'dinutuximab': ['NCT02743429'],
    'UNITUXIN': ['NCT00026312'],
    'DANYELZA': ['NCT03363373'],
    'naxitamab': ['NCT03363373'],
    'ADSTILADRIN': ['NCT02773849'],
    'nadofaragene': ['NCT02773849'],
    'ELZONRIS': ['NCT02113982'],
    'tagraxofusp': ['NCT02113982'],
    'LUMOXITI': ['NCT01829711'],
    'moxetumomab': ['NCT01829711'],
    'POLATUZUMAB': ['NCT02257567'],
    'BESPONSA': ['NCT01564784'],
    'inotuzumab': ['NCT01564784'],
    'MYLOTARG': ['NCT00091234'],
    'gemtuzumab': ['NCT00091234'],

    # DMD therapies
    'CASIMERSEN': ['NCT03532542'],
    'AMONDYS': ['NCT03532542'],
    'EXONDYS': ['NCT02255552'],
    'eteplirsen': ['NCT02255552'],
    'VILTEPSO': ['NCT02740972'],
    'viltolarsen': ['NCT02740972'],
    'AGAMREE': ['NCT03439670'],
    'vamorolone': ['NCT03439670'],
    'DUVYZAT': ['NCT02851797'],
    'givinostat': ['NCT02851797'],
    'ELADOCAGENE': ['NCT02926066'],
    'UPSTAZA': ['NCT02926066'],

    # HIV
    'VOCABRIA': ['NCT02938520'],
    'APRETUDE': ['NCT04994509'],
    'cabotegravir': ['NCT02938520'],

    # More oncology
    'VITRAKVI': ['NCT02122913', 'NCT02576431'],
    'larotrectinib': ['NCT02122913'],
    'ROZLYTREK': ['NCT02568267'],
    'entrectinib': ['NCT02568267'],
    'ALUNBRIG': ['NCT02737501'],
    'brigatinib': ['NCT02737501'],
    'LORBRENA': ['NCT03052608'],
    'lorlatinib': ['NCT03052608'],
    'XALKORI': ['NCT00932893'],
    'crizotinib': ['NCT00932893'],
    'ZYKADIA': ['NCT01685060'],
    'ceritinib': ['NCT01685060'],
    'ALECENSA': ['NCT02075840'],
    'alectinib': ['NCT02075840'],
    'CYRAMZA': ['NCT01170663'],
    'ramucirumab': ['NCT01170663'],
    'STIVARGA': ['NCT01103323'],
    'regorafenib': ['NCT01103323'],
    'COMETRIQ': ['NCT00704730'],
    'BRUKINSA': ['NCT03053440'],
    'zanubrutinib': ['NCT03053440'],

    # Immunology additions
    'PRALUENT': ['NCT01507831'],
    'alirocumab': ['NCT01507831'],
    'EVENITY': ['NCT01631214', 'NCT01575834'],
    'romosozumab': ['NCT01631214'],
    'PROLIA': ['NCT00089791'],
    'denosumab': ['NCT00089791'],
    'XGEVA': ['NCT00330759'],

    # Neurology additions
    'TAKHZYRO': ['NCT02586805'],
    'lanadelumab': ['NCT02586805'],
    'HAEGARDA': ['NCT01912456'],
    'CINRYZE': ['NCT00438815'],
    'BERINERT': ['NCT00262301'],
    'RUCONEST': ['NCT00561314'],
    'FIRAZYR': ['NCT00912093'],
    'icatibant': ['NCT00912093'],

    # Ophthalmology
    'EYLEA HD': ['NCT04429503'],
    'VABYSMO': ['NCT03823287', 'NCT03622580'],
    'faricimab': ['NCT03823287'],
    'SUSVIMO': ['NCT03677934'],
    'BYOOVIZ': ['NCT02842190'],
    'CIMERLI': ['NCT02842190'],

    # Endocrine
    'RECORLEV': ['NCT03621143'],
    'levoketoconazole': ['NCT03621143'],
    'ISTURISA': ['NCT02180217'],
    'osilodrostat': ['NCT02180217'],
    'KORLYM': ['NCT00569582'],
    'mifepristone': ['NCT00569582'],

    # Respiratory
    'WINREVAIR': ['NCT04576988'],
    'sotatercept': ['NCT04576988'],
    'TYVASO DPI': ['NCT02664558'],
    'TYVASO': ['NCT00848315'],
    'treprostinil': ['NCT00848315'],
    'UPTRAVI': ['NCT01106014'],
    'selexipag': ['NCT01106014'],
    'ORENITRAM': ['NCT02344576'],
    'REMODULIN': ['NCT00293137'],
    'ADEMPAS': ['NCT00810693', 'NCT01392339'],
    'riociguat': ['NCT00810693'],
    'OPSUMIT': ['NCT00660179'],
    'macitentan': ['NCT00660179'],
    'TRACLEER': ['NCT00153400'],
    'bosentan': ['NCT00153400'],
    'LETAIRIS': ['NCT00091442'],
    'ambrisentan': ['NCT00091442'],
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
