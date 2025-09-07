from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field, field_validator


Market = Literal["crypto", "stocks"]
Side = Literal["buy", "sell", "flat"]


class Decision(BaseModel):
    run_id: str
    ts: int
    market: Market
    symbol: str
    side: Side
    size: float = Field(ge=0)
    max_notional_usd: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    reason: List[str]
    ttl_s: int = Field(ge=0)
    features_used: List[str]
    # v2 extras
    signals_used: List[str] = []
    risk_context: str = ""
    flow_evidence: str = ""
    gates_passed: List[str] = []
    gates_failed: List[str] = []
    outcome: str = "proposed"
    # tracing
    slippage_model: str = ""
    profile: str = ""

    @field_validator("symbol")
    @classmethod
    def non_empty(cls, v: str):
        if not v:
            raise ValueError("symbol required")
        return v

