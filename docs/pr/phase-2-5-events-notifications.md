# Phase 2.5: Risk Daily Loss Limit Notifications

## Summary
Introduce explicit daily-loss stop handling so the risk engine can halt trading for
the session without engaging the global kill switch. The branch adds shared halt
flags, a `DailyLossLimitBreach` event, richer blocking reasons, and pytest
coverage to guard the behaviour.

## Changes
- Risk engine (`src/paperbot/risk/engine.py`)
  - Tracks `DAILY_STOP` vs `KILL_SWITCH` flags and refreshes them on every
    `approve` call.
  - Emits a `DailyLossLimitBreach` event with equity, drop %, and flag snapshot
    when equity falls beyond the configured daily cap.
  - Blocks subsequent orders with `reason="daily_stop"` while the global kill
    switch remains clear.
- Halt flag registry (`src/paperbot/risk/halt_flags.py`)
  - Lightweight module storing halt flags, with helpers for `set_flag`,
    `snapshot`, `reset_flags`, and `any_active`.
- Event schema (`src/paperbot/events/schema.py`)
  - Adds the `DailyLossLimitBreach` payload to the shared event model.
- Tests
  - New `tests/test_daily_loss_limit.py` simulates a 5% drawdown, verifies the
    breach event payload, and asserts only `DAILY_STOP` is true.
  - Existing risk engine tests reset the halt registry and expect the
    `daily_stop` reason after losses.

## How to Run
- Install deps: `poetry install --with dev`
- Targeted tests: `poetry run python -m pytest tests/test_daily_loss_limit.py tests/test_risk_engine.py`
- Full suite (optional): `poetry run python -m pytest`
- During manual experiments, watch the Redis stream
  (`paperbot.events`) or bot logs for `event_type="daily_loss_limit_breach"` and
  confirm `paperbot_killswitch_active{market="crypto"}` remains `0` while
  `DAILY_STOP` is true.

## Observability Notes
- Breach events are published through the existing event bus and can be tailed
  alongside other risk notifications.
- Metrics continue to use the Prometheus kill switch gauge; no new collectors
  were introduced here.

## Compatibility
- Additive update; default behaviour stays untouched until equity drops below
  the daily cap.
- Global kill switch semantics remain unchanged and still report through
  `paperbot_killswitch_active`.

## Checklist
- [x] Daily stop logic blocks orders without toggling the global kill switch
- [x] `DailyLossLimitBreach` event emitted with flag snapshot
- [x] Targeted pytest coverage passes
- [x] Docs/PR notes updated to describe the change set

## Links
- Risk engine: `src/paperbot/risk/engine.py`
- Halt flags: `src/paperbot/risk/halt_flags.py`
- Tests: `tests/test_daily_loss_limit.py`
