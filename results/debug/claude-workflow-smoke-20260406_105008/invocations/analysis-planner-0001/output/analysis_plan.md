# Analysis Plan

## Primary Frame
Identify which employee attributes, if any, are predictive of `performance_rating`.

## Dataset Summary
- 800 rows, 10 columns (1 ID, 8 numeric features, 1 categorical: `salary_band` with 5 levels)
- Zero nulls across all columns (synthetic / pre-cleaned data)
- `performance_rating`: mean 50.0, std 10.0, range [9.5, 75.3]

---

## Experiments

### EXP-01: Distribution & Pairwise Correlations
**Covers**: required checks 1, 2

Assess the distribution of `performance_rating` (normality, outliers) and compute pairwise correlations between every numeric feature and `performance_rating`.

- Shapiro-Wilk test on `performance_rating`
- Histogram + boxplot of `performance_rating`
- Pearson and Spearman correlation of each numeric feature vs `performance_rating` with p-values
- Bar chart of correlation coefficients

**Pass criteria**: Report whether any correlation exceeds |r| > 0.1 at p < 0.05. Flag outliers beyond 3 standard deviations.

---

### EXP-02: Salary Band Investigation
**Covers**: required check 3

Verify whether `salary_band` acts as an ordinal proxy by inspecting level frequencies and comparing feature distributions across bands.

- Frequency table of `salary_band`
- Group-wise mean and std of `years_experience`, `training_hours`, `performance_rating`, and `satisfaction_score` per band
- Kruskal-Wallis test for `performance_rating` across bands
- Boxplot of `performance_rating` by `salary_band`

**Pass criteria**: If band ordering shows a monotonic trend in any feature, flag the variable as an ordinal proxy.

---

### EXP-03: Multicollinearity Assessment
**Covers**: required check 5

Compute Variance Inflation Factors (VIF) and a predictor-to-predictor correlation matrix to detect multicollinearity before any regression interpretation.

- VIF for each numeric predictor (exclude `employee_id`)
- Correlation heatmap among predictors
- Flag any VIF > 5 or pairwise |r| > 0.7

**Pass criteria**: Report which, if any, predictor pairs are collinear.

---

### EXP-04: Permutation Baseline Test
**Covers**: required check 4

Fit an OLS regression of `performance_rating` on all numeric predictors, then compare the observed R-squared to a null distribution built by shuffling the target 200 times.

- Fit OLS on real data, record R-squared
- Shuffle `performance_rating` 200 times, refit each time, collect R-squared values
- Compute empirical p-value = fraction of permuted R-squared >= observed R-squared
- Histogram of permuted R-squared with observed value marked

**Pass criteria**: If empirical p-value > 0.05, conclude that the observed fit does not exceed chance.

---

## Experiment-to-Check Mapping

| Required Check | Experiment |
|---|---|
| Pairwise correlations vs performance_rating | EXP-01 |
| Distribution of performance_rating (normality, outliers) | EXP-01 |
| Salary_band ordinal proxy verification | EXP-02 |
| Permutation / shuffle test for signal vs chance | EXP-04 |
| Multicollinearity among predictors | EXP-03 |

## Framing Risks Addressed

| Risk | Mitigation |
|---|---|
| Spurious correlations (800 rows, 9 predictors) | EXP-01 reports raw p-values; EXP-04 gives a global permutation check |
| Salary bands may be arbitrary | EXP-02 directly tests this |
| Commute_minutes right-skewed | EXP-01 uses Spearman (rank) alongside Pearson |
| Zero nulls / synthetic data | Noted; no special experiment needed, flagged in report |
