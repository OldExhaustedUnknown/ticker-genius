"""Expanded mapping for generic_name and therapeutic_area."""
import json
import os
import re
from datetime import datetime

enriched_dir = 'data/enriched'
files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

# Expanded brand to generic mapping
BRAND_TO_GENERIC = {
    # Gene/Cell therapies (keep as-is or extract from name)
    'ZEVASKYN': 'prademagene zamikeracel',
    'ELEVIDYS': 'delandistrogene moxeparvovec',
    'CASGEVY': 'exagamglogene autotemcel',
    'HEMGENIX': 'etranacogene dezaparvovec',
    'BEQVEZ': 'fidanacogene elaparvovec',
    'ZOLGENSMA': 'onasemnogene abeparvovec',
    'LUXTURNA': 'voretigene neparvovec',
    'ROCTAVIAN': 'valoctocogene roxaparvovec',
    'SKYSONA': 'elivaldogene autotemcel',
    'LYFGENIA': 'lovotibeglogene autotemcel',
    'ABECMA': 'idecabtagene vicleucel',
    'CARVYKTI': 'ciltacabtagene autoleucel',
    'BREYANZI': 'lisocabtagene maraleucel',
    'YESCARTA': 'axicabtagene ciloleucel',
    'KYMRIAH': 'tisagenlecleucel',
    'TECARTUS': 'brexucabtagene autoleucel',
    'AUCATZYL': 'obecabtagene autoleucel',
    'AMTAGVI': 'lifileucel',
    'LENMELDY': 'atidarsagene autotemcel',
    'KRESLADI': 'marnetegragene autotemcel',

    # Oncology
    'PYRUKYND': 'mitapivat',
    'VORANIGO': 'vorasidenib',
    'KOSELUGO': 'selumetinib',
    'IMDELLTRA': 'tarlatamab',
    'TEVIMBRA': 'tislelizumab',
    'OJEMDA': 'tovorafenib',
    'KOMZIFTI': 'ziftomenib',
    'AUGTYRO': 'repotrectinib',
    'IBTROZI': 'taletrectinib',
    'BIZENGRI': 'zenocutuzumab',
    'ZIIHERA': 'zanidatamab',
    'DANYELZA': 'naxitamab',
    'MARGENZA': 'margetuximab',
    'ORSERDU': 'elacestrant',
    'ZYNYZ': 'retifanlimab',
    'RYTELO': 'imetelstat',
    'ZEPZELCA': 'lurbinectedin',
    'UNLOXCYT': 'cosibelimab',
    'TAZVERIK': 'tazemetostat',
    'PEMAZYRE': 'pemigatinib',
    'NIKTIMVO': 'axatilimab',
    'EPKINLY': 'epcoritamab',
    'ELREXFIO': 'elranatamab',
    'SCEMBLIX': 'asciminib',
    'PLUVICTO': 'lutetium Lu 177 vipivotide tetraxetan',
    'VIJOICE': 'alpelisib',
    'TABRECTA': 'capmatinib',
    'TAFINLAR': 'dabrafenib',
    'MEKINIST': 'trametinib',
    'RETEVMO': 'selpercatinib',
    'LITFULO': 'ritlecitinib',
    'WINREVAIR': 'sotatercept',
    'KEYTRUDA': 'pembrolizumab',
    'OPDIVO': 'nivolumab',
    'BLENREP': 'belantamab mafodotin',
    'SARCLISA': 'isatuximab',
    'IMBRUVICA': 'ibrutinib',
    'TUKYSA': 'tucatinib',
    'PADCEV': 'enfortumab vedotin',
    'TIVDAK': 'tisotumab vedotin',
    'TRODELVY': 'sacituzumab govitecan',
    'ELAHERE': 'mirvetuximab soravtansine',
    'AYVAKIT': 'avapritinib',
    'GAVRETO': 'pralsetinib',
    'QINLOCK': 'ripretinib',
    'LUMAKRAS': 'sotorasib',
    'KRAZATI': 'adagrasib',
    'WELIREG': 'belzutifan',
    'REVUFORJ': 'revumenib',
    'GOMEKLI': 'mirdametinib',
    'FAKZYNJA': 'avutometinib/defactinib',
    'AVMAPKI': 'avutometinib/defactinib',

    # Neurology/Psychiatry
    'NUPLAZID': 'pimavanserin',
    'DAYBUE': 'trofinetide',
    'CAPLYTA': 'lumateperone',
    'COBENFY': 'xanomeline/trospium',
    'FINTEPLA': 'fenfluramine',
    'ZTALMY': 'ganaxolone',
    'QELBREE': 'viloxazine',
    'WAKIX': 'pitolisant',
    'XYWAV': 'calcium/magnesium/potassium/sodium oxybates',
    'LUMRYZ': 'sodium oxybate',
    'INGREZZA': 'valbenazine',
    'IGALMI': 'dexmedetomidine',
    'ZURANOLONE': 'zuranolone',
    'SKYCLARYS': 'omaveloxolone',
    'RELYVRIO': 'sodium phenylbutyrate/taurursodiol',
    'QALSODY': 'tofersen',
    'VYGLXIA': 'troriluzole',
    'TONMYA': 'cyclobenzaprine',
    'VYONDYS': 'golodirsen',
    'AMONDYS': 'casimersen',

    # Cardiovascular
    'CAMZYOS': 'mavacamten',
    'ENTRESTO': 'sacubitril/valsartan',
    'VERQUVO': 'vericiguat',
    'ELIQUIS': 'apixaban',
    'MYQORZO': 'omecamtiv mecarbil',
    'EKTERLY': 'sebetralstat',
    'CARDAMYST': 'etripamil',
    'FUROSCIX': 'furosemide',

    # Immunology/Rheumatology
    'DUPIXENT': 'dupilumab',
    'RINVOQ': 'upadacitinib',
    'XELJANZ': 'tofacitinib',
    'OPZELURA': 'ruxolitinib',
    'SOTYKTU': 'deucravacitinib',
    'SKYRIZI': 'risankizumab',
    'TREMFYA': 'guselkumab',
    'COSENTYX': 'secukinumab',
    'TALTZ': 'ixekizumab',
    'NUCALA': 'mepolizumab',
    'FASENRA': 'benralizumab',
    'TEZSPIRE': 'tezepelumab',
    'ENTYVIO': 'vedolizumab',
    'TAVNEOS': 'avacopan',
    'UPLIZNA': 'inebilizumab',
    'SAPHNELO': 'anifrolumab',
    'VYVGART': 'efgartigimod',
    'BRINSUPRI': 'brensocatib',
    'DAWNZERA': 'donidalorsen',

    # Rare/Genetic Disease
    'VOYDEYA': 'danicopan',
    'ELFABRIO': 'pegunigalsidase alfa',
    'REZDIFFRA': 'resmetirom',
    'LIVMARLI': 'maralixibat',
    'TARPEYO': 'budesonide',
    'FILSPARI': 'sparsentan',
    'XPHOZAH': 'tenapanor',
    'ALYFTREK': 'vanzacaftor/tezacaftor/deutivacaftor',
    'TRIKAFTA': 'elexacaftor/tezacaftor/ivacaftor',
    'KALYDECO': 'ivacaftor',
    'RYONCIL': 'remestemcel-L',
    'APHEXDA': 'motixafortide',
    'CRENESSITY': 'crinecerfont',
    'PALSONIFY': 'paltusotine',
    'MIPLYFFI': 'arimoclomol',
    'PAPZIMEOS': 'zopapogene imadenovec',

    # Infectious Disease
    'BIKTARVY': 'bictegravir/emtricitabine/tenofovir alafenamide',
    'DOVATO': 'dolutegravir/lamivudine',
    'CABENUVA': 'cabotegravir/rilpivirine',
    'VOCABRIA': 'cabotegravir',
    'RUKOBIA': 'fostemsavir',
    'SUNLENCA': 'lenacapavir',
    'YEZTUGO': 'lenacapavir',
    'VEKLURY': 'remdesivir',
    'PAXLOVID': 'nirmatrelvir/ritonavir',
    'HEPLISAV': 'hepatitis B vaccine',
    'ABRYSVO': 'respiratory syncytial virus vaccine',
    'PREVNAR': 'pneumococcal vaccine',
    'PENBRAYA': 'meningococcal vaccine',
    'CAPVAXIVE': 'pneumococcal 21-valent conjugate vaccine',
    'mRESVIA': 'respiratory syncytial virus vaccine mRNA',
    'IXCHIQ': 'chikungunya vaccine',
    'ENFLONSIA': 'clesrovimab',
    'NIRSEVIMAB': 'nirsevimab',
    'BEYFORTUS': 'nirsevimab',
    'TEMBEXA': 'brincidofovir',
    'CYFENDUS': 'anthrax vaccine adsorbed',
    'BLUJEPA': 'gepotidacin',
    'XACDURO': 'sulbactam/durlobactam',
    'NUZOLVENCE': 'zoliflodacin',
    'FRUZAQLA': 'fruquintinib',

    # Ophthalmology
    'DURYSTA': 'bimatoprost',
    'VUITY': 'pilocarpine',
    'SYFOVRE': 'pegcetacoplan',
    'IZERVAY': 'avacincaptad pegol',
    'DEXTENZA': 'dexamethasone',
    'EYSUVIS': 'loteprednol etabonate',
    'XIPERE': 'triamcinolone acetonide',
    'XDEMVY': 'lotilaner',
    'MIEBO': 'perfluorohexyloctane',
    'VIZZ': 'aceclidine',

    # Dermatology
    'VTAMA': 'tapinarof',
    'ZORYVE': 'roflumilast',
    'ZILXI': 'minocycline',
    'BIMZELX': 'bimekizumab',
    'DAXXIFY': 'daxibotulinumtoxinA',
    'LETYBO': 'letibotulinumtoxinA',

    # GI
    'VOQUEZNA': 'vonoprazan',
    'LIVDELZI': 'seladelpar',
    'OCALIVA': 'obeticholic acid',
    'TERLIVAZ': 'terlipressin',
    'XIFAXAN': 'rifaximin',
    'PHEXXI': 'lactic acid/citric acid/potassium bitartrate',
    'GIMOTI': 'metoclopramide',
    'VOWST': 'fecal microbiota',

    # Pain/Anesthesia
    'ZYNRELEF': 'bupivacaine/meloxicam',
    'BARHEMSYS': 'amisulpride',
    'BYFAVO': 'remimazolam',
    'OLINVYK': 'oliceridine',
    'JOURNAVX': 'suzetrigine',
    'ELYXYB': 'celecoxib',
    'NURTEC': 'rimegepant',
    'TRUDHESA': 'dihydroergotamine',
    'NEFFY': 'epinephrine',
    'NARCAN': 'naloxone',
    'ZIMHI': 'naloxone',

    # Hematology
    'REBLOZYL': 'luspatercept',
    'ROLONTIS': 'eflapegrastim',
    'UDENYCA': 'pegfilgrastim',
    'NYVEPRIA': 'pegfilgrastim',
    'HYMPAVZI': 'marstacimab',
    'ALHEMO': 'concizumab',
    'QFITLIA': 'fitusiran',
    'TRYNGOLZA': 'olezarsen',

    # Other
    'TWIRLA': 'levonorgestrel/ethinyl estradiol',
    'BIJUVA': 'estradiol/progesterone',
    'MYFEMBREE': 'relugolix/estradiol/norethindrone',
    'ORLADEYO': 'berotralstat',
    'TEPEZZA': 'teprotumumab',
    'ANKTIVA': 'nogapendekin alfa inbakicept',
    'XOLREMDI': 'mavorixafor',
    'LEQVIO': 'inclisiran',
    'NEXLETOL': 'bempedoic acid',
    'NEXLIZET': 'bempedoic acid/ezetimibe',
    'ENSIFENTRINE': 'ensifentrine',
    'YUTREPIA': 'treprostinil',
    'IMCIVREE': 'setmelanotide',
    'RECORLEV': 'levoketoconazole',
    'ONAPGO': 'apomorphine',
    'PEDMARK': 'sodium thiosulfate',
    'DEFENCATH': 'taurolidine/citrate',
    'TLANDO': 'testosterone undecanoate',
    'UPNEEQ': 'oxymetazoline',
    'REDEMPLO': 'plozasiran',

    # Generics/Biosimilars
    'SEMGLEE': 'insulin glargine-yfgn',
    'HULIO': 'adalimumab-fkjp',
    'RIABNI': 'rituximab-arrx',
    'TOFIDENCE': 'tocilizumab-bavi',
    'HADLIMA': 'adalimumab-bwwd',
    'CIMERLI': 'ranibizumab-eqrn',
    'YUSIMRY': 'adalimumab-aqvh',
    'WYOST': 'denosumab-bbdz',
    'ENZEEVU': 'ranibizumab',
}

# Additional therapeutic area keywords
THERAPEUTIC_AREA_MAP = {
    'aml': 'Oncology',
    'cll': 'Oncology',
    'dlbcl': 'Oncology',
    'mantle cell': 'Oncology',
    'follicular': 'Oncology',
    'marginal zone': 'Oncology',
    'waldenstrom': 'Oncology',
    't-cell': 'Oncology',
    'b-cell': 'Oncology',
    'car-t': 'Oncology',
    'solid tumor': 'Oncology',
    'metastatic': 'Oncology',
    'advanced': 'Oncology',
    'unresectable': 'Oncology',
    'kras': 'Oncology',
    'egfr': 'Oncology',
    'alk': 'Oncology',
    'ret': 'Oncology',
    'ntrk': 'Oncology',
    'her2': 'Oncology',
    'flt3': 'Oncology',
    'idh': 'Oncology',

    'mds': 'Hematology',
    'myelodysplastic': 'Hematology',
    'iron overload': 'Hematology',
    'blood': 'Hematology',
    'bleeding': 'Hematology',
    'clotting': 'Hematology',
    'platelet': 'Hematology',

    'vaccine': 'Infectious Disease',
    'viral': 'Infectious Disease',
    'flu': 'Infectious Disease',
    'pneumococcal': 'Infectious Disease',
    'meningitis': 'Infectious Disease',
    'sepsis': 'Infectious Disease',
    'septic': 'Infectious Disease',

    'gene therapy': 'Rare/Genetic Disease',
    'cell therapy': 'Rare/Genetic Disease',
    'enzyme replacement': 'Rare/Genetic Disease',
    'lysosomal': 'Rare/Genetic Disease',
    'mitochondrial': 'Rare/Genetic Disease',
    'metabolism': 'Metabolic/Endocrine',

    'inflammatory': 'Immunology/Rheumatology',
    'autoimmune': 'Immunology/Rheumatology',
    'immune': 'Immunology/Rheumatology',

    'retina': 'Ophthalmology',
    'cornea': 'Ophthalmology',
    'amd': 'Ophthalmology',
    'ga ': 'Ophthalmology',

    'nausea': 'Gastroenterology',
    'vomiting': 'Gastroenterology',
    'ponv': 'Anesthesiology/Pain',
    'cinv': 'Oncology',

    'burn': 'Dermatology',
    'scar': 'Dermatology',

    'anxiety': 'Psychiatry',
    'panic': 'Psychiatry',
    'ptsd': 'Psychiatry',
    'ocd': 'Psychiatry',

    'cataplexy': 'Neurology',
    'spasticity': 'Neurology',
    'movement disorder': 'Neurology',
    'chorea': 'Neurology',

    'pcos': 'Metabolic/Endocrine',
    'hormone': 'Metabolic/Endocrine',

    'cystinosis': 'Rare/Genetic Disease',
    'porphyria': 'Rare/Genetic Disease',
    'urea cycle': 'Rare/Genetic Disease',
}

def get_therapeutic_area(indication):
    if not indication:
        return None
    indication_lower = indication.lower()
    for keyword, area in THERAPEUTIC_AREA_MAP.items():
        if keyword in indication_lower:
            return area
    return None

def extract_generic_from_drug_name(drug_name):
    """Extract generic name from drug name if it contains both brand and generic."""
    if not drug_name:
        return None

    # Pattern: BRAND generic or BRAND (generic)
    # Look for lowercase words that might be generic name
    parts = drug_name.split()
    for i, part in enumerate(parts):
        # If this part is lowercase and has > 5 chars, might be generic
        if part[0].islower() and len(part) > 5:
            # Return this and following lowercase parts
            generic_parts = []
            for p in parts[i:]:
                if p[0].islower() or p.lower() in ['alfa', 'beta', 'pegol']:
                    generic_parts.append(p)
                elif generic_parts:
                    break
            if generic_parts:
                return ' '.join(generic_parts)

    return None

updated = 0
for filename in files:
    filepath = os.path.join(enriched_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        event = json.load(f)

    modified = False
    now = datetime.now().isoformat()

    # 1. Generic name
    if event.get('generic_name', {}).get('status') == 'not_searched':
        drug_name = event.get('drug_name', '')
        generic = None
        source = None

        # First check brand to generic map
        drug_upper = drug_name.upper()
        for brand, gen in BRAND_TO_GENERIC.items():
            if brand in drug_upper:
                generic = gen
                source = 'brand_to_generic_map'
                break

        # If not found, try to extract from drug name
        if not generic:
            generic = extract_generic_from_drug_name(drug_name)
            if generic:
                source = 'extracted_from_drug_name'

        # If still not found, check if drug name itself is generic
        if not generic and drug_name and drug_name[0].islower():
            generic = drug_name.split()[0].lower()  # Take first word
            source = 'drug_name_is_generic'

        if generic:
            event['generic_name'] = {
                'status': 'found',
                'value': generic,
                'source': source,
                'confidence': 0.85 if source == 'brand_to_generic_map' else 0.7,
                'evidence': [f'From {drug_name}'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True

    # 2. Therapeutic area
    if event.get('therapeutic_area', {}).get('status') == 'not_searched':
        indication = event.get('indication', {}).get('value', '')
        ta = get_therapeutic_area(indication)
        if ta:
            event['therapeutic_area'] = {
                'status': 'found',
                'value': ta,
                'source': 'derived_from_indication',
                'confidence': 0.85,
                'evidence': [f'Derived from indication: {indication}'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
        updated += 1

print(f'Updated {updated} files with expanded mappings')
