"""Unit tests for MomentumStrategy (long-only RSI bands)."""

from src.paperbot.strategies.momentum import MomentumStrategy


def r(symbol: str, ts: int, rsi: float):
    return {
        "symbol": symbol,
        "timestamp": ts,
        "rsi14": rsi,
    }


def test_momentum_long_entry_and_exit():
    mo = MomentumStrategy({
        "enter_long_if_rsi_at_least": 60,
        "exit_long_if_rsi_at_most": 50,
        "confirm_bars": 0,
    })
    sym = "TEST/XYZ"

    # Start flat; RSI rises above 60 -> enter long
    sig = mo.on_bar(r(sym, 1, 61))
    assert sig is not None and sig.side == "long"

    # Stay long until RSI falls to 50 -> exit to flat
    sig = mo.on_bar(r(sym, 2, 49))
    assert sig is not None and sig.side == "flat"


def test_momentum_confirmation_bars():
    mo = MomentumStrategy({
        "enter_long_if_rsi_at_least": 60,
        "exit_long_if_rsi_at_most": 50,
        "confirm_bars": 2,
    })
    sym = "TEST/XYZ"

    # First bar meeting condition -> no signal yet (needs 2)
    sig = mo.on_bar(r(sym, 1, 61))
    assert sig is None
    # Second consecutive -> emit long
    sig = mo.on_bar(r(sym, 2, 62))
    assert sig is not None and sig.side == "long"

