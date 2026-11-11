import sqlite3

import pandas as pd
import pytest

from src import journal, scheduler
from src.outcomes import evaluate_pending, outcome_summary

T = pd.Timestamp("2026-11-11 00:00", tz="UTC")
SIGNAL = str(T)
NEXT = str(T + pd.Timedelta(15, unit="min"))

PLAN = {"side": "LONG", "entry": 100.0, "stop": 97.5, "target1": 102.5, "target2": 105.0,
        "risk": 2.5, "reward": 5.0, "cost_estimate": 0.16, "executable": False}
HIT = [(106.0, 100.0, 105.5)]
QUIET = [(101.0, 99.0, 100.0)] * 3


def result(status="VALID_LONG", plan=PLAN, label="LONG SETUP"):
    return {
        "label": label,
        "data": {"status": "VALID", "reasons": []},
        "market": {"status": "TRADEABLE", "reasons": []},
        "direction": {"status": "BULLISH", "bull": 7, "bear": 0,
                      "bull_evidence": [], "bear_evidence": []},
        "setup": {"status": status, "reasons": [], "plan": plan},
        "executable": False,
        "error": None,
    }


def after(rows):
    times = pd.date_range(T + pd.Timedelta(15, unit="min"), periods=len(rows), freq="15min")
    return pd.DataFrame({
        "time": times,
        "high": [r[0] for r in rows],
        "low": [r[1] for r in rows],
        "close": [r[2] for r in rows],
    })


def save(db, fp, candle=SIGNAL, source="scheduled", res=None):
    return journal.save_analysis(res or result(), {}, fp, db_path=db,
                                 candle_time=candle, source=source)


def test_scheduled_one_record_per_candle(tmp_path):
    db = tmp_path / "j.sqlite3"
    first = save(db, "a")
    same_candle = save(db, "b")
    next_candle = save(db, "c", candle=NEXT)
    assert first["duplicate"] is False
    assert same_candle["duplicate"] is True and same_candle["id"] == first["id"]
    assert next_candle["duplicate"] is False


def test_scheduled_and_manual_with_same_fingerprint_are_both_stored(tmp_path):
    db = tmp_path / "j.sqlite3"
    manual = save(db, "same", source="manual", candle=None)
    scheduled = save(db, "same")
    assert manual["duplicate"] is False and scheduled["duplicate"] is False
    df = journal.recent_decisions(db_path=db)
    assert set(df["source"]) == {"manual", "scheduled"}


def test_scheduled_requires_candle_time(tmp_path):
    with pytest.raises(ValueError):
        journal.save_analysis(result(), {}, "x", db_path=tmp_path / "j.sqlite3", source="scheduled")


def test_unknown_source_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        journal.save_analysis(result(), {}, "x", db_path=tmp_path / "j.sqlite3", source="robot")


def test_old_database_is_migrated(tmp_path):
    db = tmp_path / "old.sqlite3"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id TEXT NOT NULL UNIQUE,
        analyzed_at TEXT NOT NULL, engine_version TEXT NOT NULL, label TEXT NOT NULL,
        data_status TEXT NOT NULL, market_status TEXT NOT NULL, direction_status TEXT NOT NULL,
        setup_status TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
        config TEXT NOT NULL, payload TEXT NOT NULL)""")
    con.execute("""INSERT INTO analyses (analysis_id, analyzed_at, engine_version, label,
        data_status, market_status, direction_status, setup_status, fingerprint, config, payload)
        VALUES ('x','2026-11-11T00:00:00+00:00','0.3.0-dev','WAIT','VALID','NOT_TRADEABLE',
                'NEUTRAL','NO_ENTRY','old','{}','{}')""")
    con.commit()
    con.close()

    df = journal.recent_decisions(db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["source"] == "manual"
    assert save(db, "new")["duplicate"] is False


def test_outcome_is_stored_once(tmp_path):
    db = tmp_path / "j.sqlite3"
    save(db, "a")
    assert evaluate_pending(after(HIT), db_path=db) == 1
    assert evaluate_pending(after(HIT), db_path=db) == 0
    summary = outcome_summary(db_path=db)
    assert summary["setups"] == 1
    assert summary["pending"] == 0
    assert summary["n_resolved"] == 1
    assert summary["by_status"]["TARGET2"]["n"] == 1
    assert summary["sum_r_net"] == pytest.approx((5.0 - 0.16) / 2.5)


def test_manual_setups_are_not_evaluated(tmp_path):
    db = tmp_path / "j.sqlite3"
    save(db, "a", source="manual", candle=None)
    assert evaluate_pending(after(HIT), db_path=db) == 0
    assert outcome_summary(db_path=db)["setups"] == 0


def test_pending_setup_has_no_outcome_yet(tmp_path):
    db = tmp_path / "j.sqlite3"
    save(db, "a")
    assert evaluate_pending(after(QUIET), db_path=db) == 0
    summary = outcome_summary(db_path=db)
    assert summary["pending"] == 1
    assert summary["n_resolved"] == 0


def test_non_setup_records_are_not_evaluated(tmp_path):
    db = tmp_path / "j.sqlite3"
    save(db, "a", res=result(status="NO_ENTRY", plan=None, label="WAIT"))
    assert evaluate_pending(after(HIT), db_path=db) == 0
    summary = outcome_summary(db_path=db)
    assert summary["analyses"] == 1 and summary["setups"] == 0


def test_run_once_stores_one_record_per_candle(monkeypatch, tmp_path):
    db = tmp_path / "run.sqlite3"
    monkeypatch.setattr(scheduler, "decide", lambda market, deriv, cfg: result())
    frame = pd.DataFrame({
        "time": pd.date_range(end=T, periods=3, freq="15min"),
        "high": 101.0, "low": 99.0, "close": 100.0,
    })
    deriv = {"funding_rate": 0.0001, "mark_price": 65000.0, "open_interest": 1234.0,
             "book_imbalance": 0.1, "snapshot_time": pd.Timestamp("2026-11-11T00:05:00Z")}
    load = lambda: ({"15m": frame}, deriv)

    first = scheduler.run_once(load=load, db_path=db)
    second = scheduler.run_once(load=load, db_path=db)

    assert first["duplicate"] is False and second["duplicate"] is True
    assert first["candle_time"] == SIGNAL
    assert outcome_summary(db_path=db)["pending"] == 1
