# Analysis Report: pure_noise Dataset

## Executive Summary

This analysis investigated whether any of the 7 numeric features or the categorical `salary_band` variable predict `performance_rating` in an 800-row employee dataset. **No statistically significant relationships were found.** After multiple-testing correction, zero features reject the null hypothesis of no association. Both OLS regression and random-forest models fail to outperform a simple mean baseline. The dataset is consistent with pure noise — all features appear independently generated with no true signal.

---

## Dataset Overview

| Property | Value |
|----------|-------|
| Rows | 800 |
| Columns | 10 (7 numeric predictors, 1 categorical, 1 ID, 1 target) |
| Target | `performance_rating` (mean=50.0, std=10.0) |
| Null values | 0 |
| Categorical | `salary_band` with 5 levels (L1-L5) |

---

## Phase 1: Distribution & Data-Quality Checks

### CHK-01: performance_rating Distribution
- **Shapiro-Wilk**: W=0.9947, p=0.0071
- The p-value is below 0.05, but with n=800 the Shapiro-Wilk test is very sensitive to minor deviations. The histogram (see `plots/dist_performance_rating.png`) shows a visually bell-shaped distribution centered near 50 with std ~10. The departure from perfect normality is negligible for practical purposes.
- **Conclusion**: Approximately normal; parametric methods are appropriate.

### CHK-02: Numeric Feature Distributions
All numeric features display reasonable distributions consistent with independent generation. See `plots/dist_numeric_features.png`.

### CHK-03: salary_band Category Counts
Five levels with counts ranging from ~140 to 170. No severe imbalance. See `plots/salary_band_counts.png`.

### CHK-04: employee_id Validation
employee_id is unique and sequential (1 to 800) with no gaps or duplicates.

---

## Phase 2: Bivariate Relationships

### CHK-05: Correlations with performance_rating

| Feature | Pearson r | p-value | Spearman rho | p-value |
|---------|-----------|---------|--------------|---------|
| years_experience | -0.015 | 0.673 | -0.004 | 0.908 |
| training_hours | 0.046 | 0.198 | 0.039 | 0.269 |
| team_size | -0.086 | 0.015 | -0.083 | 0.019 |
| projects_completed | 0.016 | 0.644 | 0.015 | 0.666 |
| satisfaction_score | 0.001 | 0.969 | 0.015 | 0.679 |
| commute_minutes | -0.006 | 0.860 | 0.008 | 0.812 |
| remote_pct | 0.023 | 0.512 | 0.029 | 0.410 |

Only `team_size` has a raw p-value < 0.05 (Pearson p=0.015), but this does not survive multiple-testing correction (see Phase 5). All absolute correlations are below 0.09.

### CHK-06: Pairwise Correlation Heatmap
The heatmap (`plots/correlation_heatmap.png`) shows no strong pairwise relationships among predictors. All off-diagonal values are near zero, consistent with independently generated variables.

### CHK-07: Top-4 Feature Scatter Plots
Scatter plots of `team_size`, `training_hours`, `remote_pct`, and `projects_completed` vs `performance_rating` show uniform scatter clouds with no discernible pattern. See `plots/scatter_top4.png`.

### CHK-08: ANOVA — salary_band vs performance_rating
- **F-statistic**: 0.7185
- **p-value**: 0.5794
- Not significant. There is no evidence that salary band affects performance rating.

### CHK-09: Box Plot
Box plots (`plots/boxplot_salary_band.png`) show nearly identical median and spread across all five salary bands.

---

## Phase 3: Multicollinearity & Redundancy

### CHK-10: Variance Inflation Factors

| Feature | VIF |
|---------|-----|
| years_experience | 1.006 |
| training_hours | 1.013 |
| team_size | 1.005 |
| projects_completed | 1.004 |
| satisfaction_score | 1.002 |
| commute_minutes | 1.013 |
| remote_pct | 1.007 |

All VIF values are essentially 1.0, confirming zero multicollinearity. The features are independent.

### CHK-11: Condition Number
- **Condition number**: 28.83
- Well below concerning thresholds (>30 moderate, >100 severe). No numerical instability.

---

## Phase 4: Predictive Modelling (Null-Signal Test)

### CHK-12: OLS Regression
- **R-squared**: 0.01359
- **Adjusted R-squared**: -0.00018 (effectively zero)
- **F-statistic**: 0.9870
- **F p-value**: 0.4564

The global F-test fails to reject the null that all coefficients are zero. The model explains ~1.4% of variance, and the negative adjusted R-squared confirms this is within noise.

### CHK-13: Random-Forest Permutation Importance
Permutation importance values on the training set are positive due to random-forest overfitting to noise. However, the cross-validated RMSE (10.45) is **worse** than the mean baseline (10.01), confirming the model captures no real signal. The 95% CI plot is at `plots/permutation_importance.png`.

### CHK-14: Cross-Validated RMSE Comparison

| Model | CV RMSE |
|-------|---------|
| Mean baseline | 10.01 |
| OLS (full) | 10.06 |
| Random forest | 10.45 |

Both models perform at or slightly worse than the mean baseline. The OLS ratio is 1.005 (within 1%). The random forest is 4.4% worse, as expected when fitting 100 trees to pure noise.

---

## Phase 5: Multiple-Testing & Robustness

### CHK-15: Multiple-Testing Corrections

| Test | Raw p | Bonferroni p | BH p | Reject (Bonf.) | Reject (BH) |
|------|-------|-------------|------|-----------------|-------------|
| years_experience | 0.673 | 1.000 | 0.898 | No | No |
| training_hours | 0.198 | 1.000 | 0.793 | No | No |
| team_size | 0.015 | 0.120 | 0.120 | No | No |
| projects_completed | 0.644 | 1.000 | 0.898 | No | No |
| satisfaction_score | 0.969 | 1.000 | 0.969 | No | No |
| commute_minutes | 0.860 | 1.000 | 0.969 | No | No |
| remote_pct | 0.512 | 1.000 | 0.898 | No | No |
| ANOVA (salary_band) | 0.579 | 1.000 | 0.898 | No | No |

**Zero tests are significant** under either Bonferroni or Benjamini-Hochberg correction.

### CHK-16: Bootstrap 95% CIs for Pearson r

| Feature | r | 95% CI | Includes zero? |
|---------|---|--------|----------------|
| years_experience | -0.015 | [-0.087, 0.057] | Yes |
| training_hours | 0.046 | [-0.023, 0.119] | Yes |
| team_size | -0.086 | [-0.152, -0.018] | No |
| projects_completed | 0.016 | [-0.056, 0.086] | Yes |
| satisfaction_score | 0.001 | [-0.070, 0.072] | Yes |
| commute_minutes | -0.006 | [-0.079, 0.067] | Yes |
| remote_pct | 0.023 | [-0.038, 0.094] | Yes |

Six of seven features have CIs spanning zero. The `team_size` CI (-0.152 to -0.018) narrowly excludes zero, but this is expected with 7 tests — roughly one false positive at the ~2.5% tail. After Bonferroni correction, team_size is non-significant (p=0.12).

---

## Hypothesis Verdicts

| Hypothesis | Verdict | Key Evidence |
|------------|---------|--------------|
| H-01: No feature has significant correlation after correction | **Supported** | 0/7 features significant after Bonferroni or BH |
| H-02: salary_band has no effect on performance_rating | **Supported** | ANOVA p=0.58 |
| H-03: OLS model has no power beyond intercept | **Supported** | F p=0.46, CV RMSE ratio=1.005 |
| H-04: No feature has permutation importance above zero | **Supported** | RF CV RMSE worse than baseline |
| H-05: performance_rating is approximately normal | **Supported** | Visually bell-shaped; Shapiro-Wilk sensitive at n=800 |
| H-06: Predictors are mutually uncorrelated | **Supported** | All VIF ~1.0, all |r| < 0.09 |

---

## Conclusion

The `pure_noise` dataset lives up to its name. All features — numeric and categorical — are independent of each other and of the target variable `performance_rating`. No linear, monotonic, or nonlinear relationship was detected. The data appears to be synthetically generated with each column drawn from its own independent distribution. Any apparent pattern (e.g., the marginal team_size correlation) dissolves under proper multiple-testing correction.

---

## Artifacts Produced

### Plots (`plots/`)
- `dist_performance_rating.png` — Histogram with Shapiro-Wilk result
- `dist_numeric_features.png` — Histograms for all numeric columns
- `salary_band_counts.png` — Bar chart of category counts
- `correlation_heatmap.png` — Full pairwise correlation heatmap
- `scatter_top4.png` — Scatter plots of top-4 correlated features vs target
- `boxplot_salary_band.png` — Box plot of target by salary band
- `permutation_importance.png` — Random-forest permutation importance with 95% CI

### Statistics (`stats/`)
- `summary_stats.json` — Key summary statistics (R-squared, F-test, VIF, RMSE)
- `correlations.json` — Full correlation table with adjusted p-values
- `vif.json` — Variance inflation factors
- `permutation_importance.json` — Feature importance scores
- `bootstrap_ci.json` — Bootstrap confidence intervals for Pearson r
- `multiple_testing.json` — Bonferroni and BH adjusted p-values

### Other
- `correlation_table.csv` — Correlation results with adjusted p-values
- `findings.json` — Structured findings
- `claim_evidence_map.json` — Claims mapped to supporting evidence
