# Analysis Plan

## Context

Dataset: 800-row synthetic HR/employee dataset with 8 candidate predictors and 1 target (`performance_rating`). Zero nulls, uniform row count, 5-level `salary_band`. The framing flags a high risk that features are independently generated with no genuine predictive signal ("pure noise" scenario).

## Phase 1: Distribution & Quality Checks

| Step | What | Why | Output |
|------|------|-----|--------|
| 1.1 | Histogram + KDE for `performance_rating` | Verify distribution shape; detect outliers or multimodality | `dist_performance_rating.png` |
| 1.2 | Histograms for all numeric predictors | Confirm uniform/normal/skewed shapes noted in profile | `dist_numeric_predictors.png` |
| 1.3 | Box-plot of `commute_minutes` | Profile shows heavy right skew (mean 24.5, median 16, max 120) | `boxplot_commute_minutes.png` |
| 1.4 | Bar chart of `salary_band` frequencies | Confirm level balance (top=L5 at 170; check the other 4 levels) | `bar_salary_band.png` |

## Phase 2: Signal Detection (Critical Path)

This phase gates all downstream modeling. If no signal is found, the analysis should report that conclusion rather than forcing a model.

| Step | What | Why | Output |
|------|------|-----|--------|
| 2.1 | Pearson & Spearman correlation of each numeric predictor vs `performance_rating` | Quantify linear and monotonic association; report p-values | `correlation_matrix.png`, stats in results table |
| 2.2 | One-way ANOVA of `performance_rating` across `salary_band` levels | Test whether the categorical predictor carries signal | p-value in results table |
| 2.3 | Pairwise correlation heatmap (all numeric features) | Check for multicollinearity and inter-feature structure | `correlation_heatmap.png` |
| 2.4 | Permutation test: fit OLS on all features, permute target 1000 times, compare R-squared | Establish whether observed R-squared exceeds chance | `permutation_r2_histogram.png` |
| 2.5 | Variance Inflation Factor (VIF) for numeric predictors | Quantify multicollinearity severity | VIF table in results |

## Phase 3: Modeling (Conditional on Phase 2 Findings)

Proceed only if Phase 2 shows at least one feature with p < 0.05 or permutation R-squared exceeds the 95th percentile of the null distribution.

| Step | What | Why | Output |
|------|------|-----|--------|
| 3.1 | OLS regression: `performance_rating ~ all features` | Baseline parametric model; inspect coefficients and R-squared | Coefficients table |
| 3.2 | Random Forest regressor with 5-fold CV | Non-linear benchmark; compare CV RMSE to std of target (~10.0) | CV RMSE, feature importances |
| 3.3 | Null-model baseline (predict mean) | Reference RMSE = std(performance_rating) ~ 10.0 | Baseline RMSE |

## Phase 4: Alternative Frames (If Primary Frame Fails)

| Step | What | Why | Output |
|------|------|-----|--------|
| 4.1 | Correlation of all features vs `satisfaction_score` | Alternative target from framing | Stats table |
| 4.2 | Chi-squared tests among categorical/binned features and `salary_band` | Test alternative classification frame | Stats table |

## Phase 5: Synthesis

| Step | What | Why | Output |
|------|------|-----|--------|
| 5.1 | Summary table: feature, correlation, p-value, VIF, RF importance | Single view of all evidence | `feature_signal_summary.csv` |
| 5.2 | Narrative conclusion: signal vs noise verdict | Answer the core question raised by framing risks | Section in analysis report |

## Validation Checkpoints

- If no individual correlation has p < 0.05 after Bonferroni correction (8 tests, threshold 0.00625), flag "no univariate signal."
- If permutation-test R-squared is not in the top 5% of null distribution, flag "no multivariate signal."
- If CV RMSE of Random Forest is within 2% of null-model RMSE (std of target), flag "model adds no value."
- Any of these flags supports a "pure noise" conclusion.
