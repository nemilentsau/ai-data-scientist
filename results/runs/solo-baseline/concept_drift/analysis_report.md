# Manufacturing Process Defect Rate Analysis

## Executive Summary

This dataset contains 1,500 observations of a manufacturing process recorded at 30-minute intervals from June 1 to July 2, 2023. The target variable, `defect_rate`, is **statistically independent of all measured process parameters** (temperature, pressure, vibration, speed) and categorical factors (operator shift, time of day, day of week). No model -- linear, non-linear, or ensemble -- achieves predictive performance above chance. The measured sensor variables do not explain variation in defect rates; the root cause lies in unmeasured factors.

---

## 1. Data Overview

| Property | Value |
|---|---|
| Rows | 1,500 |
| Columns | 7 |
| Time range | 2023-06-01 00:00 to 2023-07-02 05:30 |
| Sampling interval | 30 minutes (regular) |
| Missing values | 0 |
| Duplicate rows | 0 |
| Duplicate timestamps | 0 |

### Variables

| Variable | Type | Mean | Std | Min | Max |
|---|---|---|---|---|---|
| `temperature_c` | float | 200.2 | 5.0 | 183.8 | 219.3 |
| `pressure_bar` | float | 50.0 | 2.95 | 41.1 | 62.2 |
| `vibration_mm_s` | float | 1.93 | 1.91 | 0.0 | 12.3 |
| `speed_rpm` | int | 2993 | 199 | 2365 | 3623 |
| `operator` | categorical | -- | -- | Shift_A (498) | Shift_B (520), Shift_C (482) |
| `defect_rate` | float | 0.862 | 0.192 | 0.011 | 1.000 |

### Data Quality

- **No missing data.** All 1,500 rows are complete.
- **No duplicate timestamps.** Each 30-minute slot is unique.
- **Outliers (IQR method):** temperature (11), pressure (18), vibration (76), speed (15). Vibration is right-skewed with a long tail, which is physically expected for vibration measurements.
- **No data quality issues** that would invalidate analysis.

---

## 2. Target Variable: `defect_rate`

The defect rate distribution is highly unusual:

- **47.5% of observations are exactly 1.0** (713 out of 1,500)
- The remaining 52.5% range from 0.011 to 0.9997
- Overall distribution is **strongly left-skewed** (skewness = -1.49)
- Among non-1.0 values: mean = 0.738, std = 0.194

### Distributional Fit

The non-1.0 values follow a **Beta(2.92, 1.05) distribution** (Kolmogorov-Smirnov test: p = 0.48, fail to reject). The overall distribution is best described as a **one-inflated Beta distribution** -- a mixture of a point mass at 1.0 (weight ~0.475) and a Beta(2.9, 1.0) component.

The full distribution is decidedly non-normal (Shapiro-Wilk p < 0.000001).

*See: `plots/01_distributions.png`, `plots/11_distribution_analysis.png`*

---

## 3. Exploratory Data Analysis

### 3.1 Correlations

All Pearson correlations with `defect_rate` are negligible:

| Feature | Pearson r | Spearman rho | p-value (Spearman) |
|---|---|---|---|
| `temperature_c` | 0.025 | 0.039 | 0.131 |
| `pressure_bar` | -0.063 | -0.040 | 0.123 |
| `vibration_mm_s` | -0.017 | -0.027 | 0.297 |
| `speed_rpm` | 0.017 | 0.014 | 0.582 |

No correlation reaches statistical significance at alpha = 0.05. The strongest (pressure_bar, r = -0.063) explains only 0.4% of variance.

*See: `plots/02_correlation_heatmap.png`, `plots/03_defect_vs_features.png`*

### 3.2 Operator Shift Effects

| Shift | Mean Defect Rate | % at 1.0 |
|---|---|---|
| Shift_A | 0.861 | 46.6% |
| Shift_B | 0.853 | 46.3% |
| Shift_C | 0.875 | 49.8% |

**Kruskal-Wallis test: H = 2.58, p = 0.275** -- no significant difference across shifts.

*See: `plots/05_boxplots_by_operator.png`, `plots/06_defect_by_hour_operator.png`*

### 3.3 Temporal Patterns

- **No hourly pattern:** defect rate is stable across all 24 hours (range of hourly means: 0.837 to 0.898)
- **No day-of-week pattern:** range of daily means: 0.842 to 0.894
- **No temporal autocorrelation:** lag-1 autocorrelation = -0.018 (within noise bounds). The defect rate behaves as white noise over time -- successive readings are independent.
- **No trend or seasonality** visible in rolling 24-hour averages.

*See: `plots/04_timeseries.png`, `plots/08_autocorrelation.png`, `plots/13_rolling_statistics.png`*

### 3.4 Non-linear and Threshold Effects

- **Binned feature analysis:** mean defect rate is flat across quantile bins of every feature (no threshold effects visible).
- **Interaction analysis:** the number of simultaneously extreme features (0, 1, 2, 3, or 4 features beyond 10th/90th percentile) has no relationship with defect rate.
- **Mutual information:** all values < 0.02 nats (essentially zero non-linear dependence).
- **Variance homogeneity (Levene's test):** only pressure shows marginally significant heteroscedasticity (p = 0.028), but this is weak and does not translate into predictive power.

*See: `plots/07_defect_rate_by_binned_features.png`, `plots/09_pairwise_interactions.png`*

---

## 4. Modeling

### 4.1 Regression Models (predicting continuous defect_rate)

All models were evaluated with 5-fold cross-validation.

| Model | R² (CV) | RMSE (CV) |
|---|---|---|
| Linear Regression | -0.006 +/- 0.010 | 0.193 |
| Linear Regression (with interactions) | -0.004 +/- 0.019 | 0.192 |
| Decision Tree (depth=3) | -0.021 | 0.194 |
| Random Forest (200 trees) | -0.043 +/- 0.025 | 0.196 |
| Gradient Boosting (200 trees) | -0.130 +/- 0.048 | 0.204 |
| RF with lagged + rolling features | -0.029 +/- 0.031 | -- |

**All R² values are negative**, meaning every model performs worse than simply predicting the mean. More complex models (RF, GB) overfit to noise and perform even worse out-of-sample.

### 4.2 Classification (defect_rate = 1.0 vs < 1.0)

| Model | Accuracy (CV) | AUC-ROC (CV) |
|---|---|---|
| Logistic Regression | 0.520 +/- 0.020 | 0.524 |
| Random Forest Classifier | 0.495 +/- 0.033 | 0.499 |
| Baseline (majority class) | 0.525 | 0.500 |

AUC-ROC of ~0.50 means these models perform at **chance level** -- no better than flipping a coin.

### 4.3 Two-Part Model

Given the one-inflated distribution, a two-part model was tested:
1. **Part 1 (Logistic):** Predicting P(defect_rate = 1.0) -- AUC = 0.503 (chance)
2. **Part 2 (RF regression):** Predicting magnitude among non-1.0 cases -- R² = -0.053 (no signal)

Neither component has predictive power.

### 4.4 Beta Regression (GLM)

A generalized linear model with Binomial family was fit to non-1.0 values. All coefficients are non-significant:

| Feature | Coefficient | p-value |
|---|---|---|
| `temperature_c` | -0.0005 | 0.975 |
| `pressure_bar` | -0.0317 | 0.251 |
| `vibration_mm_s` | -0.0062 | 0.883 |
| `speed_rpm` | -0.00004 | 0.916 |

### 4.5 Effect Sizes

Cohen's d comparing groups (defect_rate = 1.0 vs < 1.0) across features:

| Feature | Cohen's d |
|---|---|
| `temperature_c` | 0.083 |
| `speed_rpm` | 0.060 |
| `pressure_bar` | -0.040 |
| `vibration_mm_s` | -0.036 |

All effect sizes are **negligible** (well below the 0.2 threshold for "small" effects).

*See: `plots/10_feature_importance.png`, `plots/12_partial_dependence.png`, `plots/14_summary_dashboard.png`*

---

## 5. Assumption Checks

| Assumption | Status |
|---|---|
| **Linearity** | Checked via scatter plots & binned analysis -- no linear or monotonic relationship exists |
| **Non-linear relationships** | Checked via RF, GB, mutual information, binned analysis -- none detected |
| **Independence of observations** | Confirmed: autocorrelation at all lags is within noise bounds |
| **Normality of target** | Violated (left-skewed, one-inflated) -- appropriate models (Beta regression, non-parametric tests) were used |
| **Multicollinearity** | Not an issue -- features are nearly uncorrelated with each other (max r = 0.034) |
| **Temporal stationarity** | Rolling statistics are stable -- no drift or regime changes |
| **Homogeneity of variance** | Marginal heteroscedasticity for pressure (Levene p = 0.028), no practical consequence |

---

## 6. Key Findings

1. **The measured process parameters do not predict defect rates.** This is the central finding, supported by every statistical and machine learning approach attempted. Correlations are near zero, all models fail, effect sizes are negligible, and no non-linear or interaction effects are detectable.

2. **The defect rate follows a one-inflated Beta distribution.** Approximately 47.5% of readings are exactly 1.0, and the remainder follow Beta(2.9, 1.0). This distributional structure is independent of process conditions.

3. **No operator shift effects exist.** All three shifts produce statistically indistinguishable defect rate distributions (Kruskal-Wallis p = 0.27).

4. **No temporal patterns exist.** No autocorrelation, no time-of-day effects, no day-of-week effects, no trends, no seasonality. Each observation's defect rate is independent of when it was recorded.

5. **The process parameters themselves are well-behaved.** Temperature, pressure, vibration, and speed are approximately independently distributed with no concerning trends or anomalies, and very low inter-feature correlation.

---

## 7. Recommendations

1. **Investigate unmeasured variables.** The defect rate is driven by factors not captured in this dataset. Candidates include: raw material properties (batch, supplier, composition), environmental factors (humidity, ambient temperature), tooling wear/age, specific machine or production line identity, or upstream process parameters.

2. **Clarify the semantics of `defect_rate = 1.0`.** The fact that 47.5% of readings are exactly 1.0 may indicate censoring, a measurement artifact, or that this is actually a "pass rate" or "yield" metric rather than a defect rate. Understanding the data generation process is essential.

3. **Expand the sensor suite.** The current four process variables (temperature, pressure, vibration, speed) are informative about the machine state but are apparently unrelated to product quality. Additional measurements closer to the quality-determining step of the process are needed.

4. **Do not build predictive models on these features alone.** Any model trained on these features will not generalize -- it will fit noise. Resources should be directed at data collection, not modeling.

---

## 8. Plots Index

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all numeric variables |
| `plots/02_correlation_heatmap.png` | Pearson correlation matrix |
| `plots/03_defect_vs_features.png` | Scatter plots: defect_rate vs each feature |
| `plots/04_timeseries.png` | Time series of all variables |
| `plots/05_boxplots_by_operator.png` | Feature distributions by operator shift |
| `plots/06_defect_by_hour_operator.png` | Defect rate by hour and operator |
| `plots/07_defect_rate_by_binned_features.png` | Mean defect rate across feature quantile bins |
| `plots/08_autocorrelation.png` | ACF and PACF of defect rate |
| `plots/09_pairwise_interactions.png` | Pairwise feature scatter plots colored by defect rate |
| `plots/10_feature_importance.png` | RF and permutation feature importance |
| `plots/11_distribution_analysis.png` | Defect rate distribution deep dive with Beta fit |
| `plots/12_partial_dependence.png` | Partial dependence plots from Random Forest |
| `plots/13_rolling_statistics.png` | Rolling 24h statistics for defect rate, temperature, vibration |
| `plots/14_summary_dashboard.png` | Summary dashboard of key findings |
