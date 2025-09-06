from src.paperbot.exec.simulator import ExecutionSimulator
from src.paperbot.exec.model import Order, new_id


def test_fixed_bps_slippage():
    sim = ExecutionSimulator({"slippage_bps_market": 10, "slippage_model": "fixed_bps", "liquidity_fraction": 1.0}, profile={"tick_size": 0.000001, "step_size": 1.0})
    o = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=1.0, price=None, strategy="t", reason="t", params={})
    c = {"timestamp": 2, "close": 100.0}
    f = sim.submit(o, c)[0]
    assert 100.099 < f.price < 100.101


def test_atr_scaled_slippage():
    sim = ExecutionSimulator({"slippage_bps_market": 10, "slippage_model": "atr_scaled", "atr_slip_mult": 1.0, "liquidity_fraction": 1.0}, profile={"tick_size": 0.000001, "step_size": 1.0})
    o = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=1.0, price=None, strategy="t", reason="t", params={})
    c = {"timestamp": 2, "close": 100.0}
    f = sim.submit(o, c, features={"atr14": 2.0})[0]
    # expected bps = 10 * (2/100) = 0.2 bps => price ~ 100 * (1 + 0.00002) = 100.002
    assert 100.001 < f.price < 100.003
