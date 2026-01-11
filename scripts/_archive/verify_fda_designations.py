"""
Phase 2: OpenFDA API로 FDA Designation 검증
==========================================
BTD, Priority Review, Fast Track, Orphan Drug, Accelerated Approval 검증.

Tier 1 소스: OpenFDA API (99% 신뢰도)
"""
import json
import os
import time
import re
from datetime import datetime
from typing import Optional
import httpx

# OpenFDA API 설정
OPENFDA_BASE = "https://api.fda.gov/drug"
RATE_LIMIT_DELAY = 0.5  # 초

class OpenFDAClient:
    """OpenFDA API 클라이언트."""

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self._last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request = time.time()

    def search_drug(self, drug_name: str) -> Optional[dict]:
        """약물 검색."""
        self._rate_limit()

        # 약물명 정규화
        clean_name = re.sub(r'[^\w\s]', '', drug_name).strip()
        words = clean_name.split()
        if not words:
            return None

        # 첫 단어로 검색 (브랜드명)
        search_term = words[0]

        try:
            # drugsfda 엔드포인트 사용
            url = f"{OPENFDA_BASE}drugsfda.json"
            params = {
                "search": f'openfda.brand_name:"{search_term}"',
                "limit": 5,
            }
            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0]

            # generic name으로도 시도
            params["search"] = f'openfda.generic_name:"{search_term}"'
            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0]

        except Exception as e:
            print(f"  OpenFDA error for {drug_name}: {e}")

        return None

    def get_application_info(self, application_number: str) -> Optional[dict]:
        """NDA/BLA 번호로 상세 정보 조회."""
        self._rate_limit()

        try:
            url = f"{OPENFDA_BASE}drugsfda.json"
            params = {
                "search": f'application_number:"{application_number}"',
                "limit": 1,
            }
            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0]

        except Exception as e:
            print(f"  OpenFDA error for {application_number}: {e}")

        return None

    def close(self):
        self.client.close()


def extract_designations(fda_data: dict) -> dict:
    """FDA 데이터에서 designation 추출."""
    result = {
        'btd': None,
        'priority_review': None,
        'fast_track': None,
        'orphan_drug': None,
        'accelerated_approval': None,
        'generic_name': None,
        'application_number': None,
    }

    if not fda_data:
        return result

    # OpenFDA 필드에서 추출
    openfda = fda_data.get('openfda', {})

    # Generic name
    if openfda.get('generic_name'):
        result['generic_name'] = openfda['generic_name'][0].lower()

    # Application number
    if openfda.get('application_number'):
        result['application_number'] = openfda['application_number'][0]

    # Products/submissions에서 designation 확인
    products = fda_data.get('products', [])
    submissions = fda_data.get('submissions', [])

    for product in products:
        # Orphan drug
        if product.get('orphan_drug_status') == 'Yes':
            result['orphan_drug'] = True

    for submission in submissions:
        sub_type = submission.get('submission_type', '').upper()
        sub_status = submission.get('submission_status', '').upper()
        review_priority = submission.get('review_priority', '').upper()

        # Priority Review
        if 'PRIORITY' in review_priority:
            result['priority_review'] = True
        elif 'STANDARD' in review_priority:
            result['priority_review'] = False

        # Accelerated Approval (submission class code AA)
        if submission.get('submission_class_code') == 'AA':
            result['accelerated_approval'] = True

    # BTD, Fast Track은 OpenFDA에서 직접 제공되지 않음
    # FDA Orange Book 또는 별도 API 필요
    # 일단 None으로 유지 (NOT_FOUND)

    return result


def verify_single_event(event: dict, client: OpenFDAClient) -> dict:
    """단일 이벤트 검증."""
    drug_name = event.get('drug_name', '')
    ticker = event.get('ticker', '')

    updates = {}

    # OpenFDA 검색
    fda_data = client.search_drug(drug_name)

    if fda_data:
        designations = extract_designations(fda_data)
        now = datetime.now().isoformat()

        # Generic name
        if designations['generic_name']:
            updates['generic_name'] = {
                'status': 'found',
                'value': designations['generic_name'],
                'source': 'openfda_api',
                'confidence': 0.95,
                'tier': 1,
                'evidence': [f"OpenFDA generic_name field"],
                'searched_sources': ['openfda'],
                'last_searched': now,
                'error': None,
            }

        # Priority Review
        if designations['priority_review'] is not None:
            updates['priority_review'] = {
                'status': 'found',
                'value': designations['priority_review'],
                'source': 'openfda_api',
                'confidence': 0.95,
                'tier': 1,
                'evidence': [f"OpenFDA review_priority field"],
                'searched_sources': ['openfda'],
                'last_searched': now,
                'error': None,
                'needs_verification': False,  # 검증 완료
            }

        # Orphan Drug
        if designations['orphan_drug'] is not None:
            updates['orphan_drug'] = {
                'status': 'found',
                'value': designations['orphan_drug'],
                'source': 'openfda_api',
                'confidence': 0.95,
                'tier': 1,
                'evidence': [f"OpenFDA orphan_drug_status field"],
                'searched_sources': ['openfda'],
                'last_searched': now,
                'error': None,
                'needs_verification': False,
            }

        # Accelerated Approval
        if designations['accelerated_approval'] is not None:
            updates['accelerated_approval'] = {
                'status': 'found',
                'value': designations['accelerated_approval'],
                'source': 'openfda_api',
                'confidence': 0.95,
                'tier': 1,
                'evidence': [f"OpenFDA submission_class_code AA"],
                'searched_sources': ['openfda'],
                'last_searched': now,
                'error': None,
                'needs_verification': False,
            }

    return updates


def main():
    enriched_dir = 'data/enriched'
    files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

    client = OpenFDAClient()
    stats = {
        'verified': 0,
        'not_found': 0,
        'fields_updated': 0,
    }

    print("=" * 60)
    print("Phase 2: OpenFDA Designation 검증")
    print("=" * 60)

    try:
        for i, filename in enumerate(files):
            filepath = os.path.join(enriched_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                event = json.load(f)

            drug_name = event.get('drug_name', '')
            ticker = event.get('ticker', '')

            # 진행 상황 출력 (10개마다)
            if i % 10 == 0:
                print(f"[{i+1}/{len(files)}] Processing {ticker} - {drug_name[:30]}...")

            # OpenFDA 검증
            updates = verify_single_event(event, client)

            if updates:
                stats['verified'] += 1
                for field, data in updates.items():
                    event[field] = data
                    stats['fields_updated'] += 1

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(event, f, indent=2, ensure_ascii=False)
            else:
                stats['not_found'] += 1

    finally:
        client.close()

    print("=" * 60)
    print(f"검증 완료: {stats['verified']} events")
    print(f"OpenFDA에서 못찾음: {stats['not_found']} events")
    print(f"업데이트된 필드 수: {stats['fields_updated']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
