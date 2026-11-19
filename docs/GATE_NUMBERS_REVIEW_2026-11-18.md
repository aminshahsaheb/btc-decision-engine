# Gate numbers review: input for GATE_v1

Status: DRAFT proposal for the owner and the independent reviewer. Nothing here is frozen and no number is final. Date: 2026-11-18.

**خلاصهٔ فارسی:** با ۱۰۰ هشدار برای هر سمت فقط مزیتی نزدیک ۰.۳ تا ۰.۴ R قابل‌تشخیص است و رسیدن به ۱۰۰ هشدار برای هر سمت ۳.۴ تا ۶.۳ سال طول می‌کشد. مزیت کوچک‌تر INCONCLUSIVE می‌ماند. این صفحه گزینه‌ها را برای بازبین می‌آورد و تصمیم نمی‌گیرد.

## 1. Measured inputs
Source: the owner's local research log (not in this repository). Period 2021-02-01 to 2025-06-30. Frequency uses events only, no outcomes. Rule: the 20-day breakout of ALERT_RULES_v1 (alert B), 24-hour same-side cooldown.

| Item | Value |
|---|---|
| Span | 52.9 months |
| Events | 201 (long 131, short 70) |
| Per month | 3.80 (long 2.48, short 1.32) |
| Spread of r_net per trade (122 closed trades) | SD 1.336 R (long 1.339, short 1.344) |
| Historical result of the same rule | mean -0.012 R, 95 percent block-bootstrap interval -0.23 to +0.21 R |

## 2. What the arithmetic says
Normal approximation, one-sided test, 80 percent power, independent trades, SD 1.336 R. Descriptive arithmetic, not a test of any hypothesis.

| Alerts n | Smallest detectable true mean (alpha 0.05) | (alpha 0.0125) | Months to reach n, both sides pooled | Years to reach n per side (long / short) |
|---|---|---|---|---|
| 30 | 0.61 R | 0.75 R | 8 | 1.0 / 1.9 |
| 60 | 0.43 R | 0.53 R | 16 | 2.0 / 3.8 |
| 100 | 0.33 R | 0.41 R | 26 | 3.4 / 6.3 |
| 300 | 0.19 R | 0.24 R | 79 | 10.1 / 18.9 |

- Detecting a true mean of 0.10 R needs about 1,100 alerts (alpha 0.05), roughly 57 years for the long side at the historical rate.
- An SD near 1.3 R follows from the 1R stop and 2R target exits; any rule using them is expected to have a similar spread.
- The historical interval above makes a true mean of 0.33 R or more unlikely for this rule. A forward test of 100 alerts therefore mostly examines an effect size that the development data already makes unlikely. This is an observation, not a verdict; the market regime can change.

## 3. Facts about the frozen text
ALERT_RULES_v1 is FROZEN and states that a statistical conclusion needs at least 100 alerts per side. That is a necessary minimum, not a test. Any change is ALERT_RULES_v2 and counting restarts from zero. This review did not check the alert-log branch for existing scheduled alerts; if none exist, a change now loses nothing.

## 4. Options for the reviewer (not decisions)
- A. Per side (as v1) or one pooled test of both sides. Pooled reaches 100 alerts in about 26 months but contradicts the v1 wording, so it needs v2.
- B. A sequential futility stop with pre-stated checkpoints (for example n = 30 and 60 pooled): if the upper bound of the one-sided interval for the mean is below a pre-stated minimum useful effect, the verdict is FAIL; otherwise continue. The error-spending rule and the numbers are for the reviewer to set.
- C. State the minimum detectable effect as an explicit line of the gate, and require every verdict to report the interval.
- D. Count and report the ideas tried on the same data. In the local log: 8 hypotheses (10 test lines), none passed on development data. Ideas tried inside btc-signal-lab are not counted here.
- E. Apply the gate only to rules that have a prior reason to work. For alert B the historical result gives no such reason, so a multi-year evaluation of it is questionable.

## 5. Not verified
The normal approximation and independence; the SD comes from one rule's trades; the forward frequency may differ from the development period; nothing here was reviewed independently.
