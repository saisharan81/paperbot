# Phase 2.5: Pattern Observability (Events + Notifications)

## Summary
Introduce lightweight, strategy-agnostic observability for candlestick pattern events. Adds Prometheus counters/histogram, Loki-structured logs, Grafana panels, a simple alert, and an ENV-gated synthetic emitter to validate locally without depending on unmerged strategy code.

## Changes
- Metrics (src/paperbot/metrics/exec.py)
  - Counter: `pattern_detected_total{market,symbol,pattern}`
  - Counter: `pattern_intent_total{market,pattern,side}`
  - Histogram: `pattern_to_intent_latency_seconds` with buckets `[0.5,1,2,5,10,30,60]`
  - Helpers: `inc_pattern_detected`, `inc_pattern_intent`, `observe_pattern_to_intent_latency`
- Structured logs (src/paperbot/logs/decision_log.py)
  - `log_pattern_event(event_type, market, symbol, pattern, rsi=None, side=None, ts=None, extra=None)`
  - Emits JSON for Loki with keys: `event`, `market`, `symbol`, `pattern`, `rsi`, `side`, `ts`, `severity`, `component`, `schema_version`.
- Strategy wiring points (src/paperbot/strategies/runner.py)
  - `record_pattern_detected(...)` and `record_pattern_intent(...)` (no dependency on specific strategies)
- Demo emitter (src/paperbot/main.py)
  - ENV-gated: `ENABLE_PATTERN_OBS_DEMO=1`; interval `PATTERN_OBS_DEMO_SECONDS` (default 15)
  - Emits BTC/USDT `pattern_detected` (bullish_engulfing, rsi=33) then `pattern_intent` (long) after ~0.5s
- Grafana (config/grafana/provisioning/dashboards/paperbot.json)
  - New row “Patterns”: detections rate, intents rate, latency P50/P95, Loki logs panels
- Alert (config/grafana/provisioning/alerting/patterns-min-activity.yml)
  - If `sum(increase(pattern_detected_total[30m])) == 0` for 45m → “No pattern detections (30m)”
  - Datasource UID: `PBFA97CFB590B2093`
- Docs
  - ADR: `docs/decisions/ADR-0012-pattern-observability.md`
  - Runbook: new section “Pattern Observability (Phase 2.5)”
  - README: features bullet linking to ADR + Runbook
  - .env example: `src/paperbot/.env.example`
- Tooling
  - Smoke script: `scripts/smoke_pattern_obs.sh`
- Tests
  - `tests/test_pattern_observability.py` covering counters/logs/histogram

## How to Run
- Compose (Prometheus+Grafana):
  - `ENABLE_PATTERN_OBS_DEMO=1 PATTERN_OBS_DEMO_SECONDS=10 docker compose up`
- Validate metrics:
  - `curl -s http://localhost:8000/metrics | egrep 'pattern_detected_total|pattern_intent_total|pattern_to_intent_latency_seconds_bucket'`
- Grafana → Paperbot Overview → Patterns row
  - P50: `histogram_quantile(0.5, sum by (le) (rate(pattern_to_intent_latency_seconds_bucket[5m])))`
  - P95: `histogram_quantile(0.95, sum by (le) (rate(pattern_to_intent_latency_seconds_bucket[5m])))`
- Loki (optional overlay `-f docker-compose.loki.yml`):
  - `{app="paperbot"} |= "pattern_detected"`
  - `{app="paperbot"} |= "pattern_intent"`
  - Note: If you prefer JSON filtering and your Loki supports it, use
    `{app="paperbot"} | json | event == "pattern_detected"` (and `pattern_intent`).

## Compatibility
- Additive; no changes to existing strategy/execution flows.
- Metrics use safe getters; tolerant in constrained envs and tests.

## Checklist
- [x] Metrics compile and export
- [x] Logs JSON parse in Grafana Loki
- [x] Panels present under “Patterns”
- [x] Alert provisioned
- [x] Smoke and unit tests present

## Links
- ADR: `docs/decisions/ADR-0012-pattern-observability.md`
- Runbook: `docs/RUNBOOK.md#pattern-observability-phase-25`
