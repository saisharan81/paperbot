from src.paperbot.ledger.ledger import Ledger
from src.paperbot.exec.model import Fill


def test_ledger_open_reduce_and_mtm(tmp_path):
    led = Ledger(equity_start=10_000.0)
    # Open long 1 @100 (fee 0.01)
    led.on_fill(
        Fill(
            order_id="1",
            ts=1,
            symbol="BTC/USDT",
            qty=1.0,
            price=100.0,
            fee=0.01,
            fee_currency="USDT",
            fee_usd=0.01,
            liquidity="taker",
        )
    )
    assert led.positions["BTC/USDT"].qty == 1.0
    # Sell 0.4 @110 (fee 0.01) -> realized ~ (110-100)*0.4 - 0.01 = 3.99
    led.on_fill(
        Fill(
            order_id="2",
            ts=2,
            symbol="BTC/USDT",
            qty=-0.4,
            price=110.0,
            fee=0.01,
            fee_currency="USDT",
            fee_usd=0.01,
            liquidity="taker",
        )
    )
    assert led.realized_total > 3.9
    # MTM with price 105
    led.mark_to_market(3, {"BTC/USDT": 105.0})
    assert led.equity > 10_000.0
