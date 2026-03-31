# Dataset Analysis Report

## Scope

This report inspects the dataset, performs exploratory analysis, evaluates data quality, builds and validates predictive models, and checks whether any model assumptions are defensible.

## 1. Data Loading and Inspection

- File: `dataset.csv`
- Shape: `500 rows x 10 columns` after feature engineering
- Original columns: `timestamp, sensor_id, temperature_c, humidity_pct, pressure_hpa, voltage_mv`
- Time span: `2024-01-01 00:00:00` to `2024-01-21 19:00:00`
- Dominant time step: `0 days 01:00:00` observed `499` times
- Duplicate rows: `0`
- Duplicate timestamps: `0`

### Dtypes

```text
timestamp        datetime64[us]
sensor_id                   str
temperature_c           float64
humidity_pct            float64
pressure_hpa            float64
voltage_mv              float64
hour                      int32
date                     object
hour_sin                float64
hour_cos                float64
```

### Missing Values

```text
timestamp        0
sensor_id        0
temperature_c    0
humidity_pct     0
pressure_hpa     0
voltage_mv       0
hour             0
date             0
hour_sin         0
hour_cos         0
```

### Basic Numeric Statistics

```text
       temperature_c  humidity_pct  pressure_hpa  voltage_mv
count        500.000       500.000       500.000     500.000
mean          29.856        50.113      1013.728      62.713
std           29.869        15.106         9.954      59.738
min          -19.490         9.500       984.000     -35.980
25%            4.132        40.200      1006.975      11.265
50%           31.315        49.500      1013.800      65.630
75%           55.615        59.925      1020.100     114.230
max           79.300        96.200      1038.800     161.600
```

### Sensor Counts

```text
sensor_id
S-001    122
S-002    122
S-003    117
S-004    139
```

## 2. Exploratory Data Analysis

Generated plots:

- `plots/missing_values.png`
- `plots/numeric_distributions.png`
- `plots/correlation_heatmap.png`
- `plots/temperature_voltage_scatter.png`
- `plots/time_series_overview.png`
- `plots/sensor_boxplots.png`
- `plots/model_residuals.png`

### Correlations

```text
               temperature_c  humidity_pct  pressure_hpa  voltage_mv
temperature_c       1.000000      0.068207      0.098292    1.000000
humidity_pct        0.068207      1.000000      0.034705    0.068207
pressure_hpa        0.098292      0.034705      1.000000    0.098292
voltage_mv          1.000000      0.068207      0.098292    1.000000
```

### Sensor-Level Summary

```text
          temperature_c         humidity_pct         pressure_hpa         voltage_mv        
                   mean     std         mean     std         mean     std       mean     std
sensor_id                                                                                   
S-001            36.480  27.876       52.119  14.249     1013.431   9.229     75.960  55.751
S-002            31.400  29.023       51.152  15.500     1014.398  10.375     65.799  58.047
S-003            22.522  31.653       49.517  13.785     1013.115  10.828     48.043  63.305
S-004            28.862  29.604       47.942  16.343     1013.916   9.476     60.724  59.208
```

### Temporal Dependence

Lag-1 autocorrelation values:

```text
temperature_c    0.038848
humidity_pct     0.007552
pressure_hpa    -0.031550
voltage_mv       0.038848
```

Interpretation: all lag-1 autocorrelations are close to zero, so there is little evidence of strong short-run persistence.

## 3. Patterns, Relationships, and Anomalies

- `voltage_mv` is an exact deterministic linear transformation of `temperature_c`: `voltage_mv = 2 * temperature_c + 3` within floating-point tolerance.
- Maximum absolute deviation from that formula: `1.776e-15`.
- The correlation between `temperature_c` and `voltage_mv` is `1.000000`, effectively perfect.
- `humidity_pct` and `pressure_hpa` show only weak linear associations with both temperature and voltage.
- Sensor-level mean differences exist, but the temperature-to-voltage mapping is unchanged across all four sensors.
- A small number of univariate IQR outliers appear in humidity and pressure, but none break the temperature-voltage rule.

### IQR Outlier Counts

```text
temperature_c    0
humidity_pct     3
pressure_hpa     3
voltage_mv       0
```

### Outlier Rows

```text
          timestamp sensor_id outlier_variable  temperature_c  humidity_pct  pressure_hpa  voltage_mv
2024-01-04 20:00:00     S-001     humidity_pct          56.08          96.2         997.2      115.16
2024-01-11 20:00:00     S-004     humidity_pct          41.50           9.5        1002.0       86.00
2024-01-12 18:00:00     S-004     humidity_pct          17.56          10.2        1018.9       38.12
2024-01-08 07:00:00     S-004     pressure_hpa          -2.56          81.1         984.5       -2.12
2024-01-09 23:00:00     S-001     pressure_hpa           3.72          36.2         984.0       10.44
2024-01-20 13:00:00     S-004     pressure_hpa          76.32          41.4         987.1      155.64
```

### Per-Sensor Formula Check

```text
sensor_id  slope  intercept  max_abs_residual
    S-001    2.0        3.0               0.0
    S-002    2.0        3.0               0.0
    S-003    2.0        3.0               0.0
    S-004    2.0        3.0               0.0
```

## 4. Modeling

A chronological 80/20 split was used: the first 400 observations for training and the last 100 for testing. This is more appropriate than a random split for ordered timestamped data, even though the series shows weak autocorrelation.

Models compared:

- `baseline_mean`: predicts the training-set mean voltage.
- `non_temperature_features`: linear regression on humidity, pressure, hour-of-day sine/cosine encoding, and sensor dummies.
- `temperature_only`: linear regression on temperature alone.
- `full_feature_set`: the previous model plus all available covariates.

### Validation Metrics

```text
                   model split      rmse       mae        r2
           baseline_mean train 58.677834 51.244367  0.000000
           baseline_mean  test 63.551527 55.098490 -0.004752
non_temperature_features train 57.706968 50.072092  0.032818
non_temperature_features  test 62.204683 53.796714  0.037384
        temperature_only train  0.000000  0.000000  1.000000
        temperature_only  test  0.000000  0.000000  1.000000
        full_feature_set train  0.000000  0.000000  1.000000
        full_feature_set  test  0.000000  0.000000  1.000000
```

### Fitted Temperature Model

- Estimated slope: `2.000000000000`
- Estimated intercept: `3.000000000000`
- Test-set residual max absolute value: `2.842e-14`

### Full Model Coefficients

```text
temperature_c      2.0
humidity_pct      -0.0
pressure_hpa      -0.0
hour_sin          -0.0
hour_cos           0.0
sensor_id_S-002   -0.0
sensor_id_S-003   -0.0
sensor_id_S-004    0.0
```

Interpretation: once temperature is included, every other coefficient collapses to numerical noise around zero. The additional features do not improve predictive performance because voltage is already fully determined by temperature.

## 5. Assumption Checks and Result Validation

- Linearity: satisfied exactly for the temperature-voltage relationship.
- Generalization: confirmed on the held-out chronological test set with `R^2 = 1.0` and residuals near machine precision.
- Residual diagnostics: classical checks such as normality or heteroskedasticity are not meaningful here because residual variance is effectively zero.
- Multicollinearity concern: the main issue is not unstable estimation but target derivation. `voltage_mv` appears engineered directly from `temperature_c` rather than independently generated with noise.
- Leakage risk: if the real analytical goal were to predict an independently measured voltage, using temperature would be valid only if voltage is genuinely caused by temperature. If not, the dataset likely contains a derived variable and the prediction task is trivialized.

## 6. Conclusions

- The dataset is clean in the narrow operational sense: no missing values, no duplicate rows, regular hourly cadence, and stable schema.
- The core finding dominates everything else: `voltage_mv` is deterministically encoded from `temperature_c` using `2 * temperature_c + 3`.
- Humidity, pressure, timestamp-derived features, and sensor identity provide negligible incremental information for predicting voltage.
- Because the target is effectively a formula of one predictor, this is not a realistic noisy forecasting problem. Any downstream scientific or operational conclusion should treat `voltage_mv` as a transformed version of temperature, not as an independent signal.

## 7. Reproducibility

- Analysis script: `analysis_pipeline.py`
- Report output: `analysis_report.md`
- Plot directory: `plots/`
