import numpy as np
import pandas as pd
import pytest

from src import decision

NOW = pd.Timestamp("2026-11-11T01:07:00Z")
FREQ = {"15m": "15min", "1h": "1h", "4h": "4h"}

CFG = {
    "min_adx": 18.0, "min_atr_pct": 0.05, "max_atr_pct": 1.2, "min_volume_ratio": 0.8,
    "fee_pct_side": 0.05, "slippage_pct_side": 0.03, "min_net_rr": 1.5,
    "equity": 1000.0, "risk_pct": 0.5, "max_leverage": 2.0,
}
DUMMY = {"15m": None, "1h": None, "4h": None}


def frame(side="LONG"):
    n = 30
    if side == "LONG":
        close = [100.0] * (n - 1) + [101.0]
        ema20 = [100.5] * (n - 1) + [100.6]
        ema50, rsi, low, high = 99.0, 55.0, 99.5, 103.0
    else:
        close = [100.0] * (n - 2) + [101.0, 100.0]
        ema20 = [100.5] * (n - 1) + [100.4]
        ema50, rsi, low, high = 101.5, 45.0, 97.0, 101.5
    return pd.DataFrame({
        "time": pd.date_range("2026-11-11", periods=n, freq="15min", tz="UTC"),
        "close": close, "ema20": ema20, "ema50": ema50, "rsi": rsi,
        "atr": 2.0, "adx": 25.0, "atr_pct": 0.3, "vol_ratio": 1.0,
        "low": low, "high": high,
    })


def deriv(side="LONG"):
    sign = 1 if side == "LONG" else -1
    return {"funding_rate": 0.0001 * sign, "mark_price": 65000.0,
            "open_interest": 1234.0, "book_imbalance": 0.5 * sign}


def prepare(monkeypatch, df, h="BULLISH", structure="BULLISH BOS"):
    monkeypatch.setattr(decision, "assess_data",
                        lambda d, v, now=None: {"status": "VALID", "reasons": []})
    monkeypatch.setattr(decision, "indicators", lambda x: df)
    monkeypatch.setattr(decision, "bias_of", lambda x: h)
    monkeypatch.setattr(decision, "market_structure", lambda x: structure)


def test_invalid_data_gives_no_trade(monkeypatch):
    monkeypatch.setattr(decision, "assess_data",
                        lambda d, v, now=None: {"status": "INVALID", "reasons": ["x"]})
    r = decision.decide(DUMMY, deriv(), CFG)
    assert r["label"] == "NO TRADE"
    assert r["setup"]["status"] == "NO_ENTRY"
    assert r["market"]["status"] == "UNKNOWN"
    assert r["executable"] is False


def test_stale_data_gives_no_trade(monkeypatch):
    monkeypatch.setattr(decision, "assess_data",
                        lambda d, v, now=None: {"status": "STALE", "reasons": ["x"]})
    r = decision.decide(DUMMY, deriv(), CFG)
    assert r["label"] == "NO TRADE"
    assert r["data"]["status"] == "STALE"


def test_market_not_tradeable_gives_wait(monkeypatch):
    prepare(monkeypatch, frame("LONG"))
    r = decision.decide(DUMMY, deriv("LONG"), dict(CFG, min_adx=40.0))
    assert r["label"] == "WAIT"
    assert r["market"]["status"] == "NOT_TRADEABLE"
    assert r["setup"]["status"] == "NO_ENTRY"


def test_neutral_direction_gives_wait(monkeypatch):
    prepare(monkeypatch, frame("LONG"), h="MIXED", structure="RANGE / NO BOS")
    neutral = {"funding_rate": 0.0, "mark_price": 65000.0,
               "open_interest": 1234.0, "book_imbalance": 0.0}
    r = decision.decide(DUMMY, neutral, CFG)
    assert r["label"] == "WAIT"
    assert r["direction"]["status"] == "NEUTRAL"


def test_long_setup(monkeypatch):
    prepare(monkeypatch, frame("LONG"))
    r = decision.decide(DUMMY, deriv("LONG"), CFG)
    assert r["label"] == "LONG SETUP"
    assert r["setup"]["status"] == "VALID_LONG"
    assert r["direction"]["status"] == "BULLISH"
    assert r["setup"]["plan"]["stop"] == pytest.approx(99.0)
    assert r["setup"]["plan"]["executable"] is False
    assert r["executable"] is False


def test_short_setup(monkeypatch):
    prepare(monkeypatch, frame("SHORT"), h="BEARISH", structure="BEARISH BOS")
    r = decision.decide(DUMMY, deriv("SHORT"), CFG)
    assert r["label"] == "SHORT SETUP"
    assert r["setup"]["status"] == "VALID_SHORT"
    assert r["direction"]["status"] == "BEARISH"
    assert r["setup"]["plan"]["stop"] == pytest.approx(102.0)


def test_bias_without_trigger_is_not_an_entry(monkeypatch):
    df = frame("LONG")
    df.loc[df.index[-1], "close"] = 100.0
    prepare(monkeypatch, df)
    r = decision.decide(DUMMY, deriv("LONG"), CFG)
    assert r["label"] == "BULLISH BIAS — NO VALID ENTRY"
    assert r["setup"]["status"] == "NO_ENTRY"
    assert r["setup"]["plan"] is None


def test_low_net_rr_is_not_an_entry(monkeypatch):
    prepare(monkeypatch, frame("LONG"))
    r = decision.decide(DUMMY, deriv("LONG"), dict(CFG, min_net_rr=5.0))
    assert r["label"] == "BULLISH BIAS — NO VALID ENTRY"
    assert r["setup"]["status"] == "NO_ENTRY"
    assert r["setup"]["plan"]["status"] == "LOW_NET_RR"


def test_non_finite_indicator_gives_no_trade(monkeypatch):
    df = frame("LONG")
    df.loc[df.index[-1], "rsi"] = np.inf
    prepare(monkeypatch, df)
    r = decision.decide(DUMMY, deriv("LONG"), CFG)
    assert r["label"] == "NO TRADE"
    assert r["data"]["status"] == "INVALID"


def test_unexpected_error_fails_closed(monkeypatch):
    prepare(monkeypatch, frame("LONG"))
    cfg = {k: v for k, v in CFG.items() if k != "fee_pct_side"}
    r = decision.decide(DUMMY, deriv("LONG"), cfg)
    assert r["label"] == "NO TRADE"
    assert r["setup"]["status"] == "NO_ENTRY"
    assert "KeyError" in r["error"]


def make_flat(tf, count=220):
    step = pd.tseries.frequencies.to_offset(FREQ[tf])
    last_open = NOW.floor(FREQ[tf]) - step
    times = pd.date_range(end=last_open, periods=count, freq=FREQ[tf])
    return pd.DataFrame({
        "time": times, "open": 100.0, "high": 103.0, "low": 99.0, "close": 101.0,
        "volume": 10.0, "taker_buy_base": 5.0, "taker_buy_quote": 500.0,
    })


def test_real_flat_data_fails_closed_without_error():
    data = {tf: make_flat(tf) for tf in FREQ}
    r = decision.decide(data, deriv("LONG"), CFG, now=NOW)
    assert r["label"] == "NO TRADE"
    assert r["setup"]["status"] == "NO_ENTRY"
    assert r["error"] is None
