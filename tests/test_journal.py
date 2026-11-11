import json
import sqlite3

import pandas as pd

from src import journal

CFG = {"equity": 1000.0, "risk_pct": 0.5}


def sample_result(label="WAIT"):
    return {
        "label": label,
        "data": {"status": "VALID", "reasons": []},
        "market": {"status": "NOT_TRADEABLE", "reasons": ["x"]},
        "direction": {"status": "NEUTRAL", "bull": 1, "bear": 1,
                      "bull_evidence": [], "bear_evidence": []},
        "setup": {"status": "NO_ENTRY", "reasons": ["y"], "plan": None},
        "executable": False,
        "error": None,
    }


def frames(last="2026-11-11 01:00"):
    return {
        tf: pd.DataFrame({"time": pd.to_datetime(["2026-11-11 00:45", last], utc=True)})
        for tf in ("15m", "1h", "4h")
    }


def deriv(snapshot="2026-11-11T01:00:00Z"):
    return {"funding_rate": 0.0001, "mark_price": 65000.0, "open_interest": 1234.0,
            "book_imbalance": 0.1, "snapshot_time": pd.Timestamp(snapshot)}


def test_save_and_read_back(tmp_path):
    db = tmp_path / "j.sqlite3"
    saved = journal.save_analysis(sample_result(), CFG, "fp1", db_path=db, now="2026-11-11T02:00:00Z")
    assert saved["duplicate"] is False
    df = journal.recent_decisions(db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["label"] == "WAIT"
    assert df.iloc[0]["setup_status"] == "NO_ENTRY"
    assert df.iloc[0]["analyzed_at"].startswith("2026-11-11T02:00:00")
    with sqlite3.connect(db) as con:
        row = con.execute("SELECT engine_version, payload, config FROM analyses").fetchone()
    assert row[0] == journal.ENGINE_VERSION
    assert json.loads(row[1])["setup"]["status"] == "NO_ENTRY"
    assert json.loads(row[2]) == CFG


def test_duplicate_fingerprint_is_not_saved_twice(tmp_path):
    db = tmp_path / "j.sqlite3"
    first = journal.save_analysis(sample_result(), CFG, "same", db_path=db)
    second = journal.save_analysis(sample_result(), CFG, "same", db_path=db)
    assert second["duplicate"] is True
    assert second["id"] == first["id"]
    assert len(journal.recent_decisions(db_path=db)) == 1


def test_different_fingerprints_make_separate_rows(tmp_path):
    db = tmp_path / "j.sqlite3"
    a = journal.save_analysis(sample_result(), CFG, "a", db_path=db)
    b = journal.save_analysis(sample_result(), CFG, "b", db_path=db)
    assert a["analysis_id"] != b["analysis_id"]
    assert len(journal.recent_decisions(db_path=db)) == 2


def test_recent_is_newest_first_and_limited(tmp_path):
    db = tmp_path / "j.sqlite3"
    for name in ("a", "b", "c"):
        journal.save_analysis(sample_result(), CFG, name, db_path=db)
    df = journal.recent_decisions(limit=2, db_path=db)
    assert list(df["id"]) == [3, 2]


def test_empty_journal(tmp_path):
    df = journal.recent_decisions(db_path=tmp_path / "empty.sqlite3")
    assert len(df) == 0
    assert "label" in df.columns


def test_journal_file_is_not_the_v02_file():
    assert journal.DB.name == "decision_journal_v3.sqlite3"


def test_fingerprint_is_stable():
    assert journal.input_fingerprint(frames(), deriv(), CFG) == journal.input_fingerprint(frames(), deriv(), CFG)


def test_fingerprint_changes_with_config():
    a = journal.input_fingerprint(frames(), deriv(), CFG)
    b = journal.input_fingerprint(frames(), deriv(), dict(CFG, risk_pct=1.0))
    assert a != b


def test_fingerprint_changes_with_last_candle():
    a = journal.input_fingerprint(frames("2026-11-11 01:00"), deriv(), CFG)
    b = journal.input_fingerprint(frames("2026-11-11 01:15"), deriv(), CFG)
    assert a != b


def test_fingerprint_ignores_snapshot_time():
    a = journal.input_fingerprint(frames(), deriv("2026-11-11T01:00:00Z"), CFG)
    b = journal.input_fingerprint(frames(), deriv("2026-11-11T01:05:00Z"), CFG)
    assert a == b
