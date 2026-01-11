"""Final mapping pass for remaining generic_name and therapeutic_area."""
import json
import os
from datetime import datetime

enriched_dir = 'data/enriched'
files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

# Final batch of brand to generic mappings
BRAND_TO_GENERIC_FINAL = {
    'EMRELIS': 'elritrecetam',
    'ORIAHNN': 'elagolix/estradiol/norethindrone',
    'OLPRUVA': 'sodium phenylbutyrate',
    'ACER-001': 'sodium phenylbutyrate',
    'ZUNVEYL': 'apomorphine',
    'AFAMI-CEL': 'afamitresgene autoleucel',
    'MITAPIVAT': 'mitapivat',
    'VAFSEO': 'vadadustat',
    'VADADUSTAT': 'vadadustat',
    'REPROXALAP': 'reproxalap',
    'AMVUTTRA': 'vutrisiran',
    'VUTRISIRAN': 'vutrisiran',
    'OXLUMO': 'lumasiran',
    'LUMASIRAN': 'lumasiran',
    'ONPATTRO': 'patisiran',
    'PATISIRAN': 'patisiran',
    'AVT05': 'aflibercept biosimilar',
    'BLINCYTO': 'blinatumomab',
    'REPATHA': 'evolocumab',
    'AMX0035': 'sodium phenylbutyrate/taurursodiol',
    'REXTOVY': 'naloxone',
    'ONGENTYS': 'opicapone',
    'OZILTUS': 'omeprazole/sodium bicarbonate',
    'CREXONT': 'carbidopa/levodopa',
    'BONCRESA': 'denosumab-bbdz',
    'BREKIYA': 'bevacizumab biosimilar',
    'OLEOGEL-S10': 'birch bark extract',
    'GOVORESTAT': 'govorestat',
    'YORVIPATH': 'palopegteriparatide',
    'TRANSCON HGH': 'lonapegsomatropin',
    'SKYTROFA': 'lonapegsomatropin',
    'NAVEPEGRITIDE': 'navepegritide',
    'QDOLO': 'tramadol',
    'PACLITAXEL': 'paclitaxel',
    'TRAMADOL': 'tramadol',
    'AVANCE': 'processed nerve allograft',
    'SYMBRAVO': 'meloxicam/rizatriptan',
    'AXS-07': 'meloxicam/rizatriptan',
    'AIRSUPRA': 'albuterol/budesonide',
    'SYMBICORT': 'budesonide/formoterol',
    'BREZTRI': 'budesonide/glycopyrrolate/formoterol',
    'PANTOPRAZOLE': 'pantoprazole',
    'EPINEPHRINE': 'epinephrine',
    'ACORAMIDIS': 'acoramidis',
    'PROCYSBI': 'cysteamine',
    'TASCENSO': 'fingolimod',
    'AMELUZ': 'aminolevulinic acid',
    'CABTREO': 'clobetasol/halobetasol',
    'ATROPINE': 'atropine',
    'LECANEMAB': 'lecanemab',
    'FLUORESCEIN': 'fluorescein/benoxinate',
    'BETI-CEL': 'betibeglogene autotemcel',
    'VOXZOGO': 'vosoritide',
    'REPOTRECTINIB': 'repotrectinib',
    'ZEPOSIA': 'ozanimod',
    'ONUREG': 'azacitidine',
    'AVAPRITINIB': 'avapritinib',
    'AURLUMYN': 'iloprost',
    'BXCL501': 'dexmedetomidine',
    'ANJESO': 'meloxicam',
    'PLINABULIN': 'plinabulin',
    'NEFECON': 'budesonide',
    'DERAMIOCEL': 'deramiocel',
    'CAP-1002': 'deramiocel',
    'AVACOPAN': 'avacopan',
    'REZAFUNGIN': 'rezafungin',
    'CHS-201': 'pegfilgrastim biosimilar',
    'TORIPALIMAB': 'toripalimab',
    'RUBRACA': 'rucaparib',
    'RELACORILANT': 'relacorilant',
    'VAMOROLONE': 'vamorolone',
    'FIRDAPSE': 'amifampridine',
    'PACRITINIB': 'pacritinib',
    'I/ONTAK': 'denileukin diftitox',
    'E7777': 'denileukin diftitox',
    'LYMPHIR': 'denileukin diftitox',
    'QWO': 'collagenase clostridium histolyticum',
    'OMECAMTIV': 'omecamtiv mecarbil',
    'HEPZATO': 'melphalan',
    'DFD-29': 'minocycline',
    'TIVIDENOFUSP': 'tividenofusp alfa',
    'DNL310': 'tividenofusp alfa',
    'VASOPRESSIN': 'vasopressin',
    'RYANODEX': 'dantrolene',
    'KANGIO': 'bivalirudin',
    'BIVALIRUDIN': 'bivalirudin',
    'ZONISAMIDE': 'zonisamide',
    'ALKINDI': 'hydrocortisone',
    'TOPIRAMATE': 'topiramate',
    'PEMFEXY': 'pemetrexed',
    'MYDCOMBI': 'tropicamide/phenylephrine',
    'MICROSTAT': 'tropicamide/phenylephrine',
    'CUTX-101': 'copper histidinate',
    'ROXADUSTAT': 'roxadustat',
    'AT-GAA': 'cipaglucosidase alfa/miglustat',
    'CERIANNA': 'fluoroestradiol F 18',
    'LENACAPAVIR': 'lenacapavir',
    'FILGOTINIB': 'filgotinib',
    'EPIOXA': 'epinastine',
    'TABELECLEUCEL': 'tabelecleucel',
    'SPINRAZA': 'nusinersen',
    'OPDIVO': 'nivolumab',
    'YERVOY': 'ipilimumab',
    'HETLIOZ': 'tasimelteon',
    'DCCR': 'diazoxide choline',
    'VICINEUM': 'oportuzumab monatox',
    'APITEGROMAB': 'apitegromab',
    'SRK-015': 'apitegromab',
    'VEVERIMER': 'veverimer',
    'IBREXAFUNGERP': 'ibrexafungerp',
    'TEPLIZUMAB': 'teplizumab',
    'TZIELD': 'teplizumab',
    'KRYSTEXXA': 'pegloticase',
    'UPNEEQ': 'oxymetazoline',
    'DAXXIFY': 'daxibotulinumtoxinA',
    'DAXIBOTULINUM': 'daxibotulinumtoxinA',
    'BREXAFEMME': 'ibrexafungerp',
    'FEXINIDAZOLE': 'fexinidazole',
    'XHANCE': 'fluticasone propionate',
    'JELMYTO': 'mitomycin',
    'LENIOLISIB': 'leniolisib',
    'YARTEMLEA': 'narsoplimab',
    'NARSOPLIMAB': 'narsoplimab',
    'NITROGEN': 'nitrogen',
    'OXYGEN': 'oxygen',
    'SYMVESS': 'human acellular vessel',
    'ATEV': 'human acellular vessel',
    'AVASOPASEM': 'avasopasem manganese',
    'LEQVIO': 'inclisiran',
    'PLUVICTO': 'lutetium Lu 177 vipivotide tetraxetan',
    'RHAPSIDO': 'remibrutinib',
    'GEFAPIXANT': 'gefapixant',
    'LYFNUA': 'gefapixant',
    'PREVYMIS': 'letermovir',
    'CTEXLI': 'chenodiol',
    'EKTERLY': 'sebetralstat',
    'PALOPEGTERIPARATIDE': 'palopegteriparatide',
}

# Therapeutic area mapping for specific indications
INDICATION_TO_TA = {
    'opioid overdose': 'Emergency Medicine',
    'opioid': 'Emergency Medicine',
    'naloxone': 'Emergency Medicine',
    'contraception': "Women's Health",
    'contraceptive': "Women's Health",
    'designated medical gas': 'Respiratory',
    'hyperoxaluria': 'Nephrology',
    'anca': 'Immunology/Rheumatology',
    'vasculitis': 'Immunology/Rheumatology',
    'hypercholesterolemia': 'Cardiovascular',
    'ldl': 'Cardiovascular',
    'cholesterol': 'Cardiovascular',
    'lipid': 'Cardiovascular',
    'sclc': 'Oncology',
    'osteoporosis': 'Metabolic/Endocrine',
    'myasthenia gravis': 'Neurology',
    'myasthenic': 'Neurology',
    'galactosemia': 'Rare/Genetic Disease',
    'sord deficiency': 'Rare/Genetic Disease',
    'fcs': 'Rare/Genetic Disease',
    'chylomicronemia': 'Rare/Genetic Disease',
    'achondroplasia': 'Rare/Genetic Disease',
    'ebv': 'Oncology',
    'lymphoproliferative': 'Oncology',
    'nerve repair': 'Surgery',
    'peripheral nerve': 'Neurology',
    'nf1': 'Oncology',
    'neurofibromas': 'Oncology',
    'hae': 'Immunology/Rheumatology',
    'hereditary angioedema': 'Immunology/Rheumatology',
    'relapsing ms': 'Neurology',
    'actinic keratosis': 'Dermatology',
    'bcc': 'Dermatology',
    'basal cell': 'Dermatology',
    'bradycardia': 'Cardiovascular',
    'anticholinergic': 'Anesthesiology/Pain',
    'biosimilar': 'Various',
    'adrenoleukodystrophy': 'Rare/Genetic Disease',
    'hcc': 'Oncology',
    'crc': 'Oncology',
    'frostbite': 'Emergency Medicine',
    'candidemia': 'Infectious Disease',
    'candidiasis': 'Infectious Disease',
    'candida': 'Infectious Disease',
    'lems': 'Neurology',
    'lambert-eaton': 'Neurology',
    'vasodilatory shock': 'Critical Care',
    'hefh': 'Cardiovascular',
    'ascvd': 'Cardiovascular',
    'on-demand': "Women's Health",
    'rcc': 'Oncology',
    'renal cell': 'Oncology',
    'pupil': 'Ophthalmology',
    'mydriasis': 'Ophthalmology',
    'menkes': 'Rare/Genetic Disease',
    'ototoxicity': 'Oncology',
    'cisplatin': 'Oncology',
    'pbc': 'Gastroenterology',
    'biliary cholangitis': 'Gastroenterology',
    'radiotherapy': 'Oncology',
    'oral mucositis': 'Oncology',
    'vulvovaginal': 'Infectious Disease',
    'nmosd': 'Neurology',
    'gout': 'Immunology/Rheumatology',
    'bcg': 'Oncology',
    'nmibc': 'Oncology',
    'bladder cancer': 'Oncology',
    'tnbc': 'Oncology',
    'triple negative': 'Oncology',
    'habp': 'Infectious Disease',
    'vabp': 'Infectious Disease',
    'acinetobacter': 'Infectious Disease',
    'cmv': 'Infectious Disease',
    'cytomegalovirus': 'Infectious Disease',
    'transplant': 'Transplant Medicine',
    'chronic cough': 'Respiratory',
    'psma': 'Oncology',
    'mcrpc': 'Oncology',
    'prostate': 'Oncology',
    'cml': 'Oncology',
    'urticaria': 'Dermatology',
    'hives': 'Dermatology',
    'tma': 'Hematology',
    'hsct': 'Hematology',
    'nasal polyps': 'Respiratory',
    'crs': 'Immunology/Rheumatology',
    'mld': 'Rare/Genetic Disease',
    'metachromatic': 'Rare/Genetic Disease',
    'braf': 'Oncology',
    'mcrc': 'Oncology',
    'papillomatosis': 'Infectious Disease',
    'apds': 'Rare/Genetic Disease',
    't1d': 'Metabolic/Endocrine',
    'type 1 diabetes': 'Metabolic/Endocrine',
    'lad-i': 'Rare/Genetic Disease',
    'leukocyte adhesion': 'Rare/Genetic Disease',
    'blepharoptosis': 'Ophthalmology',
    'glabellar': 'Dermatology',
    'frown lines': 'Dermatology',
    'prader-willi': 'Rare/Genetic Disease',
    'trypanosomiasis': 'Infectious Disease',
    'sma': 'Neurology',
    'spinal muscular': 'Neurology',
    'menopausal': "Women's Health",
    'vasomotor': "Women's Health",
    'utuc': 'Oncology',
    'non-24': 'Neurology',
    'sleep-wake': 'Neurology',
    'ctx': 'Rare/Genetic Disease',
    'cerebrotendinous': 'Rare/Genetic Disease',
    'extremity': 'Vascular Surgery',
    'vascular trauma': 'Vascular Surgery',
}

def get_therapeutic_area_final(indication):
    if not indication:
        return None
    indication_lower = indication.lower()
    for keyword, area in INDICATION_TO_TA.items():
        if keyword in indication_lower:
            return area
    return None

def extract_generic_from_name(drug_name):
    """Try to extract generic name from drug name."""
    if not drug_name:
        return None

    # Check mapping first
    name_upper = drug_name.upper()
    for brand, generic in BRAND_TO_GENERIC_FINAL.items():
        if brand in name_upper:
            return generic

    # Pattern matching for generic names in parentheses
    import re
    paren_match = re.search(r'\(([a-z][a-z\-\s]+)\)', drug_name.lower())
    if paren_match:
        return paren_match.group(1).strip()

    # If drug name starts with lowercase, it's likely generic
    if drug_name and drug_name[0].islower():
        words = drug_name.split()
        generic_parts = []
        for w in words:
            if w[0].islower() or w.lower() in ['alfa', 'beta', 'pegol', 'sodium', 'hcl', 'hydrochloride']:
                generic_parts.append(w.lower())
            else:
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
        generic = extract_generic_from_name(drug_name)

        if generic:
            event['generic_name'] = {
                'status': 'found',
                'value': generic,
                'source': 'final_mapping',
                'confidence': 0.8,
                'evidence': [f'From {drug_name}'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True

    # 2. Therapeutic area
    if event.get('therapeutic_area', {}).get('status') == 'not_searched':
        indication = event.get('indication', {}).get('value', '')
        ta = get_therapeutic_area_final(indication)

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

print(f'Updated {updated} files with final mappings')
