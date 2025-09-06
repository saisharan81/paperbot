## PR Checklist

- [ ] Updated `codex/STATE.json` and README Phase Log
- [ ] No secrets committed (.env, keys)
- [ ] Linked task id: <!-- e.g., P0-FIXES-AND-OFFLINE-DEMO -->

### Merge checklist
- [ ] Tests pass (`PYTHONPATH=src pytest -q`)
- [ ] Offline demo shows `order submitted`, `fill`, and **execution demo complete**
- [ ] Metrics/Grafana panels verified (signals/orders/fills/fees/equity)
- [ ] RUNBOOK + ADR index updated
- [ ] Branch up to date with `main`
 - [ ] Decision Log V2 JSONL sample present
 - [ ] Legacy → new metric name migration confirmed (`account_equity_usd`, `fees_paid_usd_total`)

## Summary

- What changed and why

## Acceptance Evidence

- Commands run and key logs/outputs

## Risks

- Potential regressions or operational concerns
