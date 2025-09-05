from __future__ import annotations

"""
Strategy base types for paperbot Phase 1.2.

Defines a normalized Signal schema and a simple Strategy interface.
Per Phase 1.2 scope, strategies emit signals only (no sizing yet).
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal


Side = Literal["long", "short", "flat"]


@dataclass
class Signal:
    """A normalized trading signal.

    Attributes:
        ts: UTC timestamp in milliseconds (from feature row)
        symbol: Instrument symbol (e.g., "BTC/USDT")
        strategy: Strategy identifier (e.g., "mr", "momentum")
        side: "long" | "short" | "flat" (flat = exit/neutral)
        strength: Normalized confidence in [0, 1]
        reason: Short explanation for auditability
        params: Snapshot of thresholds/params used to generate the signal
    """

    ts: int
    symbol: str
    strategy: str
    side: Side
    strength: float
    reason: str
    params: Dict[str, Any]


class Strategy:
    """Base strategy interface.

    Subclasses implement `on_bar` and may keep internal state per symbol.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config or {}

    def on_bar(self, features: Dict[str, Any]) -> Optional[Signal]:
        """Process a single feature row and optionally emit a Signal.

        Args:
            features: Feature dict from FeatureBuilder.compute_latest().

        Returns:
            A Signal or None when no action is taken.
        """
        return None

