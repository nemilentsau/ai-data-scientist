# Student GPA Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 600 |
| Columns | 7 |
| Missing values | 0 (any column) |
| Duplicate rows | 0 |
| Duplicate student IDs | 0 |

### Variables

| Variable | Type | Min | Max | Mean | Std |
|---|---|---|---|---|---|
| `student_id` | int (identifier) | 1 | 600 | 300.5 | 173.3 |
| `weekly_study_hours` | float (continuous) | 0.0 | 26.0 | 11.48 | 4.07 |
| `gpa` | float (target) | 1.55 | 4.00 | 3.14 | 0.58 |
| `extracurriculars` | int (ordinal, 0-5) | 0 | 5 | 2.53 | 1.72 |
| `commute_minutes` | int (continuous) | 0 | 80 | 30.15 | 14.61 |
| `part_time_job_hours` | float (continuous) | 0.0 | 27.2 | 8.16 | 5.48 |
| `absences` | int (count) | 0 | 9 | 2.89 | 1.69 |

The data is clean: no missing values, no duplicate records, no obviously invalid entries (e.g., no GPAs above 4.0 or below 0, no negative hours). The `student_id` column is purely an identifier and was excluded from all modeling.

## 2. Exploratory Data Analysis

### 2.1 Distributions

**GPA** is left-skewed (skew = -0.35) with a notable ceiling effect at 4.0 -- 66 students (11%) have the maximum GPA of 4.0. The distribution is mildly platykurtic (kurtosis = -0.48). A Shapiro-Wilk test rejects normality (p < 0.001), largely due to the ceiling spike.

**Study hours** are approximately normally distributed (D'Agostino-Pearson p = 0.91), centered around 11.5 hours/week.

**Part-time job hours** are right-skewed (skew = 0.48), with most students working under 12 hours/week and a few working 20+.

**Commute minutes** are roughly symmetric, centered around 30 minutes.

**Extracurriculars** (0-5) are approximately uniformly distributed across all 6 levels.

**Absences** (0-9) are right-skewed (skew = 0.53), with most students having 0-4 absences.

See: `plots/01_distributions.png`, `plots/07_gpa_distribution.png`

### 2.2 Outliers

Using the IQR method (1.5x IQR), outliers are minimal:

- `weekly_study_hours`: 3 outliers (>23 hrs)
- `commute_minutes`: 3 outliers (>70 min)
- `part_time_job_hours`: 4 outliers (>23.5 hrs)
- `absences`: 5 outliers (>7)
- `gpa`: 0 outliers

These outliers are plausible real values (e.g., a student studying 26 hrs/week or commuting 80 minutes) and were retained in the analysis.

## 3. Key Finding: No Predictive Relationship Exists

### 3.1 Correlation Analysis

All pairwise **Pearson correlations** between features and GPA are effectively zero:

| Feature | Pearson r | Spearman rho | p-value (Spearman) |
|---|---|---|---|
| `weekly_study_hours` | -0.003 | 0.013 | 0.755 |
| `extracurriculars` | -0.008 | -0.005 | 0.905 |
| `commute_minutes` | 0.058 | 0.041 | 0.313 |
| `part_time_job_hours` | 0.003 | 0.007 | 0.872 |
| `absences` | -0.018 | -0.020 | 0.628 |

No feature has even a weak correlation with GPA. Spearman rank correlations confirm this is not a linearity issue.

See: `plots/02_correlation_heatmap.png`

### 3.2 Non-Linear Relationship Checks

**LOWESS smoothing** of each feature vs GPA shows flat trend lines with no curvature, confirming the absence of non-linear patterns (see `plots/03_scatter_vs_gpa.png`).

**Mutual information** (a model-free measure of dependency) returns near-zero values for all features, ruling out complex non-linear relationships.

**ANOVA** for GPA across extracurricular groups: F = 0.09, p = 0.99. The non-parametric Kruskal-Wallis test agrees (H = 0.34, p = 0.997).

### 3.3 Interaction Effects

Heatmaps of mean GPA across binned feature combinations (study hours x job hours, study hours x extracurriculars, absences x extracurriculars) show no meaningful patterns -- values hover around 3.0-3.3 across all cells with no systematic trends.

See: `plots/08_interaction_heatmaps.png`

### 3.4 GPA Ceiling Effect

66 students (11%) have GPA = 4.0. However, t-tests comparing features of 4.0-GPA students vs. others show no significant differences on any feature (all p > 0.48). The ceiling effect does not mask a hidden relationship.

### 3.5 Features Are Independent of Each Other

All features are mutually uncorrelated (max |r| = 0.054 between `weekly_study_hours` and `part_time_job_hours`). Variance inflation factors are all near 1 (range: 2.8-5.7), confirming no multicollinearity. Chi-squared tests between discretized features found no significant associations.

## 4. Modeling

### 4.1 OLS Linear Regression

```
GPA = 3.098 - 0.0005*study_hours - 0.002*extracurriculars + 0.002*commute
      + 0.0001*job_hours - 0.006*absences
```

| Metric | Value |
|---|---|
| R-squared | 0.004 |
| Adjusted R-squared | -0.005 |
| F-statistic | 0.44 (p = 0.82) |
| All coefficients | p > 0.16 |

The model is statistically meaningless. No coefficient is significant. The F-test confirms the model as a whole has no explanatory power.

See: `plots/06_ols_diagnostics.png`

### 4.2 OLS Assumption Checks

Even though the model is useless, diagnostics are clean:

- **Linearity**: Residuals vs. fitted shows no pattern (flat, as expected with no signal)
- **Normality of residuals**: Q-Q plot shows minor deviations in the tails (GPA ceiling effect), but residuals are approximately normal
- **Homoscedasticity**: Breusch-Pagan test non-significant (p = 0.27) -- constant variance
- **Independence**: Durbin-Watson = 2.06, very close to 2.0 -- no autocorrelation
- **Multicollinearity**: All VIFs < 6 -- no collinearity concern

### 4.3 Non-Linear Models (Cross-Validated)

10-fold cross-validated performance:

| Model | CV R-squared | CV MAE | CV RMSE |
|---|---|---|---|
| **Baseline (predict mean)** | **0.000** | **0.476** | **0.582** |
| OLS Linear | -0.051 +/- 0.046 | 0.481 | 0.588 |
| Random Forest | -0.082 +/- 0.077 | 0.484 | 0.596 |
| Gradient Boosting | -0.170 +/- 0.129 | 0.497 | 0.618 |

**Every model performs worse than simply predicting the mean GPA (3.14) for every student.** Negative R-squared values indicate the models are fitting noise. More complex models (Gradient Boosting) overfit more severely.

Random Forest feature importances and permutation importances are all low and reflect noise fitting, not genuine predictive signal.

See: `plots/09_model_comparison.png`

### 4.4 Feature Distributions by GPA Quartile

Boxplots of each feature split by GPA quartile show identical distributions across all quartiles -- the interquartile ranges and medians overlap almost perfectly.

See: `plots/10_features_by_gpa_quartile.png`

## 5. Conclusions

### Primary Finding

**The features in this dataset (study hours, extracurriculars, commute time, part-time job hours, and absences) have no detectable relationship with GPA.** This conclusion is supported by:

1. Near-zero linear correlations (Pearson and Spearman)
2. Near-zero mutual information (rules out non-linear relationships)
3. Non-significant ANOVA and Kruskal-Wallis tests
4. No interaction effects in feature combination heatmaps
5. OLS regression with R-squared = 0.004 and no significant coefficients
6. All ML models performing worse than a naive mean predictor under cross-validation

### Interpretation

There are several possible explanations:

1. **Missing key predictors**: GPA is likely driven by factors not captured in this dataset -- such as course difficulty, prior academic preparation, cognitive ability, motivation, quality of instruction, or socioeconomic factors. The measured variables may be too distal from academic performance.

2. **Measurement granularity**: Self-reported study hours or coarse counts of extracurriculars may not capture the quality or effectiveness of these activities (e.g., 10 focused hours vs. 10 distracted hours).

3. **Synthetic or simulated data**: The combination of (a) perfectly clean data with no missing values, (b) mutually independent features, (c) zero predictive signal, and (d) uniform-like distribution of `extracurriculars` is consistent with independently generated random variables. If this dataset is synthetic, it may have been constructed without embedding real relationships between features and the target.

### Recommendations

- **Do not build predictive models** using only these features -- any apparent fit would be spurious.
- **Collect additional variables** that are theoretically linked to academic performance (e.g., prior GPA, standardized test scores, course load, major, socioeconomic indicators).
- **Investigate data provenance** -- if this data was collected via self-report surveys, measurement error may be washing out real effects. If simulated, the data generation process did not encode feature-target relationships.

## 6. Plots Index

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all variables |
| `plots/02_correlation_heatmap.png` | Pearson correlation matrix |
| `plots/03_scatter_vs_gpa.png` | Scatter plots with LOWESS trends |
| `plots/04_gpa_by_extracurriculars.png` | GPA boxplots by extracurricular count |
| `plots/05_pairplot.png` | Full pairplot (n=200 sample) |
| `plots/06_ols_diagnostics.png` | OLS residual diagnostic plots |
| `plots/07_gpa_distribution.png` | GPA histogram, KDE, and ECDF |
| `plots/08_interaction_heatmaps.png` | Feature interaction heatmaps |
| `plots/09_model_comparison.png` | Cross-validated model performance |
| `plots/10_features_by_gpa_quartile.png` | Features split by GPA quartile |
