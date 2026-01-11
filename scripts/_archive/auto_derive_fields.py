"""Auto-derive fields from existing data."""
import json
import os
from datetime import datetime

enriched_dir = 'data/enriched'
files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

# Therapeutic area mapping from indication keywords
THERAPEUTIC_AREA_MAP = {
    'cancer': 'Oncology',
    'tumor': 'Oncology',
    'carcinoma': 'Oncology',
    'lymphoma': 'Oncology',
    'leukemia': 'Oncology',
    'melanoma': 'Oncology',
    'sarcoma': 'Oncology',
    'myeloma': 'Oncology',
    'glioma': 'Oncology',
    'neuroblastoma': 'Oncology',
    'nsclc': 'Oncology',
    'lung': 'Oncology',
    'breast': 'Oncology',
    'prostate': 'Oncology',
    'ovarian': 'Oncology',
    'colorectal': 'Oncology',
    'hepatocellular': 'Oncology',
    'cholangiocarcinoma': 'Oncology',
    'gist': 'Oncology',
    'bladder': 'Oncology',
    'renal cell': 'Oncology',
    'mesothelioma': 'Oncology',
    'gastric': 'Oncology',
    'esophageal': 'Oncology',
    'pancreatic': 'Oncology',
    'thyroid cancer': 'Oncology',
    'head and neck': 'Oncology',

    'diabetes': 'Metabolic/Endocrine',
    'obesity': 'Metabolic/Endocrine',
    'weight': 'Metabolic/Endocrine',
    'thyroid': 'Metabolic/Endocrine',
    'adrenal': 'Metabolic/Endocrine',
    'cushing': 'Metabolic/Endocrine',
    'acromegaly': 'Metabolic/Endocrine',
    'growth hormone': 'Metabolic/Endocrine',
    'lipodystrophy': 'Metabolic/Endocrine',

    'heart': 'Cardiovascular',
    'cardiac': 'Cardiovascular',
    'hypertension': 'Cardiovascular',
    'atrial fibrillation': 'Cardiovascular',
    'heart failure': 'Cardiovascular',
    'pulmonary arterial hypertension': 'Cardiovascular',
    'pah': 'Cardiovascular',
    'cardiomyopathy': 'Cardiovascular',
    'anticoagul': 'Cardiovascular',
    'thrombosis': 'Cardiovascular',
    'angioedema': 'Cardiovascular',
    'psvt': 'Cardiovascular',
    'svt': 'Cardiovascular',

    'alzheimer': 'Neurology',
    'parkinson': 'Neurology',
    'epilepsy': 'Neurology',
    'seizure': 'Neurology',
    'migraine': 'Neurology',
    'multiple sclerosis': 'Neurology',
    'als': 'Neurology',
    'huntington': 'Neurology',
    'neuropathy': 'Neurology',
    'stroke': 'Neurology',
    'tardive dyskinesia': 'Neurology',
    'dystonia': 'Neurology',
    'ataxia': 'Neurology',

    'schizophrenia': 'Psychiatry',
    'depression': 'Psychiatry',
    'bipolar': 'Psychiatry',
    'anxiety': 'Psychiatry',
    'adhd': 'Psychiatry',
    'insomnia': 'Psychiatry',
    'narcolepsy': 'Psychiatry',
    'agitation': 'Psychiatry',

    'hiv': 'Infectious Disease',
    'hepatitis': 'Infectious Disease',
    'covid': 'Infectious Disease',
    'rsv': 'Infectious Disease',
    'influenza': 'Infectious Disease',
    'pneumonia': 'Infectious Disease',
    'bacterial': 'Infectious Disease',
    'fungal': 'Infectious Disease',
    'antifungal': 'Infectious Disease',
    'antibiotic': 'Infectious Disease',
    'infection': 'Infectious Disease',
    'meningococcal': 'Infectious Disease',
    'vaccine': 'Infectious Disease',
    'smallpox': 'Infectious Disease',
    'anthrax': 'Infectious Disease',
    'cdiff': 'Infectious Disease',
    'c. diff': 'Infectious Disease',
    'clostridioides': 'Infectious Disease',
    'uti': 'Infectious Disease',
    'urinary tract': 'Infectious Disease',
    'gonorrhea': 'Infectious Disease',

    'rheumatoid': 'Immunology/Rheumatology',
    'lupus': 'Immunology/Rheumatology',
    'psoriasis': 'Immunology/Rheumatology',
    'psoriatic': 'Immunology/Rheumatology',
    'crohn': 'Immunology/Rheumatology',
    'ulcerative colitis': 'Immunology/Rheumatology',
    'atopic dermatitis': 'Immunology/Rheumatology',
    'eczema': 'Immunology/Rheumatology',
    'gvhd': 'Immunology/Rheumatology',
    'asthma': 'Immunology/Rheumatology',
    'copd': 'Immunology/Rheumatology',
    'bronchiectasis': 'Immunology/Rheumatology',
    'eosinophilic': 'Immunology/Rheumatology',

    'hemophilia': 'Hematology',
    'anemia': 'Hematology',
    'sickle cell': 'Hematology',
    'thalassemia': 'Hematology',
    'neutropenia': 'Hematology',
    'thrombocytopenia': 'Hematology',
    'myelofibrosis': 'Hematology',
    'polycythemia': 'Hematology',
    'mds': 'Hematology',
    'myelodysplastic': 'Hematology',

    'fabry': 'Rare/Genetic Disease',
    'gaucher': 'Rare/Genetic Disease',
    'pompe': 'Rare/Genetic Disease',
    'duchenne': 'Rare/Genetic Disease',
    'dmd': 'Rare/Genetic Disease',
    'spinal muscular': 'Rare/Genetic Disease',
    'cystic fibrosis': 'Rare/Genetic Disease',
    'pku': 'Rare/Genetic Disease',
    'mps': 'Rare/Genetic Disease',
    'batten': 'Rare/Genetic Disease',
    'niemann': 'Rare/Genetic Disease',
    'wilson': 'Rare/Genetic Disease',
    'amyloidosis': 'Rare/Genetic Disease',
    'attr': 'Rare/Genetic Disease',
    'hereditary': 'Rare/Genetic Disease',
    'epidermolysis': 'Rare/Genetic Disease',
    'eb ': 'Rare/Genetic Disease',
    'progeria': 'Rare/Genetic Disease',
    'friedreich': 'Rare/Genetic Disease',
    'leigh syndrome': 'Rare/Genetic Disease',
    'vhl': 'Rare/Genetic Disease',
    'von hippel': 'Rare/Genetic Disease',
    'pnh': 'Rare/Genetic Disease',
    'paroxysmal nocturnal': 'Rare/Genetic Disease',
    'cah': 'Rare/Genetic Disease',
    'congenital adrenal': 'Rare/Genetic Disease',

    'glaucoma': 'Ophthalmology',
    'macular': 'Ophthalmology',
    'retinal': 'Ophthalmology',
    'dry eye': 'Ophthalmology',
    'uveitis': 'Ophthalmology',
    'presbyopia': 'Ophthalmology',
    'myopia': 'Ophthalmology',
    'eye': 'Ophthalmology',
    'ophthalmic': 'Ophthalmology',
    'geographic atrophy': 'Ophthalmology',
    'demodex': 'Ophthalmology',
    'blepharitis': 'Ophthalmology',

    'dermat': 'Dermatology',
    'acne': 'Dermatology',
    'rosacea': 'Dermatology',
    'alopecia': 'Dermatology',
    'vitiligo': 'Dermatology',
    'pruritus': 'Dermatology',
    'skin': 'Dermatology',
    'wound': 'Dermatology',
    'cellulite': 'Dermatology',
    'plaque': 'Dermatology',
    'molluscum': 'Dermatology',
    'wart': 'Dermatology',

    'gerd': 'Gastroenterology',
    'ibs': 'Gastroenterology',
    'constipation': 'Gastroenterology',
    'nausea': 'Gastroenterology',
    'liver': 'Gastroenterology',
    'nash': 'Gastroenterology',
    'pbc': 'Gastroenterology',
    'esophagitis': 'Gastroenterology',
    'gastroparesis': 'Gastroenterology',
    'cholestasis': 'Gastroenterology',
    'bile': 'Gastroenterology',
    'hepatorenal': 'Gastroenterology',

    'kidney': 'Nephrology',
    'renal': 'Nephrology',
    'dialysis': 'Nephrology',
    'iga nephropathy': 'Nephrology',
    'fsgs': 'Nephrology',
    'alport': 'Nephrology',

    'pain': 'Anesthesiology/Pain',
    'anesthesia': 'Anesthesiology/Pain',
    'sedation': 'Anesthesiology/Pain',
    'analges': 'Anesthesiology/Pain',
    'postoperative': 'Anesthesiology/Pain',
    'fibromyalgia': 'Anesthesiology/Pain',

    'allergy': 'Allergy',
    'anaphylaxis': 'Allergy',
    'allergic': 'Allergy',

    'hypogonadism': 'Urology',
    'testosterone': 'Urology',
    'bph': 'Urology',
    'overactive bladder': 'Urology',
    'incontinence': 'Urology',

    'menopause': 'Women\'s Health',
    'endometriosis': 'Women\'s Health',
    'uterine': 'Women\'s Health',
    'contraceptive': 'Women\'s Health',
    'vaginosis': 'Women\'s Health',
}

def get_therapeutic_area(indication):
    if not indication:
        return None
    indication_lower = indication.lower()
    for keyword, area in THERAPEUTIC_AREA_MAP.items():
        if keyword in indication_lower:
            return area
    return None

# Known generic names for common brand drugs
BRAND_TO_GENERIC = {
    'DURYSTA': 'bimatoprost',
    'VUITY': 'pilocarpine',
    'EMBLAVEO': 'lotiglipron',
    'NUPLAZID': 'pimavanserin',
    'DAYBUE': 'trofinetide',
    'ZIMHI': 'naloxone',
    'XACIATO': 'clindamycin',
    'WAKIX': 'pitolisant',
    'TEPEZZA': 'teprotumumab',
    'UPLIZNA': 'inebilizumab',
    'DARZALEX': 'daratumumab',
    'RYBREVANT': 'amivantamab',
    'IMAAVY': 'talquetamab',
    'KEYTRUDA': 'pembrolizumab',
    'OPDIVO': 'nivolumab',
    'YERVOY': 'ipilimumab',
    'TECENTRIQ': 'atezolizumab',
    'IMBRUVICA': 'ibrutinib',
    'CALQUENCE': 'acalabrutinib',
    'BRUKINSA': 'zanubrutinib',
    'VENCLEXTA': 'venetoclax',
    'POLIVY': 'polatuzumab vedotin',
    'PADCEV': 'enfortumab vedotin',
    'TIVDAK': 'tisotumab vedotin',
    'ADCETRIS': 'brentuximab vedotin',
    'ENHERTU': 'trastuzumab deruxtecan',
    'TRODELVY': 'sacituzumab govitecan',
    'ELAHERE': 'mirvetuximab soravtansine',
    'TUKYSA': 'tucatinib',
    'AYVAKIT': 'avapritinib',
    'GAVRETO': 'pralsetinib',
    'RETEVMO': 'selpercatinib',
    'TABRECTA': 'capmatinib',
    'TAGRISSO': 'osimertinib',
    'LUMAKRAS': 'sotorasib',
    'KRAZATI': 'adagrasib',
    'INGREZZA': 'valbenazine',
    'AUSTEDO': 'deutetrabenazine',
    'CAPLYTA': 'lumateperone',
    'LYBALVI': 'olanzapine/samidorphan',
    'COBENFY': 'xanomeline/trospium',
    'FINTEPLA': 'fenfluramine',
    'EPIDIOLEX': 'cannabidiol',
    'ZTALMY': 'ganaxolone',
    'QELBREE': 'viloxazine',
    'SUNOSI': 'solriamfetol',
    'XYWAV': 'calcium/magnesium/potassium/sodium oxybates',
    'XYREM': 'sodium oxybate',
    'BIKTARVY': 'bictegravir/emtricitabine/tenofovir',
    'DOVATO': 'dolutegravir/lamivudine',
    'CABENUVA': 'cabotegravir/rilpivirine',
    'VOCABRIA': 'cabotegravir',
    'RUKOBIA': 'fostemsavir',
    'SUNLENCA': 'lenacapavir',
    'VEMLIDY': 'tenofovir alafenamide',
    'MAVYRET': 'glecaprevir/pibrentasvir',
    'VEKLURY': 'remdesivir',
    'PAXLOVID': 'nirmatrelvir/ritonavir',
    'LAGEVRIO': 'molnupiravir',
    'RINVOQ': 'upadacitinib',
    'XELJANZ': 'tofacitinib',
    'OLUMIANT': 'baricitinib',
    'OPZELURA': 'ruxolitinib',
    'SOTYKTU': 'deucravacitinib',
    'SKYRIZI': 'risankizumab',
    'TREMFYA': 'guselkumab',
    'ILUMYA': 'tildrakizumab',
    'STELARA': 'ustekinumab',
    'COSENTYX': 'secukinumab',
    'TALTZ': 'ixekizumab',
    'SILIQ': 'brodalumab',
    'DUPIXENT': 'dupilumab',
    'ADBRY': 'tralokinumab',
    'NUCALA': 'mepolizumab',
    'FASENRA': 'benralizumab',
    'TEZSPIRE': 'tezepelumab',
    'XOLAIR': 'omalizumab',
    'ENTYVIO': 'vedolizumab',
    'HUMIRA': 'adalimumab',
    'REMICADE': 'infliximab',
    'SIMPONI': 'golimumab',
    'CIMZIA': 'certolizumab pegol',
    'ACTEMRA': 'tocilizumab',
    'KEVZARA': 'sarilumab',
    'ORENCIA': 'abatacept',
    'BENLYSTA': 'belimumab',
    'SAPHNELO': 'anifrolumab',
    'JARDIANCE': 'empagliflozin',
    'FARXIGA': 'dapagliflozin',
    'INVOKANA': 'canagliflozin',
    'OZEMPIC': 'semaglutide',
    'WEGOVY': 'semaglutide',
    'RYBELSUS': 'semaglutide',
    'TRULICITY': 'dulaglutide',
    'VICTOZA': 'liraglutide',
    'SAXENDA': 'liraglutide',
    'MOUNJARO': 'tirzepatide',
    'ZEPBOUND': 'tirzepatide',
    'LEQEMBI': 'lecanemab',
    'KISUNLA': 'donanemab',
    'ADUHELM': 'aducanumab',
    'ENTRESTO': 'sacubitril/valsartan',
    'VERQUVO': 'vericiguat',
    'FARXIGA': 'dapagliflozin',
    'ELIQUIS': 'apixaban',
    'XARELTO': 'rivaroxaban',
    'PRADAXA': 'dabigatran',
    'SAVAYSA': 'edoxaban',
    'NURTEC': 'rimegepant',
    'UBRELVY': 'ubrogepant',
    'QULIPTA': 'atogepant',
    'AIMOVIG': 'erenumab',
    'AJOVY': 'fremanezumab',
    'EMGALITY': 'galcanezumab',
    'VYEPTI': 'eptinezumab',
    'TRIKAFTA': 'elexacaftor/tezacaftor/ivacaftor',
    'KALYDECO': 'ivacaftor',
    'SYMDEKO': 'tezacaftor/ivacaftor',
    'ORKAMBI': 'lumacaftor/ivacaftor',
    'SPINRAZA': 'nusinersen',
    'ZOLGENSMA': 'onasemnogene abeparvovec',
    'EVRYSDI': 'risdiplam',
    'EXONDYS': 'eteplirsen',
    'VYONDYS': 'golodirsen',
    'AMONDYS': 'casimersen',
    'VILTEPSO': 'viltolarsen',
    'ELEVIDYS': 'delandistrogene moxeparvovec',
    'LUXTURNA': 'voretigene neparvovec',
    'HEMGENIX': 'etranacogene dezaparvovec',
    'ROCTAVIAN': 'valoctocogene roxaparvovec',
    'BEQVEZ': 'fidanacogene elaparvovec',
    'CASGEVY': 'exagamglogene autotemcel',
    'LYFGENIA': 'lovotibeglogene autotemcel',
    'ABECMA': 'idecabtagene vicleucel',
    'CARVYKTI': 'ciltacabtagene autoleucel',
    'BREYANZI': 'lisocabtagene maraleucel',
    'YESCARTA': 'axicabtagene ciloleucel',
    'KYMRIAH': 'tisagenlecleucel',
    'TECARTUS': 'brexucabtagene autoleucel',
    'PROVENGE': 'sipuleucel-T',
    'IMLYGIC': 'talimogene laherparepvec',
    'KIMMTRAK': 'tebentafusp',
    'ANKTIVA': 'nogapendekin alfa inbakicept',
    'REBLOZYL': 'luspatercept',
    'EPOGEN': 'epoetin alfa',
    'ARANESP': 'darbepoetin alfa',
    'NEULASTA': 'pegfilgrastim',
    'ZARXIO': 'filgrastim-sndz',
    'UDENYCA': 'pegfilgrastim-cbqv',
    'NYVEPRIA': 'pegfilgrastim-apgf',
    'ZIEXTENZO': 'pegfilgrastim-bmez',
    'FULPHILA': 'pegfilgrastim-jmdb',
    'ROLONTIS': 'eflapegrastim',
    'EMPAVELI': 'pegcetacoplan',
    'SOLIRIS': 'eculizumab',
    'ULTOMIRIS': 'ravulizumab',
    'NARCAN': 'naloxone',
    'NEFFY': 'epinephrine',
    'EPIPEN': 'epinephrine',
    'SYMJEPI': 'epinephrine',
    'AUVI-Q': 'epinephrine',
}

def get_generic_name(drug_name, brand_map):
    if not drug_name:
        return None
    # Check brand to generic map
    drug_upper = drug_name.upper()
    for brand, generic in brand_map.items():
        if brand in drug_upper:
            return generic
    return None

updated = 0
for filename in files:
    filepath = os.path.join(enriched_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        event = json.load(f)

    modified = False
    now = datetime.now().isoformat()

    # 1. therapeutic_area - derive from indication
    if event.get('therapeutic_area', {}).get('status') == 'not_searched':
        indication_val = event.get('indication', {}).get('value')
        ta = get_therapeutic_area(indication_val)
        if ta:
            event['therapeutic_area'] = {
                'status': 'found',
                'value': ta,
                'source': 'derived_from_indication',
                'confidence': 0.85,
                'evidence': [f'Derived from indication: {indication_val}'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True

    # 2. phase - derive from approval_type
    if event.get('phase', {}).get('status') == 'not_searched':
        approval_type_val = event.get('approval_type', {}).get('value', '')
        if approval_type_val:
            approval_type_val = approval_type_val.lower()
        else:
            approval_type_val = ''
        result = event.get('result', '')

        if approval_type_val in ('anda', 'dmg'):
            # Generics don't have phases
            event['phase'] = {
                'status': 'not_applicable',
                'value': None,
                'source': 'approval_type_anda_dmg',
                'confidence': 1.0,
                'evidence': ['ANDA/DMG applications do not have clinical trial phases'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True
        elif approval_type_val in ('nda', 'bla', 'snda', 'sbla'):
            # New drugs typically complete Phase 3
            event['phase'] = {
                'status': 'found',
                'value': 'Phase 3',
                'source': 'derived_from_approval_type',
                'confidence': 0.9,
                'evidence': [f'{approval_type_val.upper()} typically requires Phase 3 completion'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True
        elif approval_type_val == '505(b)(2)':
            event['phase'] = {
                'status': 'found',
                'value': 'Phase 3',
                'source': 'derived_from_approval_type',
                'confidence': 0.85,
                'evidence': ['505(b)(2) typically requires clinical trials'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True

    # 3. generic_name - check brand to generic map or use drug_name if lowercase
    if event.get('generic_name', {}).get('status') == 'not_searched':
        drug_name = event.get('drug_name', '')
        generic = get_generic_name(drug_name, BRAND_TO_GENERIC)
        if generic:
            event['generic_name'] = {
                'status': 'found',
                'value': generic,
                'source': 'brand_to_generic_map',
                'confidence': 0.95,
                'evidence': [f'Generic name for {drug_name}'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True
        elif drug_name and drug_name[0].islower():
            # Lowercase names are typically generic
            event['generic_name'] = {
                'status': 'found',
                'value': drug_name,
                'source': 'drug_name_is_generic',
                'confidence': 0.8,
                'evidence': [f'Drug name {drug_name} appears to be generic name'],
                'searched_sources': ['derived'],
                'last_searched': now,
                'error': None
            }
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
        updated += 1

print(f'Updated {updated} files with derived fields')
