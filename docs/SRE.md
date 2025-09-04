SRE Runbook — paperbot

Overview
- Purpose: Operate and validate the paperbot service locally (dev) and via Docker Compose, run tests, and troubleshoot.
- Scope: Phase 0 demo and Phase 1.1 features.

Environments
- Local venv (fast iteration):
  - Python 3.11: `python3.11 -m venv .venv && source .venv/bin/activate`
  - Deps: `pip install -U pip setuptools wheel` then
    `pip install ccxt pandas numpy pyarrow ta pandas-ta pydantic prometheus_client jinja2 matplotlib duckdb python-dotenv pyyaml pytest pytest-mock black ruff`
  - Env: `set -a; source .env; set +a`
  - Run: `PYTHONPATH=src python -m paperbot.main`
- Docker Compose (full stack):
  - `docker compose up --build`
  - Services: bot (exits after demo), Prometheus (:9090), Grafana (:3000)

Config & Env Prefix
- Config: `config/config.yaml`
  - `exchange`, `environment`, `symbols`, `timeframe`, `fetch.*`, `features.*`
- Env prefix: `{exchange.upper()}_{environment.replace('-', '_').upper()}`
  - Example: `binance + spot-testnet` → `BINANCE_SPOT_TESTNET_API_KEY`, `..._API_SECRET`, optional `..._API_PASSPHRASE`
- Example `.env`: see `src/paperbot/.env.example`

Run Tests
- All tests: `pytest -q`
- With output: `pytest -vv -s`
- Focused:
  - Phase 1.1 basics: `pytest -q -s tests/test_feature_builder_phase11.py::test_phase11_basic_bounds`
  - Z-score behavior: `pytest -q -s tests/test_feature_builder_phase11.py::test_z_vwap_on_flat_and_outlier`

What to Expect
- Phase 0 demo:
  - Logs exactly 10 lines starting with `candle: {...}` then `INFO candle demo complete`.
  - Metrics on `:$PROMETHEUS_PORT` (default 8000).
- Phase 1.1 tests print example values (when `-s`): RSI/ATR/VWAP/z_vwap/rv_30m.

Metrics & Observability
- Exporter: started in `paperbot.main` via `prometheus_client.start_http_server($PROMETHEUS_PORT)`.
- Counters:
  - `candles_fetched_total{symbol}` — increments per logged candle (10 in demo).
  - `features_computed_total{symbol}` — increments per computed feature row.
- Quick check: `curl http://localhost:$PROMETHEUS_PORT/metrics | head -n 10`

Making Changes — Where & How
- Baseline features (Phase 1.1): `src/paperbot/features/feature_builder.py`
  - Functions: `_rsi_wilder`, `_atr_ewm`, `_session_vwap_current`, `_zscore_to_vwap`, `_realized_vol`.
  - Aggregator: `compute_phase11_features` (merged into `compute_latest`).
  - Tuning windows via `config/config.yaml` under `features`:
    - `window_rsi` (default 14), `window_atr` (14), `zscore_lookback` (50), `rv_window` (30)
- Optional indicators: `src/paperbot/features/expansion.py` (enable/disable in `config/config.yaml` → `features.expansion`).
- Candle fetch & normalization: `src/paperbot/data/candles.py`.
- Settings/env-prefix: `src/paperbot/config/loader.py`.
- Entry point & metrics: `src/paperbot/main.py` (candle logging, counters, final log).

Testing Changes
- Add tests in `tests/`, follow existing style:
  - `tests/test_feature_builder_phase11.py` for Phase 1.1 examples.
- Run `pytest -q`; use `-k` to filter and `-s` to see `print()` output.
- Keep functions pure and handle low-data cases with safe defaults (no NaNs/exceptions leaking to callers).

Common Issues & Remedies
- Missing credentials: Exception in `load_settings()`. Ensure `.env` matches prefix and `config.yaml`.
- Port in use: Change `PROMETHEUS_PORT` in `.env` or free the port.
- No metrics: Confirm main logs "Prometheus metrics server started on :PORT" and curl `/metrics`.
- Exchange network/rate limits: Re-run after a short delay; reduce symbol list; check connectivity.
- Timezone-sensitive tests: `hour_of_day` uses UTC; ensure system clock/timezone don’t affect UTC.

Operational Notes
- Demo intentionally exits; Compose may restart the `bot` container since it ends by design.
- For continuous runs, add a loop in `paperbot.main` (future phase) or run a scheduler.

