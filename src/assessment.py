from __future__ import annotations

import math
import numbers

from src.validation import validate_ohlcv

NEEDED_TIMEFRAMES = ("15m", "1h", "4h")
MIN_CANDLES = 220
DERIVATIVE_KEYS = ("funding_rate", "mark_price", "open_interest", "book_imbalance")


def _is_finite_number(value) -> bool:
    return (
        isinstance(value, numbers.Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def assess_data(data, deriv, now=None) -> dict:
    """Data status: VALID, INVALID or STALE. Fails closed."""
    status = "VALID"
    reasons = []

    for tf in NEEDED_TIMEFRAMES:
        df = data.get(tf) if isinstance(data, dict) else None
        if df is None or len(df) < MIN_CANDLES:
            reasons.append(f"{tf}: insufficient candles")
            status = "INVALID"
            continue
        try:
            validate_ohlcv(df, tf, now=now)
        except Exception as exc:
            message = str(exc)
            reasons.append(f"{tf}: {message}")
            if "stale" in message.lower():
                if status == "VALID":
                    status = "STALE"
            else:
                status = "INVALID"

    for key in DERIVATIVE_KEYS:
        value = deriv.get(key) if isinstance(deriv, dict) else None
        if not _is_finite_number(value):
            reasons.append(f"derivatives: {key} missing or not finite")
            status = "INVALID"

    if isinstance(deriv, dict) and _is_finite_number(deriv.get("mark_price")):
        if deriv["mark_price"] <= 0:
            reasons.append("derivatives: mark_price must be positive")
            status = "INVALID"

    return {"status": status, "reasons": reasons}


def assess_market(row, cfg) -> dict:
    """Market status: TRADEABLE, NOT_TRADEABLE or UNKNOWN."""
    values = {}
    for key in ("adx", "atr_pct", "vol_ratio"):
        try:
            value = float(row[key])
        except (KeyError, TypeError, ValueError):
            value = float("nan")
        if not math.isfinite(value):
            return {"status": "UNKNOWN", "reasons": [f"{key} unavailable"]}
        values[key] = value

    reasons = []
    if values["adx"] < cfg["min_adx"]:
        reasons.append("trend strength too low")
    if values["atr_pct"] < cfg["min_atr_pct"]:
        reasons.append("volatility too low")
    if values["atr_pct"] > cfg["max_atr_pct"]:
        reasons.append("volatility too high")
    if values["vol_ratio"] < cfg["min_volume_ratio"]:
        reasons.append("relative volume too low")

    return {"status": "NOT_TRADEABLE" if reasons else "TRADEABLE", "reasons": reasons}


def assess_direction(row, h1, h4, structure, deriv) -> dict:
    """Directional bias: BULLISH, BEARISH or NEUTRAL. Not an entry signal."""
    bull_checks = {
        "1h bias bullish": h1 == "BULLISH",
        "4h bias bullish": h4 == "BULLISH",
        "close above EMA50": row["close"] > row["ema50"],
        "EMA20 above EMA50": row["ema20"] > row["ema50"],
        "RSI >= 52": row["rsi"] >= 52,
        "bullish break of structure": structure == "BULLISH BOS",
        "order book imbalance > 0.10": deriv["book_imbalance"] > 0.10,
        "funding below 0.0005": deriv["funding_rate"] < 0.0005,
    }
    bear_checks = {
        "1h bias bearish": h1 == "BEARISH",
        "4h bias bearish": h4 == "BEARISH",
        "close below EMA50": row["close"] < row["ema50"],
        "EMA20 below EMA50": row["ema20"] < row["ema50"],
        "RSI <= 48": row["rsi"] <= 48,
        "bearish break of structure": structure == "BEARISH BOS",
        "order book imbalance < -0.10": deriv["book_imbalance"] < -0.10,
        "funding above -0.0005": deriv["funding_rate"] > -0.0005,
    }
    bull_evidence = [name for name, ok in bull_checks.items() if bool(ok)]
    bear_evidence = [name for name, ok in bear_checks.items() if bool(ok)]
    bull, bear = len(bull_evidence), len(bear_evidence)

    if bull >= 6 and bear <= 2:
        status = "BULLISH"
    elif bear >= 6 and bull <= 2:
        status = "BEARISH"
    else:
        status = "NEUTRAL"

    return {
        "status": status,
        "bull": bull,
        "bear": bear,
        "bull_evidence": bull_evidence,
        "bear_evidence": bear_evidence,
    }
