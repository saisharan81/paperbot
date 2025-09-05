"""Unit tests for MeanReversionStrategy."""

from src.paperbot.strategies.mr import MeanReversionStrategy


def row(symbol: str, ts: int, z: float, rv: float = 0.0):
    return {
        "symbol": symbol,
        "timestamp": ts,
        "z_vwap": z,
        "rv_30m": rv,
    }


def test_mr_enters_and_exits_long_short():
    mr = MeanReversionStrategy({
        "enter_long_if_below": -1.5,
        "exit_long_if_above": -0.3,
        "enter_short_if_above": 1.5,
        "exit_short_if_below": 0.3,
        "vol_gate_rv_30m_max": 0.03,
    })
    sym = "TEST/XYZ"

    # Start flat; z drops below -1.5 -> enter long
    sig = mr.on_bar(row(sym, 1, -1.6, 0.01))
    assert sig is not None and sig.side == "long"

    # Stay long until z rises above -0.3 -> exit to flat
    sig = mr.on_bar(row(sym, 2, -0.2, 0.01))
    assert sig is not None and sig.side == "flat"

    # From flat; z above 1.5 -> enter short
    sig = mr.on_bar(row(sym, 3, 1.6, 0.01))
    assert sig is not None and sig.side == "short"

    # Exit short when z <= 0.3
    sig = mr.on_bar(row(sym, 4, 0.2, 0.01))
    assert sig is not None and sig.side == "flat"


def test_mr_vol_gate_suppresses_entries():
    mr = MeanReversionStrategy({"vol_gate_rv_30m_max": 0.03})
    sym = "TEST/XYZ"
    # High realized vol should suppress any entries
    sig = mr.on_bar(row(sym, 1, -2.0, 0.05))
    assert sig is None
    sig = mr.on_bar(row(sym, 2, 2.0, 0.05))
    assert sig is None

