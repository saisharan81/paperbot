from src.paperbot.llm.memory.sqlite_store import SQLiteStore


def test_sqlite_store_insert(tmp_path):
    db = tmp_path / "mem.sqlite"
    st = SQLiteStore(str(db))
    rec = {
        "run_id": "r1",
        "ts": 1700000000000,
        "market": "crypto",
        "symbol": "BTC/USDT",
        "side": "flat",
        "size": 0.0,
        "max_notional_usd": 100.0,
        "confidence": 0.7,
        "reason": ["test"],
        "ttl_s": 10,
    }
    st.insert(rec)
    # simple existence check by reading raw file
    assert db.exists()
