# BTC Decision Engine v0.3 — Architecture Specification

Date: 2026-11-11
Status: PROPOSED — NOT IMPLEMENTED
Version: 0.3

## 1. Objective

Build an auditable BTC trading decision-support engine.

The engine must assess:

1. Data validity.
2. Market tradability.
3. Directional evidence.
4. Entry validity.
5. Risk acceptability.

It must not promise profitability or place live orders.

## 2. Architecture boundaries

The system has seven logical layers:

1. Data Sources and Adapters
2. Data Integrity and Normalization
3. Indicators and Market Structure
4. Market Assessment
5. Directional Assessment
6. Trade Planning and Risk
7. Decision Journal and Evaluation

The user interface is a separate presentation layer.

The UI must not contain trading rules or duplicate engine calculations.

## 3. Decision contract

The engine must return four independent assessments.

### 3.1 Data status

- VALID
- INVALID
- STALE

INVALID or STALE data must prevent a valid trade setup.

### 3.2 Market status

- TRADEABLE
- NOT_TRADEABLE
- UNKNOWN

UNKNOWN must not be treated as TRADEABLE.

### 3.3 Directional bias

- BULLISH
- BEARISH
- NEUTRAL

Directional bias is not an entry signal.

### 3.4 Setup status

- VALID_LONG
- VALID_SHORT
- NO_ENTRY

A valid setup requires valid data, acceptable market conditions, a valid entry trigger, and passing risk checks.

### 3.5 Display examples

BULLISH BIAS — NO VALID ENTRY

BEARISH BIAS — NO VALID ENTRY

LONG SETUP

SHORT SETUP

WAIT

NO TRADE

The display label must not replace the four underlying assessments.

## 4. Data contract

Every market data record must preserve:

- Exchange
- Symbol
- Instrument type
- Timeframe
- Open time
- Close time
- Open
- High
- Low
- Close
- Volume
- Source timestamp
- Retrieval timestamp

All timestamps must use UTC.

Only fully closed candles may enter analysis.

The engine must detect:

- Missing candles
- Duplicate candles
- Invalid OHLC relationships
- Non-finite values
- Zero or negative prices
- Negative volume
- Unexpected intervals
- Stale data
- Timestamp inconsistencies

Data validation must fail closed.

A failed validation must not silently produce a valid setup.

## 5. Timeframes

Initial analytical timeframes:

- 15m: entry and short-term structure
- 1h: intermediate market context
- 4h: higher-timeframe context

Timeframe roles must be configurable.

All timeframes must be aligned by closed-candle timestamps.

The engine must not use future candles or future-derived features.

## 6. Data source design

Market data access must be separated from analytical logic.

Use an exchange adapter interface.

The initial implementation may use public Binance Futures market data.

Source failures must be explicit.

Network retries, timeouts, rate limits, and partial responses must be handled.

Snapshot data must include source and retrieval timestamps.

A snapshot must not be presented as historical evidence.

## 7. Indicator contract

Indicators must be pure, deterministic calculations.

Each indicator must define:

- Formula
- Input requirements
- Warm-up period
- Missing-data behavior
- Output range, where applicable
- Reference test cases

ADX and directional movement must follow a documented Wilder-compatible method.

Indicator tests must compare numerical values with independent reference calculations.

Output-label tests alone are insufficient.

## 8. Market structure

Market structure must distinguish:

- Swing highs
- Swing lows
- Higher highs
- Higher lows
- Lower highs
- Lower lows
- Break of structure
- Change of character
- Range
- Unclear structure

Pivot confirmation delay must be explicit.

A pivot must not be treated as known before its confirmation time.

No look-ahead is allowed.

## 9. Market and directional assessment

Market tradability and directional bias must be separate calculations.

The engine must document:

- Evidence used
- Evidence weight
- Thresholds
- Conflicts
- Missing evidence
- Reason for the final assessment

A score must not be described as a probability unless it has been statistically calibrated and independently validated.

## 10. Trade planning

A trade plan must define:

- Side
- Entry type
- Entry price or entry zone
- Trigger
- Stop-loss
- Take-profit levels
- Expected reward-to-risk ratio
- Estimated fees
- Estimated slippage
- Funding assumptions
- Maximum holding assumptions

An invalid or missing stop-loss must prevent a valid setup.

A directional bias alone must never create an entry.

## 11. Risk management

Position sizing must use:

- Account equity
- Risk budget
- Entry price
- Stop distance
- Contract specifications
- Quantity step
- Price tick
- Minimum quantity
- Minimum notional
- Fees
- Slippage

Unknown contract specifications must prevent executable quantity output.

Leverage must not be used to hide the underlying position risk.

All risk limits must be checked before a setup is accepted.

## 12. Decision journal

The v0.3 journal must be independent of the v0.2 database.

Each analysis record should preserve:

- Unique analysis ID
- UTC analysis time
- Engine version
- Configuration
- Data source
- Data timestamps
- Input fingerprint
- Four assessment outputs
- Reasons and warnings
- Trade plan, if valid

Decision records must be traceable and reproducible.

Trade outcomes must be stored separately from original decisions.

Duplicate analysis records must be controlled.

## 13. Error handling

Errors must be explicit and classified.

Examples:

- Network error
- Source unavailable
- Invalid response
- Insufficient history
- Stale data
- Data integrity failure
- Calculation failure
- Risk validation failure

A source failure must not be converted into a neutral market signal.

## 14. Testing requirements

Required test groups:

1. Data validation
2. Timestamp and candle closure
3. Indicator reference calculations
4. Market structure
5. No-look-ahead behavior
6. Market assessment
7. Directional assessment
8. Entry and exit planning
9. Position sizing
10. Fee and slippage calculations
11. Journal integrity
12. API failure handling
13. End-to-end decision behavior

Tests must include valid, invalid, boundary, and missing-data cases.

## 15. Research and validation

Engineering correctness is not evidence of profitability.

Before any performance claim, the system requires:

- Historical data quality checks
- Realistic fees and slippage
- Separate discovery and confirmation data
- Out-of-sample testing
- Walk-forward validation
- Multiple-testing controls
- Monte Carlo analysis
- Paper trading

No strategy is considered profitable without sufficient independent evidence.

## 16. Dependencies

Runtime dependencies currently identified:

- streamlit
- pandas
- numpy
- requests
- plotly

Python standard library modules include:

- sqlite3
- json
- math
- time
- pathlib

Testing dependencies must be separated from runtime dependencies.

Exact dependency versions and reproducible installation must be addressed before release.

## 17. Scope exclusions

Version 0.3 does not include:

- Live order execution
- Automatic leverage selection
- Guaranteed profit claims
- Unverified probability estimates
- Unvalidated strategy optimization

## 18. Approval and implementation status

This document is a proposed architecture.

No architecture component is marked implemented or tested by this document alone.

Changes require recorded reasons, implementation evidence, and relevant tests.
