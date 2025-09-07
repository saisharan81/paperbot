from prometheus_client import REGISTRY

from src.paperbot.metrics.exec import get_fees_paid_usd_total, set_equity_gauges


def _sample(metric: str, labels: dict) -> float:
    val = REGISTRY.get_sample_value(metric, labels)
    return 0.0 if val is None else float(val)


def test_fees_paid_usd_total_sum_of_two_increments():
    fees = get_fees_paid_usd_total()
    labels = {"market": "crypto", "symbol": "TEST/USDT"}
    before = _sample("fees_paid_usd_total", labels)
    fees.labels(**labels).inc(1.25)
    fees.labels(**labels).inc(0.75)
    after = _sample("fees_paid_usd_total", labels)
    assert round(after - before, 6) == round(2.0, 6)


def test_account_equity_usd_set_twice():
    labels = {"market": "crypto"}
    # Set once, verify value
    set_equity_gauges({"crypto": 10_000.0})
    first = _sample("account_equity_usd", labels)
    assert first == 10_000.0
    # Set again, verify updated value
    set_equity_gauges({"crypto": 10_250.5})
    second = _sample("account_equity_usd", labels)
    assert second == 10_250.5

