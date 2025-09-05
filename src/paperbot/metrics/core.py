"""Core metrics helpers for Paperbot.

Provides a thin wrapper to start the Prometheus HTTP server while tolerating
bind failures (useful in constrained environments and tests).
"""

import logging
from typing import Optional

try:
    from prometheus_client import start_http_server
except Exception:  # pragma: no cover
    start_http_server = None  # type: ignore


def start_server_safe(port: int) -> Optional[int]:
    """Start Prometheus metrics server; return port or None if failed.

    Logs a warning and continues if the port cannot be bound.
    """
    if start_http_server is None:
        logging.warning("Prometheus client not available; metrics disabled")
        return None
    try:
        start_http_server(port)
        logging.info(f"Prometheus metrics server started on :{port}")
        return port
    except OSError as e:
        logging.warning(f"Failed to start Prometheus server on :{port}: {e}")
        return None

