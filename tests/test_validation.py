import pandas as pd
import pytest

from src.validation import validate_ohlcv


NOW = pd.Timestamp("2026-01-01T01:00:00Z")


def sample():
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01T00:15:00Z", periods=3, freq="15min"),
        "open": [100, 101, 102],
        "high": [103, 104, 105],
        "low": [99, 100, 101],
        "close": [101, 102, 103],
        "volume": [10, 11, 12],
    })


def test_valid_data_passes():
    validate_ohlcv(sample(), "15min", now=NOW)


def test_duplicate_candle_fails():
    x = sample()
    x.loc[2, "time"] = x.loc[1, "time"]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_ohlcv(x, "15min", now=NOW)


def test_missing_interval_fails():
    x = sample()
    x.loc[2, "time"] += pd.Timedelta(15, unit="min")
    with pytest.raises(ValueError, match="intervals"):
        validate_ohlcv(x, "15min", now=NOW)


def test_invalid_ohlc_fails():
    x = sample()
    x.loc[2, "high"] = 90
    with pytest.raises(ValueError, match="OHLC"):
        validate_ohlcv(x, "15min", now=NOW)


def test_stale_data_fails():
    x = sample()
    with pytest.raises(ValueError, match="stale"):
        validate_ohlcv(x, "15min", now=NOW + pd.Timedelta(1, unit="h"))
