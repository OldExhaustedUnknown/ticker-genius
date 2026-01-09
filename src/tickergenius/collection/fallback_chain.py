"""
Fallback Chain Manager
=======================
필드별 폴백 체인을 관리하는 매니저.

각 데이터 필드에 대해 여러 소스를 순차적으로 시도하고,
실패 시 다음 소스로 폴백합니다.

추론 금지 원칙:
- 모든 소스에서 데이터를 찾지 못하면 NOT_FOUND로 반환
- 절대로 추론하지 않음

참조: docs/SEARCH_IMPROVEMENT_DESIGN.md
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Callable, Awaitable, TYPE_CHECKING

from .models import SearchStatus
from .search_chain import SearchChainResult

if TYPE_CHECKING:
    from .api_clients import (
        AACTClient,
        ClinicalTrialsClient,
        PubMedClient,
        SECEdgarClient,
        FDAAdvisoryCommitteeClient,
        FDAWarningLettersClient,
        DesignationSearchClient,
    )
    from .web_search import WebSearchClient

logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    """데이터 소스 종류."""
    # Clinical Trial Sources
    AACT_DB = "aact_db"
    CLINICALTRIALS_CLASSIC = "clinicaltrials_classic"
    PUBMED = "pubmed"

    # Regulatory Sources
    SEC_8K = "sec_8k"
    FDA_CALENDAR = "fda_calendar"
    FDA_WARNING_LETTERS = "fda_warning_letters"
    OPENFDA = "openfda"

    # Web Search Sources
    WEB_SEARCH = "web_search"
    WEB_SEARCH_NEWS = "web_search_news"
    WEB_SEARCH_FDA = "web_search_fda"


@dataclass
class SourceConfig:
    """소스별 설정."""
    source: DataSource
    timeout: float = 30.0  # 초
    max_retries: int = 2
    domains: list[str] = field(default_factory=list)  # 웹 검색 시 도메인 제한
    priority: int = 1  # 낮을수록 우선순위 높음

    def __post_init__(self):
        if not self.domains:
            self.domains = []


@dataclass
class FallbackChainConfig:
    """폴백 체인 설정."""
    field_name: str
    sources: list[SourceConfig]
    description: str = ""

    @property
    def source_names(self) -> list[str]:
        """소스 이름 리스트."""
        return [s.source.value for s in self.sources]


@dataclass
class ChainExecutionResult:
    """체인 실행 결과."""
    status: SearchStatus
    value: Any = None
    source: Optional[str] = None
    source_tier: int = 4
    confidence: float = 0.0
    date: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

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
        execution_time_ms: float = 0.0,
    ) -> "ChainExecutionResult":
        return cls(
            status=SearchStatus.FOUND,
            value=value,
            source=source,
            source_tier=source_tier,
            confidence=confidence,
            date=date,
            evidence=evidence or [],
            searched_sources=searched_sources or [],
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def not_found(
        cls,
        searched_sources: list[str],
        errors: list[str] = None,
        execution_time_ms: float = 0.0,
    ) -> "ChainExecutionResult":
        return cls(
            status=SearchStatus.NOT_FOUND,
            searched_sources=searched_sources,
            errors=errors or [],
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def confirmed_none(
        cls,
        source: str,
        searched_sources: list[str],
        execution_time_ms: float = 0.0,
    ) -> "ChainExecutionResult":
        """공식 소스에서 없음 확인."""
        return cls(
            status=SearchStatus.CONFIRMED_NONE,
            source=source,
            source_tier=1,
            confidence=1.0,
            searched_sources=searched_sources,
            execution_time_ms=execution_time_ms,
        )

    def to_search_chain_result(self) -> SearchChainResult:
        """SearchChainResult로 변환."""
        return SearchChainResult(
            status=self.status,
            value=self.value,
            source=self.source,
            source_tier=self.source_tier,
            confidence=self.confidence,
            date=self.date,
            evidence=self.evidence,
            searched_sources=self.searched_sources,
        )


# =============================================================================
# 필드별 폴백 체인 정의
# =============================================================================

FALLBACK_CHAINS: dict[str, FallbackChainConfig] = {
    # Phase (임상시험 Phase)
    "phase": FallbackChainConfig(
        field_name="phase",
        description="임상시험 Phase (1, 2, 3, 4)",
        sources=[
            SourceConfig(
                source=DataSource.AACT_DB,
                timeout=45.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.CLINICALTRIALS_CLASSIC,
                timeout=30.0,
                max_retries=2,
                priority=2,
            ),
            SourceConfig(
                source=DataSource.PUBMED,
                timeout=30.0,
                max_retries=2,
                priority=3,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH,
                timeout=20.0,
                max_retries=1,
                domains=["clinicaltrials.gov", "biospace.com", "fiercepharma.com"],
                priority=4,
            ),
        ],
    ),

    # Primary Endpoint Met
    "primary_endpoint_met": FallbackChainConfig(
        field_name="primary_endpoint_met",
        description="Primary endpoint 달성 여부",
        sources=[
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_NEWS,
                timeout=20.0,
                max_retries=1,
                domains=["biospace.com", "fiercepharma.com", "reuters.com", "businesswire.com"],
                priority=2,
            ),
            SourceConfig(
                source=DataSource.PUBMED,
                timeout=30.0,
                max_retries=2,
                priority=3,
            ),
        ],
    ),

    # AdCom (Advisory Committee)
    "adcom": FallbackChainConfig(
        field_name="adcom",
        description="Advisory Committee 개최 여부 및 결과",
        sources=[
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.FDA_CALENDAR,
                timeout=30.0,
                max_retries=2,
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH,
                timeout=20.0,
                max_retries=1,
                domains=["fda.gov", "biospace.com", "fiercepharma.com"],
                priority=3,
            ),
        ],
    ),

    # PAI Passed (Pre-Approval Inspection)
    "pai_passed": FallbackChainConfig(
        field_name="pai_passed",
        description="Pre-Approval Inspection 통과 여부",
        sources=[
            SourceConfig(
                source=DataSource.FDA_WARNING_LETTERS,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH,
                timeout=20.0,
                max_retries=1,
                domains=["fda.gov", "biospace.com"],
                priority=3,
            ),
        ],
    ),

    # BTD (Breakthrough Therapy Designation)
    "btd": FallbackChainConfig(
        field_name="btd",
        description="Breakthrough Therapy Designation",
        sources=[
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_FDA,
                timeout=20.0,
                max_retries=1,
                domains=["fda.gov"],
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_NEWS,
                timeout=20.0,
                max_retries=1,
                domains=["biospace.com", "fiercepharma.com", "businesswire.com"],
                priority=3,
            ),
        ],
    ),

    # Orphan Drug Designation
    "orphan_drug": FallbackChainConfig(
        field_name="orphan_drug",
        description="Orphan Drug Designation",
        sources=[
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_FDA,
                timeout=20.0,
                max_retries=1,
                domains=["fda.gov"],
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_NEWS,
                timeout=20.0,
                max_retries=1,
                domains=["biospace.com", "fiercepharma.com"],
                priority=3,
            ),
        ],
    ),

    # Priority Review
    "priority_review": FallbackChainConfig(
        field_name="priority_review",
        description="Priority Review Designation",
        sources=[
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_FDA,
                timeout=20.0,
                max_retries=1,
                domains=["fda.gov"],
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_NEWS,
                timeout=20.0,
                max_retries=1,
                domains=["biospace.com", "fiercepharma.com"],
                priority=3,
            ),
        ],
    ),

    # CRL (Complete Response Letter)
    "crl": FallbackChainConfig(
        field_name="crl",
        description="Complete Response Letter 발급 여부",
        sources=[
            SourceConfig(
                source=DataSource.SEC_8K,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_NEWS,
                timeout=20.0,
                max_retries=1,
                domains=["biospace.com", "fiercepharma.com", "reuters.com"],
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH,
                timeout=20.0,
                max_retries=1,
                priority=3,
            ),
        ],
    ),

    # Warning Letter
    "warning_letter": FallbackChainConfig(
        field_name="warning_letter",
        description="FDA Warning Letter 발급 여부",
        sources=[
            SourceConfig(
                source=DataSource.FDA_WARNING_LETTERS,
                timeout=30.0,
                max_retries=2,
                priority=1,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH_FDA,
                timeout=20.0,
                max_retries=1,
                domains=["fda.gov"],
                priority=2,
            ),
            SourceConfig(
                source=DataSource.WEB_SEARCH,
                timeout=20.0,
                max_retries=1,
                priority=3,
            ),
        ],
    ),
}


class FallbackChainManager:
    """
    폴백 체인 관리자.

    각 필드에 대해 정의된 소스 체인을 순차적으로 실행하고,
    첫 번째로 성공한 소스의 결과를 반환합니다.

    Usage:
        manager = FallbackChainManager()
        result = await manager.execute_chain(
            field_name="phase",
            ticker="AXSM",
            drug_name="AXS-05",
        )
        if result.status == SearchStatus.FOUND:
            print(f"Phase: {result.value} from {result.source}")
    """

    def __init__(
        self,
        aact_client: "AACTClient" = None,
        clinicaltrials_client: "ClinicalTrialsClient" = None,
        pubmed_client: "PubMedClient" = None,
        sec_client: "SECEdgarClient" = None,
        fda_calendar_client: "FDAAdvisoryCommitteeClient" = None,
        warning_letters_client: "FDAWarningLettersClient" = None,
        designation_client: "DesignationSearchClient" = None,
        web_client: "WebSearchClient" = None,
    ):
        """
        Args:
            aact_client: AACT Database 클라이언트
            clinicaltrials_client: ClinicalTrials.gov 클라이언트
            pubmed_client: PubMed 클라이언트
            sec_client: SEC EDGAR 클라이언트
            fda_calendar_client: FDA Advisory Committee 클라이언트
            warning_letters_client: FDA Warning Letters 클라이언트
            designation_client: Designation Search 클라이언트
            web_client: Web Search 클라이언트
        """
        self.aact_client = aact_client
        self.clinicaltrials_client = clinicaltrials_client
        self.pubmed_client = pubmed_client
        self.sec_client = sec_client
        self.fda_calendar_client = fda_calendar_client
        self.warning_letters_client = warning_letters_client
        self.designation_client = designation_client
        self.web_client = web_client

        # 체인 설정
        self.chains = FALLBACK_CHAINS.copy()

    def get_chain_config(self, field_name: str) -> Optional[FallbackChainConfig]:
        """필드별 체인 설정 가져오기."""
        return self.chains.get(field_name)

    def add_chain(self, config: FallbackChainConfig) -> None:
        """새 체인 추가."""
        self.chains[config.field_name] = config

    async def execute_chain(
        self,
        field_name: str,
        ticker: str,
        drug_name: str,
        start_date: str = None,
        before_date: str = None,
        **kwargs,
    ) -> ChainExecutionResult:
        """
        폴백 체인 실행.

        첫 번째 소스부터 순차적으로 시도하고,
        실패 시 다음 소스로 폴백합니다.

        Args:
            field_name: 필드명 (phase, primary_endpoint_met, adcom, pai_passed 등)
            ticker: 티커 심볼
            drug_name: 약물명
            start_date: 검색 시작 날짜 (YYYY-MM-DD)
            before_date: 이 날짜 이전만 검색 (YYYYMMDD)
            **kwargs: 추가 검색 파라미터

        Returns:
            ChainExecutionResult
        """
        config = self.get_chain_config(field_name)
        if not config:
            logger.error(f"Unknown field name: {field_name}")
            return ChainExecutionResult.not_found(
                searched_sources=[],
                errors=[f"Unknown field: {field_name}"],
            )

        start_time = datetime.now()
        searched_sources = []
        errors = []

        logger.info(
            f"Starting fallback chain for {field_name}: "
            f"{' -> '.join(config.source_names)}"
        )

        # 각 소스 순차 실행
        for source_config in sorted(config.sources, key=lambda x: x.priority):
            source_name = source_config.source.value
            searched_sources.append(source_name)

            logger.debug(
                f"[{field_name}] Trying source: {source_name} "
                f"(timeout={source_config.timeout}s, retries={source_config.max_retries})"
            )

            try:
                result = await self._execute_source(
                    source_config=source_config,
                    field_name=field_name,
                    ticker=ticker,
                    drug_name=drug_name,
                    start_date=start_date,
                    before_date=before_date,
                    **kwargs,
                )

                if result and result.status == SearchStatus.FOUND:
                    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                    logger.info(
                        f"[{field_name}] Found in {source_name}: "
                        f"value={result.value}, confidence={result.confidence:.2f}"
                    )
                    return ChainExecutionResult.found(
                        value=result.value,
                        source=source_name,
                        source_tier=result.source_tier,
                        confidence=result.confidence,
                        date=result.date,
                        evidence=result.evidence,
                        searched_sources=searched_sources,
                        execution_time_ms=elapsed_ms,
                    )

                if result and result.status == SearchStatus.CONFIRMED_NONE:
                    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                    logger.info(f"[{field_name}] Confirmed none in {source_name}")
                    return ChainExecutionResult.confirmed_none(
                        source=source_name,
                        searched_sources=searched_sources,
                        execution_time_ms=elapsed_ms,
                    )

                logger.debug(f"[{field_name}] Not found in {source_name}, trying next")

            except asyncio.TimeoutError:
                error_msg = f"{source_name} timed out after {source_config.timeout}s"
                logger.warning(f"[{field_name}] {error_msg}")
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"{source_name} failed: {type(e).__name__}: {str(e)}"
                logger.warning(f"[{field_name}] {error_msg}")
                errors.append(error_msg)

        # 모든 소스 실패
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"[{field_name}] NOT_FOUND after trying all sources: "
            f"{', '.join(searched_sources)}"
        )

        return ChainExecutionResult.not_found(
            searched_sources=searched_sources,
            errors=errors,
            execution_time_ms=elapsed_ms,
        )

    async def _execute_source(
        self,
        source_config: SourceConfig,
        field_name: str,
        ticker: str,
        drug_name: str,
        start_date: str = None,
        before_date: str = None,
        **kwargs,
    ) -> Optional[ChainExecutionResult]:
        """
        단일 소스 실행.

        Args:
            source_config: 소스 설정
            field_name: 필드명
            ticker: 티커
            drug_name: 약물명
            start_date: 시작 날짜
            before_date: 이전 날짜
            **kwargs: 추가 파라미터

        Returns:
            ChainExecutionResult 또는 None
        """
        source = source_config.source

        # 타임아웃 적용
        try:
            result = await asyncio.wait_for(
                self._dispatch_source(
                    source=source,
                    field_name=field_name,
                    ticker=ticker,
                    drug_name=drug_name,
                    start_date=start_date,
                    before_date=before_date,
                    domains=source_config.domains,
                    **kwargs,
                ),
                timeout=source_config.timeout,
            )
            return result
        except asyncio.TimeoutError:
            raise

    async def _dispatch_source(
        self,
        source: DataSource,
        field_name: str,
        ticker: str,
        drug_name: str,
        start_date: str = None,
        before_date: str = None,
        domains: list[str] = None,
        **kwargs,
    ) -> Optional[ChainExecutionResult]:
        """
        소스별 실제 검색 로직 디스패치.

        Args:
            source: 데이터 소스
            field_name: 필드명
            ticker: 티커
            drug_name: 약물명
            start_date: 시작 날짜
            before_date: 이전 날짜
            domains: 도메인 제한 (웹 검색 시)
            **kwargs: 추가 파라미터

        Returns:
            ChainExecutionResult 또는 None
        """
        # AACT Database
        if source == DataSource.AACT_DB:
            return await self._search_aact(field_name, drug_name)

        # ClinicalTrials.gov Classic API
        elif source == DataSource.CLINICALTRIALS_CLASSIC:
            return await self._search_clinicaltrials(field_name, drug_name)

        # PubMed
        elif source == DataSource.PUBMED:
            return await self._search_pubmed(field_name, drug_name)

        # SEC 8-K
        elif source == DataSource.SEC_8K:
            return await self._search_sec_8k(
                field_name, ticker, drug_name, start_date, before_date
            )

        # FDA Calendar (AdCom)
        elif source == DataSource.FDA_CALENDAR:
            return await self._search_fda_calendar(field_name, drug_name)

        # FDA Warning Letters
        elif source == DataSource.FDA_WARNING_LETTERS:
            return await self._search_warning_letters(field_name, ticker, drug_name)

        # Web Search variants
        elif source in (
            DataSource.WEB_SEARCH,
            DataSource.WEB_SEARCH_NEWS,
            DataSource.WEB_SEARCH_FDA,
        ):
            return await self._search_web(
                field_name, ticker, drug_name, domains, before_date
            )

        else:
            logger.warning(f"Unknown source: {source}")
            return None

    # =========================================================================
    # 소스별 검색 구현
    # =========================================================================

    async def _search_aact(
        self,
        field_name: str,
        drug_name: str,
    ) -> Optional[ChainExecutionResult]:
        """AACT Database 검색."""
        if not self.aact_client:
            return None

        # 동기 클라이언트를 비동기로 래핑
        loop = asyncio.get_event_loop()

        if field_name == "phase":
            phase = await loop.run_in_executor(
                None,
                self.aact_client.find_phase_for_drug,
                drug_name,
            )
            if phase:
                return ChainExecutionResult.found(
                    value=phase,
                    source=DataSource.AACT_DB.value,
                    source_tier=1,
                    confidence=0.95,
                    evidence=[f"Phase {phase} found in AACT database"],
                )

        return None

    async def _search_clinicaltrials(
        self,
        field_name: str,
        drug_name: str,
    ) -> Optional[ChainExecutionResult]:
        """ClinicalTrials.gov 검색."""
        if not self.clinicaltrials_client:
            return None

        loop = asyncio.get_event_loop()

        if field_name == "phase":
            studies = await loop.run_in_executor(
                None,
                self.clinicaltrials_client.search_by_drug_sponsor,
                drug_name,
                None,
            )

            if studies:
                # 가장 높은 Phase 찾기
                for study in studies:
                    protocol = study.get("protocolSection", {})
                    design = protocol.get("designModule", {})
                    phases = design.get("phases", [])

                    for phase_str in phases:
                        phase_upper = phase_str.upper()
                        if "PHASE 3" in phase_upper or "PHASE3" in phase_upper:
                            return ChainExecutionResult.found(
                                value="3",
                                source=DataSource.CLINICALTRIALS_CLASSIC.value,
                                source_tier=2,
                                confidence=0.90,
                            )
                        elif "PHASE 2" in phase_upper or "PHASE2" in phase_upper:
                            return ChainExecutionResult.found(
                                value="2",
                                source=DataSource.CLINICALTRIALS_CLASSIC.value,
                                source_tier=2,
                                confidence=0.90,
                            )

        return None

    async def _search_pubmed(
        self,
        field_name: str,
        drug_name: str,
    ) -> Optional[ChainExecutionResult]:
        """PubMed 검색."""
        if not self.pubmed_client:
            return None

        loop = asyncio.get_event_loop()

        if field_name == "phase":
            # NCT ID 찾기
            nct_ids = await loop.run_in_executor(
                None,
                self.pubmed_client.find_nct_ids_for_drug,
                drug_name,
                None,
            )

            if nct_ids and self.clinicaltrials_client:
                # NCT ID로 study 조회
                for nct_id in nct_ids[:3]:
                    study = await loop.run_in_executor(
                        None,
                        self.clinicaltrials_client.search_by_nct_id,
                        nct_id,
                    )
                    if study:
                        protocol = study.get("protocolSection", {})
                        design = protocol.get("designModule", {})
                        phases = design.get("phases", [])

                        for phase_str in phases:
                            if "3" in phase_str:
                                return ChainExecutionResult.found(
                                    value="3",
                                    source=DataSource.PUBMED.value,
                                    source_tier=2,
                                    confidence=0.85,
                                    evidence=[f"Found via PubMed -> NCT: {nct_id}"],
                                )

        return None

    async def _search_sec_8k(
        self,
        field_name: str,
        ticker: str,
        drug_name: str,
        start_date: str = None,
        before_date: str = None,
    ) -> Optional[ChainExecutionResult]:
        """SEC 8-K 검색."""
        if not self.sec_client and not self.designation_client:
            return None

        loop = asyncio.get_event_loop()

        # BTD, Orphan, Priority Review
        if field_name in ("btd", "orphan_drug", "priority_review") and self.designation_client:
            if field_name == "btd":
                result = await loop.run_in_executor(
                    None,
                    self.designation_client.search_btd_designation,
                    ticker,
                    drug_name,
                    start_date,
                )
                if result.get("has_btd") is not None:
                    return ChainExecutionResult.found(
                        value=result["has_btd"],
                        source=DataSource.SEC_8K.value,
                        source_tier=1,
                        confidence=result.get("confidence", 0.85),
                        date=result.get("designation_date"),
                        evidence=result.get("evidence", []),
                    )

            elif field_name == "orphan_drug":
                result = await loop.run_in_executor(
                    None,
                    self.designation_client.search_orphan_designation,
                    ticker,
                    drug_name,
                    start_date,
                )
                if result.get("has_orphan") is not None:
                    return ChainExecutionResult.found(
                        value=result["has_orphan"],
                        source=DataSource.SEC_8K.value,
                        source_tier=1,
                        confidence=result.get("confidence", 0.85),
                        date=result.get("designation_date"),
                        evidence=result.get("evidence", []),
                    )

            elif field_name == "priority_review":
                result = await loop.run_in_executor(
                    None,
                    self.designation_client.search_priority_review,
                    ticker,
                    drug_name,
                    start_date,
                )
                if result.get("has_priority_review") is not None:
                    return ChainExecutionResult.found(
                        value=result["has_priority_review"],
                        source=DataSource.SEC_8K.value,
                        source_tier=1,
                        confidence=result.get("confidence", 0.85),
                        date=result.get("designation_date"),
                        evidence=result.get("evidence", []),
                    )

        # CRL, AdCom, Primary Endpoint
        if self.sec_client:
            if field_name == "crl":
                filings = await loop.run_in_executor(
                    None,
                    lambda: self.sec_client.search_8k_filings(
                        ticker=ticker,
                        keywords=["complete response letter", "CRL", "FDA rejection"],
                        start_date=start_date or "2010-01-01",
                    ),
                )

                for filing in filings:
                    info = self.sec_client.extract_pdufa_info(filing)
                    if info.get("has_crl"):
                        filing_date = filing.get("filingDate", "").replace("-", "")
                        if before_date and filing_date >= before_date.replace("-", ""):
                            continue
                        return ChainExecutionResult.found(
                            value="crl",
                            source=DataSource.SEC_8K.value,
                            source_tier=1,
                            confidence=0.85,
                            date=filing_date,
                            evidence=info.get("detected_keywords", []),
                        )

            elif field_name == "adcom":
                filings = await loop.run_in_executor(
                    None,
                    lambda: self.sec_client.search_8k_filings(
                        ticker=ticker,
                        keywords=["advisory committee", "AdCom", "FDA panel"],
                        start_date=start_date or "2010-01-01",
                    ),
                )

                for filing in filings:
                    info = self.sec_client.extract_pdufa_info(filing)
                    if info.get("has_adcom"):
                        return ChainExecutionResult.found(
                            value={"held": True},
                            source=DataSource.SEC_8K.value,
                            source_tier=1,
                            confidence=0.80,
                            date=filing.get("filingDate", "").replace("-", ""),
                            evidence=info.get("detected_keywords", []),
                        )

            elif field_name == "primary_endpoint_met":
                filings = await loop.run_in_executor(
                    None,
                    lambda: self.sec_client.search_8k_filings(
                        ticker=ticker,
                        keywords=[
                            "primary endpoint",
                            "met primary",
                            "statistically significant",
                            "positive results",
                        ],
                        start_date=start_date or "2015-01-01",
                    ),
                )

                # 8-K에서 직접 primary endpoint 결과 추출은 어려움
                # 키워드 감지만 수행
                if filings:
                    # 더 자세한 분석 필요 - 현재는 감지만
                    pass

        return None

    async def _search_fda_calendar(
        self,
        field_name: str,
        drug_name: str,
    ) -> Optional[ChainExecutionResult]:
        """FDA Calendar 검색 (AdCom)."""
        if not self.fda_calendar_client:
            return None

        loop = asyncio.get_event_loop()

        if field_name == "adcom":
            results = await loop.run_in_executor(
                None,
                self.fda_calendar_client.search_adcom_by_drug,
                drug_name,
            )

            if results:
                for r in results:
                    adcom_info = self.fda_calendar_client.extract_adcom_info(r)
                    if adcom_info.get("has_adcom"):
                        return ChainExecutionResult.found(
                            value={
                                "held": True,
                                "advisory_committee": adcom_info.get("advisory_committee"),
                            },
                            source=DataSource.FDA_CALENDAR.value,
                            source_tier=1,
                            confidence=0.90,
                            date=adcom_info.get("meeting_date"),
                        )

        return None

    async def _search_warning_letters(
        self,
        field_name: str,
        ticker: str,
        drug_name: str,
    ) -> Optional[ChainExecutionResult]:
        """FDA Warning Letters 검색."""
        if not self.warning_letters_client:
            return None

        loop = asyncio.get_event_loop()

        if field_name in ("pai_passed", "warning_letter"):
            # 회사명으로 검색 (ticker를 회사명으로 변환 필요)
            has_enforcement = await loop.run_in_executor(
                None,
                self.warning_letters_client.has_recent_enforcement,
                ticker,  # 실제로는 회사명이 필요
                3,
            )

            if field_name == "warning_letter":
                return ChainExecutionResult.found(
                    value=has_enforcement,
                    source=DataSource.FDA_WARNING_LETTERS.value,
                    source_tier=1,
                    confidence=0.90 if has_enforcement else 0.70,
                )

            elif field_name == "pai_passed":
                # Warning letter가 없으면 PAI 통과로 간주할 수 없음
                # 단지 warning letter 여부만 확인 가능
                if has_enforcement:
                    return ChainExecutionResult.found(
                        value=False,  # Warning letter 있으면 PAI 실패 가능성
                        source=DataSource.FDA_WARNING_LETTERS.value,
                        source_tier=1,
                        confidence=0.70,
                        evidence=["Recent FDA enforcement action found"],
                    )

        return None

    async def _search_web(
        self,
        field_name: str,
        ticker: str,
        drug_name: str,
        domains: list[str] = None,
        before_date: str = None,
    ) -> Optional[ChainExecutionResult]:
        """웹 검색."""
        if not self.web_client:
            return None

        loop = asyncio.get_event_loop()

        # 필드별 웹 검색
        if field_name == "crl":
            result = await loop.run_in_executor(
                None,
                lambda: self.web_client.search_crl_event(
                    ticker=ticker,
                    drug_name=drug_name,
                    before_date=before_date,
                ),
            )
            if result.found:
                return ChainExecutionResult.found(
                    value=result.value,
                    source=DataSource.WEB_SEARCH.value,
                    source_tier=3,
                    confidence=result.confidence,
                    date=result.date,
                    evidence=result.evidence,
                )

        elif field_name in ("btd", "orphan_drug", "priority_review"):
            designation_map = {
                "btd": "btd",
                "orphan_drug": "orphan",
                "priority_review": "priority",
            }
            result = await loop.run_in_executor(
                None,
                lambda: self.web_client.search_designation(
                    ticker=ticker,
                    drug_name=drug_name,
                    designation_type=designation_map[field_name],
                ),
            )
            if result.found:
                return ChainExecutionResult.found(
                    value=result.value,
                    source=DataSource.WEB_SEARCH.value,
                    source_tier=2 if "fda.gov" in (result.url or "").lower() else 3,
                    confidence=result.confidence,
                    date=result.date,
                    evidence=result.evidence,
                )

        elif field_name == "adcom":
            result = await loop.run_in_executor(
                None,
                lambda: self.web_client.search_adcom(
                    ticker=ticker,
                    drug_name=drug_name,
                ),
            )
            if result.found:
                return ChainExecutionResult.found(
                    value=result.value,
                    source=DataSource.WEB_SEARCH.value,
                    source_tier=2 if "fda.gov" in (result.url or "").lower() else 3,
                    confidence=result.confidence,
                    date=result.date,
                    evidence=result.evidence,
                )

        elif field_name == "primary_endpoint_met":
            result = await loop.run_in_executor(
                None,
                lambda: self.web_client.search_primary_endpoint(
                    ticker=ticker,
                    drug_name=drug_name,
                ),
            )
            if result.found:
                return ChainExecutionResult.found(
                    value=result.value,
                    source=DataSource.WEB_SEARCH.value,
                    source_tier=3,
                    confidence=result.confidence,
                    date=result.date,
                    evidence=result.evidence,
                )

        return None

    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================

    async def execute_multiple_chains(
        self,
        field_names: list[str],
        ticker: str,
        drug_name: str,
        **kwargs,
    ) -> dict[str, ChainExecutionResult]:
        """
        여러 필드 체인을 병렬로 실행.

        Args:
            field_names: 필드명 리스트
            ticker: 티커
            drug_name: 약물명
            **kwargs: 추가 파라미터

        Returns:
            {field_name: ChainExecutionResult}
        """
        tasks = [
            self.execute_chain(
                field_name=field_name,
                ticker=ticker,
                drug_name=drug_name,
                **kwargs,
            )
            for field_name in field_names
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            field_name: (
                result if isinstance(result, ChainExecutionResult)
                else ChainExecutionResult.not_found(
                    searched_sources=[],
                    errors=[str(result)],
                )
            )
            for field_name, result in zip(field_names, results)
        }

    def get_available_chains(self) -> list[str]:
        """사용 가능한 체인 목록."""
        return list(self.chains.keys())

    def describe_chain(self, field_name: str) -> Optional[str]:
        """체인 설명."""
        config = self.get_chain_config(field_name)
        if not config:
            return None

        sources_desc = " -> ".join(
            f"{s.source.value}(timeout={s.timeout}s)"
            for s in sorted(config.sources, key=lambda x: x.priority)
        )
        return f"{config.description}: {sources_desc}"


def create_fallback_chain_manager(
    use_aact: bool = True,
    use_clinicaltrials: bool = True,
    use_pubmed: bool = True,
    use_sec: bool = True,
    use_fda: bool = True,
    use_web: bool = True,
) -> FallbackChainManager:
    """
    FallbackChainManager 생성 헬퍼.

    Args:
        use_aact: AACT DB 사용 여부
        use_clinicaltrials: ClinicalTrials.gov 사용 여부
        use_pubmed: PubMed 사용 여부
        use_sec: SEC EDGAR 사용 여부
        use_fda: FDA API 사용 여부
        use_web: 웹 검색 사용 여부

    Returns:
        FallbackChainManager 인스턴스
    """
    aact_client = None
    clinicaltrials_client = None
    pubmed_client = None
    sec_client = None
    fda_calendar_client = None
    warning_letters_client = None
    designation_client = None
    web_client = None

    if use_aact:
        try:
            from .api_clients import AACTClient
            aact_client = AACTClient()
        except Exception as e:
            logger.warning(f"Failed to initialize AACT client: {e}")

    if use_clinicaltrials:
        try:
            from .api_clients import ClinicalTrialsClient
            clinicaltrials_client = ClinicalTrialsClient()
        except Exception as e:
            logger.warning(f"Failed to initialize ClinicalTrials client: {e}")

    if use_pubmed:
        try:
            from .api_clients import PubMedClient
            pubmed_client = PubMedClient()
        except Exception as e:
            logger.warning(f"Failed to initialize PubMed client: {e}")

    if use_sec:
        try:
            from .api_clients import SECEdgarClient, DesignationSearchClient
            sec_client = SECEdgarClient()
            designation_client = DesignationSearchClient()
        except Exception as e:
            logger.warning(f"Failed to initialize SEC client: {e}")

    if use_fda:
        try:
            from .api_clients import FDAAdvisoryCommitteeClient, FDAWarningLettersClient
            fda_calendar_client = FDAAdvisoryCommitteeClient()
            warning_letters_client = FDAWarningLettersClient()
        except Exception as e:
            logger.warning(f"Failed to initialize FDA clients: {e}")

    if use_web:
        try:
            from .web_search import WebSearchClient
            web_client = WebSearchClient()
        except Exception as e:
            logger.warning(f"Failed to initialize web search client: {e}")

    return FallbackChainManager(
        aact_client=aact_client,
        clinicaltrials_client=clinicaltrials_client,
        pubmed_client=pubmed_client,
        sec_client=sec_client,
        fda_calendar_client=fda_calendar_client,
        warning_letters_client=warning_letters_client,
        designation_client=designation_client,
        web_client=web_client,
    )
