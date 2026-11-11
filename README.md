# BTC Decision Engine

Decision-support tool for BTC/USDT perpetual futures (public Binance market data).

## Status
Version 0.3 is under development. It is NOT validated.

- It does NOT place orders and needs no API keys.
- No backtest, walk-forward or paper-trading evidence exists yet.
- Nothing here is financial advice and no profitability is claimed.
- Tests passing means the code behaves as tested, not that any strategy is profitable.

## Run
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py

## Tests
pip install pytest && python -m pytest -q

## Documents
- ARCHITECTURE_SPEC.md: proposed design
- PROJECT_LOG.md: project log
- project_control/: status, decisions, changelog, test evidence

No license is granted yet (all rights reserved by default).
