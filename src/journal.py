from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path

import pandas as pd

ENGINE_VERSION = "0.3.0-dev"
DB = Path("decision_journal_v3.sqlite3")

_SCHEMA = """CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL UNIQUE,
    analyzed_at TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    label TEXT NOT NULL,
    data_status TEXT NOT NULL,
    market_status TEXT NOT NULL,
    direction_status TEXT NOT NULL,
    setup_status TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE,
    config TEXT NOT NULL,
    payload TEXT NOT NULL
)"""


def _connect(db_path=None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB
    con = sqlite3.connect(path)
    con.execute(_SCHEMA)
    return con


def input_fingerprint(data, deriv, cfg) -> str:
    """Hash of the inputs that determine an analysis (last candle times, derivatives, config)."""
    times = {}
    for tf in sorted(data):
        try:
            times[tf] = str(data[tf]["time"].iloc[-1])
        except Exception:
            times[tf] = None
    deriv_part = {k: v for k, v in deriv.items() if k != "snapshot_time"}
    body = {"engine": ENGINE_VERSION, "times": times, "deriv": deriv_part, "cfg": cfg}
    text = json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_analysis(result, cfg, fingerprint, db_path=None, now=None) -> dict:
    """Store one analysis. An identical fingerprint is not stored twice."""
    stamp = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    payload = json.dumps(result, ensure_ascii=False, default=str)
    config = json.dumps(cfg, sort_keys=True, default=str)
    con = _connect(db_path)
    try:
        existing = con.execute(
            "SELECT id, analysis_id FROM analyses WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        if existing:
            return {"id": existing[0], "analysis_id": existing[1], "duplicate": True}
        analysis_id = str(uuid.uuid4())
        cur = con.execute(
            """INSERT INTO analyses
               (analysis_id, analyzed_at, engine_version, label, data_status, market_status,
                direction_status, setup_status, fingerprint, config, payload)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                analysis_id, stamp.isoformat(), ENGINE_VERSION, result["label"],
                result["data"]["status"], result["market"]["status"],
                result["direction"]["status"], result["setup"]["status"],
                fingerprint, config, payload,
            ),
        )
        con.commit()
        return {"id": cur.lastrowid, "analysis_id": analysis_id, "duplicate": False}
    finally:
        con.close()


def recent_decisions(limit=50, db_path=None) -> pd.DataFrame:
    con = _connect(db_path)
    try:
        return pd.read_sql_query(
            """SELECT id, analyzed_at, label, data_status, market_status,
                      direction_status, setup_status
               FROM analyses ORDER BY id DESC LIMIT ?""",
            con, params=(limit,),
        )
    finally:
        con.close()
