# Paperbot Runbook — Phase 2 (Execution + Risk + Ledger)

## Purpose
Turn strategy signals into paper orders and simulated fills, track PnL and equity in a ledger, and expose execution metrics for observability.

## Prerequisites
- Python path or Docker Compose environment for running the app
- For online mode: valid Binance Spot Testnet API key/secret in repo‑root `.env`, and `config/config.yaml` with `exchange: binance`, `environment: spot-testnet`.
- Optional: `HOLD_METRICS_SECONDS=120` to keep metrics endpoint up for scraping.

## Offline Demo (Deterministic)
- Command:
  - `PYTHONPATH=src OFFLINE_DEMO=1 BINANCE_SPOT_TESTNET_API_KEY=foo BINANCE_SPOT_TESTNET_API_SECRET=bar HOLD_METRICS_SECONDS=120 python -m paperbot.main`
- Expected logs:
  - `strategy signal: { ... }` (1–3 lines)
  - `order submitted: { ... }`
  - `fill: { ... }`
  - `execution demo complete`
- Regex (rough):
  - `^.*order submitted: \{.*\}$`
  - `^.*fill: \{.*\}$`
  - `^.*execution demo complete$`
- Artifacts:
  - `data/trades.parquet`
  - `data/ledger.parquet`
- Metrics (if port binds):
  - `curl -s http://localhost:8000/metrics | egrep 'orders_submitted_total|fills_total|fees_paid_total|equity_gauge|killswitch_trips_total'`

## Online Demo (Testnet via Docker)
- .env (repo root):
  - `BINANCE_SPOT_TESTNET_API_KEY=...`
  - `BINANCE_SPOT_TESTNET_API_SECRET=...`
  - `PROMETHEUS_PORT=8000`
  - `HOLD_METRICS_SECONDS=120`
  - Ensure `OFFLINE_DEMO` is unset or `0`.
- Run:
  - `docker compose up --build`
  - Tail logs: `docker compose logs -f bot`
- What to expect:
  - Phase 0 candle logs, Phase 1.2 strategy logs (data dependent), Phase 2 execution logs if signals fire in the demo window.
- Metrics validation:
  - Prometheus: http://localhost:9090/targets (job `paperbot` UP), http://localhost:9090/graph
  - Grafana (anonymous): http://localhost:3000 → Paperbot Overview
- PromQL examples:
    - `sum by (type,symbol) (orders_submitted_total)`
    - `sum by (liquidity,symbol) (fills_total)`
    - `sum by (symbol) (fees_paid_total)`
    - `equity_gauge`
    - `killswitch_trips_total`

## Pattern Observability (Phase 2.5)
- Env flags:
  - `ENABLE_PATTERN_OBS_DEMO=1` to enable a tiny synthetic emitter
  - `PATTERN_OBS_DEMO_SECONDS=15` interval (seconds)
- Run demo (Compose with Loki optional):
  - `ENABLE_PATTERN_OBS_DEMO=1 PATTERN_OBS_DEMO_SECONDS=10 docker compose up`
- Verify Prometheus metrics:
  - `curl -s http://localhost:8000/metrics | egrep 'pattern_detected_total|pattern_intent_total|pattern_to_intent_latency_seconds_bucket'`
- Grafana panels (Paperbot Overview → row "Patterns"):
  - Detections rate by pattern (5m)
  - Intents rate by pattern/side (5m)
  - Latency P50/P95 (s)
- Loki logs (when running with `-f docker-compose.loki.yml`):
  - `{app="paperbot"} |= "pattern_detected"`
  - `{app="paperbot"} |= "pattern_intent"`
  - Optional JSON filter (if supported): `{app="paperbot"} | json | event == "pattern_detected"`


## Metrics to Validate
- Data/Features (prior phases): `candles_fetched_total`, `features_computed_total`
- Strategies: `signals_emitted_total{strat,side,symbol}`
- Execution:
  - `orders_submitted_total{type,symbol}`
  - `orders_blocked_total{reason}`
  - `fills_total{liquidity,symbol}`
  - `fees_paid_total{symbol}`
  - `realized_pnl_total{symbol}`
  - `equity_gauge`
  - `killswitch_trips_total`

## Artifacts
- `data/trades.parquet`: trade records with qty/price/fee/realized PnL
- `data/ledger.parquet`: equity/drawdown snapshots and PnL totals

## Acceptance Checklist
- [ ] Offline demo logs include ≥1 order and ≥1 fill
- [ ] Offline demo ends with `execution demo complete`
- [ ] Parquet files exist under `data/`
- [ ] Metrics counters increment (when scraped)

## Decision Log workflow
- Author ADRs under `docs/decisions/` using `ADR-0000-template.md`.
- One ADR per significant decision (schema, metrics, risk rules, branching).
- Update the Decision Log index (`docs/decisions/README.md`) in the same PR.

## Troubleshooting
- Metrics port bind fails: run via Docker Compose (Prometheus scrapes internal bot:8000) or set `HOLD_METRICS_SECONDS` and curl quickly.
- No orders/fills online: signals depend on live data and thresholds; extend run duration or use offline deterministic mode.
- Prometheus duplicates in tests: already mitigated by safe metric getters; avoid manual registry reuse across processes.


---

## Phase 2.2 — Execution Refinements

### Purpose
Make fills more realistic and observable via partial fills, exchange-specific fees/rounding, and slippage models.

### Steps (offline deterministic)
- Run: `PYTHONPATH=src OFFLINE_DEMO=1 BINANCE_SPOT_TESTNET_API_KEY=foo BINANCE_SPOT_TESTNET_API_SECRET=bar python -m paperbot.main`
- Expect logs:
  - `order submitted: {…}`
  - `fill: {…}` (repeats across ≥2 bars with the same `order_id`)
  - `execution demo complete`
- Artifacts: `data/trades.parquet`, `data/ledger.parquet`

### Exchange profiles
- Location: `config/exchanges/*.yml` (e.g., `binance_spot.yml`, `alpaca.yml`)
- Fields: `fees.{maker_bps,taker_bps}`, `min_notional`, `tick_size`, `step_size`, `slippage_bps`
- Auto-load based on `(exchange, environment)` in `config/config.yaml`.

### Slippage models
- `fixed_bps` (default): use `slippage_bps` from profile or execution config
- `atr_scaled`: effective bps = base_bps * (atr14/price) * `atr_slip_mult`

### Troubleshooting
- Min notional block: orders below profile `min_notional` are dropped and counted in `orders_blocked_total{reason="min_notional"}`.
- Rounding: prices rounded to `tick_size`; quantities floored to `step_size`.
