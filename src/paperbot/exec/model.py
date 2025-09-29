from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional
import uuid

SideOrder = Literal["buy", "sell"]
TypeOrder = Literal["market", "limit"]
Liquidity = Literal["maker", "taker"]


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Order:
    id: str
    ts: int
    symbol: str
    side: SideOrder
    type: TypeOrder
    qty: float
    price: Optional[float]
    strategy: str
    reason: str
    params: Dict[str, Any]
    fee_currency: Optional[str] = None
    fee_amount: float = 0.0


@dataclass
class Fill:
    order_id: str
    ts: int
    symbol: str
    qty: float
    price: float
    fee: float
    fee_currency: str
    fee_usd: float
    liquidity: Liquidity


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float


@dataclass
class Trade:
    ts: int
    symbol: str
    side: str
    qty: float
    price: float
    fee: float
    fee_currency: str
    fee_usd: float
    realized_pnl: float


@dataclass
class LedgerRow:
    ts: int
    symbol: str
    realized_pnl: float
    unrealized_pnl: float
    equity: float
    drawdown: float
