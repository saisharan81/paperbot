"""LLM metrics (future; placeholders)."""

from __future__ import annotations

from typing import Optional
from prometheus_client import Counter

_llm_calls: Optional[Counter] = None


def get_llm_calls_total():
    global _llm_calls
    if _llm_calls is None:
        try:
            _llm_calls = Counter("llm_calls_total", "LLM calls", ["provider"])  # placeholder
        except Exception:
            class _NoOp:
                def labels(self, *_, **__):
                    return self
                def inc(self, *_a, **_k):
                    return None
            _llm_calls = _NoOp()  # type: ignore
    return _llm_calls

