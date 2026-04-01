# Dataset Analysis Report

## Executive Summary
The dataset contains **1,500 rows** and **8 columns** describing ad-driven web sessions with a binary conversion target. The data are structurally clean: there are no missing values, no duplicate rows, and no duplicated `session_id` values.
Conversion is moderately imbalanced at **29.3%** (439 positives / 1061 negatives). The strongest and most consistent signals are `channel_score` and `time_of_day_hour`; the other measured inputs contribute little once those are in the model.
A simple logistic regression and a random forest perform almost identically out of sample (ROC AUC around 0.69), which suggests the available features contain only modest predictive signal. Because the flexible model does not materially outperform the interpretable one, the logistic model is the better primary model here.

## 1. Data Loading and Inspection
- Shape: `(1500, 8)`
- Duplicate rows: `0`
- Duplicate `session_id`: `0`
- Null values: `0` total
- Conversion rate: `0.2927`

### Column Types
| Column | Dtype | Unique Values | Nulls |
|---|---:|---:|---:|
| session_id | int64 | 1500 | 0 |
| ad_budget_usd | float64 | 1500 | 0 |
| time_of_day_hour | float64 | 240 | 0 |
| channel_score | float64 | 763 | 0 |
| device | str | 3 | 0 |
| page_load_time_sec | float64 | 487 | 0 |
| previous_visits | int64 | 11 | 0 |
| converted | int64 | 2 | 0 |

### Numeric Summary
| Variable | Mean | Std | Min | 25% | 50% | 75% | Max | Skew |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ad_budget_usd | 2546.850 | 1440.674 | 122.700 | 1263.967 | 2582.150 | 3792.977 | 4998.620 | -0.007 |
| time_of_day_hour | 12.009 | 6.945 | 0.000 | 6.200 | 12.100 | 18.100 | 24.000 | -0.022 |
| channel_score | 0.489 | 0.285 | 0.000 | 0.242 | 0.487 | 0.729 | 1.000 | 0.029 |
| page_load_time_sec | 1.951 | 1.907 | 0.300 | 0.558 | 1.320 | 2.710 | 15.000 | 1.986 |
| previous_visits | 2.995 | 1.823 | 0.000 | 2.000 | 3.000 | 4.000 | 10.000 | 0.654 |
| converted | 0.293 | 0.455 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |  |

### Range and Sanity Checks
- `time_of_day_hour_outside_0_24`: 0
- `time_of_day_hour_equal_24`: 1
- `channel_score_outside_0_1`: 0
- `page_load_time_sec_nonpositive`: 0
- `converted_not_binary`: 0
- The only obvious edge case is one record with `time_of_day_hour = 24.0`. That is not outside the declared range, but it is an endpoint value that often duplicates hour 0 in clock-style data.

## 2. Exploratory Data Analysis
### Distributional Findings
- `ad_budget_usd`: skew=-0.007, normality test p-value=0.000e+00, IQR outliers=0
- `time_of_day_hour`: skew=-0.022, normality test p-value=9.874e-233, IQR outliers=0
- `channel_score`: skew=0.029, normality test p-value=1.182e-208, IQR outliers=0
- `page_load_time_sec`: skew=1.986, normality test p-value=7.123e-139, IQR outliers=63
- `previous_visits`: skew=0.654, normality test p-value=1.355e-22, IQR outliers=26
- `page_load_time_sec` is strongly right-skewed and contains the most IQR-defined outliers, so any analysis assuming Gaussian behavior would be inappropriate without transformation or robust methods.

### Relationship to Conversion
- Pearson correlation with `converted`: `time_of_day_hour` = 0.224
- Pearson correlation with `converted`: `channel_score` = 0.224
- Pearson correlation with `converted`: `previous_visits` = 0.028
- Pearson correlation with `converted`: `ad_budget_usd` = -0.012
- Pearson correlation with `converted`: `page_load_time_sec` = -0.014

### Device-Level Summary
| Device | Conversion Rate | Sessions | Conversions |
|---|---:|---:|---:|
| tablet | 0.304 | 158 | 48 |
| mobile | 0.303 | 833 | 252 |
| desktop | 0.273 | 509 | 139 |

### Interpreted EDA Patterns
- `channel_score` shows the clearest monotonic relationship: higher quintiles have substantially higher conversion rates.
- `time_of_day_hour` shows a broad upward trend across the day, though the hourly series is noisy and includes one endpoint case at hour 24.
- `ad_budget_usd`, `previous_visits`, and `device` show only weak marginal differences.
- `page_load_time_sec` is noisy: the raw distribution is highly skewed, but conversion does not change monotonically with load time in a stable way.

## 3. Modeling Strategy
Two models were evaluated with 5-fold stratified cross-validation after excluding `session_id` from features because it is an identifier, not a behavioral predictor.
- Logistic regression with standard scaling and one-hot encoding.
- Random forest classifier with the same feature set and categorical encoding.

### Cross-Validated Performance
| Model | ROC AUC Mean | ROC AUC SD | AP Mean | AP SD | Brier Mean | Brier SD | Accuracy Mean | F1 Mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| logistic | 0.692 | 0.026 | 0.504 | 0.049 | 0.186 | 0.006 | 0.737 | 0.345 |
| random_forest | 0.694 | 0.035 | 0.499 | 0.053 | 0.185 | 0.009 | 0.747 | 0.388 |

Interpretation: the random forest is not materially better than logistic regression. That weak performance gap argues against hidden strong nonlinear structure in the observed variables.

## 4. Logistic Model Interpretation
| Term | Coef | Odds Ratio | 95% CI Lower | 95% CI Upper | p-value |
|---|---:|---:|---:|---:|---:|
| const | -2.976 | 0.051 | 0.031 | 0.085 | 1.641e-30 |
| ad_budget_usd | -0.000 | 1.000 | 1.000 | 1.000 | 5.967e-01 |
| time_of_day_hour | 0.079 | 1.082 | 1.063 | 1.101 | 2.777e-18 |
| channel_score | 1.893 | 6.638 | 4.319 | 10.202 | 6.043e-18 |
| page_load_time_sec | -0.011 | 0.989 | 0.929 | 1.053 | 7.292e-01 |
| previous_visits | 0.046 | 1.047 | 0.981 | 1.117 | 1.651e-01 |
| device_mobile | 0.069 | 1.071 | 0.827 | 1.387 | 6.012e-01 |
| device_tablet | 0.060 | 1.062 | 0.701 | 1.609 | 7.771e-01 |

Key interpretation:
- `channel_score` is the dominant effect. A one-unit increase multiplies the odds of conversion by about 6.64, holding other variables fixed.
- `time_of_day_hour` is also significant. Each additional hour is associated with about 8.2% higher odds of conversion on average in the fitted linear-logit model.
- `ad_budget_usd`, `page_load_time_sec`, `previous_visits`, and device indicators are not statistically significant after adjustment.

## 5. Assumption Checks and Validation
### Multicollinearity
| Feature | VIF |
|---|---:|
| ad_budget_usd | 3.391 |
| channel_score | 3.257 |
| time_of_day_hour | 3.223 |
| previous_visits | 3.010 |
| device_mobile | 2.392 |
| page_load_time_sec | 1.942 |
| device_tablet | 1.273 |
- All VIF values are below 5, so multicollinearity is not a serious concern.

### Linearity of the Logit
A Box-Tidwell style check was run by adding `x * log(x)` terms for each continuous feature after shifting nonpositive values slightly above zero.
| Term | p-value |
|---|---:|
| ad_budget_usd_bt | 4.661e-01 |
| time_of_day_hour_bt | 3.115e-01 |
| channel_score_bt | 9.037e-01 |
| page_load_time_sec_bt | 7.867e-02 |
| previous_visits_bt | 3.620e-01 |
- None of the Box-Tidwell interaction terms were significant at 0.05, so there is no strong evidence that the simple linear-logit specification is badly misspecified for these features.

### Calibration and Influence
- Logistic regression cross-validated ROC AUC: `0.692`
- Logistic regression cross-validated average precision: `0.497`
- Logistic regression cross-validated Brier score: `0.186`
- Logistic regression cross-validated log loss: `0.556`
- Cook's distance threshold `4/n` flags `64` observations, but the maximum Cook's distance is only `0.0092`, so there is no sign of a single observation dominating the fit.

Most influential observations by Cook's distance:
| session_id | time_of_day_hour | channel_score | page_load_time_sec | converted |
|---:|---:|---:|---:|---:|
| 519 | 0.5 | 0.071 | 7.90 | 1 |
| 1388 | 9.8 | 0.049 | 7.45 | 1 |
| 1248 | 3.5 | 0.120 | 3.97 | 1 |
| 727 | 7.2 | 0.062 | 0.82 | 1 |
| 1408 | 5.4 | 0.143 | 7.06 | 1 |

## 6. Random Forest Feature Importance
| Feature | Permutation Importance Mean | Importance SD |
|---|---:|---:|
| channel_score | 0.2402 | 0.0112 |
| time_of_day_hour | 0.2008 | 0.0094 |
| ad_budget_usd | 0.0830 | 0.0024 |
| page_load_time_sec | 0.0800 | 0.0038 |
| device | 0.0638 | 0.0036 |
| previous_visits | 0.0576 | 0.0030 |
- The random forest importance ranking agrees with the logistic model: `channel_score` and `time_of_day_hour` dominate, while the remaining variables contribute little.

## 7. Conclusions
- The dataset is clean enough for modeling without imputation or major repair, but not perfectly well-behaved: `page_load_time_sec` is skewed and one hour value sits at the edge case `24.0`.
- The primary practical story is simple: stronger channel quality and later hours are associated with higher conversion probability in this sample.
- The predictive ceiling is modest with the available variables. With ROC AUC around 0.69, this is useful for ranking or directional analysis, not for high-confidence individual session decisions.
- Since the flexible model does not beat logistic regression by much, chasing more complex models is hard to justify until richer features are available.

## 8. Output Files
- `plots/01_target_balance.png`
- `plots/02_numeric_distributions.png`
- `plots/03_correlation_heatmap.png`
- `plots/04_conversion_rate_by_device.png`
- `plots/05_conversion_rate_by_hour.png`
- `plots/06_conversion_by_feature_bins.png`
- `plots/07_boxplots_by_conversion.png`
- `plots/08_page_load_outliers.png`
- `plots/09_model_diagnostics.png`
- `plots/10_rf_feature_importance.png`