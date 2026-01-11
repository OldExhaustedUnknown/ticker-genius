"""
DDG Clinical Searcher
=====================
DuckDuckGo 기반 임상 데이터 검색.

ddgs 라이브러리를 사용해서 primary_endpoint, p-value, adcom 정보 검색.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ddgs import DDGS

logger = logging.getLogger(__name__)


@dataclass
class DDGSearchResult:
    """DDG 검색 결과."""
    found: bool = False
    value: any = None
    confidence: float = 0.0
    source: str = ""
    evidence: list[str] = field(default_factory=list)
    p_value: Optional[str] = None
    adcom_held: Optional[bool] = None
    adcom_vote: Optional[str] = None


class DDGClinicalSearcher:
    """
    DuckDuckGo 기반 임상 데이터 검색기.

    수집 항목:
    - primary_endpoint_met: 1차 평가지표 달성 여부
    - p_value: 통계적 유의성
    - adcom_held: Advisory Committee 개최 여부
    """

    # Rate limit: 요청 간 최소 간격 (초)
    MIN_INTERVAL = 2.0

    # Primary Endpoint 패턴
    ENDPOINT_MET_PATTERNS = [
        r"met\s+(?:its\s+)?primary\s+endpoint",
        r"achieved\s+(?:its\s+)?primary\s+endpoint",
        r"primary\s+endpoint\s+(?:was\s+)?met",
        r"positive\s+(?:top-?line|phase\s*[23])\s+results?",
        r"statistically\s+significant",
    ]

    ENDPOINT_MISSED_PATTERNS = [
        r"did\s+not\s+meet\s+(?:its\s+)?primary\s+endpoint",
        r"failed\s+to\s+(?:meet|achieve)",
        r"negative\s+(?:top-?line|phase\s*[23])\s+results?",
        r"discontinued",
    ]

    # P-value 패턴
    PVALUE_PATTERNS = [
        r"p\s*[=<]\s*(0\.\d+)",
        r"p\s*[-]?\s*value\s*(?:of|=|:)?\s*(0\.\d+)",
        r"p\s*<\s*(0\.0+1)",
    ]

    # AdCom 패턴
    ADCOM_PATTERNS = [
        r"advisory\s+committee",
        r"adcom",
        r"FDA\s+advisory",
        r"voted\s+(?:\d+\s*[-–]\s*\d+)",
        r"recommended\s+approval",
    ]

    def __init__(self):
        self._last_request = 0

    def _rate_limit(self):
        """Rate limit 적용."""
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - elapsed)
        self._last_request = time.time()

    def search_clinical_data(
        self,
        ticker: str,
        drug_name: str,
    ) -> DDGSearchResult:
        """
        임상 데이터 검색.

        Args:
            ticker: 티커 심볼
            drug_name: 약물명

        Returns:
            DDGSearchResult
        """
        result = DDGSearchResult()

        # 검색 쿼리 구성
        queries = [
            f"{ticker} {drug_name} phase 3 primary endpoint met",
            f"{drug_name} clinical trial results p-value",
        ]

        all_text = []

        for query in queries:
            try:
                self._rate_limit()
                search_results = DDGS().text(query, max_results=5)

                for r in search_results:
                    text = f"{r.get('title', '')} {r.get('body', '')}"
                    all_text.append(text)
                    result.evidence.append(r.get('body', '')[:200])

            except Exception as e:
                logger.warning(f"DDG search failed for '{query}': {e}")
                continue

        if not all_text:
            return result

        combined_text = " ".join(all_text).lower()

        # Primary endpoint 분석
        met_count = sum(1 for p in self.ENDPOINT_MET_PATTERNS
                        if re.search(p, combined_text, re.IGNORECASE))
        missed_count = sum(1 for p in self.ENDPOINT_MISSED_PATTERNS
                           if re.search(p, combined_text, re.IGNORECASE))

        if met_count > 0 or missed_count > 0:
            result.found = True
            result.value = met_count > missed_count
            result.confidence = min(0.9, 0.6 + (met_count - missed_count) * 0.1)
            result.source = "ddg_search"

        # P-value 추출
        for pattern in self.PVALUE_PATTERNS:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                result.p_value = match.group(1) if match.lastindex else match.group(0)
                break

        # AdCom 확인
        adcom_mentions = sum(1 for p in self.ADCOM_PATTERNS
                             if re.search(p, combined_text, re.IGNORECASE))
        if adcom_mentions > 0:
            result.adcom_held = True

            # 투표 결과 추출
            vote_match = re.search(r"voted?\s+(\d+)\s*[-–]\s*(\d+)", combined_text)
            if vote_match:
                result.adcom_vote = f"{vote_match.group(1)}-{vote_match.group(2)}"

        return result

    def search_approval_type(
        self,
        ticker: str,
        drug_name: str,
    ) -> tuple[Optional[str], float]:
        """
        Approval type 검색 (NDA/BLA/ANDA).

        Returns:
            (approval_type, confidence)
        """
        try:
            self._rate_limit()
            query = f"{ticker} {drug_name} FDA NDA BLA application filing"
            results = DDGS().text(query, max_results=5)

            combined_text = " ".join(
                f"{r.get('title', '')} {r.get('body', '')}"
                for r in results
            ).lower()

            # NDA/BLA/ANDA 패턴
            if re.search(r"\b(bla|biologics?\s+license)\b", combined_text):
                return "bla", 0.8
            if re.search(r"\b(anda|abbreviated|generic)\b", combined_text):
                return "anda", 0.8
            if re.search(r"\b(snda|sbla|supplemental)\b", combined_text):
                return "snda", 0.8
            if re.search(r"\b(nda|new\s+drug\s+application)\b", combined_text):
                return "nda", 0.8

        except Exception as e:
            logger.warning(f"DDG approval type search failed: {e}")

        return None, 0.0


def enrich_with_ddg(
    ticker: str,
    drug_name: str,
) -> dict:
    """
    DDG로 임상 데이터 enrichment.

    Returns:
        {
            "primary_endpoint_met": bool or None,
            "p_value": str or None,
            "adcom_held": bool or None,
            "adcom_vote": str or None,
            "approval_type": str or None,
            "confidence": float,
            "evidence": list[str],
        }
    """
    searcher = DDGClinicalSearcher()

    # 임상 데이터 검색
    clinical = searcher.search_clinical_data(ticker, drug_name)

    # Approval type 검색
    approval_type, type_conf = searcher.search_approval_type(ticker, drug_name)

    return {
        "primary_endpoint_met": clinical.value if clinical.found else None,
        "p_value": clinical.p_value,
        "adcom_held": clinical.adcom_held,
        "adcom_vote": clinical.adcom_vote,
        "approval_type": approval_type,
        "confidence": clinical.confidence,
        "evidence": clinical.evidence[:3],  # 상위 3개만
    }
