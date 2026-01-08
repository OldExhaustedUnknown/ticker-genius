"""
Ticker-Genius Version Information
=================================
Single Source of Truth for all version numbers.

This file is the ONLY place where versions are defined.
All other files must import from here.
"""

# Application version (semver)
__version__ = "4.0.0"

# Schema version for data models (Pydantic schemas)
__schema_version__ = "1.0.0"

# API version for MCP tools
__api_version__ = "v1"

# Cache schema version (for migration detection)
__cache_version__ = "4_0_0"

# Build info (set by CI/CD, empty in dev)
__build_date__ = ""
__build_commit__ = ""


def get_version_info() -> dict:
    """Get complete version information as dictionary."""
    return {
        "version": __version__,
        "schema_version": __schema_version__,
        "api_version": __api_version__,
        "cache_version": __cache_version__,
        "build_date": __build_date__,
        "build_commit": __build_commit__,
    }


def get_user_agent() -> str:
    """Get User-Agent string for HTTP requests."""
    return f"TickerGenius/{__version__}"
