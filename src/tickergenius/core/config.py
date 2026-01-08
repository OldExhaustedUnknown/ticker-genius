"""
Ticker-Genius Configuration Module
==================================
M2 Core: Environment-first configuration management.

Security Policy:
- API keys are loaded ONLY from environment variables
- No config file fallback for sensitive data in production
- Development mode allows .env file loading via python-dotenv

Usage:
    from tickergenius.core import load_config, get_api_key

    config = load_config()
    fmp_key = get_api_key("FMP_API_KEY")
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

from tickergenius.__version__ import __version__, __cache_version__

logger = logging.getLogger("tickergenius.config")


# =============================================================================
# API Key Management (Environment Variables Only)
# =============================================================================

# Supported API keys with their environment variable names
API_KEY_NAMES = [
    "FMP_API_KEY",           # Financial Modeling Prep
    "POLYGON_API_KEY",       # Polygon.io / Massive
    "ALPHAVANTAGE_API_KEY",  # Alpha Vantage
    "FINNHUB_API_KEY",       # Finnhub
    "OPENFDA_API_KEY",       # OpenFDA (optional)
    "TELEGRAM_BOT_TOKEN",    # Telegram notifications
    "TELEGRAM_CHAT_ID",      # Telegram chat ID
    "ALPACA_API_KEY",        # Alpaca trading (Phase 9+)
    "ALPACA_API_SECRET",     # Alpaca secret (Phase 9+)
]

# Global API keys cache (loaded once)
_API_KEYS: dict[str, str] = {}


def _load_api_keys() -> dict[str, str]:
    """Load all API keys from environment variables."""
    keys = {}
    for key_name in API_KEY_NAMES:
        value = os.environ.get(key_name, "").strip()
        if value:
            keys[key_name] = value
    return keys


def get_api_key(key_name: str) -> str:
    """
    Get an API key by name.

    Args:
        key_name: Environment variable name (e.g., 'FMP_API_KEY')

    Returns:
        The API key value or empty string if not found.
    """
    return _API_KEYS.get(key_name, "")


def is_api_configured(key_name: str) -> bool:
    """Check if an API key is configured."""
    return bool(get_api_key(key_name))


# =============================================================================
# Configuration Dataclass
# =============================================================================

@dataclass(frozen=True)
class Config:
    """
    Immutable configuration container for Ticker-Genius.

    All paths are resolved to absolute paths during loading.
    """
    # Version info (from __version__.py)
    version: str = __version__
    cache_version: str = __cache_version__

    # HTTP settings
    http_timeout: int = 15
    http_max_retries: int = 3
    http_backoff_factor: float = 0.6

    # Cache settings
    cache_db: str = "./tickergenius_cache.sqlite3"
    cache_default_ttl: int = 3600  # 1 hour
    cache_cleanup_days: int = 7

    # Workspace
    workspace_root: str = ""
    data_dir: str = "./data"
    logs_dir: str = "./logs"

    # User-Agent for SEC requests
    sec_user_agent: str = ""

    # Safety limits
    max_request_size: int = 2_000_000  # 2MB
    max_workers: int = 4

    # Feature flags (from Phase 3)
    feature_organic_analysis: bool = True
    feature_cross_validation: bool = True

    # Environment
    env: str = "development"  # development | production

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env.lower() == "production"


# =============================================================================
# Configuration Loading
# =============================================================================

def load_config(
    base_dir: Optional[str] = None,
    load_dotenv: bool = True,
) -> Config:
    """
    Load configuration from environment variables.

    Args:
        base_dir: Base directory for relative paths.
                  Defaults to current working directory.
        load_dotenv: Whether to load .env file (development only)

    Returns:
        Configured Config instance
    """
    # Load .env file in development
    if load_dotenv:
        try:
            from dotenv import load_dotenv as _load_dotenv
            _load_dotenv()
            logger.debug(".env file loaded")
        except ImportError:
            pass  # python-dotenv not installed, skip

    # Set base directory
    if base_dir is None:
        base_dir = os.getcwd()
    base_dir = os.path.abspath(base_dir)

    # Load API keys
    global _API_KEYS
    _API_KEYS = _load_api_keys()

    # Log loaded keys (without values)
    loaded_keys = [k for k, v in _API_KEYS.items() if v]
    if loaded_keys:
        logger.info(f"API keys loaded: {', '.join(loaded_keys)}")
    else:
        logger.warning("No API keys found in environment variables")

    # Build config from environment
    env = os.environ.get("TICKERGENIUS_ENV", "development").lower()

    # Resolve paths
    def resolve_path(p: str) -> str:
        p = os.path.expandvars(os.path.expanduser(p))
        if not os.path.isabs(p):
            p = os.path.join(base_dir, p)
        return os.path.normpath(p)

    cache_db = resolve_path(
        os.environ.get("TICKERGENIUS_CACHE_DB", "./tickergenius_cache.sqlite3")
    )
    data_dir = resolve_path(
        os.environ.get("TICKERGENIUS_DATA_DIR", "./data")
    )
    logs_dir = resolve_path(
        os.environ.get("TICKERGENIUS_LOGS_DIR", "./logs")
    )

    # SEC User-Agent (required for SEC.gov requests)
    sec_user_agent = os.environ.get(
        "SEC_USER_AGENT",
        f"TickerGenius/{__version__} (contact: your-email@example.com)"
    )

    # HTTP settings
    http_timeout = int(os.environ.get("TICKERGENIUS_HTTP_TIMEOUT", "15"))

    config = Config(
        version=__version__,
        cache_version=__cache_version__,
        http_timeout=http_timeout,
        cache_db=cache_db,
        workspace_root=base_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        sec_user_agent=sec_user_agent,
        env=env,
    )

    logger.info(f"Config loaded: env={env}, workspace={base_dir}")

    return config


def ensure_dirs(config: Config) -> None:
    """Create necessary directories for cache and data."""
    dirs = [
        os.path.dirname(config.cache_db),
        config.data_dir,
        config.logs_dir,
    ]
    for d in dirs:
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
                logger.debug(f"Created directory: {d}")
            except Exception as e:
                logger.warning(f"Failed to create directory {d}: {e}")
