# ADR-0002: Risk Engine Guardrails

Status: Accepted

## Context
We need basic guardrails to prevent runaway losses and oversizing while staying simple for MVP.

## Decision
- Daily loss cap (killswitch): trip when equity ≤ start*(1-daily_loss_cap_pct); block new orders.
- Sizing: qty = (equity * risk_frac) / max(atr14 * atr_stop_mult, 1e-9).
- Per-symbol value cap: |qty*price|/equity ≤ max_position_value_per_symbol.
- Order type: market for MVP demo; limit later.

## Consequences
- Simple, transparent rules; easy to test.
- ATR dependence may under/oversize in edge cases; refined later.

## References
- `src/paperbot/risk/engine.py`
