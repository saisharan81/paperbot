"""Global risk halt flags used to coordinate session-wide stop states.

These flags are intentionally simple (module-level dict) because the
current runtime is a single-process paper trading bot. If/when we migrate
execution into a distributed service, this module becomes the seam for
backing the flags with Redis or another shared datastore.
"""
from __future__ import annotations

from typing import Dict

HALT_DAILY_STOP = "DAILY_STOP"
HALT_KILL_SWITCH = "KILL_SWITCH"

# Maintain a predictable set of flags so callers can snapshot safely.
_default_flags = {
    HALT_DAILY_STOP: False,
    HALT_KILL_SWITCH: False,
}

_flags: Dict[str, bool] = dict(_default_flags)


def set_flag(name: str, active: bool) -> None:
    """Set a halt flag to the provided boolean state."""
    if name not in _flags:
        # Allow discovery of new flags without crashing; default to bool.
        _flags[name] = bool(active)
        return
    _flags[name] = bool(active)


def get_flag(name: str) -> bool:
    """Return the current boolean state for a halt flag (defaults False)."""
    return bool(_flags.get(name, False))


def reset_flags() -> None:
    """Reset all known halt flags to their default (False)."""
    for key in list(_flags.keys()):
        _flags[key] = _default_flags.get(key, False)


def snapshot() -> Dict[str, bool]:
    """Return a shallow copy of the current halt flag states."""
    return dict(_flags)


def any_active() -> bool:
    """Convenience helper: return True if any halt flag is active."""
    return any(bool(val) for val in _flags.values())
