"""
Ticker-Genius Repositories
===========================
M3: Data access layer with repository pattern.

Provides clean interfaces for data access, abstracting storage details.
"""

from tickergenius.repositories.constants import (
    ConstantsLoader,
    get_factor_adjustment,
    get_base_rate,
    get_cap_rule,
)

__all__ = [
    "ConstantsLoader",
    "get_factor_adjustment",
    "get_base_rate",
    "get_cap_rule",
]
