from src.paperbot.exec.model import Order, new_id
from src.paperbot.exec.simulator import ExecutionSimulator


def test_market_fill_with_slippage_and_fee():
    sim = ExecutionSimulator({"slippage_bps_market": 10, "taker_bps": 5})
    order = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=1.0, price=None, strategy="t", reason="t", params={})
    candle = {"timestamp": 2, "close": 100.0}
    fills = sim.submit(order, candle)
    assert len(fills) == 1
    f = fills[0]
    # price = 100 * (1 + 10bps) = 100 * 1.001 = 100.1
    assert 100.09 < f.price < 100.11
    # fee = notional * 5bps = 100.1 * 0.0005 ≈ 0.05005
    assert 0.04 < f.fee < 0.06


def test_limit_fill_cross_maker_fee():
    sim = ExecutionSimulator({"maker_bps": 5})
    order = Order(id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="limit", qty=1.0, price=99.0, strategy="t", reason="t", params={})
    candle = {"timestamp": 2, "open": 100.0, "high": 101.0, "low": 98.5, "close": 100.0}
    fills = sim.submit(order, candle)
    assert len(fills) == 1
    f = fills[0]
    assert f.price == 99.0
    assert f.fee > 0

