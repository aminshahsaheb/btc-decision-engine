from __future__ import annotations
import math
import numpy as np
import pandas as pd

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    c, h, l = x.close, x.high, x.low
    x["ema20"] = c.ewm(span=20, adjust=False).mean()
    x["ema50"] = c.ewm(span=50, adjust=False).mean()
    x["ema200"] = c.ewm(span=200, adjust=False).mean()
    delta = c.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    avg_up = up.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_down = down.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.mask((avg_down == 0) & (avg_up > 0), 100.0)
    rsi = rsi.mask((avg_up == 0) & (avg_down > 0), 0.0)
    x["rsi"] = rsi.mask((avg_up == 0) & (avg_down == 0), 50.0)
    prev = c.shift(1)
    tr = pd.concat([(h-l), (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    up_move = h.diff()
    down_move = -l.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    smooth_plus = plus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    smooth_minus = minus_dm.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    plus_di = 100 * smooth_plus / x["atr"].replace(0, np.nan)
    minus_di = 100 * smooth_minus / x["atr"].replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    x["adx"] = dx.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    x["atr_pct"] = x["atr"] / c * 100
    x["vol_sma20"] = x.volume.rolling(20, min_periods=20).mean()
    x["vol_ratio"] = x.volume / x["vol_sma20"].replace(0, np.nan)
    x["taker_buy_ratio"] = x.taker_buy_base / x.volume.replace(0, np.nan)
    return x

def bias_of(df: pd.DataFrame) -> str:
    x = indicators(df).dropna()
    if len(x) < 5:
        return "INSUFFICIENT"
    r = x.iloc[-1]
    if r.close > r.ema50 > r.ema200 and r.ema50 > x.ema50.iloc[-5]:
        return "BULLISH"
    if r.close < r.ema50 < r.ema200 and r.ema50 < x.ema50.iloc[-5]:
        return "BEARISH"
    return "MIXED"

def market_structure(df: pd.DataFrame, lookback: int = 20) -> str:
    # Detect breakouts against the prior completed range.
    if isinstance(lookback, (bool, np.bool_)) or not isinstance(lookback, (int, np.integer)):
        raise ValueError("lookback must be a positive integer")
    if lookback < 1:
        raise ValueError("lookback must be a positive integer")

    if not isinstance(df, pd.DataFrame) or not df.columns.is_unique:
        return "UNKNOWN"

    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        return "UNKNOWN"

    if len(df) < lookback + 1:
        return "UNKNOWN"

    prior = df.iloc[-lookback-1:-1]

    try:
        prior_high = pd.to_numeric(prior["high"], errors="coerce").to_numpy(dtype=float)
        prior_low = pd.to_numeric(prior["low"], errors="coerce").to_numpy(dtype=float)
        last_close = float(pd.to_numeric(pd.Series([df["close"].iloc[-1]]), errors="coerce").iloc[0])
    except (TypeError, ValueError, OverflowError):
        return "UNKNOWN"

    if not np.isfinite(prior_high).all():
        return "UNKNOWN"
    if not np.isfinite(prior_low).all():
        return "UNKNOWN"
    if not math.isfinite(last_close):
        return "UNKNOWN"

    if last_close > prior_high.max():
        return "BULLISH BOS"
    if last_close < prior_low.min():
        return "BEARISH BOS"
    return "RANGE / NO BOS"

def analyze(data: dict, deriv: dict, cfg: dict) -> dict:
    needed = ["15m", "1h", "4h"]
    for tf in needed:
        if tf not in data or len(data[tf]) < 220:
            return {"decision":"NO TRADE", "reason":f"دادهٔ کافی برای {tf} وجود ندارد."}
    frames = {tf: indicators(data[tf]).dropna().reset_index(drop=True) for tf in needed}
    base = frames["15m"]
    r = base.iloc[-1]
    now = pd.Timestamp.now(tz="UTC")
    age_min = (now - pd.Timestamp(r.time)).total_seconds() / 60
    if age_min > 25:
        return {"decision":"NO TRADE", "reason":f"دادهٔ ۱۵ دقیقه‌ای قدیمی است ({age_min:.1f} دقیقه)."}
    if not all(math.isfinite(float(r[k])) for k in ["close","atr","adx","atr_pct","rsi","vol_ratio"]):
        return {"decision":"NO TRADE", "reason":"اندیکاتور یا دادهٔ بازار نامعتبر است."}

    h1, h4 = bias_of(data["1h"]), bias_of(data["4h"])
    structure = market_structure(data["15m"])
    bull = sum([
        h1 == "BULLISH", h4 == "BULLISH",
        r.close > r.ema50, r.ema20 > r.ema50,
        r.rsi >= 52, structure == "BULLISH BOS",
        deriv["book_imbalance"] > 0.10,
        deriv["funding_rate"] < 0.0005
    ])
    bear = sum([
        h1 == "BEARISH", h4 == "BEARISH",
        r.close < r.ema50, r.ema20 < r.ema50,
        r.rsi <= 48, structure == "BEARISH BOS",
        deriv["book_imbalance"] < -0.10,
        deriv["funding_rate"] > -0.0005
    ])
    bias = "LONG" if bull >= 6 and bear <= 2 else "SHORT" if bear >= 6 and bull <= 2 else "NO CLEAR BIAS"

    # Regime classification. Thresholds are initial engineering defaults, not learned probabilities.
    if r.atr_pct > cfg["max_atr_pct"]:
        regime = "HIGH VOLATILITY"
    elif r.adx < cfg["min_adx"]:
        regime = "RANGE / WEAK TREND"
    elif bias == "LONG":
        regime = "UPTREND"
    elif bias == "SHORT":
        regime = "DOWNTREND"
    else:
        regime = "TRANSITION / MIXED"

    market_ok = (
        r.adx >= cfg["min_adx"] and
        cfg["min_atr_pct"] <= r.atr_pct <= cfg["max_atr_pct"] and
        r.vol_ratio >= cfg["min_volume_ratio"] and
        deriv["mark_price"] > 0
    )
    common = {
        "price": float(r.close), "h1": h1, "h4": h4, "structure": structure,
        "regime": regime, "bias": bias, "bull": int(bull), "bear": int(bear),
        "adx": float(r.adx), "atr_pct": float(r.atr_pct),
        "vol_ratio": float(r.vol_ratio), "rsi": float(r.rsi),
        "taker_buy_ratio": float(r.taker_buy_ratio),
        "funding_rate": deriv["funding_rate"],
        "open_interest": deriv["open_interest"],
        "book_imbalance": deriv["book_imbalance"],
        "mark_price": deriv["mark_price"], "candle_time": r.time,
        "data_age_min": age_min
    }
    if not market_ok:
        why = []
        if r.adx < cfg["min_adx"]: why.append("قدرت روند کافی نیست")
        if r.atr_pct < cfg["min_atr_pct"]: why.append("نوسان بسیار کم است")
        if r.atr_pct > cfg["max_atr_pct"]: why.append("نوسان بیش از حد است")
        if r.vol_ratio < cfg["min_volume_ratio"]: why.append("حجم نسبی پایین است")
        return {"decision":"WAIT", "reason":"؛ ".join(why), **common}

    # Pullback/reclaim trigger on the closed 15m candle.
    prev = base.iloc[-2]
    long_trigger = prev.close <= prev.ema20 and r.close > r.ema20 and r.rsi > 50
    short_trigger = prev.close >= prev.ema20 and r.close < r.ema20 and r.rsi < 50
    direction = "LONG" if bias == "LONG" and long_trigger else "SHORT" if bias == "SHORT" and short_trigger else None
    if direction is None:
        return {"decision":"WAIT", "reason":"بازار ممکن است قابل معامله باشد، اما ستاپ ورود تأیید نشده است.", **common}

    n = 12
    entry = float(r.close)
    atr = float(r.atr)
    if direction == "LONG":
        stop = float(base.low.iloc[-n:].min() - 0.25 * atr)
        risk = entry - stop
        target1 = entry + risk
        target2 = entry + 2.0 * risk
        reward = target2 - entry
    else:
        stop = float(base.high.iloc[-n:].max() + 0.25 * atr)
        risk = stop - entry
        target1 = entry - risk
        target2 = entry - 2.0 * risk
        reward = entry - target2
    if risk <= 0 or risk / entry > 0.025:
        return {"decision":"WAIT", "reason":"فاصلهٔ حد ضرر بیش از حد مجاز است.", **common}

    # Fees and slippage are round-trip percentage estimates; funding is displayed separately.
    cost_rate = 2 * (cfg["fee_pct_side"] + cfg["slippage_pct_side"]) / 100
    cost = entry * cost_rate
    net_rr = (reward - cost) / (risk + cost) if risk + cost > 0 else 0
    if net_rr < cfg["min_net_rr"]:
        return {"decision":"NO TRADE", "reason":"نسبت سود به زیان خالص پس از هزینه‌ها کافی نیست.",
                **common, "entry":entry, "stop":stop, "target1":target1, "target2":target2, "net_rr":net_rr}

    risk_cash = cfg["equity"] * cfg["risk_pct"] / 100
    qty_risk = risk_cash / (risk + cost)
    qty_lev = cfg["equity"] * cfg["max_leverage"] / entry
    qty = min(qty_risk, qty_lev)
    return {"decision":f"{direction} SETUP",
            "reason":"فیلتر بازار، جهت و تریگر ورود عبور کرده‌اند؛ قبل از سفارش مشخصات قرارداد و قیمت را کنترل کن.",
            **common, "entry":entry, "stop":stop, "target1":target1, "target2":target2,
            "net_rr":net_rr, "quantity_estimate":qty,
            "risk_cash_estimate":qty*(risk+cost), "notional_estimate":qty*entry}
