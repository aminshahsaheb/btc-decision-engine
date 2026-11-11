from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path

import pandas as pd

ENGINE_VERSION = "0.3.0-dev"
DB = Path("decision_journal_v3.sqlite3")
SOURCES = ("manual", "scheduled")

_ANALYSES = """CREATE TABLE IF NOT EXISTS analyses (
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

_OUTCOMES = """CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    exit_price REAL,
    exit_time TEXT,
    candles_held INTEGER,
    r_gross REAL,
    r_net REAL,
    evaluated_at TEXT NOT NULL,
    note TEXT
)"""


def _migrate(con: sqlite3.Connection) -> None:
    columns = {row[1] for row in con.execute("PRAGMA table_info(analyses)")}
    if "source" not in columns:
        con.execute("ALTER TABLE analyses ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")
    if "candle_time" not in columns:
        con.execute("ALTER TABLE analyses ADD COLUMN candle_time TEXT")
    con.commit()


def _connect(db_path=None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB
    con = sqlite3.connect(path)
    con.execute(_ANALYSES)
    _migrate(con)
    con.execute(_OUTCOMES)
    con.commit()
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


def save_analysis(result, cfg, fingerprint, db_path=None, now=None,
                  candle_time=None, source="manual") -> dict:
    """Store one analysis.

    manual: an identical input fingerprint is not stored twice.
    scheduled: at most one record per closed 15m candle (candle_time is required).
    """
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    if source == "scheduled" and not candle_time:
        raise ValueError("scheduled analyses need candle_time")

    stamp = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    payload = json.dumps(result, ensure_ascii=False, default=str)
    config = json.dumps(cfg, sort_keys=True, default=str)
    stored_fp = fingerprint if source == "manual" else f"{source}|{candle_time}|{fingerprint}"

    con = _connect(db_path)
    try:
        if source == "scheduled":
            existing = con.execute(
                "SELECT id, analysis_id FROM analyses WHERE source = 'scheduled' AND candle_time = ?",
                (candle_time,),
            ).fetchone()
        else:
            existing = con.execute(
                "SELECT id, analysis_id FROM analyses WHERE fingerprint = ?", (stored_fp,)
            ).fetchone()
        if existing:
            return {"id": existing[0], "analysis_id": existing[1], "duplicate": True}

        analysis_id = str(uuid.uuid4())
        cur = con.execute(
            """INSERT INTO analyses
               (analysis_id, analyzed_at, engine_version, label, data_status, market_status,
                direction_status, setup_status, fingerprint, config, payload, source, candle_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                analysis_id, stamp.isoformat(), ENGINE_VERSION, result["label"],
                result["data"]["status"], result["market"]["status"],
                result["direction"]["status"], result["setup"]["status"],
                stored_fp, config, payload, source, candle_time,
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
            """SELECT id, analyzed_at, source, candle_time, label, data_status,
                      market_status, direction_status, setup_status
               FROM analyses ORDER BY id DESC LIMIT ?""",
            con, params=(limit,),
        )
    finally:
        con.close()
