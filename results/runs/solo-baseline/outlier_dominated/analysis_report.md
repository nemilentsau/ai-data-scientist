# E-Commerce Order Returns: Data Analysis Report

## 1. Dataset Overview

| Property | Value |
|----------|-------|
| Rows | 1,200 |
| Columns | 8 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Duplicate order IDs | 0 |

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | int | Unique order identifier (10000-11199) |
| `customer_segment` | str | New (480), Returning (541), VIP (179) |
| `items_qty` | int | Items per order (1-19, uniform-like) |
| `unit_price_usd` | float | Price per item ($1.01-$199.98) |
| `shipping_usd` | float | 4 tiers: $0.00, $4.99, $9.99, $14.99 |
| `discount_pct` | int | 5 levels: 0%, 5%, 10%, 15%, 20% |
| `order_total_usd` | float | Order total (-$19,241 to $21,439) |
| `returned` | binary | Return flag: 0 (1,095) / 1 (105) = 8.75% return rate |

## 2. Data Quality Issues

### 2.1 Order Total Anomaly (Critical Finding)

The `order_total_usd` column does **not** follow the expected formula:

```
expected = items_qty * unit_price_usd * (1 - discount_pct/100) + shipping_usd
```

- Only **6 out of 1,200 rows** (0.5%) match this formula within $0.05.
- **28 orders have negative totals** (as low as -$19,241), which is commercially impossible.
- **67 orders** are IQR outliers in order total.
- The difference between actual and expected totals ranges from -$19,792 to +$19,868.

An OLS regression of `order_total_usd` on the available features yields **R-squared = 0.070** — the features explain only 7% of variance in order total. Residuals are heavily leptokurtic (kurtosis = 28.3), indicating extreme non-normality.

**Interpretation:** The order total either (a) incorporates additional factors not present in the dataset (taxes, multi-item discounts, promotions, partial refunds), (b) contains systematic data corruption, or (c) was generated with substantial random noise. The heavy tails and negative values suggest data quality problems rather than hidden variables alone.

### 2.2 Data Otherwise Clean

- No missing values in any column.
- No duplicate orders.
- `items_qty`, `unit_price_usd`, `shipping_usd`, and `discount_pct` all have plausible ranges.
- VIF values for all features are near 1.0 (no multicollinearity).

## 3. Exploratory Data Analysis

### 3.1 Feature Distributions

- **items_qty**: Approximately uniform over 1-19 (mean 9.8, std 5.6).
- **unit_price_usd**: Approximately uniform over $1-$200 (mean $103.8, std $57.5).
- **shipping_usd**: Roughly uniform across 4 tiers ($0, $4.99, $9.99, $14.99).
- **discount_pct**: Roughly uniform across 5 levels (0%, 5%, 10%, 15%, 20%).
- **order_total_usd**: Heavy-tailed, centered near $764 (median), with extreme values in both tails.

> See: `plots/01_distributions.png`

### 3.2 Customer Segments

| Segment | Orders | Return Rate | Avg Order Total |
|---------|--------|-------------|-----------------|
| New | 480 (40.0%) | 8.75% | $1,137 |
| Returning | 541 (45.1%) | 8.13% | $978 |
| VIP | 179 (14.9%) | 10.61% | $1,280 |

Return rates are nearly identical across segments. Chi-squared test: p = 0.595 (no significant difference).

> See: `plots/02_segment_analysis.png`

### 3.3 Return Rates by Discount and Shipping

**By discount:** Rates range from 7.4% (20% discount) to 10.8% (10% discount). Chi-squared p = 0.784 — not significant.

**By shipping tier:** Rates range from 6.5% ($0 shipping) to 10.5% ($9.99 shipping). Chi-squared p = 0.336 — not significant.

> See: `plots/03_return_by_discount_shipping.png`

### 3.4 Correlations

No meaningful correlations exist between `returned` and any feature. The strongest correlation involving `returned` is with `shipping_usd` at r = 0.04. The `order_total_usd` correlates moderately with `expected_total` (r = 0.26), confirming the anomaly in order totals.

> See: `plots/04_correlation_matrix.png`, `plots/05_order_total_anomaly.png`

## 4. Statistical Testing

### 4.1 Tests for Association with Returns

| Test | Feature | Statistic | p-value | Conclusion |
|------|---------|-----------|---------|------------|
| Chi-squared | customer_segment | 1.037 | 0.595 | Not significant |
| Chi-squared | discount_pct | 1.738 | 0.784 | Not significant |
| Chi-squared | shipping_usd | 3.388 | 0.336 | Not significant |
| Mann-Whitney U | items_qty | 55,255 | 0.510 | Not significant |
| Mann-Whitney U | unit_price_usd | 60,518 | 0.372 | Not significant |
| Mann-Whitney U | order_total_usd | 58,545 | 0.755 | Not significant |
| Mann-Whitney U | expected_total | 59,355 | 0.582 | Not significant |
| Mann-Whitney U | total_anomaly | 54,601 | 0.395 | Not significant |

**No feature shows a statistically significant association with returns at any conventional significance level.**

### 4.2 Effect Sizes

All effect sizes are **negligible**:

- Cohen's d for all continuous features: |d| < 0.15
- Cramer's V for all categorical features: V < 0.06

### 4.3 Randomness Tests

- **Wald-Wolfowitz Runs test:** p = 0.768 (no evidence against randomness in the sequence of returns)
- **Return rate by order ID decile:** All 10 bins have return rates between 5.0% and 10.8%, with no binomial test rejecting the null (all p > 0.19)

### 4.4 Logistic Regression (Statsmodels)

Full model with all features and interactions:

- **LLR p-value = 0.738** (model is not significantly better than intercept-only)
- **Pseudo R-squared = 0.010** (effectively zero explanatory power)
- **No individual coefficient is significant** (all p > 0.14)
- **Hosmer-Lemeshow test:** p = 0.766 (model fits adequately — but only because it converges to predicting the base rate for everyone)

## 5. Predictive Modeling

Three classifiers were trained on a 75/25 stratified split with the target variable `returned`:

### 5.1 Model Comparison

| Model | Test ROC AUC | 5-Fold CV AUC | Precision (class 1) | Recall (class 1) |
|-------|-------------|---------------|---------------------|-------------------|
| Logistic Regression | 0.502 | 0.503 +/- 0.043 | 0.00 | 0.00 |
| Random Forest | 0.440 | 0.513 +/- 0.043 | 0.00 | 0.00 |
| Gradient Boosting | 0.468 | 0.518 +/- 0.054 | 0.00 | 0.00 |
| **Baseline (majority)** | **0.500** | **0.500** | **--** | **--** |

All models achieve ROC AUC approximately equal to 0.50 (random chance). No model can identify returns better than flipping a coin. All models default to predicting the majority class (not returned) for every observation.

> See: `plots/07_model_curves.png`, `plots/08_feature_importance.png`, `plots/09_confusion_matrices.png`

### 5.2 Feature Importance (from Random Forest)

The Random Forest assigns importance based on variance reduction, not predictive value for the target. The top features (`total_anomaly`, `order_total_usd`, `unit_price_usd`) have high variance but no discriminative power for returns.

### 5.3 Model Assumptions

- **Logistic regression:** VIF values near 1.0 (no multicollinearity). Hosmer-Lemeshow adequate. But the fundamental assumption that a linear combination of features relates to log-odds of return is unsupported — no feature has a significant relationship.
- **OLS for order_total:** Residuals violate normality severely (kurtosis 28.3, Shapiro-Wilk p < 0.001). The Q-Q plot shows extreme departures in both tails. The model is unreliable for inference on order totals.

> See: `plots/10_ols_residuals.png`

## 6. Key Findings

### Finding 1: Returns Are Essentially Random

The 8.75% return rate is **uniformly distributed** across all customer segments, discount levels, shipping tiers, price ranges, and order quantities. No statistical test, effect size measure, or machine learning model finds any signal. The Wald-Wolfowitz runs test confirms no sequential pattern. **Returns in this dataset appear to be generated by a Bernoulli process with p ~ 0.0875, independent of all observed features.**

### Finding 2: Order Total Contains Severe Anomalies

The `order_total_usd` field cannot be explained by the other columns. It contains negative values, extreme outliers, and deviates from the expected pricing formula for 99.5% of orders. The OLS model explains only 7% of its variance. This column is either corrupted or dependent on unobserved variables.

### Finding 3: Feature Distributions Are Synthetic

The near-uniform distributions of `items_qty` (1-19), `unit_price_usd` ($1-$200), `shipping_usd` (4 exact tiers), and `discount_pct` (5 exact levels) suggest this dataset was **synthetically generated**, not derived from real e-commerce transactions. Real order data would show skewed distributions, seasonal patterns, and correlations between features (e.g., VIPs getting higher discounts).

### Finding 4: No Actionable Predictive Model Is Possible

Given the independence of returns from all features, no model — regardless of complexity — can predict returns from these variables. The ceiling for predictive performance is the base rate.

## 7. Recommendations

1. **Investigate the order_total_usd column.** If this is real data, the pipeline producing order totals has a critical bug. If synthetic, the generation process introduces unrealistic noise.

2. **Do not deploy a return-prediction model** based on these features alone. The data provides no signal for returns.

3. **Collect additional features** if return prediction is a business goal. Potentially useful: product category, customer history, time-to-return, review text, return reason codes, payment method, delivery time.

4. **Validate data provenance.** The uniform feature distributions and random returns suggest this dataset may be synthetic or a simulation. Confirm whether it represents real transactions before drawing business conclusions.

## 8. Plots Index

| File | Description |
|------|-------------|
| `plots/01_distributions.png` | Histograms of all numeric features |
| `plots/02_segment_analysis.png` | Return rate, order count, and AOV by segment |
| `plots/03_return_by_discount_shipping.png` | Return rate by discount % and shipping tier |
| `plots/04_correlation_matrix.png` | Pearson correlation heatmap |
| `plots/05_order_total_anomaly.png` | Actual vs expected total; anomaly distribution |
| `plots/06_returns_boxplots.png` | Feature distributions by return status |
| `plots/07_model_curves.png` | ROC and Precision-Recall curves for all models |
| `plots/08_feature_importance.png` | LR coefficients and RF feature importance |
| `plots/09_confusion_matrices.png` | Confusion matrices for all models |
| `plots/10_ols_residuals.png` | OLS residual diagnostics (Q-Q, fitted vs residual) |
| `plots/11_additional_analysis.png` | Anomaly by return status, rate by qty/price, segment composition |
