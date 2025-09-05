"""
Main entrypoint for paperbot.

What it does:
- Loads runtime settings from `config/config.yaml` and environment variables
  using the env-prefix convention (e.g., `BINANCE_SPOT_TESTNET_*`).
- Fetches a small batch of recent OHLCV candles per configured symbol via ccxt.
- Builds a feature vector for the most recent candle(s) using FeatureBuilder.
- Logs the resulting features and exits cleanly (demo flow; no long-running loop yet).

Where it is used:
- Invoked by `python -m paperbot.main` (see `Makefile: run` and Docker CMD).
- The Docker Compose `bot` service runs this module as the container entrypoint.

Key related modules:
- `paperbot.config.loader.Settings` and `load_settings`
- `paperbot.data.candles.CandleFetcher`
- `paperbot.features.feature_builder.FeatureBuilder`
"""
import logging
import os
import yaml
import time
from paperbot.config.loader import load_settings
from paperbot.features.feature_builder import FeatureBuilder
from prometheus_client import start_http_server, Counter

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Resolve settings from YAML + environment; errors if API creds missing
    settings = load_settings()
    env_prefix = f"{settings.exchange.upper()}_{settings.environment.replace('-', '_').upper()}"
    logging.info(f"Resolved env prefix: {env_prefix}")
    logging.info(f"Exchange: {settings.exchange}, Environment: {settings.environment}")
    
    # Load config for feature builder (feature toggles, etc.)
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Start Prometheus metrics server
    prom_port = int(os.getenv("PROMETHEUS_PORT", "8000"))
    try:
        start_http_server(prom_port)
        logging.info(f"Prometheus metrics server started on :{prom_port}")
    except OSError as e:
        logging.warning(f"Failed to start Prometheus server on :{prom_port}: {e}")

    # Define metrics
    CANDLES_FETCHED = Counter("candles_fetched_total", "Candles fetched", ["symbol"]) 
    FEATURES_COMPUTED = Counter("features_computed_total", "Features computed", ["symbol"]) 
    SIGNALS_EMITTED = Counter("signals_emitted_total", "Signals emitted", ["strat", "side", "symbol"]) 
    SIGNALS_SUPPRESSED = Counter("signals_suppressed_total", "Signals suppressed", ["strat", "reason"]) 

    # Feature computation pipeline (fetcher is created later if needed)
    feature_builder = FeatureBuilder(config)

    # Optional OFFLINE_DEMO mode: generate synthetic candles, avoid network
    if os.getenv("OFFLINE_DEMO", "0") == "1":
        logging.info("OFFLINE_DEMO=1: using synthetic candles")
        try:
            import numpy as np  # local import to keep main lean
        except Exception:
            logging.warning("OFFLINE_DEMO requested but numpy unavailable; falling back to zeros")
            np = None

        candle_logs_remaining = 10
        now_ms = int(time.time() * 1000)
        timeframe_ms = 60_000  # assumes 1m timeframe for demo

        # Prepare strategies
        strategies_cfg = config.get("strategies", {})
        enabled_strategies = []
        try:
            from paperbot.strategies.mr import MeanReversionStrategy
            from paperbot.strategies.momentum import MomentumStrategy
            from paperbot.strategies.runner import StrategyRunner
        except Exception as e:
            logging.warning(f"Failed to import strategies: {e}")
            strategies_cfg = {}

        if strategies_cfg:
            if strategies_cfg.get("mr", {}).get("enabled", False):
                enabled_strategies.append(MeanReversionStrategy(strategies_cfg.get("mr", {})))
            if strategies_cfg.get("momentum", {}).get("enabled", False):
                enabled_strategies.append(MomentumStrategy(strategies_cfg.get("momentum", {})))
        runner = StrategyRunner(enabled_strategies, signals_counter=SIGNALS_EMITTED, suppressed_counter=SIGNALS_SUPPRESSED)

        signals_remaining = 3
        forced_done = False
        for symbol in settings.symbols:
            # create ~20 synthetic candles per symbol
            candles = []
            price = 100.0
            for i in range(20):
                if np is not None:
                    price += float(np.random.normal(0.0, 0.5))
                    o = price + float(np.random.normal(0.0, 0.1))
                    h = max(o, price) + 0.5
                    l = min(o, price) - 0.5
                    v = abs(float(np.random.normal(100.0, 10.0)))
                else:
                    # deterministic fallback
                    o = price
                    h = o + 0.5
                    l = o - 0.5
                    v = 100.0
                candles.append({
                    "timestamp": now_ms - (19 - i) * timeframe_ms,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": price,
                    "volume": v,
                    "symbol": symbol,
                })

            # Emit exactly 10 normalized candles across symbols
            for c in candles:
                if candle_logs_remaining <= 0:
                    break
                normalized = {
                    "ts": c.get("timestamp"),
                    "o": c.get("open"),
                    "h": c.get("high"),
                    "l": c.get("low"),
                    "c": c.get("close"),
                    "v": c.get("volume"),
                    "timeframe": settings.timeframe,
                    "symbol": symbol,
                }
                logging.info(f"candle: {normalized}")
                CANDLES_FETCHED.labels(symbol).inc()
                candle_logs_remaining -= 1

            # Compute features and increment metrics
            features = feature_builder.compute_latest(candles)
            logging.info(f"{symbol} features: {features}")
            FEATURES_COMPUTED.labels(symbol).inc()

            # Run strategies and log up to 10 signals across all symbols
            if enabled_strategies and signals_remaining > 0:
                signals = runner.on_feature_row(features)
                for sig in signals:
                    if signals_remaining <= 0:
                        break
                    logging.info(f"strategy signal: {sig.__dict__}")
                    signals_remaining -= 1

            # Deterministic forced signals (once) to demonstrate Phase 1.2
            if enabled_strategies and not forced_done and signals_remaining > 0:
                # Force MR enter (z<=-1.6) and Momentum enter (rsi>=60) on first row
                forced1 = dict(features)
                forced1["z_vwap"] = -1.7
                forced1["rsi14"] = 62.0
                forced1["rv_30m"] = 0.01
                # Force MR exit (z>=-0.3); keep RSI still high to avoid momentum exit
                forced2 = dict(features)
                forced2["z_vwap"] = -0.2
                forced2["rsi14"] = 61.0
                forced2["rv_30m"] = 0.01
                for row in (forced1, forced2):
                    if signals_remaining <= 0:
                        break
                    s_list = runner.on_feature_row(row)
                    for sig in s_list:
                        if signals_remaining <= 0:
                            break
                        logging.info(f"strategy signal: {sig.__dict__}")
                        signals_remaining -= 1
                forced_done = True

        # --- Phase 2: Execution demo (offline) ---
        try:
            from paperbot.exec.simulator import ExecutionSimulator
            from paperbot.risk.engine import RiskEngine
            from paperbot.ledger.ledger import Ledger
        except Exception as e:
            logging.warning(f"Failed to import execution modules: {e}")
            logging.info("candle demo complete")
            logging.info("strategy demo complete")
            hold = int(os.getenv("HOLD_METRICS_SECONDS", "0"))
            if hold > 0:
                logging.info(f"holding metrics server for {hold}s before exit")
                time.sleep(hold)
            return

        exec_cfg = config.get("execution", {})
        risk_cfg = config.get("risk", {})
        # Load exchange execution profile
        from paperbot.config.loader import load_exchange_profile
        profile = load_exchange_profile(settings.exchange, settings.environment)
        simulator = ExecutionSimulator(exec_cfg, profile=profile)
        ledger = Ledger(equity_start=10_000.0)
        risk_engine = RiskEngine(risk_cfg, equity_start=ledger.equity)

        # Use the last synthetic candle per symbol for fills and the shaped rows for entries
        for symbol in settings.symbols:
            # Create a shaped feature row to force an entry for each symbol
            forced = {
                "timestamp": int(time.time() * 1000),
                "symbol": symbol,
                "price": 100.0,
                "atr14": 1.0,
            }
            # Use Momentum long for demo simplicity
            if enabled_strategies:
                from paperbot.strategies.base import Signal
                sig = Signal(ts=forced["timestamp"], symbol=symbol, strategy="momentum", side="long", strength=1.0, reason="demo", params={})
                order = risk_engine.approve(sig, forced, ledger.equity)
                if order:
                    logging.info(f"order submitted: {order.__dict__}")
                    # fabricate a candle for this symbol
                    candles = [
                        {"timestamp": forced["timestamp"], "open": 100.0, "high": 100.2, "low": 99.8, "close": 100.1, "volume": 100.0},
                        {"timestamp": forced["timestamp"] + 60_000, "open": 100.1, "high": 100.3, "low": 99.9, "close": 100.15, "volume": 100.0},
                    ]
                    # simulate partial fills across two bars
                    for cndl in candles:
                        fills = simulator.submit(order, cndl, features={"atr14": 1.0})
                        for f in fills:
                            logging.info(f"fill: {f.__dict__}")
                            ledger.on_fill(f)
                    # MTM at close
                    ledger.mark_to_market(forced["timestamp"], {symbol: cndl["close"]})
        # Write outputs
        ledger.write_parquet("data")
        logging.info("candle demo complete")
        logging.info("strategy demo complete")
        logging.info("execution demo complete")
        # Optional: keep the metrics server alive for inspection
        hold = int(os.getenv("HOLD_METRICS_SECONDS", "0"))
        if hold > 0:
            logging.info(f"holding metrics server for {hold}s before exit")
            time.sleep(hold)
        return

    # Exchange client + feature computation pipeline for live/demo network mode
    from paperbot.data.candles import CandleFetcher
    fetcher = CandleFetcher(settings)
    # Prepare strategies for online mode
    strategies_cfg = config.get("strategies", {})
    enabled_strategies = []
    try:
        from paperbot.strategies.mr import MeanReversionStrategy
        from paperbot.strategies.momentum import MomentumStrategy
        from paperbot.strategies.runner import StrategyRunner
    except Exception as e:
        logging.warning(f"Failed to import strategies: {e}")
        strategies_cfg = {}

    if strategies_cfg:
        if strategies_cfg.get("mr", {}).get("enabled", False):
            enabled_strategies.append(MeanReversionStrategy(strategies_cfg.get("mr", {})))
        if strategies_cfg.get("momentum", {}).get("enabled", False):
            enabled_strategies.append(MomentumStrategy(strategies_cfg.get("momentum", {})))
    runner = StrategyRunner(enabled_strategies, signals_counter=SIGNALS_EMITTED, suppressed_counter=SIGNALS_SUPPRESSED)
    signals_remaining = 10
    
    # Log exactly 10 normalized candles across all symbols, then compute features
    candle_logs_remaining = 10
    for symbol in settings.symbols:
        logging.info(f"Processing {symbol}...")
        # Need ~20 candles for some optional indicators (e.g., Bands)
        candles = fetcher.fetch_candles(symbol, limit=20)
        
        # Add symbol to each candle for feature building
        for candle in candles:
            candle['symbol'] = symbol
        
        # Emit up to `candle_logs_remaining` normalized candles across symbols
        for c in candles:
            if candle_logs_remaining <= 0:
                break
            # Normalize keys to concise schema for logs
            normalized = {
                "ts": c.get("timestamp"),
                "o": c.get("open"),
                "h": c.get("high"),
                "l": c.get("low"),
                "c": c.get("close"),
                "v": c.get("volume"),
                "timeframe": settings.timeframe,
                "symbol": symbol,
            }
            logging.info(f"candle: {normalized}")
            CANDLES_FETCHED.labels(symbol).inc()
            candle_logs_remaining -= 1
        
        # Compute features for the latest candle window
        features = feature_builder.compute_latest(candles)
        
        # Log the feature row
        logging.info(f"{symbol} features: {features}")
        FEATURES_COMPUTED.labels(symbol).inc()
        
        # Log selected expansion features if enabled via config
        expansion_config = config.get('features', {}).get('expansion', {})
        if expansion_config.get('sma_ema', False):
            logging.info(f"{symbol} SMA/EMA: sma={features.get('sma_ema_sma', 'N/A'):.2f}, "
                        f"ema={features.get('sma_ema_ema', 'N/A'):.2f}, "
                        f"signal={features.get('sma_ema_crossover_signal', 'N/A')}")
        
        if expansion_config.get('bollinger', False):
            logging.info(f"{symbol} Bollinger: upper={features.get('bb_upper_band', 'N/A'):.2f}, "
                        f"middle={features.get('bb_middle_band', 'N/A'):.2f}, "
                        f"lower={features.get('bb_lower_band', 'N/A'):.2f}")
        
        if expansion_config.get('obv', False):
            logging.info(f"{symbol} OBV: obv={features.get('obv_obv', 'N/A'):.2f}, "
                        f"change={features.get('obv_obv_change', 'N/A'):.2f}")
        
        if expansion_config.get('hour_of_day', False):
            logging.info(f"{symbol} Hour: {features.get('hour_hour_int', 'N/A')} "
                        f"({features.get('hour_hour_cat', 'N/A')})")

        # Run strategies and log up to 10 signals across all symbols
        if enabled_strategies and signals_remaining > 0:
            signals = runner.on_feature_row(features)
            for sig in signals:
                if signals_remaining <= 0:
                    break
                logging.info(f"strategy signal: {sig.__dict__}")
                signals_remaining -= 1
    
    logging.info("candle demo complete")
    logging.info("strategy demo complete")
    # Optional: keep the metrics server alive for inspection
    hold = int(os.getenv("HOLD_METRICS_SECONDS", "0"))
    if hold > 0:
        logging.info(f"holding metrics server for {hold}s before exit")
        time.sleep(hold)

if __name__ == "__main__":
    main()
