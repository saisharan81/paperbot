# Paperbot Metrics Catalog

This reference highlights the Prometheus metrics that matter for Phase 3 readiness. All metrics are emitted from `src/paperbot/metrics/exec.py` unless noted otherwise.

## Risk & Execution

- `paperbot_killswitch_active{market}` *(Gauge)*
  - Value `1` when the daily loss cap has triggered and the global kill switch is holding the system in a safe state; `0` otherwise.
  - Updated by the Risk Engine (`RiskEngine._set_killswitch`) and mirrored for other modules via `paperbot.risk.killswitch.check_killswitch`.
  - Grafana: Phase 3 dashboard row "Risk" → add stat panel targeting `paperbot_killswitch_active` to spot stuck kill switches.
- `killswitch_trips_total` *(Counter)*
  - Incremented the first time the loss cap is breached each session.
  - Use together with `paperbot_killswitch_active` to distinguish transient trips from persistent lockouts.
- `orders_blocked_total{reason="killswitch"}` *(Counter)*
  - Counts attempted orders rejected because the kill switch is active.
- `fees_paid_usd_total{market,symbol}` *(Counter)*
  - Emits USD-normalised fees for every fill; the Execution Simulator now converts non-USD fee currencies via `PriceOracle`.

## LLM Guardrails

- `llm_guard_denied_total{reason}` *(Counter — TODO)*
  - Placeholder for a future counter; until implemented, monitor Loki logs for `{"event": "llm_guard_denied"}` entries triggered by `GuardrailError`.

## Equity & Performance

- `account_equity_usd{market}` *(Gauge)*
  - Snapshot of ledger equity by market. Updated by `set_equity_gauges`.
- `mtm_tick_total{market}` *(Counter)*
  - Count of MTM refreshes emitted by the periodic equity tick.

## Pattern Observability (Phase 2.5)

- `pattern_detected_total{market,symbol,pattern}` *(Counter)*
- `pattern_intent_total{market,pattern,side}` *(Counter)*
- `pattern_to_intent_latency_seconds_bucket` *(Histogram)*

## Verification Tips

1. `curl -s http://localhost:8000/metrics | egrep 'paperbot_killswitch_active|killswitch_trips_total|fees_paid_usd_total'`
2. Grafana quick stats:
   - Panel A: `max(paperbot_killswitch_active)` — should be `0` under normal ops.
   - Panel B: `sum(increase(killswitch_trips_total[1h]))` — alerts if >0 during trading session.
3. During guardrail tests, tail Loki for the structured denial log: `{event="llm_guard_denied"}`.
