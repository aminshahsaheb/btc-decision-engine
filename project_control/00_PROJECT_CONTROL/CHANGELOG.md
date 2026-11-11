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

## 2026-11-11 - decide() added
- Added src/decision.py: combines assess_data, assess_market, assess_direction, entry_trigger and plan_trade into four independent assessments.
- Fails closed: invalid/stale data, non-finite indicators and unexpected errors give NO TRADE; executable is always False.
- Added tests/test_decision.py (11 tests).
- analyze() and app.py unchanged.
- Evidence: 03_TEST_EVIDENCE/unit/decision_2026-11-11.txt

## 2026-11-11 - New journal and app connected to decide()
- Rewrote src/journal.py (new DB file, fingerprint, duplicate control).
- Rewrote app.py to use decide(); four assessments and reasons are shown; width=stretch replaces use_container_width.
- Added tests/test_journal.py and tests/test_app.py (headless app run with mocked data).
- Evidence: 03_TEST_EVIDENCE/integration/journal_app_2026-11-11.txt
- Limits: app tested with synthetic data only; outcomes table and contract filters not implemented.

## 2026-11-11 - First live app run
- app.py with decide() ran against live data; 91 tests passed (commit 47b3ffe).
- Observations and open decisions D-009 to D-014 recorded.
- Evidence: 03_TEST_EVIDENCE/integration/live_app_run_2026-11-11.md

## 2026-11-11 - Forward tracking added
- Journal now has source and candle_time; scheduled analyses are stored once per closed 15m candle.
- New outcomes table, src/outcomes.py (resolve_outcome, evaluate_pending, outcome_summary), src/scheduler.py, src/config.py, scripts/forward.py (run, loop, report).
- app.py stores manual analyses with candle_time.
- Evidence: 03_TEST_EVIDENCE/integration/forward_tracking_2026-11-11.txt
- Not yet run over time; no results exist.
