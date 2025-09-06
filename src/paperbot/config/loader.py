"""
Configuration loader for paperbot.

What it does:
- Reads static settings from `config/config.yaml`.
- Resolves API credentials from environment variables using an exchange/environment
  derived prefix: `{exchange.upper()}_{environment.replace('-', '_').upper()}`.
  Example: `BINANCE_SPOT_TESTNET_API_KEY`.
- Validates the resulting configuration using Pydantic models.

Where it is used:
- Called by `paperbot.main` to build a `Settings` object for runtime.

Key outputs:
- `Settings` model containing exchange, environment, symbols, timeframe, and
  validated credential fields, plus fetch/backoff configuration.
"""

import os
import yaml
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator
import pathlib

class FetchConfig(BaseModel):
    """Tunable parameters for API request pacing and backoff."""
    rate_limit_ms: int
    backoff_initial_ms: int
    backoff_max_ms: int

class Settings(BaseModel):
    """Runtime settings assembled from YAML + environment variables."""
    exchange: str
    environment: str
    symbols: List[str]
    timeframe: str
    api_key: str
    api_secret: str
    api_passphrase: Optional[str] = ""
    fetch: FetchConfig

    @field_validator("api_key", "api_secret")
    @classmethod
    def not_empty(cls, v, info):
        if not v:
            raise ValueError(f"Missing required API credential: {info.field_name}")
        return v

def load_settings(path: str = "config/config.yaml") -> Settings:
    """Load YAML config, resolve env-var credentials, and return Settings.

    Env-var names follow the prefix convention using `exchange` and `environment`.
    """
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    exchange = config["exchange"]
    environment = config["environment"]
    symbols = config["symbols"]
    timeframe = config["timeframe"]
    fetch = config["fetch"]
    env_prefix = f"{exchange.upper()}_{environment.replace('-', '_').upper()}"
    api_key = os.getenv(f"{env_prefix}_API_KEY", "")
    api_secret = os.getenv(f"{env_prefix}_API_SECRET", "")
    api_passphrase = os.getenv(f"{env_prefix}_API_PASSPHRASE", "")
    if not api_key or not api_secret:
        raise ValueError(
            f"Missing required API credentials. Expected env vars: {env_prefix}_API_KEY, {env_prefix}_API_SECRET"
        )
    return Settings(
        exchange=exchange,
        environment=environment,
        symbols=symbols,
        timeframe=timeframe,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
        fetch=FetchConfig(**fetch),
    )


def load_exchange_profile(exchange: str, environment: str) -> Dict[str, Any]:
    """Load an exchange execution profile YAML from config/exchanges/.

    Selects a profile name based on (exchange, environment). For example,
    binance + spot-* loads `binance_spot.yml`.
    """
    base = pathlib.Path("config/exchanges")
    name = None
    ex = exchange.lower()
    env = environment.lower()
    if ex == "binance" and "spot" in env:
        name = "binance_spot.yml"
    elif ex == "alpaca":
        name = "alpaca.yml"
    else:
        name = "binance_spot.yml"
    p = base / name
    if not p.exists():
        return {}
    with open(p, "r") as f:
        return yaml.safe_load(f) or {}
