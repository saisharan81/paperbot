from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict

try:
    import redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore

from .schema import EventEnvelope
from .metrics import get_events_total, get_orders_rejected_total


STREAM_EVENTS = os.getenv("EVENTS_STREAM", "paperbot.events")
STREAM_DLQ = os.getenv("EVENTS_DLQ", "paperbot.dlq")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

log = logging.getLogger("paperbot.events")


def _get_redis():
    if redis is None:
        raise RuntimeError("redis client not available")
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish(env: EventEnvelope) -> None:
    """Publish an event to Redis Streams and log a single-line JSON for Loki.

    Safe: swallow errors if Redis is not reachable to avoid impacting trading loop.
    """
    # Metrics: total per type
    try:
        get_events_total().labels(env.event.event_type).inc()
        if env.event.event_type == "order_rejected":
            reason = getattr(env.event, "reason", "unknown")
            get_orders_rejected_total().labels(reason).inc()
    except Exception:
        pass

    line = json.dumps({
        "schema_version": env.schema_version,
        "correlation_id": env.correlation_id,
        "sequence": env.sequence,
        "event": env.event.model_dump(),
    }, separators=(",", ":"))
    try:
        r = _get_redis()
        r.xadd(STREAM_EVENTS, {"json": line})
    except Exception:
        try:
            # best-effort DLQ
            r = _get_redis()
            r.xadd(STREAM_DLQ, {"json": line})
        except Exception:
            pass
    # Always log for Loki ingestion
    try:
        log.info(line)
    except Exception:
        pass


def ensure_group(group: str) -> None:
    try:
        r = _get_redis()
        # Create the group if it doesn't exist
        r.xgroup_create(name=STREAM_EVENTS, groupname=group, id="$", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" in str(e):
            return


def consume(group: str, consumer: str, block_ms: int = 15000):
    """Generator yielding (id, json_str) from Redis Stream consumer group.

    Caller is responsible for acknowledging XACK.
    """
    r = _get_redis()
    ensure_group(group)
    while True:
        resp = r.xreadgroup(group, consumer, {STREAM_EVENTS: ">"}, count=100, block=block_ms)
        if not resp:
            yield None
            continue
        # resp is list[(stream, [(id, {field:value}), ...])]
        for _stream, entries in resp:
            for msg_id, fields in entries:
                yield (msg_id, fields.get("json", ""))

