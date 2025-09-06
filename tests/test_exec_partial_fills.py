from src.paperbot.exec.simulator import ExecutionSimulator
from src.paperbot.exec.model import Order, new_id


def test_partial_fills_two_bars_rounding():
    profile = {"step_size": 1.0, "tick_size": 0.01, "min_notional": 0.0}
    sim = ExecutionSimulator({"liquidity_fraction": 0.25}, profile=profile)
    order = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=100.0, price=None, strategy="t", reason="t", params={})
    cndl = {"timestamp": 2, "close": 10.0}
    fills1 = sim.submit(order, cndl)
    fills2 = sim.submit(order, cndl)
    filled = sum(f.qty for f in fills1 + fills2)
    assert 49 <= filled <= 51

def test_min_notional_blocks():
    profile = {"min_notional": 50.0, "step_size": 1.0, "tick_size": 0.01}
    sim = ExecutionSimulator({}, profile=profile)
    order = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=4.0, price=None, strategy="t", reason="t", params={})
    cndl = {"timestamp": 2, "close": 10.0}
    fills = sim.submit(order, cndl)
    assert fills == []
