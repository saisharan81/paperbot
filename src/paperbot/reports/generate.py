"""
Generate simple HTML report with candlestick PNGs for configured symbols.

Usage (venv):
  set -a; source .env; set +a
  PYTHONPATH=src python -m paperbot.reports.generate
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from paperbot.config.loader import load_settings
from paperbot.data.candles import CandleFetcher
from paperbot.reports.charts import save_candlestick_png


def _template_env(template_dir: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )


def main() -> None:
    settings = load_settings()
    fetcher = CandleFetcher(settings)

    # Where to write artifacts
    out_dir = os.environ.get("REPORT_DIR", "reports")
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    bars = int(os.getenv("REPORT_BARS", "120"))

    entries = []
    for symbol in settings.symbols:
        candles: List[Dict[str, Any]] = fetcher.fetch_candles(symbol, limit=bars)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fname = f"{symbol.replace('/', '-')}_{settings.timeframe}_{ts}.png"
        out_png = os.path.join(img_dir, fname)
        abs_path = save_candlestick_png(candles, symbol, settings.timeframe, out_png, overlay_session_vwap=True)
        entries.append({
            "symbol": symbol,
            "timeframe": settings.timeframe,
            "image": os.path.relpath(abs_path, start=out_dir),
            "bars": len(candles),
        })

    # Render HTML
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = _template_env(template_dir)
    tpl = env.get_template("report.html.j2")
    html = tpl.render(generated_at=datetime.utcnow().isoformat() + "Z", entries=entries)

    out_html = os.path.join(out_dir, "index.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report written to: {out_html}")


if __name__ == "__main__":
    main()

