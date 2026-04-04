# Analysis Report

## What the dataset is about

This is an order-level ecommerce-style dataset with 1,200 rows and 8 columns: an order identifier, customer segment, quantity, unit price, shipping charge, discount rate, recorded order total, and a binary return flag.

The basic structure is clean: there are no nulls, `order_id` is unique for every row, `customer_segment` has three levels (`Returning`: 541, `New`: 480, `VIP`: 179), shipping is coded at four fixed price points (`0`, `4.99`, `9.99`, `14.99`), discounts are coded at five fixed percentages (`0`, `5`, `10`, `15`, `20`), and the overall return rate is 8.8% (105 of 1,200).

Two features require caution before interpretation:

1. `order_total_usd` contains 28 negative values (2.3% of rows), including extreme values down to -19,240.64. Most of those rows are **not** marked as returned (25 of 28), so they do not behave like standard refunds or cancellations.
2. `order_total_usd` cannot be exactly reconstructed from `items_qty`, `unit_price_usd`, `discount_pct`, and `shipping_usd`. Even after restricting to non-negative totals, the residual spread is large enough to suggest either hidden charges/taxes or synthetic noise. That means spending analyses should be treated as directional rather than accounting-precise.

Raw rows otherwise look plausible for an order table: quantities range from 1 to 19, unit prices from 5.63 to 199.89, and return is encoded as `0` or `1`.

## Key findings

### 1. Negative order totals are a small but material anomaly, not a valid business pattern

**Hypothesis:** The negative totals represent a meaningful business state such as returned orders or refunds.

**Test:** Compare negative-total rows with the `returned` flag and visualize all order totals across the full dataset.

**Result:** The hypothesis is refuted. Only 3 of the 28 negative-total rows are marked as returned. The remaining 25 sit among otherwise ordinary orders and span all three segments. [order_total_anomalies.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/plots/order_total_anomalies.png) shows these values as isolated points far below the rest of the data rather than a separate operational regime.

**Interpretation:** These rows are best treated as data anomalies or bookkeeping fields encoded inconsistently with the rest of the table. They are too few to dominate the dataset, but they are large enough to distort any average or model that uses `order_total_usd` naively. For that reason, all spending comparisons below use the 1,172 non-negative rows.

### 2. Customer segment does not explain spending once order composition is known

**Hypothesis:** VIP or returning customers place systematically larger orders than new customers.

**Test:** Compare cleaned order totals across segments, then fit a regression for `log(1 + order_total_usd)` using segment plus quantity, unit price, shipping, and discount.

**Result:** The segment-only story is weak. On the cleaned subset, median order totals are 758.12 for `New`, 813.93 for `Returning`, and 868.62 for `VIP`, but the overall distributional difference is not statistically significant (Kruskal-Wallis p = 0.292). This overlap is visible in [segment_total_clean_boxplot.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/plots/segment_total_clean_boxplot.png).

In the regression, `items_qty` and `unit_price_usd` dominate:

- `items_qty` coefficient: 0.129 on log-total, p < 0.001
- `unit_price_usd` coefficient: 0.013 on log-total, p < 0.001
- `customer_segment_Returning`: -0.044, p = 0.290
- `customer_segment_VIP`: -0.006, p = 0.917

The model explains about 71.6% of the variance in log-order-total, and almost all of that explanatory power comes from quantity and unit price rather than segment.

**Interpretation:** Apparent segment differences are mostly compositional. VIP customers do not appear to spend more because they are VIP; they spend more only insofar as they buy slightly more items or higher-priced items on a given order.

### 3. Returns are only weakly related to the observed order attributes

**Hypothesis:** Returns can be meaningfully predicted from segment, price, quantity, discount, shipping, and total.

**Test:** Check segment-level differences, compare return rates across price bands, and fit a cross-validated logistic regression.

**Result:** The evidence for strong return structure is weak.

- Segment is not associated with return at conventional significance levels (chi-square = 1.037, p = 0.595).
- The highest unit-price quintile has the highest return rate, but the effect is modest: 11.7% in the top quintile versus 8.0% in the other four combined, with chi-square p = 0.097. This pattern is shown in [return_rate_by_price_quintile.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/plots/return_rate_by_price_quintile.png).
- A logistic regression using all observed fields achieved mean 5-fold ROC AUC of 0.475 (std 0.047), which is effectively no predictive signal.

**Interpretation:** Returns in this dataset are close to irreducible given the available columns. There may be some weak tendency for high-priced items to be returned more often, but the dataset does not support operational targeting based on these variables alone.

### 4. Recorded order totals track discounted subtotal directionally, but not mechanically

**Hypothesis:** `order_total_usd` is a near-deterministic function of quantity, unit price, discount, and shipping.

**Test:** Compare the recorded total against a discounted subtotal estimate and fit a simple regression of `order_total_usd` on discounted subtotal plus shipping.

**Result:** The relationship is monotonic but not tightly accounting-based. The Spearman correlation between discounted subtotal and recorded total is 0.944, but the linear model explains only 13.6% of the variance, and the median markup over discounted subtotal plus shipping is 50.90 USD with a long right tail up to 19,867.89 USD. [total_vs_subtotal_clean.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/plots/total_vs_subtotal_clean.png) shows that totals generally rise with subtotal, but many points sit far above the one-to-one line.

**Interpretation:** The total field likely includes unobserved components or synthetic perturbation. It is still useful as a rough size metric after excluding negatives, but it should not be treated as a clean accounting target for reconciliation or margin analysis.

## Practical implications

- For spending analysis, exclude the 28 negative-total rows or handle them in a separate anomaly workflow.
- For customer strategy, segment labels alone are not a strong lever in this data. Order composition matters more than whether a customer is `New`, `Returning`, or `VIP`.
- For returns, the observed fields are inadequate for accurate prediction. Better signals would likely come from product category, fulfillment problems, customer history, or time-to-delivery, none of which are present here.

## Limitations and self-critique

- The largest limitation is field semantics. I assumed negative totals are data quality issues because they do not align with the return flag, but without documentation they could reflect an undocumented accounting process.
- I treated the non-negative subset as the best basis for monetary comparisons. If the negative rows are actually legitimate and systematically different, then the cleaned analyses understate that process.
- The weak return findings may reflect missing predictors rather than true randomness. A low-AUC model here means “little signal in these columns,” not “returns are inherently unpredictable.”
- I did not test causal claims, because the dataset is observational and lacks time, product, and customer-history fields. All findings are associative.
- The irregular relationship between `order_total_usd` and the other monetary columns means effect sizes tied to totals should be interpreted cautiously. This is especially important for any downstream forecasting or unit-economics work.
