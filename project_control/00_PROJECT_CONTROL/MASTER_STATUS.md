# BTC Decision Engine v0.3 — Master Status

Last updated: 2026-11-11

## Project objective
Build a reliable, testable BTC market decision-support engine.
This version does not execute live orders.

## Project boundaries
- v0.2 must remain unchanged.
- All development changes must apply only to v0.3.
- Use closed candles only.
- Reject invalid, incomplete, stale, or misaligned data.
- A score is not a probability unless independently calibrated.
- Estimated quantity is not executable order quantity.
- Do not claim profitability without independent evidence.

## Current environment
- macOS
- Python 3.13.7
- Pandas 2.3.3
- NumPy 2.5.4
- Streamlit 1.67.0
- pytest 9.2.0
- Project: ~/Downloads/btc_decision_engine_v0_3

## Initial snapshot
File: 01_SOURCE_SNAPSHOTS/initial/v0.3_initial_2026-11-11.tar.gz
SHA256: b187173c823bab40e0036661444df6975b72bbd1fe8fde17bb6df0f0ce49ab24
SHA256 comparison: PASS
Archive integrity: PASS

## Verified test evidence
- engine.py compilation: PASS
- tests/test_engine.py: 7 passed
- Full project test suite: NOT YET VERIFIED

## Current status
Development is in progress.
No release has been approved.
No profitability claim is supported.

## Completion rule
A task is complete only when its implementation, relevant tests,
test evidence, and review are recorded.

## Latest verified milestone
- market_structure minimum-row condition: FIXED AND TESTED.
- Focused engine tests: 11 passed.
- Remaining market_structure input validation: OPEN.

## Latest verified milestone — 2026-11-11
Market structure minimum-row and input-validation fixes are applied.
Compilation passed. Focused engine tests: 27 passed.
Evidence: `03_TEST_EVIDENCE/unit/market_structure_after_validation_fix.txt`.
This confirms only the market_structure function and its focused tests. Full v0.3 completion is NOT established.

## Full-suite verification — 2026-11-11
- Full test suite: 40 passed, 0 failed.
- Evidence: `03_TEST_EVIDENCE/integration/full_suite_2026-11-11.txt`.
- This is a verified test milestone, not a release or proof of full project readiness.
