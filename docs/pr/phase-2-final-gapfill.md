# Phase 2 Gap-Fill: extra indicators, stocks paper-only, metrics tune-up

## Summary
- Indicators: Added CCI(20), StochRSI(14,3,3), MFI(14) to baseline features with guards.
- Execution: Added slippage model `random_bps` (uniform jitter; default range [0,3] bps) in addition to `fixed_bps` and `atr_scaled`.
- Markets: Added stocks paper-only profile (AAPL, TSLA) with tick/step/min_notional/fees/slippage defaults; extended loader to resolve `exchange=stocks, environment=paper`.
- Labels: Introduced `{market}` label alongside existing labels; kept legacy metrics for compatibility.
- Dashboards: Provisioned `paperbot-crypto.json` and `paperbot-stocks.json` with `{market="..."}` filters; kept layout consistent and signals panels unchanged.
- Decision Log v2: Enriched JSONL records (market, strategy, side, size, price, slippage_model, profile, features_used, signals_used, risk_context, flow_evidence, gates_passed/failed, outcome).
- Metrics tune-up: Added `account_equity_usd` (Gauge) and `fees_paid_usd_total` (Counter) alongside legacy names; added histograms for slippage_bps and order→fill latency; added `paperbot_build_info`.

## Validation
- Tests: `PYTHONPATH=src pytest -q` → 44 passed
- Offline demo (deterministic): `APP_TRACK=crypto OFFLINE_DEMO=1 PYTHONPATH=src python -m paperbot.main`
  - Logs include `order submitted: {...}`
  - ≥2 `fill: {...}` sharing the same `order_id` (partial fills)
  - Final EXACT: `execution demo complete`
  - Decision Log v2 JSONL appended under `data/decisions/phase2.jsonl`
- Dashboards:
  - `config/grafana/provisioning/dashboards/paperbot-crypto.json`
  - `config/grafana/provisioning/dashboards/paperbot-stocks.json`

## Metric migration note
- New names added: `account_equity_usd`, `fees_paid_usd_total`; legacy names still emitted for this release to avoid breakage.
- Histograms added: `slippage_bps_bucket`, `order_fill_latency_seconds_bucket` (+ _sum/_count) with `{market}` labels.
- Build info: `paperbot_build_info{version,git_sha,market} 1`.

## Links
- Runbook: docs/RUNBOOK.md
- Decision Log index: docs/decisions/README.md
