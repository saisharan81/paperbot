# ADR-0004: Offline Determinism

Status: Accepted

## Context
CI/sandboxes may block network or metrics ports. We still need reliable acceptance.

## Decision
- `OFFLINE_DEMO=1` runs a deterministic path that emits:
  - `candle:` lines (Phase 0)
  - `strategy signal:` lines (≤3)
  - `execution demo complete` (Phase 2)
- Metrics server failures log WARN and do not abort the run.

## Consequences
- Demos/tests are reliable without external dependencies.

## References
- `src/paperbot/main.py`
