# Marketing Campaign Dataset Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 1,000 |
| Columns | 8 |
| Null values | 0 |
| Duplicate rows | 0 |
| Duplicate campaign IDs | 0 |

**Columns:** `campaign_id`, `region`, `channel`, `ad_spend_usd`, `impressions`, `clicks`, `revenue_usd`, `month`

### Data Quality Assessment

The dataset is clean: no missing values, no duplicates, no negative values, no zero values in numeric fields. All 1,000 campaign IDs are unique. The data appears synthetically generated given its uniformity and lack of quality issues.

### Descriptive Statistics (Numeric)

| Metric | ad_spend_usd | impressions | clicks | revenue_usd |
|---|---|---|---|---|
| Mean | 24,768 | 284,200 | 8,423 | 61,979 |
| Std | 14,461 | 177,138 | 6,443 | 37,101 |
| Min | 729 | 7,126 | 145 | 1,481 |
| Median | 25,092 | 272,571 | 6,861 | 61,328 |
| Max | 49,986 | 709,259 | 34,102 | 155,838 |

### Categorical Distributions

- **Region:** Roughly balanced — North (261), South (258), West (241), East (240)
- **Channel:** Roughly balanced — Email (266), Search (258), Social (250), Display (226)
- **Month:** Ranges 1-12, approximately uniform (64-97 campaigns per month)

---

## 2. Exploratory Data Analysis

### Key Derived Metrics

| Metric | Mean | Min | Max |
|---|---|---|---|
| CTR (Click-Through Rate) | 0.030 | 0.010 | 0.050 |
| CPC (Cost Per Click) | $3.60 | $1.39 | $11.93 |
| ROAS (Return on Ad Spend) | 2.51 | 0.97 | 4.27 |

- **ROAS** is approximately normally distributed (mean ~2.5, std ~0.35), though formal normality tests reject normality due to heavier-than-normal tails (kurtosis = 4.98 vs. normal kurtosis of 3).
- Only 6 campaigns (0.6%) had ROAS below 1.5, and only 7 (0.7%) exceeded 3.5. Nearly all campaigns are profitable.
- One campaign had a ROAS of 0.97 (the only near-loss).

### Correlation Structure

| | ad_spend | impressions | clicks | revenue |
|---|---|---|---|---|
| ad_spend | 1.000 | 0.945 | 0.773 | 0.972 |
| impressions | 0.945 | 1.000 | 0.804 | 0.915 |
| clicks | 0.773 | 0.804 | 1.000 | 0.742 |
| revenue | 0.972 | 0.915 | 0.742 | 1.000 |

**Key finding:** Ad spend and revenue are extremely strongly correlated (r = 0.972). Impressions and ad spend are also highly correlated (r = 0.945), indicating impressions scale linearly with budget. Clicks are somewhat less correlated — reflecting natural variability in click-through behavior.

### Channel Performance

| Channel | Count | Mean ROAS | Mean CTR | Mean CPC |
|---|---|---|---|---|
| Display | 226 | 2.49 | 0.031 | $3.45 |
| Email | 266 | 2.50 | 0.030 | $3.71 |
| Search | 258 | 2.51 | 0.029 | $3.76 |
| Social | 250 | 2.53 | 0.030 | $3.59 |

All channels perform virtually identically. A one-way ANOVA on ROAS by channel yields F = 0.50, p = 0.68 — **no statistically significant difference**. The Kruskal-Wallis non-parametric test confirms this (p = 0.44). CTR differences are also non-significant (F = 1.46, p = 0.22). No pairwise CTR comparisons survive Bonferroni correction.

### Regional Performance

| Region | Count | Mean ROAS | Total Revenue |
|---|---|---|---|
| East | 240 | 2.52 | $15.6M |
| North | 261 | 2.47 | $16.1M |
| South | 258 | 2.50 | $15.9M |
| West | 241 | 2.55 | $14.4M |

Regional ROAS differences are marginal. ANOVA yields F = 2.30, p = 0.076 — **not significant at the 0.05 level**, though approaching borderline significance. The Kruskal-Wallis test also fails to reject (p = 0.16).

### Channel x Region Interaction

A two-way ANOVA testing region, channel, and their interaction on ROAS found:
- Region: F = 2.27, p = 0.079
- Channel: F = 0.49, p = 0.69
- Interaction: F = 0.45, p = 0.91

**No significant main effects or interaction effects** on ROAS. Marketing performance is remarkably uniform across all segments.

### Monthly Trends

No discernible seasonal pattern in ROAS, CTR, or spend. Monthly ROAS fluctuates within a narrow band around the global mean (2.51). Campaign counts vary from 64 (August) to 97 (October) but show no systematic trend.

### Spend Efficiency

ROAS does **not** vary with spending level. The correlation between ad spend and ROAS is r = -0.024, p = 0.45 (not significant). When grouped into spend deciles, mean ROAS is nearly identical across all deciles (~2.47-2.57). There is **no evidence of diminishing returns** at higher spend levels within the observed range.

### Outliers

- **Clicks:** 16 outlier campaigns (IQR method) — all on the high side, representing campaigns with unusually high engagement
- **ROAS:** 18 outlier campaigns — both tails, but very few (6 below 1.5, 7 above 3.5)
- **Low-ROAS campaigns** tend to be low-spend (mean $2,378) and appear in the North region more often
- **High-ROAS campaigns** also tend to be low-spend (mean $5,858) and appear more in the West

Both tails are associated with lower spend — this is expected, as ROAS has higher variance at low spend levels (small denominator effect).

---

## 3. Predictive Modeling

### Objective

Predict campaign revenue from available features (ad spend, impressions, clicks, month, region, channel).

### Model 1: Full OLS Linear Regression

**Features:** ad_spend_usd, impressions, clicks, month, region (one-hot), channel (one-hot)

| Metric | Value |
|---|---|
| R-squared | 0.946 |
| Adj. R-squared | 0.946 |
| Significant predictors | ad_spend_usd only (p < 0.001) |

**Diagnostics:**
- **Multicollinearity:** VIF for ad_spend (9.4) and impressions (10.7) both exceed 5, confirming redundancy
- **Heteroscedasticity:** Breusch-Pagan test significant (p < 0.001) — residual variance increases with fitted values
- **Normality:** Residuals have excess kurtosis (4.98), indicating heavier tails than normal
- **Autocorrelation:** Durbin-Watson = 2.08 (no concern)
- **Non-significant predictors:** Impressions, clicks, month, all region dummies, and all channel dummies are statistically non-significant

### Model 2: Parsimonious OLS (ad_spend only, robust SE)

Given multicollinearity and non-significance of other features, a single-predictor model was fit:

**revenue = 192.5 + 2.495 * ad_spend** (with HC3 robust standard errors)

| Metric | Value |
|---|---|
| R-squared | 0.945 |
| Coefficient | 2.495 (p < 0.001) |

The parsimonious model loses only 0.001 in R-squared compared to the full model, confirming that **ad spend alone explains 94.5% of revenue variance**. Every additional dollar of ad spend generates approximately $2.50 in revenue.

### Model 3: Log-Log Regression

**log(revenue) = 0.912 + 1.000 * log(spend)**

| Metric | Value |
|---|---|
| R-squared | 0.974 |
| Elasticity | 1.00 |

The log-log model achieves higher R-squared (0.974) and reveals that the **elasticity of revenue with respect to spend is almost exactly 1.0** — a perfectly proportional relationship. A 1% increase in ad spend produces ~1% increase in revenue. This is consistent with the finding of constant ROAS across spend levels.

Note: Heteroscedasticity persists in the log-log model (Breusch-Pagan p < 0.001), and residuals show left skew and excess kurtosis. HC3 robust standard errors are used to ensure valid inference.

### Model Comparison (Cross-Validated)

| Model | 5-Fold CV R-squared | CV RMSE | Holdout R-squared |
|---|---|---|---|
| Linear Regression | 0.9444 +/- 0.0032 | $8,706 | 0.9444 |
| Random Forest (200 trees) | 0.9408 +/- 0.0058 | $8,977 | 0.9433 |
| Gradient Boosting (200 trees) | 0.9356 +/- 0.0066 | $9,361 | 0.9321 |

**Linear regression outperforms tree-based models** — consistent with the underlying relationship being strongly linear. The random forest and gradient boosting models offer no improvement and slightly overfit to noise.

**Feature importance (Random Forest):** ad_spend_usd dominates (>85% importance), followed by impressions (~10%). Clicks, month, region, and channel contribute negligibly.

---

## 4. Key Findings

1. **Revenue is almost entirely determined by ad spend.** The relationship is linear and proportional (ROAS ~2.5x, elasticity ~1.0). A simple linear model with ad_spend alone achieves R-squared = 0.945.

2. **Channel choice does not matter.** Email, Search, Social, and Display yield statistically indistinguishable ROAS, CTR, and CPC. There is no evidence that any channel outperforms another.

3. **Regional differences are negligible.** While West shows slightly higher mean ROAS (2.55) and North slightly lower (2.47), these differences are not statistically significant (ANOVA p = 0.076).

4. **No diminishing returns observed.** ROAS is constant across all spend levels within the observed range ($729 - $49,986). The quadratic term in a polynomial fit is essentially zero.

5. **No seasonal patterns.** Monthly performance is flat — no evidence of seasonality in any metric.

6. **ROAS variance is higher at low spend.** Both extreme-high and extreme-low ROAS campaigns tend to have below-average spend, consistent with small-sample variance effects.

7. **The data appears synthetically generated.** The perfect uniformity across channels and regions, the absence of any quality issues, and the almost-exactly-1.0 elasticity suggest the data was generated from a simple model (revenue ~ 2.5 * ad_spend + noise).

---

## 5. Assumptions Checked

| Assumption | Status | Notes |
|---|---|---|
| Linearity | Confirmed | Pearson r = 0.972, elasticity = 1.00 |
| No multicollinearity | Violated (full model) | VIF > 9 for spend and impressions; resolved in parsimonious model |
| Homoscedasticity | Violated | Breusch-Pagan p < 0.001; mitigated with HC3 robust standard errors |
| Normality of residuals | Violated | Excess kurtosis (4.98); large N makes OLS robust via CLT |
| Independence | Confirmed | Durbin-Watson = 2.08 |
| No diminishing returns | Confirmed | Quadratic coefficient ~ 0 |

---

## 6. Recommendations

1. **Budget allocation across channels can be flexible** — since all channels perform equally, allocation decisions can be driven by other factors (reach, brand goals, audience targeting).

2. **Scale spend confidently** — within the observed range, every dollar spent returns ~$2.50 with no diminishing returns. If the goal is revenue maximization, increase budgets uniformly.

3. **Investigate beyond this data** — the remarkable uniformity suggests either (a) this data was synthetically generated, or (b) the campaigns are extremely homogeneous. Real-world data would likely show channel and regional differences that inform differentiated strategies.

4. **Monitor low-spend campaigns more carefully** — ROAS variance is higher for small campaigns, so these carry more risk of underperformance.

---

## 7. Plots Index

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all key numeric variables |
| `plots/02_scatter_relationships.png` | Scatter plots of spend vs revenue, impressions vs clicks, CTR by channel |
| `plots/03_channel_region_performance.png` | Bar charts of ROAS and revenue by channel and region |
| `plots/04_monthly_trends.png` | Monthly trends in spend, revenue, ROAS, campaign count, CTR |
| `plots/05_correlation_heatmap.png` | Correlation matrix heatmap |
| `plots/06_roas_region_channel.png` | ROAS by region-channel interaction |
| `plots/07_ols_diagnostics.png` | OLS residual diagnostics (residuals vs fitted, Q-Q, histogram, scale-location) |
| `plots/08_prediction_performance.png` | Predicted vs actual and test residual distribution |
| `plots/09_feature_importance.png` | Random forest feature importance |
| `plots/10_model_comparison.png` | Cross-validated R-squared comparison across models |
| `plots/11_loglog_diagnostics.png` | Log-log model residual diagnostics |
| `plots/12_spend_efficiency.png` | Ad spend vs ROAS and ROAS by spend decile |
