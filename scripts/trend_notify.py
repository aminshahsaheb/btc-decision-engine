"""Step B of the daily trend alert (holds the Telegram secrets). Reads trend_state.json as UNTRUSTED data, validates it,
logs first (write-ahead: PENDING is pushed before the send), then sends. A timeout is UNCERTAIN and is never resent."""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alerts as al  # noqa: E402
import trend_common as tc  # noqa: E402

DAILY_FIELDS = ["date", "symbol", "signal", "prev_signal", "close", "w_eq", "code_sha", "data_hash", "logged_utc"]
MSG_FIELDS = ["key", "state", "state_utc", "base_date", "asof_date", "targets", "summary", "note"]
PENDING_RECOVERY_MS = 30 * 60 * 1000
OPEN_STATE_REPORT_MS = 3600 * 1000
MAX_TEXT = 3800
MAX_FLIPS = 12


def append_csv(path, fields, rows):
    path = Path(path)
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if new:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def latest_msgs(rows):
    out = {}
    for r in rows:
        out[r["key"]] = r
    return out


def last_sent(msgs):
    best = None
    for r in msgs.values():
        if r["state"] == "SENT" and (best is None or r["asof_date"] > best["asof_date"]):
            best = r
    if best is None:
        return {}, None
    return json.loads(best["targets"]), best["asof_date"]


def complete_dates(daily_rows):
    by = {}
    for r in daily_rows:
        by.setdefault(r["date"], {})[r["symbol"]] = r
    return {d: v for d, v in by.items() if set(tc.COINS) <= set(v)}


def label(old, new):
    if new > old + 1e-9:
        return "ENTER" if old < 1e-9 else "ADD"
    if new < old - 1e-9:
        return "EXIT TO CASH" if new < 1e-9 else "REDUCE"
    return ""


def intermediate_flips(by_date, base_date, latest):
    dates = sorted(by_date)
    out = []
    for i, d in enumerate(dates):
        if i == 0 or d >= latest or (base_date is not None and d <= base_date):
            continue
        prev = by_date[dates[i - 1]]
        for s in tc.COINS:
            a, b = float(prev[s]["signal"]), float(by_date[d][s]["signal"])
            if abs(a - b) > 1e-9:
                out.append((d, s, a, b))
    return out


def compose(latest, base_date, changes, flips, table, uncertain_dates):
    lines = [f"هشدار روند روزانه — UNPROVEN (ثبت کاغذی از {tc.day_str(tc.FIRST_ASOF_MS)})",
             f"تاریخ تصمیم: {latest} UTC (بر اساس close کندل روزانهٔ بسته‌شدهٔ روز قبل)",
             "فقط لانگ یا نقد؛ هرگز شورت.",
             f"تغییر نسبت به آخرین پیام ارسال‌شده ({base_date or 'شروع از نقد'}):"]
    for sym, old, new, w in changes:
        lines.append(f"{label(old, new)} {sym}: {old:.1f} → {new:.1f} | هدف {w * 100:.1f}% از سرمایهٔ ۷‌کوینی")
    if uncertain_dates:
        lines.append("توجه: وضعیت ارسال پیام‌های " + "، ".join(uncertain_dates) +
                     " نامعلوم است؛ تغییرهای آن‌ها هم در این خالص آمده.")
    if flips:
        lines.append("تغییرهای میانی:")
        for d, sym, a, b in flips[:MAX_FLIPS]:
            lines.append(f"{d}: {sym} {a:.1f}→{b:.1f}")
        if len(flips) > MAX_FLIPS:
            lines.append(f"... و {len(flips) - MAX_FLIPS} مورد دیگر")
    lines.append("جدول ۷ کوین (سیگنال | هدف از سرمایهٔ ۷‌کوینی):")
    for sym, sig, w in table:
        lines.append(f"{sym}: {sig:.1f} | {w * 100:.1f}%")
    lines.append("مدل کاغذی در open روز بعد (۰۰:۰۰ UTC) وارد می‌شود؛ این پیام دیرتر می‌رسد و قیمت فعلی فرق دارد. "
                 "اندازهٔ موقعیت واقعی را خودت با سرمایه و ریسک مجاز تعیین کن؛ این‌ها فقط سهم هدف مدل‌اند و مزیتی اثبات نشده است.")
    return "\n".join(lines)[:MAX_TEXT]


def run_notify(days, log_dir, now_ms, send, persist):
    log_dir = Path(log_dir)
    daily_path, msgs_path = log_dir / "trend_daily.csv", log_dir / "trend_msgs.csv"
    summary = {"new_days": 0, "message": "none", "recovered": 0, "uncertain": 0,
               "open_pending": 0, "open_uncertain": 0}
    daily = al.read_csv(daily_path)
    msgs = latest_msgs(al.read_csv(msgs_path))
    msg_rows = []
    for key, r in list(msgs.items()):
        if r["state"] == "PENDING" and now_ms - al.parse_utc(r["state_utc"]) > PENDING_RECOVERY_MS:
            row = dict(r, state="UNCERTAIN", state_utc=al.utc_iso(now_ms), note="recovered: no final state was saved")
            msg_rows.append(row)
            msgs[key] = row
            summary["recovered"] += 1
    logged = {(r["date"], r["symbol"]) for r in daily}
    new_rows = []
    for day in days:
        for r in day["rows"]:
            k = (day["date"], r["symbol"])
            if k in logged:
                continue
            logged.add(k)
            new_rows.append({"date": day["date"], "symbol": r["symbol"], "signal": r["sig"],
                             "prev_signal": r["prev_sig"], "close": r["close"], "w_eq": r["w_eq"],
                             "code_sha": tc.PINNED_SHA256, "data_hash": r["data_hash"],
                             "logged_utc": al.utc_iso(now_ms)})
    summary["new_days"] = len({r["date"] for r in new_rows})
    by_date = complete_dates(daily + new_rows)
    pending, text, key = None, None, None
    if by_date:
        latest = max(by_date)
        base_targets, base_date = last_sent(msgs)
        cur = {s: float(by_date[latest][s]["signal"]) for s in tc.COINS}
        changed = [s for s in tc.COINS if abs(cur[s] - float(base_targets.get(s, 0.0))) > 1e-9]
        key = f"TREND|{latest}"
        if changed and key not in msgs:
            changes = [(s, float(base_targets.get(s, 0.0)), cur[s], float(by_date[latest][s]["w_eq"])) for s in changed]
            table = [(s, cur[s], float(by_date[latest][s]["w_eq"])) for s in tc.COINS]
            unc = sorted(r["asof_date"] for r in msgs.values()
                         if r["state"] == "UNCERTAIN" and r["asof_date"] > (base_date or ""))
            text = compose(latest, base_date, changes, intermediate_flips(by_date, base_date, latest), table, unc)
            pending = {"key": key, "state": "PENDING", "state_utc": al.utc_iso(now_ms), "base_date": base_date or "",
                       "asof_date": latest, "targets": json.dumps(cur),
                       "summary": "; ".join(f"{label(o, n)} {s} {o:.1f}->{n:.1f}" for s, o, n, _w in changes),
                       "note": ""}
    if new_rows:
        append_csv(daily_path, DAILY_FIELDS, new_rows)
    rows_out = msg_rows + ([pending] if pending else [])
    if rows_out:
        append_csv(msgs_path, MSG_FIELDS, rows_out)
    if new_rows or rows_out:
        persist("trend: daily rows and pending state")
    if pending:
        ok, detail = send(text)
        final = dict(pending, state="SENT" if ok else "UNCERTAIN", state_utc=al.utc_iso(now_ms), note="" if ok else detail)
        append_csv(msgs_path, MSG_FIELDS, [final])
        persist(f"trend: {final['state']} {key}")
        msgs[key] = final
        summary["message"] = final["state"]
        if not ok:
            summary["uncertain"] += 1
    for r in msgs.values():
        if now_ms - al.parse_utc(r["state_utc"]) > OPEN_STATE_REPORT_MS:
            if r["state"] == "PENDING":
                summary["open_pending"] += 1
            elif r["state"] == "UNCERTAIN":
                summary["open_uncertain"] += 1
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="trend_state.json")
    ap.add_argument("--log-dir", default="log")
    a = ap.parse_args(argv)
    try:
        days = tc.validate_state(json.loads(Path(a.state).read_text(encoding="utf-8")))
    except (OSError, ValueError, tc.StateError) as exc:
        print(f"ERROR: state file rejected ({type(exc).__name__}: {exc}); nothing logged, nothing sent")
        return 1
    if not os.environ.get("TOKEN") or not os.environ.get("CHAT"):
        print("ERROR: Telegram credentials are missing; nothing logged, nothing sent")
        return 2
    log_dir = Path(a.log_dir)
    try:
        summary = run_notify(days, log_dir, int(time.time() * 1000), al.telegram_send, al.make_persist(log_dir))
    except al.PersistError as exc:
        print(f"ERROR saving the log ({exc}); the run stops here")
        return 1
    print("summary:", summary)
    if summary["uncertain"] or summary["recovered"]:
        print("RED: an UNCERTAIN delivery state exists; check trend_msgs.csv on the alert-log branch")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
