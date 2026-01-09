"""
Ticker-Genius Data Collection Module
=====================================
M3: Automated PDUFA data collection and verification.
"""

from tickergenius.collection.collector import DataCollector
from tickergenius.collection.models import CollectedCase, ValidationResult

__all__ = ["DataCollector", "CollectedCase", "ValidationResult"]
