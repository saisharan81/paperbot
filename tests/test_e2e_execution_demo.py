import os
import logging
from src.paperbot import main as main_mod


def test_offline_execution_demo_emits_orders_and_fills(monkeypatch, caplog):
    monkeypatch.setenv("OFFLINE_DEMO", "1")
    monkeypatch.setenv("BINANCE_SPOT_TESTNET_API_KEY", "foo")
    monkeypatch.setenv("BINANCE_SPOT_TESTNET_API_SECRET", "bar")
    # Port may be blocked; PROMETHEUS_PORT provided but failure is tolerated in code
    monkeypatch.setenv("PROMETHEUS_PORT", "8000")
    caplog.set_level(logging.INFO)
    main_mod.main()
    out = "\n".join([r.message for r in caplog.records])
    # Look for order/filled and final line
    assert "order submitted: {" in out
    assert "fill: {" in out
    assert "execution demo complete" in out
    # Check parquet outputs exist
    assert os.path.exists("data/trades.parquet")
    assert os.path.exists("data/ledger.parquet")
