"""
DDG 고도화 FDA 데이터 수집기
===========================
DuckDuckGo 검색을 통해 FDA 공식 소스에서 데이터 수집.

수집 대상:
1. FDA Designations (BTD, Priority Review, Fast Track, Orphan Drug, Accelerated Approval)
2. Generic name
3. Phase
4. Safety signal
5. 483/Warning Letter/PAI

원칙:
- FDA.gov, ClinicalTrials.gov 등 공식 소스 우선
- 검색 결과에 약물명 명시 확인
- 출처 URL 기록
"""
import json
import os
import re
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List
from ddgs import DDGS

# Rate limit 설정
MIN_INTERVAL = 2.5  # 초


@dataclass
class FDASearchResult:
    """FDA 검색 결과."""
    # Designations
    btd: Optional[bool] = None
    priority_review: Optional[bool] = None
    fast_track: Optional[bool] = None
    orphan_drug: Optional[bool] = None
    accelerated_approval: Optional[bool] = None

    # Other fields
    generic_name: Optional[str] = None
    phase: Optional[str] = None
    safety_signal: Optional[bool] = None

    # Manufacturing
    has_483: Optional[bool] = None
    warning_letter: Optional[bool] = None
    pai_passed: Optional[bool] = None

    # Metadata
    found_any: bool = False
    sources: List[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


class DDGFDACollector:
    """DDG 기반 FDA 데이터 수집기."""

    # FDA 공식 소스 도메인
    FDA_DOMAINS = [
        'fda.gov',
        'accessdata.fda.gov',
        'clinicaltrials.gov',
    ]

    # Designation 패턴
    DESIGNATION_PATTERNS = {
        'btd': [
            r'breakthrough\s+therapy\s+designation',
            r'granted\s+breakthrough',
            r'received\s+breakthrough',
            r'BTD\s+(?:granted|received|designation)',
        ],
        'priority_review': [
            r'priority\s+review\s+(?:designation|status|granted)',
            r'granted\s+priority\s+review',
            r'received\s+priority\s+review',
        ],
        'fast_track': [
            r'fast\s+track\s+(?:designation|status|granted)',
            r'granted\s+fast\s+track',
            r'received\s+fast\s+track',
        ],
        'orphan_drug': [
            r'orphan\s+drug\s+(?:designation|status|granted)',
            r'granted\s+orphan',
            r'received\s+orphan',
            r'orphan\s+(?:disease|condition)',
        ],
        'accelerated_approval': [
            r'accelerated\s+approval',
            r'received\s+accelerated',
            r'granted\s+under\s+accelerated',
            r'approved\s+under\s+accelerated',
        ],
    }

    # Phase 패턴
    PHASE_PATTERNS = [
        (r'phase\s*(?:3|iii|three)\b', 'Phase 3'),
        (r'phase\s*(?:2|ii|two)\b', 'Phase 2'),
        (r'phase\s*(?:1|i|one)\b', 'Phase 1'),
        (r'pivotal\s+(?:trial|study)', 'Phase 3'),
        (r'registration\s+(?:trial|study)', 'Phase 3'),
    ]

    # Safety signal 패턴
    SAFETY_NEGATIVE_PATTERNS = [
        r'clinical\s+hold',
        r'safety\s+concern',
        r'black\s+box\s+warning',
        r'boxed\s+warning',
        r'serious\s+adverse',
        r'safety\s+signal',
        r'hepatotoxicity',
        r'cardiotoxicity',
        r'death(?:s)?\s+(?:reported|observed)',
    ]

    # Manufacturing/483 패턴
    MANUFACTURING_PATTERNS = {
        '483': [
            r'form\s*483',
            r'483\s+observation',
            r'inspection\s+observation',
        ],
        'warning_letter': [
            r'warning\s+letter',
            r'FDA\s+warning',
        ],
        'pai_passed': [
            r'pre-?approval\s+inspection\s+(?:passed|completed|successful)',
            r'PAI\s+(?:passed|completed|successful)',
            r'manufacturing\s+(?:facility|site)\s+(?:approved|cleared)',
        ],
    }

    def __init__(self):
        self._last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        self._last_request = time.time()

    def _search_ddg(self, query: str, max_results: int = 10) -> List[dict]:
        """DDG 검색 실행."""
        self._rate_limit()
        try:
            results = DDGS().text(query, max_results=max_results)
            return list(results)
        except Exception as e:
            print(f"  DDG error: {e}")
            return []

    def _normalize_drug_name(self, drug_name: str) -> str:
        """약물명 정규화."""
        # 괄호 내용 제거
        name = re.sub(r'\s*\([^)]*\)', '', drug_name)
        # 특수문자 제거
        name = re.sub(r'[^\w\s-]', '', name)
        return name.strip()

    def _drug_mentioned(self, text: str, drug_name: str) -> bool:
        """텍스트에 약물명 언급 확인."""
        text_lower = text.lower()
        normalized = self._normalize_drug_name(drug_name).lower()

        # 정규화된 이름 확인
        if normalized in text_lower:
            return True

        # 첫 단어만 확인 (브랜드명)
        first_word = normalized.split()[0] if normalized else ''
        if first_word and len(first_word) > 3 and first_word in text_lower:
            return True

        return False

    def _is_fda_source(self, url: str) -> bool:
        """FDA 공식 소스 여부."""
        return any(domain in url.lower() for domain in self.FDA_DOMAINS)

    def collect(self, ticker: str, drug_name: str, pdufa_date: str = None) -> FDASearchResult:
        """FDA 데이터 수집."""
        result = FDASearchResult()
        normalized_name = self._normalize_drug_name(drug_name)
        year = pdufa_date[:4] if pdufa_date and len(pdufa_date) >= 4 else ''

        # 1. FDA designation 검색
        self._collect_designations(result, normalized_name, year)

        # 2. Phase 검색
        self._collect_phase(result, normalized_name, year)

        # 3. Safety signal 검색
        self._collect_safety(result, normalized_name, year)

        # 4. Manufacturing/483 검색
        self._collect_manufacturing(result, normalized_name, ticker)

        # 5. Generic name 검색
        self._collect_generic_name(result, normalized_name)

        result.found_any = any([
            result.btd is not None,
            result.priority_review is not None,
            result.fast_track is not None,
            result.orphan_drug is not None,
            result.accelerated_approval is not None,
            result.generic_name is not None,
            result.phase is not None,
            result.safety_signal is not None,
        ])

        return result

    def _collect_designations(self, result: FDASearchResult, drug_name: str, year: str):
        """FDA designation 수집."""
        queries = [
            f'"{drug_name}" FDA breakthrough therapy designation site:fda.gov',
            f'"{drug_name}" FDA priority review fast track orphan {year}',
            f'"{drug_name}" FDA accelerated approval designation',
        ]

        for query in queries:
            search_results = self._search_ddg(query, max_results=5)

            for r in search_results:
                title = r.get('title', '')
                body = r.get('body', '')
                url = r.get('href', '')
                combined = f"{title} {body}".lower()

                # 약물명 확인
                if not self._drug_mentioned(combined, drug_name):
                    continue

                is_fda = self._is_fda_source(url)

                # Designation 패턴 매칭
                for designation, patterns in self.DESIGNATION_PATTERNS.items():
                    if getattr(result, designation) is not None:
                        continue

                    for pattern in patterns:
                        if re.search(pattern, combined, re.I):
                            setattr(result, designation, True)
                            result.sources.append(url)
                            result.evidence[designation] = {
                                'text': body[:200],
                                'url': url,
                                'is_fda_source': is_fda,
                            }
                            break

    def _collect_phase(self, result: FDASearchResult, drug_name: str, year: str):
        """Phase 수집."""
        if result.phase:
            return

        query = f'"{drug_name}" clinical trial phase {year}'
        search_results = self._search_ddg(query, max_results=5)

        for r in search_results:
            title = r.get('title', '')
            body = r.get('body', '')
            url = r.get('href', '')
            combined = f"{title} {body}".lower()

            if not self._drug_mentioned(combined, drug_name):
                continue

            for pattern, phase_val in self.PHASE_PATTERNS:
                if re.search(pattern, combined, re.I):
                    result.phase = phase_val
                    result.sources.append(url)
                    result.evidence['phase'] = {
                        'text': body[:200],
                        'url': url,
                    }
                    return

    def _collect_safety(self, result: FDASearchResult, drug_name: str, year: str):
        """Safety signal 수집."""
        query = f'"{drug_name}" FDA safety concern clinical hold warning {year}'
        search_results = self._search_ddg(query, max_results=5)

        safety_mentions = 0
        for r in search_results:
            title = r.get('title', '')
            body = r.get('body', '')
            url = r.get('href', '')
            combined = f"{title} {body}".lower()

            if not self._drug_mentioned(combined, drug_name):
                continue

            for pattern in self.SAFETY_NEGATIVE_PATTERNS:
                if re.search(pattern, combined, re.I):
                    safety_mentions += 1
                    result.sources.append(url)
                    result.evidence['safety_signal'] = {
                        'text': body[:200],
                        'url': url,
                        'pattern': pattern,
                    }
                    break

        # 2개 이상 소스에서 safety concern 언급 시 True
        if safety_mentions >= 2:
            result.safety_signal = True
        elif safety_mentions == 0 and len(search_results) > 0:
            # 검색했지만 safety 문제 없음
            result.safety_signal = False

    def _collect_manufacturing(self, result: FDASearchResult, drug_name: str, ticker: str):
        """Manufacturing/483 정보 수집."""
        # 회사 기반 483 검색
        query = f'{ticker} "{drug_name}" FDA 483 warning letter manufacturing site:fda.gov'
        search_results = self._search_ddg(query, max_results=5)

        for r in search_results:
            title = r.get('title', '')
            body = r.get('body', '')
            url = r.get('href', '')
            combined = f"{title} {body}".lower()

            # 483 패턴
            for pattern in self.MANUFACTURING_PATTERNS['483']:
                if re.search(pattern, combined, re.I):
                    result.has_483 = True
                    result.evidence['483'] = {'url': url, 'text': body[:200]}
                    break

            # Warning letter 패턴
            for pattern in self.MANUFACTURING_PATTERNS['warning_letter']:
                if re.search(pattern, combined, re.I):
                    result.warning_letter = True
                    result.evidence['warning_letter'] = {'url': url, 'text': body[:200]}
                    break

    def _collect_generic_name(self, result: FDASearchResult, drug_name: str):
        """Generic name 수집."""
        query = f'"{drug_name}" generic name active ingredient site:fda.gov OR site:drugs.com'
        search_results = self._search_ddg(query, max_results=3)

        for r in search_results:
            body = r.get('body', '').lower()
            url = r.get('href', '')

            # "generic name:" 또는 "active ingredient:" 패턴
            match = re.search(
                r'(?:generic\s+name|active\s+ingredient)[:\s]+([a-z][a-z\s\-]+?)(?:\.|,|\s+is|\s+\()',
                body
            )
            if match:
                generic = match.group(1).strip()
                if len(generic) > 3 and len(generic) < 50:
                    result.generic_name = generic
                    result.sources.append(url)
                    result.evidence['generic_name'] = {'url': url, 'text': generic}
                    return


def update_event_from_ddg(event: dict, ddg_result: FDASearchResult) -> dict:
    """DDG 결과로 이벤트 업데이트."""
    now = datetime.now().isoformat()
    updates = {}

    # Designation 필드들
    designation_fields = ['btd', 'priority_review', 'fast_track', 'orphan_drug', 'accelerated_approval']

    for field_name in designation_fields:
        value = getattr(ddg_result, field_name)
        evidence = ddg_result.evidence.get(field_name, {})

        if value is not None:
            updates[field_name] = {
                'status': 'found',
                'value': value,
                'source': 'ddg_fda_search',
                'confidence': 0.85 if evidence.get('is_fda_source') else 0.75,
                'tier': 2,
                'evidence': [evidence.get('text', '')[:200]],
                'source_url': evidence.get('url', ''),
                'searched_sources': ['ddg', 'fda.gov'],
                'last_searched': now,
                'error': None,
                'needs_verification': False,
            }
        else:
            # 기존에 레거시 데이터가 있으면 그대로 유지하되 검증 시도했음 표시
            if field_name in event and event[field_name].get('needs_verification'):
                event[field_name]['ddg_search_attempted'] = True
                event[field_name]['ddg_search_at'] = now

    # Generic name
    if ddg_result.generic_name:
        updates['generic_name'] = {
            'status': 'found',
            'value': ddg_result.generic_name,
            'source': 'ddg_fda_search',
            'confidence': 0.8,
            'tier': 2,
            'evidence': [ddg_result.evidence.get('generic_name', {}).get('text', '')],
            'source_url': ddg_result.evidence.get('generic_name', {}).get('url', ''),
            'searched_sources': ['ddg'],
            'last_searched': now,
            'error': None,
        }

    # Phase
    if ddg_result.phase:
        updates['phase'] = {
            'status': 'found',
            'value': ddg_result.phase,
            'source': 'ddg_clinical_search',
            'confidence': 0.8,
            'tier': 2,
            'evidence': [ddg_result.evidence.get('phase', {}).get('text', '')[:200]],
            'source_url': ddg_result.evidence.get('phase', {}).get('url', ''),
            'searched_sources': ['ddg'],
            'last_searched': now,
            'error': None,
        }

    # Safety signal
    if ddg_result.safety_signal is not None:
        updates['safety_signal'] = {
            'status': 'found',
            'value': ddg_result.safety_signal,
            'source': 'ddg_safety_search',
            'confidence': 0.7 if ddg_result.safety_signal else 0.6,
            'tier': 3,
            'evidence': [ddg_result.evidence.get('safety_signal', {}).get('text', '')[:200]],
            'searched_sources': ['ddg'],
            'last_searched': now,
            'error': None,
        }

    # Warning letter
    if ddg_result.warning_letter is not None:
        updates['warning_letter'] = {
            'status': 'found',
            'value': ddg_result.warning_letter,
            'source': 'ddg_manufacturing_search',
            'confidence': 0.75,
            'tier': 2,
            'evidence': [ddg_result.evidence.get('warning_letter', {}).get('text', '')[:200]],
            'searched_sources': ['ddg', 'fda.gov'],
            'last_searched': now,
            'error': None,
        }

    return updates


def main():
    enriched_dir = 'data/enriched'
    files = sorted([f for f in os.listdir(enriched_dir) if f.endswith('.json')])

    collector = DDGFDACollector()

    stats = {
        'processed': 0,
        'found': 0,
        'fields_updated': 0,
    }

    print("=" * 60)
    print("DDG FDA Data Collection")
    print("=" * 60)

    for i, filename in enumerate(files):
        filepath = os.path.join(enriched_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            event = json.load(f)

        ticker = event.get('ticker', '')
        drug_name = event.get('drug_name', '')
        pdufa_date = event.get('pdufa_date', '')

        print(f"[{i+1}/{len(files)}] {ticker} - {drug_name[:40]}...")

        # DDG 검색
        ddg_result = collector.collect(ticker, drug_name, pdufa_date)

        if ddg_result.found_any:
            stats['found'] += 1

            # 이벤트 업데이트
            updates = update_event_from_ddg(event, ddg_result)

            for field_name, field_data in updates.items():
                event[field_name] = field_data
                stats['fields_updated'] += 1

            # 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(event, f, indent=2, ensure_ascii=False)

        stats['processed'] += 1

        # 중간 진행상황 (50개마다)
        if (i + 1) % 50 == 0:
            print(f"  Progress: {stats['processed']}/{len(files)}, Found: {stats['found']}, Fields: {stats['fields_updated']}")

    print("=" * 60)
    print(f"처리 완료: {stats['processed']} events")
    print(f"데이터 찾음: {stats['found']} events")
    print(f"업데이트된 필드: {stats['fields_updated']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
