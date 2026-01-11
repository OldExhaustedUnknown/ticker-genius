"""MOA (Mechanism of Action) 적용 - Batch 4"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

moa_data = {
    # Gene Therapy / Cell Therapy
    'CAR-T': 'CAR-T cell therapy',
    'KYMRIAH': 'CAR-T cell therapy',
    'TISAGENLECLEUCEL': 'CAR-T cell therapy',
    'YESCARTA': 'CAR-T cell therapy',
    'AXICABTAGENE': 'CAR-T cell therapy',
    'TECARTUS': 'CAR-T cell therapy',
    'BREXUCABTAGENE': 'CAR-T cell therapy',
    'BREYANZI': 'CAR-T cell therapy',
    'LISOCABTAGENE': 'CAR-T cell therapy',
    'ABECMA': 'CAR-T cell therapy',
    'IDECABTAGENE': 'CAR-T cell therapy',
    'CARVYKTI': 'CAR-T cell therapy',
    'CILTACABTAGENE': 'CAR-T cell therapy',
    'AMTAGVI': 'TIL cell therapy',
    'LIFILEUCEL': 'TIL cell therapy',
    'AFAMI-CEL': 'TCR-T cell therapy',
    'TECELRA': 'TCR-T cell therapy',
    'AUCATZYL': 'CAR-T cell therapy',
    'OBE-CEL': 'CAR-T cell therapy',
    'OBECABTAGENE': 'CAR-T cell therapy',

    # Gene Therapy - AAV
    'ZOLGENSMA': 'AAV gene therapy',
    'ONASEMNOGENE': 'AAV gene therapy',
    'LUXTURNA': 'AAV gene therapy',
    'VORETIGENE': 'AAV gene therapy',
    'HEMGENIX': 'AAV gene therapy',
    'ETRANACOGENE': 'AAV gene therapy',
    'BEQVEZ': 'AAV gene therapy',
    'FIDANACOGENE': 'AAV gene therapy',
    'ELEVIDYS': 'AAV gene therapy',
    'DELANDISTROGENE': 'AAV gene therapy',
    'ROCTAVIAN': 'AAV gene therapy',
    'VALOCTOCOGENE': 'AAV gene therapy',
    'RGX-121': 'AAV gene therapy',
    'UX111': 'AAV gene therapy',
    'ABO-102': 'AAV gene therapy',

    # Gene Therapy - Lentiviral
    'ZYNTEGLO': 'Lentiviral gene therapy',
    'BETIBEGLOGENE': 'Lentiviral gene therapy',
    'SKYSONA': 'Lentiviral gene therapy',
    'ELIVALDOGENE': 'Lentiviral gene therapy',
    'BETI-CEL': 'Lentiviral gene therapy',
    'LOVOTIBEGLOGENE': 'Lentiviral gene therapy',
    'LENMELDY': 'Lentiviral gene therapy',
    'ATIDARSAGENE': 'Lentiviral gene therapy',
    'CASGEVY': 'CRISPR gene editing',
    'EXAGAMGLOGENE': 'CRISPR gene editing',

    # Oncolytic Virus
    'IMLYGIC': 'Oncolytic virus',
    'TALIMOGENE': 'Oncolytic virus',
    'RP1': 'Oncolytic virus',
    'VUSOLIMOGENE': 'Oncolytic virus',

    # ADC (Antibody-Drug Conjugate)
    'ADCETRIS': 'ADC (CD30-targeted)',
    'BRENTUXIMAB': 'ADC (CD30-targeted)',
    'POLIVY': 'ADC (CD79b-targeted)',
    'POLATUZUMAB': 'ADC (CD79b-targeted)',
    'PADCEV': 'ADC (Nectin-4-targeted)',
    'ENFORTUMAB': 'ADC (Nectin-4-targeted)',
    'TRODELVY': 'ADC (Trop-2-targeted)',
    'SACITUZUMAB': 'ADC (Trop-2-targeted)',
    'ELAHERE': 'ADC (FRα-targeted)',
    'MIRVETUXIMAB': 'ADC (FRα-targeted)',
    'TIVDAK': 'ADC (Tissue factor-targeted)',
    'TISOTUMAB': 'ADC (Tissue factor-targeted)',
    'BLENREP': 'ADC (BCMA-targeted)',
    'BELANTAMAB': 'ADC (BCMA-targeted)',
    'ZYNLONTA': 'ADC (CD19-targeted)',
    'LONCASTUXIMAB': 'ADC (CD19-targeted)',
    'ZIIHERA': 'Bispecific HER2-targeted ADC',
    'ZANIDATAMAB': 'Bispecific HER2-targeted ADC',

    # Bispecific Antibodies
    'HEMLIBRA': 'Bispecific antibody (FIXa/FX)',
    'EMICIZUMAB': 'Bispecific antibody (FIXa/FX)',
    'BLINCYTO': 'BiTE (CD19/CD3)',
    'BLINATUMOMAB': 'BiTE (CD19/CD3)',
    'TECVAYLI': 'Bispecific antibody (BCMAxCD3)',
    'TECLISTAMAB': 'Bispecific antibody (BCMAxCD3)',
    'TALVEY': 'Bispecific antibody (GPRC5DxCD3)',
    'TALQUETAMAB': 'Bispecific antibody (GPRC5DxCD3)',
    'ELREXFIO': 'Bispecific antibody (BCMAxCD3)',
    'ELRANATAMAB': 'Bispecific antibody (BCMAxCD3)',
    'COLUMVI': 'Bispecific antibody (CD20xCD3)',
    'GLOFITAMAB': 'Bispecific antibody (CD20xCD3)',
    'EPKINLY': 'Bispecific antibody (CD20xCD3)',
    'EPCORITAMAB': 'Bispecific antibody (CD20xCD3)',
    'LUNSUMIO': 'Bispecific antibody (CD20xCD3)',
    'MOSUNETUZUMAB': 'Bispecific antibody (CD20xCD3)',
    'RYBREVANT': 'Bispecific antibody (EGFRxMET)',
    'AMIVANTAMAB': 'Bispecific antibody (EGFRxMET)',
    'ODRONEXTAMAB': 'Bispecific antibody (CD20xCD3)',
    'IMDELLTRA': 'BiTE (DLL3xCD3)',
    'TARLATAMAB': 'BiTE (DLL3xCD3)',
    'TEBENTAFUSP': 'BiTE (gp100xCD3)',

    # FcRn Inhibitors
    'VYVGART': 'FcRn inhibitor',
    'EFGARTIGIMOD': 'FcRn inhibitor',
    'RYSTIGGO': 'FcRn inhibitor',
    'ROZANOLIXIZUMAB': 'FcRn inhibitor',

    # SMA
    'SPINRAZA': 'ASO (SMN2 splicing modifier)',
    'NUSINERSEN': 'ASO (SMN2 splicing modifier)',
    'EVRYSDI': 'SMN2 splicing modifier',
    'RISDIPLAM': 'SMN2 splicing modifier',

    # DMD
    'EXONDYS': 'Exon-skipping ASO',
    'ETEPLIRSEN': 'Exon-skipping ASO',
    'VYONDYS': 'Exon-skipping ASO',
    'GOLODIRSEN': 'Exon-skipping ASO',
    'VILTEPSO': 'Exon-skipping ASO',
    'VILTOLARSEN': 'Exon-skipping ASO',
    'AMONDYS': 'Exon-skipping ASO',
    'CASIMERSEN': 'Exon-skipping ASO',

    # RNAi / ASO
    'ONPATTRO': 'siRNA',
    'PATISIRAN': 'siRNA',
    'AMVUTTRA': 'siRNA',
    'VUTRISIRAN': 'siRNA',
    'GIVLAARI': 'siRNA',
    'GIVOSIRAN': 'siRNA',
    'OXLUMO': 'siRNA',
    'LUMASIRAN': 'siRNA',
    'FITUSIRAN': 'siRNA',
    'QFITLIA': 'siRNA',
    'REDEMPLO': 'siRNA',
    'PLOZASIRAN': 'siRNA',
    'WAINUA': 'ASO',
    'EPLONTERSEN': 'ASO',
    'TRYNGOLZA': 'ASO',
    'OLEZARSEN': 'ASO',
    'DAWNZERA': 'ASO',
    'DONIDALORSEN': 'ASO',
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_moa = data.get('mechanism_of_action', '')
    if existing_moa and existing_moa.strip():
        continue

    drug = data.get('drug_name', '').upper()
    matched_moa = None

    for key, moa in moa_data.items():
        if key.upper() in drug:
            matched_moa = moa
            break

    if matched_moa:
        data['mechanism_of_action'] = matched_moa
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'{data.get("ticker")}: {drug[:25]} -> {matched_moa}')
        updated += 1

print(f'\nBatch 4 updated: {updated}')
