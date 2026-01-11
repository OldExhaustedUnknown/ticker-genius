"""NCT ID 일괄 적용 스크립트"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 포괄적인 NCT ID 매핑
nct_map = {
    # Batch 1-2 drugs
    'ORIAHNN': ['NCT02655419', 'NCT02654054'],
    'elagolix': ['NCT02654054'],
    'ZEVASKYN': ['NCT04227106'],
    'prademagene': ['NCT04227106'],
    'OLPRUVA': ['NCT04534530'],
    'ACER-001': ['NCT04534530'],
    'ZUNVEYL': ['NCT00594568'],
    'ZIMHI': ['NCT02438436'],
    'TWIRLA': ['NCT01955902', 'NCT02059551'],
    'LYBALVI': ['NCT02694328', 'NCT02469155'],
    'RELYVRIO': ['NCT03127514'],
    'AMX0035': ['NCT03127514'],
    'tabelecleucel': ['NCT03392142'],
    'AXS-07': ['NCT04163185'],
    'SYMBRAVO': ['NCT04163185'],
    'AIRSUPRA': ['NCT03769090'],
    'BREZTRI': ['NCT03197818', 'NCT02465567'],
    'Calquence': ['NCT02029443', 'NCT02477696'],
    'acalabrutinib': ['NCT02029443'],
    'PROCYSBI': ['NCT01744782'],
    'ORLADEYO': ['NCT03485911', 'NCT03235024'],
    'berotralstat': ['NCT03485911'],
    'Ameluz': ['NCT01966120'],
    'TEVIMBRA': ['NCT03783442', 'NCT03412773'],
    'tislelizumab': ['NCT03783442'],

    # Batch 3 drugs
    'Rubraca': ['NCT01891344', 'NCT01968382'],
    'rucaparib': ['NCT01891344'],
    'Relacorilant': ['NCT03697109'],
    'Vamorolone': ['NCT03439670'],
    'FIRDAPSE': ['NCT01377922'],
    'amifampridine': ['NCT01377922'],
    'DefenCath': ['NCT01558505', 'NCT01816776'],
    'PALSONIFY': ['NCT03789656', 'NCT05318456'],
    'paltusotine': ['NCT03789656'],
    'Pacritinib': ['NCT02055781', 'NCT03165734'],
    'LYMPHIR': ['NCT00003209'],
    'denileukin': ['NCT00003209'],
    'MYQORZO': ['NCT05186818', 'NCT06081894'],
    'aficamten': ['NCT05186818'],
    'omecamtiv': ['NCT02929329'],

    # Batch 4 drugs
    'RYTELO': ['NCT02598661'],
    'imetelstat': ['NCT02598661'],
    'Trodelvy': ['NCT02574455', 'NCT03901339'],
    'sacituzumab': ['NCT02574455'],
    'Lenacapavir': ['NCT04150068', 'NCT04143594'],
    'SUNLENCA': ['NCT04150068'],
    'Livdelzi': ['NCT03602560', 'NCT04620733'],
    'seladelpar': ['NCT03602560'],
    'YEZTUGO': ['NCT04443907'],
    'exagamglogene': ['NCT04443907'],
    'Filgotinib': ['NCT02889796', 'NCT02873936'],
    'VEKLURY': ['NCT04280705', 'NCT04292899'],
    'remdesivir': ['NCT04280705'],
    'iDose': ['NCT03868124'],
    'Omidubicel': ['NCT02730299'],
    'NiCord': ['NCT02730299'],
    'Elafibranor': ['NCT04526665'],
    'Avasopasem': ['NCT03689712'],

    # Batch 5 drugs
    'Pegunigalsidase': ['NCT03018730'],
    'VYJUVEK': ['NCT03536143'],
    'beremagene': ['NCT03536143'],
    'IMCIVREE': ['NCT03013543'],
    'setmelanotide': ['NCT03013543'],
    'IZERVAY': ['NCT04435366', 'NCT04566445'],
    'avacincaptad': ['NCT04435366'],
    'TEPEZZA': ['NCT01868997', 'NCT03298867'],
    'teprotumumab': ['NCT01868997'],
    'CABLIVI': ['NCT02553317'],
    'caplacizumab': ['NCT02553317'],
    'FILSPARI': ['NCT03762850'],
    'sparsentan': ['NCT03762850'],
    'INQOVI': ['NCT03306264'],
    'INREBIC': ['NCT01523171', 'NCT02101268'],
    'fedratinib': ['NCT01523171'],
    'IQIRVO': ['NCT04526665'],
    'EXKIVITY': ['NCT02716116'],
    'mobocertinib': ['NCT02716116'],

    # Batch 6 drugs
    'SPRAVATO': ['NCT02417064', 'NCT02493868'],
    'esketamine': ['NCT02417064'],
    'RYBREVANT': ['NCT02609776', 'NCT04538664'],
    'amivantamab': ['NCT02609776'],
    'DARZALEX': ['NCT02076009', 'NCT02136134'],
    'daratumumab': ['NCT02076009'],
    'ERLEADA': ['NCT01946204', 'NCT02489318'],
    'apalutamide': ['NCT01946204'],
    'BALVERSA': ['NCT02365597', 'NCT03390504'],
    'erdafitinib': ['NCT02365597'],
    'RYBELSUS': ['NCT02906930', 'NCT02863328'],
    'REZUROCK': ['NCT03474679'],
    'belumosudil': ['NCT03474679'],
    'KRAZATI': ['NCT03785249'],
    'adagrasib': ['NCT03785249'],
    'LUMAKRAS': ['NCT03600883', 'NCT04303780'],
    'sotorasib': ['NCT03600883'],
    'MINJUVI': ['NCT02399085'],
    'tafasitamab': ['NCT02399085'],
    'PEPAXTO': ['NCT03151811'],

    # Batch 7 drugs
    'INGREZZA': ['NCT02274558', 'NCT02405091'],
    'valbenazine': ['NCT02274558'],
    'AUSTEDO': ['NCT01795859', 'NCT02291861'],
    'deutetrabenazine': ['NCT01795859'],
    'ELAHERE': ['NCT04209855'],
    'mirvetuximab': ['NCT04209855'],
    'TIBSOVO': ['NCT02074839', 'NCT03173248'],
    'ivosidenib': ['NCT02074839'],
    'WELIREG': ['NCT02974738', 'NCT04195750'],
    'belzutifan': ['NCT02974738'],
    'QINLOCK': ['NCT03353753'],
    'ripretinib': ['NCT03353753'],
    'AYVAKIT': ['NCT02508532', 'NCT03731260'],
    'avapritinib': ['NCT02508532'],
    'GAVRETO': ['NCT03037385'],
    'pralsetinib': ['NCT03037385'],
    'RETEVMO': ['NCT03157128', 'NCT03899792'],
    'selpercatinib': ['NCT03157128'],
    'TABRECTA': ['NCT02414139', 'NCT02750215'],
    'capmatinib': ['NCT02414139'],
    'TUKYSA': ['NCT02614794'],
    'tucatinib': ['NCT02614794'],

    # Batch 8 drugs
    'COSELA': ['NCT02514447', 'NCT03041311'],
    'trilaciclib': ['NCT02514447'],
    'BLENREP': ['NCT03525678'],
    'belantamab': ['NCT03525678'],
    'LYTGOBI': ['NCT02052778'],
    'futibatinib': ['NCT02052778'],
    'XTANDI': ['NCT00974311', 'NCT01212991'],
    'enzalutamide': ['NCT00974311'],
    'NUBEQA': ['NCT02200614', 'NCT02799602'],
    'darolutamide': ['NCT02200614'],
    'ZEPZELCA': ['NCT02454972'],
    'lurbinectedin': ['NCT02454972'],
    'FOTIVDA': ['NCT01030783', 'NCT02627963'],
    'tivozanib': ['NCT01030783'],
    'CABOMETYX': ['NCT01865747', 'NCT03141177'],
    'cabozantinib': ['NCT01865747'],
    'LENVIMA': ['NCT01321554', 'NCT02702401'],
    'lenvatinib': ['NCT01321554'],
    'OPDUALAG': ['NCT03470922'],
    'relatlimab': ['NCT03470922'],

    # Additional common drugs
    'TRODELVY': ['NCT02574455', 'NCT03901339'],
    'KEYTRUDA': ['NCT02362594'],
    'OPDIVO': ['NCT02066636'],
    'YERVOY': ['NCT00324155'],
    'ipilimumab': ['NCT00324155'],
    'IMBRUVICA': ['NCT01236391', 'NCT02264574'],
    'ibrutinib': ['NCT01236391'],
    'VENCLEXTA': ['NCT02756611', 'NCT02242942'],
    'venetoclax': ['NCT02756611'],
    'TAGRISSO': ['NCT02296125', 'NCT02474355'],
    'osimertinib': ['NCT02296125'],
    'LORBRENA': ['NCT03052608'],
    'lorlatinib': ['NCT03052608'],
    'ALUNBRIG': ['NCT02737501'],
    'brigatinib': ['NCT02737501'],
    'ROZLYTREK': ['NCT02568267'],
    'entrectinib': ['NCT02568267'],
    'VITRAKVI': ['NCT02122913', 'NCT02576431'],
    'larotrectinib': ['NCT02122913'],
    'BRUKINSA': ['NCT03053440', 'NCT03734016'],
    'zanubrutinib': ['NCT03053440'],
    'CALQUENCE': ['NCT02029443'],
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
