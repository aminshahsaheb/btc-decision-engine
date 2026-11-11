from __future__ import annotations

import math


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def entry_trigger(side, prev_close, prev_ema20, close, ema20, rsi) -> bool:
    """Pullback/reclaim trigger on a closed candle. Not a directional signal."""
    values = (prev_close, prev_ema20, close, ema20, rsi)
    if not all(_finite(v) for v in values):
        return False
    if side == "LONG":
        return bool(prev_close <= prev_ema20 and close > ema20 and rsi > 50)
    if side == "SHORT":
        return bool(prev_close >= prev_ema20 and close < ema20 and rsi < 50)
    return False


def plan_trade(side, entry, atr, recent_low, recent_high, cfg) -> dict:
    """Build stop, targets, net R:R and an ESTIMATED quantity.

    Status: OK, INVALID, WIDE_STOP or LOW_NET_RR.
    The quantity is never executable: real contract filters are not applied.
    """
    if side not in ("LONG", "SHORT"):
        return {"status": "INVALID", "reason": "side must be LONG or SHORT"}
    if not all(_finite(v) for v in (entry, atr, recent_low, recent_high)):
        return {"status": "INVALID", "reason": "non-finite input"}
    entry, atr = float(entry), float(atr)
    recent_low, recent_high = float(recent_low), float(recent_high)
    if entry <= 0 or atr <= 0:
        return {"status": "INVALID", "reason": "entry and atr must be positive"}

    if side == "LONG":
        stop = recent_low - 0.25 * atr
        risk = entry - stop
        target1 = entry + risk
        target2 = entry + 2.0 * risk
        reward = target2 - entry
    else:
        stop = recent_high + 0.25 * atr
        risk = stop - entry
        target1 = entry - risk
        target2 = entry - 2.0 * risk
        reward = entry - target2

    if risk <= 0:
        return {"status": "INVALID", "reason": "stop is on the wrong side of entry"}

    plan = {
        "side": side, "entry": entry, "stop": stop,
        "target1": target1, "target2": target2,
        "risk": risk, "reward": reward, "executable": False,
    }

    max_stop_pct = cfg.get("max_stop_pct", 0.025)
    if risk / entry > max_stop_pct:
        return {"status": "WIDE_STOP", "reason": "stop distance exceeds limit", **plan}

    cost = entry * 2 * (cfg["fee_pct_side"] + cfg["slippage_pct_side"]) / 100
    net_rr = (reward - cost) / (risk + cost)
    plan["net_rr"] = net_rr
    plan["cost_estimate"] = cost

    if net_rr < cfg["min_net_rr"]:
        return {"status": "LOW_NET_RR", "reason": "net reward-to-risk below minimum", **plan}

    risk_cash = cfg["equity"] * cfg["risk_pct"] / 100
    qty_by_risk = risk_cash / (risk + cost)
    qty_by_leverage = cfg["equity"] * cfg["max_leverage"] / entry
    qty = min(qty_by_risk, qty_by_leverage)
    plan.update({
        "quantity_estimate": qty,
        "risk_cash_estimate": qty * (risk + cost),
        "notional_estimate": qty * entry,
    })
    return {"status": "OK", "reason": "", **plan}
