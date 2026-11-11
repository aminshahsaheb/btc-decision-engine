from __future__ import annotations

import json

import pandas as pd

from src.journal import _connect

CANDLE = pd.Timedelta(15, unit="min")
MAX_CANDLES = 96
RESOLVED = ("STOP", "TARGET2", "EXPIRED")


def _utc(value) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def _unevaluable(note: str) -> dict:
    return {"status": "UNEVALUABLE", "exit_price": None, "exit_time": None,
            "candles_held": None, "r_gross": None, "r_net": None, "note": note}


def _done(status, exit_price, exit_time, held, pnl, risk, cost, note="") -> dict:
    return {
        "status": status,
        "exit_price": float(exit_price),
        "exit_time": str(exit_time),
        "candles_held": int(held),
        "r_gross": pnl / risk,
        "r_net": (pnl - cost) / risk,
        "note": note,
    }


def resolve_outcome(plan, signal_time, candles, max_candles=MAX_CANDLES):
    """Decide how a paper trade ended, using only closed candles after the signal candle.

    Entry is assumed at the plan entry (close of the signal candle). If one candle touches
    both stop and target, the stop is assumed to have been hit first.
    Returns None while the trade is still pending.
    """
    side = plan["side"]
    entry = float(plan["entry"])
    stop = float(plan["stop"])
    target2 = float(plan["target2"])
    risk = float(plan["risk"])
    reward = float(plan["reward"])
    cost = float(plan["cost_estimate"])
    if side not in ("LONG", "SHORT") or risk <= 0:
        return _unevaluable("invalid plan")

    signal_time = _utc(signal_time)
    after = candles[candles["time"] > signal_time].reset_index(drop=True)
    if after.empty:
        return None
    if after["time"].iloc[0] != signal_time + CANDLE:
        return _unevaluable("candle history does not start right after the signal candle")

    window = after.head(max_candles)
    if len(window) > 1 and not (window["time"].diff().dropna() == CANDLE).all():
        return _unevaluable("gap in candle history")

    for i in range(len(window)):
        row = window.iloc[i]
        high, low = float(row["high"]), float(row["low"])
        if side == "LONG":
            hit_stop, hit_target = low <= stop, high >= target2
        else:
            hit_stop, hit_target = high >= stop, low <= target2
        if hit_stop:
            note = "stop and target touched in one candle; stop assumed first" if hit_target else ""
            return _done("STOP", stop, row["time"], i + 1, -risk, risk, cost, note)
        if hit_target:
            return _done("TARGET2", target2, row["time"], i + 1, reward, risk, cost)

    if len(window) >= max_candles:
        last = window.iloc[-1]
        exit_price = float(last["close"])
        pnl = exit_price - entry if side == "LONG" else entry - exit_price
        return _done("EXPIRED", exit_price, last["time"], len(window), pnl, risk, cost)
    return None


_PENDING_SQL = """FROM analyses a
    WHERE a.source = 'scheduled' AND a.setup_status LIKE 'VALID_%'
      AND NOT EXISTS (SELECT 1 FROM outcomes o WHERE o.analysis_id = a.analysis_id)"""


def evaluate_pending(candles, db_path=None, now=None) -> int:
    """Evaluate scheduled setups that have no outcome yet. Returns how many outcomes were stored."""
    stamp = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    con = _connect(db_path)
    stored = 0
    try:
        rows = con.execute(
            "SELECT a.analysis_id, a.candle_time, a.payload " + _PENDING_SQL + " ORDER BY a.id"
        ).fetchall()
        for analysis_id, candle_time, payload in rows:
            try:
                plan = json.loads(payload)["setup"]["plan"]
                outcome = resolve_outcome(plan, candle_time, candles)
            except (KeyError, TypeError, ValueError):
                outcome = _unevaluable("plan incomplete or unreadable")
            if outcome is None:
                continue
            con.execute(
                """INSERT INTO outcomes
                   (analysis_id, status, exit_price, exit_time, candles_held,
                    r_gross, r_net, evaluated_at, note)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (analysis_id, outcome["status"], outcome["exit_price"], outcome["exit_time"],
                 outcome["candles_held"], outcome["r_gross"], outcome["r_net"],
                 stamp.isoformat(), outcome["note"]),
            )
            stored += 1
        con.commit()
    finally:
        con.close()
    return stored


def outcome_summary(db_path=None) -> dict:
    con = _connect(db_path)
    try:
        analyses = con.execute(
            "SELECT COUNT(*) FROM analyses WHERE source = 'scheduled'").fetchone()[0]
        setups = con.execute(
            "SELECT COUNT(*) FROM analyses WHERE source = 'scheduled' "
            "AND setup_status LIKE 'VALID_%'").fetchone()[0]
        pending = con.execute("SELECT COUNT(*) " + _PENDING_SQL).fetchone()[0]
        rows = con.execute(
            "SELECT status, COUNT(*), AVG(r_net), SUM(r_net) FROM outcomes GROUP BY status"
        ).fetchall()
    finally:
        con.close()
    by_status = {s: {"n": n, "avg_r_net": avg, "sum_r_net": total} for s, n, avg, total in rows}
    resolved = [v for k, v in by_status.items() if k in RESOLVED]
    return {
        "analyses": analyses,
        "setups": setups,
        "pending": pending,
        "by_status": by_status,
        "n_resolved": sum(v["n"] for v in resolved),
        "sum_r_net": sum((v["sum_r_net"] or 0.0) for v in resolved),
    }
