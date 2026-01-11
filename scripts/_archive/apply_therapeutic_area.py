"""
therapeutic_area 데이터를 enriched 파일에 적용하는 스크립트
"""
import json
from pathlib import Path
import glob
from datetime import datetime

# 수집된 데이터 로드 (모든 배치 파일 병합)
collected_data = []
batch_files = glob.glob('d:/ticker-genius/data/therapeutic_area_batch*.json')
for batch_file in batch_files:
    with open(batch_file, 'r', encoding='utf-8') as f:
        collected_data.extend(json.load(f))

print(f"로드된 배치 파일: {len(batch_files)}개, 총 {len(collected_data)}개 약물")

# 약물명 정규화 함수
def normalize_drug_name(name):
    if not name:
        return ""
    # 대문자로 변환하고 특수문자 제거
    name = name.upper()
    # 일반적인 접미사/접두사 제거
    for suffix in [' HYDROCHLORIDE', ' HCL', '-IPDL', '-AAHU', '-TPZI', '-CDON', '-DLWR', '-CMKB', ' INJECTION', ' CAPSULE', ' TABLET', ' CREAM', ' GEL', ' SOLUTION', ' SPRAY']:
        name = name.replace(suffix, '')
    # 괄호 안의 내용 제거
    import re
    name = re.sub(r'\([^)]*\)', '', name)
    # 슬래시로 나눠진 이름 처리
    if '/' in name:
        parts = name.split('/')
        name = parts[0]  # 첫 번째 부분만 사용
    return name.strip()

# 수집 데이터를 딕셔너리로 변환 (ticker + 정규화된 약물명 -> 데이터)
collected_dict = {}
for item in collected_data:
    ticker = item.get('ticker', '').upper()
    drug = normalize_drug_name(item.get('drug', ''))
    key = f"{ticker}:{drug}"
    collected_dict[key] = item

# enriched 파일 처리
enriched_dir = Path('d:/ticker-genius/data/enriched')
files = list(enriched_dir.glob('*.json'))

matched = 0
updated = 0
not_matched = 0

for f in files:
    data = json.loads(f.read_text(encoding='utf-8'))
    ticker = data.get('ticker', '').upper()
    drug_name = data.get('drug_name', '')
    normalized_drug = normalize_drug_name(drug_name)

    # 매칭 시도
    key = f"{ticker}:{normalized_drug}"
    match = collected_dict.get(key)

    # 부분 매칭 시도
    if not match:
        for k, v in collected_dict.items():
            k_ticker, k_drug = k.split(':', 1)
            if k_ticker == ticker and (k_drug in normalized_drug or normalized_drug in k_drug):
                match = v
                break

    if match:
        matched += 1
        ta = match.get('therapeutic_area')
        if ta:
            # therapeutic_area 필드 업데이트
            data['therapeutic_area'] = {
                'status': 'found',
                'value': ta,
                'source': 'websearch',
                'confidence': 0.85,
                'tier': 2,
                'evidence': [],
                'searched_sources': ['websearch'],
                'last_searched': datetime.now().isoformat(),
                'error': None
            }
            updated += 1

            # 파일 저장
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    else:
        not_matched += 1

print("=" * 60)
print("Therapeutic Area 데이터 반영 완료")
print("=" * 60)
print(f"매칭된 이벤트: {matched}")
print(f"업데이트된 필드: {updated}")
print(f"매칭 안됨: {not_matched}")
print("=" * 60)
