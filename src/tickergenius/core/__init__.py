"""
Ticker-Genius Core Infrastructure
=================================
M2 Core Module - Configuration, Cache, HTTP Client, DataProvider

Exports:
- Config: Immutable configuration container
- load_config: Load configuration from environment
- DiskCache: SQLite-based caching
- HTTPClient: HTTP client with caching
- DataProvider: Unified data access with fallback chain
"""

from tickergenius.core.config import Config, load_config, get_api_key, is_api_configured, ensure_dirs
from tickergenius.core.cache import DiskCache
from tickergenius.core.http import HTTPClient, create_http_client
from tickergenius.core.data_provider import DataProvider, create_data_provider

__all__ = [
    # Config
    "Config",
    "load_config",
    "get_api_key",
    "is_api_configured",
    "ensure_dirs",
    # Cache
    "DiskCache",
    # HTTP
    "HTTPClient",
    "create_http_client",
    # DataProvider
    "DataProvider",
    "create_data_provider",
]
