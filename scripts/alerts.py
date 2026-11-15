"""BTCUSDT attention alerts (UNVALIDATED). Rules: docs/ALERT_RULES_v1.md. No trading edge is claimed."""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SPOT = "https://data-api.binance.vision/api/v3/klines"
TFS = ["15m", "1h", "4h", "1d", "1w", "1M"]
STATE_EVENT_TFS = ["1d", "1w", "1M"]
MAX_AGE_MS = {"15m": 3600e3, "1h": 3 * 3600e3, "4h": 9 * 3600e3,
              "1d": 50 * 3600e3, "1w": 9 * 86400e3, "1M": 33 * 86400e3}
Z_BAND = 0.5
SCAN_1H = 4
SCAN_STATE = 2
COOLDOWN_MS = 24 * 3600 * 1000
LOG_FIELDS = ["key", "type", "side", "bar_open_ms", "ref", "level", "atr1d", "stop", "target", "sent_utc"]
NAMES = {1: "صعودی ▲", 0: "خنثی ▬", -1: "نزولی ▼"}
NOW_MS = int(time.time() * 1000)


def get(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "btc-alerts/0.1"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except Exception as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise last


def klines(interval, limit=400):
    rows = get(f"{SPOT}?symbol=BTCUSDT&interval={interval}&limit={limit}")
    out = []
    for r in rows:
        if r[6] < NOW_MS:
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


def load():
    data = {}
    for tf in TFS:
        bars = klines(tf)
        if len(bars) < 40:
            raise RuntimeError(f"too few closed bars for {tf}")
        if NOW_MS - bars[-1]["close_ms"] > MAX_AGE_MS[tf]:
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
        for i in range(len(bars) - SCAN_STATE, len(bars)):
            if i >= 1 and st[i] is not None and st[i - 1] is not None and st[i] != st[i - 1]:
                events.append({"type": "STATE", "side": tf, "bar_open_ms": bars[i]["open_ms"],
                               "close_ms": bars[i]["close_ms"], "ref": bars[i]["c"], "level": "",
                               "atr": "", "stop": "", "target": "", "from": st[i - 1], "to": st[i],
                               "key": f"STATE|{tf}|{bars[i]['open_ms']}"})
    daily, hourly, atr_d = data["1d"]["bars"], data["1h"]["bars"], data["1d"]["atr"]
    for j in range(len(hourly) - SCAN_1H, len(hourly)):
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
                       "stop": stop, "target": target,
                       "key": f"BREAK20D|{side}|{h['open_ms']}"})
    return sorted(events, key=lambda e: e["bar_open_ms"])


def in_cooldown(ev, rows):
    for r in rows:
        if r["type"] == "BREAK20D" and r["side"] == ev["side"]:
            gap = ev["bar_open_ms"] - int(r["bar_open_ms"])
            if 0 < gap < COOLDOWN_MS:
                return True
    return False


def utc(ms):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000))


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


def message(ev, data):
    if ev["type"] == "STATE":
        return (f"تغییر وضعیت تایم‌فریم {ev['side']} (اطلاعاتی)\n"
                f"{NAMES[ev['from']]} ← {NAMES[ev['to']]}\n"
                f"کندل بسته‌شده تا {utc(ev['close_ms'])} UTC\n\n" + table_text(data))
    side = "لانگ" if ev["side"] == "LONG" else "شورت"
    lvl = "سقف" if ev["side"] == "LONG" else "کف"
    return (f"⚠️ شکست ۲۰ روزه — {side} (تأییدنشده)\n"
            f"BTCUSDT اسپات | کندل ۱ ساعته تا {utc(ev['close_ms'])} UTC\n"
            f"قیمت: {ev['ref']:.1f} | {lvl} ۲۰ روز: {ev['level']:.1f}\n"
            f"استاپ: {ev['stop']:.1f} | هدف: {ev['target']:.1f} (R = {ev['atr'] / ev['ref'] * 100:.2f}% قیمت)\n"
            "این هشدار مزیت اثبات‌شده ندارد و فقط ثبت می‌شود تا بعداً سنجیده شود. "
            "حجم را با ماشین‌حساب حساب کن؛ ریسک هر معامله حداکثر ۰.۵٪.")


def telegram(text):
    token, chat = os.environ.get("TOKEN"), os.environ.get("CHAT")
    if not token or not chat:
        print("telegram: skipped (no credentials)")
        return False
    payload = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
    try:
        urllib.request.urlopen(request, timeout=20).read()
        return True
    except Exception as exc:
        print(f"telegram: FAILED {type(exc).__name__}")
        return False


def read_log(path):
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def append_log(path, row):
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


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
    assert in_cooldown(brk, [{"type": "BREAK20D", "side": "LONG", "bar_open_ms": str(brk["bar_open_ms"] - 3 * H)}])
    assert not in_cooldown(brk, [{"type": "BREAK20D", "side": "LONG", "bar_open_ms": str(brk["bar_open_ms"] - 25 * H)}])
    assert not in_cooldown(brk, [{"type": "BREAK20D", "side": "SHORT", "bar_open_ms": str(brk["bar_open_ms"] - 3 * H)}])


def main():
    args = sys.argv[1:]
    mode = args[0] if args else "status"
    if mode == "selftest":
        selftest()
        print("SELFTEST: PASS")
        return 0
    log_path = Path(args[args.index("--log") + 1]) if "--log" in args else None
    try:
        data = load()
    except Exception as exc:
        print(f"ERROR loading data (nothing sent): {type(exc).__name__}: {exc}")
        return 1
    if mode == "status":
        text = table_text(data)
        print(text)
        print("telegram: sent" if telegram(text) else "telegram: not sent")
        return 0
    if mode != "run" or log_path is None:
        print("usage: alerts.py status | alerts.py run --log PATH | alerts.py selftest")
        return 2
    rows = read_log(log_path)
    keys = {r["key"] for r in rows}
    events = detect(data)
    sent = suppressed = 0
    for ev in events:
        if ev["key"] in keys:
            continue
        if ev["type"] == "BREAK20D" and in_cooldown(ev, rows):
            suppressed += 1
            continue
        if not telegram(message(ev, data)):
            print("send failed; stopping (nothing logged for this event)")
            return 1
        row = {"key": ev["key"], "type": ev["type"], "side": ev["side"], "bar_open_ms": ev["bar_open_ms"],
               "ref": ev["ref"], "level": ev["level"], "atr1d": ev["atr"], "stop": ev["stop"],
               "target": ev["target"], "sent_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        append_log(log_path, row)
        rows.append(row)
        keys.add(ev["key"])
        sent += 1
    print(f"events detected={len(events)} sent={sent} suppressed_by_cooldown={suppressed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
