import random
from src.paperbot.exec.simulator import ExecutionSimulator
from src.paperbot.exec.model import Order, new_id


def test_random_bps_slippage_range():
    random.seed(1234)
    sim = ExecutionSimulator({"slippage_model": "random_bps", "slippage_random_bps_range": [0, 3], "liquidity_fraction": 1.0}, profile={"tick_size": 0.000001, "step_size": 1.0})
    o = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=1.0, price=None, strategy="t", reason="t", params={})
    # Close 100 → price should be >=100, sometimes slightly above depending on draw
    c = {"timestamp": 2, "close": 100.0}
    prices = []
    for _ in range(5):
        f = sim.submit(o, c)[0]
        prices.append(f.price)
        # reset remaining to allow full fills for repeated calls
        sim._remaining[o.id] = o.qty
    assert any(p > 100.0 for p in prices)
