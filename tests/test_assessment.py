import numpy as np
import pandas as pd

from src.assessment import assess_data, assess_market, assess_direction

NOW = pd.Timestamp("2026-11-11T01:07:00Z")
FREQ = {"15m": "15min", "1h": "1h", "4h": "4h"}


def make_frame(tf, count=220):
    last_open = NOW.floor(FREQ[tf]) - pd.Timedelta(1, unit="ns") * 0
    step = pd.tseries.frequencies.to_offset(FREQ[tf])
    last_open = NOW.floor(FREQ[tf]) - step
    times = pd.date_range(end=last_open, periods=count, freq=FREQ[tf])
    return pd.DataFrame({
        "time": times,
        "open": 100.0, "high": 103.0, "low": 99.0, "close": 101.0,
        "volume": 10.0, "taker_buy_base": 5.0, "taker_buy_quote": 500.0,
    })


def good_data():
    return {tf: make_frame(tf) for tf in ["15m", "1h", "4h"]}


def good_deriv():
    return {"funding_rate": 0.0001, "mark_price": 65000.0,
            "open_interest": 1234.0, "book_imbalance": 0.0}


CFG = {"min_adx": 18.0, "min_atr_pct": 0.05, "max_atr_pct": 1.2, "min_volume_ratio": 0.8}


def good_row():
    return {"adx": 25.0, "atr_pct": 0.3, "vol_ratio": 1.0}


def test_data_valid():
    assert assess_data(good_data(), good_deriv(), now=NOW)["status"] == "VALID"


def test_data_too_few_candles_is_invalid():
    data = good_data()
    data["1h"] = make_frame("1h", count=100)
    assert assess_data(data, good_deriv(), now=NOW)["status"] == "INVALID"


def test_data_missing_timeframe_is_invalid():
    data = good_data()
    del data["4h"]
    assert assess_data(data, good_deriv(), now=NOW)["status"] == "INVALID"


def test_data_stale():
    result = assess_data(good_data(), good_deriv(), now=NOW + pd.Timedelta(10, unit="h"))
    assert result["status"] == "STALE"
    assert any("stale" in r.lower() for r in result["reasons"])


def test_data_nan_derivative_is_invalid():
    deriv = good_deriv()
    deriv["funding_rate"] = float("nan")
    assert assess_data(good_data(), deriv, now=NOW)["status"] == "INVALID"


def test_data_zero_mark_price_is_invalid():
    deriv = good_deriv()
    deriv["mark_price"] = 0.0
    assert assess_data(good_data(), deriv, now=NOW)["status"] == "INVALID"


def test_market_tradeable():
    assert assess_market(good_row(), CFG)["status"] == "TRADEABLE"


def test_market_low_adx():
    row = good_row(); row["adx"] = 10.0
    assert assess_market(row, CFG)["status"] == "NOT_TRADEABLE"


def test_market_low_volatility():
    row = good_row(); row["atr_pct"] = 0.01
    assert assess_market(row, CFG)["status"] == "NOT_TRADEABLE"


def test_market_high_volatility():
    row = good_row(); row["atr_pct"] = 3.0
    assert assess_market(row, CFG)["status"] == "NOT_TRADEABLE"


def test_market_low_volume():
    row = good_row(); row["vol_ratio"] = 0.2
    assert assess_market(row, CFG)["status"] == "NOT_TRADEABLE"


def test_market_nan_is_unknown():
    row = good_row(); row["adx"] = float("nan")
    assert assess_market(row, CFG)["status"] == "UNKNOWN"


def test_market_missing_key_is_unknown():
    row = good_row(); del row["vol_ratio"]
    assert assess_market(row, CFG)["status"] == "UNKNOWN"


def test_direction_bullish():
    row = {"close": 110.0, "ema20": 108.0, "ema50": 105.0, "rsi": 60.0}
    deriv = {"book_imbalance": 0.5, "funding_rate": 0.0001}
    result = assess_direction(row, "BULLISH", "BULLISH", "BULLISH BOS", deriv)
    assert result["status"] == "BULLISH"
    assert result["bull"] == 8


def test_direction_bearish():
    row = {"close": 90.0, "ema20": 92.0, "ema50": 95.0, "rsi": 40.0}
    deriv = {"book_imbalance": -0.5, "funding_rate": -0.0001}
    result = assess_direction(row, "BEARISH", "BEARISH", "BEARISH BOS", deriv)
    assert result["status"] == "BEARISH"
    assert result["bear"] == 8


def test_direction_neutral_when_mixed():
    row = {"close": 100.0, "ema20": 100.0, "ema50": 100.0, "rsi": 50.0}
    deriv = {"book_imbalance": 0.0, "funding_rate": 0.0}
    result = assess_direction(row, "MIXED", "MIXED", "RANGE / NO BOS", deriv)
    assert result["status"] == "NEUTRAL"
