# Live fetch check - 2026-11-11

Read-only check of src.data.fetch_klines and fetch_derivatives_snapshot against public Binance Futures.

- 15m: OK, 499 rows, last candle open 2026-11-11 01:00 UTC, close 73376.2
- 1h:  OK, 499 rows, last candle open 2026-11-11 00:00 UTC, close 73514.4
- 4h:  OK, 499 rows, last candle open 2026-11-10 20:00 UTC, close 73762.9
- derivatives: OK, funding 9.412e-05, mark 73564.7, open interest 99740.336, book imbalance 0.861

Result: validate_ohlcv produced no false rejection on live data.
Limits: one-time check; says nothing about stability, outages, or trading value.
Observation: book imbalance 0.861 is extreme and is a single snapshot; the current 0.10 threshold is too easy to trigger.
