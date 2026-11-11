# BTC Decision Engine v0.3 — Project Log

## 1. Project identity

- Project: BTC Decision Engine
- Version: 0.3
- Start date: 2026-11-11
- Status: INITIALIZATION
- Previous version: v0.2
- Rule: v0.2 must remain unchanged.

## 2. Project objective

Build an evidence-based BTC trading decision-support engine.

The engine must answer:

1. Is the market suitable for a trade now?
2. Is bullish or bearish evidence stronger?
3. Is there a valid entry, stop-loss, and take-profit plan?
4. Is the planned risk acceptable?

The engine must not promise profits or produce trades only to increase signal frequency.

## 3. Core principles

- Data integrity comes before analysis.
- A directional bias is not an entry signal.
- Missing or invalid data must not produce a valid trade.
- Risk limits must be enforced.
- Every decision must be traceable to its inputs and configuration.
- Tests must verify calculations, not only output labels.
- No stage is complete without test evidence.
- Engineering tests do not prove trading profitability.
- Backtests must include realistic fees and slippage.
- Out-of-sample and paper-trading evidence are required.
- No live order execution in this version.

## 4. Version protection

Original v0.2:
~/Downloads/btc_decision_engine_v0_2

Backup:
~/Downloads/btc_decision_engine_v0_2_backup_20261111

New independent source:
~/Downloads/btc_decision_engine_v0_3

Do not edit or delete v0.2 or its backup during v0.3 development.

## 5. Initialization record

### 2026-11-11 — Backup

- Created v0.2 backup with `ditto`.
- Compared source files outside `.venv` with `rsync -anic`.
- No differences were reported.
- `.venv` was excluded from the comparison.
- Full environment equivalence was not tested.

### 2026-11-11 — v0.3 source copy

- Created a separate v0.3 directory.
- Excluded `.venv`, Python cache files, and pytest cache.
- Confirmed the expected application, source, test, and documentation files.
- Found two Streamlit skill symlinks.
- Removed those two symlinks from v0.3.
- Confirmed no symlinks remain.

### Initial files

- app.py
- src/__init__.py
- src/data.py
- src/engine.py
- src/journal.py
- tests/test_engine.py
- README_FA.md
- requirements.txt
- run_mac.command
- decision_journal.sqlite3

### Unverified item

`decision_journal.sqlite3` was copied from v0.2.
Its contents and migration requirements have not been inspected.
Do not use it as the v0.3 journal until it is reviewed.

## 6. Planned architecture

1. Data Ingestion and Integrity
2. Indicators and Reference Calculations
3. Market Structure and Regime
4. Market Tradability Assessment
5. Directional Assessment
6. Entry and Trade Planning
7. Risk Management
8. Decision Journal and Evaluation
9. Historical Backtesting
10. Walk-Forward Validation
11. Monte Carlo Analysis
12. Paper Trading
13. Final Audit

## 7. Decision states

- NO TRADE: data is invalid or analysis is not reliable.
- WAIT: data is valid, but market or entry conditions are not suitable.
- BULLISH BIAS: bullish evidence is stronger; no valid entry is implied.
- BEARISH BIAS: bearish evidence is stronger; no valid entry is implied.
- LONG SETUP: a valid long plan passes all required checks.
- SHORT SETUP: a valid short plan passes all required checks.

A directional bias must never be presented as a confirmed entry.

## 8. Stage tracking

| Stage | Status | Evidence |
|---|---|---|
| v0.2 backup | COMPLETE WITH SCOPE LIMIT | rsync comparison outside .venv |
| v0.3 source copy | COMPLETE | directory and file listing |
| v0.3 symlink cleanup | COMPLETE | no symlinks remain |
| v0.3 environment setup | NOT STARTED | none |
| architecture specification | NOT STARTED | none |
| data integrity | NOT STARTED | none |
| indicator verification | NOT STARTED | none |
| market assessment | NOT STARTED | none |
| directional assessment | NOT STARTED | none |
| trade planning | NOT STARTED | none |
| risk management | NOT STARTED | none |
| journal and evaluation | NOT STARTED | none |
| unit and integration tests | NOT STARTED | none |
| backtesting | NOT STARTED | none |
| walk-forward validation | NOT STARTED | none |
| Monte Carlo validation | NOT STARTED | none |
| paper trading | NOT STARTED | none |
| final audit | NOT STARTED | none |

## 9. Change log

No application code has been changed in v0.3 yet.

Every future change must record:

- Date
- Reason
- Files changed
- Expected behavior
- Tests executed
- Test results
- Evidence
- Remaining limitations

## 10. Completion policy

A task may be marked COMPLETE only when:

1. The implementation exists.
2. Relevant tests pass.
3. Test output is recorded.
4. Known limitations are documented.
5. The result is reproducible.

A passing test suite does not prove that the strategy is profitable.

### 2026-11-11 — v0.2 journal archive

- Archived the copied v0.2 SQLite database at `archive/v0_2/decision_journal.sqlite3`.
- Original v0.2 directory was not modified.
- Records preserved: 3 (2 NO TRADE, 1 WAIT).
- SHA-256: `64c85394d19b29f76f268e020d8a74db7b68e5ed074a4ea511706b2494f14c97`
- A separate v0.3 journal database must be created by the v0.3 implementation.


### 2026-11-11 — Initial architecture specification

- Created `ARCHITECTURE_SPEC.md` as a proposed design document.
- Defined independent data, market, directional, and setup assessments.
- Defined initial data, risk, journal, testing, and validation requirements.
- No application code was changed.
- Architecture approval and implementation remain pending.
