import pytest

from src.paperbot.exec.model import Order, new_id
from src.paperbot.ledger.ledger import Ledger
from src.paperbot.exec.simulator import ExecutionSimulator


def test_market_fill_with_slippage_and_fee():
    sim = ExecutionSimulator(
        {"slippage_bps_market": 10, "taker_bps": 5, "liquidity_fraction": 1.0},
        profile={"tick_size": 0.000001, "step_size": 1.0},
    )
    order = Order(
        id=new_id(),
        ts=1,
        symbol="BTC/USDT",
        side="buy",
        type="market",
        qty=1.0,
        price=None,
        strategy="t",
        reason="t",
        params={}
    )
    candle = {"timestamp": 2, "close": 100.0}
    fills = sim.submit(order, candle)
    assert len(fills) == 1
    f = fills[0]
    # price = 100 * (1 + 10bps) = 100 * 1.001 = 100.1
    assert 100.09 < f.price < 100.11
    # fee = notional * 5bps = 100.1 * 0.0005 ≈ 0.05005
    assert 0.04 < f.fee < 0.06
    assert f.fee_currency == "USDT"
    assert abs(f.fee_usd - f.fee) < 1e-6


def test_limit_fill_cross_maker_fee():
    sim = ExecutionSimulator({"maker_bps": 5})
    order = Order(
        id=new_id(),
        ts=1,
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        qty=1.0,
        price=99.0,
        strategy="t",
        reason="t",
        params={}
    )
    candle = {"timestamp": 2, "open": 100.0, "high": 101.0, "low": 98.5, "close": 100.0}
    fills = sim.submit(order, candle)
    assert len(fills) == 1
    f = fills[0]
    assert f.price == 99.0
    assert f.fee > 0
    assert f.fee_currency == "USDT"
    assert abs(f.fee_usd - f.fee) < 1e-6


def test_fee_conversion_non_usd_pair_updates_ledger():
    profile = {
        "tick_size": 0.000001,
        "step_size": 0.0001,
        "oracle": {
            "fx_overrides": {"ETH": 1800.0},
        },
    }
    sim = ExecutionSimulator(
        {"taker_bps": 10, "liquidity_fraction": 1.0, "slippage_bps_market": 0.0},
        profile=profile,
    )
    order = Order(
        id=new_id(),
        ts=1,
        symbol="BTC/ETH",
        side="buy",
        type="market",
        qty=0.2,
        price=None,
        strategy="t",
        reason="t",
        params={},
        fee_currency="BTC",
    )
    candle = {"timestamp": 2, "close": 15.0}
    fills = sim.submit(order, candle)
    assert len(fills) == 1
    f = fills[0]
    # fee in BTC = qty * rate (10bps=0.001)
    assert f.fee_currency == "BTC"
    assert pytest.approx(0.0002, rel=1e-6) == f.fee
    # Base USD price = close (15 ETH) * ETHUSD (1800) = 27000
    assert pytest.approx(5.4, rel=1e-6) == f.fee_usd

    ledger = Ledger(equity_start=10_000.0)
    ledger.on_fill(f)
    assert pytest.approx(-5.4, rel=1e-6) == ledger.realized_total
