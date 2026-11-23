"""BTCUSDT attention alerts (UNVALIDATED). Rules: docs/ALERT_RULES_v2.md (v1 is frozen). No trading edge is claimed."""
import calendar
import csv
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RULES_VERSION = "v2"
SPOT = "https://data-api.binance.vision/api/v3/klines"
TFS = ["15m", "1h", "4h", "1d", "1w", "1M"]
STATE_EVENT_TFS = ["1d", "1w", "1M"]
MAX_AGE_MS = {"15m": 3600e3, "1h": 3 * 3600e3, "4h": 9 * 3600e3,
              "1d": 50 * 3600e3, "1w": 9 * 86400e3, "1M": 33 * 86400e3}
Z_BAND = 0.5
SCAN_1H = 24
SCAN_STATE = 2
COOLDOWN_MS = 24 * 3600 * 1000
MAX_SEND_AGE_MS = 12 * 3600 * 1000
PENDING_RECOVERY_MS = 30 * 60 * 1000
SEND_TIMEOUT_S = 60
COUNTING_STATES = ("PENDING", "UNCERTAIN", "SENT", "STALE")
V2_FIELDS = ["key", "rules_version", "type", "side", "bar_open_ms", "close_ms", "ref", "level",
             "atr1d", "stop", "target", "state", "state_utc", "age_min", "note"]
NAMES = {1: "صعودی ▲", 0: "خنثی ▬", -1: "نزولی ▼"}


class PersistError(Exception):
    pass


def get(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "btc-alerts/0.2"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except Exception as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise last


def klines(interval, now_ms, limit=400):
    rows = get(f"{SPOT}?symbol=BTCUSDT&interval={interval}&limit={limit}")
    out = []
    for r in rows:
        if r[6] < now_ms:
            out.append({"open_ms": int(r[0]), "close_ms": int(r[6]), "o": float(r[1]),
                        "h": float(r[2]), "l": float(r[3]), "c": float(r[4])})
    return out


def ema20(closes):
    e = closes[0]
    out = [e]
    for c in closes[1:]:
        e += (2.0 / 21.0) * (c - e)
        out.append(e)
    return out


def atr14(bars):
    n = len(bars)
    out = [None] * n
    if n <= 14:
        return out
    tr = [bars[0]["h"] - bars[0]["l"]]
    for i in range(1, n):
        pc = bars[i - 1]["c"]
        tr.append(max(bars[i]["h"] - bars[i]["l"], abs(bars[i]["h"] - pc), abs(bars[i]["l"] - pc)))
    a = sum(tr[1:15]) / 14.0
    out[14] = a
    for i in range(15, n):
        a = (a * 13.0 + tr[i]) / 14.0
        out[i] = a
    return out


def states(bars):
    e = ema20([b["c"] for b in bars])
    a = atr14(bars)
    out = []
    for i, b in enumerate(bars):
        if i < 20 or a[i] is None or a[i] <= 0:
            out.append(None)
            continue
        z = (b["c"] - e[i]) / a[i]
        out.append(1 if z > Z_BAND else (-1 if z < -Z_BAND else 0))
    return out


def load(now_ms):
    data = {}
    for tf in TFS:
        bars = klines(tf, now_ms)
        if len(bars) < 40:
            raise RuntimeError(f"too few closed bars for {tf}")
        if now_ms - bars[-1]["close_ms"] > MAX_AGE_MS[tf]:
            raise RuntimeError(f"stale data for {tf}")
        if any(min(b["o"], b["h"], b["l"], b["c"]) <= 0 for b in bars):
            raise RuntimeError(f"non-positive price in {tf}")
        data[tf] = {"bars": bars, "state": states(bars), "atr": atr14(bars)}
        if data[tf]["state"][-1] is None:
            raise RuntimeError(f"no valid state for {tf}")
    return data


def detect(data):
    events = []
    for tf in STATE_EVENT_TFS:
        bars, st = data[tf]["bars"], data[tf]["state"]
        for i in range(max(1, len(bars) - SCAN_STATE), len(bars)):
            if st[i] is not None and st[i - 1] is not None and st[i] != st[i - 1]:
                events.append({"type": "STATE", "side": tf, "bar_open_ms": bars[i]["open_ms"],
                               "close_ms": bars[i]["close_ms"], "ref": bars[i]["c"], "level": "",
                               "atr": "", "stop": "", "target": "", "from": st[i - 1], "to": st[i],
                               "note": f"{st[i - 1]}->{st[i]}",
                               "key": f"STATE|{tf}|{bars[i]['open_ms']}"})
    daily, hourly, atr_d = data["1d"]["bars"], data["1h"]["bars"], data["1d"]["atr"]
    for j in range(max(1, len(hourly) - SCAN_1H), len(hourly)):
        h, prev = hourly[j], hourly[j - 1]
        done = [k for k, d in enumerate(daily) if d["close_ms"] < h["close_ms"]]
        if len(done) < 21:
            continue
        last20 = [daily[k] for k in done[-20:]]
        hi = max(d["h"] for d in last20)
        lo = min(d["l"] for d in last20)
        atr = atr_d[done[-1]]
        if atr is None or atr <= 0:
            continue
        if prev["c"] <= hi < h["c"]:
            side, level = "LONG", hi
        elif prev["c"] >= lo > h["c"]:
            side, level = "SHORT", lo
        else:
            continue
        ref = h["c"]
        stop = ref - atr if side == "LONG" else ref + atr
        target = ref + 2 * atr if side == "LONG" else ref - 2 * atr
        events.append({"type": "BREAK20D", "side": side, "bar_open_ms": h["open_ms"],
                       "close_ms": h["close_ms"], "ref": ref, "level": level, "atr": atr,
                       "stop": stop, "target": target, "note": "",
                       "key": f"BREAK20D|{side}|{h['open_ms']}"})
    return sorted(events, key=lambda e: e["bar_open_ms"])


def utc(ms):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000))


def utc_iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))


def parse_utc(text):
    return calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%M:%SZ")) * 1000


def fmt_age(ms):
    minutes = max(0, ms) / 60000.0
    return f"{minutes:.0f} دقیقه" if minutes < 90 else f"{minutes / 60:.1f} ساعت"


def table_text(data):
    lines = ["وضعیت تایم‌فریم‌ها (اطلاعاتی، بدون ادعای مزیت)"]
    total = 0
    for tf in TFS:
        s = data[tf]["state"][-1]
        lines.append(f"{tf}: {NAMES[s]}")
        total += s
    lines.append(f"جمع: {total:+d} از {len(TFS)}")
    lines.append(f"قیمت: {data['1h']['bars'][-1]['c']:.1f} (اسپات BTCUSDT، آخرین کندل ۱ ساعته بسته‌شده)")
    return "\n".join(lines)


def message(ev, data, now_ms):
    age = fmt_age(now_ms - ev["close_ms"])
    if ev["type"] == "STATE":
        return (f"تغییر وضعیت تایم‌فریم {ev['side']} (اطلاعاتی)\n"
                f"{NAMES[ev['from']]} ← {NAMES[ev['to']]}\n"
                f"کندل بسته‌شده تا {utc(ev['close_ms'])} UTC | سن هشدار: {age}\n\n" + table_text(data))
    side = "لانگ" if ev["side"] == "LONG" else "شورت"
    lvl = "سقف" if ev["side"] == "LONG" else "کف"
    return (f"⚠️ شکست ۲۰ روزه — {side} (تأییدنشده، قاعده‌های v2)\n"
            f"BTCUSDT اسپات | کندل ۱ ساعته تا {utc(ev['close_ms'])} UTC | سن هشدار: {age}\n"
            f"قیمت مرجع (close همان کندل): {ev['ref']:.1f} | {lvl} ۲۰ روز: {ev['level']:.1f}\n"
            f"استاپ: {ev['stop']:.1f} | هدف: {ev['target']:.1f} (R = {ev['atr'] / ev['ref'] * 100:.2f}% قیمت)\n"
            "قیمت فعلی ممکن است با مرجع فرق کند؛ قبل از هر تصمیم نمودار را ببین.\n"
            "این هشدار مزیت اثبات‌شده ندارد و فقط ثبت می‌شود تا بعداً سنجیده شود. "
            "حجم را با ماشین‌حساب حساب کن؛ ریسک هر معامله حداکثر ۰.۵٪.")


def telegram_send(text):
    """Returns (ok, detail). Only an explicit ok=true answer is success. detail never contains the token."""
    token, chat = os.environ.get("TOKEN"), os.environ.get("CHAT")
    if not token or not chat:
        return False, "no credentials"
    payload = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
    try:
        with urllib.request.urlopen(request, timeout=SEND_TIMEOUT_S) as resp:
            body = json.load(resp)
        if body.get("ok") is True:
            return True, ""
        return False, "telegram answered ok=false"
    except Exception as exc:
        code = getattr(exc, "code", "")
        return False, f"{type(exc).__name__} {code}".strip()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def append_rows(path, rows):
    path = Path(path)
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=V2_FIELDS)
        if new:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_row(ev, state, now_ms, note=""):
    return {"key": ev["key"], "rules_version": RULES_VERSION, "type": ev["type"], "side": ev["side"],
            "bar_open_ms": ev["bar_open_ms"], "close_ms": ev["close_ms"], "ref": ev["ref"],
            "level": ev["level"], "atr1d": ev["atr"], "stop": ev["stop"], "target": ev["target"],
            "state": state, "state_utc": utc_iso(now_ms),
            "age_min": round((now_ms - ev["close_ms"]) / 60000), "note": note or ev.get("note", "")}


def latest_states(rows):
    out = {}
    for r in rows:
        out[r["key"]] = r
    return out


def counting_rows(v1_rows, latest):
    rows = [{"type": r.get("type"), "side": r.get("side"), "bar_open_ms": r.get("bar_open_ms")}
            for r in v1_rows]
    rows += [r for r in latest.values() if r["state"] in COUNTING_STATES]
    return rows


def in_cooldown(ev, rows):
    for r in rows:
        if r.get("type") == "BREAK20D" and r.get("side") == ev["side"]:
            if abs(ev["bar_open_ms"] - int(r["bar_open_ms"])) < COOLDOWN_MS:
                return True
    return False


def process_events(events, v1_rows, v2_path, now_ms, send, persist):
    """Write-ahead state machine: PENDING is saved and pushed BEFORE the send; the outcome is SENT or UNCERTAIN.
    A timeout or any non-success answer is UNCERTAIN and is never resent."""
    summary = {"detected": len(events), "known": 0, "suppressed": 0, "stale": 0,
               "sent": 0, "uncertain": 0, "recovered": 0}
    latest = latest_states(read_csv(v2_path))
    fresh = []
    for key, r in list(latest.items()):
        if r["state"] == "PENDING" and now_ms - parse_utc(r["state_utc"]) > PENDING_RECOVERY_MS:
            row = dict(r, state="UNCERTAIN", state_utc=utc_iso(now_ms),
                       note="recovered: no final state was saved")
            fresh.append(row)
            latest[key] = row
            summary["recovered"] += 1
    known = {r["key"] for r in v1_rows} | set(latest)
    to_send = []
    for ev in events:
        if ev["key"] in known:
            summary["known"] += 1
            continue
        if ev["type"] == "BREAK20D" and in_cooldown(ev, counting_rows(v1_rows, latest)):
            summary["suppressed"] += 1
            continue
        known.add(ev["key"])
        if now_ms - ev["close_ms"] > MAX_SEND_AGE_MS:
            row = make_row(ev, "STALE", now_ms, "older than the send limit; logged, not sent")
            summary["stale"] += 1
        else:
            row = make_row(ev, "PENDING", now_ms)
            to_send.append(ev)
        fresh.append(row)
        latest[ev["key"]] = row
    if fresh:
        append_rows(v2_path, fresh)
        persist("alerts v2: pending, stale and recovered rows")
    for ev in to_send:
        ok, detail = send(ev)
        note = ev.get("note", "") if ok else (ev.get("note", "") + " " + detail).strip()
        row = make_row(ev, "SENT" if ok else "UNCERTAIN", now_ms, note)
        summary["sent" if ok else "uncertain"] += 1
        latest[ev["key"]] = row
        append_rows(v2_path, [row])
        persist(f"alerts v2: {row['state']} {ev['key']}")
    return summary


def _git(log_dir, *args):
    return subprocess.run(["git", "-C", str(log_dir), *args], capture_output=True, text=True)


def make_persist(log_dir):
    def persist(msg):
        _git(log_dir, "add", "-A")
        if _git(log_dir, "diff", "--cached", "--quiet").returncode == 0:
            return
        if _git(log_dir, "commit", "-q", "-m", msg).returncode != 0:
            raise PersistError("commit failed")
        for attempt in range(4):
            if _git(log_dir, "push", "-q", "origin", "alert-log").returncode == 0:
                return
            time.sleep(2 * (attempt + 1))
            if _git(log_dir, "fetch", "-q", "origin", "alert-log").returncode == 0:
                if _git(log_dir, "rebase", "origin/alert-log").returncode != 0:
                    _git(log_dir, "rebase", "--abort")
                    raise PersistError("rebase conflict")
        raise PersistError("push failed after retries")
    return persist


def selftest():
    e = ema20([10.0, 20.0])
    assert e[0] == 10.0 and abs(e[1] - (10.0 + 10.0 * 2 / 21)) < 1e-12
    flat = [{"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0} for _ in range(40)]
    a = atr14(flat)
    assert a[13] is None and abs(a[14] - 2.0) < 1e-12 and abs(a[39] - 2.0) < 1e-12
    up = [{"o": 100.0, "h": 101.0 + i, "l": 99.0 + i, "c": 100.0 + i} for i in range(40)]
    down = [{"o": 100.0, "h": 101.0 - i, "l": 99.0 - i, "c": 100.0 - i} for i in range(40)]
    assert states(up)[-1] == 1 and states(down)[-1] == -1
    assert states(flat)[-1] == 0 and states(flat)[19] is None
    D, H = 86400000, 3600000
    daily = [{"open_ms": k * D, "close_ms": (k + 1) * D - 1, "o": 95.0, "h": 100.0, "l": 90.0, "c": 95.0}
             for k in range(25)]
    closes = [95.0, 95.0, 95.0, 96.0, 100.0, 102.0]
    hourly = [{"open_ms": 25 * D + i * H, "close_ms": 25 * D + (i + 1) * H - 1,
               "o": c, "h": c + 1, "l": c - 1, "c": c} for i, c in enumerate(closes)]
    week = [{"open_ms": k * 7 * D, "close_ms": (k + 1) * 7 * D - 1, "o": 1.0, "h": 1.0, "l": 1.0, "c": 1.0}
            for k in range(3)]
    data = {"1d": {"bars": daily, "state": [None] * 25, "atr": atr14(daily)},
            "1h": {"bars": hourly, "state": [], "atr": []},
            "1w": {"bars": week, "state": [0, 0, 1], "atr": [None] * 3},
            "1M": {"bars": week, "state": [0, 0, 0], "atr": [None] * 3}}
    events = detect(data)
    assert sorted(ev["type"] for ev in events) == ["BREAK20D", "STATE"], events
    brk = [ev for ev in events if ev["type"] == "BREAK20D"][0]
    assert brk["side"] == "LONG" and brk["ref"] == 102.0 and brk["level"] == 100.0
    assert abs(brk["stop"] - 92.0) < 1e-9 and abs(brk["target"] - 122.0) < 1e-9
    near = [{"type": "BREAK20D", "side": "LONG", "bar_open_ms": str(brk["bar_open_ms"] - 3 * H)}]
    far = [{"type": "BREAK20D", "side": "LONG", "bar_open_ms": str(brk["bar_open_ms"] - 25 * H)}]
    other = [{"type": "BREAK20D", "side": "SHORT", "bar_open_ms": str(brk["bar_open_ms"] - 3 * H)}]
    assert in_cooldown(brk, near) and not in_cooldown(brk, far) and not in_cooldown(brk, other)


def main():
    args = sys.argv[1:]
    mode = args[0] if args else "status"
    if mode == "selftest":
        selftest()
        print("SELFTEST: PASS")
        return 0
    now_ms = int(time.time() * 1000)
    log_path = Path(args[args.index("--log") + 1]) if "--log" in args else None
    try:
        data = load(now_ms)
    except Exception as exc:
        print(f"ERROR loading data (nothing sent): {type(exc).__name__}: {exc}")
        return 1
    if mode == "status":
        ok, detail = telegram_send(table_text(data))
        print(table_text(data))
        print("telegram: sent" if ok else f"telegram: not sent ({detail})")
        return 0
    if mode != "run" or log_path is None:
        print("usage: alerts.py status | alerts.py run --log PATH | alerts.py selftest")
        return 2
    if not os.environ.get("TOKEN") or not os.environ.get("CHAT"):
        print("ERROR: Telegram credentials are missing; nothing logged, nothing sent")
        return 2
    log_dir = log_path.parent
    events = detect(data)

    def send(ev):
        return telegram_send(message(ev, data, now_ms))

    try:
        summary = process_events(events, read_csv(log_path), log_dir / "alerts_v2.csv", now_ms,
                                 send, make_persist(log_dir))
    except PersistError as exc:
        print(f"ERROR saving the log ({exc}); the run stops here")
        return 1
    print("summary:", summary)
    if summary["uncertain"] or summary["recovered"]:
        print("RED: at least one alert has an UNCERTAIN delivery state; check alerts_v2.csv on the alert-log branch")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
