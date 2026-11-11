# Decision Log

## D-001 — Version isolation
Decision: Develop v0.3 independently.
Reason: Protect the existing v0.2 implementation.
Status: ACTIVE

## D-002 — Closed candles only
Decision: Do not use an unfinished candle for a decision.
Status: ACTIVE

## D-003 — Fail closed
Decision: Reject invalid, stale, incomplete, or misaligned input.
Status: ACTIVE

## D-004 — Score interpretation
Decision: A score must not be described as a probability without
independent calibration.
Status: ACTIVE

## D-005 — Order quantity
Decision: Do not present estimated quantity as executable quantity.
Real contract filters are required.
Status: ACTIVE

## D-006 — No live execution
Decision: v0.3 is a decision-support tool, not an order execution system.
Status: ACTIVE

## D-007 — Evidence-based completion
Decision: No task is complete without relevant tests and recorded evidence.
Status: ACTIVE

## D-008 — ADX reference
Decision: Compare the current EWM implementation with an independent
Wilder calculation before deciding whether to change it.
Status: OPEN

## D-009 — Funding evidence counted for both directions
Observation: normal funding (e.g. 0.0001) satisfies both "< 0.0005" (bull) and "> -0.0005" (bear), so both sides get a free point.
Decision: not decided. Copied unchanged into assess_direction. Evaluate by backtest before changing.
Status: OPEN

## D-010 — Order book imbalance weight
Observation: a live snapshot showed imbalance 0.861; the 0.10 threshold is easy to trigger and a single snapshot is not stable evidence.
Decision: not decided. Copied unchanged. Consider showing it as supporting evidence only.
Status: OPEN

## D-011 — Labels in decide() differ from the old analyze()
Change: when a direction exists but no valid entry/plan exists, the label is "<BULLISH|BEARISH> BIAS — NO VALID ENTRY".
Old analyze(): wide stop -> WAIT; low net R:R -> NO TRADE.
Reason: ARCHITECTURE_SPEC section 3.5 requires bias to be separate from entry.
Status: ACTIVE (analyze() and app.py not yet switched to decide()).

## D-012 — app.py switched to decide(); new journal
Change: app.py now calls decide() and shows the four assessments and reasons. The journal is a new file (decision_journal_v3.sqlite3) with analysis id, UTC time, engine version, config, four statuses, input fingerprint and full payload.
Duplicate control: an identical input fingerprint is not stored twice.
Not done: trade outcomes table (must stay separate from decisions), exchange contract filters.
Note: analyze() in engine.py is no longer used by app.py; it is kept for now and may be removed later.
Status: ACTIVE

## D-009 update — 2026-11-11
Live run confirmed it: the same funding value appears in both the bullish and the bearish evidence lists, so both sides get a free point. Still not changed. Status: OPEN

## D-010 update — 2026-11-11
Order book imbalance was +0.861 in the earlier live fetch and -0.351 in the app run (hours apart). Consistent with an unstable single-snapshot measure; not proof. Status: OPEN

## D-013 — Journal granularity
Observation: every button click created a new record (4 in under a minute) because the order book snapshot changes the fingerprint.
Proposal: one analysis per closed 15m candle, labeled manual or scheduled, so forward evaluation is not distorted.
Status: OPEN

## D-014 — Limits of backtesting
- Funding and order book imbalance have no historical snapshots, so the full decide() cannot be backtested honestly.
- The 5m 2021-2026 dataset is burned for new directional hypotheses under the btc-signal-lab research rules, and the v0.3 rules are EMA/RSI based.
- Therefore a historical backtest is only a sanity check. The forward journal (paper trading with a separate outcomes table) is the primary evidence source.
Status: OPEN

## D-013 update — 2026-11-11
Implemented: scheduled analyses store one record per closed 15m candle (source "scheduled"). Clicks in the app are stored as "manual" and are never counted in forward evaluation.
Status: IMPLEMENTED (not yet run over time)

## D-015 — Paper trade outcome rules
- Entry is assumed at the plan entry (close of the signal candle). No fill uncertainty is modelled.
- Only closed 15m candles after the signal candle are used.
- If one candle touches both stop and target 2, the stop is assumed to have been hit first.
- Target 1 is ignored; the trade ends at stop, target 2, or after 96 candles (EXPIRED, exit at that candle's close).
- r_net subtracts the estimated fees and slippage (cost_estimate) from the result, in units of risk.
- Missing or non-contiguous candle history gives UNEVALUABLE (stored, never silently dropped).
- Only scheduled records are evaluated.
Status: ACTIVE

## D-016 — Known gaps of forward tracking
- A failed fetch or validation stores nothing, so gaps in the journal are possible (only printed by the loop).
- The Mac must stay awake and online for the loop to record every candle.
- A handful of resolved trades proves nothing; no conclusion about an edge before a large sample.
Status: OPEN

## D-017 — Read-only live panel and position calculator
- panel.py shows decide() output and refreshes every 60 s. It never writes to the journal.
- A failed fetch shows an error and no decision (fail closed).
- src/risk_calc.position_size is an estimate for a manually chosen entry and stop. It never claims to be executable: contract filters and liquidation are not modelled.
- The panel is a checklist and risk guard; the engine has no evidence of profitability.
Status: ACTIVE
