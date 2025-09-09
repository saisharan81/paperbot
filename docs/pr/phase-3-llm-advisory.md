# Phase 3.0: LLM Advisory, Metrics, and Grafana Provisioning

## Summary
- LLM advisory scaffolding enabled: lightweight client/router, providers (Gemini, Local OpenAI), guards and contracts; offline demo integrates advisory flow.
- New Prometheus metrics wired for dashboards:
  - `fees_paid_usd_total{market,symbol}` Counter — increments on every simulated fill.
  - `account_equity_usd{market}` Gauge — emitted at least twice per offline run for plotting.
- Grafana provisioning fixed and hardened:
  - Dashboards `paperbot-crypto.json` and `paperbot-stocks.json` have titles, stable UIDs, required metadata; panels unchanged.
  - File provider `dashboards.yml` points to `/etc/grafana/provisioning/dashboards`; Prometheus datasource set default.
  - CI guard `scripts/verify_dashboards.py` validates dashboard titles.
- Stability fix: `equity_gauge` is a labeled Gauge; ledger guards prevent NoneType crashes.

## Changes
- Metrics (exec):
  - Added getters `get_fees_paid_usd_total()` and `get_account_equity_usd()`; helper `set_equity_gauges(...)`.
  - Simulator: increments USD fees per fill with `{market,symbol}`.
  - Ledger: sets USD equity per market on mark-to-market.
  - Offline demo: logs "fees emitted: <count>", and emits two equity snapshots with markers.
- Grafana:
  - `config/grafana/provisioning/dashboards/paperbot-crypto.json` and `paperbot-stocks.json` updated with `title`, `uid`, `schemaVersion`, `timezone`, `time`, `tags` (including `market`), and stable shells.
  - `config/grafana/provisioning/dashboards/dashboards.yml` provider points to `/etc/grafana/provisioning/dashboards` with `foldersFromFilesStructure: true`.
  - `config/grafana/provisioning/datasources/prometheus.yml` default Prometheus datasource.
  - Added `scripts/verify_dashboards.py` to fail CI on missing titles.
- LLM advisory:
  - `src/paperbot/llm/` client, providers (Gemini, Local OpenAI), router, guards, contracts; tests for schema/memory/metrics.

## Validation
- Dashboards: Provisioned without "Dashboard title cannot be empty"; API confirms titles/uids.
- Datasource: `/api/datasources` shows Prometheus as default.
- Verify script: `python3 scripts/verify_dashboards.py` → status ok.
- Metrics (live proof via container offline demo):
  - `fees_paid_usd_total{market="crypto",symbol="BTC/USDT"} ...`
  - `account_equity_usd{market="crypto"} ...`
  - Logs: `fees emitted: <count>`, `equity gauges set (first)`, `equity gauges set (second)`.
- Tests (subset): metrics accounting tests pass; broader suite unchanged.

## Rollout and Compatibility
- Legacy metrics remain in parallel for one release; dashboards continue to render.
- New metrics power additional panels; migration plan retained in notes.

## Next Steps
- Add periodic equity tick in online mode (N-second scheduler).
- USD conversion for non-USD quoted pairs in fees (if needed).
- CI: include dashboard verify script and optional Grafana API smoke check.

## Links
- Runbook: docs/RUNBOOK.md
- Decision Log index: docs/decisions/README.md

