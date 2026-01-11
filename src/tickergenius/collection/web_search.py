"""
Web Search Client
==================
웹 검색 폴백 클라이언트.

API 검색 실패 시 웹 검색으로 데이터를 찾습니다.
추론 금지 원칙에 따라, 찾지 못하면 NOT_FOUND로 기록합니다.

참조: docs/SEARCH_IMPROVEMENT_DESIGN.md
"""

import re
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from urllib.parse import quote_plus

import httpx

from .search_utils import (
    SearchQueryBuilder,
    SearchResultValidator,
    ValidationResult,
    extract_date_from_text,
)

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """웹 검색 결과."""
    found: bool
    value: Any = None
    date: Optional[str] = None  # YYYYMMDD
    source: Optional[str] = None
    url: Optional[str] = None
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)

    @classmethod
    def not_found(cls, searched_sources: list[str]) -> "WebSearchResult":
        return cls(found=False, searched_sources=searched_sources)


class WebSearchClient:
    """
    웹 검색 클라이언트.

    검색 체인:
    1. 도메인 제한 검색 (fda.gov, biospace.com 등)
    2. 일반 웹 검색
    3. 결과 검증 및 정보 추출

    주의: 추론 금지. 검색 결과에서 명확한 정보가 없으면 NOT_FOUND.
    """

    # DuckDuckGo Instant Answer API (무료, API 키 불필요)
    DDG_API_URL = "https://api.duckduckgo.com/"

    # DuckDuckGo HTML 검색 (파싱 필요)
    DDG_HTML_URL = "https://html.duckduckgo.com/html/"

    # 신뢰 도메인 (우선순위순)
    TRUSTED_NEWS_DOMAINS = [
        "biospace.com",
        "fiercepharma.com",
        "fiercebiotech.com",
        "reuters.com",
        "businesswire.com",
        "prnewswire.com",
        "globenewswire.com",
    ]

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._last_request_time = 0.0
        self._min_interval = 1.0  # 최소 1초 간격

    def _wait_rate_limit(self):
        """Rate limit 대기."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, url: str, params: dict = None) -> Optional[str]:
        """HTTP 요청 실행."""
        self._wait_rate_limit()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.debug(f"Web request failed: {url} - {e}")
            return None

    def _search_ddg_html(self, query: str) -> list[dict]:
        """
        DuckDuckGo HTML 검색.

        Returns:
            [{"title": str, "url": str, "snippet": str}]
        """
        self._wait_rate_limit()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.post(
                    self.DDG_HTML_URL,
                    data={"q": query, "b": ""},
                    headers=headers,
                )
                response.raise_for_status()
                return self._parse_ddg_html(response.text)
        except Exception as e:
            logger.debug(f"DuckDuckGo search failed: {e}")
            return []

    def _parse_ddg_html(self, html: str) -> list[dict]:
        """DuckDuckGo HTML 결과 파싱."""
        results = []

        # 결과 블록 추출
        # <a class="result__a" href="...">Title</a>
        # <a class="result__snippet">Snippet</a>
        title_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>',
            re.IGNORECASE
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>([^<]+)',
            re.IGNORECASE
        )

        # 간단한 파싱 (정확하지 않을 수 있음)
        blocks = re.split(r'<div[^>]*class="[^"]*result[^"]*"', html)

        for block in blocks[1:20]:  # 최대 20개
            title_match = title_pattern.search(block)
            if not title_match:
                continue

            url = title_match.group(1)
            title = title_match.group(2)

            # URL 디코딩 (DuckDuckGo는 리다이렉트 URL 사용)
            if "uddg=" in url:
                url_match = re.search(r'uddg=([^&]+)', url)
                if url_match:
                    from urllib.parse import unquote
                    url = unquote(url_match.group(1))

            snippet = ""
            snippet_match = snippet_pattern.search(block)
            if snippet_match:
                snippet = snippet_match.group(1)

            # HTML 엔티티 디코딩
            import html
            title = html.unescape(title)
            snippet = html.unescape(snippet)

            results.append({
                "title": title.strip(),
                "url": url,
                "snippet": snippet.strip(),
            })

        return results

    def search_crl_event(
        self,
        ticker: str,
        drug_name: str,
        before_date: str = None,
    ) -> WebSearchResult:
        """
        CRL 이벤트 검색.

        검색 순서:
        1. 도메인 제한 검색 (biospace.com, fiercepharma.com)
        2. 일반 검색

        Args:
            ticker: 티커 심볼
            drug_name: 약물명
            before_date: 이 날짜 이전의 CRL만 찾음 (YYYYMMDD)

        Returns:
            WebSearchResult
        """
        searched_sources = []
        drug_variants = SearchQueryBuilder.drug_name_variants(drug_name)
        brand = drug_variants[0] if drug_variants else drug_name

        # 검색 쿼리 구성
        queries = [
            # 1. 도메인 제한 검색
            f'site:biospace.com {ticker} "{brand}" CRL "complete response"',
            f'site:fiercepharma.com {ticker} "{brand}" FDA rejection CRL',
            f'site:fda.gov "{brand}" "complete response letter"',
            # 2. 일반 검색
            f'{ticker} "{brand}" FDA "complete response letter" CRL',
            f'{ticker} "{brand}" PDUFA CRL',
        ]

        for query in queries:
            searched_sources.append(f"web:{query[:50]}")
            results = self._search_ddg_html(query)

            for result in results:
                # CRL 관련 키워드 확인
                text = f"{result['title']} {result['snippet']}".upper()
                if not any(kw in text for kw in ["CRL", "COMPLETE RESPONSE", "REJECTION", "REFUSED"]):
                    continue

                # 티커 또는 약물명 확인
                ticker_found = ticker.upper() in text
                drug_found = any(v.upper() in text for v in drug_variants)

                if not (ticker_found or drug_found):
                    continue

                # 날짜 추출
                content = f"{result['title']} {result['snippet']}"
                date = extract_date_from_text(content)

                # 날짜 검증
                if date and before_date:
                    if date >= before_date.replace("-", ""):
                        continue  # before_date 이후면 스킵

                # 검증
                validation = SearchResultValidator.validate_crl_result(
                    {"date": date, "url": result["url"], "content": content},
                    ticker, drug_name, before_date
                )

                if validation.is_valid or validation.confidence > 0.5:
                    return WebSearchResult(
                        found=True,
                        value="crl",
                        date=date,
                        source="web_search",
                        url=result["url"],
                        confidence=validation.confidence,
                        evidence=[content[:500]],
                        searched_sources=searched_sources,
                    )

        return WebSearchResult.not_found(searched_sources)

    def search_designation(
        self,
        ticker: str,
        drug_name: str,
        designation_type: str,
    ) -> WebSearchResult:
        """
        FDA 지정 정보 검색.

        Args:
            designation_type: "btd", "orphan", "priority", "fast_track"

        Returns:
            WebSearchResult (value=True/False)
        """
        searched_sources = []
        drug_variants = SearchQueryBuilder.drug_name_variants(drug_name)
        brand = drug_variants[0] if drug_variants else drug_name

        # 지정 유형별 키워드
        designation_keywords = {
            "btd": ["breakthrough therapy", "BTD designation", "breakthrough designation"],
            "orphan": ["orphan drug", "orphan designation"],
            "priority": ["priority review"],
            "fast_track": ["fast track"],
        }

        keywords = designation_keywords.get(designation_type, [designation_type])
        keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)

        queries = [
            f'site:fda.gov "{brand}" {keyword_query}',
            f'site:biospace.com {ticker} "{brand}" {keywords[0]}',
            f'{ticker} "{brand}" FDA {keywords[0]} granted received',
        ]

        for query in queries:
            searched_sources.append(f"web:{query[:50]}")
            results = self._search_ddg_html(query)

            for result in results:
                text = f"{result['title']} {result['snippet']}".upper()

                # 지정 키워드 확인
                keyword_found = any(kw.upper() in text for kw in keywords)
                if not keyword_found:
                    continue

                # "granted", "received", "designated" 등 긍정적 표현 확인
                positive_terms = ["GRANTED", "RECEIVED", "DESIGNATED", "AWARDED", "OBTAINED"]
                is_positive = any(term in text for term in positive_terms)

                # 약물명 확인
                drug_found = any(v.upper() in text for v in drug_variants)
                ticker_found = ticker.upper() in text

                if not (drug_found or ticker_found):
                    continue

                # 날짜 추출
                content = f"{result['title']} {result['snippet']}"
                date = extract_date_from_text(content)

                # 신뢰도 계산
                confidence = 0.7
                if is_positive:
                    confidence += 0.15
                if "FDA.GOV" in result["url"].upper():
                    confidence = min(confidence + 0.15, 0.95)

                return WebSearchResult(
                    found=True,
                    value=True if is_positive else None,
                    date=date,
                    source="web_search",
                    url=result["url"],
                    confidence=confidence,
                    evidence=[content[:500]],
                    searched_sources=searched_sources,
                )

        return WebSearchResult.not_found(searched_sources)

    def search_adcom(
        self,
        ticker: str,
        drug_name: str,
    ) -> WebSearchResult:
        """
        AdCom (Advisory Committee) 정보 검색.

        Returns:
            WebSearchResult (value={"held": bool, "date": str, "vote_ratio": float})
        """
        searched_sources = []
        drug_variants = SearchQueryBuilder.drug_name_variants(drug_name)
        brand = drug_variants[0] if drug_variants else drug_name

        queries = [
            f'site:fda.gov "{brand}" "advisory committee" meeting',
            f'{ticker} "{brand}" FDA AdCom vote',
            f'{ticker} "{brand}" "advisory committee" recommendation',
        ]

        for query in queries:
            searched_sources.append(f"web:{query[:50]}")
            results = self._search_ddg_html(query)

            for result in results:
                text = f"{result['title']} {result['snippet']}".upper()

                # AdCom 키워드 확인
                if not any(kw in text for kw in ["ADVISORY COMMITTEE", "ADCOM", "FDA PANEL"]):
                    continue

                # 약물/티커 확인
                drug_found = any(v.upper() in text for v in drug_variants)
                ticker_found = ticker.upper() in text

                if not (drug_found or ticker_found):
                    continue

                content = f"{result['title']} {result['snippet']}"

                # 투표 비율 추출 시도 (예: "voted 10-2", "12 to 3")
                vote_ratio = self._extract_vote_ratio(content)

                # 날짜 추출
                date = extract_date_from_text(content)

                return WebSearchResult(
                    found=True,
                    value={
                        "held": True,
                        "date": date,
                        "vote_ratio": vote_ratio,
                    },
                    date=date,
                    source="web_search",
                    url=result["url"],
                    confidence=0.75 if vote_ratio else 0.6,
                    evidence=[content[:500]],
                    searched_sources=searched_sources,
                )

        return WebSearchResult.not_found(searched_sources)

    def _extract_vote_ratio(self, text: str) -> Optional[float]:
        """텍스트에서 투표 비율 추출."""
        # 패턴: "voted 10-2", "10 to 2", "10-2 vote"
        patterns = [
            r"voted?\s+(\d+)\s*[-to]+\s*(\d+)",
            r"(\d+)\s*[-to]+\s*(\d+)\s+vote",
            r"(\d+)\s+in favor.*?(\d+)\s+against",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                yes = int(match.group(1))
                no = int(match.group(2))
                if yes + no > 0:
                    return yes / (yes + no)

        return None

    def search_primary_endpoint(
        self,
        ticker: str,
        drug_name: str,
    ) -> WebSearchResult:
        """
        Primary endpoint 결과 검색.

        Returns:
            WebSearchResult (value=True/False for met/not met)
        """
        searched_sources = []
        drug_variants = SearchQueryBuilder.drug_name_variants(drug_name)
        brand = drug_variants[0] if drug_variants else drug_name

        queries = [
            f'{ticker} "{brand}" "primary endpoint" met achieved',
            f'{ticker} "{brand}" phase 3 results "statistically significant"',
            f'{ticker} "{brand}" trial "met primary"',
        ]

        positive_indicators = [
            "MET PRIMARY", "ACHIEVED PRIMARY", "POSITIVE RESULTS",
            "STATISTICALLY SIGNIFICANT", "ENDPOINT MET",
        ]
        negative_indicators = [
            "FAILED TO MEET", "DID NOT MEET", "MISSED PRIMARY",
            "NOT STATISTICALLY SIGNIFICANT", "NEGATIVE RESULTS",
        ]

        for query in queries:
            searched_sources.append(f"web:{query[:50]}")
            results = self._search_ddg_html(query)

            for result in results:
                text = f"{result['title']} {result['snippet']}".upper()

                # 약물/티커 확인
                drug_found = any(v.upper() in text for v in drug_variants)
                ticker_found = ticker.upper() in text

                if not (drug_found or ticker_found):
                    continue

                # Primary endpoint 관련 확인
                if "PRIMARY" not in text and "ENDPOINT" not in text:
                    continue

                content = f"{result['title']} {result['snippet']}"

                # 결과 판단
                is_positive = any(ind in text for ind in positive_indicators)
                is_negative = any(ind in text for ind in negative_indicators)

                if is_positive or is_negative:
                    return WebSearchResult(
                        found=True,
                        value=is_positive and not is_negative,
                        date=extract_date_from_text(content),
                        source="web_search",
                        url=result["url"],
                        confidence=0.7 if (is_positive != is_negative) else 0.5,
                        evidence=[content[:500]],
                        searched_sources=searched_sources,
                    )

        return WebSearchResult.not_found(searched_sources)

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Generic 웹 검색 - OnDemandSearcher 호환.

        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수

        Returns:
            [{"title": str, "url": str, "snippet": str}]
        """
        import asyncio

        # 동기 검색을 async로 래핑
        results = await asyncio.to_thread(self._search_ddg_html, query)
        return results[:max_results]
