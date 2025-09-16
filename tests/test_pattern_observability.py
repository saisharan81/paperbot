import logging
from prometheus_client import REGISTRY

from src.paperbot.strategies.runner import record_pattern_detected, record_pattern_intent


def test_record_pattern_helpers_emit_metrics_and_logs(caplog, monkeypatch):
    caplog.set_level(logging.INFO)

    market = "crypto"
    symbol = "BTC/USDT"
    pattern = "bullish_engulfing"
    side = "long"
    ts_det = 1_000  # ms
    ts_int = 1_600  # ms -> 0.6s latency

    record_pattern_detected(market, symbol, pattern, rsi=33.0, ts=ts_det)
    record_pattern_intent(market, symbol, pattern, side=side, ts_detected=ts_det, ts_intent=ts_int)

    # Logs contain JSON with event types
    log_out = "\n".join([r.message for r in caplog.records])
    assert '"event":"pattern_detected"' in log_out
    assert '"event":"pattern_intent"' in log_out

    # Counters incremented
    v_det = REGISTRY.get_sample_value(
        "pattern_detected_total", {"market": market, "symbol": symbol, "pattern": pattern}
    )
    assert v_det is not None and v_det >= 1.0

    v_int = REGISTRY.get_sample_value(
        "pattern_intent_total", {"market": market, "pattern": pattern, "side": side}
    )
    assert v_int is not None and v_int >= 1.0

    # Histogram observed with positive value
    v_cnt = REGISTRY.get_sample_value("pattern_to_intent_latency_seconds_count")
    v_sum = REGISTRY.get_sample_value("pattern_to_intent_latency_seconds_sum")
    assert v_cnt is not None and v_cnt >= 1.0
    assert v_sum is not None and v_sum > 0.0

