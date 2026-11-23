# Alert rules v2 (attention alerts, UNVALIDATED)

Date: 2026-11-24. Status: FROZEN once merged to main. A change needs ALERT_RULES_v3.md. docs/ALERT_RULES_v1.md stays frozen and unedited.

## What stays the same
Data source, the timeframe states, Alert A (STATE), Alert B (BREAK20D), the stop and target definitions and the later-evaluation rule are exactly as in v1. No new alert features. Alert B stays an UNPROVEN side alert: a historical replay of its exact rule gave about +0.02 R after 2023 (not evidence), and the same rule failed its development-period test.

## What changes (delivery and logging, not the signal definitions)
1. Scan: the last 24 closed 1h bars (v1: 4). State changes still use the last 2 bars.
2. Write-ahead log in the file alerts_v2.csv on the alert-log branch (append-only; one row per state change, the last row of a key is its current state; column rules_version = v2). alerts.csv (v1) is not modified.
3. State machine: a new alert is saved and pushed as PENDING BEFORE the Telegram call. Afterwards it becomes SENT (Telegram answered ok=true) or UNCERTAIN (a timeout or any other answer). An UNCERTAIN alert is NEVER resent, because a message can arrive after the client gave up (run #10 of 2026-11-20).
4. A PENDING row older than 30 minutes at the next run becomes UNCERTAIN (note: recovered).
5. The job is red when a run produces an UNCERTAIN or a recovered row, when the log cannot be pushed (then nothing is sent), or when data fails validation.
6. An alert older than 12 hours since its candle closed is logged as STALE and not sent.
7. Cooldown (Alert B): at most one alert per side within 24 hours. PENDING, UNCERTAIN, SENT and STALE rows and the v1 rows count, and the distance is checked in both directions.
8. The message shows the alert age (time since the candle closed) and says the reference price is the close of that candle.
9. Telegram send timeout 60 seconds. Dedupe by key against v1 and v2 rows.
10. One shared concurrency group (alert-log-writer) for every workflow that pushes to alert-log.

## Known defect of the v1 sample
On 2026-11-20 a v1 alert was delivered but never logged (the send timed out after delivery; nothing was written), so the 24-hour cooldown read an incomplete log. The v1 alert sample is therefore unreliable and is not pooled with v2.

## Evidence
Counting for any evidence gate restarts at the first v2 row. This file defines delivery behaviour only; it adds no claim about the signal.
