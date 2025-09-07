from __future__ import annotations

import os
import sqlite3
from typing import Dict, Any


DDL = """
CREATE TABLE IF NOT EXISTS decisions (
  run_id TEXT,
  ts INTEGER,
  market TEXT,
  symbol TEXT,
  side TEXT,
  size REAL,
  max_notional_usd REAL,
  confidence REAL,
  reason TEXT,
  ttl_s INTEGER,
  json TEXT
);
"""


class SQLiteStore:
    def __init__(self, path: str = "data/memory.sqlite"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        with sqlite3.connect(self.path) as con:
            con.execute(DDL)

    def insert(self, rec: Dict[str, Any]) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO decisions(run_id,ts,market,symbol,side,size,max_notional_usd,confidence,reason,ttl_s,json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rec.get("run_id"),
                    rec.get("ts"),
                    rec.get("market"),
                    rec.get("symbol"),
                    rec.get("side"),
                    float(rec.get("size", 0.0)),
                    float(rec.get("max_notional_usd", 0.0)),
                    float(rec.get("confidence", 0.0)),
                    ",".join(rec.get("reason", [])),
                    int(rec.get("ttl_s", 0)),
                    str(rec),
                ),
            )

