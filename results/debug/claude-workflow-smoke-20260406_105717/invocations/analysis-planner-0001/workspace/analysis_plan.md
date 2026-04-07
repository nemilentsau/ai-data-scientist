# Analysis Plan

## Dataset summary

| Property | Value |
|---|---|
| Rows | 800 |
| Numeric features | 8 (years_experience, training_hours, team_size, projects_completed, satisfaction_score, commute_minutes, performance_rating, remote_pct) |
| Categorical features | 1 (salary_band: L1-L5) |
| Nulls | 0 |
| Assumed target | performance_rating |

## Experiments

### EXP-01: Pairwise correlation matrix with Bonferroni-corrected significance

**Covers**: required check 1 ("Compute pairwise correlations among all numeric features and test significance with Bonferroni correction")

**Addresses risk**: multiple-testing inflation (framing risk 3)

**Method**: Pearson correlation for all 28 numeric pairs. Compute p-values with `scipy.stats.pearsonr`. Apply Bonferroni correction (alpha = 0.05 / 28). Report which pairs, if any, survive correction.

**Outputs**: correlation heatmap (`corr_heatmap.png`), significance table in results JSON.

---

### EXP-02: Commute-minutes distribution and outlier inspection

**Covers**: required check 5 ("Inspect commute_minutes for right-skew outliers before modeling")

**Method**: Compute skewness, IQR, and flag values > Q3 + 1.5*IQR. Plot histogram with boxplot overlay.

**Outputs**: distribution plot (`commute_dist.png`), skewness statistic, outlier count and threshold in results JSON.

---

### EXP-03: Permutation feature importance + baseline model comparison

**Covers**: required check 2 ("permutation-based feature importance test against performance_rating") and required check 3 ("baseline model indistinguishable from fitted model")

**Addresses risks**: spurious fits (framing risk 2), no explicit target (framing risk 1)

**Method**:
1. Fit a single `RandomForestRegressor(n_estimators=100, random_state=42)` on all 8 numeric features predicting `performance_rating`.
2. Compute `permutation_importance` (n_repeats=30, random_state=42) on held-out test set (80/20 split).
3. Record test-set R-squared. Compare to mean-predictor baseline (R-squared = 0 by definition). Report whether model R-squared is significantly > 0 using the permutation null distribution from step 2.

**Outputs**: feature importance bar chart (`feat_importance.png`), model vs baseline R-squared comparison in results JSON.

---

### EXP-04: Salary-band group separation

**Covers**: required check 4 ("salary_band levels show meaningful separation on numeric features via ANOVA or Kruskal-Wallis")

**Addresses risk**: class imbalance in salary_band (framing risk 4)

**Method**: For each numeric feature, run Kruskal-Wallis H-test across salary_band groups (robust to non-normality and unequal group sizes). Apply Bonferroni correction (alpha = 0.05 / 8). Report which features, if any, differ significantly across bands.

**Outputs**: box plots per feature by salary_band (`salary_band_boxplots.png`), test statistics table in results JSON.

## Experiment-to-check mapping

| Required check | Experiment |
|---|---|
| 1. Pairwise correlations + Bonferroni | EXP-01 |
| 2. Permutation feature importance | EXP-03 |
| 3. Baseline vs fitted model | EXP-03 |
| 4. salary_band ANOVA/Kruskal-Wallis | EXP-04 |
| 5. commute_minutes skew/outliers | EXP-02 |
