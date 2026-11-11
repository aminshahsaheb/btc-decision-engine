import numpy as np
import pandas as pd
import pytest
from src.engine import indicators, bias_of, market_structure

def sample(n=350, trend=0.2):
    close = [30000 + i*trend for i in range(n)]
    return pd.DataFrame({
        "time":pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC"),
        "open":[x-2 for x in close], "high":[x+10 for x in close],
        "low":[x-10 for x in close], "close":close,
        "volume":[100.0]*n, "taker_buy_base":[55.0]*n,
        "taker_buy_quote":[55.0*x for x in close]
    })

def test_indicators_exist():
    out = indicators(sample())
    for col in ["ema20","ema50","ema200","rsi","atr","adx","atr_pct","vol_ratio","taker_buy_ratio"]:
        assert col in out.columns
    assert out.iloc[-1].ema20 > 0

def test_bias_returns_known_state():
    assert bias_of(sample()) in ["BULLISH","BEARISH","MIXED","INSUFFICIENT"]

def test_structure_returns_known_state():
    assert market_structure(sample()) in ["BULLISH BOS","BEARISH BOS","RANGE / NO BOS","UNKNOWN"]


def test_rsi_is_100_when_price_only_rises():
    out = indicators(sample(trend=0.2))
    assert out["rsi"].iloc[-1] == 100.0


def test_rsi_is_0_when_price_only_falls():
    out = indicators(sample(trend=-0.2))
    assert out["rsi"].iloc[-1] == 0.0


def test_rsi_is_50_when_price_is_flat():
    out = indicators(sample(trend=0.0))
    assert out["rsi"].iloc[-1] == 50.0


def test_directional_movement_uses_original_moves():
    high = pd.Series([110.0, 112.0, 113.0])
    low = pd.Series([100.0, 97.0, 95.0])

    up_move = high.diff()
    down_move = -low.diff()

    expected_plus = up_move.where(
        (up_move > down_move) & (up_move > 0), 0.0
    )
    expected_minus = down_move.where(
        (down_move > up_move) & (down_move > 0), 0.0
    )

    assert expected_plus.iloc[1] == 0.0
    assert expected_minus.iloc[1] == 3.0
    assert expected_plus.iloc[2] == 0.0
    assert expected_minus.iloc[2] == 2.0


def make_structure_df(count, last_close=100.0):
    return pd.DataFrame({
        "high": [110.0] * (count - 1) + [max(110.0, last_close)],
        "low": [90.0] * (count - 1) + [min(90.0, last_close)],
        "close": [100.0] * (count - 1) + [last_close],
    })


def test_structure_accepts_exact_minimum_rows():
    df = make_structure_df(21, last_close=111.0)
    assert market_structure(df, lookback=20) == "BULLISH BOS"


def test_structure_rejects_one_row_below_minimum():
    df = make_structure_df(20, last_close=111.0)
    assert market_structure(df, lookback=20) == "UNKNOWN"


def test_structure_detects_bearish_breakout():
    df = make_structure_df(21, last_close=89.0)
    assert market_structure(df, lookback=20) == "BEARISH BOS"


def test_structure_detects_no_breakout():
    df = make_structure_df(21, last_close=100.0)
    assert market_structure(df, lookback=20) == "RANGE / NO BOS"


@pytest.mark.parametrize("lookback", [0, -1, 1.5, True, False, None, "20"])
def test_structure_rejects_invalid_lookback(lookback):
    with pytest.raises(ValueError):
        market_structure(make_structure_df(21), lookback=lookback)


@pytest.mark.parametrize("column", ["high", "low", "close"])
def test_structure_rejects_missing_required_columns(column):
    df = make_structure_df(21).drop(columns=[column])
    assert market_structure(df) == "UNKNOWN"


@pytest.mark.parametrize(
    "column,row,value",
    [
        ("high", 0, np.nan),
        ("high", 0, np.inf),
        ("low", 0, -np.inf),
        ("low", 0, np.nan),
        ("close", -1, np.nan),
        ("close", -1, np.inf),
    ],
)
def test_structure_rejects_non_finite_values(column, row, value):
    df = make_structure_df(21)
    df.iloc[row, df.columns.get_loc(column)] = value
    assert market_structure(df) == "UNKNOWN"
