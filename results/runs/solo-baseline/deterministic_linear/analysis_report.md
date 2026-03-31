# IoT Sensor Dataset Analysis Report

## 1. Data Overview

| Property | Value |
|---|---|
| Rows | 500 |
| Columns | 6 |
| Time range | 2024-01-01 00:00 to 2024-01-21 19:00 (21 days) |
| Sensors | 4 (S-001, S-002, S-003, S-004) |
| Frequency | Hourly (exactly 1 reading per hour) |
| Missing values | None |
| Duplicate rows | None |

**Columns:** `timestamp`, `sensor_id`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `voltage_mv`

**Sensor distribution:** S-004 has the most readings (139), followed by S-001 and S-002 (122 each), and S-003 (117). Only one sensor reports per hour — sensors appear to be randomly assigned.

## 2. Key Finding: Voltage is Deterministic

The most striking discovery is that **voltage is a perfect linear function of temperature**:

```
voltage_mv = 2.0 * temperature_c + 3.0
```

- R-squared = 1.000000 (exact)
- Maximum residual = 0.0000

This means `voltage_mv` carries zero independent information. It is fully redundant with `temperature_c` and was excluded from all subsequent modeling. This relationship likely reflects a thermocouple or similar temperature-to-voltage transducer with known calibration constants.

*See: `plots/03_scatter_relationships.png`*

## 3. Distributional Analysis

### Temperature
- Range: -19.49 to 79.30 degC (abnormally wide for a single location)
- Distribution: **approximately uniform** (Kolmogorov-Smirnov test p = 0.24) — not rejected as uniform
- Clearly **not normal** (Shapiro-Wilk p < 0.000001)
- This uniform distribution is unusual for real environmental data, suggesting either synthetic data generation or a sensor testing/calibration scenario

### Humidity
- Range: 9.5% to 96.2%
- Mean: 50.1%, Std: 15.1%
- 3 IQR outliers: one very high reading (96.2%, S-001) and two very low readings (9.5% and 10.2%, both S-004)

### Pressure
- Range: 984.0 to 1038.8 hPa
- Mean: 1013.7 hPa, Std: 10.0 hPa
- 3 IQR outliers at the low end (984.0, 984.5, 987.1 hPa)

*See: `plots/02_distributions.png`, `plots/07_qq_plots.png`*

## 4. Temporal Patterns

### No diurnal cycle
There is **no significant hour-of-day pattern** in any variable. A one-way ANOVA of temperature by hour yields F = 0.63, p = 0.91. Real outdoor temperature data would show strong diurnal cycling — its absence reinforces that this data is either synthetic or from a controlled environment.

### No temporal trend
Linear regression of temperature against time: slope = 0.011 degC/hour, R-squared = 0.003, p = 0.25. No significant trend in humidity or pressure either.

### No autocorrelation
Lag-1 autocorrelation for each sensor's temperature series is near zero:

| Sensor | Lag-1 ACF |
|---|---|
| S-001 | 0.186 |
| S-002 | -0.028 |
| S-003 | 0.023 |
| S-004 | -0.094 |

Real environmental data is highly autocorrelated; consecutive readings should be similar. The near-zero ACF strongly suggests **independently drawn random samples**, not natural time-series data.

*See: `plots/05_hourly_patterns.png`, `plots/08_autocorrelation.png`, `plots/09_rolling_stats.png`*

## 5. Sensor Comparison

### Statistically significant sensor bias
A one-way ANOVA confirms significant temperature differences between sensors (F = 4.61, **p = 0.003**). The non-parametric Kruskal-Wallis test agrees (H = 13.41, p = 0.004).

**Mean temperature by sensor:**

| Sensor | Mean Temp (degC) | Std | n |
|---|---|---|---|
| S-001 | 36.5 | 27.9 | 122 |
| S-002 | 31.4 | 29.0 | 122 |
| S-003 | 22.5 | 31.7 | 117 |
| S-004 | 28.9 | 29.6 | 139 |

S-003 reads approximately **14 degC lower** on average than S-001 (t-test: t = 3.62, p = 0.0004). This is a meaningful calibration offset if these sensors are measuring the same environment.

Humidity and pressure do not differ significantly between sensors (humidity ANOVA p = 0.12).

*See: `plots/06_sensor_violin.png`, `plots/13_pairplot.png`*

## 6. Variable Relationships

Temperature, humidity, and pressure are **essentially independent**:

| | temperature_c | humidity_pct | pressure_hpa |
|---|---|---|---|
| temperature_c | 1.000 | 0.068 | 0.098 |
| humidity_pct | 0.068 | 1.000 | 0.035 |
| pressure_hpa | 0.098 | 0.035 | 1.000 |

All pairwise correlations are below 0.10. In real environmental data, these variables are typically correlated (e.g., temperature inversely related to humidity). The independence further supports that this is synthetic or laboratory-generated data.

*See: `plots/04_correlation_heatmap.png`*

## 7. Modeling

### 7.1 Sensor Classification (Random Forest)

**Goal:** Predict which sensor produced a reading from the sensor values and time features.

| Metric | Value |
|---|---|
| 5-fold CV Accuracy | 27.2% +/- 1.6% |
| Random baseline (4 classes) | 25% |

The model barely beats random chance. Sensors are nearly indistinguishable despite the slight temperature bias detected in S-003. Feature importances are evenly distributed (~20% each for temperature, humidity, pressure, hour, day), indicating no single feature discriminates well.

*See: `plots/11_classification_confusion.png`*

### 7.2 Humidity Regression

**Goal:** Predict humidity from temperature and pressure.

| Metric | Value |
|---|---|
| 5-fold CV R-squared | -0.024 +/- 0.031 |
| Train R-squared | 0.005 |
| MAE | 12.1% |

The negative cross-validated R-squared confirms that temperature and pressure have **no predictive power for humidity** in this dataset. The model performs worse than simply predicting the mean. Residuals are approximately normal (Shapiro-Wilk p = 0.42), but this is expected when the predictors are irrelevant and the response is roughly symmetric.

*See: `plots/12_regression_diagnostics.png`*

### 7.3 Anomaly Detection (Isolation Forest)

**Goal:** Identify unusual multivariate readings.

With contamination set at 5%, 25 observations were flagged. The most anomalous readings feature **extreme combinations** of variables:

**Top 5 anomalies:**

| Timestamp | Sensor | Temp (degC) | Humidity (%) | Pressure (hPa) | Score |
|---|---|---|---|---|---|
| 2024-01-08 07:00 | S-004 | -2.6 | 81.1 | 984.5 | -0.694 |
| 2024-01-04 20:00 | S-001 | 56.1 | 96.2 | 997.2 | -0.657 |
| 2024-01-15 11:00 | S-003 | -15.5 | 24.5 | 1038.8 | -0.631 |
| 2024-01-16 09:00 | S-002 | -13.1 | 89.5 | 1000.9 | -0.629 |
| 2024-01-09 23:00 | S-001 | 3.7 | 36.2 | 984.0 | -0.627 |

Anomalies are characterized by unusual joint behavior: extreme pressure combined with unusual humidity or temperature extremes. S-004 accounts for 10 of 25 anomalies (40%), disproportionate to its 28% share of readings.

*See: `plots/10_anomaly_detection.png`*

## 8. Model Assumptions Check

- **Linear regression residuals** are normally distributed (Shapiro-Wilk p = 0.42), homoscedastic, and centered at zero. However, the model is uninformative (R-squared near zero), so these diagnostics are moot.
- **Random Forest** was cross-validated with stratified folds to handle slight class imbalance.
- **Isolation Forest** contamination was set at 5% based on a reasonable prior for sensor anomaly rates. Results are robust to reasonable variation (3-7% contamination produces similar top anomalies).

## 9. Summary of Findings

1. **Redundant column:** `voltage_mv` is an exact linear transform of `temperature_c` (V = 2T + 3). It should be dropped or documented as derived.

2. **Data appears synthetic:** Multiple lines of evidence suggest this is not real environmental data:
   - Uniform (not normal/seasonal) temperature distribution
   - No diurnal cycle
   - No temporal autocorrelation
   - Independence between temperature, humidity, and pressure
   - One sensor per timestamp (random rotation)

3. **Sensor calibration issue:** S-003 reads significantly lower temperatures than S-001 (14 degC mean difference, p = 0.0004). If sensors are measuring the same environment, S-003 may need recalibration.

4. **No predictive structure:** Variables are independent, sensors are indistinguishable from readings alone, and there are no temporal patterns to exploit for forecasting.

5. **Anomalies detected:** 25 readings (5%) show unusual multivariate combinations, with S-004 overrepresented. These warrant inspection for sensor malfunction.

## 10. Recommendations

- **Drop or document `voltage_mv`** as a deterministic function of temperature.
- **Investigate S-003 calibration** — its consistent low-temperature bias is statistically significant.
- **Monitor S-004 more closely** — it produces a disproportionate share of anomalous readings.
- **If this is real data**, the lack of temporal structure suggests the sensors may be in a chaotic or controlled environment (e.g., test chamber) rather than outdoors.
- **If this is synthetic data**, the generation process should introduce realistic temporal correlations and variable dependencies to better simulate environmental monitoring.

## Plots Index

| File | Description |
|---|---|
| `plots/01_timeseries_overview.png` | All variables over time, colored by sensor |
| `plots/02_distributions.png` | Histograms and box plots of all numeric variables |
| `plots/03_scatter_relationships.png` | Temperature vs voltage (perfect linear), temperature vs humidity |
| `plots/04_correlation_heatmap.png` | Correlation matrix heatmap |
| `plots/05_hourly_patterns.png` | Mean +/- std of each variable by hour of day |
| `plots/06_sensor_violin.png` | Violin plots comparing sensor distributions |
| `plots/07_qq_plots.png` | Q-Q plots (normal and uniform) for temperature |
| `plots/08_autocorrelation.png` | Autocorrelation functions per sensor |
| `plots/09_rolling_stats.png` | 24-hour rolling mean and std for temperature and humidity |
| `plots/10_anomaly_detection.png` | Isolation Forest anomalies in pairwise scatter plots |
| `plots/11_classification_confusion.png` | Sensor classification confusion matrix |
| `plots/12_regression_diagnostics.png` | Humidity regression residual diagnostics |
| `plots/13_pairplot.png` | Full pairwise scatter/histogram matrix by sensor |
