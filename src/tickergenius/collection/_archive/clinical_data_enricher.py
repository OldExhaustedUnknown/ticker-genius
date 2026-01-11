"""
Clinical Data Enricher
======================
primary_endpoint_met, adcom_held, pai_passed 3개 필드 수집 전용.

SEC 8-K 본문 검색 기반으로 임상 결과/AdCom/PAI 정보 추출.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .api_clients import SECEdgarClient

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """수집 결과."""
    found: bool = False
    value: Optional[bool] = None  # True/False/None
    confidence: float = 0.0
    source: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    searched_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ClinicalDataEnricher:
    """
    임상 데이터 enricher.

    SEC 8-K 파일링에서 다음 정보를 추출:
    - primary_endpoint_met: 임상시험 primary endpoint 달성 여부
    - adcom_held: Advisory Committee 개최 여부
    - pai_passed: Pre-Approval Inspection 통과 여부/전적
    """

    # Primary Endpoint 키워드
    ENDPOINT_MET_KEYWORDS = [
        "met its primary endpoint",
        "met the primary endpoint",
        "achieved the primary endpoint",
        "achieved its primary endpoint",
        "primary endpoint was met",
        "statistically significant",
        "positive top-line results",
        "positive phase 3 results",
        "positive pivotal",
    ]

    ENDPOINT_MISSED_KEYWORDS = [
        "did not meet",
        "failed to meet",
        "did not achieve",
        "failed to achieve",
        "negative results",
        "did not reach statistical significance",
        "discontinued",
    ]

    # AdCom 키워드
    ADCOM_KEYWORDS = [
        "advisory committee",
        "advisory panel",
        "adcom",
        "FDA advisory",
        "ODAC",  # Oncologic Drugs Advisory Committee
        "CDER advisory",
        "voted in favor",
        "voted against",
        "recommended approval",
    ]

    # PAI 키워드
    PAI_KEYWORDS = [
        "pre-approval inspection",
        "preapproval inspection",
        "PAI",
        "manufacturing inspection",
        "FDA inspection",
        "facility inspection",
        "GMP inspection",
        "inspection completed",
        "passed inspection",
    ]

    PAI_WARNING_KEYWORDS = [
        "warning letter",
        "483 observation",
        "form 483",
        "inspection deficiency",
        "failed inspection",
    ]

    def __init__(self):
        self.sec_client = SECEdgarClient()

    def search_primary_endpoint(
        self,
        ticker: str,
        drug_name: str,
        before_date: str = None,  # PDUFA date 이전
    ) -> EnrichmentResult:
        """
        Primary endpoint 달성 여부 검색.

        Args:
            ticker: 티커 심볼
            drug_name: 약물명
            before_date: 이 날짜 이전 파일링만 검색 (YYYYMMDD)

        Returns:
            EnrichmentResult
        """
        result = EnrichmentResult()

        # 모든 endpoint 관련 키워드로 검색
        all_keywords = self.ENDPOINT_MET_KEYWORDS + self.ENDPOINT_MISSED_KEYWORDS

        try:
            filings = self.sec_client.search_8k_filings(
                ticker=ticker,
                keywords=all_keywords,
                before_date=before_date,
                limit=20,
            )
        except Exception as e:
            logger.warning(f"SEC search failed for {ticker}/{drug_name}: {e}")
            return result

        if not filings:
            return result

        # 각 파일링 분석
        for filing in filings[:10]:
            content = self._fetch_filing_content(filing)
            if not content:
                continue

            # 약물명이 언급된 파일링만 분석
            if drug_name and drug_name.lower() not in content.lower():
                continue

            # Positive/Negative 결과 판정
            met_score = sum(1 for kw in self.ENDPOINT_MET_KEYWORDS
                          if kw.lower() in content.lower())
            missed_score = sum(1 for kw in self.ENDPOINT_MISSED_KEYWORDS
                             if kw.lower() in content.lower())

            if met_score > 0 or missed_score > 0:
                result.found = True
                result.value = met_score > missed_score
                result.confidence = 0.80 if result.value else 0.75
                result.source = f"sec_8k:{filing.get('accessionNumber', '')}"
                result.evidence = self._extract_sentences(
                    content,
                    self.ENDPOINT_MET_KEYWORDS + self.ENDPOINT_MISSED_KEYWORDS,
                    max_sentences=3
                )
                break

        return result

    def search_adcom_held(
        self,
        ticker: str,
        drug_name: str,
        before_date: str = None,
    ) -> EnrichmentResult:
        """
        Advisory Committee 개최 여부 검색.

        Returns:
            EnrichmentResult (value=True if AdCom was held)
        """
        result = EnrichmentResult()

        try:
            filings = self.sec_client.search_8k_filings(
                ticker=ticker,
                keywords=self.ADCOM_KEYWORDS,
                before_date=before_date,
                limit=20,
            )
        except Exception as e:
            logger.warning(f"SEC search failed for {ticker}/{drug_name}: {e}")
            return result

        if not filings:
            return result

        for filing in filings[:10]:
            content = self._fetch_filing_content(filing)
            if not content:
                continue

            # 약물명 확인
            if drug_name and drug_name.lower() not in content.lower():
                continue

            # AdCom 키워드 확인
            adcom_mentions = sum(1 for kw in self.ADCOM_KEYWORDS
                                if kw.lower() in content.lower())

            if adcom_mentions > 0:
                result.found = True
                result.value = True  # AdCom이 개최됨
                result.confidence = 0.85
                result.source = f"sec_8k:{filing.get('accessionNumber', '')}"
                result.evidence = self._extract_sentences(
                    content, self.ADCOM_KEYWORDS, max_sentences=3
                )
                break

        return result

    def search_pai_status(
        self,
        ticker: str,
        drug_name: str,
        before_date: str = None,
    ) -> EnrichmentResult:
        """
        Pre-Approval Inspection 상태 검색.

        Returns:
            EnrichmentResult (value=True if passed, False if warning/issue, None if unknown)
        """
        result = EnrichmentResult()

        # PAI 관련 키워드 + 경고 키워드
        all_keywords = self.PAI_KEYWORDS + self.PAI_WARNING_KEYWORDS

        try:
            filings = self.sec_client.search_8k_filings(
                ticker=ticker,
                keywords=all_keywords,
                before_date=before_date,
                limit=20,
            )
        except Exception as e:
            logger.warning(f"SEC search failed for {ticker}/{drug_name}: {e}")
            return result

        if not filings:
            return result

        for filing in filings[:10]:
            content = self._fetch_filing_content(filing)
            if not content:
                continue

            # PAI 언급 확인
            pai_positive = sum(1 for kw in self.PAI_KEYWORDS
                              if kw.lower() in content.lower())
            pai_negative = sum(1 for kw in self.PAI_WARNING_KEYWORDS
                              if kw.lower() in content.lower())

            if pai_positive > 0 or pai_negative > 0:
                result.found = True

                # Warning letter가 있으면 negative
                if pai_negative > 0:
                    result.value = False
                    result.confidence = 0.80
                elif pai_positive > 0:
                    result.value = True
                    result.confidence = 0.70  # PAI 통과는 덜 명확함

                result.source = f"sec_8k:{filing.get('accessionNumber', '')}"
                result.evidence = self._extract_sentences(
                    content, all_keywords, max_sentences=3
                )
                break

        return result

    def enrich_event(
        self,
        ticker: str,
        drug_name: str,
        pdufa_date: str,  # YYYYMMDD format
    ) -> dict:
        """
        이벤트에 대해 3개 필드 모두 수집.

        Returns:
            {
                "primary_endpoint_met": EnrichmentResult,
                "adcom_held": EnrichmentResult,
                "pai_passed": EnrichmentResult,
            }
        """
        return {
            "primary_endpoint_met": self.search_primary_endpoint(
                ticker, drug_name, before_date=pdufa_date
            ),
            "adcom_held": self.search_adcom_held(
                ticker, drug_name, before_date=pdufa_date
            ),
            "pai_passed": self.search_pai_status(
                ticker, drug_name, before_date=pdufa_date
            ),
        }

    def _fetch_filing_content(self, filing: dict) -> Optional[str]:
        """SEC 파일링 본문 가져오기."""
        try:
            # primaryDocDescription이 있는 경우 그 문서를 가져옴
            documents = filing.get("documentFormatFiles", [])
            for doc in documents:
                if doc.get("type") == "8-K" or "8-K" in doc.get("description", ""):
                    url = doc.get("documentUrl")
                    if url:
                        return self.sec_client._fetch_document_content(url)

            # 첫 번째 문서 시도
            if documents:
                url = documents[0].get("documentUrl")
                if url:
                    return self.sec_client._fetch_document_content(url)
        except Exception as e:
            logger.debug(f"Failed to fetch filing content: {e}")

        return None

    def _extract_sentences(
        self,
        content: str,
        keywords: list[str],
        max_sentences: int = 3,
    ) -> list[str]:
        """키워드 포함 문장 추출."""
        sentences = []
        content_lower = content.lower()

        # 문장 단위로 분리 (간단한 휴리스틱)
        sent_pattern = r'[^.!?]*[.!?]'
        all_sentences = re.findall(sent_pattern, content)

        for sent in all_sentences:
            sent_lower = sent.lower()
            if any(kw.lower() in sent_lower for kw in keywords):
                # 정리
                clean_sent = ' '.join(sent.split())
                if len(clean_sent) > 50 and len(clean_sent) < 500:
                    sentences.append(clean_sent)
                    if len(sentences) >= max_sentences:
                        break

        return sentences
