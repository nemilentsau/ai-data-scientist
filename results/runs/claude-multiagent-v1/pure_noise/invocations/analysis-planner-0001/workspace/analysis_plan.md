# Analysis Plan

## Dataset Summary

| Property | Value |
|---|---|
| Rows | 800 |
| Columns | 10 (8 numeric, 1 categorical, 1 identifier) |
| Nulls | 0 across all columns |
| Target (primary) | `performance_rating` (float64, mean 50.0, std 10.0) |
| Categorical | `salary_band` (5 levels: L1-L5) |

## Primary Frame

**Identify predictors of employee performance rating from workplace attributes.**

## Key Risks Identified in Framing

1. Data may contain **no genuine signal** -- features appear independently generated.
2. Salary-band labels show **no consistent ordering** with experience or performance.
3. With 800 rows and 9 features, **spurious correlations** may appear significant without correction.
4. All numeric features appear **independently distributed**, risking overfitting noise.

These risks make rigorous null-signal detection the highest-priority objective of this analysis.

---

## Analysis Stages

### Stage 1: Univariate Distributions (EXP-01, EXP-02)

**Goal**: Characterise the marginal distribution of every feature and the target.

- Histogram + KDE for each numeric column.
- Bar chart for `salary_band` frequency.
- Shapiro-Wilk normality test on `performance_rating`.
- Check for multimodality in `performance_rating` (Hartigan dip test or visual inspection).

**Artifacts**: `distributions.png`, distribution statistics table.

### Stage 2: Bivariate Association Tests (EXP-03, EXP-04, EXP-05)

**Goal**: Quantify linear and nonlinear associations between each feature and `performance_rating`.

- Pearson and Spearman correlations for every numeric feature vs `performance_rating`.
- Scatter-plot matrix of all numeric features with LOWESS smoothers.
- Distance correlation (or mutual information) for each feature vs `performance_rating` to detect nonlinear relationships.
- ANOVA / Kruskal-Wallis: `performance_rating` across `salary_band` groups.
- Box plots of `performance_rating` by `salary_band`.

**Artifacts**: `correlation_heatmap.png`, `scatter_matrix.png`, `salary_band_boxplot.png`, association statistics table.

### Stage 3: Multicollinearity Check (EXP-06)

**Goal**: Assess pairwise and higher-order collinearity among predictors.

- Full Pearson correlation matrix heatmap for all numeric features.
- Variance Inflation Factor (VIF) for each predictor in a linear model.

**Artifacts**: `feature_correlation_heatmap.png`, VIF table.

### Stage 4: Predictive Modelling vs Baseline (EXP-07, EXP-08)

**Goal**: Determine whether any model outperforms a no-skill (mean-prediction) baseline.

- Baseline model: predict mean `performance_rating` for all rows. Record RMSE and R^2.
- Linear regression (OLS): 5-fold CV. Record RMSE, R^2, F-test p-value.
- Random forest regressor: 5-fold CV. Record RMSE, R^2, feature importances.
- Permutation test (100+ shuffles): compare observed CV R^2 against null distribution of R^2 from shuffled targets.

**Artifacts**: `model_comparison.png`, `permutation_test.png`, `feature_importance.png`, model metrics table.

### Stage 5: Salary-Band Prediction (EXP-09)

**Goal**: Test whether `salary_band` is predictable from numeric features.

- Random forest classifier: 5-fold CV. Record accuracy vs majority-class baseline.
- Confusion matrix and classification report.

**Artifacts**: `salary_band_confusion.png`, classification metrics table.

### Stage 6: Cluster / Segment Discovery (EXP-10)

**Goal**: Check for natural employee segments in the feature space.

- Standardize all numeric features.
- PCA scree plot + first two components scatter (coloured by `salary_band`).
- K-Means with k=2..6, silhouette score for each k.
- Compare cluster labels vs `salary_band` (adjusted Rand index).

**Artifacts**: `pca_scatter.png`, `silhouette_scores.png`, cluster comparison table.

### Stage 7: Multiple-Comparison Correction (EXP-11)

**Goal**: Apply corrections to all hypothesis tests performed above.

- Collect all p-values from Stages 2-6.
- Apply Benjamini-Hochberg FDR correction at alpha=0.05.
- Report which (if any) associations survive correction.

**Artifacts**: corrected p-value table.

---

## Validation Checkpoints

| Checkpoint | Pass Criterion |
|---|---|
| No nulls after load | All columns have 0 nulls |
| Row count matches profile | 800 rows loaded |
| Target distribution plausible | mean ~ 50, std ~ 10 |
| Baseline RMSE computed | RMSE ~ 10 (std of target) |
| All p-values collected | Count matches number of tests run |
| FDR correction applied | Adjusted p-values reported |

## Decision Framework

- If **no association survives FDR correction** and **model R^2 ~ 0**: conclude the dataset contains no detectable signal. Report that features are independently generated noise.
- If **some associations survive** but **model R^2 is low** (< 0.05): report weak, possibly spurious structure.
- If **model significantly beats baseline**: identify top predictors and report effect sizes.
