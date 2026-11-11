from __future__ import annotations

import math


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _invalid(reason: str) -> dict:
    return {"status": "INVALID", "reason": reason, "executable": False}


def position_size(side, entry, stop, equity, risk_pct,
                  fee_pct_side, slippage_pct_side, max_leverage) -> dict:
    """Estimated position size for a manually chosen entry and stop.

    The quantity is an ESTIMATE: exchange contract filters are not applied and liquidation
    is not modelled, so the result is never executable.
    """
    if side not in ("LONG", "SHORT"):
        return _invalid("side must be LONG or SHORT")
    values = (entry, stop, equity, risk_pct, fee_pct_side, slippage_pct_side, max_leverage)
    if not all(_finite(v) for v in values):
        return _invalid("all inputs must be finite numbers")

    entry, stop, equity, risk_pct, fee, slip, leverage = (float(v) for v in values)
    if entry <= 0 or stop <= 0 or equity <= 0 or risk_pct <= 0 or leverage <= 0:
        return _invalid("entry, stop, equity, risk and leverage must be positive")
    if fee < 0 or slip < 0:
        return _invalid("fee and slippage cannot be negative")
    if side == "LONG" and stop >= entry:
        return _invalid("stop must be below entry for a LONG")
    if side == "SHORT" and stop <= entry:
        return _invalid("stop must be above entry for a SHORT")

    risk = abs(entry - stop)
    cost = entry * 2 * (fee + slip) / 100
    risk_cash = equity * risk_pct / 100
    qty_by_risk = risk_cash / (risk + cost)
    qty_by_leverage = equity * leverage / entry
    quantity = min(qty_by_risk, qty_by_leverage)

    sign = 1 if side == "LONG" else -1
    warnings = []
    if risk / entry > 0.025:
        warnings.append("WIDE_STOP")
    if qty_by_leverage < qty_by_risk:
        warnings.append("LEVERAGE_CAPPED")

    return {
        "status": "OK",
        "side": side,
        "quantity_estimate": quantity,
        "risk_cash_estimate": quantity * (risk + cost),
        "notional_estimate": quantity * entry,
        "stop_pct": risk / entry * 100,
        "cost_estimate": cost,
        "target_1r": entry + sign * risk,
        "target_2r": entry + sign * 2 * risk,
        "target_3r": entry + sign * 3 * risk,
        "warnings": warnings,
        "executable": False,
    }
