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

## Troubleshooting
- Metrics port bind fails: run via Docker Compose (Prometheus scrapes internal bot:8000) or set `HOLD_METRICS_SECONDS` and curl quickly.
- No orders/fills online: signals depend on live data and thresholds; extend run duration or use offline deterministic mode.
- Prometheus duplicates in tests: already mitigated by safe metric getters; avoid manual registry reuse across processes.
