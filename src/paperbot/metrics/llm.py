"""LLM metrics for advisory.

Counters:
- llm_calls_total{provider,ok}
- llm_tokens_total{provider,type="prompt|output"}
- decisions_count_total{market,symbol,side}

Histogram:
- decisions_confidence_bucket{market}
"""

from __future__ import annotations

from typing import Optional
from prometheus_client import Counter, Histogram

_llm_calls: Optional[Counter] = None
_llm_tokens: Optional[Counter] = None
_decisions_count: Optional[Counter] = None
_decisions_conf_hist: Optional[Histogram] = None


def get_llm_calls_total():
    global _llm_calls
    if _llm_calls is None:
        try:
            _llm_calls = Counter("llm_calls_total", "LLM calls", ["provider", "ok"])  # ok=true|false
        except Exception:
            class _NoOp:
                def labels(self, *_, **__):
                    return self
                def inc(self, *_a, **_k):
                    return None
            _llm_calls = _NoOp()  # type: ignore
    return _llm_calls


def get_llm_tokens_total():
    global _llm_tokens
    if _llm_tokens is None:
        try:
            _llm_tokens = Counter("llm_tokens_total", "LLM tokens", ["provider", "type"])  # type: prompt|output
        except Exception:
            class _NoOp:
                def labels(self, *_, **__):
                    return self
                def inc(self, *_a, **_k):
                    return None
            _llm_tokens = _NoOp()  # type: ignore
    return _llm_tokens


def get_decisions_count_total():
    global _decisions_count
    if _decisions_count is None:
        try:
            _decisions_count = Counter("decisions_count_total", "LLM decisions count", ["market", "symbol", "side"])
        except Exception:
            class _NoOp:
                def labels(self, *_, **__):
                    return self
                def inc(self, *_a, **_k):
                    return None
            _decisions_count = _NoOp()  # type: ignore
    return _decisions_count


def get_decisions_confidence_hist():
    global _decisions_conf_hist
    if _decisions_conf_hist is None:
        try:
            _decisions_conf_hist = Histogram("decisions_confidence_bucket", "Decision confidences", ["market"], buckets=[0.0,0.25,0.5,0.6,0.7,0.8,0.9,1.0])
        except Exception:
            class _NoOp:
                def labels(self, *_, **__):
                    return self
                def observe(self, *_a, **_k):
                    return None
            _decisions_conf_hist = _NoOp()  # type: ignore
    return _decisions_conf_hist
