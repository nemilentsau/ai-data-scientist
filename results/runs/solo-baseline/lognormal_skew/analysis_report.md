# Startup Funding Analysis Report

## 1. Dataset Overview

| Property | Value |
|----------|-------|
| Rows | 800 |
| Columns | 8 |
| Missing values | 0 |
| Duplicate IDs | 0 |

**Variables:**
- `company_id`: Unique identifier (CO-0000 to CO-0799)
- `sector`: Categorical (6 levels: AI/ML, Biotech, Consumer, Fintech, Hardware, SaaS)
- `round_type`: Ordinal (Seed, Series A, Series B, Series C)
- `employees`: Integer, 5-498 (mean 255, roughly uniform)
- `years_since_founding`: Float, 0.6-15.0 (mean 7.7, roughly uniform)
- `revenue_growth_pct`: Float, -85.5% to +148.6% (mean 30.2%, roughly symmetric)
- `num_investors`: Integer, 1-11 (mean 6.0, roughly uniform)
- `funding_amount_usd`: Integer, $10,846 - $1,633,984 (mean $168K, **right-skewed**, skew = 3.23)

**Data quality:** The dataset is clean with no missing values, no duplicates, and no impossible values. All numeric features are well-behaved with low skewness (~0), except the target variable `funding_amount_usd` which is heavily right-skewed.

## 2. Exploratory Data Analysis

### 2.1 Target Variable: Funding Amount

The funding amount is heavily right-skewed (skewness = 3.23) with a long right tail containing 42 outliers (5.2%) above $446K by IQR criterion. A log-transformation yields an approximately normal distribution (Shapiro-Wilk p = 0.52), justifying its use as the modeling target.

*See: `plots/01_distributions.png`*

### 2.2 Sector Distribution

Sectors are approximately balanced (124-143 companies each). **Sector has no statistically significant effect on funding** (Kruskal-Wallis H = 2.00, p = 0.85). Median funding ranges from ~$104K (Biotech) to ~$129K (AI/ML), but these differences are not meaningful.

### 2.3 Round Type Distribution

Round types follow a typical funding funnel: Seed (324), Series A (219), Series B (155), Series C (102). **Round type has a statistically significant effect on funding** (Kruskal-Wallis H = 9.66, p = 0.02), with median funding increasing from $111K (Seed) to $150K (Series C).

*See: `plots/03_funding_by_category.png`, `plots/07_violin_plots.png`*

### 2.4 Key Correlations with Funding

Correlations with log(funding):
| Feature | Pearson r |
|---------|-----------|
| `years_since_founding` | 0.505 |
| `employees` | 0.453 |
| `revenue_growth_pct` | 0.195 |
| `num_investors` | -0.066 |

The interaction `employees x years_since_founding` shows correlation of 0.647 with log(funding), suggesting a multiplicative relationship: companies that are both large and established command the most funding.

*See: `plots/02_correlation_heatmap.png`, `plots/04_scatter_vs_funding.png`, `plots/05_pairplot.png`*

### 2.5 Notable Patterns

1. **Company maturity dominates:** Years since founding and employee count are the strongest predictors. Investors fund established, larger companies more heavily.
2. **Revenue growth matters, but less:** A positive but modest effect. Funding scales with growth, but age and size matter more.
3. **More investors does not mean more money:** The relationship is slightly negative and weakly significant. This may reflect that deals with many investors involve smaller checks, or that highly contested rounds signal uncertainty.
4. **Sector is irrelevant:** No sector commands significantly higher or lower funding. The startup's fundamentals matter, not its industry vertical.
5. **Only Series C differs from Seed:** Series A and B are not statistically distinguishable from Seed rounds in funding amount after controlling for other variables.

*See: `plots/06_interaction_scatter.png`*

## 3. Modeling

### 3.1 Approach

Given the log-normal distribution of funding, I modeled `log(funding_amount_usd)` as the target. I compared five model families using 10-fold cross-validation:

| Model | CV R^2 | CV RMSE | CV MAE |
|-------|--------|---------|--------|
| OLS | 0.489 +/- 0.043 | 0.606 +/- 0.031 | 0.490 +/- 0.028 |
| Ridge | 0.489 +/- 0.043 | 0.606 +/- 0.031 | 0.490 +/- 0.028 |
| **Lasso** | **0.497 +/- 0.039** | **0.602 +/- 0.032** | **0.486 +/- 0.028** |
| Random Forest | 0.414 +/- 0.063 | 0.648 +/- 0.033 | 0.523 +/- 0.025 |
| GBM | 0.363 +/- 0.091 | 0.675 +/- 0.037 | 0.540 +/- 0.036 |

**Linear models outperform tree-based models**, confirming that the relationships are genuinely linear in log-space. The Lasso model, which automatically penalizes irrelevant features, performs best.

*See: `plots/10_model_comparison.png`*

### 3.2 Final Model: Parsimonious OLS

Since sector is not significant (confirmed by both statistical tests and Lasso shrinkage), the final model drops sector for interpretability. The model uses robust (HC3) standard errors to handle mild heteroscedasticity (Breusch-Pagan p = 0.03).

```
log(funding) = 10.11
             + 0.0028 * employees
             + 0.0994 * years_since_founding
             + 0.0048 * revenue_growth_pct
             - 0.0173 * num_investors
             + 0.001  * Series_A     (not significant)
             + 0.073  * Series_B     (not significant)
             + 0.171  * Series_C     (p = 0.013)
```

**R^2 = 0.512, Adjusted R^2 = 0.508** (CV R^2 ~ 0.496)

*See: `plots/08_ols_diagnostics.png`, `plots/11_actual_vs_predicted.png`*

### 3.3 Practical Effect Sizes

| Change | Multiplicative effect on funding |
|--------|----------------------------------|
| +100 employees | x1.32 (32% more) |
| +5 years since founding | x1.64 (64% more) |
| +10 percentage points revenue growth | x1.05 (5% more) |
| +1 additional investor | x0.983 (1.7% less) |
| Series C vs Seed | x1.19 (19% more) |

### 3.4 GBM Feature Importances (confirmatory)

Even though GBM underperforms linearly, its feature importances confirm the story:
- `years_since_founding`: 37.2%
- `employees`: 35.0%
- `revenue_growth_pct`: 19.2%
- `num_investors`: 3.8%
- All sector and round-type dummies: < 1% each

*See: `plots/09_feature_importance.png`*

## 4. Model Diagnostics and Assumption Checks

| Check | Result | Interpretation |
|-------|--------|----------------|
| Residual normality (Shapiro-Wilk) | W=0.994, p=0.617 | Residuals are normal |
| Homoscedasticity (Breusch-Pagan) | LM=24.2, p=0.029 | Mild heteroscedasticity (addressed with HC3 SEs) |
| Independence (Durbin-Watson) | DW=1.975 | No autocorrelation |
| Multicollinearity (VIF) | All < 4 (parsimonious model) | Acceptable |
| Residuals by group | Centered at zero for all sectors/rounds | No systematic bias |
| Omnibus test | p=0.242 | No departure from normality |
| Cross-validation stability | Low CV standard deviations | Model generalizes well |

The model's assumptions are well-satisfied. The only minor concern is mild heteroscedasticity, which is handled by using robust standard errors. All conclusions remain identical under HC3 correction.

*See: `plots/08_ols_diagnostics.png`, `plots/12_residuals_by_group.png`*

## 5. Key Findings

1. **Startup funding follows a log-normal distribution.** A log-linear model explains ~51% of the variance.

2. **Company maturity is the strongest driver of funding.** Years since founding (r=0.50 with log-funding) and employee count (r=0.45) together explain most of the variance. The interaction between these two is the single strongest correlate (r=0.65).

3. **Revenue growth has a real but modest effect.** Each 10 percentage point increase in revenue growth adds about 5% to funding. Growth matters, but size and age matter more.

4. **Sector does not predict funding.** After controlling for fundamentals, AI/ML, SaaS, Fintech, Biotech, Consumer, and Hardware companies receive statistically indistinguishable funding amounts.

5. **More investors slightly reduces per-deal funding.** Each additional investor is associated with ~1.7% less total funding. This could reflect syndication dynamics (splitting rounds) or adverse selection.

6. **Round type has limited independent explanatory power.** Only Series C is significantly different from Seed (+19%), and even then the effect is modest. This suggests round labels primarily proxy for the underlying company stage (age, size) rather than carrying independent weight.

7. **The relationships are genuinely linear** (in log-space). Tree-based models do not capture additional nonlinear signal, and actually perform worse due to overfitting.

## 6. Limitations

- **R^2 ~ 0.51** means ~49% of funding variance is unexplained, likely driven by factors not in this dataset: product quality, market conditions, founder track record, competitive dynamics, and negotiation outcomes.
- The dataset lacks temporal information. If companies span different market cycles, time-varying effects are conflated.
- The negative `num_investors` coefficient could be a suppressor effect or reflect data-generating dynamics not captured here.
- This is an observational dataset; causal claims (e.g., "adding employees increases funding") are not supported.

## 7. Plots Index

| File | Description |
|------|-------------|
| `plots/01_distributions.png` | Distributions of all numeric variables |
| `plots/02_correlation_heatmap.png` | Correlation matrix heatmap |
| `plots/03_funding_by_category.png` | Funding by sector and round type (box plots) |
| `plots/04_scatter_vs_funding.png` | Scatter plots of predictors vs funding |
| `plots/05_pairplot.png` | Pairplot colored by round type |
| `plots/06_interaction_scatter.png` | Interaction effects scatter plots |
| `plots/07_violin_plots.png` | Violin plots for funding and revenue growth |
| `plots/08_ols_diagnostics.png` | OLS residual diagnostics (4 panels) |
| `plots/09_feature_importance.png` | GBM feature importances |
| `plots/10_model_comparison.png` | Cross-validated model comparison |
| `plots/11_actual_vs_predicted.png` | Actual vs predicted (log and USD) |
| `plots/12_residuals_by_group.png` | Residuals by sector and round type |
