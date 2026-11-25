#!/usr/bin/env python3
"""Trend Setup v0 reference tool (specs/trend-setup/SETUP_TREND_v0.md is the authority; this file only implements it).

The rule (frozen): for every coin of a fixed universe, five Donchian-channel states (N = 10, 20, 30, 55, 100 days; enter long when the daily close is
above the previous N-day high, exit when it is below the previous N//2-day low) are averaged into a signal s in {0, 0.2, ..., 1}. The coin's weight
is s x min(1, 0.50 / 30-day annualised volatility). The portfolio is long-or-flat, equal weight over the active coins of the universe.
Decisions use the CLOSE of bar i; they are held from the OPEN of bar i+1 (open-to-open returns). Cost 0.08% of traded notional per side (assumption).

Commands:  table  = today's signal table from the last closed daily bar;   paper = deterministic paper track since T0 (recomputed from public data).
Nothing here is validated: tests are synthetic and by the same author, and show the code does what it says, not that the rule earns money.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

VERSION = "trendsetup-v0"
DAY_MS = 86_400_000
START_MS = 1_502_928_000_000  # 2017-08-17T00:00:00Z (data start; warm-up only)
T0_MS = 1_795_305_600_000  # 2026-11-22T00:00:00Z: first bar that counts for the paper track (decided at the close of 2026-11-21)
HOSTS = ("data-api.binance.vision", "api.binance.com")
UNIVERSE = (
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "LTCUSDT", "TRXUSDT", "LINKUSDT", "XLMUSDT", "ETCUSDT", "NEOUSDT",
    "SOLUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "ATOMUSDT", "UNIUSDT", "AAVEUSDT", "FILUSDT", "ALGOUSDT", "VETUSDT",
    "NEARUSDT", "XTZUSDT", "ZECUSDT", "DASHUSDT", "HBARUSDT",
)
ENS_N = (10, 20, 30, 55, 100)
TARGET_VOL, VOL_WINDOW, ANN, WARMUP_BARS, MIN_ACTIVE, C_SIDE = 0.50, 30, 365.0, 260, 3, 0.0008
MIN_COINS, MAX_MISSING_DAYS = 8, 5


# ----------------------------------------------------------------------------- data (same fetch/validation rules as Search Lab v1)
class DataError(Exception):
    pass


def default_http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "btc-signal-lab-trendsetup/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def _page(symbol, start_ms, end_ms, http_get, hosts, retries, sleep):
    last = None
    for host in hosts:
        url = f"https://{host}/api/v3/klines?symbol={symbol}&interval=1d&startTime={start_ms}&endTime={end_ms - 1}&limit=1000"
        for attempt in range(retries):
            try:
                data = json.loads(http_get(url))
                if isinstance(data, list):
                    return data
                last = f"{host}: unexpected payload {str(data)[:80]}"
            except (urllib.error.URLError, OSError, ValueError) as e:
                last = f"{host}: {type(e).__name__} {e}"
            sleep(1.0 * (attempt + 1))
    raise DataError(f"{symbol}: all hosts failed ({last})")


def validate_rows(symbol, rows):
    if not rows:
        raise DataError(f"{symbol}: no rows")
    try:
        t = np.array([int(r[0]) for r in rows], dtype=np.int64)
        o, h, l, c = (np.array([float(r[k]) for r in rows]) for k in (1, 2, 3, 4))
    except (TypeError, ValueError, IndexError) as e:
        raise DataError(f"{symbol}: malformed row ({e})")
    if not np.all(np.isfinite([o, h, l, c])) or (np.minimum.reduce([o, h, l, c]) <= 0).any():
        raise DataError(f"{symbol}: non-positive or non-finite price")
    if (h < np.maximum(o, c)).any() or (l > np.minimum(o, c)).any() or (h < l).any():
        raise DataError(f"{symbol}: inconsistent OHLC bar")
    dt = np.diff(t)
    if (dt < DAY_MS).any() or (t % DAY_MS != 0).any():
        raise DataError(f"{symbol}: duplicate, unordered or non-daily timestamps")
    return dict(symbol=symbol, t=t, o=o, h=h, l=l, c=c, missing_days=int(((dt // DAY_MS) - 1).sum()))


def fetch_klines(symbol, http_get=default_http_get, start_ms=START_MS, end_ms=T0_MS, hosts=HOSTS, retries=3, sleep=time.sleep):
    rows, cur = [], start_ms
    while cur < end_ms:
        page = _page(symbol, cur, end_ms, http_get, hosts, retries, sleep)
        if not page:
            break
        rows += [r for r in page if start_ms <= int(r[0]) < end_ms]
        last_open = int(page[-1][0])
        if len(page) < 1000 or last_open < cur:
            break
        cur = last_open + DAY_MS
        sleep(0.15)
    return validate_rows(symbol, rows)


def data_hash(d):
    hh = hashlib.sha256()
    for k in ("t", "o", "h", "l", "c"):
        hh.update(np.ascontiguousarray(d[k]).tobytes())
    return hh.hexdigest()


def load_universe(end_ms, http_get=default_http_get, sleep=time.sleep, symbols=UNIVERSE):
    """Fetch every coin up to end_ms (exclusive). A failing or malformed coin is excluded and listed; fewer than MIN_COINS = infrastructure failure."""
    got, notes = {}, []
    for s in symbols:
        try:
            d = fetch_klines(s, http_get=http_get, sleep=sleep, end_ms=end_ms)
        except DataError as e:
            notes.append(dict(symbol=s, status="EXCLUDED", reason=str(e)))
            continue
        if d["missing_days"] > MAX_MISSING_DAYS:
            notes.append(dict(symbol=s, status="EXCLUDED", reason=f"missing_days={d['missing_days']}"))
            continue
        got[s] = d
        notes.append(dict(symbol=s, status="OK", bars=len(d["c"]), missing_days=d["missing_days"], last=time.strftime("%Y-%m-%d", time.gmtime(int(d["t"][-1]) / 1000)), sha256=data_hash(d)[:16]))
    if len(got) < MIN_COINS:
        raise DataError(f"only {len(got)} coins usable (< {MIN_COINS}); infrastructure failure, not a result")
    return got, notes


# ----------------------------------------------------------------------------- the rule (scalar, per coin, written independently of Search Lab's vectorised code)
def donchian_state(h, l, c, N):
    """1 while long. Enter when close > max(high of the previous N bars); exit when close < min(low of the previous N//2 bars). Uses bars <= i only."""
    M = N // 2
    out = np.zeros(len(c))
    st = 0
    for i in range(len(c)):
        if st == 1 and i >= M and c[i] < min(l[i - M:i]):
            st = 0
        elif st == 0 and i >= N and c[i] > max(h[i - N:i]):
            st = 1
        out[i] = st
    return out


def vol30(c):
    """Annualised population standard deviation of the last 30 simple daily close-to-close returns (NaN before 30 returns exist)."""
    v = np.full(len(c), np.nan)
    ret = np.full(len(c), np.nan)
    ret[1:] = c[1:] / c[:-1] - 1.0
    for i in range(VOL_WINDOW, len(c)):
        v[i] = np.std(ret[i - VOL_WINDOW + 1:i + 1]) * math.sqrt(ANN)
    return v


def coin_calc(d):
    """Per-bar arrays for one coin: states (T x 5), signal, vol, scale, ready, weight (= ready x signal x scale)."""
    h, l, c = d["h"], d["l"], d["c"]
    S = np.column_stack([donchian_state(h, l, c, N) for N in ENS_N])
    sig = S.mean(axis=1)
    vol = vol30(c)
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(np.isfinite(vol) & (vol > 0), np.minimum(1.0, TARGET_VOL / vol), 0.0)
    ready = np.arange(len(c)) >= WARMUP_BARS
    return dict(S=S, sig=sig, vol=vol, scale=scale, ready=ready, w=np.where(ready, sig * scale, 0.0))


# ----------------------------------------------------------------------------- paper track (deterministic; recomputable from public data at any time)
def grid(datas):
    names = sorted(datas)
    t_min = min(int(datas[s]["t"][0]) for s in names)
    t_max = max(int(datas[s]["t"][-1]) for s in names)
    T = int((t_max - t_min) // DAY_MS) + 1
    O, W, B, R = (np.full((T, len(names)), np.nan) for _ in range(4))
    for a, s in enumerate(names):
        d = datas[s]
        cc = coin_calc(d)
        idx = ((d["t"] - t_min) // DAY_MS).astype(int)
        O[idx, a] = d["o"]
        W[idx, a] = cc["w"]
        B[idx, a] = np.where(cc["ready"], cc["scale"], 0.0)
        R[idx, a] = np.where(cc["ready"], 1.0, 0.0)
    return dict(names=names, t=t_min + DAY_MS * np.arange(T, dtype=np.int64), O=O, W=W, B=B, ready=R)


def paper_track(datas, t0_ms=T0_MS, c_side=C_SIDE, start_flat=True):
    """Daily equal-weight portfolio return of bar j = held from the open of j to the open of j+1 (weights decided at the close of j-1).
    Only bars with open time >= t0_ms and a following open count. start_flat: the first counted day starts from cash (entry costs are paid)."""
    G = grid(datas)
    O, W, B, ready, t = G["O"], G["W"], G["B"], G["ready"], G["t"]
    T = len(t)
    Wf, Bf = np.nan_to_num(W), np.nan_to_num(B)
    R, Rb = np.full(T, np.nan), np.full(T, np.nan)
    first = None
    for j in range(2, T - 1):
        if t[j] < t0_ms:
            continue
        if first is None:
            first = j
        ro = O[j + 1] / O[j] - 1.0
        act = (ready[j - 1] == 1.0) & np.isfinite(ro)
        n = int(act.sum())
        if n < MIN_ACTIVE:
            continue
        w1, w2 = Wf[j - 1], (np.zeros_like(Wf[j - 2]) if (start_flat and j == first) else Wf[j - 2])
        b1, b2 = Bf[j - 1], (np.zeros_like(Bf[j - 2]) if (start_flat and j == first) else Bf[j - 2])
        R[j] = float(np.where(act, w1 * np.nan_to_num(ro) - c_side * np.abs(w1 - w2), 0.0).sum() / n)
        Rb[j] = float(np.where(act, b1 * np.nan_to_num(ro) - c_side * np.abs(b1 - b2), 0.0).sum() / n)
    return dict(t=t, R=R, Rb=Rb)


def _equity_stats(r):
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return dict(days=0, cum=float("nan"), maxdd=float("nan"), sharpe=float("nan"))
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    sh = float(r.mean() / r.std(ddof=1) * math.sqrt(ANN)) if len(r) > 2 and r.std(ddof=1) > 0 else float("nan")
    return dict(days=int(len(r)), cum=float(eq[-1] - 1.0), maxdd=float(((peak - eq) / peak).max()), sharpe=sh)


# ----------------------------------------------------------------------------- today's table
def table_rows(datas, asof_ms):
    """Rows for the last CLOSED bar (open time asof_ms - one day). A coin without that bar is stale and treated as flat."""
    last_t = asof_ms - DAY_MS
    rows = []
    for s in sorted(datas):
        d = datas[s]
        cc = coin_calc(d)
        fresh = int(d["t"][-1]) == last_t
        i = len(d["c"]) - 1
        ok = bool(fresh and cc["ready"][i] and np.isfinite(cc["vol"][i]))
        rows.append(dict(symbol=s, fresh=fresh, ready=ok, close=float(d["c"][i]), states="".join(str(int(x)) for x in cc["S"][i]),
                         sig=float(cc["sig"][i]), prev_sig=float(cc["sig"][i - 1]) if i > 0 else float("nan"), vol=float(cc["vol"][i]),
                         scale=float(cc["scale"][i]), w_coin=float(cc["w"][i]) if ok else 0.0))
    n = sum(r["ready"] for r in rows)
    for r in rows:
        r["w_eq"] = r["w_coin"] / n if n else 0.0
    return rows, n


def render_table(rows, n, asof_ms, equity, notes, code_sha):
    day = time.strftime("%Y-%m-%d", time.gmtime((asof_ms - DAY_MS) / 1000))
    tot = sum(r["w_eq"] for r in rows)
    L = [f"# Trend Setup v0: signal table for the daily bar closed {day} UTC ({VERSION})", "",
         "**UNPROVEN: attention and record-keeping only. Not a recommendation. Nothing here is validated; tests are synthetic and by the same author.**", "",
         f"code sha256: `{code_sha}`", f"Active coins: {n} of {len(rows)}. Sum of suggested weights: {tot * 100:.1f}% of equity (rest in cash). Equity used for the notional column: {equity:,.0f}.", "",
         "| coin | close | states (N=10,20,30,55,100) | signal | prev signal | vol30 (ann.) | scale | weight inside own slice | % of equity (all active coins) | notional | note |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        note = "stale: no bar for the last closed day, treated as flat" if not r["fresh"] else ("warm-up (fewer than 260 bars): flat" if not r["ready"] else ("CHANGED" if abs(r["sig"] - r["prev_sig"]) > 1e-9 else ""))
        L.append(f"| {r['symbol']} | {r['close']:.6g} | {r['states']} | {r['sig']:.1f} | {r['prev_sig']:.1f} | {r['vol']:.2f} | {r['scale']:.2f} | {r['w_coin']:.2f} | {r['w_eq'] * 100:.1f}% | {r['w_eq'] * equity:,.0f} | {note} |")
    L += ["", "If you trade only M of these coins, give each coin a slice of equity/M and size it by the 'weight inside own slice' column; fewer coins means less diversification and larger swings than the tested portfolio.", "",
          "## Data", "| symbol | status | bars | missing | last | sha256(data, first 16) |", "|---|---|---|---|---|---|"]
    for x in notes:
        L.append(f"| {x['symbol']} | {x['status']} | {x.get('bars', '')} | {x.get('missing_days', '')} | {x.get('last', x.get('reason', ''))} | {x.get('sha256', '')} |")
    return "\n".join(L) + "\n"


def render_paper(res, datas, code_sha, notes):
    s, b = _equity_stats(res["R"]), _equity_stats(res["Rb"])
    f = lambda x: "n/a" if not np.isfinite(x) else f"{x:+.3f}"
    L = [f"# Trend Setup v0: paper track since T0 = 2026-11-22 00:00 UTC ({VERSION})", "", "**UNPROVEN. Descriptive record; no performance statement is made before 90 counted days, and none counts as proof at any length.**", "", f"code sha256: `{code_sha}`", "",
         f"- counted days: {s['days']} (fewer than 90: Sharpe not interpreted)", f"- rule: cumulative return {f(s['cum'])}, max drawdown {f(s['maxdd'])}, Sharpe {f(s['sharpe'])}",
         f"- always-long benchmark (same coins, same vol scaling, same costs): cumulative {f(b['cum'])}, max drawdown {f(b['maxdd'])}, Sharpe {f(b['sharpe'])}", "",
         "Entry costs of day one are included (the track starts from cash). Recompute at any time from public data with this file; compare the data hashes below.", "", "## Data", "| symbol | status | bars | missing | last | sha256(data, first 16) |", "|---|---|---|---|---|---|"]
    for x in notes:
        L.append(f"| {x['symbol']} | {x['status']} | {x.get('bars', '')} | {x.get('missing_days', '')} | {x.get('last', x.get('reason', ''))} | {x.get('sha256', '')} |")
    return "\n".join(L) + "\n"


def code_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "table"
    opts = dict(zip(argv[2::2], argv[3::2]))
    outdir = Path(opts.get("--out", "trendsetup_out"))
    outdir.mkdir(parents=True, exist_ok=True)
    asof_ms = int(opts.get("--asof-ms", int(time.time() * 1000) // DAY_MS * DAY_MS))
    equity = float(opts.get("--equity", 10000))
    datas, notes = load_universe(asof_ms)
    sha = code_sha256()
    if cmd == "table":
        rows, n = table_rows(datas, asof_ms)
        txt = render_table(rows, n, asof_ms, equity, notes, sha)
        (outdir / "table.json").write_text(json.dumps(dict(asof_ms=asof_ms, rows=rows, n_active=n, code_sha256=sha), indent=1), encoding="utf-8")
        (outdir / "table.md").write_text(txt, encoding="utf-8")
    elif cmd == "paper":
        txt = render_paper(paper_track(datas), datas, sha, notes)
        (outdir / "paper.md").write_text(txt, encoding="utf-8")
    else:
        raise SystemExit("usage: trendsetup.py table|paper [--equity N] [--out DIR] [--asof-ms MS]")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
