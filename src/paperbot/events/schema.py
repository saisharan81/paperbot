from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# ---- Base + envelope ----

class BaseEvent(BaseModel):
    event_type: str
    ts: int
    run_id: str = "r1"
    market: str
    symbol: str
    strategy: Optional[str] = None
    side: Optional[str] = None  # long|short|flat or buy|sell
    confidence: Optional[float] = None
    tags: List[str] = []


class EventEnvelope(BaseModel):
    schema_version: str = "v1"
    correlation_id: str
    sequence: int = 0
    event: BaseEvent


# ---- Event types ----

class SignalDetected(BaseEvent):
    event_type: Literal["signal_detected"] = "signal_detected"
    pattern_id: Optional[str] = None
    threshold: Optional[float] = None


class PatternBreak(BaseEvent):
    event_type: Literal["pattern_break"] = "pattern_break"
    breakout_level: Optional[float] = None
    strength: Optional[float] = None


class OrderIntent(BaseEvent):
    event_type: Literal["order_intent"] = "order_intent"
    notional_usd: float = 0.0


class OrderSubmitted(BaseEvent):
    event_type: Literal["order_submitted"] = "order_submitted"
    order_id: str
    qty: float
    price: Optional[float] = None


class OrderPartiallyFilled(BaseEvent):
    event_type: Literal["order_partially_filled"] = "order_partially_filled"
    order_id: str
    qty: float
    price: float
    fee_usd: float = 0.0
    slippage_bps: Optional[float] = None


class OrderFilled(BaseEvent):
    event_type: Literal["order_filled"] = "order_filled"
    order_id: str
    qty: float
    avg_price: float
    fee_usd: float = 0.0


class OrderCanceled(BaseEvent):
    event_type: Literal["order_canceled"] = "order_canceled"
    order_id: str
    reason: str


class OrderRejected(BaseEvent):
    event_type: Literal["order_rejected"] = "order_rejected"
    reason: str


class RiskBlocked(BaseEvent):
    event_type: Literal["risk_blocked"] = "risk_blocked"
    reason: str


class DailyLossLimitBreach(BaseEvent):
    event_type: Literal["daily_loss_limit_breach"] = "daily_loss_limit_breach"
    equity: float
    equity_start: float
    pct_drop: float
    flags: Dict[str, bool] = Field(default_factory=dict)


class DayHighlight(BaseEvent):
    event_type: Literal["day_highlight"] = "day_highlight"
    summary: str


class Heartbeat(BaseEvent):
    event_type: Literal["heartbeat"] = "heartbeat"
    service: str = "bot"


AnyEvent = Union[
    SignalDetected,
    PatternBreak,
    OrderIntent,
    OrderSubmitted,
    OrderPartiallyFilled,
    OrderFilled,
    OrderCanceled,
    OrderRejected,
    RiskBlocked,
    DailyLossLimitBreach,
    DayHighlight,
    Heartbeat,
]
