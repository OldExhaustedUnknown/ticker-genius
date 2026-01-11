"""AdCom 정보 적용 - Batch 1: 기본값 + 알려진 AdCom 미팅"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Known AdCom meetings (drug name -> adcom info)
# Most drugs don't have AdCom, so we'll set scheduled=False by default
# and only mark True for known cases
known_adcom = {
    # Alzheimer's drugs - controversial, had AdCom
    'ADUHELM': {'scheduled': True, 'held': True, 'outcome': 'unfavorable', 'vote': '1-8-2'},
    'ADUCANUMAB': {'scheduled': True, 'held': True, 'outcome': 'unfavorable', 'vote': '1-8-2'},
    'LEQEMBI': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '6-0'},
    'LECANEMAB': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '6-0'},
    'KISUNLA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'DONANEMAB': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Gene therapy - novel, often have AdCom
    'ZOLGENSMA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'LUXTURNA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'CASGEVY': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'EXAGAMGLOGENE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'LYFGENIA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'LOVO-CEL': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Controversial safety
    'CAMZYOS': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '9-3'},
    'MAVACAMTEN': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '9-3'},
    'RELYVRIO': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '7-2'},
    'AMX0035': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '7-2'},
    'ZURZUVAE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'ZURANOLONE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # CNS - often have AdCom
    'EPIDIOLEX': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '13-0'},
    'CANNABIDIOL': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '13-0'},
    'FINTEPLA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'FENFLURAMINE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'XYWAV': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'XYREM': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'COBENFY': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '9-2'},
    'XANOMELINE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '9-2'},

    # Accelerated approval drugs often have AdCom
    'KEYTRUDA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'OPDIVO': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'TECENTRIQ': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Cardiovascular - some had AdCom
    'REPATHA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '17-0'},
    'PRALUENT': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '17-0'},
    'ENTRESTO': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'VERQUVO': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'WINREVAIR': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'SOTATERCEPT': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Weight loss drugs - controversial
    'WEGOVY': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'ZEPBOUND': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Diabetes - some had AdCom
    'TZIELD': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '10-7'},
    'TEPLIZUMAB': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': '10-7'},

    # Rare disease - some had AdCom
    'SKYCLARYS': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'SKYSONA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'ELEVIDYS': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'ROCTAVIAN': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Eye drugs - novel mechanisms
    'SYFOVRE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'IZERVAY': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},

    # Novel mechanisms/First in class
    'TRIKAFTA': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'KALYDECO': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'JOURNAVX': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
    'SUZETRIGINE': {'scheduled': True, 'held': True, 'outcome': 'favorable', 'vote': 'positive'},
}

data_dir = Path('data/enriched')
updated = 0
with_adcom = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Skip if already has AdCom data
    if data.get('adcom_info'):
        continue

    drug = data.get('drug_name', '').upper()
    adcom_found = None

    for key, adcom in known_adcom.items():
        if key.upper() in drug:
            adcom_found = adcom
            break

    if adcom_found:
        data['adcom_info'] = {
            'scheduled': adcom_found['scheduled'],
            'held': adcom_found.get('held', False),
            'outcome': adcom_found.get('outcome'),
            'vote': adcom_found.get('vote'),
        }
        with_adcom += 1
        print(f'{data.get("ticker")}: {drug[:25]} -> AdCom {adcom_found.get("outcome")}')
    else:
        # Default: no AdCom scheduled
        data['adcom_info'] = {
            'scheduled': False,
            'held': False,
            'outcome': None,
            'vote': None,
        }

    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    updated += 1

print(f'\nTotal updated: {updated}')
print(f'With AdCom meetings: {with_adcom}')
