# Market Structure Review

Date: 2026-11-11
File: src/engine.py
Function: market_structure()

## Current implementation
- Default lookback: 20
- Prior range: df.iloc[-lookback-1:-1]
- Current candle: df.iloc[-1]
- Output: BULLISH BOS / BEARISH BOS / RANGE / NO BOS / UNKNOWN

## Findings

### MS-001 — Minimum row count
Status: CONFIRMED
Severity: Low

The current condition requires lookback + 2 rows.
The prior slice requires exactly lookback previous rows and one current row.
Therefore, the minimum is lookback + 1.

### MS-002 — Missing input validation
Status: OPEN
The function does not validate lookback or required columns.

### MS-003 — Invalid numeric values
Status: OPEN
NaN and infinite values are not explicitly rejected.

### MS-004 — Candle closure
Status: OPEN
The function assumes the current candle is closed.
The data pipeline currently filters open candles, but this contract
is not enforced inside this function.

### MS-005 — Insufficient behavioral tests
Status: CONFIRMED
The current test only checks that the output belongs to an allowed set.
It does not verify actual bullish or bearish breakouts.

## Required tests
- Exact minimum row count
- One row below minimum
- Bullish breakout
- Bearish breakout
- No breakout
- Invalid lookback
- Missing columns
- NaN and infinite values

## Decision
Do not modify the function until the behavioral tests are added
and the expected behavior is verified.

## Fix MS-001 — 2026-11-11
- Changed minimum row condition from lookback + 2 to lookback + 1.
- Created source backup: src/engine.py.pre_market_structure_fix
- Before-fix evidence: 3 failed, 8 passed.
- After-fix evidence: 11 passed.
- Compilation: PASS.
- After-fix test evidence:
  03_TEST_EVIDENCE/unit/market_structure_after_fix.txt
- MS-001 status: FIXED AND TESTED.
- Remaining input validation findings are still OPEN.

## Validation Fix — 2026-11-11

- MS-001 minimum row count: FIXED; 27 focused tests pass.
- MS-002 invalid lookback: FIXED; invalid types and non-positive values raise ValueError.
- MS-003 invalid numeric values: FIXED; non-finite inputs return UNKNOWN.
- Missing required columns and invalid DataFrame inputs return UNKNOWN.
- Regression and behavioral tests: 27 passed.
- Evidence: `03_TEST_EVIDENCE/unit/market_structure_after_validation_fix.txt`.
- Candle closure remains the responsibility of the data pipeline; it is not verified by this function.
