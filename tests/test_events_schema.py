from src.paperbot.events.schema import (
    EventEnvelope, OrderIntent, OrderSubmitted, OrderPartiallyFilled, OrderFilled,
)


def test_event_envelope_roundtrip():
    intent = OrderIntent(ts=1, market="crypto", symbol="BTC/USDT", strategy="s", side="long", confidence=0.9, notional_usd=100.0)
    env = EventEnvelope(correlation_id="c1", event=intent)
    js = env.model_dump_json()
    assert 'order_intent' in js


def test_order_events_models():
    sub = OrderSubmitted(ts=2, market="crypto", symbol="BTC/USDT", strategy="s", side="buy", order_id="o1", qty=1.0)
    pf = OrderPartiallyFilled(ts=3, market="crypto", symbol="BTC/USDT", strategy="s", side="buy", order_id="o1", qty=0.5, price=100.0, fee_usd=0.01)
    full = OrderFilled(ts=4, market="crypto", symbol="BTC/USDT", strategy="s", side="buy", order_id="o1", qty=1.0, avg_price=100.05, fee_usd=0.02)
    assert sub.order_id == pf.order_id == full.order_id == "o1"

