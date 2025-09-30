import pytest

from src.paperbot.risk.engine import RiskEngine
from src.paperbot.risk.killswitch import reset_killswitch, check_killswitch
from src.paperbot.risk.halt_flags import (
    reset_flags as reset_halt_flags,
    snapshot as snapshot_halt_flags,
    HALT_DAILY_STOP,
    HALT_KILL_SWITCH,
)
from src.paperbot.events.schema import DailyLossLimitBreach
from src.paperbot.strategies.base import Signal


def _make_signal(symbol: str, ts: int, side: str, strategy: str = "mr") -> Signal:
    return Signal(ts=ts, symbol=symbol, strategy=strategy, side=side, strength=1.0, reason="t", params={})


def test_daily_loss_limit_breach_sets_daily_stop_without_kill_switch(monkeypatch):
    reset_killswitch()
    reset_halt_flags()
    published = []

    def _capture_publish(env):
        published.append(env)

    monkeypatch.setattr("src.paperbot.risk.engine.publish_event", _capture_publish)

    engine = RiskEngine({"daily_loss_cap_pct": 0.05}, equity_start=10_000.0)
    equity_after_loss = 10_000.0 - 501.0
    engine.on_realized_pnl(equity=equity_after_loss, timestamp=1_700_000_000_000)

    flags = snapshot_halt_flags()
    assert flags[HALT_DAILY_STOP] is True
    assert flags[HALT_KILL_SWITCH] is False
    assert engine.is_active is True
    assert check_killswitch("crypto") is False

    assert published, "DailyLossLimitBreach event should be emitted"
    breach_events = [env.event for env in published if isinstance(env.event, DailyLossLimitBreach)]
    assert breach_events, "Expected DailyLossLimitBreach in published events"
    breach = breach_events[-1]
    assert breach.equity == pytest.approx(equity_after_loss, rel=1e-6)
    assert breach.equity_start == pytest.approx(10_000.0, rel=1e-6)
    assert breach.pct_drop == pytest.approx(0.0501, rel=1e-3)
    assert breach.flags[HALT_DAILY_STOP] is True
    assert breach.flags[HALT_KILL_SWITCH] is False

    sig = _make_signal("BTC/USDT", ts=2, side="long")
    features = {"price": 100.0, "atr14": 1.0, "timestamp": 2}
    assert engine.approve(sig, features, equity=equity_after_loss) is None
