# Live app run - 2026-11-11 (manual, from screenshots)

app.py (v0.3, using decide()) was run with streamlit against live public Binance Futures data.

- Label: WAIT; data VALID; market NOT_TRADEABLE; direction NEUTRAL (bull 3 / bear 5); setup NO_ENTRY.
- Market: close 73,823.90; RSI 55.0; ADX 7.5; ATR 0.265%; volume ratio 0.58.
- Derivatives snapshot: funding 0.0094%; order book imbalance -0.351; open interest 100,437.11.
- Reasons shown: trend strength too low; relative volume too low; market not tradeable.
- Bull evidence: close above EMA50; RSI >= 52; funding below 0.0005.
- Bear evidence: 1h bias bearish; 4h bias bearish; EMA20 below EMA50; order book imbalance < -0.10; funding above -0.0005.
- Journal: 4 records in under one minute (each click stored, since the snapshot differs every time).

Limits: one manual observation; no trading conclusion can be drawn from it.
