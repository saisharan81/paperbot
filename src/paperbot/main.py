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

        logging.info("candle demo complete")
        # Optional: keep the metrics server alive for inspection
        hold = int(os.getenv("HOLD_METRICS_SECONDS", "0"))
        if hold > 0:
            logging.info(f"holding metrics server for {hold}s before exit")
            time.sleep(hold)
        return

    # Exchange client + feature computation pipeline for live/demo network mode
    from paperbot.data.candles import CandleFetcher
    fetcher = CandleFetcher(settings)
    
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
    
    logging.info("candle demo complete")
    # Optional: keep the metrics server alive for inspection
    hold = int(os.getenv("HOLD_METRICS_SECONDS", "0"))
    if hold > 0:
        logging.info(f"holding metrics server for {hold}s before exit")
        time.sleep(hold)

if __name__ == "__main__":
    main()
