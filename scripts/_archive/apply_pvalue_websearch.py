"""웹서치로 수집한 p-value 적용"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 웹서치 결과 p-value 데이터
PVALUE_DATA = {
    # Batch 1
    'DURYSTA': {'pvalue': None, 'note': 'noninferiority trial', 'trial': 'ARTEMIS 1&2'},
    'ACER-001': {'pvalue': None, 'note': 'bioequivalence 505(b)(2)', 'trial': 'BE trial'},
    'ZUNVEYL': {'pvalue': 0.0007, 'note': 'primary endpoint met', 'trial': 'SKYLARK'},
    'ZURANOLONE': {'pvalue': 0.0007, 'note': 'primary endpoint met', 'trial': 'SKYLARK'},
    'AFAMI-CEL': {'pvalue': None, 'note': 'single-arm Phase 2, ORR 38.6%', 'trial': 'SPEARHEAD-1'},
    'VADADUSTAT': {'pvalue': None, 'note': 'noninferiority met', 'trial': 'INNO2VATE'},
    'VAFSEO': {'pvalue': None, 'note': 'noninferiority met', 'trial': 'INNO2VATE'},
    'AVT05': {'pvalue': None, 'note': 'biosimilar', 'trial': None},
    'RIABNI': {'pvalue': None, 'note': 'biosimilar', 'trial': None},
    'REXTOVY': {'pvalue': None, 'note': 'generic/branded generic', 'trial': None},
    'BONCRESA': {'pvalue': None, 'note': 'biosimilar', 'trial': None},
    'BREKIYA': {'pvalue': None, 'note': '505(b)(2)', 'trial': None},

    # Batch 2
    'ANAPHYLM': {'pvalue': None, 'note': 'PK study', 'trial': 'Pivotal PK'},
    'TRANSCON': {'pvalue': 0.0001, 'note': 'p<0.0001 adult GHD', 'trial': 'foresiGHt'},
    'LONAPEGSOMATROPIN': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'foresiGHt'},
    'AVAPRITINIB': {'pvalue': 0.055, 'note': 'failed primary endpoint', 'trial': 'VOYAGER'},
    'ANKTIVA': {'pvalue': None, 'note': 'single-arm CR=71%', 'trial': 'QUILT-3.032'},
    'N-803': {'pvalue': None, 'note': 'single-arm CR=71%', 'trial': 'QUILT-3.032'},
    'RUXOLITINIB': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'TRuE-AD'},
    'OPZELURA': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'TRuE-AD'},
    'DONIDALORSEN': {'pvalue': 0.001, 'note': 'p<0.001 Q4W', 'trial': 'OASIS-HAE'},
    'DEFITELIO': {'pvalue': 0.0109, 'note': 'p=0.0109', 'trial': 'Phase 3 VOD'},
    'DEFIBROTIDE': {'pvalue': 0.0109, 'note': 'p=0.0109', 'trial': 'Phase 3 VOD'},

    # Batch 3
    'LERODALCIBEP': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'LIBerate-HeFH'},
    'LEROCHOL': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'LIBerate-HeFH'},
    'AFREZZA': {'pvalue': None, 'note': 'noninferiority met', 'trial': 'AFFINITY'},
    'MRNA-1283': {'pvalue': 0.0005, 'note': 'p=0.0005', 'trial': 'NextCOVE'},
    'VIJOICE': {'pvalue': None, 'note': 'single-arm 27% ORR', 'trial': 'EPIK-P1'},
    'ALPELISIB': {'pvalue': None, 'note': 'single-arm', 'trial': 'EPIK-P1'},
    'SOMATROGON': {'pvalue': None, 'note': 'noninferiority met', 'trial': 'Phase 3 GHD'},
    'PT027': {'pvalue': 0.001, 'note': 'p<0.001', 'trial': 'MANDALA'},
    'RVL-1201': {'pvalue': 0.001, 'note': 'p<0.001', 'trial': 'RVL-1201-201/202'},
    'ZURZUVAE': {'pvalue': 0.0141, 'note': 'WATERFALL met', 'trial': 'WATERFALL'},
    'DCCR': {'pvalue': 0.198, 'note': 'ITT not significant', 'trial': 'DESTINY PWS'},
    'DIAZOXIDE': {'pvalue': 0.198, 'note': 'ITT not significant', 'trial': 'DESTINY PWS'},
    'REVUMENIB': {'pvalue': 0.0036, 'note': 'p=0.0036', 'trial': 'AUGMENT-101'},

    # Batch 4
    'TP-03': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'Saturn-1/2'},
    'LOTILANER': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'Saturn-1/2'},
    'XDEMVY': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'Saturn-1/2'},
    'VEVERIMER': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'TRCA-301'},
    'UZEDY': {'pvalue': 0.0001, 'note': 'p<0.0001', 'trial': 'RISE'},
    'UGN-102': {'pvalue': None, 'note': 'single-arm CR=79.6%', 'trial': 'ENVISION'},
    'VK2809': {'pvalue': 0.001, 'note': 'Phase 2b only', 'trial': 'VOYAGE'},
    'SEMGLEE': {'pvalue': None, 'note': 'biosimilar', 'trial': None},
    'ERMEZA': {'pvalue': None, 'note': 'bioequivalence NDA', 'trial': None},
    'LEVOKETOCONAZOLE': {'pvalue': 0.0002, 'note': 'p=0.0002', 'trial': 'LOGICS'},
    'RECORLEV': {'pvalue': 0.0002, 'note': 'p=0.0002', 'trial': 'LOGICS'},
    'OMBURTAMAB': {'pvalue': None, 'note': 'external control rejected', 'trial': 'Trial 101'},
    'DASIGLUCAGON': {'pvalue': 0.0029, 'note': 'p=0.0029 post hoc', 'trial': 'Trial 17109'},
}

data_dir = Path('data/enriched')
updated = 0
already_has = 0
not_found = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Skip if already has p_value_numeric
    if data.get('p_value_numeric') is not None:
        already_has += 1
        continue

    drug = data.get('drug_name', '').upper()
    ticker = data.get('ticker', '')

    # Find matching p-value
    matched = None
    for key, info in PVALUE_DATA.items():
        if key.upper() in drug:
            matched = info
            break

    if matched and matched.get('pvalue') is not None:
        data['p_value_numeric'] = matched['pvalue']

        # Update p_value StatusField too
        if not data.get('p_value') or (isinstance(data.get('p_value'), dict) and not data['p_value'].get('value')):
            pval = matched['pvalue']
            pval_text = f"p={'<' if pval < 0.001 else '='}{pval}"
            data['p_value'] = {
                'status': 'found',
                'value': pval_text,
                'source': 'websearch',
                'confidence': 0.90,
                'trial': matched.get('trial'),
                'tier': 2
            }

        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f'{ticker}: {drug[:30]} -> p={matched["pvalue"]} ({matched.get("trial", "")})')
        updated += 1
    elif matched:
        # Has note but no numeric p-value (biosimilar, single-arm, etc.)
        if matched.get('note'):
            # Update p_value with note
            if not data.get('p_value') or (isinstance(data.get('p_value'), dict) and not data['p_value'].get('value')):
                data['p_value'] = {
                    'status': 'found',
                    'value': matched['note'],
                    'source': 'websearch',
                    'confidence': 0.85,
                    'trial': matched.get('trial'),
                    'tier': 2,
                    'note': 'No numeric p-value applicable'
                }
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f'{ticker}: {drug[:30]} -> {matched["note"]}')
                updated += 1
    else:
        not_found += 1

print(f'\n=== 결과 ===')
print(f'p_value 업데이트: {updated}건')
print(f'이미 보유: {already_has}건')
print(f'매칭 안됨: {not_found}건')
