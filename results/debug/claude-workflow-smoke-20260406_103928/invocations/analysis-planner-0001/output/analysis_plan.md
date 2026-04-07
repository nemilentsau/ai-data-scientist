# Analysis Plan

## Dataset Summary

- **Rows**: 800, **Columns**: 10, **Nulls**: 0
- **Target**: `performance_rating` (continuous, mean 50.0, std 10.0, range 9.5-75.3)
- **Numeric predictors**: `years_experience`, `training_hours`, `team_size`, `projects_completed`, `satisfaction_score`, `commute_minutes`, `remote_pct`
- **Categorical predictor**: `salary_band` (5 levels: L1-L5)
- **Key risk**: The dataset name and framing both suggest features may be independently generated noise with no genuine signal.

## Analysis Steps

### Step 1 — Distribution & Sanity Checks (EXP-DIST)
- Histogram of `performance_rating` to confirm approximate shape.
- Histograms of each numeric predictor.
- Value-count bar chart for `salary_band`.
- Goal: confirm uniform/normal shapes and spot any anomalies before modelling.

### Step 2 — Pairwise Correlations (EXP-CORR)
- Compute Pearson and Spearman correlation matrices for all numeric columns.
- Generate a heatmap of the correlation matrix.
- Flag any |r| > 0.10 pairs for further inspection.
- Directly addresses required check: "Test pairwise correlations between numeric features and performance_rating".

### Step 3 — Non-Linear Relationship Scan (EXP-NONLIN)
- For each numeric predictor vs `performance_rating`, compute Mutual Information (MI) regression score.
- Scatter plots with LOWESS smoother for the top-3 MI-scoring features.
- Directly addresses required check: "Check for non-linear relationships".

### Step 4 — Salary Band Group Comparison (EXP-ANOVA)
- One-way ANOVA of `performance_rating` across `salary_band` groups.
- Box plot of `performance_rating` by `salary_band`.
- Report F-statistic, p-value, and effect size (eta-squared).
- Directly addresses required check: "Verify that salary_band groups differ meaningfully".

### Step 5 — Multicollinearity Check (EXP-VIF)
- Compute Variance Inflation Factor (VIF) for all numeric predictors.
- Flag any VIF > 5.
- Directly addresses required check: "Check for multicollinearity among predictor features".

### Step 6 — Predictive Model Fit (EXP-MODEL)
- Fit a Random Forest regressor with 5-fold cross-validation predicting `performance_rating`.
- Report mean R-squared and RMSE across folds.
- Compare against a dummy (mean-prediction) baseline.
- Compute permutation feature importances.
- If cross-validated R-squared <= 0.02, declare "no reliable signal detected".
- Directly addresses required check: "Assess overall model fit and warn if no feature is predictive".

### Step 7 — Noise Confirmation (EXP-NOISE)
- Permutation test: shuffle `performance_rating` 200 times, re-fit model each time, build null distribution of R-squared.
- Compare actual R-squared against this null distribution to compute empirical p-value.
- This is the definitive test for the framing risk that data may be pure noise.

## Expected Outputs

| Experiment | Primary Plot | Key Metric |
|---|---|---|
| EXP-DIST | histograms grid | visual inspection |
| EXP-CORR | correlation heatmap | max absolute Pearson r with target |
| EXP-NONLIN | scatter + LOWESS | max MI score |
| EXP-ANOVA | box plot by salary_band | F-statistic, p-value, eta-squared |
| EXP-VIF | VIF table | max VIF value |
| EXP-MODEL | feature importance bar chart | CV R-squared, RMSE |
| EXP-NOISE | null distribution histogram | empirical p-value |
