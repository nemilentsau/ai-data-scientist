# Dataset Analysis Report

## Executive Summary

This dataset contains **730 daily observations** from **2023-01-01 to 2024-12-30** with no missing values and a complete daily cadence. The dominant structure is strong annual seasonality: temperature, UV index, ice cream sales, pool visits, and drowning incidents all rise together in warmer months, while humidity is comparatively weakly related to the other variables.

The two strongest business-style targets are:

- **Ice cream sales**: a weather-driven continuous outcome that is modeled well with linear regression.
- **Pool visits**: also well explained by weather with linear regression.

For **drowning incidents**, the response is a low-count, zero-heavy series, so a **Poisson generalized linear model** is more appropriate than OLS. The Poisson dispersion estimate is close to 1, which supports the Poisson assumption and does not justify a more complex negative binomial model for this dataset.

One important caution: the weather and behavior variables are **extremely collinear** because they all share the same seasonal pattern. This makes them useful predictors but weakens coefficient-level causal interpretation in multivariable models that include multiple seasonal proxies simultaneously.

## 1. Data Loading and Inspection

- Shape: **730 rows x 7 original columns**
- Date coverage: **2023-01-01 to 2024-12-30**
- Duplicate dates: **0**
- Irregular date steps: **0**

### Dtypes

```text
date                     datetime64[us]
avg_temperature_c               float64
ice_cream_sales_units             int64
pool_visits                       int64
drowning_incidents                int64
uv_index                        float64
humidity_pct                      int64
```

### Null Counts

```text
date                     0
avg_temperature_c        0
ice_cream_sales_units    0
pool_visits              0
drowning_incidents       0
uv_index                 0
humidity_pct             0
```

### Basic Statistics

```text
                       count     mean      std   min    25%     50%      75%     max
avg_temperature_c      730.0    9.958   11.025 -11.0   0.00    9.95    20.00    33.3
ice_cream_sales_units  730.0  559.400  493.093   0.0  23.25  510.00  1008.75  1866.0
pool_visits            730.0  335.295  295.119   0.0   0.00  287.00   607.25  1044.0
drowning_incidents     730.0    0.577    0.892   0.0   0.00    0.00     1.00     5.0
uv_index               730.0    1.673    1.520   0.0   0.00    1.50     3.00     5.3
humidity_pct           730.0   54.982   14.777  11.0  45.00   54.00    65.75    95.0
```

### Shape Diagnostics

```text
                        skew  excess_kurtosis  zero_count
avg_temperature_c      0.010           -1.321           3
ice_cream_sales_units  0.299           -1.315         174
pool_visits            0.304           -1.291         185
drowning_incidents     1.734            2.957         454
uv_index               0.351           -1.253         199
humidity_pct          -0.010           -0.178           0
```

Observations:

- No missing values or duplicate dates were found.
- The dataset is unusually clean for operational data.
- `drowning_incidents` is strongly right-skewed and contains many zeros.
- `ice_cream_sales_units` and `pool_visits` have many zero days, concentrated in cold months.

## 2. Exploratory Data Analysis

Generated plots:

- `plots/time_series_overview.png`
- `plots/distributions.png`
- `plots/correlation_heatmap.png`
- `plots/temperature_relationships.png`
- `plots/monthly_seasonality.png`
- `plots/sales_model_diagnostics.png`
- `plots/drowning_poisson_diagnostics.png`

### Correlation Matrix

```text
                       avg_temperature_c  ice_cream_sales_units  pool_visits  drowning_incidents  uv_index  humidity_pct
avg_temperature_c                  1.000                  0.973        0.963               0.481     0.947         0.036
ice_cream_sales_units              0.973                  1.000        0.961               0.486     0.946         0.028
pool_visits                        0.963                  0.961        1.000               0.468     0.931         0.024
drowning_incidents                 0.481                  0.486        0.468               1.000     0.482         0.054
uv_index                           0.947                  0.946        0.931               0.482     1.000         0.057
humidity_pct                       0.036                  0.028        0.024               0.054     0.057         1.000
```

### Average by Month

```text
       avg_temperature_c  ice_cream_sales_units  pool_visits  drowning_incidents  uv_index  humidity_pct
month                                                                                                   
1                  -3.30                  25.53        19.60                0.18      0.06         55.19
2                   1.81                 144.54        88.82                0.18      0.36         54.37
3                   8.54                 436.68       262.61                0.45      1.30         54.02
4                  16.28                 814.05       477.72                0.92      2.50         54.70
5                  22.05                1120.05       662.34                1.10      3.39         55.34
6                  24.69                1259.57       749.12                1.18      3.66         56.38
7                  23.48                1171.90       712.45                1.19      3.65         56.35
8                  18.25                 924.02       546.05                0.84      2.75         55.37
9                  11.03                 529.70       337.48                0.43      1.58         55.78
10                  3.31                 212.02       121.66                0.24      0.56         52.89
11                 -2.10                  38.57        24.40                0.05      0.14         55.52
12                 -5.11                   6.85         4.05                0.13      0.02         53.89
```

### IQR-Based Outlier Summary

```text
                       lower_bound  upper_bound  iqr_outlier_count
column                                                            
avg_temperature_c          -30.000       50.000                  0
ice_cream_sales_units    -1455.000     2487.000                  0
pool_visits               -910.875     1518.125                  0
drowning_incidents          -1.500        2.500                 33
uv_index                    -4.500        7.500                  0
humidity_pct                13.875       96.875                  2
```

Key EDA takeaways:

- `avg_temperature_c`, `uv_index`, `ice_cream_sales_units`, and `pool_visits` move together very tightly.
- `ice_cream_sales_units` and `avg_temperature_c` have an especially strong correlation (**0.973**).
- `pool_visits` is likewise strongly associated with temperature (**0.963**).
- `drowning_incidents` has a moderate positive relationship with warm-weather activity variables, but much weaker than the sales and pool signals.
- `humidity_pct` is almost orthogonal to the main seasonal variables.

## 3. Patterns, Relationships, and Anomalies

### Seasonality

The monthly profiles show a clear annual cycle:

- Winter months have near-zero pool use and very low ice cream demand.
- Late spring through summer has the highest temperature, UV, sales, visits, and incidents.
- Drowning incidents peak in **June and July** on average, aligning with the highest exposure/activity months.

### Multicollinearity

Variance inflation factors for a full seasonal-feature set:

```text
const                    17.51
avg_temperature_c        25.33
uv_index                 11.10
humidity_pct              1.01
pool_visits              16.22
ice_cream_sales_units    24.01
```

Interpretation:

- Temperature, UV, pool visits, and ice cream sales all have high VIF values.
- This means those variables contain overlapping seasonal information.
- A coefficient sign flip in a saturated model would not be surprising and should not be over-interpreted.

### Potentially Unusual Observations

Largest drowning-incident days:

```text
          date  drowning_incidents  avg_temperature_c  pool_visits  ice_cream_sales_units  uv_index  humidity_pct
193 2023-07-13                   5               20.1          576                    936       2.8            83
103 2023-04-14                   4               13.6          479                    604       2.9            58
115 2023-04-26                   4               19.6          586                   1030       3.3            60
135 2023-05-16                   4               27.0          728                   1310       5.0            74
470 2024-04-15                   4               15.7          372                    796       2.0            59
504 2024-05-19                   4               20.9          672                    966       3.4            26
568 2024-07-22                   4               17.1          529                    880       2.7            53
571 2024-07-25                   4               27.3          740                   1463       4.2            54
```

Most influential points for the full-sample ice cream sales model:

```text
          date  ice_cream_sales_units  avg_temperature_c  uv_index  humidity_pct  standard_resid  cooks_d
503 2024-05-18                   1480               24.4       2.8            89           3.446    0.044
708 2024-12-09                      0              -11.0       0.0            57           2.551    0.021
179 2023-06-29                   1866               33.0       4.7            53           2.821    0.015
561 2024-07-15                   1738               29.8       5.0            42           2.360    0.015
721 2024-12-22                      0              -10.1       0.0            50           2.237    0.014
210 2023-07-30                   1039               23.3       4.8            68          -1.918    0.014
426 2024-03-02                     58                2.5       1.7            44          -2.437    0.013
704 2024-12-05                      0               -9.3       0.0            29           1.901    0.013
```

Interpretation:

- The highest-incident days occur on warm, high-activity days rather than isolated cold-weather anomalies.
- The most influential sales observations are still plausible and generally lie on the same seasonal manifold.
- There is no strong evidence of gross data corruption, but a few days have unusually high positive sales residuals.

## 4. Modeling Strategy

I fit models on **2023 as training data** and evaluated them on **2024 as a forward holdout set**. That is stricter than random splitting because it respects time order.

### Model A: Ice Cream Sales

Model form:

`ice_cream_sales_units ~ avg_temperature_c + uv_index + humidity_pct`

Why this model:

- The target is continuous and high-volume.
- The weather relationship appears approximately linear in the scatterplots.
- A simple weather model is interpretable and performs very well.

Training coefficients:

```text
const                113.8311
avg_temperature_c     36.2546
uv_index              60.6783
humidity_pct          -0.2557
```

### Model B: Pool Visits

Model form:

`pool_visits ~ avg_temperature_c + uv_index + humidity_pct`

Training coefficients:

```text
const                84.1313
avg_temperature_c    22.2931
uv_index             28.4032
humidity_pct         -0.2967
```

### Model C: Drowning Incidents

Model form:

`drowning_incidents ~ avg_temperature_c + uv_index + humidity_pct`

Why Poisson:

- The target is a non-negative count.
- It is zero-heavy and right-skewed.
- The estimated train dispersion is **1.029**, which is close to 1.

Training coefficients:

```text
const               -1.7976
avg_temperature_c    0.0616
uv_index             0.1067
humidity_pct         0.0030
```

## 5. Assumption Checks and Validation

### Ice Cream Sales OLS

Validation:

```text
test_mae                      88.6690
test_rmse                    109.6856
test_r2                        0.9483
durbin_watson_train_resid      1.6490
breusch_pagan_p                0.0016
shapiro_p                      0.2483
```

Assumption notes:

- Residuals are close to normal by QQ plot and Shapiro test.
- Breusch-Pagan p-value indicates **some heteroskedasticity**.
- Durbin-Watson indicates **mild positive autocorrelation** in training residuals.
- Despite those imperfections, holdout performance is very strong.

### Pool Visits OLS

Validation:

```text
test_mae                     62.0651
test_rmse                    78.3764
test_r2                       0.9272
durbin_watson_train_resid     1.6395
breusch_pagan_p               0.0224
shapiro_p                     0.5512
```

Assumption notes:

- Residual normality looks acceptable.
- There is again mild heteroskedasticity and mild autocorrelation.
- The model generalizes well on the 2024 holdout set.

### Drowning Incidents Poisson GLM

Validation:

```text
test_mae                      0.5533
test_rmse                     0.7794
test_poisson_deviance       336.6450
null_poisson_deviance       451.3916
mean_predicted_rate           0.5911
mean_actual_rate              0.5425
observed_zero_rate            0.6356
predicted_zero_rate_mean      0.6064
train_dispersion              1.0290
```

Assumption notes:

- The Poisson dispersion statistic is close to 1, so overdispersion is not a major concern.
- The predicted zero rate (**0.606**) is reasonably close to the observed zero rate (**0.636**).
- Holdout Poisson deviance is materially lower than the null-model deviance, so the weather model adds predictive signal.
- On the training fit, temperature is the clearest signal; UV and humidity are weaker once temperature is already present.

## 6. Findings

1. **The dataset is dominated by shared seasonality.** Temperature, UV, ice cream sales, and pool visits all rise and fall together over the year.
2. **Ice cream sales are highly weather-sensitive.** A simple linear model using weather alone explains most of the variation and generalizes strongly to the next year.
3. **Pool visits show the same pattern.** Weather is also enough to explain a large majority of variation in visits.
4. **Drowning incidents increase in warmer, more active periods, but the signal is weaker and noisier.** A count model is required; OLS would be a poor choice.
5. **Humidity contributes little.** It has weak marginal correlation with the main outcomes and is not a stable driver in the fitted models.
6. **Multicollinearity limits causal interpretation.** Because many predictors are seasonal proxies, coefficient-level interpretations should be made cautiously.
7. **The data looks unusually smooth and structured.** The tight relationships and clean seasonality are more consistent with a simulated or heavily curated dataset than messy real-world observational data.

## 7. Recommendations

- For **prediction**, the simple weather-driven models are adequate and interpretable.
- For **causal claims**, avoid saying that ice cream sales or pool visits themselves cause drowning; they likely proxy for shared seasonal exposure.
- If this were a production problem, I would next test:
  - day-of-week effects
  - holiday indicators
  - lagged weather effects
  - spline or GAM terms for nonlinearity
  - robust or HAC standard errors for the OLS models

## Reproducibility

The report and plots were generated programmatically from `dataset.csv` by running `analyze_dataset.py`.
