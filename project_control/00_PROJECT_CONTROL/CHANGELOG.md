# Changelog

## 2026-11-11 — Development tracking initialized
- Created the development management directory.
- Created four project control documents.
- Created the initial v0.3 source snapshot.
- Verified SHA256:
  b187173c823bab40e0036661444df6975b72bbd1fe8fde17bb6df0f0ce49ab24
- Verified archive integrity: PASS.
- No application source files changed in this step.

## 2026-11-11 — Market structure minimum-row fix
- Corrected minimum rows from lookback + 2 to lookback + 1.
- Added four behavioral tests.
- Before fix: 3 failed, 8 passed.
- After fix: 11 passed.
- Python compilation: PASS.
- Saved before/after test evidence.
- Input validation remains incomplete.

## 2026-11-11 — Market Structure validation
- Added strict lookback validation.
- Invalid DataFrame structure and non-finite required values now return UNKNOWN.
- Focused test suite: 27 passed.
- Evidence saved under `03_TEST_EVIDENCE/unit/`.

## 2026-11-11 — Full-suite verification
- Full current test suite passed: 40 tests.
- Output saved in `03_TEST_EVIDENCE/integration/full_suite_2026-11-11.txt`.

## 2026-11-11 - Live data check and cleanup
- Live fetch of 15m, 1h, 4h and derivatives passed validation.
- Moved .pre_* backup files out of src/ and tests/ to the local 07_BACKUPS folder (not in Git).
- Evidence: 03_TEST_EVIDENCE/integration/live_fetch_2026-11-11.md

## 2026-11-11 - Independent assessments added
- Added src/assessment.py: assess_data, assess_market, assess_direction (behavior copied from analyze(); analyze() not yet changed).
- Added tests/test_assessment.py (16 tests).
- Evidence: 03_TEST_EVIDENCE/unit/assessment_2026-11-11.txt
- Not yet integrated into analyze() or app.py.

## 2026-11-11 - Trade planning extracted
- Added src/planning.py: entry_trigger and plan_trade (behavior copied from analyze(); analyze() unchanged).
- plan_trade rejects invalid input, wrong-side stop, wide stop and low net R:R; quantity is always marked executable=False.
- Added tests/test_planning.py (12 tests) with hand-computed values.
- Logged D-009 and D-010 as OPEN.
- Evidence: 03_TEST_EVIDENCE/unit/planning_2026-11-11.txt
