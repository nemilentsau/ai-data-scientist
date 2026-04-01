# Marketing Campaign Dataset Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| **Rows** | 1,000 |
| **Columns** | 8 |
| **Missing values** | None |
| **Duplicate rows** | None |
| **Data quality issues** | None detected |

**Variables:**
- `campaign_id`: Unique identifier (1-1000)
- `region`: Categorical — East (240), West (241), South (258), North (261)
- `channel`: Categorical — Email (266), Search (258), Social (250), Display (226)
- `ad_spend_usd`: Continuous — Range $729 to $49,986 (mean: $24,768)
- `impressions`: Integer — Range 7,126 to 709,259 (mean: 284,200)
- `clicks`: Integer — Range 145 to 34,102 (mean: 8,423)
- `revenue_usd`: Continuous — Range $1,481 to $155,838 (mean: $61,979)
- `month`: Integer 1-12, roughly uniformly distributed (64-97 campaigns per month)

**Aggregate Totals:**
- Total ad spend: $24.77M
- Total revenue: $61.98M
- Overall return: **$2.50 revenue per $1 spent** (ROI of 150%)

## 2. Data Quality Assessment

The dataset is remarkably clean:
- No null values in any column
- No duplicate campaign IDs or rows
- No negative values in spend, impressions, clicks, or revenue
- No cases where clicks exceed impressions (logically consistent)
- No zero values in any numeric column
- All categorical values are from expected sets (4 regions, 4 channels)
- Month values are all valid (1-12)

## 3. Exploratory Data Analysis

### 3.1 Distributions (see `plots/01_distributions.png`)

All four numeric variables (ad_spend, impressions, clicks, revenue) follow roughly **uniform distributions** across their ranges, which is characteristic of simulated/synthetic data. There are no extreme outliers or skew in the raw variables.

### 3.2 Correlations (see `plots/02_correlation_heatmap.png`)

| | ad_spend | impressions | clicks | revenue |
|---|---|---|---|---|
| **ad_spend** | 1.000 | 0.945 | 0.773 | **0.972** |
| **impressions** | 0.945 | 1.000 | 0.804 | 0.915 |
| **clicks** | 0.773 | 0.804 | 1.000 | 0.742 |
| **revenue** | **0.972** | 0.915 | 0.742 | 1.000 |

Key observations:
- **Ad spend and revenue have an extremely strong linear relationship (r = 0.972)**
- Ad spend and impressions are also very highly correlated (r = 0.945), suggesting impressions are largely a function of spend
- Clicks has weaker but still strong correlations with other metrics
- Month has near-zero correlation with all numeric variables (r < 0.03)

### 3.3 Channel and Region Analysis

**ANOVA Results (Revenue):**
- Revenue by Channel: F = 0.54, **p = 0.657** (not significant)
- Revenue by Region: F = 0.85, **p = 0.465** (not significant)
- ROI by Channel: F = 0.50, **p = 0.680** (not significant)
- ROI by Region: F = 2.30, **p = 0.076** (not significant)
- Channel x Region interaction (controlling for spend): F = 1.03, **p = 0.412** (not significant)

**Channel-Region Independence:**
- Chi-square test: p = 0.887 (channels and regions are distributed independently)

**Interpretation:** Neither channel nor region has a statistically significant effect on revenue or ROI. All channels perform nearly identically when controlling for spend.

### 3.4 Channel Performance Summary

| Channel | Avg ROI | Avg CTR | Revenue per $1 Spent | Spend-Revenue Slope |
|---|---|---|---|---|
| Display | 1.49 | 3.08% | $2.50 | 2.50 |
| Email | 1.50 | 2.97% | $2.49 | 2.46 |
| Search | 1.51 | 2.87% | $2.52 | 2.46 |
| Social | 1.53 | 3.01% | $2.53 | 2.56 |

All channels generate approximately **$2.50 in revenue per $1 of ad spend**, with ROI consistently around 150%. The differences are not statistically significant.

### 3.5 Click-Through Rates

Mean CTR across all campaigns is **2.98%**, with negligible variation across channels (2.87%-3.08%) and regions (2.92%-3.07%). No channel or region demonstrates meaningfully superior engagement.

### 3.6 Monthly Trends (see `plots/06_monthly_trends.png`)

Monthly variations in total revenue and spend are driven primarily by **campaign count fluctuations** (64-97 per month), not by changes in per-campaign performance. Average ROI is stable across months (no seasonal pattern detected).

### 3.7 Diminishing Returns (see `plots/11_diminishing_returns.png`)

There is **no evidence of diminishing returns** to ad spend:
- Quadratic term in polynomial regression: p = 0.491 (not significant)
- Spearman correlation between spend and ROI: r = -0.023, p = 0.461 (not significant)
- Revenue scales linearly across all spend deciles
- ROI remains flat (~1.50) regardless of spend level

## 4. Predictive Modeling

### 4.1 OLS Regression (Primary Model)

**Model:** `revenue_usd ~ ad_spend_usd + channel + region + impressions + clicks + month`

| Metric | Value |
|---|---|
| R-squared | 0.946 |
| Adj. R-squared | 0.946 |
| F-statistic | 1,735 (p < 0.001) |

**Significant predictors:** Only `ad_spend_usd` (p < 0.001, coef = 2.575)

All other variables — impressions, clicks, channel, region, month — are **not statistically significant** (all p > 0.05). The parsimonious model `revenue ~ ad_spend` achieves the same R-squared (0.946).

**Interpretation of coefficient:** Each additional $1 in ad spend generates approximately **$2.50 in revenue**.

### 4.2 Log-Log Model (Elasticity)

**Model:** `log(revenue) ~ log(ad_spend)`

| Metric | Value |
|---|---|
| R-squared | 0.974 |
| Elasticity | 0.9996 |

The elasticity is essentially **1.0**, meaning a 1% increase in ad spend produces a 1% increase in revenue. This confirms a **constant-returns relationship** with no diminishing or increasing returns.

The log-log model achieves higher R-squared (0.974 vs 0.946) because it better handles heteroscedasticity — variance of revenue grows proportionally with spend level.

### 4.3 Machine Learning Models (5-Fold Cross-Validation)

| Model | CV R-squared | Test R-squared | Test MAE | Test RMSE |
|---|---|---|---|---|
| Linear Regression | 0.943 +/- 0.004 | 0.944 | $5,994 | $8,542 |
| Random Forest | 0.938 +/- 0.003 | 0.943 | $6,302 | $8,630 |
| Gradient Boosting | 0.928 +/- 0.001 | 0.931 | $6,668 | $9,554 |

**Linear regression outperforms** both ensemble methods, confirming the relationship is fundamentally linear. The tree-based models find no non-linear structure to exploit.

**Random Forest feature importance:**
- `ad_spend_usd`: **96.5%**
- `impressions`: 1.1%
- `clicks`: 1.0%
- All others: < 1%

### 4.4 Regression Diagnostics

| Diagnostic | Result | Interpretation |
|---|---|---|
| Breusch-Pagan | p < 0.001 | **Heteroscedasticity present** — residual variance increases with fitted values |
| Durbin-Watson | 2.08 | No autocorrelation |
| Shapiro-Wilk | p < 0.001 | Residuals have heavier tails than normal (kurtosis = 4.98) |
| VIF (ad_spend) | 9.41 | High collinearity with impressions (VIF = 10.7) |

**Heteroscedasticity** is the main diagnostic concern. The log-log model addresses this (R-squared = 0.974). For inference with the linear model, robust standard errors (HC3) would be appropriate, though the practical conclusions are unchanged given the overwhelming significance of ad_spend.

**Multicollinearity** between ad_spend and impressions is expected (impressions are purchased with spend). Using ad_spend alone in the parsimonious model eliminates this issue with no loss of explanatory power.

## 5. Key Findings

1. **Ad spend is the sole meaningful driver of revenue.** It explains 94.5% of variance alone. No other variable — channel, region, impressions, clicks, or month — adds significant predictive power after accounting for spend.

2. **Constant returns to ad spend.** Each dollar spent generates approximately $2.50 in revenue (ROI ~150%), regardless of spend level. There are no diminishing returns within the observed range ($729-$49,986).

3. **Channels and regions are interchangeable.** ANOVA tests (all p > 0.05), interaction tests (p = 0.41), and per-channel regression slopes (all ~2.5) confirm no meaningful performance differences across channels or regions.

4. **The relationship is linear.** Linear regression matches or exceeds tree-based ML models, and the quadratic term is not significant (p = 0.49).

5. **The data exhibits properties of synthetic/simulated data:** uniform distributions of numeric variables, near-identical performance across all categorical segments, perfectly consistent ROI across spend levels, and the absence of any noise or anomalies typically found in real marketing data.

## 6. Recommendations

Given the analysis findings:

- **If this is real data:** The uniform performance across channels and regions suggests budget allocation can be driven by factors other than channel efficiency (e.g., audience reach, strategic goals), since all channels deliver equivalent returns. The organization should continue to invest in ad spend as there are no diminishing returns within the observed range.

- **If this is synthetic/simulated data:** The data generation process produces a clean linear relationship (`revenue ~ 2.5 * ad_spend + noise`) with no meaningful variation by channel, region, or time. To make the simulation more realistic, consider adding: (a) channel-specific conversion rates, (b) diminishing returns at higher spend levels, (c) seasonal effects, and (d) regional market-size differences.

## 7. Plots Index

| Plot | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all numeric variables |
| `plots/02_correlation_heatmap.png` | Correlation matrix heatmap |
| `plots/03_pairplot_by_channel.png` | Scatter matrix colored by channel |
| `plots/04_revenue_vs_spend.png` | Revenue vs spend by channel and region |
| `plots/05_boxplots.png` | Revenue, spend, and ROI boxplots by channel/region |
| `plots/06_monthly_trends.png` | Monthly revenue, spend, ROI, and campaign count |
| `plots/07_residual_diagnostics.png` | OLS residual analysis (residuals vs fitted, Q-Q, histogram, scale-location) |
| `plots/08_model_comparison.png` | ML model R-squared comparison and feature importance |
| `plots/09_best_model_diagnostics.png` | Gradient Boosting predicted vs actual and residuals |
| `plots/10_channel_efficiency.png` | Revenue per dollar, CTR, and total spend by channel |
| `plots/11_diminishing_returns.png` | Spend decile analysis for diminishing returns |
| `plots/12_region_channel_heatmap.png` | Region x channel heatmaps (revenue, ROI, CTR) |
