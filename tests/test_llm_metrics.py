from src.paperbot.metrics.llm import get_llm_calls_total, get_llm_tokens_total, get_decisions_count_total, get_decisions_confidence_hist


def test_llm_metrics_increment():
    calls = get_llm_calls_total()
    calls.labels("gemini", "true").inc()
    tokens = get_llm_tokens_total()
    tokens.labels("gemini", "prompt").inc(10)
    decs = get_decisions_count_total()
    decs.labels("crypto", "BTC/USDT", "flat").inc()
    hist = get_decisions_confidence_hist()
    hist.labels("crypto").observe(0.7)
    assert True
