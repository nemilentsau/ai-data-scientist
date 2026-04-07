# Analysis Plan

## Objective

Determine whether any workforce attribute is a genuine driver of `performance_rating`, or whether all apparent associations are consistent with pure noise.

## Experiments

### EXP-01 — Pairwise Correlation Analysis (Pearson & Spearman)

**Covers**: required checks 1, 2, 4; framing risks 1, 4.

Compute Pearson and Spearman correlations between every numeric feature and `performance_rating`. Report raw p-values and Bonferroni-corrected p-values (7 tests per method, 14 total). Flag any corrected p < 0.05.

**Outputs**: correlation table (CSV), scatter matrix plot of top features vs `performance_rating`.

### EXP-02 — Salary Band Distribution Test

**Covers**: required check 3; framing risk 1.

For each numeric feature, run a Kruskal-Wallis H-test across the 5 `salary_band` levels. Apply Bonferroni correction (7 tests). Produce grouped box plots for any feature with corrected p < 0.05 (or all features if none significant).

**Outputs**: test-statistics table (CSV), box plot grid by salary band.

### EXP-03 — Predictive Signal vs Permutation Null

**Covers**: required check 5; framing risks 1, 3.

Fit a Ridge regression predicting `performance_rating` from all numeric features plus one-hot-encoded `salary_band`, using 5-fold cross-validated R². Compare the observed mean CV R² against a 100-iteration permutation-null distribution. Report the permutation p-value.

**Outputs**: observed vs null R² histogram, permutation p-value.

## Experiment-to-Check Mapping

| Required Check | Experiment(s) |
|---|---|
| Pairwise Pearson correlations with performance_rating | EXP-01 |
| Spearman (rank-based / nonlinear) associations | EXP-01 |
| Salary_band levels show distinct feature distributions | EXP-02 |
| Statistical significance after multiple-comparison correction | EXP-01, EXP-02 |
| Predictive signal exceeds permutation-null baseline | EXP-03 |

## Framing Risk Coverage

| Risk | Mitigation |
|---|---|
| Features may be pure noise | EXP-01 + EXP-03 quantify signal; null result is an expected valid outcome |
| No data dictionary | EXP-01 reveals empirical feature relationships |
| Synthetic data may lack embedded relationships | EXP-03 permutation test directly tests this |
| Multiple-testing false-positive risk | Bonferroni correction in EXP-01 and EXP-02 |
