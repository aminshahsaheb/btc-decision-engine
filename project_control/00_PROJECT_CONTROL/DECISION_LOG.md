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
