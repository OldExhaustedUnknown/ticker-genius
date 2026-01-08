"""
Ticker-Genius Data Provider Module
==================================
M2 Core: Unified data access with fallback chain.

Fallback Chain:
1. yfinance (free, primary)
2. FMP (Financial Modeling Prep, 250 calls/day)
3. Polygon (if configured)

Features:
- Automatic fallback on failure
- Data quality tracking (StatusField)
- Response normalization
"""

from __future__ import annotations

import logging
from typing import Optional, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from tickergenius.core.config import Config
    from tickergenius.core.http import HTTPClient

logger = logging.getLogger("tickergenius.data_provider")


class DataSource(Enum):
    """Data source identifiers."""
    YFINANCE = "yfinance"
    FMP = "fmp"
    POLYGON = "polygon"
    CACHE = "cache"
    UNKNOWN = "unknown"


class DataQuality(Enum):
    """Data quality status (maps to StatusField)."""
    CONFIRMED = "CONFIRMED"  # Data verified from reliable source
    EMPTY = "EMPTY"          # No data available
    UNKNOWN = "UNKNOWN"      # Data exists but unverified


@dataclass
class TickerData:
    """Normalized ticker data response."""
    ticker: str
    source: DataSource
    quality: DataQuality

    # Price data
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None

    # Company info
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None

    # 52-week range
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None

    # Error info
    error: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if data is valid (has price)."""
        return self.price is not None and self.quality != DataQuality.EMPTY


class DataProvider:
    """
    Unified data provider with fallback chain.

    Usage:
        provider = DataProvider(config, http_client)
        data = provider.get_ticker("MRNA")
        if data.is_valid():
            print(f"{data.ticker}: ${data.price}")
    """

    def __init__(
        self,
        config: "Config",
        http_client: "HTTPClient",
    ):
        """
        Initialize data provider.

        Args:
            config: Config instance (for API keys)
            http_client: HTTPClient instance
        """
        self.config = config
        self.http = http_client
        self._yf_available: Optional[bool] = None

    def _check_yfinance(self) -> bool:
        """Check if yfinance is available."""
        if self._yf_available is None:
            try:
                import yfinance  # noqa: F401
                self._yf_available = True
            except ImportError:
                self._yf_available = False
                logger.warning("yfinance not installed, using API fallbacks")
        return self._yf_available

    def _get_from_yfinance(self, ticker: str) -> Optional[TickerData]:
        """Get data from yfinance."""
        if not self._check_yfinance():
            return None

        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or "regularMarketPrice" not in info:
                return None

            return TickerData(
                ticker=ticker.upper(),
                source=DataSource.YFINANCE,
                quality=DataQuality.CONFIRMED,
                price=info.get("regularMarketPrice") or info.get("currentPrice"),
                change=info.get("regularMarketChange"),
                change_percent=info.get("regularMarketChangePercent"),
                volume=info.get("regularMarketVolume"),
                name=info.get("shortName") or info.get("longName"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=info.get("marketCap"),
                week_52_high=info.get("fiftyTwoWeekHigh"),
                week_52_low=info.get("fiftyTwoWeekLow"),
            )

        except Exception as e:
            logger.debug(f"yfinance failed for {ticker}: {e}")
            return None

    def _get_from_fmp(self, ticker: str) -> Optional[TickerData]:
        """Get data from Financial Modeling Prep API."""
        from tickergenius.core.config import get_api_key

        api_key = get_api_key("FMP_API_KEY")
        if not api_key:
            return None

        try:
            # Quote endpoint
            url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
            status, data = self.http.get_json(url, params={"apikey": api_key})

            if status != 200 or not data or not isinstance(data, list):
                return None

            quote = data[0] if data else {}
            if not quote:
                return None

            return TickerData(
                ticker=ticker.upper(),
                source=DataSource.FMP,
                quality=DataQuality.CONFIRMED,
                price=quote.get("price"),
                change=quote.get("change"),
                change_percent=quote.get("changesPercentage"),
                volume=quote.get("volume"),
                name=quote.get("name"),
                market_cap=quote.get("marketCap"),
                week_52_high=quote.get("yearHigh"),
                week_52_low=quote.get("yearLow"),
            )

        except Exception as e:
            logger.debug(f"FMP failed for {ticker}: {e}")
            return None

    def _get_from_polygon(self, ticker: str) -> Optional[TickerData]:
        """Get data from Polygon.io API."""
        from tickergenius.core.config import get_api_key

        api_key = get_api_key("POLYGON_API_KEY")
        if not api_key:
            return None

        try:
            # Previous close endpoint
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
            status, data = self.http.get_json(url, params={"apiKey": api_key})

            if status != 200 or not data:
                return None

            results = data.get("results", [])
            if not results:
                return None

            bar = results[0]
            return TickerData(
                ticker=ticker.upper(),
                source=DataSource.POLYGON,
                quality=DataQuality.CONFIRMED,
                price=bar.get("c"),  # close
                volume=bar.get("v"),
            )

        except Exception as e:
            logger.debug(f"Polygon failed for {ticker}: {e}")
            return None

    def get_ticker(self, ticker: str) -> TickerData:
        """
        Get ticker data with automatic fallback.

        Tries sources in order: yfinance -> FMP -> Polygon

        Args:
            ticker: Stock ticker symbol

        Returns:
            TickerData with best available data
        """
        ticker = ticker.upper().strip()

        # Try yfinance first
        data = self._get_from_yfinance(ticker)
        if data and data.is_valid():
            logger.debug(f"{ticker}: data from yfinance")
            return data

        # Try FMP
        data = self._get_from_fmp(ticker)
        if data and data.is_valid():
            logger.debug(f"{ticker}: data from FMP")
            return data

        # Try Polygon
        data = self._get_from_polygon(ticker)
        if data and data.is_valid():
            logger.debug(f"{ticker}: data from Polygon")
            return data

        # No data available
        logger.warning(f"{ticker}: no data from any source")
        return TickerData(
            ticker=ticker,
            source=DataSource.UNKNOWN,
            quality=DataQuality.EMPTY,
            error="No data available from any source",
        )

    def get_multiple(self, tickers: list[str]) -> dict[str, TickerData]:
        """
        Get data for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to TickerData
        """
        results = {}
        for ticker in tickers:
            results[ticker.upper()] = self.get_ticker(ticker)
        return results

    def check_health(self) -> dict[str, Any]:
        """
        Check health of data sources.

        Returns:
            Dict with source availability status
        """
        from tickergenius.core.config import is_api_configured

        return {
            "yfinance": self._check_yfinance(),
            "fmp": is_api_configured("FMP_API_KEY"),
            "polygon": is_api_configured("POLYGON_API_KEY"),
        }


def create_data_provider(
    config: "Config", http_client: "HTTPClient"
) -> DataProvider:
    """Factory function to create DataProvider instance."""
    return DataProvider(config, http_client)
