# Employee Performance Dataset — Analysis Report

## 1. Dataset Overview

| Property | Value |
|----------|-------|
| Rows | 800 |
| Columns | 10 |
| Missing values | 0 |
| Duplicate rows | 0 |

### Variables

| Variable | Type | Range / Values | Distribution |
|----------|------|----------------|--------------|
| `employee_id` | int | 1–800 | Sequential identifier |
| `years_experience` | float | 0.2–30.0 | Uniform (KS p=0.48) |
| `training_hours` | float | 0.0–79.5 | Approximately Normal |
| `team_size` | int | 3–24 | Discrete Uniform (chi2 p=0.92) |
| `projects_completed` | int | 1–18 | Near-Normal, slight right skew |
| `satisfaction_score` | float | 1.0–9.98 | Uniform (KS p=0.17) |
| `commute_minutes` | int | 5–120 | Right-skewed (median=16, mean=24.5) |
| `performance_rating` | float | 9.5–75.3 | Normal (KS p=0.43, mean=50.0, std=10.0) |
| `salary_band` | categorical | L1–L5 | Near-uniform across 5 levels (chi2 p=0.67) |
| `remote_pct` | int | {0, 25, 50, 75, 100} | Near-uniform (chi2 p=0.03) |

### Data Quality Notes

- **No nulls, no duplicates.** The dataset is complete and clean.
- **3 zeros in `training_hours`** — plausible (employees who received no training).
- **49 outliers in `commute_minutes`** by IQR method — driven by the heavy right tail, not data errors.
- **3 outliers in `performance_rating`** at the extremes (9.5 and 75.3) — within plausible range.

## 2. Exploratory Data Analysis

### 2.1 Distributions

All numeric features were examined for shape, skewness, and normality:

- **`performance_rating`** follows a near-perfect Normal distribution (mean ≈ 50, std ≈ 10, skewness = -0.22).
- **`years_experience`**, **`satisfaction_score`**, and **`team_size`** follow uniform distributions — confirmed by Kolmogorov-Smirnov and chi-squared goodness-of-fit tests.
- **`commute_minutes`** is strongly right-skewed (skewness = 1.77, kurtosis = 3.29).
- **`salary_band`** and **`remote_pct`** are approximately uniformly distributed across their discrete levels.

See: `plots/01_distributions.png`

### 2.2 Bivariate Relationships

**All pairwise Pearson correlations between features are near zero** (|r| < 0.09 for every pair). This is the most striking finding: the features appear to be statistically independent of one another.

Key correlation values with `performance_rating`:

| Feature | r | p-value |
|---------|---|---------|
| `team_size` | -0.086 | 0.015 |
| `training_hours` | 0.046 | 0.19 |
| `remote_pct` | 0.023 | 0.52 |
| `years_experience` | -0.015 | 0.67 |
| All others | |r| < 0.02 | p > 0.5 |

The `team_size` correlation (r = -0.086), while nominally significant at alpha = 0.05, has a trivially small effect size (R² = 0.007) and is likely a false positive given 8 simultaneous tests.

See: `plots/03_scatter_with_lowess.png`, `plots/04_correlation_heatmap.png`

### 2.3 Group Comparisons

**Performance by Salary Band (ANOVA):**
- F = 0.72, p = 0.579 — no significant differences.
- Mean performance is virtually identical across all bands (range: 49.2–51.1).

**Performance by Remote % (ANOVA):**
- F = 2.11, p = 0.078 — not significant at alpha = 0.05.
- Means range from 47.9 (50% remote) to 51.1 (100% remote) — a negligible spread.

**Top 10% vs Bottom 10% performers** have statistically indistinguishable profiles on every feature (all t-test p-values > 0.14).

See: `plots/02_performance_by_categories.png`, `plots/05_multivariate_scatter.png`

### 2.4 Non-linear Relationships

LOWESS smoothing curves across all scatter plots are essentially flat, confirming that the lack of correlation is not masking non-linear patterns.

Quadratic terms (x²) and interaction terms (x₁ × x₂) were tested: none achieve meaningful correlation with performance (all |r| < 0.09, most p > 0.10).

### 2.5 Feature Independence (PCA)

PCA on the 8 numeric features shows variance distributed nearly equally across all components:

| Component | Explained Variance |
|-----------|-------------------|
| PC1 | 14.6% |
| PC2 | 13.4% |
| PC3 | 12.8% |
| ... | ... |
| PC8 | 10.6% |

For 8 independent features, the expected value under uniform variance is 12.5% per component. The observed values are consistent with **independent random variables** — there is no latent structure to discover.

See: `plots/07_pca_analysis.png`

## 3. Modeling

### 3.1 Approach

Given `performance_rating` as the natural target variable, five models were fit using all other features as predictors, evaluated via 5-fold cross-validation:

| Model | CV R² (mean ± std) |
|-------|-------------------|
| Linear Regression | -0.013 ± 0.020 |
| Ridge (alpha=1) | -0.013 ± 0.020 |
| Lasso (alpha=1) | -0.007 ± 0.014 |
| Gradient Boosting | -0.120 ± 0.059 |
| Random Forest | -0.098 ± 0.058 |

**All models produce negative R² values**, meaning they perform worse than simply predicting the mean. The more complex ensemble methods overfit more severely (negative R² further from zero).

See: `plots/09_model_comparison.png`

### 3.2 OLS Regression Details

The full OLS regression was estimated for diagnostic purposes:

- **R² = 0.010, Adjusted R² = 0.000**
- **F-statistic = 1.004, p = 0.431** — the overall regression is not significant.
- Only `team_size` has a nominally significant coefficient (t = -2.36, p = 0.019), but this is likely a false positive given multiple testing.
- The Durbin-Watson statistic (2.09) indicates no autocorrelation in residuals.

### 3.3 Cross-Target Prediction

To rule out the possibility that a different variable should be the target, Random Forest models were trained to predict every variable from all others:

| Target | CV R² |
|--------|-------|
| `performance_rating` | -0.098 |
| `years_experience` | -0.036 |
| `training_hours` | -0.107 |
| `satisfaction_score` | -0.119 |
| `commute_minutes` | -0.074 |
| All others | < 0 |

**No variable in this dataset can be predicted from the others.** Additionally, classifying `salary_band` from all features yields 20.1% accuracy, indistinguishable from the 21.3% baseline (random chance for 5 classes).

### 3.4 Model Diagnostics

OLS residual diagnostics show:
- Residuals are approximately normally distributed (Jarque-Bera p = 0.039).
- No heteroscedasticity visible in residuals-vs-fitted plot.
- Residuals are essentially equal to the original data minus the grand mean — the model captures nothing.

See: `plots/08_ols_diagnostics.png`

## 4. Key Findings

### Primary Conclusion: The features are statistically independent.

The evidence is overwhelming and consistent across every analysis method:

1. **Near-zero correlations** between all variable pairs (|r| < 0.09).
2. **No non-linear relationships** detected via LOWESS, quadratic terms, or interaction terms.
3. **No group differences** in performance across salary bands or remote work categories.
4. **All predictive models fail** — negative cross-validated R² across linear, regularized, and ensemble methods.
5. **PCA shows no latent structure** — variance is uniformly distributed across components.
6. **Distribution tests** are consistent with independently generated random variables drawn from simple parametric families (Uniform, Normal).
7. **No variable predicts any other** — cross-target modeling confirms complete mutual independence.

### Interpretation

This dataset exhibits all the hallmarks of **synthetically generated data** where each column was sampled independently from its own distribution:

- `years_experience` ~ Uniform(0, 30)
- `training_hours` ~ Normal(41, 15)
- `team_size` ~ DiscreteUniform(3, 24)
- `projects_completed` ~ roughly Normal(8, 3), rounded to integers
- `satisfaction_score` ~ Uniform(1, 10)
- `commute_minutes` ~ Right-skewed (possibly Exponential + offset)
- `performance_rating` ~ Normal(50, 10)
- `salary_band` ~ Uniform({L1, L2, L3, L4, L5})
- `remote_pct` ~ Uniform({0, 25, 50, 75, 100})

There is no signal to extract and no model to build. This is not a failure of methodology — it is the correct conclusion given the data.

## 5. Plots Index

| File | Description |
|------|-------------|
| `plots/01_distributions.png` | Histograms of all numeric variables |
| `plots/02_performance_by_categories.png` | Performance by salary band and remote % |
| `plots/03_scatter_with_lowess.png` | Scatter plots with LOWESS smoothing |
| `plots/04_correlation_heatmap.png` | Correlation heatmap |
| `plots/05_multivariate_scatter.png` | Multivariate scatter plots |
| `plots/06_feature_importances.png` | Random Forest feature importances |
| `plots/07_pca_analysis.png` | PCA scree plot and PC1 vs PC2 |
| `plots/08_ols_diagnostics.png` | OLS residual diagnostics |
| `plots/09_model_comparison.png` | Cross-validated R² across models |
| `plots/10_comprehensive_summary.png` | Comprehensive summary figure |
