from src.paperbot.risk.engine import RiskEngine
from src.paperbot.strategies.base import Signal


def make_signal(symbol: str, ts: int, side: str, strategy: str = "mr"):
    return Signal(ts=ts, symbol=symbol, strategy=strategy, side=side, strength=1.0, reason="t", params={})


def test_risk_sizing_and_caps():
    cfg = {"risk_frac": 0.0025, "atr_stop_mult": 1.5, "max_position_value_per_symbol": 0.2}
    r = RiskEngine(cfg, equity_start=10_000.0)
    sig = make_signal("BTC/USDT", 1, "long")
    features = {"price": 100.0, "atr14": 2.0}
    order = r.approve(sig, features, equity=10_000.0)
    assert order is not None and order.side == "buy" and order.type == "market"
    # qty ~= (eq*risk_frac)/(atr*mult) = (10000*0.0025)/(3.0) ~= 8.3333
    assert 8.0 < order.qty < 8.5


def test_risk_killswitch_blocks():
    r = RiskEngine({}, equity_start=10_000.0)
    # Trip killswitch by passing low equity
    r.on_realized_pnl(equity=9_800.0)
    assert r.killswitch_on is True
    sig = make_signal("BTC/USDT", 1, "long")
    features = {"price": 100.0, "atr14": 1.0}
    assert r.approve(sig, features, equity=9_800.0) is None

