# ADR-0007: Partial Fills

Status: Accepted

## Context
Full-bar fills are unrealistic; we need controlled partials without complex order book simulation.

## Decision
- Use `liquidity_fraction` ∈ (0,1] to fill a fraction of remaining qty per bar (default 0.25).
- Track remaining by `order_id` across bars; sign qty by side (+buy, -sell).
- Allow per-symbol overrides in config later (future improvement).

## Consequences
- Deterministic, testable partial fills aligned to bar volume intuition, without heavy market depth logic.

## References
- `src/paperbot/exec/simulator.py`
