# Alert rules v1 (attention alerts, UNVALIDATED)

Date: 2026-11-15. Frozen before the first live alert. A change needs a new version file (v2) with a dated reason; alerts of different versions are never pooled.

## Purpose
Send a Telegram message at moments that deserve attention. No trading edge is claimed. Entry is manual.

## Data
Binance spot BTCUSDT (data-api.binance.vision), closed candles only (close time before now), intervals 15m, 1h, 4h, 1d, 1w, 1M. Last 400 closed bars per interval. A fetch error or stale data sends nothing.

## State of a timeframe
z = (close - EMA20) / ATR14 on that timeframe. EMA20: first value = first close, factor 2/21. ATR14: Wilder, first value = mean of TR over bars 2..15. State = +1 if z > 0.5, -1 if z < -0.5, otherwise 0. Valid from bar index 20.

## Alert A (STATE)
When the state of the 1d, 1w or 1M timeframe differs from the state of its previous bar, for the last 2 closed bars. Informational.

## Alert B (BREAK20D)
For each of the last 4 closed 1h bars: level high = highest high and level low = lowest low of the 20 daily bars completed before that 1h bar closed.
- LONG: previous 1h close <= level high and this 1h close > level high.
- SHORT: previous 1h close >= level low and this 1h close < level low.
- At most one alert per side per 24 hours (the earlier logged alert counts).
- Reference price = the 1h close. R = ATR14 of the daily bars completed at that time. LONG: stop = ref - R, target = ref + 2R. SHORT is the mirror. Time limit 168 hours.

## Deduplication and log
Each event has a key (type, side, bar open time). A key already in alerts.csv on the alert-log branch is never sent again. Nothing is logged unless it was sent.

## Later evaluation (not part of the alert)
Outcome from 1h bars after the alert bar, entry at the reference price: first touch of stop or target (stop first if both in one bar), otherwise exit at the close 168 hours later. Cost 0.16 percent of the reference price. r_net = (pnl - cost) / R. A statistical conclusion needs at least 100 alerts per side; the frequency is unknown and may need years.

## Limits
Spot price differs from perpetual futures and from the venue where the user trades. The scheduler is best effort (delays of minutes are normal). Public repository: the alert log is public.
