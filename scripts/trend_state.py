"""Step A of the daily trend alert. NO secrets here. Runs the vendored, hash-pinned trendsetup.py and writes trend_state.json."""
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trend_common as tc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "trend-setup" / "trendsetup.py"


def load_vendor(path=VENDOR):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != tc.PINNED_SHA256:
        raise tc.StateError("the vendored trendsetup.py does not match the pinned sha256")
    spec = importlib.util.spec_from_file_location("trendsetup_pinned", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cut(d, asof_ms):
    """Bars with open time before asof_ms (history is cut at the end only, never at the start)."""
    n = int(np.searchsorted(d["t"], asof_ms, side="left"))
    return {k: (v[:n] if isinstance(v, np.ndarray) else v) for k, v in d.items()}


def last_complete_date(rows):
    seen = {}
    for r in rows:
        seen.setdefault(r.get("date"), set()).add(r.get("symbol"))
    full = [d for d, s in seen.items() if d and set(tc.COINS) <= s]
    return max(full) if full else None


def plan_asofs(last_date, latest_asof_ms):
    if latest_asof_ms % tc.DAY_MS:
        raise tc.StateError("the latest as-of time must be a UTC midnight")
    start = tc.FIRST_ASOF_MS if last_date is None else tc.date_to_ms(last_date) + tc.DAY_MS
    start = max(start, tc.FIRST_ASOF_MS)
    out = list(range(start, latest_asof_ms + 1, tc.DAY_MS))
    if len(out) > tc.MAX_DAYS_PER_RUN:
        raise tc.StateError("the gap since the last logged date is too large; check it manually")
    return out


def build_state(tt, datas, asof_list):
    """datas: FULL-history dict (the whole universe). Only the 7 configured coins reach table_rows,
    so w_eq is a slice of 7-coin capital. Any data problem raises StateError (never a signal)."""
    missing = [s for s in tc.COINS if s not in datas]
    if missing:
        raise tc.StateError(f"coins missing from the data: {missing}")
    days = []
    for asof in asof_list:
        if asof % tc.DAY_MS:
            raise tc.StateError("asof must be a UTC midnight")
        date = tc.day_str(asof)
        sub = {}
        for s in tc.COINS:
            c = cut(datas[s], asof)
            if len(c["t"]) < 2:
                raise tc.StateError(f"{s}: not enough history before {date}")
            sub[s] = c
        rows, n = tt.table_rows(sub, asof)
        by = {r["symbol"]: r for r in rows}
        out = []
        for s in tc.COINS:
            r = by[s]
            if not r["fresh"]:
                raise tc.StateError(f"{s}: no bar for the last closed day before {date}")
            if not r["ready"]:
                raise tc.StateError(f"{s}: warm-up not finished or invalid volatility on {date}")
            if not (tc.is_sig(r["sig"]) and tc.is_sig(r["prev_sig"])):
                raise tc.StateError(f"{s}: signal outside the allowed set on {date}")
            if not (tc.is_num(r["close"]) and r["close"] > 0 and tc.is_num(r["w_eq"]) and 0.0 <= r["w_eq"] <= 1.0):
                raise tc.StateError(f"{s}: invalid close or weight on {date}")
            out.append({"symbol": s, "sig": round(float(r["sig"]), 1), "prev_sig": round(float(r["prev_sig"]), 1),
                        "close": float(r["close"]), "w_eq": float(r["w_eq"]), "states": r["states"],
                        "scale": float(r["scale"]), "data_hash": tt.data_hash(sub[s])[:16]})
        if n != len(tc.COINS):
            raise tc.StateError(f"only {n} of {len(tc.COINS)} coins active on {date}")
        days.append({"date": date, "asof_ms": asof, "rows": out})
    return {"version": getattr(tt, "VERSION", "unknown"), "code_sha256": tc.PINNED_SHA256,
            "coins": list(tc.COINS), "days": days}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-csv", default=None)
    ap.add_argument("--out", default="trend_state.json")
    ap.add_argument("--asof-ms", type=int, default=None)
    a = ap.parse_args(argv)
    try:
        tt = load_vendor()
        rows = []
        if a.log_csv and Path(a.log_csv).exists():
            with open(a.log_csv, newline="") as f:
                rows = list(csv.DictReader(f))
        latest = a.asof_ms if a.asof_ms is not None else int(time.time() * 1000) // tc.DAY_MS * tc.DAY_MS
        asofs = plan_asofs(last_complete_date(rows), latest)
        if asofs:
            datas, _notes = tt.load_universe(latest)
            state = build_state(tt, datas, asofs)
        else:
            state = {"version": getattr(tt, "VERSION", "unknown"), "code_sha256": tc.PINNED_SHA256,
                     "coins": list(tc.COINS), "days": []}
        Path(a.out).write_text(json.dumps(state, indent=1), encoding="utf-8")
    except Exception as exc:
        print(f"ERROR (nothing computed, no signal): {type(exc).__name__}: {exc}")
        return 1
    print(f"days computed: {[d['date'] for d in state['days']]}")
    if state["days"]:
        last = state["days"][-1]
        print(f"signals on {last['date']}:", {r["symbol"]: r["sig"] for r in last["rows"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
