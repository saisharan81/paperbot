# ADR-0012: Pattern Observability (Phase 2.5)

Context
- Add lightweight, strategy-agnostic observability for candlestick pattern events.
- Avoid dependency on unmerged strategy code; provide an ENV-gated synthetic emitter.

Decisions
- Counters and histogram in `src/paperbot/metrics/exec.py`:
  - Counter: `pattern_detected_total{market,symbol,pattern}`
  - Counter: `pattern_intent_total{market,pattern,side}`
  - Histogram: `pattern_to_intent_latency_seconds` with buckets `[0.5,1,2,5,10,30,60]`
- Structured logs (Loki) via helper in `src/paperbot/logs/decision_log.py`:
  - `log_pattern_event(event, market, symbol, pattern, rsi=None, side=None, ts=None, extra=None)`
  - JSON keys: `event` ("pattern_detected"|"pattern_intent"), `market`, `symbol`, `pattern`, `rsi`, `side`, `ts`, `severity`, `component="strategy"`, `schema_version="v1"`.
- Thin wiring helpers in `src/paperbot/strategies/runner.py`:
  - `record_pattern_detected(market, symbol, pattern, rsi, ts)`
  - `record_pattern_intent(market, symbol, pattern, side, ts_detected, ts_intent)`
- Synthetic demo emitter (env-gated) in `src/paperbot/main.py`:
  - Enabled when `ENABLE_PATTERN_OBS_DEMO=1`.
  - Emits BTC/USDT bullish_engulfing every `PATTERN_OBS_DEMO_SECONDS` (default 15s)
  - Emits intent ~0.5s later; records latency.
- Grafana: a new row “Patterns” with timeseries/stat/quantile panels and Loki log panels.
- Alert: `config/grafana/provisioning/alerting/patterns-min-activity.yml` alerts if zero detections for 30m (for 45m).

Env Flags
- `ENABLE_PATTERN_OBS_DEMO` (default `0`) — enable synthetic emitter
- `PATTERN_OBS_DEMO_SECONDS` (default `15`) — emit interval in seconds

Sample Queries
- Prometheus (rate):
  - `sum by (pattern) (rate(pattern_detected_total[5m]))`
  - `sum by (pattern,side) (rate(pattern_intent_total[5m]))`
- Prometheus (latency):
  - `histogram_quantile(0.5, sum by (le) (rate(pattern_to_intent_latency_seconds_bucket[5m])))`
  - `histogram_quantile(0.95, sum by (le) (rate(pattern_to_intent_latency_seconds_bucket[5m])))`
- Loki (logs):
  - `{app="paperbot"} | json | event="pattern_detected"`
  - `{app="paperbot"} | json | event="pattern_intent"`

Consequences
- Minimal, backwards-compatible additions; no impact to trading logic.
- Ready-made wiring points for real strategies without new dependencies.
