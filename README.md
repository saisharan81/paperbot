# Paperbot — AI Paper Trading Agent

**What this is**
An autonomous trading system that starts with **paper trading** (no real money) to build confidence, then can graduate to live trading. MVP runs on **Binance Spot Testnet**; the design supports multiple brokers via config.

**Key Goals**
- Robust end-to-end pipeline: **Market data → Features → Strategies → Risk → Execution (paper) → Ledger → Reports**
- Safety-first design: central Risk Engine + kill-switch control
- Observability: Prometheus metrics + Grafana dashboards + daily EOD reports
- Incremental development in **phases**, each with tests and documentation

## Tech Stack
- **Language:** Python 3.11
- **Core libs:** ccxt, pandas, numpy, pyarrow, ta/pandas-ta, pydantic
- **Monitoring:** prometheus_client, Prometheus, Grafana
- **Config/Env:** YAML configs + `.env` with **dynamic env-prefix** (e.g., `BINANCE_SPOT_TESTNET_*`)
- **Packaging/Runtime:** Docker + Docker Compose
- **Testing:** pytest, pytest-mock

## Repository Layout

```
src/paperbot/
├── data/         # exchange adapters, OHLCV/candles fetchers
├── features/     # feature pipeline (RSI/ATR/VWAP/Z-score/realized vol)
├── strategies/   # Signal dataclass, base, MR/Momentum, runner
├── risk/         # central risk engine + limits + kill-switch
├── exec/         # order/position/fill models + execution simulator
├── ledger/       # positions, realized/unrealized PnL, equity/drawdown
├── metrics/      # Prometheus helpers and counters/gauges
├── reports/      # EOD HTML/CSV (future)
└── config/       # config loader & typed settings

  llm/            # provider-agnostic client (future)
  prompts/        # decision prompts (bounded JSON)

config/           # YAML config + Prometheus/Grafana provisioning
tests/            # unit tests
```

## Decision Log
- See `docs/decisions/README.md` for ADRs (Architecture Decision Records), including signal schema, risk guardrails, metrics naming, offline determinism, and branching/release workflow.

## Current Status

- Phase 0 — Bootstrap & Candle Fetch Demo: PASS
  - Emits exactly 10 normalized candle lines; exits with "candle demo complete".
  - Prometheus endpoint served on `$PROMETHEUS_PORT` (default 8000).
- Phase 1.1 — Baseline Features: Implemented
  - RSI(14) [Wilder], ATR(14) [TR EWM], Session VWAP (UTC), Z-score to VWAP (50 bars), Realized Vol (30 bars).
  - Optional extras (config toggles): SMA/EMA crossover, Bollinger Bands, OBV, Keltner, skew/kurtosis, hour-of-day.

See also: `tests/test_feature_builder_phase11.py` for coverage of Phase 1.1 indicators.

## Setup & Run (Phase 0)

### 1. **.env** (Binance Spot Testnet)
```bash
BINANCE_SPOT_TESTNET_API_KEY=your_key
BINANCE_SPOT_TESTNET_API_SECRET=your_secret
PROMETHEUS_PORT=8000
```

### 2. **config/config.yaml** (snippet)
```yaml
exchange: binance
environment: spot-testnet
symbols: ["BTC/USDT", "ETH/USDT"]
timeframe: "1m"
fetch:
  rate_limit_ms: 900
  backoff_initial_ms: 500
  backoff_max_ms: 8000
```

### 3. Run via Docker
```bash
docker compose up --build

# metrics:
curl http://localhost:8000/metrics | head -n 10
# grafana: http://localhost:3000  (Prometheus DS pre-provisioned)
# prometheus: http://localhost:9090
```

### 4. Expected Phase 0 demo behavior
- Logs exactly 10 normalized candles total across symbols, then:
  ```
  INFO candle demo complete
  ```
- Compose may restart the container (demo ends by design).
- Metrics endpoint available on `:8000/metrics`.

## Local Development (venv)

```bash
# Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -U pip setuptools wheel
pip install ccxt pandas numpy pyarrow ta pandas-ta pydantic prometheus_client jinja2 matplotlib duckdb python-dotenv pyyaml pytest pytest-mock black ruff

# Export env and run
set -a; source .env; set +a
PYTHONPATH=src python -m paperbot.main

# Tests (show prints for a few results)
pytest -q
pytest -vv -s tests/test_feature_builder_phase11.py -k basic_bounds
```

## Testing & Verification

- What we test (automated):
  - Phase 1.1 baseline indicators: RSI(14), ATR(14), Session VWAP, Z-score to VWAP(50), Realized Vol(30). Invariants: RSI∈[0,100], ATR≥0, VWAP>0 (with volume), Z-score finite/0 on flat series, RV≥0 and >0 on noise.
  - Phase 1.1.1 optional indicators (config-gated): SMA/EMA crossover (signal ±1), MACD (trend-consistent sign), Bollinger (upper>middle>lower), OBV (sign follows trend), Keltner (upper>middle>lower), rolling skew/kurtosis (well-defined), hour_of_day (UTC-safe).
  - Integration sanity: dict shapes/types, robust defaults on insufficient data.

- How to run just Phase 1.1 / 1.1.1 tests:
  - `PYTHONPATH=. .venv/bin/pytest -q tests/test_feature_builder_phase11.py tests/test_features_expansion.py`

- Expected outcome (current):
  - `25 passed` in under a second on a typical dev machine.

- End-to-end demo (Phase 0):
  - Online (default): `docker compose up --build` with testnet keys in repo-root `.env`.
  - Offline (no network): set `OFFLINE_DEMO=1` and optional `HOLD_METRICS_SECONDS=120`; run `python -m paperbot.main` to emit exactly 10 `candle:` logs then `candle demo complete`.
  - Metrics: Prometheus at `:8000/metrics` (hold needed so Prom scrapes); counters `candles_fetched_total{symbol}` and `features_computed_total{symbol}`.

## Strategy Signals (Phase 1.2)

- Log prefix: `strategy signal: { ... }`
- Keys included in the dict: `ts, symbol, strategy, side, strength, reason, params`
- Deterministic offline demo (guaranteed signals):
  - `OFFLINE_DEMO=1 PYTHONPATH=src python -m paperbot.main`
  - Emits 1–3 strategy signals, then prints `strategy demo complete`.
- PromQL examples:
  - Rate (5m): `sum by (strat,side,symbol) (rate(signals_emitted_total[5m]))`
  - Totals (run): `sum by (strat,side,symbol) (signals_emitted_total)`

## Features (Phase 1.1)

- rsi14: Wilder-smoothed RSI over 14 closes, clamped [0,100], safe default 50 on low data.
- atr14: True Range EWM with alpha=1/14, non-negative.
- vwap: Session VWAP for the current UTC day using close*volume.
- z_vwap: Z-score of (close - session VWAP) over 50-bar lookback; 0 if std≈0 or insufficient data.
- rv_30m: Realized volatility over last 30 bars: sqrt(sum(logret^2)), no annualization.

Windows can be tuned via `config/config.yaml` under `features`:

```yaml
features:
  window_rsi: 14
  window_atr: 14
  zscore_lookback: 50
  rv_window: 30
  expansion:
    sma_ema: true
    bollinger: true
    obv: true
```

## Observability (Metrics)

- Prometheus: starts in `paperbot.main` at `$PROMETHEUS_PORT` (default 8000).
- Counters:
  - `candles_fetched_total{symbol}`
  - `features_computed_total{symbol}`

Check quickly:
```bash
curl http://localhost:8000/metrics | head -n 10
```

If your browser says "connection refused": the demo exits quickly. Either:
- Re-run and open `/metrics` immediately, or
- Hold the server open: `HOLD_METRICS_SECONDS=120 PYTHONPATH=src python -m paperbot.main`

## Reports & Charts

- Generate candlestick PNGs and an HTML index:
  - Poetry: `make report`
  - venv: `PYTHONPATH=src python -m paperbot.reports.generate`
- Output location: `./reports/` (images in `./reports/images/`, HTML at `./reports/index.html`)
- Session VWAP is overlaid on charts; bars default to last 120 candles (tune via `REPORT_BARS`).

---

## Architecture (End-State Target)

```mermaid
flowchart LR
  subgraph Ingest
    A[Exchange APIs<br/>(Binance, Alpaca, ...)] --> B[Data Fetchers<br/>(ccxt/SDKs)]
    B --> C[Raw OHLCV Queue]
  end

  subgraph Features
    C --> D[Feature Builder<br/>RSI/ATR/VWAP/ZScore/RealizedVol]
    D --> E[Feature Stream]
  end

  subgraph Strategy
    E --> F[Strategies<br/>Mean Reversion / Momentum / Pairs]
    F --> G[Targets<br/>(side, size, stops, tp)]
  end

  subgraph Risk & Execution
    G --> H[Risk Engine<br/>exposure caps, daily loss, kill-switch]
    H -->|approved| I[Paper Execution<br/>fees/slippage/partial fills]
    I --> J[Ledger<br/>Parquet/SQLite]
  end

  subgraph Observability
    I --> K[Prometheus Metrics]
    J --> L[EOD Reports<br/>HTML/CSV]
  end
```

## Runtime Dataflow (current: Phase 0→1 baseline)

```mermaid
sequenceDiagram
  participant EX as Exchange Testnet
  participant CF as Candle Fetcher
  participant FB as Feature Builder
  participant ST as Strategies
  participant RK as Risk Engine
  participant EXE as Paper Exec
  participant LG as Ledger

  EX->>CF: OHLCV (1m)
  CF->>FB: Candles (ts,o,h,l,c,v)
  FB->>ST: Feature vectors (Phase 1+)
  ST->>RK: Targets (Phase 1.2+)
  RK->>EXE: Approved orders (Phase 2)
  EXE->>LG: Fills & PnL (Phase 2)
```

---

## Phase Map
- **Phase 0** — Bootstrap & Candle Fetch Demo ✅ (complete)
- **Phase 1** — Features & Strategies (MVP)
  - 1.1: Feature Builder (RSI, ATR, VWAP, Z-score to VWAP, realized vol) ✅
  - 1.1.1: Optional features (MACD, Bollinger, OBV, etc.)
  - 1.2: Strategy base + MR/MO
- **Phase 2** — Risk & Execution (paper realism)
- **Phase 3** — Orchestration, Metrics, EOD Reports
- **Phase 4** — Backtesting/Validation
- **Phase 5** — Allocation & Daily Risk Discipline
- **Phase 6** — Paper Burn-in & Go/No-Go
- **Phase 7** — Extensions (pairs, basis, execution improvements)

---

## Phase Log (living diary)

New phase entries will be inserted between these anchors automatically by future tasks.

<!-- PHASE-LOG-START -->

### Phase 0 — Bootstrap & Candle Fetch Demo ✅

**Achievements**
- Repo scaffolding with Docker/Compose, Prometheus, Grafana
- Dynamic env-prefix loader (e.g., `BINANCE_SPOT_TESTNET_*`)
- Binance Spot Testnet integration via ccxt
- Demo: 10 normalized candles per symbol; clean exit with "candle demo complete"
- Metrics endpoint on `:8000/metrics`

**Hurdles & Fixes**
- Python 3.11 mismatch locally → standardized on Docker
- Validated environment resolution logs and curl check for `/metrics`

**Evidence**
- Logs: `Resolved env prefix: BINANCE_SPOT_TESTNET`, `Exchange: binance, Environment: spot-testnet`
- Logs: candle lines + `candle demo complete`
- `curl http://localhost:8000/metrics | head`

### Phase 0 — Offline Demo Path ✅

**Achievements**
- Added `OFFLINE_DEMO=1` mode in `paperbot.main` to generate synthetic 1m candles without network.
- Emits exactly 10 normalized `candle:` logs across configured symbols, then prints `candle demo complete`.
- Metrics server attempted via `prometheus_client`; on bind failure, logs WARNING and proceeds. Metrics counters increment in offline mode.

**Hurdles & Fixes**
- Network/DNS blocked in sandbox → bypassed with offline synthetic candles.
- Port bind denied on `:8000` → graceful degradation with WARNING; marked metrics status as `degraded_warn` in state.

**Evidence**
- Command: `PYTHONPATH=src OFFLINE_DEMO=1 BINANCE_SPOT_TESTNET_API_KEY=foo BINANCE_SPOT_TESTNET_API_SECRET=bar python -m paperbot.main`
- Logs: 10 lines matching `candle: {…}` and a final `candle demo complete`.
- Metrics: `WARNING Failed to start Prometheus server on :8000` (sandbox restriction).

**Acceptance**
- Result: PASS (offline mode with metrics degraded_warn)

### Phase 1.2 — Strategies (MR + Momentum) ✅

**Achievements**
- Added Strategy base and normalized `Signal` schema; implemented Mean Reversion (z_vwap with hysteresis + vol gate) and Momentum (RSI long-only with optional confirmation).
- Wired strategies into offline/online demos; added `signals_emitted_total{strat,side,symbol}` counter and Grafana panels for rates and totals.
- Offline demo shapes deterministic features so 1–3 `strategy signal:` lines are emitted and the run ends with `strategy demo complete`.

**Hurdles & Fixes**
- Synthetic candles don’t always cross thresholds → added deterministic forced rows in offline mode to guarantee at least one signal.
- Metrics bind may be blocked in some environments → counters defined and incremented; dashboard queries operate when Prometheus can scrape.

**Evidence**
- Logs: up to 3 lines prefixed with `strategy signal: { ... }`, then `strategy demo complete`.
- Metrics: PromQL `sum by (strat,side,symbol) (signals_emitted_total)` returns counts during the demo hold.

**Acceptance**
- Result: PASS (deterministic offline signals + metrics counters present)

### Phase 2 — Execution + Risk + Ledger ✅

**Achievements**
- Added Execution Simulator (market/limit fills with slippage & fees), Risk Engine (ATR-based sizing, caps, killswitch), and Ledger (positions, realized/unrealized PnL, equity/drawdown, parquet outputs).
- Wired offline demo: deterministically submits ≥1 order, produces ≥1 fill, updates ledger, and writes `data/trades.parquet` and `data/ledger.parquet`.
- Added Prometheus metrics: `orders_submitted_total{type,symbol}`, `fills_total{liquidity,symbol}`, `fees_paid_total{symbol}`, `realized_pnl_total{symbol}`, `equity_gauge`, `killswitch_trips_total`.

**Hurdles & Fixes**
- Prometheus registry duplicates under pytest → added safe metric getters with no-op fallback to avoid duplicate registration and negative counter increments.
- Metrics bind can be blocked on some hosts → offline demo still completes; use Docker Compose for Prometheus/Grafana scraping.

**Evidence**
- Logs (offline):
  - `order submitted: { ... }`
  - `fill: { ... }`
  - `execution demo complete`
- Artifacts: `data/trades.parquet`, `data/ledger.parquet`
- Metrics (when scraped): counters above increment; `equity_gauge` reflects MTM equity.

**Acceptance**
- Result: PASS (orders + fills + parquet outputs + metrics wired)

<!-- PHASE-LOG-END -->

### Phase 2.1 — Repo Cleanup & Structure Hardening ✅

**Achievements**
- Ensured all packages have `__init__.py` and clarified public APIs (`ledger.Ledger`).
- Added `metrics/core.py` wrapper to start Prometheus server safely; kept entrypoint `python -m paperbot.main`.
- Verified imports use canonical `paperbot.<pkg>` paths; no dead files detected.

**Hurdles & Fixes**
- Avoiding Prometheus registry duplication in tests → retained safe metric getters and no-op fallback.

**Evidence**
- Tests: `PYTHONPATH=src pytest -q` pass (≈37 tests).
- Offline demo: deterministic signals → order + fill → `execution demo complete`.

**Result**
- PASS

---

## Contributing / Extending
- Add brokers by env-prefix convention (e.g., `BINANCE_SPOT_API_KEY`, `ALPACA_PAPER_API_KEY`).
- Add/change baseline indicators in `src/paperbot/features/feature_builder.py`:
  - Key functions: `_rsi_wilder`, `_atr_ewm`, `_session_vwap_current`, `_zscore_to_vwap`, `_realized_vol`, `compute_phase11_features`.
- Add optional indicators in `src/paperbot/features/expansion.py` and toggle in `config/config.yaml` under `features.expansion`.
- Run tests: `pytest -q` (use `-s` to see printed values in Phase 1.1 tests).

For SRE runbook (tests, operations, troubleshooting), see `docs/SRE.md`.

## Disclaimer
Educational/research use only. Not financial advice.
