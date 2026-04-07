# Analysis Plan

## Dataset Summary
- **Rows**: 800 | **Columns**: 10 (8 numeric, 1 categorical, 1 ID)
- **Target**: `performance_rating` (mean ≈ 50.0, std ≈ 10.0, range 9.5–75.3)
- **Null values**: 0 across all columns
- **Categorical**: `salary_band` with 5 levels (top: L5, freq 170)
- **Key risk**: Dataset name is `pure_noise` — features may be independently generated with no true signal. The analysis must quantify this.

---

## Phase 1: Distribution & Data-Quality Checks

| ID | Check | Output |
|----|-------|--------|
| CHK-01 | Histogram + Shapiro-Wilk test for `performance_rating` | Plot: `dist_performance_rating.png` |
| CHK-02 | Histograms for all numeric features | Plot: `dist_numeric_features.png` |
| CHK-03 | Bar chart of `salary_band` category counts | Plot: `salary_band_counts.png` |
| CHK-04 | Verify `employee_id` is a unique sequential key (no duplicates, no gaps) | Assertion |

## Phase 2: Bivariate Relationships

| ID | Check | Output |
|----|-------|--------|
| CHK-05 | Pearson & Spearman correlations of every numeric feature vs `performance_rating`, with p-values | Table: `correlation_table.csv` |
| CHK-06 | Full pairwise correlation heatmap (numeric features only) | Plot: `correlation_heatmap.png` |
| CHK-07 | Scatter matrix of top-4 features (by absolute correlation) vs `performance_rating` | Plot: `scatter_top4.png` |
| CHK-08 | One-way ANOVA of `performance_rating` across `salary_band` levels | Statistical test result |
| CHK-09 | Box plot of `performance_rating` by `salary_band` | Plot: `boxplot_salary_band.png` |

## Phase 3: Multicollinearity & Redundancy

| ID | Check | Output |
|----|-------|--------|
| CHK-10 | Variance Inflation Factor (VIF) for all numeric predictors | Table |
| CHK-11 | Condition number of the design matrix | Scalar |

## Phase 4: Predictive Modelling (Null-Signal Test)

| ID | Check | Output |
|----|-------|--------|
| CHK-12 | OLS regression of `performance_rating` on all features; report global F-test p-value and R² | Model summary |
| CHK-13 | Permutation importance (random-forest, 5-fold CV) to see if any feature beats random | Plot: `permutation_importance.png` |
| CHK-14 | Compare cross-validated RMSE of full model vs intercept-only (mean) baseline | Numeric comparison |

## Phase 5: Multiple-Testing & Robustness

| ID | Check | Output |
|----|-------|--------|
| CHK-15 | Apply Bonferroni and Benjamini-Hochberg corrections to all p-values from CHK-05 and CHK-08 | Adjusted p-value table |
| CHK-16 | Bootstrap 95% CI for each Pearson correlation coefficient (1000 resamples) | Table |

## Deliverables Expected from Analysis Executor
1. All plots listed above saved as `.png` files.
2. `correlation_table.csv` with raw and adjusted p-values.
3. A summary dict/JSON with key statistics (R², F-test p, VIF max, permutation scores).
4. `analysis_report.md` written by the executor summarising findings.
