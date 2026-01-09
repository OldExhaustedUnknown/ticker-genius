"""
Ticker-Genius Constants Repository
===================================
M3: JSON-based constants loader with type safety and verification tracking.

Design Principles:
1. Data-driven: All values in JSON, code doesn't hardcode values
2. Lazy loading: Constants loaded on first access
3. Caching: In-memory cache for fast repeated access
4. Type-safe: Typed dataclasses for constant values
5. Verification tracking: Each value has status (CONFIRMED/UNKNOWN)
6. Extensible: New constant categories without code changes
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
from functools import lru_cache

from tickergenius.schemas.base import DataStatus


# =============================================================================
# Data Classes
# =============================================================================

@dataclass(frozen=True)
class FactorValue:
    """A single factor adjustment value with metadata."""
    score: float
    classification: str  # FIXED_BONUS, FIXED_PENALTY, FACT, UNCERTAIN, etc.
    sample_size: Optional[int] = None
    approval_rate: Optional[float] = None
    source: str = ""
    condition: Optional[str] = None
    verification_status: str = "UNKNOWN"
    notes: Optional[str] = None

    def is_verified(self) -> bool:
        """Check if value is verified."""
        return self.verification_status == "CONFIRMED"


@dataclass(frozen=True)
class BaseRate:
    """Base approval rate with metadata."""
    rate: float
    description: str = ""
    source: str = ""
    verification_status: str = "UNKNOWN"

    def is_verified(self) -> bool:
        return self.verification_status == "CONFIRMED"


@dataclass(frozen=True)
class CapRule:
    """A cap rule (hard cap or floor)."""
    value: float
    conditions: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CapRule":
        return cls(
            value=data.get("max_probability") or data.get("min_probability", 0.0),
            conditions=data.get("conditions", []),
            description=data.get("description", ""),
        )


# =============================================================================
# Constants Loader
# =============================================================================

class ConstantsLoader:
    """
    Singleton loader for JSON constants.

    Usage:
        loader = ConstantsLoader.instance()
        btd = loader.get_factor("fda_designations", "breakthrough_therapy")
        base = loader.get_base_rate("nda_bla")
    """

    _instance: Optional["ConstantsLoader"] = None
    _constants_dir: Path = Path(__file__).parent.parent / "data" / "constants"

    def __init__(self):
        self._factor_adjustments: Optional[dict] = None
        self._base_rates: Optional[dict] = None
        self._cap_rules: Optional[dict] = None

    @classmethod
    def instance(cls) -> "ConstantsLoader":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # -------------------------------------------------------------------------
    # Lazy Loading
    # -------------------------------------------------------------------------

    def _load_json(self, filename: str) -> dict:
        """Load JSON file from constants directory."""
        filepath = self._constants_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Constants file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def factor_adjustments(self) -> dict:
        """Lazy load factor adjustments."""
        if self._factor_adjustments is None:
            self._factor_adjustments = self._load_json("factor_adjustments.json")
        return self._factor_adjustments

    @property
    def base_rates(self) -> dict:
        """Lazy load base rates."""
        if self._base_rates is None:
            self._base_rates = self._load_json("base_rates.json")
        return self._base_rates

    @property
    def cap_rules(self) -> dict:
        """Lazy load cap rules."""
        if self._cap_rules is None:
            self._cap_rules = self._load_json("cap_rules.json")
        return self._cap_rules

    # -------------------------------------------------------------------------
    # Factor Access
    # -------------------------------------------------------------------------

    def get_factor(self, category: str, name: str) -> Optional[FactorValue]:
        """
        Get a factor adjustment value.

        Args:
            category: Category name (fda_designations, adcom, crl_resubmission, etc.)
            name: Factor name within category

        Returns:
            FactorValue or None if not found
        """
        cat_data = self.factor_adjustments.get(category, {})
        factor_data = cat_data.get(name)

        if factor_data is None:
            return None

        return FactorValue(
            score=factor_data.get("score", 0.0),
            classification=factor_data.get("classification", "UNKNOWN"),
            sample_size=factor_data.get("sample_size"),
            approval_rate=factor_data.get("approval_rate"),
            source=factor_data.get("source", ""),
            condition=factor_data.get("condition"),
            verification_status=factor_data.get("verification_status", "UNKNOWN"),
            notes=factor_data.get("notes"),
        )

    def get_all_factors(self, category: str) -> dict[str, FactorValue]:
        """Get all factors in a category."""
        cat_data = self.factor_adjustments.get(category, {})
        result = {}

        for name, data in cat_data.items():
            if name.startswith("_"):  # Skip metadata
                continue
            factor = self.get_factor(category, name)
            if factor:
                result[name] = factor

        return result

    def list_categories(self) -> list[str]:
        """List all factor categories."""
        return [k for k in self.factor_adjustments.keys() if not k.startswith("_")]

    # -------------------------------------------------------------------------
    # Base Rate Access
    # -------------------------------------------------------------------------

    def get_base_rate(self, key: str) -> Optional[BaseRate]:
        """
        Get a base approval rate.

        Args:
            key: Rate key (phase3, nda_bla, resubmission.class1, etc.)

        Returns:
            BaseRate or None if not found
        """
        # Handle nested keys like "resubmission.class1"
        parts = key.split(".")
        data = self.base_rates

        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                return None

        if data is None or not isinstance(data, dict):
            # Check by_phase and by_application_type
            for section in ["by_phase", "by_application_type"]:
                section_data = self.base_rates.get(section, {})
                if key in section_data:
                    data = section_data[key]
                    break

        if data is None or not isinstance(data, dict):
            return None

        return BaseRate(
            rate=data.get("rate", 0.0),
            description=data.get("description", ""),
            source=data.get("source", ""),
            verification_status=data.get("verification_status", "UNKNOWN"),
        )

    def get_default_base_rate(self) -> float:
        """Get default base rate (NDA/BLA baseline)."""
        default_data = self.base_rates.get("default", {})
        return default_data.get("rate", 0.70)

    # -------------------------------------------------------------------------
    # Cap Rules Access
    # -------------------------------------------------------------------------

    def get_probability_bounds(self) -> tuple[float, float]:
        """Get probability bounds (min, max)."""
        bounds = self.cap_rules.get("probability_bounds", {})
        return (bounds.get("min", 0.10), bounds.get("max", 0.90))

    def get_hard_caps(self) -> dict[str, CapRule]:
        """Get all hard cap rules."""
        caps_data = self.cap_rules.get("hard_caps", {})
        return {
            name: CapRule.from_dict(data)
            for name, data in caps_data.items()
        }

    def get_floor_rules(self) -> dict[str, CapRule]:
        """Get all floor rules."""
        floors_data = self.cap_rules.get("floor_rules", {})
        return {
            name: CapRule.from_dict(data)
            for name, data in floors_data.items()
        }


# =============================================================================
# Module-level convenience functions
# =============================================================================

def get_factor_adjustment(category: str, name: str) -> Optional[FactorValue]:
    """Get factor adjustment (convenience function)."""
    return ConstantsLoader.instance().get_factor(category, name)


def get_base_rate(key: str) -> Optional[BaseRate]:
    """Get base rate (convenience function)."""
    return ConstantsLoader.instance().get_base_rate(key)


def get_cap_rule(cap_type: str, name: str) -> Optional[CapRule]:
    """Get cap rule (convenience function)."""
    loader = ConstantsLoader.instance()
    if cap_type == "hard_caps":
        caps = loader.get_hard_caps()
    elif cap_type == "floor_rules":
        caps = loader.get_floor_rules()
    else:
        return None
    return caps.get(name)


def get_probability_bounds() -> dict[str, float]:
    """Get probability bounds (convenience function)."""
    min_val, max_val = ConstantsLoader.instance().get_probability_bounds()
    return {"min": min_val, "max": max_val}


def get_hard_cap(level: str) -> Optional[float]:
    """
    Get hard cap value for a severity level.

    Args:
        level: Severity level (catastrophic, critical, severe, moderate)

    Returns:
        Cap value (max probability) or None if not found
    """
    caps = ConstantsLoader.instance().get_hard_caps()
    cap_rule = caps.get(level)
    if cap_rule:
        return cap_rule.value
    return None


def get_floor(name: str) -> Optional[float]:
    """
    Get floor value for a floor rule.

    Args:
        name: Floor rule name (has_fda_designation, spa_agreed)

    Returns:
        Floor value (min probability) or None if not found
    """
    floors = ConstantsLoader.instance().get_floor_rules()
    floor_rule = floors.get(name)
    if floor_rule:
        return floor_rule.value
    return None


__all__ = [
    "FactorValue",
    "BaseRate",
    "CapRule",
    "ConstantsLoader",
    "get_factor_adjustment",
    "get_base_rate",
    "get_cap_rule",
    "get_probability_bounds",
    "get_hard_cap",
    "get_floor",
]
