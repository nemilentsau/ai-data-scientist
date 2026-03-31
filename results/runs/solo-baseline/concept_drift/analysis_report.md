# Manufacturing Process Data — Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 1,500 |
| Columns | 7 |
| Time span | 2023-06-01 to 2023-07-02 (31 days) |
| Frequency | 30-minute intervals |
| Missing values | None |
| Duplicates | None |

**Columns:**
- `timestamp` — 30-minute interval timestamps
- `temperature_c` — Process temperature (°C)
- `pressure_bar` — Process pressure (bar)
- `vibration_mm_s` — Vibration level (mm/s)
- `speed_rpm` — Rotational speed (RPM)
- `operator` — Shift identifier (Shift_A, Shift_B, Shift_C)
- `defect_rate` — Target variable, bounded [0.011, 1.0]

**Basic Statistics (numeric features):**

| Feature | Mean | Std | Min | Max | Skew |
|---|---|---|---|---|---|
| temperature_c | 200.2 | 5.0 | 183.8 | 219.3 | ~0 (normal) |
| pressure_bar | 50.1 | 3.0 | 40.9 | 61.8 | ~0 (normal) |
| vibration_mm_s | 1.9 | 1.9 | 0.0 | 12.2 | 1.76 (right-skewed) |
| speed_rpm | 2993 | 199 | 2365 | 3623 | ~0 (normal) |
| defect_rate | 0.862 | 0.192 | 0.011 | 1.0 | -1.56 (left-skewed) |

---

## 2. Key Findings

### Finding 1: defect_rate is independent of all measured process variables

This is the central and most important result of this analysis. Despite testing linear, non-linear, and machine learning approaches, **none of the measured features (temperature, pressure, vibration, speed, operator, time) have meaningful predictive power over defect_rate**.

**Evidence:**
- **Pearson correlations**: All |r| < 0.07 (largest: pressure_bar at r = -0.063)
- **Spearman correlations**: All |ρ| < 0.04, all p > 0.12 (non-significant)
- **Mutual information**: All values < 0.02 (near zero dependency)
- **OLS regression**: R² = 0.010, F-test p = 0.053 (borderline; no individual predictor significant at p < 0.01)
- **Random Forest CV R²**: -0.039 (worse than predicting the mean)
- **Gradient Boosting CV R²**: -0.129 (worse than predicting the mean)
- **Classification (defect_rate = 1.0 vs < 1.0)**: AUC = 0.50 across all models (random chance)

No model outperforms the trivial baseline of predicting the mean (MAE = 0.154, RMSE = 0.192).

### Finding 2: defect_rate is right-censored at 1.0

47.5% of observations (713/1500) have defect_rate exactly equal to 1.0. The non-censored portion (n = 787) follows a **Beta(2.92, 1.05) distribution** (KS test p = 0.48, good fit). This censoring pattern suggests:
- 1.0 likely represents a measurement ceiling (e.g., "100% of sampled items defective" or a sensor saturation)
- The true latent defect rate may exceed 1.0 for censored observations
- However, even accounting for censoring (chi-squared tests on censoring probability by feature quartile), no feature predicts the probability of being at the ceiling (all p > 0.43)

### Finding 3: No temporal structure in defect_rate

- **No time trend**: Linear trend slope ≈ 0 (p = 0.85)
- **No autocorrelation**: Ljung-Box test non-significant at all tested lags (1, 6, 12, 24, 48)
- **No day-of-week effect**: OLS coefficient p = 0.06 (not significant); daily means range only from 0.84 to 0.89
- **No hour-of-day effect**: Hourly means range from 0.84 to 0.90, no systematic pattern
- **No operator effect**: Kruskal-Wallis H = 2.58, p = 0.27; all pairwise Mann-Whitney tests non-significant

### Finding 4: Feature distributions are well-behaved

- **Temperature, pressure, speed**: Approximately normal (Shapiro-Wilk p > 0.26)
- **Vibration**: Follows an **exponential distribution** (KS test p = 0.91, rate λ ≈ 0.52). This is physically plausible — most observations have low vibration, with occasional high-vibration events
- Feature-to-feature correlations are negligible (all |r| < 0.04)
- No multicollinearity concerns

### Finding 5: Anomalies are driven by extreme vibration, not defect patterns

Isolation Forest (5% contamination) identified 75 anomalous observations. These are characterized by:
- **Much higher vibration**: +166% of normal standard deviation (mean 4.6 vs 1.8 mm/s)
- **Lower defect_rate**: mean 0.55 vs 0.88 for normal observations
- The paradoxical vibration–defect relationship (higher vibration, lower defects) underscores that measured vibration does not drive defect rates in a physically intuitive way

---

## 3. Modeling Details

### 3.1 Regression Models (Target: defect_rate)

| Model | CV R² | CV MAE | CV RMSE |
|---|---|---|---|
| Baseline (predict mean) | 0.000 | 0.154 | 0.192 |
| OLS Linear Regression | -0.007 ± 0.009 | 0.154 ± 0.005 | 0.193 ± 0.006 |
| Ridge Regression | -0.007 ± 0.009 | 0.154 ± 0.005 | 0.193 ± 0.006 |
| Random Forest | -0.039 ± 0.031 | 0.157 ± 0.006 | 0.196 ± 0.006 |
| Gradient Boosting | -0.129 ± 0.040 | 0.161 ± 0.006 | 0.204 ± 0.006 |

Negative R² indicates models are worse than the mean — they are fitting noise.

### 3.2 Classification Models (Target: defect_rate = 1.0)

| Model | CV Accuracy | CV AUC |
|---|---|---|
| Baseline (majority class) | 0.525 | 0.500 |
| Logistic Regression | 0.525 ± 0.022 | 0.522 ± 0.022 |
| Random Forest | 0.506 ± 0.025 | 0.501 ± 0.034 |
| Gradient Boosting | 0.485 ± 0.011 | 0.475 ± 0.018 |

AUC ≈ 0.50 confirms models cannot distinguish censored from non-censored observations.

### 3.3 OLS Regression (Formal Inference)

Only `pressure_bar` reached marginal significance (coef = -0.004, p = 0.013), but this explains < 0.4% of variance. The overall model F-test (p = 0.053) is borderline non-significant. Given the number of predictors tested, this is likely a false positive or a negligibly small effect.

### 3.4 Assumption Checks

- **Linearity**: Binned mean plots show no non-linear trends
- **Independence**: No autocorrelation in defect_rate (Ljung-Box all p > 0.18)
- **Homoscedasticity**: Variance of defect_rate is stable across feature quartiles (range: 0.030–0.042)
- **Normality of residuals**: Residuals are non-normal due to the censored/bounded target; however, since all models fail, this is moot

---

## 4. Interpretation and Recommendations

### What this means

The measured process variables (temperature, pressure, vibration, speed) and operational factors (operator shift, time of day, day of week) **do not explain variation in defect_rate**. The defect rate appears to behave as a **random process independent of the monitored parameters**.

### Possible explanations

1. **Unmeasured confounders**: The true drivers of defect rate are not captured in this dataset. Candidates include: raw material quality/batch, humidity, tool wear, coolant condition, or upstream process parameters.
2. **Process in statistical control**: If the process is well-controlled within its operating window, the observed variation in defect_rate may be inherent stochastic noise that cannot be reduced by adjusting these parameters.
3. **Measurement limitation**: The defect_rate variable being censored at 1.0 may obscure true relationships. If 47.5% of true values exceed 1.0, the ceiling effect compresses the range and attenuates correlations.
4. **Incorrect defect attribution**: Defects may originate from a different process stage than the one being monitored.

### Recommended next steps

1. **Investigate unmeasured variables**: Collect data on raw material properties, environmental conditions (humidity, ambient temperature), tool/die condition, and upstream process parameters.
2. **Review the defect_rate measurement**: Clarify what 1.0 represents. If it is a ceiling, consider whether uncensored measurements are available.
3. **Process capability study**: Conduct a formal process capability analysis (Cp/Cpk) to determine if the process is inherently capable and the variation is within acceptable limits.
4. **Root cause analysis**: For low-defect-rate observations (the lower tail), investigate what conditions were present using methods beyond the recorded sensor data (e.g., operator logs, maintenance records).

---

## 5. Plots Generated

| File | Description |
|---|---|
| `plots/01_distributions.png` | Distributions of all numeric variables |
| `plots/02_defect_rate_detail.png` | Deep dive on defect_rate (censoring, ECDF, sub-1.0 distribution) |
| `plots/03_timeseries.png` | Time series of all variables with 24h rolling mean |
| `plots/04_correlation_heatmap.png` | Pearson correlation matrix |
| `plots/05_scatter_vs_defect.png` | Scatter plots of each feature vs defect_rate |
| `plots/06_boxplots_by_operator.png` | Feature distributions by operator shift |
| `plots/07_pairplot.png` | Pairplot colored by operator (n=500 sample) |
| `plots/08_daily_trends.png` | Daily aggregated trends |
| `plots/09_feature_importance.png` | Random Forest feature importances |
| `plots/10_residual_analysis.png` | Residual diagnostics for Random Forest |
| `plots/11_binned_means.png` | Non-linear relationship check (binned means ± 95% CI) |
| `plots/12_anomalies.png` | Isolation Forest anomaly detection |
| `plots/13_summary.png` | Key findings summary dashboard |
| `plots/14_marginal_effects.png` | Marginal effects of weakest predictors |

---

## 6. Technical Notes

- **Software**: Python 3, pandas, scikit-learn, statsmodels, scipy, matplotlib, seaborn
- **Cross-validation**: 5-fold, shuffled, random_state=42
- **All statistical tests**: Two-sided, significance level α = 0.05
- **Anomaly detection**: Isolation Forest with 5% contamination rate
- **Distribution fitting**: Maximum likelihood estimation via scipy.stats
