# Dataset Analysis Report

## Executive Summary

This dataset contains **1,500 observations** and **7 original columns** sampled at a perfectly regular **30-minute cadence** from **2023-06-01 00:00:00** to **2023-07-02 05:30:00**.

The data are structurally clean: there are **no missing values**, timestamps are unique and monotonic, and the process signals remain in plausible numeric ranges. The main analytical challenge is not data quality but **weak explanatory signal**:

- `defect_rate` is strongly bounded and **47.5% of records equal exactly `1.0`**, creating a severe upper-bound pile-up.
- Pairwise linear relationships between the process variables and `defect_rate` are negligible; the largest absolute Pearson correlation is only **0.063**.
- Time-aware regression and classification models perform at or near trivial baselines, indicating that the available features explain very little of the target variation.
- OLS residual diagnostics reject normality, so classical linear-model inference is not reliable even though autocorrelation and multicollinearity are not major problems.

The practical conclusion is that, with the variables present in `dataset.csv`, there is **no strong evidence of a controllable, stable driver of `defect_rate`**. Better prediction likely requires additional features such as machine state, material batch, maintenance history, sensor lags, or upstream/downstream quality context.

## 1. Data Loading and Inspection

- Shape: **1500 rows x 7 columns**
- Timestamp frequency: **0 days 00:30:00** for all 1,499 gaps
- Missing values: **0 across all columns**
- Duplicate timestamps: **0**
- Operators: Shift_B (520), Shift_A (498), Shift_C (482)

### Numeric Summary

| feature | count | mean | std | min | 25% | 50% | 75% | max | missing | skew |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| temperature_c | 1500.0 | 200.2459 | 4.9518 | 183.8 | 196.9 | 200.25 | 203.4 | 219.3 | 0 | 0.0663 |
| pressure_bar | 1500.0 | 50.0449 | 2.9504 | 40.94 | 48.09 | 49.995 | 52.01 | 61.78 | 0 | 0.0175 |
| vibration_mm_s | 1500.0 | 1.9381 | 1.9171 | 0.0 | 0.5542 | 1.319 | 2.6792 | 12.193 | 0 | 1.7641 |
| speed_rpm | 1500.0 | 2992.8033 | 198.876 | 2365.0 | 2864.0 | 2996.5 | 3132.0 | 3623.0 | 0 | -0.0484 |
| defect_rate | 1500.0 | 0.8625 | 0.1922 | 0.0112 | 0.7657 | 0.9808 | 1.0 | 1.0 | 0 | -1.4896 |

### Null Counts

| column | null_count |
| --- | --- |
| timestamp | 0 |
| temperature_c | 0 |
| pressure_bar | 0 |
| vibration_mm_s | 0 |
| speed_rpm | 0 |
| operator | 0 |
| defect_rate | 0 |

### Distribution Checks

| feature | shapiro_stat | shapiro_pvalue |
| --- | --- | --- |
| temperature_c | 0.9973 | 0.5992 |
| pressure_bar | 0.9973 | 0.6012 |
| vibration_mm_s | 0.8108 | 0.0 |
| speed_rpm | 0.9984 | 0.9371 |
| defect_rate | 0.7727 | 0.0 |

Interpretation:

- `temperature_c`, `pressure_bar`, and `speed_rpm` look approximately Gaussian in moderate samples.
- `vibration_mm_s` is strongly right-skewed.
- `defect_rate` is decisively non-normal because it is bounded and concentrated near the upper limit.

## 2. Exploratory Data Analysis

Plots saved to `./plots/`:

- `missingness_heatmap.png`
- `numeric_distributions.png`
- `correlation_heatmap.png`
- `process_signals_over_time.png`
- `defect_rate_time_series.png`
- `defect_rate_vs_features.png`
- `groupwise_boxplots.png`
- `holdout_predicted_vs_actual.png`
- `ols_diagnostics.png`

### Correlation Matrix

| feature | temperature_c | pressure_bar | vibration_mm_s | speed_rpm | defect_rate |
| --- | --- | --- | --- | --- | --- |
| temperature_c | 1.0 | 0.0337 | 0.0158 | 0.0075 | 0.0247 |
| pressure_bar | 0.0337 | 1.0 | -0.0074 | 0.0045 | -0.0626 |
| vibration_mm_s | 0.0158 | -0.0074 | 1.0 | -0.0088 | -0.0175 |
| speed_rpm | 0.0075 | 0.0045 | -0.0088 | 1.0 | 0.017 |
| defect_rate | 0.0247 | -0.0626 | -0.0175 | 0.017 | 1.0 |

Key EDA findings:

- `defect_rate` has almost no linear association with the measured process variables.
- The process variables are also mostly uncorrelated with each other, which reduces confounding but also suggests the dataset lacks a strong latent process trend.
- The target time series is noisy with a fairly stable rolling average and near-zero autocorrelation at short and daily lags.

### Outlier Review (IQR Rule)

| feature | lower_bound | upper_bound | outlier_count | outlier_pct |
| --- | --- | --- | --- | --- |
| temperature_c | 187.15 | 213.15 | 11 | 0.0073 |
| pressure_bar | 42.21 | 57.89 | 18 | 0.012 |
| vibration_mm_s | -2.6332 | 5.8667 | 76 | 0.0507 |
| speed_rpm | 2462.0 | 3534.0 | 15 | 0.01 |
| defect_rate | 0.4143 | 1.3514 | 58 | 0.0387 |

Interpretation:

- Outliers are modest for most variables, but `vibration_mm_s` has a noticeable upper tail.
- Low-end `defect_rate` values are flagged as outliers because the target is highly concentrated near `1.0`; these are influential rare events, not obvious data-entry errors.

### Group Comparisons

Operator-level summary:

| operator | mean | median | std | min | max | pct_exactly_1 |
| --- | --- | --- | --- | --- | --- | --- |
| Shift_A | 0.8605 | 0.9698 | 0.1946 | 0.0112 | 1.0 | 0.4659 |
| Shift_B | 0.8528 | 0.9726 | 0.1991 | 0.0866 | 1.0 | 0.4635 |
| Shift_C | 0.8749 | 0.9987 | 0.1816 | 0.1061 | 1.0 | 0.4979 |

- Kruskal-Wallis test across operators: statistic = **2.5848**, p-value = **0.2746**
- Conclusion: no statistically significant operator effect at the 5% level.

Hour-of-day mean `defect_rate`:

| hour | mean_defect_rate |
| --- | --- |
| 0 | 0.8757 |
| 1 | 0.8373 |
| 2 | 0.8589 |
| 3 | 0.8471 |
| 4 | 0.8474 |
| 5 | 0.8633 |
| 6 | 0.864 |
| 7 | 0.8688 |
| 8 | 0.8747 |
| 9 | 0.8567 |
| 10 | 0.8791 |
| 11 | 0.8495 |
| 12 | 0.8639 |
| 13 | 0.8848 |
| 14 | 0.8448 |
| 15 | 0.8615 |
| 16 | 0.878 |
| 17 | 0.8492 |
| 18 | 0.8468 |
| 19 | 0.8826 |
| 20 | 0.8675 |
| 21 | 0.8603 |
| 22 | 0.8408 |
| 23 | 0.8983 |

Day-of-week mean `defect_rate`:

| dayofweek | mean_defect_rate |
| --- | --- |
| 0 | 0.8561 |
| 1 | 0.8768 |
| 2 | 0.8936 |
| 3 | 0.8693 |
| 4 | 0.8547 |
| 5 | 0.8497 |
| 6 | 0.8418 |

These temporal differences are small in magnitude and visually unstable rather than strongly systematic.

### Autocorrelation

| lag | autocorrelation |
| --- | --- |
| 1 | -0.0178 |
| 2 | 0.0144 |
| 6 | -0.0224 |
| 12 | 0.0243 |
| 24 | 0.0109 |
| 48 | -0.0009 |

## 3. Modeling Strategy

Because `defect_rate` is continuous but bounded in `[0, 1]` with a large point mass at `1.0`, I evaluated two modeling views:

1. **Regression** on the raw `defect_rate`
2. **Auxiliary classification** on whether a record achieved the upper bound (`defect_rate == 1.0`)

Time order was preserved using **5-fold `TimeSeriesSplit`** to avoid leakage from future observations into past folds.

### Regression Results

| model | mae_mean | mae_std | rmse_mean | r2_mean |
| --- | --- | --- | --- | --- |
| dummy_mean | 0.1534 | 0.004 | 0.1894 | -0.0153 |
| ridge | 0.1538 | 0.0089 | 0.1928 | -0.05 |
| linear | 0.1538 | 0.0089 | 0.1929 | -0.0503 |
| random_forest | 0.1549 | 0.0095 | 0.1948 | -0.0703 |

Holdout performance on the last 20% of the series:

| model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| ridge | 0.1582 | 0.2036 | -0.0463 |
| random_forest | 0.1593 | 0.2052 | -0.0629 |

Interpretation:

- The **dummy mean regressor** is already hard to beat.
- Linear and ridge models are essentially indistinguishable from the baseline.
- Random forest does not uncover useful nonlinear structure; average CV `R^2` is still negative.
- Negative `R^2` on time-aware validation means the models perform worse than predicting the fold mean.

### Classification Results (`defect_rate == 1.0`)

| model | accuracy_mean | roc_auc_mean | f1_mean |
| --- | --- | --- | --- |
| logistic | 0.5128 | 0.507 | 0.4565 |
| random_forest | 0.5056 | 0.5042 | 0.4655 |
| dummy_majority | 0.5136 | 0.5 | 0.0 |

Interpretation:

- The majority-class baseline reaches about **51.4% accuracy**, reflecting class balance.
- Logistic regression and random forest produce mean ROC AUC values around **0.50**, which is effectively chance performance.
- The predictors do not meaningfully separate perfect-score records from non-perfect ones.

### Feature Importance and Coefficients

Top ridge coefficients by magnitude:

| feature | coefficient | abs_coefficient |
| --- | --- | --- |
| num__temperature_c | 0.0193 | 0.0193 |
| num__dayofweek | -0.0097 | 0.0097 |
| cat__operator_Shift_C | 0.009 | 0.009 |
| num__pressure_bar | -0.0072 | 0.0072 |
| num__speed_rpm | 0.005 | 0.005 |
| num__vibration_mm_s | -0.0037 | 0.0037 |
| num__hour | -0.001 | 0.001 |
| cat__operator_Shift_B | -0.0 | 0.0 |

Random-forest permutation importance on holdout data:

| feature | importance_mean | importance_std |
| --- | --- | --- |
| pressure_bar | 0.0022 | 0.0013 |
| dayofweek | 0.001 | 0.0008 |
| vibration_mm_s | 0.0007 | 0.001 |
| operator | 0.0003 | 0.0003 |
| hour | 0.0002 | 0.0006 |
| speed_rpm | -0.0007 | 0.001 |
| temperature_c | -0.0023 | 0.0018 |

These effects are small and unstable. In weak-signal settings, rankings should not be over-interpreted.

## 4. Assumption Checks and Diagnostics

I fit an interpretable OLS model to inspect assumptions, with predictors:
`temperature_c`, `pressure_bar`, `vibration_mm_s`, `speed_rpm`, `hour`, `dayofweek`, and operator dummies.

### OLS Diagnostics

| metric | value |
|---|---:|
| R-squared | 0.0102 |
| Adjusted R-squared | 0.0049 |
| Model F-test p-value | 0.0527 |
| Durbin-Watson | 2.0428 |
| Jarque-Bera statistic | 683.9554 |
| Jarque-Bera p-value | 3.0267e-149 |
| Breusch-Pagan statistic | 14.8958 |
| Breusch-Pagan p-value | 0.0612 |

VIF values:

| feature | vif |
| --- | --- |
| operator_Shift_C | 1.3395 |
| operator_Shift_B | 1.3364 |
| hour | 1.005 |
| pressure_bar | 1.0033 |
| vibration_mm_s | 1.0029 |
| speed_rpm | 1.0029 |
| dayofweek | 1.0023 |
| temperature_c | 1.0021 |

Diagnostic interpretation:

- **Autocorrelation**: Durbin-Watson near 2 indicates no serious serial correlation in residuals.
- **Normality**: Jarque-Bera strongly rejects normal residuals. This is expected given the bounded, upper-inflated target.
- **Homoskedasticity**: Breusch-Pagan is borderline but not strongly significant at 5%.
- **Multicollinearity**: VIF values are low, so instability is not caused by collinearity.
- **Overall fit**: the main failure is simply lack of explanatory power, not a hidden overfit relationship.

## 5. Final Conclusions

1. The dataset is **clean and regularly sampled**, with no missing data or timestamp issues.
2. `defect_rate` is **non-Gaussian and upper-inflated**, so standard Gaussian assumptions are a poor description of the target.
3. There are **no strong pairwise relationships** between `defect_rate` and the available process variables.
4. Operator, hour, and day-of-week effects are **small and not robust**.
5. Regression and classification models validated with time-aware splits perform **at or near baseline**, so the current feature set has little predictive value.

## 6. Recommendations

- Add lagged sensor features and rolling statistics if the process is believed to have delayed effects.
- Add contextual variables that often drive manufacturing quality: batch ID, raw material lot, maintenance events, tool age, alarm states, calibration status, and machine identifier.
- If `defect_rate` is conceptually a proportion with structural ones, consider a **two-part or zero/one-inflated beta-style model** once richer features are available.
- If the target is actually a capped quality score rather than a physical defect proportion, rename it accordingly before downstream use to avoid modeling assumptions that do not fit the measurement process.
