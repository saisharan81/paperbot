import json

import pytest

from src.paperbot.llm.guards import GuardrailError, output_validate


def make_decision(size: float, max_notional: float = 200.0):
    return {
        "run_id": "r1",
        "ts": 1,
        "market": "crypto",
        "symbol": "BTC/USDT",
        "side": "buy",
        "size": size,
        "max_notional_usd": max_notional,
        "confidence": 0.9,
        "reason": ["test"],
        "ttl_s": 30,
        "features_used": [],
        "signals_used": [],
        "risk_context": "demo",
        "flow_evidence": "unit-test",
        "gates_passed": [],
        "gates_failed": [],
        "outcome": "proposed",
    }


def test_output_validate_allows_within_notional():
    decision = make_decision(size=50.0, max_notional=200.0)
    validated = output_validate(
        decision,
        ["BTC/USDT"],
        "crypto",
        "BTC/USDT",
        0.6,
        200.0,
    )
    assert validated.max_notional_usd == 200.0


def test_output_validate_notional_guard_blocks(caplog):
    decision = make_decision(size=250.0, max_notional=200.0)
    with caplog.at_level("ERROR"):
        with pytest.raises(GuardrailError):
            output_validate(
                decision,
                ["BTC/USDT"],
                "crypto",
                "BTC/USDT",
                0.6,
                200.0,
            )
    log_messages = [json.loads(rec.message) for rec in caplog.records if rec.levelname == "ERROR"]
    assert any(msg.get("event") == "llm_guard_denied" for msg in log_messages)


def test_output_validate_converts_size_to_notional(caplog):
    decision = make_decision(size=2.5, max_notional=200.0)
    decision["quote_price"] = 120.0
    with caplog.at_level("ERROR"):
        with pytest.raises(GuardrailError):
            output_validate(
                decision,
                ["BTC/USDT"],
                "crypto",
                "BTC/USDT",
                0.6,
                200.0,
            )
    entries = [json.loads(rec.message) for rec in caplog.records if rec.levelname == "ERROR"]
    assert entries, "expected guardrail log entry"
    payload = entries[-1]
    assert payload.get("price_source") == "quote_price"
    assert pytest.approx(payload.get("notional_usd"), rel=1e-6) == 300.0
