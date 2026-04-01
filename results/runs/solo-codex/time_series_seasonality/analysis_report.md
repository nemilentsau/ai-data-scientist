# Dataset Analysis Report

## Scope
This report analyzes `dataset.csv`, a daily web analytics dataset covering **2022-01-01** to **2024-12-30**. The workflow includes data quality checks, exploratory analysis, anomaly detection, time-series decomposition, predictive modeling, and model diagnostics.

## 1. Data Loading And Inspection

### Structure
- Raw shape: **1095 rows x 7 columns**
- Date range: **2022-01-01** to **2024-12-30**
- Frequency audit: **0** missing dates over an expected **1095**-day span
- Duplicate rows: **0**
- Duplicate dates: **0**

### Dtypes
```
date                            str
pageviews                     int64
unique_visitors               int64
bounce_rate                 float64
avg_session_duration_sec      int64
new_signups                   int64
support_tickets               int64
```

### Null Counts
```
date                        0
pageviews                   0
unique_visitors             0
bounce_rate                 0
avg_session_duration_sec    0
new_signups                 0
support_tickets             0
```

### Descriptive Statistics
```
                           count     mean      std      min      25%      50%       75%       max
pageviews                 1095.0  940.456  364.753  100.000  677.000  935.000  1212.000  1864.000
unique_visitors           1095.0  611.145  244.790   57.000  432.500  602.000   776.000  1247.000
bounce_rate               1095.0    0.448    0.078    0.172    0.394    0.448     0.502     0.695
avg_session_duration_sec  1095.0  180.140   39.610   64.000  154.000  179.000   208.000   291.000
new_signups               1095.0   14.837    3.902    5.000   12.000   15.000    17.000    27.000
support_tickets           1095.0    2.962    1.704    0.000    2.000    3.000     4.000    10.000
```

### Zeros And Negatives
```
                          zeros  negatives
pageviews                     0          0
unique_visitors               0          0
bounce_rate                   0          0
avg_session_duration_sec      0          0
new_signups                   0          0
support_tickets              63          0
```

### Outlier Screening
I used both the IQR rule and z-scores greater than 3 because a single heuristic can miss meaningful anomalies in skewed or bounded metrics.

```
                  column  iqr_outliers  lower_bound  upper_bound
               pageviews             0     -125.500     2014.500
         unique_visitors             0      -82.750     1291.250
             bounce_rate             5        0.232        0.664
avg_session_duration_sec             4       73.000      289.000
             new_signups            11        4.500       24.500
         support_tickets            10       -1.000        7.000
```

```
                  column  zscore_outliers_gt3
               pageviews                    0
         unique_visitors                    0
             bounce_rate                    3
avg_session_duration_sec                    0
             new_signups                    3
         support_tickets                    4
```

### Initial Data Quality Assessment
- The dataset is structurally clean: no nulls, duplicate rows, duplicate dates, or missing calendar days.
- `support_tickets` legitimately contains zeros; no numeric field contains negative values.
- The most notable isolated anomalies occur in bounded engagement and count metrics rather than in traffic volume.

## 2. Exploratory Data Analysis

### Saved Visualizations
- Overview time series: `./plots/timeseries_overview.png`
- Correlation heatmap: `./plots/correlation_heatmap.png`
- Weekly pattern boxplots: `./plots/weekly_patterns.png`
- STL decomposition for `pageviews`: `./plots/pageviews_stl_decomposition.png`
- Anomaly flags: `./plots/anomaly_flags.png`
- Holdout forecast comparison: `./plots/pageviews_holdout_forecast.png`
- Residual diagnostics: `./plots/pageviews_residual_diagnostics.png`

### Correlations
The strongest pairwise relationships are:
- pageviews vs unique_visitors: 0.972
- avg_session_duration_sec vs support_tickets: 0.044
- bounce_rate vs new_signups: -0.030
- unique_visitors vs avg_session_duration_sec: -0.026
- pageviews vs avg_session_duration_sec: -0.024
- new_signups vs support_tickets: 0.021

Full matrix:
```
                          pageviews  unique_visitors  bounce_rate  avg_session_duration_sec  new_signups  support_tickets
pageviews                     1.000            0.972        0.012                    -0.024        0.001            0.007
unique_visitors               0.972            1.000        0.012                    -0.026       -0.006           -0.001
bounce_rate                   0.012            0.012        1.000                     0.001       -0.030           -0.008
avg_session_duration_sec     -0.024           -0.026        0.001                     1.000       -0.020            0.044
new_signups                   0.001           -0.006       -0.030                    -0.020        1.000            0.021
support_tickets               0.007           -0.001       -0.008                     0.044        0.021            1.000
```

### Temporal Aggregates
Yearly means show strong growth in traffic volume but little movement in conversion or support burden:

```
      pageviews  unique_visitors  bounce_rate  avg_session_duration_sec  new_signups  support_tickets
year                                                                                                 
2022    647.099          419.534        0.445                   181.496       14.915            2.942
2023    934.488          607.764        0.453                   177.986       14.597            2.926
2024   1239.781          806.137        0.445                   180.937       15.000            3.016
```

Day-of-week means:
```
           pageviews  unique_visitors  new_signups  support_tickets
day_name                                                           
Monday      1124.280          730.726       14.331            2.873
Tuesday     1029.686          667.654       14.641            2.981
Wednesday    842.942          544.526       14.942            2.910
Thursday     747.654          489.788       14.615            3.019
Friday       792.609          511.776       15.013            2.942
Saturday     944.713          612.325       15.363            2.860
Sunday      1099.083          719.752       14.955            3.146
```

### Weekly Pattern Tests
I used the Kruskal-Wallis test rather than one-way ANOVA because these are operational metrics with possible non-normality and unequal variances.

```
         metric  kruskal_stat  p_value
      pageviews       147.101 3.17e-29
unique_visitors       141.658 4.48e-28
    new_signups         6.356   0.3845
support_tickets         3.430   0.7532
```

Interpretation:
- `pageviews` and `unique_visitors` vary significantly by day of week.
- `new_signups` and `support_tickets` do not show statistically significant day-of-week shifts.

### Stationarity Checks
I used the Augmented Dickey-Fuller test to distinguish trending traffic series from closer-to-stationary operational counts.

```
         metric  adf_stat  p_value
      pageviews    -1.380   0.5917
unique_visitors    -1.182   0.6811
    new_signups   -20.791 0.00e+00
support_tickets   -33.233 0.00e+00
```

### Decomposition Strength
STL with weekly period (`period=7`) indicates:

```
         metric  seasonal_strength  trend_strength
      pageviews              0.830           0.962
unique_visitors              0.679           0.915
    new_signups              0.198           0.067
```

Interpretation:
- `pageviews` has both strong trend and strong weekly seasonality.
- `unique_visitors` behaves similarly, though with slightly weaker seasonality.
- `new_signups` has weak trend and weak seasonality, which explains why feature-driven or calendar-driven models struggle to improve much over a baseline.

### Anomalies
The z-score based anomalies greater than 3 standard deviations are:
- `bounce_rate`: 2022-10-10, 2024-01-31, 2024-04-17
- `new_signups`: 2023-01-09, 2024-05-03, 2024-11-06
- `support_tickets`: 2022-10-13, 2023-11-05, 2024-03-13, 2024-09-26

Notable examples:
- `bounce_rate` spikes to **0.695** on **2024-01-31** and falls to **0.172** on **2022-10-10**.
- `new_signups` hits **27** on **2023-01-09**, **2024-05-03**, and **2024-11-06**.
- `support_tickets` spikes to **10** on **2023-11-05** and **9** on several isolated dates.

## 3. Key Patterns, Relationships, And Anomalies

- Traffic volume grew sharply across the three years: average `pageviews` rose from **647.1** in 2022 to **1239.8** in 2024, while `unique_visitors` rose from **419.5** to **806.1**.
- Growth in traffic did **not** translate into materially higher `new_signups`: yearly means remain near **15/day** throughout the period.
- `pageviews` and `unique_visitors` are almost redundant for explanatory modeling (`r = 0.972`), so combining both in a linear model introduces multicollinearity without adding much signal.
- Traffic is highly calendar-driven. Mondays and Sundays are the strongest days; Thursdays are among the weakest.
- `new_signups` appears largely independent of the observed web metrics. In lag scans from 0 to 14 days, the largest absolute linear correlation was under 0.08, which is weak in practical terms.
- `support_tickets` behaves like low-memory count noise: its sample autocorrelations through lag 14 stay close to zero.

## 4. Modeling

### Model A: `pageviews` Forecasting
Goal: forecast daily `pageviews` on a time-ordered holdout set.

Train/test split:
- Train: first **876** days
- Test: last **219** days

Candidate models:
- 7-day seasonal naive benchmark
- Calendar OLS with linear time trend, annual Fourier terms, and day-of-week dummies

Holdout performance:
```
               model    mae    rmse
7-day seasonal naive 89.183 110.034
        Calendar OLS 61.253  76.852
```

Rationale:
- The seasonal naive benchmark is a strong sanity check for daily series with pronounced weekly repetition.
- The selected OLS model is appropriate because the series shows deterministic structure: smooth growth, yearly seasonality, and strong weekday effects.
- More opaque or heavier time-series models are unnecessary when an interpretable regression already captures the pattern well and passes diagnostics.

Pageviews model coefficients (abridged intuition):
- Positive time trend: about **0.804** pageviews per day.
- Large weekday premiums for Monday, Tuesday, Saturday, and Sunday relative to Friday.
- Strong first annual sine term, consistent with broad within-year cycles.

### Model B: `new_signups` Count Modeling
Goal: test whether signups are predictably driven by observed time/calendar structure.

Compared models:
- Intercept-only baseline
- Poisson GLM with time trend, annual Fourier terms, and day-of-week dummies

Holdout results:
```
               model   mae  rmse
       Mean baseline 2.834 3.621
Calendar Poisson GLM 2.837 3.630
```

Interpretation:
- The Poisson GLM does **not** beat the mean baseline in a meaningful way.
- Calendar terms are not statistically significant.
- This is evidence that `new_signups` is mostly stable day-to-day noise around a constant mean, at least relative to the variables available here.

### Exploratory Explanatory Model For Signups
I also fit a Poisson model using the observed web metrics plus day-of-week dummies. Result:
- Overdispersion ratio (Pearson chi-square / df): **1.070**
- Statistically significant predictors at 0.05 level: **const**

This means the observed traffic, bounce, session duration, and support metrics do not provide a convincing explanation for signup variation in this dataset.

## 5. Assumption Checks And Validation

### Pageviews Calendar OLS Diagnostics
- Residual autocorrelation (Ljung-Box):
```
    lb_stat  lb_pvalue
7    7.2206     0.4063
14  12.5021     0.5660
```
- Heteroskedasticity (Breusch-Pagan p-value): **0.7902**
- Residual normality (Shapiro-Wilk p-value on random sample of 500 residuals): **0.9187**
- Training R-squared: **0.958**

Assessment:
- No evidence of problematic residual autocorrelation at lags 7 or 14 after modeling.
- No evidence of strong heteroskedasticity.
- Residuals are close enough to normal for standard inference in this context.
- The model is therefore usable both descriptively and predictively.

### Signups Poisson Diagnostics
- Pearson chi-square / residual df: **1.070**
- A ratio near 1 indicates Poisson variance is reasonable here.
- The issue is not violated count-model assumptions; the issue is lack of predictive signal.

Autocorrelation summaries:
```
 lag  new_signups_acf  support_tickets_acf
   0            1.000                1.000
   1           -0.058               -0.006
   2            0.008               -0.014
   3           -0.073               -0.026
   4            0.019               -0.009
   5           -0.040                0.007
   6            0.016                0.010
   7            0.005               -0.041
   8           -0.023                0.032
   9            0.053                0.041
  10            0.012               -0.002
  11           -0.007               -0.011
  12           -0.043               -0.008
  13           -0.015               -0.030
  14            0.023                0.017
```

## 6. Conclusions

- The dataset is clean and complete, so the main risks are analytical rather than data-quality related.
- Traffic is strongly structured by long-run growth and weekly seasonality. This is the dominant pattern in the dataset.
- `pageviews` can be modeled well with an interpretable calendar regression; it clearly outperforms a simple weekly seasonal-naive baseline on the holdout set.
- `unique_visitors` tracks `pageviews` very closely and adds limited incremental information.
- `new_signups` is surprisingly insensitive to both traffic and engagement metrics in this dataset. Higher traffic does not imply higher conversions here.
- `support_tickets` is stable, low-count, and mostly weakly dependent on the other variables.

## 7. Limitations

- No external drivers are available, such as marketing spend, campaign launches, product changes, pricing shifts, or incidents. Those omitted variables could plausibly explain signups.
- Only three years of data are available, which is adequate for weekly and yearly seasonality but thin for richer structural break analysis.
- Correlation and predictive failure do not prove causal independence; they show that the variables observed here are insufficient for a strong explanatory model.
