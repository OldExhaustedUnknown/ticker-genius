"""Safety 필드 개별 분석 및 수정

1. pai_passed: 승인 = True (FDA 승인 조건)
2. warning_letter: 회사별 실제 Warning Letter 이력 확인 필요 -> not_searched
3. safety_signal: Black Box Warning, REMS 등 확인 필요
"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 알려진 Safety Signal 보유 약물 (Black Box Warning, REMS 등)
# 출처: FDA labels, REMS database
KNOWN_SAFETY_SIGNALS = {
    # Opioids - REMS required
    'OLINVYK': {'has_signal': True, 'reason': 'Opioid REMS', 'severity': 'high'},
    'OLICERIDINE': {'has_signal': True, 'reason': 'Opioid REMS', 'severity': 'high'},

    # CNS drugs with abuse potential
    'XYWAV': {'has_signal': True, 'reason': 'REMS - GHB analogue', 'severity': 'high'},
    'XYREM': {'has_signal': True, 'reason': 'REMS - GHB', 'severity': 'high'},
    'LUMRYZ': {'has_signal': True, 'reason': 'REMS - Sodium oxybate', 'severity': 'high'},
    'FINTEPLA': {'has_signal': True, 'reason': 'REMS - Fenfluramine', 'severity': 'medium'},
    'FENFLURAMINE': {'has_signal': True, 'reason': 'REMS - Cardiac risk', 'severity': 'medium'},

    # Immunosuppressants with infection risk
    'XELJANZ': {'has_signal': True, 'reason': 'Black Box - Serious infections', 'severity': 'high'},
    'TOFACITINIB': {'has_signal': True, 'reason': 'Black Box - Serious infections', 'severity': 'high'},
    'RINVOQ': {'has_signal': True, 'reason': 'Black Box - Serious infections', 'severity': 'high'},
    'UPADACITINIB': {'has_signal': True, 'reason': 'Black Box - Serious infections', 'severity': 'high'},

    # Cardiovascular risks
    'CAMZYOS': {'has_signal': True, 'reason': 'REMS - Heart failure risk', 'severity': 'high'},
    'MAVACAMTEN': {'has_signal': True, 'reason': 'REMS - Heart failure risk', 'severity': 'high'},

    # Teratogenicity
    'THALOMID': {'has_signal': True, 'reason': 'REMS - Teratogenic', 'severity': 'high'},
    'THALIDOMIDE': {'has_signal': True, 'reason': 'REMS - Teratogenic', 'severity': 'high'},
    'REVLIMID': {'has_signal': True, 'reason': 'REMS - Teratogenic', 'severity': 'high'},
    'LENALIDOMIDE': {'has_signal': True, 'reason': 'REMS - Teratogenic', 'severity': 'high'},
    'POMALYST': {'has_signal': True, 'reason': 'REMS - Teratogenic', 'severity': 'high'},

    # Hepatotoxicity
    'ADUHELM': {'has_signal': True, 'reason': 'ARIA risk', 'severity': 'medium'},
    'ADUCANUMAB': {'has_signal': True, 'reason': 'ARIA risk', 'severity': 'medium'},
    'LEQEMBI': {'has_signal': True, 'reason': 'ARIA risk', 'severity': 'medium'},
    'LECANEMAB': {'has_signal': True, 'reason': 'ARIA risk', 'severity': 'medium'},
    'KISUNLA': {'has_signal': True, 'reason': 'ARIA risk', 'severity': 'medium'},
    'DONANEMAB': {'has_signal': True, 'reason': 'ARIA risk', 'severity': 'medium'},

    # Isotretinoin
    'ACCUTANE': {'has_signal': True, 'reason': 'iPLEDGE REMS', 'severity': 'high'},
    'ISOTRETINOIN': {'has_signal': True, 'reason': 'iPLEDGE REMS', 'severity': 'high'},

    # Clozapine
    'CLOZARIL': {'has_signal': True, 'reason': 'REMS - Agranulocytosis', 'severity': 'high'},
    'CLOZAPINE': {'has_signal': True, 'reason': 'REMS - Agranulocytosis', 'severity': 'high'},

    # Gene therapy - novel risks
    'ZOLGENSMA': {'has_signal': True, 'reason': 'Hepatotoxicity risk', 'severity': 'medium'},
    'ELEVIDYS': {'has_signal': True, 'reason': 'Myocarditis risk', 'severity': 'medium'},
    'ROCTAVIAN': {'has_signal': True, 'reason': 'Hepatotoxicity risk', 'severity': 'medium'},

    # CAR-T therapies - CRS risk
    'ABECMA': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},
    'CARVYKTI': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},
    'BREYANZI': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},
    'KYMRIAH': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},
    'YESCARTA': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},
    'TECARTUS': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},
    'AUCATZYL': {'has_signal': True, 'reason': 'REMS - CRS/ICANS', 'severity': 'high'},

    # Botulinum toxins
    'BOTOX': {'has_signal': True, 'reason': 'Black Box - Spread of toxin', 'severity': 'medium'},
    'DYSPORT': {'has_signal': True, 'reason': 'Black Box - Spread of toxin', 'severity': 'medium'},
    'DAXXIFY': {'has_signal': True, 'reason': 'Black Box - Spread of toxin', 'severity': 'medium'},
    'DAXIBOTULINUMTOXINA': {'has_signal': True, 'reason': 'Black Box - Spread of toxin', 'severity': 'medium'},

    # Antipsychotics
    'COBENFY': {'has_signal': True, 'reason': 'Elderly dementia mortality', 'severity': 'medium'},
    'XANOMELINE': {'has_signal': True, 'reason': 'Elderly dementia mortality', 'severity': 'medium'},
    'FANAPT': {'has_signal': True, 'reason': 'Elderly dementia mortality', 'severity': 'medium'},
    'ILOPERIDONE': {'has_signal': True, 'reason': 'Elderly dementia mortality', 'severity': 'medium'},

    # Eye drugs with infection risk
    'SYFOVRE': {'has_signal': True, 'reason': 'Endophthalmitis, vasculitis', 'severity': 'medium'},
    'IZERVAY': {'has_signal': True, 'reason': 'Endophthalmitis risk', 'severity': 'medium'},
}

# 알려진 Warning Letter 보유 회사 (최근 3년)
# 출처: FDA Warning Letters database
COMPANIES_WITH_WARNING_LETTERS = {
    # Major pharma with recent warning letters
    'PFE': {'has_wl': True, 'year': 2023, 'facility': 'Multiple'},
    'JNJ': {'has_wl': True, 'year': 2023, 'facility': 'Manufacturing'},
    'NVS': {'has_wl': True, 'year': 2022, 'facility': 'Gene therapy'},
    # Note: Most companies clear warning letters, so default should be not_searched
}

data_dir = Path('data/enriched')
updated = 0
safety_found = 0
wl_reset = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    drug = data.get('drug_name', '').upper()
    ticker = data.get('ticker', '').upper()
    result = data.get('result', '')
    modified = False

    # 1. Safety Signal - 실제 데이터 반영
    ss = data.get('safety_signal')
    if isinstance(ss, dict) and ss.get('status') == 'found' and ss.get('value') == False:
        # 기본값으로 설정된 경우, 실제 데이터 확인
        matched_signal = None
        for key, info in KNOWN_SAFETY_SIGNALS.items():
            if key.upper() in drug:
                matched_signal = info
                break

        if matched_signal:
            data['safety_signal'] = {
                'status': 'found',
                'value': True,
                'source': 'known_safety_database',
                'confidence': 0.95,
                'tier': 1,
                'reason': matched_signal['reason'],
                'severity': matched_signal['severity']
            }
            safety_found += 1
            print(f'[SAFETY] {ticker}: {drug[:25]} -> {matched_signal["reason"]}')
            modified = True

    # 2. Warning Letter - 대부분 not_searched로 리셋 (실제 조사 필요)
    wl = data.get('warning_letter')
    if isinstance(wl, dict) and wl.get('source') == 'default_for_approved':
        # 기본값 -> not_searched로 변경 (실제 조사 필요)
        data['warning_letter'] = {
            'status': 'not_searched',
            'value': None,
            'source': None,
            'confidence': 0.0,
            'tier': 0,
            'note': 'Requires FDA Warning Letter DB search'
        }
        wl_reset += 1
        modified = True

    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        updated += 1

print(f'\n=== 결과 ===')
print(f'Safety Signal 발견: {safety_found}건')
print(f'Warning Letter 리셋: {wl_reset}건')
print(f'총 수정: {updated}건')
