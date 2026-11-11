import pandas as pd
import pytest

from src import data


def make_klines(count=220):
    now = pd.Timestamp.now(tz="UTC")
    last_open = now.floor("15min") - pd.Timedelta(15, unit="min")
    start = last_open - pd.Timedelta(15 * (count - 1), unit="min")
    rows = []

    for i in range(count):
        open_time = start + pd.Timedelta(15 * i, unit="min")
        open_ms = int(open_time.timestamp() * 1000)
        rows.append([
            open_ms, "100", "103", "99", "101", "10",
            open_ms + 15 * 60 * 1000 - 1,
            "1000", 10, "5", "500", "0"
        ])

    return rows


def test_fetch_klines_accepts_valid_closed_data(monkeypatch):
    rows = make_klines()
    monkeypatch.setattr(data, "get_json", lambda *a, **k: rows)

    result = data.fetch_klines("15m")

    assert len(result) == 220
    assert result["time"].is_monotonic_increasing
    assert "close_time" not in result.columns


def test_fetch_klines_rejects_invalid_close_time(monkeypatch):
    rows = make_klines()
    rows[0][6] = "invalid"
    monkeypatch.setattr(data, "get_json", lambda *a, **k: rows)

    with pytest.raises(ValueError, match="close_time"):
        data.fetch_klines("15m")


def test_fetch_klines_rejects_insufficient_closed_data(monkeypatch):
    rows = make_klines()
    now_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)

    for row in rows[-11:]:
        row[6] = now_ms + 60_000

    monkeypatch.setattr(data, "get_json", lambda *a, **k: rows)

    with pytest.raises(ValueError, match="کافی"):
        data.fetch_klines("15m")
def make_derivatives_responses():
    return {
        "/fapi/v1/premiumIndex": {
            "lastFundingRate": "0.0001",
            "markPrice": "65000"
        },
        "/fapi/v1/openInterest": {
            "openInterest": "1234"
        },
        "/fapi/v1/depth": {
            "bids": [["64999", "2"], ["64998", "3"]],
            "asks": [["65001", "1"], ["65002", "4"]]
        }
    }


def mock_derivatives_api(monkeypatch, responses):
    def fake_get_json(path, params=None):
        return responses[path]

    monkeypatch.setattr(data, "get_json", fake_get_json)


def test_fetch_derivatives_snapshot_accepts_valid_data(monkeypatch):
    responses = make_derivatives_responses()
    mock_derivatives_api(monkeypatch, responses)

    result = data.fetch_derivatives_snapshot()

    assert result["funding_rate"] == pytest.approx(0.0001)
    assert result["mark_price"] == pytest.approx(65000)
    assert result["open_interest"] == pytest.approx(1234)
    assert result["book_bid_qty"] == pytest.approx(5)
    assert result["book_ask_qty"] == pytest.approx(5)
    assert result["book_imbalance"] == pytest.approx(0)


def test_fetch_derivatives_snapshot_rejects_missing_funding(monkeypatch):
    responses = make_derivatives_responses()
    del responses["/fapi/v1/premiumIndex"]["lastFundingRate"]
    mock_derivatives_api(monkeypatch, responses)

    with pytest.raises((ValueError, KeyError)):
        data.fetch_derivatives_snapshot()


def test_fetch_derivatives_snapshot_rejects_nonfinite_mark_price(monkeypatch):
    responses = make_derivatives_responses()
    responses["/fapi/v1/premiumIndex"]["markPrice"] = "nan"
    mock_derivatives_api(monkeypatch, responses)

    with pytest.raises(ValueError):
        data.fetch_derivatives_snapshot()


def test_fetch_derivatives_snapshot_rejects_missing_open_interest(monkeypatch):
    responses = make_derivatives_responses()
    del responses["/fapi/v1/openInterest"]["openInterest"]
    mock_derivatives_api(monkeypatch, responses)

    with pytest.raises((ValueError, KeyError)):
        data.fetch_derivatives_snapshot()


def test_fetch_derivatives_snapshot_rejects_empty_order_book(monkeypatch):
    responses = make_derivatives_responses()
    responses["/fapi/v1/depth"]["bids"] = []
    responses["/fapi/v1/depth"]["asks"] = []
    mock_derivatives_api(monkeypatch, responses)

    with pytest.raises(ValueError):
        data.fetch_derivatives_snapshot()
