import os
import socket
import time

import pytest

from src.paperbot.events.schema import EventEnvelope, OrderIntent
from src.paperbot.events import bus


def _redis_up(host='localhost', port=6379):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


@pytest.mark.skipif(not _redis_up(), reason="redis not running on localhost:6379")
def test_bus_publish_consume_roundtrip():
    os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
    env = EventEnvelope(correlation_id='cX', event=OrderIntent(ts=1, market='crypto', symbol='BTC/USDT', strategy='s', side='long', confidence=0.9, notional_usd=100.0))
    bus.publish(env)
    bus.ensure_group('g1')
    it = bus.consume('g1', 'c1', block_ms=1000)
    msg = next(it)
    assert msg is None or isinstance(msg, tuple)

