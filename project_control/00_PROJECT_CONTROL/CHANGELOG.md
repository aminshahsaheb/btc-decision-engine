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
