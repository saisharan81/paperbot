"""Basic tests for Strategy base types."""

from src.paperbot.strategies.base import Signal, Strategy, Side


def test_signal_schema():
    s = Signal(
        ts=1700000000000,
        symbol="TEST/XYZ",
        strategy="mr",
        side="long",
        strength=0.9,
        reason="unit",
        params={"a": 1},
    )
    assert s.ts == 1700000000000
    assert s.symbol == "TEST/XYZ"
    assert s.strategy == "mr"
    assert s.side in ("long", "short", "flat")
    assert 0.0 <= s.strength <= 1.0
    assert isinstance(s.params, dict)


def test_strategy_interface_noop():
    st = Strategy(name="noop", config={})
    out = st.on_bar({"symbol": "S", "timestamp": 1})
    assert out is None

