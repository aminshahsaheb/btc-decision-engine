from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PANEL = Path(__file__).resolve().parent.parent / "panel.py"
FREQ = {"15m": "15min", "1h": "1h", "4h": "4h"}
DERIV = {"funding_rate": 0.0001, "mark_price": 65000.0, "open_interest": 1234.0,
         "book_imbalance": 0.1, "book_bid_qty": 5.0, "book_ask_qty": 4.0,
         "snapshot_time": pd.Timestamp("2026-11-11T01:00:00Z")}


def make_market():
    now = pd.Timestamp.now(tz="UTC")
    out = {}
    for tf, freq in FREQ.items():
        step = pd.tseries.frequencies.to_offset(freq)
        last_open = now.floor(freq) - step
        times = pd.date_range(end=last_open, periods=300, freq=freq)
        i = np.arange(300)
        close = 100 + 0.05 * i + 2 * np.sin(i / 3)
        open_ = close - 0.3
        out[tf] = pd.DataFrame({
            "time": times, "open": open_,
            "high": np.maximum(open_, close) + 1, "low": np.minimum(open_, close) - 1,
            "close": close, "volume": 10.0 + (i % 5),
            "taker_buy_base": 5.0, "taker_buy_quote": 500.0,
        })
    return out


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_panel_runs_and_does_not_journal(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    from src import data, journal

    db = tmp_path / "panel_test.sqlite3"
    monkeypatch.setattr(journal, "DB", db)
    monkeypatch.setattr(data, "load_all", lambda: (make_market(), DERIV))

    at = AppTest.from_file(str(PANEL), default_timeout=60).run()
    assert not at.exception
    assert at.title[0].value == "BTC Panel"
    assert not db.exists()


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_panel_shows_error_when_fetch_fails(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from src import data

    def boom():
        raise RuntimeError("offline")

    monkeypatch.setattr(data, "load_all", boom)
    at = AppTest.from_file(str(PANEL), default_timeout=60).run()
    assert not at.exception
    assert any("offline" in e.value for e in at.error)
