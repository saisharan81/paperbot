from __future__ import annotations

import os
import json
import asyncio
from typing import AsyncGenerator, Optional, List
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM = os.getenv("EVENTS_STREAM", "paperbot.events")
GROUP = os.getenv("SSE_GROUP", "sse_gateway")

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore

app = FastAPI(title="Paperbot SSE Gateway")


async def ensure_group(r):
    try:
        await r.xgroup_create(name=STREAM, groupname=GROUP, id="$", mkstream=True)
    except Exception as e:  # BUSYGROUP
        if "BUSYGROUP" in str(e):
            return


def _match_filters(js: str, types: Optional[List[str]], symbols: Optional[List[str]]) -> bool:
    try:
        data = json.loads(js)
        ev = data.get("event", {})
        t = ev.get("event_type")
        s = ev.get("symbol")
        ok_t = True if not types else t in types
        ok_s = True if not symbols else s in symbols
        return ok_t and ok_s
    except Exception:
        return False


async def event_stream(types: Optional[List[str]], symbols: Optional[List[str]]) -> AsyncGenerator[bytes, None]:
    if aioredis is None:  # pragma: no cover
        yield b": redis async client missing\n\n"
        return
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    await ensure_group(r)
    consumer = os.getenv("SSE_CONSUMER", os.uname().nodename)
    heartbeat = 0
    try:
        while True:
            resp = await r.xreadgroup(GROUP, consumer, {STREAM: ">"}, count=100, block=15000)
            if resp:
                for _stream, entries in resp:
                    for msg_id, fields in entries:
                        js = fields.get("json", "")
                        if _match_filters(js, types, symbols):
                            yield f"event: event\ndata: {js}\n\n".encode()
                        await r.xack(STREAM, GROUP, msg_id)
            else:
                heartbeat += 1
                if heartbeat % 1 == 0:
                    yield b": keep-alive\n\n"
    finally:
        await r.aclose()


@app.get("/events")
async def sse(request: Request, types: Optional[str] = None, symbols: Optional[str] = None):
    ty = types.split(",") if types else None
    sy = symbols.split(",") if symbols else None
    generator = event_stream(ty, sy)
    return StreamingResponse(generator, media_type="text/event-stream")

