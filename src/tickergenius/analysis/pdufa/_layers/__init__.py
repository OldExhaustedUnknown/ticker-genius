"""
Ticker-Genius Probability Layers
=================================
M3: Modular probability adjustment layers.

Each layer handles one aspect of probability adjustment.
Layers are independent and can be added/removed without affecting others.

Layer Order:
1. base - Base approval rate
2. designation - FDA designations (BTD, Priority, etc.)
3. adcom - Advisory Committee results
4. crl - CRL history and resubmission
5. clinical - Clinical trial factors
6. manufacturing - Manufacturing/facility factors
7. dispute - FDA dispute resolution
8. earnings_call - Earnings call signals
9. citizen_petition - Citizen petitions
10. special - Special factors (SPA, first-in-class, etc.)
11. context - Context interactions between factors
12. cap - Hard caps and floors
"""

# Import all layers to register them with FactorRegistry
from tickergenius.analysis.pdufa._layers import (
    base,
    designation,
    adcom,
    crl,
    clinical,
    manufacturing,
    dispute,
    earnings_call,
    citizen_petition,
    special,
    context,
    cap,
)

# Define layer order for calculation
LAYER_ORDER = [
    "base",
    "designation",
    "adcom",
    "crl",
    "clinical",
    "manufacturing",
    "dispute",
    "earnings_call",
    "citizen_petition",
    "special",
    "context",
    "cap",
]

__all__ = ["LAYER_ORDER"]
