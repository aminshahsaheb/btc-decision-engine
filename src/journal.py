import sqlite3
import json
from pathlib import Path
import pandas as pd

DB = Path("decision_journal.sqlite3")

def save_decision(result: dict):
    safe = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k,v in result.items()}
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_at TEXT NOT NULL,
            decision TEXT NOT NULL,
            payload TEXT NOT NULL
        )""")
        con.execute("INSERT INTO decisions(saved_at, decision, payload) VALUES(?,?,?)",
                    (pd.Timestamp.now(tz="UTC").isoformat(), result.get("decision","UNKNOWN"),
                     json.dumps(safe, ensure_ascii=False)))
        con.commit()

def recent_decisions(limit=50):
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_at TEXT NOT NULL,
            decision TEXT NOT NULL,
            payload TEXT NOT NULL
        )""")
        return pd.read_sql_query(
            "SELECT id, saved_at, decision FROM decisions ORDER BY id DESC LIMIT ?",
            con, params=(limit,))
