"""
Search Chain Orchestrator
==========================
검색 체인 오케스트레이터.

API → 웹서치 폴백 흐름을 관리합니다.
추론 금지 원칙: 모든 소스에서 못 찾으면 NOT_FOUND로 기록합니다.

검색 체인:
1. SEC 8-K 본문 검색 (Tier 1)
2. FDA 공식 웹페이지 검색 (Tier 1)
3. 뉴스 웹서치 (Tier 2)
4. 일반 웹서치 (Tier 3)
5. 데이터 없음으로 기록 (절대 추론 안함)

참조: docs/SEARCH_IMPROVEMENT_DESIGN.md
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING

from .models import SearchStatus
from .web_search import WebSearchClient, WebSearchResult

if TYPE_CHECKING:
    from .api_clients import DesignationSearchClient, SECEdgarClient

logger = logging.getLogger(__name__)


@dataclass
class SearchChainResult:
    """검색 체인 결과."""
    status: SearchStatus
    value: Any = None
    source: Optional[str] = None
    source_tier: int = 4  # 1=공식, 2=뉴스, 3=웹, 4=없음
    confidence: float = 0.0
    date: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)

    @classmethod
    def found(
        cls,
        value: Any,
        source: str,
        source_tier: int,
        confidence: float,
        date: str = None,
        evidence: list[str] = None,
        searched_sources: list[str] = None,
    ) -> "SearchChainResult":
        return cls(
            status=SearchStatus.FOUND,
            value=value,
            source=source,
            source_tier=source_tier,
            confidence=confidence,
            date=date,
            evidence=evidence or [],
            searched_sources=searched_sources or [],
        )

    @classmethod
    def not_found(cls, searched_sources: list[str]) -> "SearchChainResult":
        return cls(
            status=SearchStatus.NOT_FOUND,
            searched_sources=searched_sources,
        )

    @classmethod
    def confirmed_none(cls, source: str, searched_sources: list[str]) -> "SearchChainResult":
        """공식 소스에서 없음 확인."""
        return cls(
            status=SearchStatus.CONFIRMED_NONE,
            source=source,
            source_tier=1,
            confidence=1.0,
            searched_sources=searched_sources,
        )


class SearchChainOrchestrator:
    """
    검색 체인 오케스트레이터.

    모든 검색에서 일관된 폴백 로직을 적용합니다.

    Usage:
        orchestrator = SearchChainOrchestrator()
        result = orchestrator.search_btd("AXSM", "AXS-05")
        if result.status == SearchStatus.FOUND:
            print(f"BTD: {result.value} from {result.source}")
    """

    def __init__(
        self,
        designation_client: "DesignationSearchClient" = None,
        sec_client: "SECEdgarClient" = None,
        web_client: WebSearchClient = None,
    ):
        """
        Args:
            designation_client: SEC 8-K 지정 검색 클라이언트
            sec_client: SEC EDGAR 클라이언트
            web_client: 웹 검색 클라이언트
        """
        self.designation_client = designation_client
        self.sec_client = sec_client
        self.web_client = web_client or WebSearchClient()

    def search_btd(
        self,
        ticker: str,
        drug_name: str,
        start_date: str = None,
    ) -> SearchChainResult:
        """
        Breakthrough Therapy Designation 검색.

        체인:
        1. SEC 8-K 본문 검색
        2. 웹 검색

        Args:
            ticker: 티커 심볼
            drug_name: 약물명
            start_date: 검색 시작 날짜 (YYYY-MM-DD)

        Returns:
            SearchChainResult
        """
        searched = []

        # 1. SEC 8-K 검색 (Tier 1)
        if self.designation_client:
            searched.append("sec_8k")
            try:
                result = self.designation_client.search_btd_designation(
                    ticker=ticker,
                    drug_name=drug_name,
                    start_date=start_date,
                )
                if result.get("has_btd") is not None:
                    return SearchChainResult.found(
                        value=result["has_btd"],
                        source=result.get("source", "sec_8k"),
                        source_tier=1,
                        confidence=result.get("confidence", 0.85),
                        date=result.get("designation_date"),
                        evidence=result.get("evidence", []),
                        searched_sources=searched,
                    )
            except Exception as e:
                logger.warning(f"SEC BTD search failed for {ticker}: {e}")

        # 2. 웹 검색 (Tier 2-3)
        searched.append("web_search")
        web_result = self.web_client.search_designation(
            ticker=ticker,
            drug_name=drug_name,
            designation_type="btd",
        )

        if web_result.found:
            return SearchChainResult.found(
                value=web_result.value,
                source=web_result.source,
                source_tier=2 if "fda.gov" in (web_result.url or "").lower() else 3,
                confidence=web_result.confidence,
                date=web_result.date,
                evidence=web_result.evidence,
                searched_sources=searched + web_result.searched_sources,
            )

        return SearchChainResult.not_found(searched + web_result.searched_sources)

    def search_orphan_drug(
        self,
        ticker: str,
        drug_name: str,
        start_date: str = None,
    ) -> SearchChainResult:
        """Orphan Drug Designation 검색."""
        searched = []

        # 1. SEC 8-K 검색
        if self.designation_client:
            searched.append("sec_8k")
            try:
                result = self.designation_client.search_orphan_designation(
                    ticker=ticker,
                    drug_name=drug_name,
                    start_date=start_date,
                )
                if result.get("has_orphan") is not None:
                    return SearchChainResult.found(
                        value=result["has_orphan"],
                        source=result.get("source", "sec_8k"),
                        source_tier=1,
                        confidence=result.get("confidence", 0.85),
                        date=result.get("designation_date"),
                        evidence=result.get("evidence", []),
                        searched_sources=searched,
                    )
            except Exception as e:
                logger.warning(f"SEC orphan search failed for {ticker}: {e}")

        # 2. 웹 검색
        searched.append("web_search")
        web_result = self.web_client.search_designation(
            ticker=ticker,
            drug_name=drug_name,
            designation_type="orphan",
        )

        if web_result.found:
            return SearchChainResult.found(
                value=web_result.value,
                source=web_result.source,
                source_tier=2 if "fda.gov" in (web_result.url or "").lower() else 3,
                confidence=web_result.confidence,
                date=web_result.date,
                evidence=web_result.evidence,
                searched_sources=searched + web_result.searched_sources,
            )

        return SearchChainResult.not_found(searched + web_result.searched_sources)

    def search_priority_review(
        self,
        ticker: str,
        drug_name: str,
        start_date: str = None,
    ) -> SearchChainResult:
        """Priority Review 검색."""
        searched = []

        # 1. SEC 8-K 검색
        if self.designation_client:
            searched.append("sec_8k")
            try:
                result = self.designation_client.search_priority_review(
                    ticker=ticker,
                    drug_name=drug_name,
                    start_date=start_date,
                )
                if result.get("has_priority_review") is not None:
                    return SearchChainResult.found(
                        value=result["has_priority_review"],
                        source=result.get("source", "sec_8k"),
                        source_tier=1,
                        confidence=result.get("confidence", 0.85),
                        date=result.get("designation_date"),
                        evidence=result.get("evidence", []),
                        searched_sources=searched,
                    )
            except Exception as e:
                logger.warning(f"SEC priority review search failed for {ticker}: {e}")

        # 2. 웹 검색
        searched.append("web_search")
        web_result = self.web_client.search_designation(
            ticker=ticker,
            drug_name=drug_name,
            designation_type="priority",
        )

        if web_result.found:
            return SearchChainResult.found(
                value=web_result.value,
                source=web_result.source,
                source_tier=2 if "fda.gov" in (web_result.url or "").lower() else 3,
                confidence=web_result.confidence,
                date=web_result.date,
                evidence=web_result.evidence,
                searched_sources=searched + web_result.searched_sources,
            )

        return SearchChainResult.not_found(searched + web_result.searched_sources)

    def search_crl_events(
        self,
        ticker: str,
        drug_name: str,
        before_date: str = None,
    ) -> list[SearchChainResult]:
        """
        CRL 이벤트 검색.

        추론 금지: 검색으로 찾은 CRL만 반환합니다.

        Args:
            ticker: 티커 심볼
            drug_name: 약물명
            before_date: 이 날짜 이전의 CRL만 (YYYYMMDD)

        Returns:
            CRL 이벤트 리스트 (시간순)
        """
        crl_events = []
        searched = []

        # 1. SEC 8-K 검색
        if self.sec_client:
            searched.append("sec_8k")
            try:
                filings = self.sec_client.search_8k_filings(
                    ticker=ticker,
                    keywords=["complete response letter", "CRL", "FDA rejection"],
                    start_date="2010-01-01",
                )

                for filing in filings:
                    info = self.sec_client.extract_pdufa_info(filing)
                    if info.get("has_crl"):
                        filing_date = filing.get("filingDate", "").replace("-", "")

                        # before_date 검증
                        if before_date and filing_date >= before_date.replace("-", ""):
                            continue

                        crl_events.append(SearchChainResult.found(
                            value="crl",
                            source=f"sec_8k:{filing.get('accessionNumber', '')}",
                            source_tier=1,
                            confidence=0.85,
                            date=filing_date,
                            evidence=info.get("detected_keywords", []),
                            searched_sources=["sec_8k"],
                        ))
            except Exception as e:
                logger.warning(f"SEC CRL search failed for {ticker}: {e}")

        # 2. 웹 검색 (SEC에서 못 찾은 경우)
        if not crl_events:
            searched.append("web_search")
            web_result = self.web_client.search_crl_event(
                ticker=ticker,
                drug_name=drug_name,
                before_date=before_date,
            )

            if web_result.found:
                crl_events.append(SearchChainResult.found(
                    value="crl",
                    source=web_result.source,
                    source_tier=3,
                    confidence=web_result.confidence,
                    date=web_result.date,
                    evidence=web_result.evidence,
                    searched_sources=searched + web_result.searched_sources,
                ))

        # 날짜순 정렬
        crl_events.sort(key=lambda e: e.date or "")

        return crl_events

    def search_adcom(
        self,
        ticker: str,
        drug_name: str,
    ) -> SearchChainResult:
        """Advisory Committee 정보 검색."""
        searched = []

        # 1. 웹 검색 (FDA AdCom API 없음)
        searched.append("web_search")
        web_result = self.web_client.search_adcom(
            ticker=ticker,
            drug_name=drug_name,
        )

        if web_result.found:
            return SearchChainResult.found(
                value=web_result.value,
                source=web_result.source,
                source_tier=2 if "fda.gov" in (web_result.url or "").lower() else 3,
                confidence=web_result.confidence,
                date=web_result.date,
                evidence=web_result.evidence,
                searched_sources=searched + web_result.searched_sources,
            )

        return SearchChainResult.not_found(searched + web_result.searched_sources)

    def search_primary_endpoint(
        self,
        ticker: str,
        drug_name: str,
    ) -> SearchChainResult:
        """Primary endpoint 결과 검색."""
        searched = []

        # 웹 검색 (ClinicalTrials.gov API 차단 대응)
        searched.append("web_search")
        web_result = self.web_client.search_primary_endpoint(
            ticker=ticker,
            drug_name=drug_name,
        )

        if web_result.found:
            return SearchChainResult.found(
                value=web_result.value,
                source=web_result.source,
                source_tier=3,
                confidence=web_result.confidence,
                date=web_result.date,
                evidence=web_result.evidence,
                searched_sources=searched + web_result.searched_sources,
            )

        return SearchChainResult.not_found(searched + web_result.searched_sources)

    def search_all_designations(
        self,
        ticker: str,
        drug_name: str,
        start_date: str = None,
    ) -> dict[str, SearchChainResult]:
        """
        모든 FDA 지정 한번에 검색.

        Returns:
            {"btd": SearchChainResult, "orphan": SearchChainResult, ...}
        """
        results = {}

        results["btd"] = self.search_btd(ticker, drug_name, start_date)
        results["orphan"] = self.search_orphan_drug(ticker, drug_name, start_date)
        results["priority_review"] = self.search_priority_review(ticker, drug_name, start_date)

        return results


def create_search_chain(
    use_sec: bool = True,
    use_web: bool = True,
) -> SearchChainOrchestrator:
    """
    검색 체인 오케스트레이터 생성 헬퍼.

    Args:
        use_sec: SEC 클라이언트 사용 여부
        use_web: 웹 검색 사용 여부

    Returns:
        SearchChainOrchestrator 인스턴스
    """
    designation_client = None
    sec_client = None
    web_client = None

    if use_sec:
        from .api_clients import DesignationSearchClient, SECEdgarClient
        designation_client = DesignationSearchClient()
        sec_client = SECEdgarClient()

    if use_web:
        web_client = WebSearchClient()

    return SearchChainOrchestrator(
        designation_client=designation_client,
        sec_client=sec_client,
        web_client=web_client,
    )
