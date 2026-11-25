"""Constants and validation shared by the two steps of the daily trend alert.
No third-party imports on purpose: the notify step (which holds the secrets) has no numpy."""
import calendar
import math
import re
import time

PINNED_SHA256 = "e5e17e3de5d8ed36b33712726cfe81256a0ee7ec8ad66cf87f2885fd3fc2bc6f"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "LTCUSDT", "TRXUSDT"]
DAY_MS = 86_400_000
FIRST_ASOF_MS = 1_795_305_600_000  # 2026-11-22T00:00:00Z, equal to T0_MS in the pinned file (tested)
ALLOWED_SIGS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
MAX_DAYS_PER_RUN = 60
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HASH = re.compile(r"^[0-9a-f]{16}$")


class StateError(Exception):
    """Bad or unsafe input. The run must fail (red) and send nothing."""


def day_str(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def date_to_ms(text):
    if not isinstance(text, str) or not _DATE.match(text):
        raise StateError(f"bad date {text!r}")
    try:
        return calendar.timegm(time.strptime(text, "%Y-%m-%d")) * 1000
    except ValueError:
        raise StateError(f"bad date {text!r}")


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def is_sig(x):
    return is_num(x) and any(abs(float(x) - a) < 1e-9 for a in ALLOWED_SIGS)


def validate_state(obj):
    """Strict validation of trend_state.json (treated as untrusted data). Returns a clean list of days."""
    if not isinstance(obj, dict):
        raise StateError("state is not an object")
    if obj.get("code_sha256") != PINNED_SHA256:
        raise StateError("state was not produced by the pinned code")
    if obj.get("coins") != COINS:
        raise StateError("unexpected coin list")
    days = obj.get("days")
    if not isinstance(days, list) or len(days) > MAX_DAYS_PER_RUN:
        raise StateError("days missing or too many")
    out, last = [], None
    for d in days:
        if not isinstance(d, dict):
            raise StateError("bad day entry")
        ms = date_to_ms(d.get("date"))
        if d.get("asof_ms") != ms:
            raise StateError("asof_ms does not match the date")
        if last is not None and ms <= last:
            raise StateError("dates must be strictly ascending")
        last = ms
        rows = d.get("rows")
        if not isinstance(rows, list) or [r.get("symbol") if isinstance(r, dict) else None for r in rows] != COINS:
            raise StateError("rows must be exactly the 7 coins in order")
        clean = []
        for r in rows:
            if not (is_sig(r.get("sig")) and is_sig(r.get("prev_sig"))):
                raise StateError("signal outside the allowed set")
            close, w = r.get("close"), r.get("w_eq")
            if not is_num(close) or close <= 0:
                raise StateError("bad close")
            if not is_num(w) or not 0.0 <= w <= 1.0:
                raise StateError("bad weight")
            h = r.get("data_hash")
            if not (isinstance(h, str) and _HASH.match(h)):
                raise StateError("bad data hash")
            clean.append({"symbol": r["symbol"], "sig": round(float(r["sig"]), 1),
                          "prev_sig": round(float(r["prev_sig"]), 1), "close": float(close),
                          "w_eq": float(w), "data_hash": h})
        out.append({"date": d["date"], "asof_ms": ms, "rows": clean})
    return out
