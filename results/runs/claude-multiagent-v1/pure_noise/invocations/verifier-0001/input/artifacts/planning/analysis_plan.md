# Analysis Plan

## Dataset Summary

- **Rows**: 800, **Columns**: 10, **Nulls**: 0
- **Target** (assumed): `performance_rating` (continuous, mean 50.0, std 10.0)
- **Numeric predictors** (7): years_experience, training_hours, team_size, projects_completed, satisfaction_score, commute_minutes, remote_pct
- **Categorical predictor** (1): salary_band (5 levels: L1-L5, mode L5 at 170/800)
- **ID column**: employee_id (sequential 1-800, not a predictor)

## Critical Risk: Possible Pure Noise

The framing identifies that performance_rating (mean ~50, std ~10) is consistent with a purely random variable. The primary goal of this analysis is to **determine whether any signal exists before attempting modelling**. Every experiment below includes a null-hypothesis baseline so we can distinguish real structure from chance.

---

## Phase 1 -- Signal Detection (must run first)

| ID | What | Why | Output |
|----|------|-----|--------|
| EXP-CORR-01 | Pairwise Pearson & Spearman correlations for all numeric columns | Detect any linear or monotonic association with performance_rating | `correlation_matrix.png`, correlation values in JSON |
| EXP-CORR-02 | P-value matrix with Bonferroni correction (28 pairwise tests) | Guard against false positives from multiple comparisons | p-value table in JSON |
| EXP-REG-01 | OLS regression of performance_rating on all 8 predictors | Measure explained variance (R-squared, adjusted R-squared, F-stat) | Regression summary text |
| EXP-PERM-01 | Permutation test: shuffle performance_rating 1000x, collect R-squared distribution | Compare observed R-squared against null distribution to assess significance | `permutation_r2_hist.png`, p-value |

**Decision gate**: If the observed R-squared does not exceed the 95th percentile of the permuted distribution AND no individual correlation survives Bonferroni correction, **declare no signal** and proceed to Phase 3 (noise characterisation) only.

---

## Phase 2 -- Deeper Analysis (conditional on signal found)

| ID | What | Why | Output |
|----|------|-----|--------|
| EXP-NONLIN-01 | Scatter plots of each predictor vs performance_rating with LOWESS overlay | Check for non-linear relationships a linear model would miss | `scatter_{feature}.png` (7 plots) |
| EXP-SAL-01 | ANOVA / Kruskal-Wallis of performance_rating across salary_band levels | Test whether salary_band explains variation in the target | Test statistic + p-value |
| EXP-MULTI-01 | Variance Inflation Factors for all numeric predictors | Detect multicollinearity before multivariate modelling | VIF table |
| EXP-FEATIMP-01 | Random Forest feature importance (permutation-based) with cross-validated R-squared | Rank predictors by predictive power, cross-check against OLS | `feature_importance.png`, importances JSON |

---

## Phase 3 -- Distribution & Data-Quality Checks (always run)

| ID | What | Why | Output |
|----|------|-----|--------|
| EXP-DIST-01 | Histograms + KDE for all numeric columns | Characterise distributions, check for uniformity consistent with synthetic data | `distributions.png` |
| EXP-COMM-01 | Commute_minutes outlier analysis (IQR rule, boxplot) | Framing flags right-skew and outliers in this column | `commute_boxplot.png`, outlier count |
| EXP-INDEP-01 | Chi-squared test of independence: salary_band vs binned remote_pct | Check whether categorical and discretised features are independent (noise indicator) | Test statistic + p-value |
| EXP-PCA-01 | PCA on standardised numeric features, scree plot + biplot | Check whether features share latent structure or are independent axes | `pca_screeplot.png`, `pca_biplot.png`, explained variance ratios |

---

## Validation Checks (map to framing.required_checks)

| Framing Check | Experiment(s) |
|---------------|---------------|
| Pairwise correlations with performance_rating | EXP-CORR-01, EXP-CORR-02 |
| Any predictor explains significant variance beyond chance | EXP-REG-01, EXP-PERM-01 |
| Baseline regression vs null model | EXP-PERM-01 |
| Commute_minutes outliers and skew | EXP-COMM-01, EXP-DIST-01 |
| Salary_band distinct feature profiles | EXP-SAL-01 |
| Multicollinearity among predictors | EXP-MULTI-01 |

## Execution Order

1. Phase 1 experiments (EXP-CORR-01 through EXP-PERM-01) -- **parallel**
2. Phase 3 experiments (EXP-DIST-01 through EXP-PCA-01) -- **parallel with Phase 1**
3. Decision gate evaluation
4. Phase 2 experiments -- **only if signal detected**
