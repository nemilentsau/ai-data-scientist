# Dataset Analysis Report

## Executive Summary

This dataset contains **500 rows** and **6 columns** of hourly sensor observations from **2024-01-01 00:00:00** through **2024-01-21 19:00:00**.

Key conclusions:

1. The dataset is structurally clean: no missing values, no duplicate rows, and a complete hourly timestamp sequence.
2. `voltage_mv` is not an independent signal. It is an exact deterministic transform of temperature: **`voltage_mv = 2 * temperature_c + 3`** up to floating-point precision.
3. Aside from that engineered relationship, the remaining variables show weak associations. Humidity and pressure have near-zero linear correlation with temperature.
4. Sensors differ modestly in temperature distribution. The strongest pairwise difference is between `S-001` and `S-003`.
5. A non-leaky temperature prediction model performs poorly out of sample, indicating little recoverable predictive structure in `sensor_id`, humidity, pressure, and calendar features alone.

## 1. Data Loading and Inspection

### Shape and schema

- Shape: **500 rows x 6 columns**
- Columns: timestamp, sensor_id, temperature_c, humidity_pct, pressure_hpa, voltage_mv

### Data types

```
timestamp        datetime64[us]
sensor_id                   str
temperature_c           float64
humidity_pct            float64
pressure_hpa            float64
voltage_mv              float64
```

### Missing values

```
               null_count
timestamp               0
sensor_id               0
temperature_c           0
humidity_pct            0
pressure_hpa            0
voltage_mv              0
```

### Duplication and temporal integrity

- Duplicate rows: **0**
- Duplicate timestamps: **0**
- Duplicate sensor-timestamp pairs: **0**
- Timestamp cadence: all consecutive differences are **1 hour**

Timestamp difference counts:

timestamp
0 days 01:00:00    499

### Basic summary statistics

```
               count      mean     std     min       25%       50%       75%     max
temperature_c  500.0    29.856  29.869  -19.49     4.132    31.315    55.615    79.3
humidity_pct   500.0    50.113  15.106    9.50    40.200    49.500    59.925    96.2
pressure_hpa   500.0  1013.728   9.954  984.00  1006.975  1013.800  1020.100  1038.8
voltage_mv     500.0    62.713  59.738  -35.98    11.265    65.630   114.230   161.6
```

## 2. Exploratory Data Analysis

### Visual outputs

- [plots/numeric_distributions.png](plots/numeric_distributions.png)
- [plots/correlation_heatmap.png](plots/correlation_heatmap.png)
- [plots/time_series.png](plots/time_series.png)
- [plots/sensor_boxplots.png](plots/sensor_boxplots.png)
- [plots/voltage_vs_temperature.png](plots/voltage_vs_temperature.png)
- [plots/temperature_model_diagnostics.png](plots/temperature_model_diagnostics.png)

### Distributional observations

- `temperature_c` spans **-19.49** to **79.30** with mean **29.86** and standard deviation **29.87**.
- `humidity_pct` is centered near **50.11%** and has a few IQR-rule outliers at both tails.
- `pressure_hpa` is tightly concentrated around **1013.73 hPa** with a few mild low-end outliers.
- `voltage_mv` mirrors temperature exactly because of the deterministic calibration relationship.

### Correlation structure

```
               temperature_c  humidity_pct  pressure_hpa  voltage_mv
temperature_c          1.000         0.068         0.098       1.000
humidity_pct           0.068         1.000         0.035       0.068
pressure_hpa           0.098         0.035         1.000       0.098
voltage_mv             1.000         0.068         0.098       1.000
```

Interpretation:

- `corr(temperature_c, voltage_mv) = 1.000` because voltage is an exact linear transform of temperature.
- `corr(temperature_c, humidity_pct) = 0.068` and `corr(temperature_c, pressure_hpa) = 0.098`, both too small to support a strong practical linear relationship.

### Sensor-level summary

```
          temperature_c                               humidity_pct                             pressure_hpa                                  voltage_mv                               
                  count    mean     std    min    max        count    mean     std   min   max        count      mean     std    min     max      count    mean     std    min     max
sensor_id                                                                                                                                                                             
S-001               122  36.480  27.876 -17.35  79.05          122  52.119  14.249  19.4  96.2          122  1013.431   9.229  984.0  1037.4        122  75.960  55.751 -31.70  161.10
S-002               122  31.400  29.023 -19.45  79.30          122  51.152  15.500  12.9  89.5          122  1014.398  10.375  991.5  1037.0        122  65.799  58.047 -35.90  161.60
S-003               117  22.522  31.653 -19.30  78.69          117  49.517  13.785  18.9  76.6          117  1013.115  10.828  987.5  1038.8        117  48.043  63.305 -35.60  160.38
S-004               139  28.862  29.604 -19.49  76.99          139  47.942  16.343   9.5  88.6          139  1013.916   9.476  984.5  1037.9        139  60.724  59.208 -35.98  156.98
```

### Outlier review

IQR-rule outlier counts:

- `temperature_c`: **0**
- `humidity_pct`: **3**
- `pressure_hpa`: **3**
- `voltage_mv`: **0**

Humidity outliers:

```
          timestamp sensor_id  temperature_c  humidity_pct  pressure_hpa  voltage_mv
2024-01-04 20:00:00     S-001          56.08          96.2         997.2      115.16
2024-01-11 20:00:00     S-004          41.50           9.5        1002.0       86.00
2024-01-12 18:00:00     S-004          17.56          10.2        1018.9       38.12
```

Pressure outliers:

```
          timestamp sensor_id  temperature_c  humidity_pct  pressure_hpa  voltage_mv
2024-01-08 07:00:00     S-004          -2.56          81.1         984.5       -2.12
2024-01-09 23:00:00     S-001           3.72          36.2         984.0       10.44
2024-01-20 13:00:00     S-004          76.32          41.4         987.1      155.64
```

These outliers are mild and plausible for environmental measurements. I did not remove them because there is no evidence they are data entry errors.

### Time structure

- The series is hourly and complete over 20 full days plus 20 hours on the last day.
- The autocorrelation function of temperature is weak at short lags, suggesting little temporal persistence.
- Hour-of-day means fluctuate, but without a stable daily cycle strong enough to support forecasting from calendar time alone.

Hourly means:

```
      temperature_c  humidity_pct  pressure_hpa
hour                                           
0             30.18         48.76       1015.10
1             41.06         51.20       1011.65
2             26.83         50.80       1013.39
3             25.60         52.63       1011.96
4             28.48         49.65       1015.13
5             30.35         49.73       1017.47
6             32.69         46.45       1013.27
7             30.96         52.73       1015.53
8             30.87         49.98       1015.89
9             33.24         52.62       1009.70
10            28.58         48.75       1013.45
11            26.07         48.40       1014.09
12            31.36         51.31       1010.64
13            26.18         49.31       1012.91
14            30.29         44.19       1017.85
15            37.03         53.15       1014.32
16            27.09         52.93       1013.40
17            29.71         54.96       1015.18
18            26.89         49.46       1015.51
19            44.35         47.09       1012.29
20            21.71         51.30       1010.56
21            26.41         48.29       1014.50
22            27.90         52.11       1014.29
23            21.69         46.84       1011.17
```

Day-of-week means:

```
           temperature_c  humidity_pct  pressure_hpa
dayofweek                                           
0                  26.29         49.64       1014.32
1                  27.19         51.77       1013.24
2                  33.23         50.94       1014.93
3                  34.31         49.14       1013.74
4                  32.64         50.20       1013.71
5                  27.58         48.70       1012.22
6                  27.63         50.41       1013.94
```

## 3. Key Patterns, Relationships, and Anomalies

### Deterministic engineering relationship

- Exact calibration check: **True**
- Maximum absolute deviation from `2 * temperature_c + 3`: **1.776e-15**

This is the dominant pattern in the data. Any model using both `temperature_c` and `voltage_mv` will exhibit perfect leakage unless one of the two is intentionally excluded.

### Sensor differences

Temperature differs across sensors more than humidity or pressure:

- ANOVA for temperature by sensor: **F = 4.610, p = 0.0034**
- Kruskal-Wallis for temperature by sensor: **H = 13.407, p = 0.0038**
- ANOVA for humidity by sensor: **p = 0.1226**
- ANOVA for pressure by sensor: **p = 0.7650**

The nonparametric result agrees with ANOVA for temperature, so the sensor effect is not an artifact of normality assumptions alone.

Pairwise Tukey HSD for temperature:

```
group1 group2  meandiff  p-adj    lower   upper  reject
 S-001  S-002   -5.0805 0.5361 -14.8334  4.6724   False
 S-001  S-003  -13.9585 0.0016 -23.8151 -4.1020    True
 S-001  S-004   -7.6181 0.1617 -17.0681  1.8320   False
 S-002  S-003   -8.8781 0.0945 -18.7346  0.9785   False
 S-002  S-004   -2.5376 0.9001 -11.9876  6.9124   False
 S-003  S-004    6.3405 0.3194  -3.2165 15.8974   False
```

The only clearly significant pairwise difference after family-wise correction is `S-001` versus `S-003`.

## 4. Modeling

### Model A: Calibration model for voltage

I fit an ordinary least squares model with `voltage_mv` as the response and `temperature_c` as the sole predictor because the scatterplot indicated a perfect line.

- Intercept: **3.000000**
- Temperature coefficient: **2.000000**
- R-squared: **1.000000**

Interpretation:

This is not a predictive discovery so much as a recovered measurement equation. The fitted model reproduces **`voltage_mv = 3 + 2 * temperature_c`** exactly within floating-point tolerance.

### Model B: Non-leaky temperature prediction

To test whether the remaining features contain useful predictive information, I modeled `temperature_c` using:

- `sensor_id`
- `humidity_pct`
- `pressure_hpa`
- `hour`
- `dayofweek`

I intentionally excluded `voltage_mv` because it is a deterministic duplicate of the target.

#### Cross-validated performance

```
                   r2_mean  r2_std  mae_mean  mae_std  rmse_mean  rmse_std
Linear regression   -0.006   0.040    25.775    0.796     29.803     0.844
Random forest       -0.076   0.041    26.336    1.109     30.816     0.754
```

Interpretation:

- Linear regression has mean cross-validated **R-squared = -0.006**
- Random forest has mean cross-validated **R-squared = -0.076**

Both are near zero or negative, meaning they do not generalize better than predicting the mean. This supports the conclusion that the dataset contains little predictive structure beyond the voltage-temperature equation.

### In-sample explanatory temperature model

For interpretability and diagnostics, I also fit an OLS model to `temperature_c` with one-hot encoded sensor indicators plus humidity, pressure, hour, and day-of-week.

- In-sample R-squared: **0.040**
- Adjusted R-squared: **0.027**

Selected coefficients:

```
                 coefficient
const              -253.2402
humidity_pct          0.1062
pressure_hpa          0.2815
hour                 -0.1350
dayofweek             0.1686
sensor_id_S-002      -5.3463
sensor_id_S-003     -13.5015
sensor_id_S-004      -7.4400
```

This model suggests lower mean temperatures for `S-003` and `S-004` relative to `S-001`, but the total explained variance remains small.

## 5. Assumption Checks and Validation

### Calibration model assumptions

The calibration model has effectively zero residual variance because the relationship is exact. That means:

- The estimated line is valid as a recovered formula.
- Classical residual diagnostics are not very informative because the residual distribution degenerates to numerical noise.

### Temperature group comparison assumptions

For ANOVA on temperature by sensor:

- Levene test for equal variances: **stat = 1.282, p = 0.2798**
- Shapiro-Wilk p-values by sensor:

```
            W  p_value
S-001  0.9506   0.0002
S-002  0.9524   0.0003
S-003  0.9123   0.0000
S-004  0.9452   0.0000
```

Interpretation:

- Homogeneity of variance is acceptable.
- Normality is rejected within each sensor group, which is not surprising given broad, somewhat flattened distributions.
- Because normality is questionable, I used Kruskal-Wallis as a robustness check; it confirmed the same qualitative conclusion.

### Temperature model residual checks

- Breusch-Pagan test for heteroskedasticity: **LM p = 0.2957, F p = 0.2974**
- Ljung-Box test on residual autocorrelation:

```
    lb_stat  lb_pvalue
10   8.1504     0.6141
24  17.1989     0.8401
```

Interpretation:

- No strong evidence of heteroskedasticity.
- No strong evidence of residual autocorrelation at lags 10 or 24.
- Residual normality is poor, as seen in the Q-Q plot and the OLS omnibus tests. This limits strict parametric inference, but does not change the larger practical finding that explained variance is very small.

## 6. Final Conclusions

1. The dataset is clean and temporally consistent.
2. `voltage_mv` is fully redundant with `temperature_c` and should be treated as a calibrated proxy, not a separate feature.
3. Humidity and pressure contribute little explanatory power for temperature in this sample.
4. Sensor identity carries a modest temperature offset, especially between `S-001` and `S-003`, but the effect is not large enough to make temperature strongly predictable.
5. After removing the leakage path through voltage, predictive models fail to generalize well. This dataset is more suitable for calibration validation and sensor comparison than for forecasting.

## 7. Recommendations

1. Drop one of `temperature_c` or `voltage_mv` in downstream predictive modeling to avoid perfect multicollinearity and leakage.
2. If the scientific goal is sensor calibration, formalize the deterministic equation and document it as part of the data dictionary.
3. If the goal is temperature prediction, collect more informative predictors such as location, external weather conditions, device state, or a longer time series with known seasonal structure.
4. If the goal is anomaly detection, keep the mild humidity and pressure outliers but define engineering thresholds rather than relying only on boxplot rules.
