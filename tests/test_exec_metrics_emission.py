from prometheus_client import REGISTRY

from src.paperbot.exec.model import Order, new_id, Fill
from src.paperbot.exec.simulator import ExecutionSimulator
from src.paperbot.ledger.ledger import Ledger


def test_fees_paid_usd_total_increments_on_fill():
    sim = ExecutionSimulator({"slippage_bps_market": 0, "taker_bps": 10, "liquidity_fraction": 1.0}, profile={"tick_size": 0.000001, "step_size": 1.0})
    order = Order(
        id=new_id(), ts=1, symbol="BTC/USDT", side="buy", type="market", qty=1.0, price=None, strategy="t", reason="t", params={}
    )
    candle = {"timestamp": 2, "close": 100.0}
    fills = sim.submit(order, candle)
    assert fills, "expected at least one fill"

    # Check that the USD-denominated fees counter increased for market=crypto
    val = REGISTRY.get_sample_value("fees_paid_usd_total", {"market": "crypto", "symbol": "BTC/USDT"})
    assert val is not None and val > 0.0


def test_account_equity_usd_set_after_mtm():
    led = Ledger(equity_start=10_000.0)
    # Open a position to move equity and then MTM
    led.on_fill(Fill(order_id="1", ts=1, symbol="BTC/USDT", qty=1.0, price=100.0, fee=0.01, liquidity="taker"))
    led.mark_to_market(2, {"BTC/USDT": 105.0})

    # Gauge should be set for inferred market=crypto
    val = REGISTRY.get_sample_value("account_equity_usd", {"market": "crypto"})
    assert val is not None and val > 0.0

