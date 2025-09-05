# ADR-0003: Metrics Naming & Labels

Status: Accepted

## Context
Consistent metric names/labels power Prometheus/Grafana dashboards and tests.

## Decision
- Signals: `signals_emitted_total{strat,side,symbol}`
- Execution: `orders_submitted_total{type,symbol}`, `orders_blocked_total{reason}`, `fills_total{liquidity,symbol}`, `fees_paid_total{symbol}`
- PnL/Equity: `realized_pnl_total{symbol}`, `equity_gauge`
- Risk: `killswitch_trips_total`

## Consequences
- Queries are stable and documented; dashboards remain valid across phases.

## References
- Grafana JSON: `config/grafana/provisioning/dashboards/paperbot.json`
- Metrics code: `src/paperbot/metrics/exec.py`

