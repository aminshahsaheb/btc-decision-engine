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
