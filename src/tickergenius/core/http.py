"""
Ticker-Genius HTTP Client Module
================================
M2 Core: HTTP client with caching, retries, and safety guards.

Features:
- Thread-local session management
- Automatic retries with backoff
- Response caching integration
- SEC-compliant User-Agent handling
"""

from __future__ import annotations

import json
import hashlib
import logging
import threading
from typing import Optional, Any, TYPE_CHECKING
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if TYPE_CHECKING:
    from tickergenius.core.config import Config
    from tickergenius.core.cache import DiskCache

logger = logging.getLogger("tickergenius.http")

# Thread-local session storage
_thread_local = threading.local()


class HTTPClient:
    """
    HTTP client with caching and safety features.

    Uses dependency injection for Config and DiskCache.
    """

    def __init__(
        self,
        config: "Config",
        cache: "DiskCache",
    ):
        """
        Initialize HTTP client.

        Args:
            config: Config instance
            cache: DiskCache instance
        """
        self.config = config
        self.cache = cache

    def _get_session(self) -> requests.Session:
        """Get or create thread-local session with retry config."""
        if not hasattr(_thread_local, "session"):
            session = requests.Session()
            retries = Retry(
                total=self.config.http_max_retries,
                backoff_factor=self.config.http_backoff_factor,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(
                pool_connections=8,
                pool_maxsize=8,
                max_retries=retries,
            )
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            _thread_local.session = session
        return _thread_local.session

    def _build_cache_key(self, method: str, url: str, headers: dict) -> str:
        """Build cache key from request components."""
        h_key = json.dumps(
            {k.lower(): v for k, v in sorted(headers.items())},
            sort_keys=True,
            ensure_ascii=False,
        )
        raw = f"{method}|{url}|{h_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        ttl: int = 3600,
        is_sec: bool = False,
        use_cache: bool = True,
    ) -> tuple[int, str]:
        """
        HTTP GET request with caching.

        Args:
            url: Target URL
            params: Query parameters
            headers: Additional headers
            ttl: Cache TTL in seconds (default: 1 hour)
            is_sec: Use SEC-compliant User-Agent
            use_cache: Whether to use cache (default: True)

        Returns:
            Tuple of (status_code, response_body)
        """
        # Build headers
        base_ua = (
            self.config.sec_user_agent
            if is_sec
            else f"TickerGenius/{self.config.version}"
        )
        real_headers = {"User-Agent": base_ua}
        if headers:
            real_headers.update(headers)

        session = self._get_session()

        try:
            # Prepare request
            req = requests.Request(
                "GET", url, params=params, headers=real_headers
            )
            prepared = session.prepare_request(req)
            final_url = prepared.url or url

            # Check cache
            cache_key = self._build_cache_key("GET", final_url, real_headers)
            if use_cache:
                cached = self.cache.get_http(cache_key, ttl)
                if cached is not None:
                    return 200, cached

            # Make request
            resp = session.send(
                prepared,
                timeout=self.config.http_timeout,
                allow_redirects=False,
            )

            # Handle redirects
            if 300 <= resp.status_code < 400:
                location = resp.headers.get("Location", "")
                return resp.status_code, f"Redirect: {location}"

            # Size guard
            if resp.status_code == 200 and len(resp.text) > self.config.max_request_size:
                logger.warning(f"Response too large: {len(resp.text)} bytes")
                return resp.status_code, "[Response Too Large]"

            # Cache successful JSON responses
            if resp.status_code == 200 and resp.text and use_cache:
                text = resp.text.strip()
                if text.startswith("{") or text.startswith("["):
                    try:
                        json.loads(text)  # Validate JSON
                        self.cache.set_http(cache_key, text)
                    except json.JSONDecodeError:
                        pass

            return resp.status_code, resp.text or ""

        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout: {url}")
            return 0, "Timeout"
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error: {url} - {e}")
            return 0, f"Connection error: {e}"
        except Exception as e:
            logger.warning(f"HTTP error: {url} - {e}")
            return 0, str(e)

    def get_json(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        ttl: int = 3600,
        is_sec: bool = False,
    ) -> tuple[int, Optional[dict | list]]:
        """
        HTTP GET with JSON parsing.

        Returns:
            Tuple of (status_code, parsed_json_or_None)
        """
        status, body = self.get(url, params, headers, ttl, is_sec)
        if status != 200 or not body:
            return status, None

        try:
            return status, json.loads(body)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON response from {url}")
            return status, None

    def post_json(
        self,
        url: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> tuple[int, Optional[dict | list]]:
        """
        HTTP POST with JSON body.

        Args:
            url: Target URL
            data: JSON body
            headers: Additional headers
            timeout: Request timeout (default: config.http_timeout)

        Returns:
            Tuple of (status_code, parsed_json_or_None)
        """
        real_headers = {
            "User-Agent": f"TickerGenius/{self.config.version}",
            "Content-Type": "application/json",
        }
        if headers:
            real_headers.update(headers)

        session = self._get_session()

        try:
            resp = session.post(
                url,
                json=data,
                headers=real_headers,
                timeout=timeout or self.config.http_timeout,
            )

            if resp.status_code == 200 and resp.text:
                try:
                    return resp.status_code, resp.json()
                except json.JSONDecodeError:
                    return resp.status_code, None

            return resp.status_code, None

        except Exception as e:
            logger.warning(f"POST error: {url} - {e}")
            return 0, None


def create_http_client(config: "Config", cache: "DiskCache") -> HTTPClient:
    """Factory function to create HTTPClient instance."""
    return HTTPClient(config, cache)
