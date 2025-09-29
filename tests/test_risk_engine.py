from src.paperbot.risk.engine import RiskEngine
from src.paperbot.risk.killswitch import reset_killswitch, check_killswitch
from src.paperbot.strategies.base import Signal


def make_signal(symbol: str, ts: int, side: str, strategy: str = "mr"):
    return Signal(ts=ts, symbol=symbol, strategy=strategy, side=side, strength=1.0, reason="t", params={})


def test_risk_sizing_and_caps():
    reset_killswitch()
    cfg = {"risk_frac": 0.0025, "atr_stop_mult": 1.5, "max_position_value_per_symbol": 0.2}
    r = RiskEngine(cfg, equity_start=10_000.0)
    sig = make_signal("BTC/USDT", 1, "long")
    features = {"price": 100.0, "atr14": 2.0}
    order = r.approve(sig, features, equity=10_000.0)
    assert order is not None and order.side == "buy" and order.type == "market"
    # qty ~= (eq*risk_frac)/(atr*mult) = (10000*0.0025)/(3.0) ~= 8.3333
    assert 8.0 < order.qty < 8.5


def test_risk_killswitch_blocks():
    reset_killswitch()
    r = RiskEngine({"daily_loss_cap_pct": 0.02}, equity_start=10_000.0)
    # Trip killswitch by passing low equity
    r.on_realized_pnl(equity=9_700.0)
    assert r.is_active is True
    assert check_killswitch("crypto") is True
    sig = make_signal("BTC/USDT", 1, "long")
    features = {"price": 100.0, "atr14": 1.0, "timestamp": 1}
    assert r.approve(sig, features, equity=9_700.0) is None


def test_risk_killswitch_blocks_followup_calls():
    reset_killswitch()
    r = RiskEngine({"daily_loss_cap_pct": 0.01}, equity_start=10_000.0)
    r.on_realized_pnl(equity=9_800.0)
    assert r.is_active
    # Another risk engine instance should observe global killswitch
    r2 = RiskEngine({}, equity_start=10_000.0)
    sig = make_signal("BTC/USDT", 5, "long")
    features = {"price": 100.0, "atr14": 1.0, "timestamp": 5}
    assert r2.approve(sig, features, equity=9_800.0) is None


def test_risk_killswitch_after_sequential_losses_blocks_orders():
    reset_killswitch()
    r = RiskEngine({"daily_loss_cap_pct": 0.02}, equity_start=10_000.0)

    # Losses that should not yet trigger the cap
    r.on_realized_pnl(equity=9_900.0)
    assert not r.is_active

    # Crossing the cap should activate the killswitch
    r.on_realized_pnl(equity=9_700.0)
    assert r.is_active is True
    assert check_killswitch("crypto") is True

    sig = make_signal("BTC/USDT", 123456, "long")
    features = {"price": 100.0, "atr14": 1.0, "timestamp": 123456}
    assert r.approve(sig, features, equity=9_700.0) is None
