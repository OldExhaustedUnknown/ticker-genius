"""
Ticker-Genius Data Collection Module
=====================================
M3: Automated PDUFA data collection and verification.
"""

from tickergenius.collection.collector import DataCollector
from tickergenius.collection.models import CollectedCase, ValidationResult
from tickergenius.collection.search_exceptions import (
    SearchException,
    RateLimitException,
    APIBlockedException,
    TimeoutException,
    DataNotFoundException,
    ValidationException,
)
from tickergenius.collection.fallback_chain import (
    FallbackChainManager,
    ChainExecutionResult,
    FallbackChainConfig,
    SourceConfig,
    DataSource,
    create_fallback_chain_manager,
    FALLBACK_CHAINS,
)
from tickergenius.collection.checkpoint import (
    CheckpointManager,
    CheckpointState,
    FieldProgress,
    FailedEvent,
    WaveProgress,
)

__all__ = [
    "DataCollector",
    "CollectedCase",
    "ValidationResult",
    # Search Exceptions
    "SearchException",
    "RateLimitException",
    "APIBlockedException",
    "TimeoutException",
    "DataNotFoundException",
    "ValidationException",
    # Fallback Chain
    "FallbackChainManager",
    "ChainExecutionResult",
    "FallbackChainConfig",
    "SourceConfig",
    "DataSource",
    "create_fallback_chain_manager",
    "FALLBACK_CHAINS",
    # Checkpoint
    "CheckpointManager",
    "CheckpointState",
    "FieldProgress",
    "FailedEvent",
    "WaveProgress",
]
