from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
import logging
import time

try:
    from ..metrics.exec import _safe_counter  # type: ignore
except Exception:  # pragma: no cover
    _safe_counter = None


def _get_append_counters():
    if _safe_counter is None:  # pragma: no cover
        class _NoOp:
            def labels(self, *a, **k):
                return self
            def inc(self, *a, **k):
                return None
        return _NoOp(), _NoOp()
    app = _safe_counter("decision_log_appends_total", "Decision records appended", ["market"])
    err = _safe_counter("decision_log_errors_total", "Decision log errors", ["reason", "market"])
    return app, err


REQUIRED_KEYS = {
    "ts", "symbol", "market", "strategy", "action", "confidence",
    "features_used", "signals_used", "risk_context", "flow_evidence",
    "gates_passed", "gates_failed", "outcome",
}


def validate_record(rec: Dict[str, Any]) -> List[str]:
    missing = [k for k in REQUIRED_KEYS if k not in rec]
    return missing


def append_jsonl(path: str, rec: Dict[str, Any]) -> None:
    market = str(rec.get("market", "unknown"))
    app, err = _get_append_counters()
    missing = validate_record(rec)
    if missing:
        err.labels("missing_fields", market).inc()
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        app.labels(market).inc()
    except Exception:
        err.labels("io_error", market).inc()


def log_pattern_event(
    event_type: str,
    market: str,
    symbol: str,
    pattern: str,
    rsi: Optional[float] = None,
    side: Optional[str] = None,
    ts: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a structured JSON log line for pattern observability.

    Keys: event, market, symbol, pattern, rsi, side, ts, severity, component, schema_version
    """
    try:
        logger = logging.getLogger("paperbot.strategy")
        payload: Dict[str, Any] = {
            "event": str(event_type),
            "market": str(market),
            "symbol": str(symbol),
            "pattern": str(pattern),
            "rsi": float(rsi) if rsi is not None else None,
            "side": str(side) if side is not None else None,
            "ts": int(ts if ts is not None else int(time.time() * 1000)),
            "severity": "INFO",
            "component": "strategy",
            "schema_version": "v1",
        }
        if extra:
            payload["extra"] = extra
        logger.info(json.dumps(payload, separators=(",", ":")))
    except Exception:
        # Logging must never throw
        pass
