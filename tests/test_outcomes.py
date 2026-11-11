import pandas as pd
import pytest

from src.outcomes import MAX_CANDLES, resolve_outcome

T = pd.Timestamp("2026-11-11 00:00", tz="UTC")

LONG = {"side": "LONG", "entry": 100.0, "stop": 97.5, "target1": 102.5, "target2": 105.0,
        "risk": 2.5, "reward": 5.0, "cost_estimate": 0.16}
SHORT = {"side": "SHORT", "entry": 100.0, "stop": 102.5, "target1": 97.5, "target2": 95.0,
         "risk": 2.5, "reward": 5.0, "cost_estimate": 0.16}


def candles(rows, start=None):
    start = T + pd.Timedelta(15, unit="min") if start is None else start
    times = pd.date_range(start, periods=len(rows), freq="15min")
    return pd.DataFrame({
        "time": times,
        "high": [r[0] for r in rows],
        "low": [r[1] for r in rows],
        "close": [r[2] for r in rows],
    })


def test_max_candles_is_one_day_of_15m():
    assert MAX_CANDLES == 96


def test_long_target_hit():
    out = resolve_outcome(LONG, T, candles([(101, 99.5, 100.5), (106, 100, 105.5)]))
    assert out["status"] == "TARGET2"
    assert out["candles_held"] == 2
    assert out["r_gross"] == pytest.approx(2.0)
    assert out["r_net"] == pytest.approx((5.0 - 0.16) / 2.5)


def test_long_stop_hit():
    out = resolve_outcome(LONG, T, candles([(101, 97.0, 98.0)]))
    assert out["status"] == "STOP"
    assert out["r_gross"] == pytest.approx(-1.0)
    assert out["r_net"] == pytest.approx((-2.5 - 0.16) / 2.5)


def test_both_levels_in_one_candle_counts_as_stop():
    out = resolve_outcome(LONG, T, candles([(106, 97.0, 100.0)]))
    assert out["status"] == "STOP"
    assert "stop assumed first" in out["note"]


def test_short_target_hit():
    out = resolve_outcome(SHORT, T, candles([(101, 94.0, 95.0)]))
    assert out["status"] == "TARGET2"
    assert out["r_gross"] == pytest.approx(2.0)


def test_pending_while_nothing_is_hit():
    assert resolve_outcome(LONG, T, candles([(101, 99, 100)] * 3)) is None


def test_no_new_candles_is_pending():
    assert resolve_outcome(LONG, T, candles([(101, 99, 100)], start=T - pd.Timedelta(15, unit="min"))) is None


def test_expired_after_max_candles():
    out = resolve_outcome(LONG, T, candles([(101, 99, 100.0), (101, 99, 100.5), (102, 99, 101.0)]),
                          max_candles=3)
    assert out["status"] == "EXPIRED"
    assert out["candles_held"] == 3
    assert out["r_gross"] == pytest.approx(1.0 / 2.5)
    assert out["r_net"] == pytest.approx((1.0 - 0.16) / 2.5)


def test_history_not_starting_after_signal_is_unevaluable():
    out = resolve_outcome(LONG, T, candles([(106, 100, 105)], start=T + pd.Timedelta(30, unit="min")))
    assert out["status"] == "UNEVALUABLE"
    assert out["r_net"] is None


def test_gap_in_history_is_unevaluable():
    frame = candles([(101, 99, 100)] * 4).drop(index=1).reset_index(drop=True)
    out = resolve_outcome(LONG, T, frame)
    assert out["status"] == "UNEVALUABLE"
