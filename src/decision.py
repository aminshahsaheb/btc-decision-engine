from __future__ import annotations

import math

from src.assessment import assess_data, assess_direction, assess_market
from src.engine import bias_of, indicators, market_structure
from src.planning import entry_trigger, plan_trade

REQUIRED_ROW = ("close", "ema20", "ema50", "rsi", "atr", "adx", "atr_pct", "vol_ratio")
STOP_LOOKBACK = 12


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _market_unknown(reason):
    return {"status": "UNKNOWN", "reasons": [reason]}


def _direction_not_assessed():
    return {"status": "NEUTRAL", "bull": 0, "bear": 0,
            "bull_evidence": [], "bear_evidence": [], "reasons": ["not assessed"]}


def _setup(status, reasons, plan=None):
    return {"status": status, "reasons": list(reasons), "plan": plan}


def _result(label, data, market, direction, setup, error=None):
    return {
        "label": label,
        "data": data,
        "market": market,
        "direction": direction,
        "setup": setup,
        "executable": False,
        "error": error,
    }


def decide(data, deriv, cfg, now=None) -> dict:
    """Combine the four independent assessments. Fails closed."""
    try:
        data_a = assess_data(data, deriv, now=now)
        if data_a["status"] != "VALID":
            return _result("NO TRADE", data_a, _market_unknown("data not valid"),
                           _direction_not_assessed(), _setup("NO_ENTRY", ["data not valid"]))

        base = indicators(data["15m"]).dropna().reset_index(drop=True)
        if len(base) < STOP_LOOKBACK + 1:
            bad = {"status": "INVALID", "reasons": ["insufficient indicator history"]}
            return _result("NO TRADE", bad, _market_unknown("no indicator history"),
                           _direction_not_assessed(),
                           _setup("NO_ENTRY", ["insufficient indicator history"]))

        row = base.iloc[-1]
        prev = base.iloc[-2]
        bad_keys = [k for k in REQUIRED_ROW if not _finite(row[k])]
        bad_keys += [f"prev_{k}" for k in ("close", "ema20") if not _finite(prev[k])]
        if bad_keys:
            bad = {"status": "INVALID", "reasons": [f"non-finite indicator: {k}" for k in bad_keys]}
            return _result("NO TRADE", bad, _market_unknown("indicator not finite"),
                           _direction_not_assessed(),
                           _setup("NO_ENTRY", ["indicator not finite"]))

        h1 = bias_of(data["1h"])
        h4 = bias_of(data["4h"])
        structure = market_structure(data["15m"])

        market = assess_market(row, cfg)
        direction = assess_direction(row, h1, h4, structure, deriv)

        if market["status"] == "UNKNOWN":
            return _result("NO TRADE", data_a, market, direction,
                           _setup("NO_ENTRY", ["market status unknown"]))
        if market["status"] == "NOT_TRADEABLE":
            return _result("WAIT", data_a, market, direction,
                           _setup("NO_ENTRY", ["market not tradeable"]))
        if direction["status"] == "NEUTRAL":
            return _result("WAIT", data_a, market, direction,
                           _setup("NO_ENTRY", ["no clear directional bias"]))

        side = "LONG" if direction["status"] == "BULLISH" else "SHORT"
        bias_label = f"{direction['status']} BIAS — NO VALID ENTRY"

        if not entry_trigger(side, prev["close"], prev["ema20"],
                             row["close"], row["ema20"], row["rsi"]):
            return _result(bias_label, data_a, market, direction,
                           _setup("NO_ENTRY", ["entry trigger not confirmed"]))

        plan = plan_trade(side, row["close"], row["atr"],
                          base["low"].iloc[-STOP_LOOKBACK:].min(),
                          base["high"].iloc[-STOP_LOOKBACK:].max(), cfg)
        if plan["status"] != "OK":
            return _result(bias_label, data_a, market, direction,
                           _setup("NO_ENTRY", [plan["status"] + ": " + plan.get("reason", "")], plan))

        return _result(f"{side} SETUP", data_a, market, direction,
                       _setup(f"VALID_{side}", [], plan))
    except Exception as exc:
        bad = {"status": "INVALID", "reasons": ["unexpected error"]}
        return _result("NO TRADE", bad, _market_unknown("unexpected error"),
                       _direction_not_assessed(),
                       _setup("NO_ENTRY", ["unexpected error"]),
                       error=f"{type(exc).__name__}: {exc}")
