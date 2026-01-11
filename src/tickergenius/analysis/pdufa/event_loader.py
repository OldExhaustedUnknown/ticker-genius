"""
Event Loader
=============
Load enriched events and convert to AnalysisContext.

Usage:
    from tickergenius.analysis.pdufa.event_loader import EventLoader

    loader = EventLoader()
    ctx = loader.load_event("ABBV_0f6cbdde2a91")
    all_contexts = loader.load_all()
"""

import json
from pathlib import Path
from typing import Optional, Iterator

from ._context import AnalysisContext


class EventLoader:
    """Load enriched events as AnalysisContext."""

    def __init__(self, data_dir: str = "data/enriched"):
        self.data_dir = Path(data_dir)

    def load_event(self, event_id: str) -> Optional[AnalysisContext]:
        """Load single event by ID."""
        # Try with and without extension
        file_path = self.data_dir / f"{event_id}.json"
        if not file_path.exists():
            # Try finding by prefix
            matches = list(self.data_dir.glob(f"{event_id}*.json"))
            if matches:
                file_path = matches[0]
            else:
                return None

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            data["_event_id"] = file_path.stem
            return AnalysisContext.from_enriched(data)
        except Exception:
            return None

    def load_by_ticker(self, ticker: str) -> list[AnalysisContext]:
        """Load all events for a ticker."""
        contexts = []
        for f in self.data_dir.glob(f"{ticker.upper()}_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["_event_id"] = f.stem
                ctx = AnalysisContext.from_enriched(data)
                contexts.append(ctx)
            except Exception:
                continue
        return contexts

    def load_all(self) -> list[AnalysisContext]:
        """Load all events."""
        contexts = []
        for f in sorted(self.data_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["_event_id"] = f.stem
                ctx = AnalysisContext.from_enriched(data)
                contexts.append(ctx)
            except Exception:
                continue
        return contexts

    def iter_all(self) -> Iterator[tuple[str, AnalysisContext]]:
        """Iterate all events with event_id."""
        for f in sorted(self.data_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["_event_id"] = f.stem
                ctx = AnalysisContext.from_enriched(data)
                yield f.stem, ctx
            except Exception:
                continue

    def load_with_outcome(self) -> list[tuple[AnalysisContext, str]]:
        """Load events with known outcomes (for backtest)."""
        results = []
        for f in sorted(self.data_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                outcome = data.get("result")
                if outcome in ("approved", "crl"):
                    ctx = AnalysisContext.from_enriched(data)
                    results.append((ctx, outcome))
            except Exception:
                continue
        return results


# Convenience function
def load_event(event_id: str) -> Optional[AnalysisContext]:
    """Quick load single event."""
    return EventLoader().load_event(event_id)


def load_all_events() -> list[AnalysisContext]:
    """Quick load all events."""
    return EventLoader().load_all()


__all__ = ["EventLoader", "load_event", "load_all_events"]
