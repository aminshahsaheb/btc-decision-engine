# BTC Decision Engine v0.3 — Task Checklist

Status values: DONE / IN PROGRESS / PENDING / BLOCKED

## 1. Project protection
- [x] Separate v0.3 project directory
- [x] Keep v0.2 unchanged
- [x] Create development archive
- [x] Verify archive SHA256
- [x] Verify archive integrity

## 2. Data validation
- [x] Required OHLCV fields
- [x] Timestamp parsing and UTC handling
- [x] Duplicate and ordering checks
- [x] Candle interval alignment
- [x] OHLC relationship checks
- [x] Numeric and finite-value checks
- [x] Closed-candle filtering
- [ ] Review max_stale_intervals input
- [ ] Review order book price ordering
- [ ] Review spread and crossed-book checks
- [ ] Review snapshot freshness and synchronization
- [ ] Review API error handling

## 3. Indicators and engine
- [x] EMA implementation
- [x] RSI edge-case corrections
- [x] RSI tests
- [x] Directional movement readability update
- [ ] Validate ADX against an independent Wilder reference
- [ ] Connect directional movement tests to indicators()
- [ ] Review bias_of()
- [ ] Review market_structure()
- [ ] Review analyze()
- [ ] Test LONG, SHORT, and NO TRADE paths
- [ ] Review missing-value handling

## 4. Risk management
- [ ] Validate configuration inputs
- [ ] Verify stop-loss and target calculations
- [ ] Verify fees and slippage calculations
- [ ] Verify net risk/reward
- [ ] Verify equity and leverage limits
- [ ] Separate estimated quantity from executable quantity
- [ ] Add contract-filter requirements

## 5. Journal
- [ ] Review database path
- [ ] Handle NumPy and Pandas JSON values
- [ ] Record configuration and version
- [ ] Record data source and timestamps
- [ ] Add decision trace and error reasons
- [ ] Add duplicate protection
- [ ] Add journal tests

## 6. User interface
- [ ] Update labels and state keys to v0.3
- [ ] Display missing data as unavailable
- [ ] Improve error handling
- [ ] Display decision rationale
- [ ] Review journal display
- [ ] Test API outage behavior

## 7. Quality assurance and release
- [ ] Run full test suite
- [ ] Run warnings-as-errors tests
- [ ] Run integration tests
- [ ] Test application startup
- [ ] Test clean installation
- [ ] Complete documentation
- [ ] Create release archive
- [ ] Verify release SHA256
- [ ] Final review

## 8. Git and delivery
- [ ] Review Git status
- [ ] Commit approved changes
- [ ] Verify exact commit
- [ ] Run tests on exact commit
- [ ] Record final evidence

## Market Structure — 2026-11-11
- [x] Minimum row count corrected and tested.
- [x] Invalid lookback validation tested.
- [x] Missing columns and non-finite values tested.
- [x] Focused tests: 27 passed.
- [ ] Full project test suite.
- [ ] Remaining engine and data-pipeline audit.

## Verification — 2026-11-11
- [x] Full current test suite executed.
- [x] 40 tests passed; 0 failed.
- [x] Full-suite output saved as evidence.
- [ ] Audit remaining engine, data, risk, journal, and UI behavior.
