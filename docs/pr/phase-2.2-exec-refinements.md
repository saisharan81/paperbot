# Phase 2.2: Execution Refinements (partial fills, profiles, slippage, docs)

Summary
- Partial fills per bar via `liquidity_fraction` (default 0.25), tracked by order_id.
- Exchange execution profiles: `config/exchanges/binance_spot.yml` (fees, tick/step, min_notional, slippage_bps).
- Slippage models: `fixed_bps` (default) and `atr_scaled` (optional with `atr_slip_mult`).
- Metrics & Grafana: orders submitted rate (5m), fills rate by liquidity (5m), fees (1h increase), equity gauge.
- Docs: README Phase Log entry; RUNBOOK section for Phase 2.2; ADR-0006 and ADR-0007 added.

Validation
- Tests: `PYTHONPATH=src pytest -q` → 42 passed
- Offline demo: `APP_TRACK=crypto OFFLINE_DEMO=1 PYTHONPATH=src python -m paperbot.main`
  - Logs include `order submitted: {…}`
  - ≥2 `fill: {…}` sharing the same `order_id`
  - Final EXACT: `execution demo complete`
- Dashboard: panels present for orders/fills/fees/equity; signals panels unchanged.

ADRs
- docs/decisions/ADR-0006-execution-profiles.md
- docs/decisions/ADR-0007-partial-fills.md

Merge checklist
- [ ] 42 tests pass (`PYTHONPATH=src pytest -q`)
- [ ] Offline demo shows ≥2 partial fills for same order_id and **execution demo complete**
- [ ] Grafana panels render (orders rate, fills rate by liquidity, fees (1h), equity gauge)
- [ ] RUNBOOK + ADR index updated to include Phase 2.2
- [ ] Branch up to date with main
