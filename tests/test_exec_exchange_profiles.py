from src.paperbot.exec.simulator import ExecutionSimulator
from src.paperbot.exec.model import Order, new_id


def test_rounding_and_fees_maker_taker():
    profile = {"fees": {"maker_bps": 10.0, "taker_bps": 20.0}, "tick_size": 0.05, "step_size": 0.1}
    sim = ExecutionSimulator({}, profile=profile)
    # market taker
    o1 = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=1.0, price=None, strategy="t", reason="t", params={})
    c = {"timestamp": 2, "close": 100.0}
    f1 = sim.submit(o1, c)[0]
    assert abs(f1.fee - (f1.price * abs(f1.qty)) * 0.002) < 1e-6
    # limit maker crossed
    o2 = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="limit", qty=1.0, price=99.97, strategy="t", reason="t", params={})
    f2 = sim.submit(o2, {"timestamp": 2, "open": 100.0, "high": 101.0, "low": 99.90, "close": 100.0})[0]
    # tick rounding to 0.05: 99.95
    assert abs(f2.price - 99.95) < 1e-9
    assert abs(f2.fee - (f2.price * abs(f2.qty)) * 0.001) < 1e-6
