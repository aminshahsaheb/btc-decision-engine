from __future__ import annotations
import time
import requests
import pandas as pd

from src.validation import validate_ohlcv

BASE = "https://fapi.binance.com"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BTC-Decision-Engine/0.2"})

def get_json(path: str, params: dict | None = None):
    response = SESSION.get(BASE + path, params=params or {}, timeout=15)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("code") is not None and int(data.get("code", 0)) < 0:
        raise RuntimeError(data.get("msg", "Binance API error"))
    return data

def fetch_klines(interval: str, limit: int = 500) -> pd.DataFrame:
    raw = get_json("/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": interval, "limit": limit})
    if not isinstance(raw, list) or len(raw) < 220:
        raise ValueError(f"کندل کافی برای {interval} دریافت نشد.")
    cols = ["open_time","open","high","low","close","volume","close_time",
            "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
    df = pd.DataFrame(raw, columns=cols)
    df["time"] = pd.to_datetime(pd.to_numeric(df.open_time), unit="ms", utc=True)
    df["close_time"] = pd.to_numeric(df.close_time, errors="coerce")

    if df["close_time"].isna().any() or not df["close_time"].map(
        lambda value: pd.notna(value) and value >= 0
    ).all():
        raise ValueError("Invalid candle close_time received from Binance.")
    for col in ["open","high","low","close","volume","taker_buy_base","taker_buy_quote"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Keep only fully closed candles; never use the forming candle.
    now_ms = int(time.time() * 1000)
    df = df[df.close_time < now_ms].copy()
    df = df[["time","open","high","low","close","volume","taker_buy_base","taker_buy_quote"]].copy()

    if len(df) < 210:
        raise ValueError(f"پس از حذف کندل باز، دادهٔ کافی برای {interval} باقی نماند.")

    validate_ohlcv(df, interval)
    return df

def fetch_derivatives_snapshot() -> dict:
    premium = get_json(
        "/fapi/v1/premiumIndex",
        {"symbol": "BTCUSDT"}
    )
    oi = get_json(
        "/fapi/v1/openInterest",
        {"symbol": "BTCUSDT"}
    )
    depth = get_json(
        "/fapi/v1/depth",
        {"symbol": "BTCUSDT", "limit": 100}
    )

    if not isinstance(premium, dict):
        raise ValueError("Invalid premiumIndex response.")
    if not isinstance(oi, dict):
        raise ValueError("Invalid openInterest response.")
    if not isinstance(depth, dict):
        raise ValueError("Invalid order book response.")

    try:
        funding_rate = float(premium["lastFundingRate"])
        mark_price = float(premium["markPrice"])
        open_interest = float(oi["openInterest"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid derivatives value.") from exc

    import math

    if not math.isfinite(funding_rate):
        raise ValueError("Funding rate must be finite.")
    if not math.isfinite(mark_price) or mark_price <= 0:
        raise ValueError("Mark price must be finite and positive.")
    if not math.isfinite(open_interest) or open_interest <= 0:
        raise ValueError("Open interest must be finite and positive.")

    bids_raw = depth.get("bids")
    asks_raw = depth.get("asks")

    if not isinstance(bids_raw, list) or not isinstance(asks_raw, list):
        raise ValueError("Invalid order book levels.")
    if not bids_raw or not asks_raw:
        raise ValueError("Order book must contain bids and asks.")

    def parse_levels(levels):
        parsed = []
        for level in levels[:20]:
            if not isinstance(level, (list, tuple)) or len(level) != 2:
                raise ValueError("Invalid order book level.")

            try:
                price = float(level[0])
                quantity = float(level[1])
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid order book number.") from exc

            if (
                not math.isfinite(price)
                or not math.isfinite(quantity)
                or price <= 0
                or quantity <= 0
            ):
                raise ValueError("Order book values must be finite and positive.")

            parsed.append((price, quantity))

        if not parsed:
            raise ValueError("Order book has no valid levels.")

        return parsed

    bids = parse_levels(bids_raw)
    asks = parse_levels(asks_raw)

    bid_qty = sum(quantity for _, quantity in bids)
    ask_qty = sum(quantity for _, quantity in asks)

    denom = bid_qty + ask_qty
    if not math.isfinite(denom) or denom <= 0:
        raise ValueError("Invalid order book quantity total.")

    imbalance = (bid_qty - ask_qty) / denom

    return {
        "funding_rate": funding_rate,
        "mark_price": mark_price,
        "open_interest": open_interest,
        "book_imbalance": imbalance,
        "book_bid_qty": bid_qty,
        "book_ask_qty": ask_qty,
        "snapshot_time": pd.Timestamp.now(tz="UTC")
    }  

def load_all():
    data = {tf: fetch_klines(tf) for tf in ["15m","1h","4h"]}
    deriv = fetch_derivatives_snapshot()
    return data, deriv
