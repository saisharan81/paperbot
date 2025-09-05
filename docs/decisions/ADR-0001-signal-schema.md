# ADR-0001: Signal Schema

Status: Accepted

## Context
Strategies need a normalized, typed signal format to decouple signal generation from execution and risk.

## Decision
Use a `Signal` dataclass with fields: `ts:int`, `symbol:str`, `strategy:str`, `side:Literal["long","short","flat"]`, `strength:float(0..1)`, `reason:str`, `params:Dict[str,Any]`.

## Consequences
- Enables pluggable strategies and consistent logging/metrics.
- Backward-compatible extensibility via `params`.

## References
- `src/paperbot/strategies/base.py`
