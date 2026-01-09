"""
API Clients for Data Collection
================================
Clients for OpenFDA, SEC EDGAR, ClinicalTrials.gov

Enhanced with:
- Retry logic with exponential backoff
- Fallback endpoints
- Better error handling
"""

import os
import time
import logging
import random
from typing import Optional, Any, Callable
from datetime import datetime
from functools import wraps
import httpx

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0

    def wait(self):
        """Wait if needed to respect rate limit."""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_errors: tuple = (httpx.TimeoutException, httpx.ConnectError),
    retryable_status_codes: tuple = (429, 500, 502, 503, 504),
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        retryable_errors: Exception types to retry
        retryable_status_codes: HTTP status codes to retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in retryable_status_codes:
                        last_exception = e
                        if attempt < max_retries:
                            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                            logger.warning(
                                f"Retry {attempt + 1}/{max_retries} after {e.response.status_code}, "
                                f"waiting {delay:.1f}s"
                            )
                            time.sleep(delay)
                            continue
                    raise
                except retryable_errors as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} after {type(e).__name__}, "
                            f"waiting {delay:.1f}s"
                        )
                        time.sleep(delay)
                        continue
                    raise

            if last_exception:
                raise last_exception
            return None

        return wrapper
    return decorator


class OpenFDAClient:
    """Client for OpenFDA API."""

    BASE_URL = "https://api.fda.gov/drug"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENFDA_API_KEY", "")
        self.rate_limiter = RateLimiter(200)  # 240/min, use 200 for safety
        self.timeout = 30.0

    def _make_request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make API request with rate limiting and retry."""
        self.rate_limiter.wait()

        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        return self._execute_request(url, params)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _execute_request(self, url: str, params: dict) -> Optional[dict]:
        """Execute HTTP request with retry logic."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # 404 is expected for unknown drugs, don't retry
                logger.debug(f"OpenFDA 404: {url}")
                return None
            raise  # Re-raise for retry
        except Exception as e:
            logger.error(f"OpenFDA request failed: {e}")
            raise

    def search_drug_approvals(self, drug_name: str) -> list[dict]:
        """Search for drug approvals by name."""
        # Extract first word of drug name (brand name)
        brand_name = drug_name.split()[0].upper() if drug_name else ""

        # Search in drugsfda endpoint - try brand name first
        params = {
            "search": f'openfda.brand_name:"{brand_name}"',
            "limit": 10,
        }

        result = self._make_request("drugsfda.json", params)
        if result and "results" in result:
            return result["results"]

        # Fallback: try generic name (last word if different)
        parts = drug_name.split()
        if len(parts) > 1:
            generic = parts[-1].lower()
            params = {
                "search": f'openfda.generic_name:"{generic}"',
                "limit": 10,
            }
            result = self._make_request("drugsfda.json", params)
            if result and "results" in result:
                return result["results"]

        return []

    def search_by_application_number(self, app_num: str) -> Optional[dict]:
        """Search by NDA/BLA application number."""
        params = {
            "search": f'application_number:"{app_num}"',
            "limit": 1,
        }

        result = self._make_request("drugsfda.json", params)
        if result and "results" in result and result["results"]:
            return result["results"][0]
        return None

    def get_drug_label(self, drug_name: str) -> list[dict]:
        """Get drug labeling information."""
        params = {
            "search": f'openfda.brand_name:"{drug_name}"',
            "limit": 5,
        }

        result = self._make_request("label.json", params)
        if result and "results" in result:
            return result["results"]
        return []


class SECEdgarClient:
    """Client for SEC EDGAR API."""

    # SEC Full-Text Search API
    SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
    # Company tickers mapping (ticker -> CIK)
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    # Submissions API
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"

    # PDUFA-related keywords for 8-K search
    PDUFA_KEYWORDS = [
        "PDUFA", "FDA approval", "FDA decision", "complete response letter",
        "CRL", "NDA", "BLA", "sNDA", "sBLA", "advisory committee",
        "AdCom", "priority review", "breakthrough therapy",
        "accelerated approval", "orphan drug", "fast track",
    ]

    def __init__(self, user_agent: str = "TickerGenius/3.0 (contact: ljk2443@gmail.com)"):
        self.user_agent = user_agent
        self.rate_limiter = RateLimiter(10)  # 10 req/sec per SEC guidelines
        self.timeout = 30.0
        self._ticker_cik_map: Optional[dict] = None

    def _make_get_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make GET request with rate limiting and retry."""
        self.rate_limiter.wait()
        return self._execute_get(url, params)

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    def _execute_get(self, url: str, params: dict = None) -> Optional[dict]:
        """Execute GET request with retry logic."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"SEC EDGAR 404: {url}")
                return None
            raise
        except Exception as e:
            logger.error(f"SEC EDGAR GET failed: {e}")
            raise

    def _make_post_request(self, url: str, data: dict) -> Optional[dict]:
        """Make POST request with rate limiting and retry."""
        self.rate_limiter.wait()
        return self._execute_post(url, data)

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    def _execute_post(self, url: str, data: dict) -> Optional[dict]:
        """Execute POST request with retry logic."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            logger.error(f"SEC EDGAR POST failed: {e}")
            raise

    def _load_ticker_cik_map(self) -> dict:
        """Load ticker to CIK mapping from SEC."""
        if self._ticker_cik_map is not None:
            return self._ticker_cik_map

        result = self._make_get_request(self.TICKERS_URL)
        if result:
            # Format: {"0": {"cik_str": "320193", "ticker": "AAPL", ...}}
            self._ticker_cik_map = {}
            for entry in result.values():
                ticker = entry.get("ticker", "").upper()
                cik = str(entry.get("cik_str", ""))
                if ticker and cik:
                    self._ticker_cik_map[ticker] = cik.zfill(10)  # Pad to 10 digits
            logger.info(f"Loaded {len(self._ticker_cik_map)} ticker-CIK mappings")
        else:
            self._ticker_cik_map = {}

        return self._ticker_cik_map

    def get_company_cik(self, ticker: str) -> Optional[str]:
        """Get CIK number for a ticker."""
        ticker_map = self._load_ticker_cik_map()
        return ticker_map.get(ticker.upper())

    def search_8k_filings(
        self,
        ticker: str,
        keywords: list[str] = None,
        start_date: str = "2010-01-01",
        end_date: str = None,
    ) -> list[dict]:
        """
        Search 8-K filings for a ticker with optional keywords.

        Uses EFTS full-text search API with fallback to submissions API.

        Args:
            ticker: Company ticker symbol
            keywords: Search keywords (defaults to PDUFA_KEYWORDS)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD, defaults to today)

        Returns:
            List of matching filing dicts
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if keywords is None:
            keywords = self.PDUFA_KEYWORDS

        # Try full-text search first
        results = self._search_efts(ticker, keywords, start_date, end_date)
        if results:
            return results

        # Fallback: get recent 8-K filings and filter by document name
        logger.debug(f"EFTS search failed for {ticker}, falling back to submissions API")
        return self.get_recent_8k_filings(ticker, limit=100)

    def _search_efts(
        self,
        ticker: str,
        keywords: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """
        Search using SEC EFTS full-text search API.

        Note: EFTS API may return 403 for programmatic access.
        Returns empty list on failure (caller should use fallback).
        """
        # Build search query
        keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
        query = f"({keyword_query})"

        # Use the EDGAR full-text search
        search_data = {
            "q": query,
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "forms": ["8-K", "8-K/A"],
            "entityName": ticker,
        }

        try:
            result = self._make_post_request(self.SEARCH_URL, search_data)
            if result and "hits" in result:
                hits = result["hits"].get("hits", [])
                logger.debug(f"EFTS found {len(hits)} 8-K filings for {ticker}")
                return hits
        except httpx.HTTPStatusError as e:
            # 403 is expected - SEC blocks programmatic EFTS access
            if e.response.status_code == 403:
                logger.debug(f"EFTS API blocked (403) for {ticker}, using fallback")
            else:
                logger.warning(f"EFTS API error {e.response.status_code} for {ticker}")
        except Exception as e:
            logger.warning(f"EFTS search failed for {ticker}: {e}")

        return []

    def get_company_filings(self, ticker: str) -> Optional[dict]:
        """
        Get all filings for a company by ticker.

        Returns submissions data including recent filings.
        """
        cik = self.get_company_cik(ticker)
        if not cik:
            logger.warning(f"Could not find CIK for ticker: {ticker}")
            return None

        url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
        return self._make_get_request(url)

    def get_recent_8k_filings(self, ticker: str, limit: int = 50) -> list[dict]:
        """
        Get recent 8-K filings from company submissions.

        This is faster than full-text search but doesn't filter by content.
        """
        submissions = self.get_company_filings(ticker)
        if not submissions:
            return []

        filings = []
        recent = submissions.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form in ("8-K", "8-K/A") and i < limit:
                filings.append({
                    "form": form,
                    "filingDate": dates[i] if i < len(dates) else None,
                    "accessionNumber": accessions[i] if i < len(accessions) else None,
                    "primaryDocument": descriptions[i] if i < len(descriptions) else None,
                    "ticker": ticker,
                })

        return filings

    def extract_pdufa_info(self, filing: dict) -> dict:
        """
        Extract PDUFA-related information from a filing.

        Returns dict with detected information.
        """
        info = {
            "has_pdufa_mention": False,
            "has_approval": False,
            "has_crl": False,
            "has_adcom": False,
            "has_designation": False,
            "detected_keywords": [],
        }

        # Check source text if available (from full-text search)
        source = filing.get("_source", {})
        text = source.get("file_description", "") + " " + source.get("display_names", [""])[0]

        # Also check primary document name (from submissions API)
        primary_doc = filing.get("primaryDocument", "")
        accession = filing.get("accessionNumber", "")
        text = f"{text} {primary_doc} {accession}".upper()

        # Keyword detection
        keyword_checks = {
            "PDUFA": "has_pdufa_mention",
            "FDA APPROVAL": "has_approval",
            "APPROVED": "has_approval",
            "COMPLETE RESPONSE": "has_crl",
            "CRL": "has_crl",
            "ADVISORY COMMITTEE": "has_adcom",
            "ADCOM": "has_adcom",
            "BREAKTHROUGH": "has_designation",
            "PRIORITY REVIEW": "has_designation",
            "FAST TRACK": "has_designation",
            "ORPHAN DRUG": "has_designation",
        }

        for keyword, flag in keyword_checks.items():
            if keyword in text:
                info[flag] = True
                info["detected_keywords"].append(keyword)

        return info


class ClinicalTrialsClient:
    """
    Client for ClinicalTrials.gov API.

    Supports multiple API versions with automatic fallback:
    - v2 API (primary): https://clinicaltrials.gov/api/v2
    - Classic API (fallback): https://classic.clinicaltrials.gov/api/query
    """

    # API endpoints
    V2_BASE_URL = "https://clinicaltrials.gov/api/v2"
    CLASSIC_BASE_URL = "https://classic.clinicaltrials.gov/api/query"

    def __init__(self):
        self.rate_limiter = RateLimiter(60)  # Be conservative
        self.timeout = 30.0
        self._v2_available = True  # Track if v2 API works

    def _make_v2_request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make API request to v2 API with retry."""
        self.rate_limiter.wait()
        url = f"{self.V2_BASE_URL}/{endpoint}"
        try:
            return self._execute_v2_request(url, params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("ClinicalTrials.gov v2 API returned 403, trying fallback")
                self._v2_available = False
            return None

    @retry_with_backoff(max_retries=2, base_delay=1.0, retryable_status_codes=(429, 500, 502, 503, 504))
    def _execute_v2_request(self, url: str, params: dict) -> Optional[dict]:
        """Execute v2 API request with retry."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "TickerGenius/3.0 (Research; contact: ljk2443@gmail.com)",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    def _make_classic_request(self, params: dict, fmt: str = "json") -> Optional[dict]:
        """Make API request to classic (v1) API with retry."""
        self.rate_limiter.wait()
        url = f"{self.CLASSIC_BASE_URL}/full_studies"
        params["fmt"] = fmt
        try:
            return self._execute_classic_request(url, params)
        except httpx.HTTPStatusError:
            return None

    @retry_with_backoff(max_retries=2, base_delay=1.0, retryable_status_codes=(429, 500, 502, 503, 504))
    def _execute_classic_request(self, url: str, params: dict) -> Optional[dict]:
        """Execute classic API request with retry."""
        headers = {
            "User-Agent": "TickerGenius/3.0 (Research; contact: ljk2443@gmail.com)",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    def search_by_nct_id(self, nct_id: str) -> Optional[dict]:
        """Get study by NCT ID with fallback."""
        # Try v2 first if available
        if self._v2_available:
            result = self._make_v2_request(f"studies/{nct_id}", {})
            if result:
                return result

        # Fallback to classic API
        params = {"expr": nct_id, "max_rnk": 1}
        result = self._make_classic_request(params)
        if result and "FullStudiesResponse" in result:
            studies = result["FullStudiesResponse"].get("FullStudies", [])
            if studies:
                return self._convert_classic_to_v2_format(studies[0])
        return None

    def search_by_drug_sponsor(self, drug_name: str, sponsor: str = None) -> list[dict]:
        """Search studies by drug name and optional sponsor with fallback."""
        # Extract just the brand name (first word)
        brand_name = drug_name.split()[0] if drug_name else ""

        # Try v2 first if available
        if self._v2_available:
            params = {
                "query.term": brand_name,
                "pageSize": 20,
            }
            if sponsor:
                params["query.spons"] = sponsor

            result = self._make_v2_request("studies", params)
            if result and "studies" in result:
                return result["studies"]

        # Fallback to classic API
        expr = brand_name
        if sponsor:
            expr = f"{brand_name} AND AREA[LeadSponsorName]{sponsor}"

        params = {"expr": expr, "max_rnk": 20}
        result = self._make_classic_request(params)
        if result and "FullStudiesResponse" in result:
            studies = result["FullStudiesResponse"].get("FullStudies", [])
            return [self._convert_classic_to_v2_format(s) for s in studies]

        return []

    def get_study_details(self, nct_id: str) -> Optional[dict]:
        """Get detailed study information."""
        return self.search_by_nct_id(nct_id)

    def _convert_classic_to_v2_format(self, classic_study: dict) -> dict:
        """Convert classic API response format to v2-like format."""
        study = classic_study.get("Study", {})
        protocol = study.get("ProtocolSection", {})

        # Build v2-compatible structure
        return {
            "protocolSection": {
                "identificationModule": protocol.get("IdentificationModule", {}),
                "statusModule": protocol.get("StatusModule", {}),
                "designModule": protocol.get("DesignModule", {}),
                "sponsorCollaboratorsModule": protocol.get("SponsorCollaboratorsModule", {}),
            }
        }


class FDAAdvisoryCommitteeClient:
    """
    Client for FDA Advisory Committee data.

    Sources:
    - FDA Calendar: https://www.fda.gov/advisory-committees/advisory-committee-calendar
    - Meeting materials: https://www.fda.gov/advisory-committees/advisory-committee-calendar/[meeting-id]
    """

    # FDA openFDA drugsfda API can provide some advisory committee info
    OPENFDA_URL = "https://api.fda.gov/drug/drugsfda.json"

    def __init__(self):
        self.rate_limiter = RateLimiter(30)
        self.timeout = 30.0

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _execute_request(self, url: str, params: dict) -> Optional[dict]:
        """Execute HTTP request with retry."""
        headers = {"Accept": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    def search_adcom_by_drug(self, drug_name: str) -> list[dict]:
        """
        Search for advisory committee meetings related to a drug.

        Note: FDA doesn't have a dedicated AdCom API, so we use OpenFDA
        and look for advisory committee references in approval documents.
        """
        self.rate_limiter.wait()

        brand_name = drug_name.split()[0].upper() if drug_name else ""

        # Try exact brand name match first
        params = {
            "search": f'openfda.brand_name:"{brand_name}"',
            "limit": 20,
        }

        try:
            result = self._execute_request(self.OPENFDA_URL, params)
            if result and "results" in result:
                # Filter results that have advisory_committee field
                return [r for r in result["results"]
                        if any("advisory_committee" in sub
                               for sub in r.get("submissions", []))]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []  # No results found
            logger.debug(f"AdCom search for {drug_name} failed: {e.response.status_code}")
        except Exception as e:
            logger.debug(f"AdCom search for {drug_name} failed: {e}")

        return []

    def extract_adcom_info(self, fda_result: dict) -> dict:
        """Extract advisory committee info from FDA approval data."""
        info = {
            "advisory_committee": None,
            "has_adcom": False,
            "meeting_date": None,
        }

        # Check advisory_committee field in submissions
        submissions = fda_result.get("submissions", [])
        for sub in submissions:
            if "advisory_committee" in sub:
                info["advisory_committee"] = sub.get("advisory_committee")
                info["has_adcom"] = True
                break

        return info


class PubMedClient:
    """
    Client for PubMed/NCBI E-utilities API.

    Alternative to ClinicalTrials.gov for finding NCT IDs through publications.
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("NCBI_API_KEY", "")
        # Without API key: 3 requests/second, with key: 10 requests/second
        rate = 10 if self.api_key else 3
        self.rate_limiter = RateLimiter(rate * 60)
        self.timeout = 30.0

    def _make_request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make API request with rate limiting."""
        self.rate_limiter.wait()
        if self.api_key:
            params["api_key"] = self.api_key
        params["retmode"] = "json"
        url = f"{self.BASE_URL}/{endpoint}"
        return self._execute_request(url, params)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _execute_request(self, url: str, params: dict) -> Optional[dict]:
        """Execute HTTP request with retry."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def search_clinical_trials(self, drug_name: str, sponsor: str = None) -> list[str]:
        """
        Search PubMed for clinical trial publications mentioning NCT IDs.

        Returns list of PubMed IDs (PMIDs).
        """
        query_parts = [f'"{drug_name}"[Title/Abstract]', "clinical trial[pt]"]
        if sponsor:
            query_parts.append(f'"{sponsor}"[Affiliation]')

        query = " AND ".join(query_parts)
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": 50,
        }

        result = self._make_request("esearch.fcgi", params)
        if result and "esearchresult" in result:
            return result["esearchresult"].get("idlist", [])
        return []

    def get_article_details(self, pmids: list[str]) -> list[dict]:
        """Get article details including NCT IDs from abstracts."""
        if not pmids:
            return []

        params = {
            "db": "pubmed",
            "id": ",".join(pmids[:20]),  # Limit batch size
        }

        result = self._make_request("esummary.fcgi", params)
        if result and "result" in result:
            articles = []
            for pmid in pmids:
                if pmid in result["result"]:
                    articles.append(result["result"][pmid])
            return articles
        return []

    def extract_nct_ids(self, articles: list[dict]) -> list[str]:
        """Extract NCT IDs from article data."""
        import re
        nct_pattern = re.compile(r"NCT\d{8}", re.IGNORECASE)
        nct_ids = set()

        for article in articles:
            # Check all string fields for NCT IDs
            for value in article.values():
                if isinstance(value, str):
                    matches = nct_pattern.findall(value)
                    nct_ids.update(m.upper() for m in matches)

        return list(nct_ids)

    def find_nct_ids_for_drug(self, drug_name: str, sponsor: str = None) -> list[str]:
        """
        Find NCT IDs associated with a drug.

        This is a fallback for when ClinicalTrials.gov is unavailable.
        """
        pmids = self.search_clinical_trials(drug_name, sponsor)
        if not pmids:
            return []

        articles = self.get_article_details(pmids)
        return self.extract_nct_ids(articles)


class FDAWarningLettersClient:
    """
    Client for FDA Warning Letters database.

    For PAI (Pre-Approval Inspection) and manufacturing quality issues.
    """

    BASE_URL = "https://api.fda.gov/drug/enforcement.json"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENFDA_API_KEY", "")
        self.rate_limiter = RateLimiter(200)
        self.timeout = 30.0

    def _make_request(self, params: dict) -> Optional[dict]:
        """Make API request with rate limiting."""
        self.rate_limiter.wait()
        if self.api_key:
            params["api_key"] = self.api_key
        return self._execute_request(self.BASE_URL, params)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _execute_request(self, url: str, params: dict) -> Optional[dict]:
        """Execute HTTP request with retry."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def search_by_company(self, company_name: str) -> list[dict]:
        """Search enforcement actions by company name."""
        params = {
            "search": f'recalling_firm:"{company_name}"',
            "limit": 100,
        }

        try:
            result = self._make_request(params)
            if result and "results" in result:
                return result["results"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []  # No results found
            raise
        except Exception as e:
            logger.warning(f"Warning letters search failed: {e}")

        return []

    def has_recent_enforcement(self, company_name: str, years: int = 3) -> bool:
        """Check if company has recent enforcement actions."""
        from datetime import datetime, timedelta

        results = self.search_by_company(company_name)
        if not results:
            return False

        cutoff = datetime.now() - timedelta(days=years * 365)

        for result in results:
            report_date = result.get("report_date", "")
            if report_date:
                try:
                    date = datetime.strptime(report_date[:8], "%Y%m%d")
                    if date > cutoff:
                        return True
                except ValueError:
                    continue

        return False
