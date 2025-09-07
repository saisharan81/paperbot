import pytest
from src.paperbot.llm.contracts import Decision


def test_decision_schema_bounds():
    d = Decision(
        run_id="r1",
        ts=1700000000000,
        market="crypto",
        symbol="BTC/USDT",
        side="buy",
        size=0.0,
        max_notional_usd=100.0,
        confidence=0.6,
        reason=["ok"],
        ttl_s=30,
        features_used=["rsi14"],
    )
    assert d.confidence == 0.6

    with pytest.raises(Exception):
        Decision(
            run_id="r1",
            ts=0,
            market="crypto",
            symbol="BTC/USDT",
            side="buy",
            size=-1.0,
            max_notional_usd=0.0,
            confidence=1.2,
            reason=[],
            ttl_s=-1,
            features_used=[],
        )

