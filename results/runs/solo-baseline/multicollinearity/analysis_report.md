# Housing Price Dataset: Analysis Report

## 1. Data Overview

| Property | Value |
|---|---|
| Rows | 800 |
| Columns | 9 |
| Missing values | 0 |
| Duplicate rows | 0 |

**Features:**

| Column | Type | Description |
|---|---|---|
| `listing_id` | int | Unique identifier (1-800) |
| `sq_ft` | int | Square footage (600-3,341) |
| `num_rooms` | int | Number of rooms (2-11) |
| `lot_size_acres` | float | Lot size in acres (0.32-1.72) |
| `garage_spaces` | int | Garage spaces (1-4) |
| `year_built` | int | Year built (1950-2023) |
| `neighborhood` | str | 5 categories: Suburbs, Eastwood, Hillcrest, Downtown, Lakeside |
| `has_pool` | int | Binary (0/1), 30.4% have pool |
| `price_usd` | int | Target variable: sale price in USD |

**Target distribution:** price_usd has a mean of $287,148 (std $61,285), ranging from $83,600 to $496,700. The distribution is approximately normal (Shapiro-Wilk p=0.10, D'Agostino p=0.70), with near-zero skewness (0.049).

---

## 2. Exploratory Data Analysis

### 2.1 Univariate Distributions

All numeric features are approximately symmetric with low skewness. No transformations are needed. See `plots/01_distributions.png`.

Only 5-6 mild outliers exist for sq_ft, lot_size_acres, and price_usd by the IQR method. The `garage_spaces` column flags 244 "outliers" because it is essentially a 3-level ordinal variable (1, 2, or 3+), not a continuous feature. No rows were removed.

### 2.2 Correlations

See `plots/02_correlation_heatmap.png`.

**Key findings:**

| Feature | Correlation with price_usd |
|---|---|
| sq_ft | **0.955** |
| num_rooms | 0.921 |
| lot_size_acres | 0.926 |
| garage_spaces | 0.751 |
| year_built | 0.177 |
| has_pool | -0.013 |

The size-related features (sq_ft, num_rooms, lot_size_acres, garage_spaces) are extremely highly correlated with each other (r > 0.76), indicating severe **multicollinearity**. This is confirmed by Variance Inflation Factors:

| Feature | VIF |
|---|---|
| sq_ft | **29.15** |
| lot_size_acres | **17.16** |
| num_rooms | **12.02** |
| garage_spaces | 2.66 |
| year_built | 1.01 |
| has_pool | 1.00 |

VIF > 10 is a standard threshold for problematic multicollinearity. The four size features are largely measuring the same underlying construct: **house size**. Among them, `sq_ft` has the highest individual correlation with price and carries almost all of the predictive signal.

### 2.3 Neighborhood Effect

One-way ANOVA on price by neighborhood: **F=1.13, p=0.343** (not significant). All pairwise t-tests with Bonferroni correction are non-significant. Neighborhood mean prices range narrowly from $278,853 (Downtown) to $292,422 (Lakeside) -- a spread of only $13,569 or ~5% of the mean price.

**Conclusion:** Neighborhood does not significantly predict price after accounting for house characteristics. See `plots/04_price_by_neighborhood.png`.

### 2.4 Pool Effect

Independent t-test: **t=-0.37, p=0.71**. Cohen's d = -0.028 (negligible effect size). Mean price with pool ($285,927) vs without ($287,681) differs by only $1,754.

**Conclusion:** Having a pool has no meaningful effect on price. See `plots/06_pool_by_neighborhood.png`.

### 2.5 Linearity

The relationship between sq_ft and price is strongly linear: Pearson r (0.955) and Spearman r (0.951) are nearly identical, confirming linearity with no significant monotonic non-linearity. See `plots/03_scatter_vs_price.png` and `plots/05_pairplot.png`.

---

## 3. Modeling

### 3.1 Model Comparison (10-Fold Cross-Validation)

| Model | R² (mean +/- std) | RMSE | MAE |
|---|---|---|---|
| **OLS** | **0.9420 +/- 0.0099** | **14,538** | **11,519** |
| Ridge | 0.9419 +/- 0.0100 | 14,541 | 11,525 |
| Lasso | 0.9420 +/- 0.0099 | 14,537 | 11,518 |
| Random Forest | 0.9260 +/- 0.0147 | 16,398 | 13,071 |
| Gradient Boosting | 0.9258 +/- 0.0145 | 16,434 | 12,906 |

See `plots/08_model_comparison.png`.

**Key observations:**
- Linear models (OLS, Ridge, Lasso) all perform identically, indicating that regularization adds no benefit -- the relationship is genuinely linear with no overfitting.
- Tree-based models (RF, GBM) perform **worse**, which is expected: they are less efficient at capturing simple linear relationships and require more data to match linear models when the true relationship is linear.
- This strongly suggests the **data-generating process is linear**.

### 3.2 Parsimonious Model: sq_ft + year_built Only

Given the severe multicollinearity, a model with just two features performs equally well:

| Model | R² (CV) | RMSE (CV) | AIC |
|---|---|---|---|
| Full (10 features) | 0.9420 | 14,538 | 17,619 |
| **Parsimonious (2 features)** | **0.9422** | **14,510** | **17,613** |

The simpler model has a **lower AIC** (17,613 vs 17,619), meaning it is statistically preferred. Adding num_rooms, lot_size_acres, garage_spaces, neighborhood, and has_pool provides essentially zero additional predictive power beyond sq_ft and year_built.

### 3.3 OLS Regression Coefficients (Full Model)

From the statsmodels OLS output, only two features have statistically significant coefficients:

| Feature | Coefficient | t-stat | p-value | Significant? |
|---|---|---|---|---|
| sq_ft | 142.22 | 20.08 | <0.001 | Yes |
| year_built | 519.95 | 21.03 | <0.001 | Yes |
| num_rooms | 1,628.36 | 1.27 | 0.205 | No |
| lot_size_acres | 2,532.75 | 0.24 | 0.812 | No |
| garage_spaces | -18.60 | -0.01 | 0.990 | No |
| has_pool | -1,828.99 | -1.63 | 0.103 | No |
| All neighborhood dummies | -- | -- | >0.23 | No |

**Interpretation of the parsimonious model:**
- Each additional square foot adds approximately **$142** to the price.
- Each additional year of construction (newer home) adds approximately **$520** to the price.
- These two factors together explain 94.2% of the variance in housing prices.

### 3.4 Holdout Test Set Performance (OLS)

| Metric | Value |
|---|---|
| Test R² | 0.9491 |
| Test RMSE | $13,486 |
| Test MAE | $10,987 |

See `plots/09_actual_vs_predicted.png`. The model generalizes well, with no sign of overfitting (test R² is slightly higher than CV R²).

---

## 4. Model Diagnostics

### 4.1 Residual Analysis

See `plots/07_residual_diagnostics.png`.

| Diagnostic | Result | Interpretation |
|---|---|---|
| Residual normality (Shapiro-Wilk) | p=0.394 | Residuals are normal |
| Durbin-Watson | 1.962 | No autocorrelation (ideal ~2.0) |
| Breusch-Pagan | p=0.064 | Borderline homoscedastic (no strong heteroscedasticity) |
| Residuals vs Fitted | Random scatter | No systematic pattern |
| Q-Q Plot | Points follow line | Confirms normality |
| Condition Number | 257,000 | High, due to multicollinearity (expected) |

All OLS assumptions are satisfied:
1. **Linearity** -- confirmed by scatter plots and residual patterns.
2. **Independence** -- Durbin-Watson = 1.96, no autocorrelation.
3. **Normality of residuals** -- Shapiro-Wilk p=0.39.
4. **Homoscedasticity** -- Breusch-Pagan p=0.064 (passes at alpha=0.05).

### 4.2 Feature Importance (Random Forest)

See `plots/10_feature_importance_rf.png`. The RF feature importance confirms the same pattern: `sq_ft` dominates, followed by `year_built`. All other features contribute minimally.

---

## 5. Key Findings and Conclusions

1. **House price is overwhelmingly determined by two factors: square footage and year built.** Together they explain 94.2% of price variance. Square footage alone explains ~91%.

2. **Severe multicollinearity** exists among size-related features (sq_ft, num_rooms, lot_size_acres, garage_spaces). These all measure the same underlying construct. Only sq_ft is needed as a predictor.

3. **Neighborhood and pool have no statistically significant effect on price.** The ANOVA for neighborhood (p=0.34) and t-test for pool (p=0.71) both fail to reject the null hypothesis. Effect sizes are negligible.

4. **The data-generating process is linear.** Evidence: (a) linear models outperform tree-based models, (b) regularization provides no benefit, (c) Pearson and Spearman correlations match, (d) residuals show no systematic patterns.

5. **The recommended model is: `price = -1,012,000 + 142 * sq_ft + 520 * year_built`** (or equivalently, the parsimonious 2-feature OLS). It is simpler, more interpretable, and has a lower AIC than the full model.

6. **Data quality is excellent:** no missing values, no duplicates, minimal outliers, approximately normal distributions. This is consistent with a synthetic or carefully curated dataset.

---

## 6. Plots Index

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all numeric features |
| `plots/02_correlation_heatmap.png` | Correlation matrix heatmap |
| `plots/03_scatter_vs_price.png` | Scatter plots of each feature vs price |
| `plots/04_price_by_neighborhood.png` | Box/violin plots of price by neighborhood |
| `plots/05_pairplot.png` | Pairplot of key features |
| `plots/06_pool_by_neighborhood.png` | Price by neighborhood and pool status |
| `plots/07_residual_diagnostics.png` | OLS residual diagnostic plots |
| `plots/08_model_comparison.png` | Cross-validation model comparison |
| `plots/09_actual_vs_predicted.png` | Actual vs predicted prices (test set) |
| `plots/10_feature_importance_rf.png` | Random Forest feature importance |
