# Analysis Report

## What this dataset is about

This dataset contains 1,200 ecommerce orders and 8 original columns:

- `order_id`: unique integer identifier.
- `customer_segment`: `New`, `Returning`, or `VIP`.
- `items_qty`, `unit_price_usd`, `shipping_usd`, `discount_pct`: transaction attributes.
- `order_total_usd`: recorded order total.
- `returned`: binary return flag.

Initial orientation findings:

- The schema is clean: no nulls in any column.
- `order_id` is unique in all 1,200 rows.
- `shipping_usd` is discretized to four values (`0`, `4.99`, `9.99`, `14.99`).
- `discount_pct` is discretized to five values (`0`, `5`, `10`, `15`, `20`).
- Returns are imbalanced but not rare: 105 of 1,200 orders were returned (8.75%).
- The surprising feature is `order_total_usd`, whose range is implausible for the other fields: from `-19,240.64` to `21,438.55`.

The natural basket formula

`items_qty * unit_price_usd * (1 - discount_pct / 100) + shipping_usd`

does not reproduce `order_total_usd` except in 4 rows (within rounding tolerance). That observation drove the rest of the analysis.

## Key findings

### 1. `order_total_usd` has a material data-integrity problem

Hypothesis: if `order_total_usd` is a valid transaction total, it should track the computed basket total closely and should not be negative when all component fields are nonnegative.

Evidence:

- 28 of 1,200 orders (2.33%) have negative recorded totals even though `items_qty`, `unit_price_usd`, `shipping_usd`, and `discount_pct` are all nonnegative.
- The correlation between computed basket total and recorded `order_total_usd` is only `r = 0.279`, far weaker than expected for a true total.
- The average recorded order total is `$1,093.43`, but if the 28 negative rows are excluded it rises to `$1,370.23`.
- Total recorded revenue is `$1,312,114.44`; excluding the negative rows raises it to `$1,605,911.70`.
- The median is less sensitive but still moves from `$764.29` to `$790.98`.

Figure evidence:

- `plots/order_total_vs_computed.png` shows that many orders sit far from the 45-degree line expected under simple basket arithmetic, and the negative-total rows are obvious outliers.
- `plots/order_gap_adjustments.png` shows the residual `order_total_usd - computed basket total`. While 79.2% of orders fall within `+/-$200`, 60 orders (5.0%) differ by more than `$5,000`, including 39 orders (3.25%) by more than `$10,000`.

Interpretation:

`order_total_usd` should not be used as a revenue metric without auditing upstream logic first. The anomalies are large enough to materially bias revenue totals and averages, not just a cosmetic edge case.

### 2. The dataset suggests an unobserved adjustment process layered onto otherwise ordinary baskets

Hypothesis: the mismatch between computed basket totals and recorded totals is not pure random noise; most orders will have small adjustments, but a minority will have extreme extra adjustments.

Evidence:

- The residual distribution is centered slightly above zero: median residual is `$46.83`.
- 79.2% of orders are within `+/-$200` of the computed basket total.
- There are no rows in the residual band `-$5,000` to `-$500`, but there are 28 rows below `-$5,000`, 21 rows between `$500` and `$5,000`, and 32 rows above `$5,000`.
- Extreme residuals are not explained by returns: return rate is 8.77% in non-extreme rows and 8.33% in rows with `|residual| > $1,000`.

Interpretation:

The observed pattern is more consistent with a two-part process than with ordinary rounding or tax differences:

- Most orders look like plausible basket totals plus a modest positive adjustment.
- A small tail looks like a separate process entirely, such as a system join error, duplicated external adjustment, sign inversion, or imported non-order ledger entries.

I cannot identify the exact mechanism from the available columns, but the residual structure is too systematic to dismiss.

### 3. Return behavior is largely unexplained by the available order fields

Hypothesis: return rates differ meaningfully by customer segment or by the observed transaction variables.

Evidence:

- Segment-level return rates are close: `VIP 10.6%` (19/179), `New 8.8%` (42/480), `Returning 8.1%` (44/541).
- A chi-square test of `customer_segment` vs `returned` is not significant (`p = 0.595`).
- Mann-Whitney tests found no significant return/non-return difference in `items_qty`, `unit_price_usd`, `shipping_usd`, `discount_pct`, `order_total_usd`, or computed basket total.
- A 5-fold cross-validated logistic regression using segment plus all numeric fields achieved `AUC = 0.492`, which is effectively no better than chance.

Figure evidence:

- `plots/return_rate_by_segment.png` shows overlapping 95% confidence intervals across all three segments.

Interpretation:

The available transactional fields do not contain meaningful predictive signal for returns. If return prediction is a business goal, important drivers are probably missing, such as product category, fulfillment quality, delivery timing, channel, geography, or customer history beyond the coarse segment label.

## What the findings mean

- The main actionable conclusion is data quality, not customer behavior. Revenue reporting based on `order_total_usd` is currently less trustworthy than any segment comparison or return analysis.
- The basket fields themselves look internally reasonable, so a pragmatic next step would be to rebuild a trustworthy revenue metric from `items_qty`, `unit_price_usd`, `discount_pct`, and `shipping_usd`, then reconcile it against the recorded total.
- The return signal is weak enough that decision-making should not rely on these columns alone for return-risk scoring.

## Limitations and self-assessment

Alternative explanations I considered:

- Negative totals might represent returns, refunds, or credits rather than bad data. The evidence does not support that strongly: only 3 of the 28 negative-total rows are marked as returned.
- Segment differences might still exist but be hidden by sample size. That is possible, especially for `VIP` with only 179 orders, but the observed effect sizes are small and the predictive model still fails.
- `order_total_usd` might include hidden taxes, fees, or bundle adjustments. That could explain the modest positive residuals, but not the extreme `+/-$10k` tail in otherwise ordinary orders.

Assumptions and gaps:

- I treated rows as independent orders because there is no customer identifier or time variable beyond sequential `order_id`.
- I assumed `order_id` ordering is roughly chronological, but I did not rely on that assumption for the main conclusions.
- I did not run causal analysis because the dataset is observational and lacks the variables needed to defend causal claims.
- I did not try complex ML models after the logistic baseline because the statistical tests already indicated that the available features carry very little return signal.

Bottom line:

The strongest conclusion is that `order_total_usd` is not a reliable standalone measure of order value in this dataset. Any substantive business interpretation should start with fixing or replacing that field.
