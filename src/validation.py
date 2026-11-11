from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED = ["time", "open", "high", "low", "close", "volume"]

_TIMEFRAME_MAP = {
    "15m": pd.Timedelta(15, unit="min"),
    "15min": pd.Timedelta(15, unit="min"),
    "1h": pd.Timedelta(1, unit="h"),
    "4h": pd.Timedelta(4, unit="h"),
}


def validate_ohlcv(
    df: pd.DataFrame,
    timeframe: str,
    now=None,
    max_stale_intervals: int = 2,
) -> None:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("OHLCV data is empty.")

    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    try:
        interval = _TIMEFRAME_MAP[timeframe]
    except (KeyError, TypeError):
        raise ValueError("Unsupported timeframe.") from None
    if interval <= pd.Timedelta(0):
        raise ValueError("Invalid timeframe.")

    x = df.copy()
    x["time"] = pd.to_datetime(x["time"], utc=True, errors="coerce")

    if x["time"].isna().any():
        raise ValueError("Invalid candle timestamps.")

    if x["time"].duplicated().any():
        raise ValueError("Duplicate candle timestamps.")

    if not x["time"].is_monotonic_increasing:
        raise ValueError("Candle timestamps are not ordered.")

    ns = x["time"].astype("int64")
    if (ns % interval.value != 0).any():
        raise ValueError("Candle timestamps are not aligned to timeframe.")

    if len(x) > 1 and not (x["time"].diff().dropna() == interval).all():
        raise ValueError("Missing or unexpected candle intervals.")

    numeric = ["open", "high", "low", "close", "volume"]
    for col in numeric:
        x[col] = pd.to_numeric(x[col], errors="coerce")

    values = x[numeric].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite OHLCV values.")

    if (x[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Prices must be positive.")

    if (x["volume"] < 0).any():
        raise ValueError("Volume cannot be negative.")

    if (
        (x["high"] < x[["open", "close", "low"]].max(axis=1)).any()
        or (x["low"] > x[["open", "close", "high"]].min(axis=1)).any()
    ):
        raise ValueError("Invalid OHLC relationships.")

    for col in ["taker_buy_base", "taker_buy_quote"]:
        if col in x.columns:
            v = pd.to_numeric(x[col], errors="coerce")
            if not np.isfinite(v.to_numpy(dtype=float)).all() or (v < 0).any():
                raise ValueError(f"Invalid {col} values.")

    if "taker_buy_base" in x.columns:
        taker = pd.to_numeric(x["taker_buy_base"], errors="coerce")
        if (taker > x["volume"]).any():
            raise ValueError("Taker buy volume exceeds total volume.")

    current = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    current = current.tz_localize("UTC") if current.tzinfo is None else current.tz_convert("UTC")

    candle_close = x["time"].iloc[-1] + interval
    age = current - candle_close

    if age < pd.Timedelta(0):
        raise ValueError("Latest candle is not closed.")

    if age > interval * max_stale_intervals:
        raise ValueError("Latest candle is stale.")
