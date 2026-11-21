# Product one-pager: BTC Decision Engine

Status: DRAFT until the owner confirms. Date: 2026-11-18. Version 0.3, NOT validated.

**خلاصهٔ فارسی:** این ابزار فعلاً فقط در سطح ۱ (کنترل ریسک) و سطح ۲ (هشدار توجه) است. سطح ۳ (سیگنال اثبات‌شده) ادعا نمی‌شود، چون هیچ قاعده‌ای از گیت شواهد نگذشته است. هیچ پیامی از این ابزار توصیهٔ معامله نیست.

## 1. What it is
A decision-support tool for the owner's own MANUAL BTC trades on KCEX. It is not a trading bot, it places no orders, and it is not a signal service for other people.

## 2. Where it stands
| Level | Meaning | Status |
|---|---|---|
| 1. Risk control | Position-size estimate, a stop fixed before entry, NO TRADE when data is invalid or stale | ACTIVE. Deterministic arithmetic checked by synthetic tests written by the same author (not independent evidence). The size is an estimate, not an executable order quantity: exchange contract filters and liquidation are not modelled. |
| 2. Attention alerts | Telegram messages when something worth a look happens | ACTIVE and UNPROVEN. Rules are frozen in docs/ALERT_RULES_v1.md. Scheduled runs exist since 2026-11-17 (an hourly cron is configured), but GitHub's scheduler ran about 3 times per day in the first 3.5 days instead of hourly, and one of 11 runs failed. Events between runs can be missed. |
| 3. Proven signal | A rule whose forward evidence passes the evidence gate | NOT CLAIMED. No rule has passed. |

Earlier historical tests of 8 hypotheses (10 test lines: multi-timeframe alignment, derivatives-based rules, 20-day breakout) did not pass on development data. Their records are in the owner's local research log, not in this repository. They give no support for a signal claim.

## 3. Output
Exists today:
- Telegram status table: trend state of 6 timeframes (15m to 1M). Information only.
- Telegram alert "20-day break" (long or short): reference price, the broken level, a reference stop (1 daily ATR) and target (2x that distance). The same rule failed its historical test, so this is a prompt to look at the chart, NOT an entry signal. Each alert is logged on the alert-log branch (public) for later evaluation.
- Local read-only panel (panel.py): decision state of the v0.3 baseline and a position-size calculator for a manually chosen entry and stop. The live part needs futures data, which is currently blocked from the owner's network (HTTP 451); the calculator works offline.
- Forward tracker (scripts/forward.py): paper outcomes of the v0.3 baseline. It needs the same futures data.

Planned, not built: a daily "system is alive" message; a weekly counts report without conclusions; measured KCEX costs; a one-screen view with PROVEN and UNPROVEN labels.

## 4. Allowed inputs
- Closed candles from public market data (alerts use Binance spot via data-api.binance.vision; futures data only where reachable).
- Numbers the owner types in: equity, risk percent, entry, stop.
- Nothing else: no exchange API keys, no account access, no order execution. Secrets live only in GitHub Secrets.

## 5. Rules of use
- An alert is a prompt to look, never a reason to enter. No trade without a stop fixed before entry; the stop is not moved away.
- The calculator default is 0.5 percent of equity at risk per trade (adjustable). Check any estimated size against the real KCEX contract before an order.
- Prices come from spot and other venues, not KCEX. The 0.16 percent round-trip cost is an assumption until measured on KCEX.
- NO TRADE means no trade.

## 6. This product never says
"Validated", "proven", "profitable" or "safe" about any rule, score or tool unless the evidence gate says PASS. It never sets a return per day as a target and never presents a score as a probability.

## 7. Parked (do not start)
A candle-less "market state engine"; a level-2 order-book or raw-trade collector; new indicators or AI layers without a gate entry; automatic order execution; public distribution or marketing (platform terms and payment rules are unverified); any change that raises apparent confidence without evidence.

## 8. How level 3 would be earned
Through docs/GATE_v1.md (not written yet). Until it is frozen, nothing here counts as proven. Alerts of this type are infrequent, so a statistical conclusion can take years; INCONCLUSIVE is a valid outcome.

## 9. Known limits
- The alert scheduler is best effort. It was observed running about 3 times per day instead of hourly, so events between runs can be missed.
- The direction logic of the v0.3 baseline is a set of simple closed-candle EMA, RSI, ADX and ATR checks: a baseline to beat, not an edge.
- Open decisions D-008, D-009 and D-010 (see DECISION_LOG.md).
- Data feeds can fail; on failure the tool must show an error and no decision.
