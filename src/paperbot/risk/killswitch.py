from __future__ import annotations

from typing import Dict

from paperbot.metrics.exec import set_killswitch_state as _set_state_metric


_state: Dict[str, bool] = {}


def set_killswitch_state(market: str, active: bool) -> None:
    """Record kill switch state and update Prometheus gauge."""
    market_key = market or "unknown"
    _state[market_key] = bool(active)
    _set_state_metric(market_key, bool(active))


def check_killswitch(market: str | None = None) -> bool:
    """Return True if kill switch active for a market or any market."""
    if market is None:
        return any(_state.values())
    return _state.get(market or "unknown", False)


def reset_killswitch(market: str | None = None) -> None:
    """Clear kill switch state (primarily for tests)."""
    if market is None:
        keys = list(_state.keys())
    else:
        keys = [market or "unknown"]
    for key in keys:
        _state[key] = False
        _set_state_metric(key, False)
