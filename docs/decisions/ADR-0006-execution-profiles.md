# ADR-0006: Execution Profiles

Status: Accepted

## Context
We need exchange-specific fee/rounding/minimums to simulate fills and PnL realistically.

## Decision
- Add YAML profiles under `config/exchanges/` selected by `(exchange, environment)`.
- Fields: `fees.{maker_bps,taker_bps}`, `min_notional`, `tick_size`, `step_size`, `slippage_bps`.
- Loader utility selects profile and simulator applies price/qty rounding and min_notional checks.

## Consequences
- Profiles decouple exchange parameters from code; easier to extend/override per environment.

## References
- `config/exchanges/binance_spot.yml`, `config/exchanges/alpaca.yml`
- `src/paperbot/config/loader.py` (load_exchange_profile)
