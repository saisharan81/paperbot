# Paperbot Roadmap

This roadmap outlines phased development, acceptance gates, and monetization.

## Phases

- Phase 0 — Bootstrap & Candle Demo
  - Acceptance:
    - Logs exactly 10 normalized candle lines and then "candle demo complete".
    - Runs via `python -m paperbot.main` or Docker Compose.

- Phase 1.1 — Baseline Features
  - Indicators: RSI(14), ATR(14), Session VWAP, Z-score to VWAP(50), Realized Vol(30 bars).
  - Acceptance:
    - Unit tests cover and pass for these fields.
    - Feature row includes the five baseline fields.

- Phase 1.1.1 — Optional Features (config-gated)
  - SMA/EMA, MACD, Bollinger, OBV, Keltner, rolling skew/kurtosis, hour_of_day.
  - Acceptance:
    - Toggles in `config/config.yaml` control computation.
    - Unit tests pass for each helper and integration checks.

- Phase 1.2 — Strategies: Mean Reversion + Momentum
  - Define Strategy base interface; implement MR & Momentum with simple parameters.
  - Acceptance:
    - Deterministic unit tests produce expected signals on synthetic data.
    - Demo prints last signal snapshot.

- Phase 2 — Risk Engine + Execution Simulator
  - Centralized limits (exposure caps, daily loss, kill-switch) + paper fills.
  - Acceptance:
    - Limits enforced in unit tests; fills recorded with fees/slippage.

- Phase 3 — Orchestration, Metrics, Reports
  - Long-running loop orchestration; Prometheus metrics; EOD HTML/CSV reports.
  - Acceptance:
    - `/metrics` live and charts generated under `reports/`.

- Phase 4 — Backtesting
  - Vectorized backtester and summary metrics.
  - Acceptance:
    - Reproducible backtest output with summary CSV/HTML.

- Phase 5 — Allocations & Daily Risk Discipline
  - Allocation rules, auto-downsize, and daily stop conditions.

- Phase 6 — Paper Burn-in
  - Multi-week paper run with positive drift and low drawdown.

- Phase 7 — Extensions & SaaS
  - Pairs trading, basis, smarter execution; productization.

## Go / No-Go (Paper → Live)

- PnL ≥ 0 after fees for rolling 30 days.
- Sharpe ≥ 1.0 (daily), Max Drawdown ≤ 5%.
- Strategy/resilience tests pass (network, exchange hiccups, restarts).
- Monitoring and alerting configured; kill-switch verified.

## How We Make Money

- Short term (Phases 3–6): small live pilot capital targeting $100–200/day with strict risk.
- Medium term (Phase 7+):
  - SaaS subscriptions (signals, dashboards, APIs).
  - B2B licensing and integrations.
  - Managed access and, later, performance fees where appropriate.

