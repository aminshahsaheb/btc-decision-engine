# Daily trend alert v1 (UNPROVEN, paper record)

Date: 2026-11-25. Status: FROZEN once merged; a change needs TREND_ALERT_v2.md. The rule itself is the vendored file vendor/trend-setup/trendsetup.py (sha256 e5e17e3de5d8ed36b33712726cfe81256a0ee7ec8ad66cf87f2885fd3fc2bc6f, commit 5daf49a09b4ebf1a8405ec9cfd94d9563df71945 of btc-signal-lab, Draft PR #45, no independent review). This file describes delivery only.

**خلاصهٔ فارسی:** هشدار روزانهٔ روند فقط ثبت کاغذی و بدون ادعای مزیت است؛ مدل لانگ یا نقد است و هرگز شورت نیست.

## What it is
A long-or-flat daily attention alert for BTC, ETH, BNB, XRP, ADA, LTC and TRX. It sends a Telegram message only when the signal `sig` of a coin changes against the last SENT message. It is not a trading recommendation, places no orders and has no proven edge. Paper record since 2026-11-22.

## How
1. Step A, no secrets: verify the pinned file by sha256, fetch the full history of the 26-coin universe, cut it at each as-of date (never at the start), pass only the 7 coins to table_rows() so weights are slices of 7-coin capital, write trend_state.json.
2. Step B, with secrets: validate trend_state.json as untrusted input; write the daily rows and a PENDING message row and push them BEFORE the Telegram call; then SENT or UNCERTAIN. Files on the alert-log branch: trend_daily.csv (key date + symbol) and trend_msgs.csv (append-only state rows).
3. A late or missed run recomputes every date from the last logged date + 1 to the latest closed daily bar and sends ONE message for the net change.

## Rules
- A data problem (a coin missing, a stale bar, an unfinished warm-up, a signal outside {0, 0.2, ..., 1}) fails the run (red) and sends nothing. It is never read as EXIT TO CASH.
- A timeout is UNCERTAIN and is never resent for the same date. The next message is the net change against the last SENT state, so it can repeat information but never loses it.
- The job is red on UNCERTAIN or a recovered PENDING row.

## Limits
- The model enters at the open of the next day (00:00 UTC); the message arrives later and the price differs.
- The 7-coin track is not the 26-coin track of the lab; evaluating this alert needs its own 7-coin paper track.
- The scheduler is best effort; a day can be late or cancelled and is recovered by the next run.
- Tests here are synthetic and by the same author; the data comes from public spot prices.
