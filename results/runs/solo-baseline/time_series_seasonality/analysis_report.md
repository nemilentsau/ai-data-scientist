# Web Analytics Dataset: Comprehensive Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| **Rows** | 1,095 |
| **Date range** | 2022-01-01 to 2024-12-30 (3 years, daily) |
| **Missing values** | 0 across all columns |
| **Date gaps** | None (consecutive daily observations) |

**Columns:**

| Column | Type | Mean | Std | Min | Max |
|---|---|---|---|---|---|
| pageviews | int | 940 | 365 | 100 | 1,864 |
| unique_visitors | int | 611 | 245 | 57 | 1,247 |
| bounce_rate | float | 0.448 | 0.078 | 0.172 | 0.695 |
| avg_session_duration_sec | int | 180 | 40 | 64 | 291 |
| new_signups | int | 14.8 | 3.9 | 5 | 27 |
| support_tickets | int | 3.0 | 1.7 | 0 | 10 |

The data is clean: no nulls, no negative values, no impossible ranges. 63 days had zero support tickets, which is plausible.

---

## 2. Key Findings

### 2.1 Strong Growth in Traffic, Flat Engagement Metrics

The dominant pattern in this dataset is **sustained linear growth in traffic** (pageviews and unique visitors) while all engagement and conversion metrics remain stationary.

| Metric | 2022 | 2023 | 2024 | Trend |
|---|---|---|---|---|
| Avg daily pageviews | 647 | 934 | 1,240 | +211/year |
| Avg daily visitors | 420 | 608 | 806 | +138/year |
| Total annual signups | 5,444 | 5,328 | 5,475 | Flat (~5,400/year) |
| Total annual tickets | 1,074 | 1,068 | 1,101 | Flat (~1,080/year) |
| Avg bounce rate | 0.445 | 0.453 | 0.445 | Flat (~0.45) |
| Avg session duration | 181s | 178s | 181s | Flat (~180s) |

**Interpretation:** Traffic nearly doubled over 3 years, but signups and support tickets did not grow proportionally. This means the **conversion rate is declining** (4.77% in 2022 -> 2.66% in 2023 -> 2.00% in 2024). The additional traffic is not converting.

### 2.2 Dual Seasonality: Annual + Weekly Cycles

Spectral analysis reveals two dominant periodic patterns in pageviews:

1. **Annual cycle (365-day period):** Pageviews peak around March-April and trough around August-September. The amplitude is approximately +/-400 pageviews around the trend. This pattern repeats consistently across all three years.

2. **Weekly cycle (7-day period):** Mondays and Sundays receive the most traffic (avg ~1,100 pageviews); Thursdays receive the least (avg ~748). This pattern is stable over time.

ADF stationarity tests confirm:
- Pageviews are **non-stationary** (ADF p=0.59) due to the trend
- All other metrics are **stationary** (ADF p<0.0001)

### 2.3 Near-Perfect Coupling Between Pageviews and Visitors

The correlation between pageviews and unique visitors is **0.972**. The pages-per-visit ratio is remarkably stable at 1.55 +/- 0.14 with no trend (slope p=0.94). This means visitor behavior hasn't changed: each visitor views roughly the same number of pages regardless of traffic level.

### 2.4 Independence of Other Metrics

A key finding is that bounce rate, session duration, signups, and support tickets are **essentially uncorrelated** with traffic and with each other (all correlations < 0.05). A regression of signups on all traffic features yields R²=0.002, confirming signups are independent of traffic volume.

This suggests:
- Signups are driven by factors not captured in this dataset (marketing campaigns, product changes, etc.)
- Bounce rate appears to be random noise around ~0.45 with no discernible pattern
- Support tickets are similarly independent of traffic volume

---

## 3. Modeling

### 3.1 Model Selection

Given the clear trend + dual seasonality in pageviews, two models were compared:

1. **Linear Regression + Fourier Terms** (trend + annual harmonics + weekly harmonics, 12 parameters)
2. **SARIMAX(1,1,1)(1,1,1,7)** (seasonal ARIMA with weekly seasonality)

### 3.2 Results (90-day holdout test set)

| Model | Train R² | Test R² | Test MAE | Test RMSE |
|---|---|---|---|---|
| Linear + Fourier | 0.957 | 0.873 | 60.1 | 75.6 |
| SARIMAX | -- | -0.135 | 178.8 | 225.7 |

The **Linear + Fourier model is the clear winner**. SARIMAX fails on multi-step forecasting because the annual cycle cannot be captured within a weekly seasonal period.

### 3.3 Model Equation

```
pageviews = 497.3 + 0.81*t + 399.3*sin(2*pi*t_year) - 11.3*cos(2*pi*t_year)
            - 49.5*sin(2*pi*t_week) + 190.7*cos(2*pi*t_week) + noise
```

Where `t` is days from start, `t_year` is fractional day-of-year, `t_week` is fractional day-of-week. The dominant terms are the linear trend (+0.81/day) and the first annual harmonic (amplitude ~399).

### 3.4 Model Diagnostics

All residual diagnostics pass:

| Test | Result | Interpretation |
|---|---|---|
| Breusch-Pagan | p=0.876 | No heteroscedasticity |
| Durbin-Watson | 1.994 | No autocorrelation (2.0 = perfect) |
| Ljung-Box (lag 30) | p=0.934 | No residual autocorrelation |
| Residual normality | Approximately normal | Q-Q plot confirms |

The residuals show no remaining structure, no trend, and constant variance. The model captures all systematic patterns in the data.

### 3.5 Time Series Cross-Validation

Using 5-fold TimeSeriesSplit, the model achieves R² of 0.83-0.86 on all folds except the first (which trains on insufficient data to learn the annual cycle). This confirms the model generalizes well across different time periods.

---

## 4. Anomalies and Data Quality

- **Outliers:** Minimal. Only 5 bounce-rate outliers and 4 session-duration outliers by IQR method. No evidence of data corruption or measurement errors.
- **No structural breaks:** The trend is linear throughout — no sudden shifts in traffic patterns.
- **Pages-per-visit ratio stability:** Extraordinarily stable at 1.55, suggesting consistent user behavior or possibly an artifact of how pageviews are counted.

---

## 5. Business Implications and Recommendations

### 5.1 The Conversion Problem

This is the most actionable finding: **traffic is growing but conversions are not**. The signup conversion rate has halved from 4.8% to 2.0% over 3 years while absolute signups remain flat at ~15/day. This suggests:

- The additional traffic may be lower-intent (e.g., organic search visitors who browse but don't convert)
- The signup funnel may not be optimized for the changing visitor profile
- Marketing/acquisition channels driving growth may differ from those that historically drove conversions

**Recommendation:** Segment visitors by acquisition channel to identify which traffic sources convert and which don't. Consider whether the signup flow needs adjustment for the evolving audience.

### 5.2 Seasonal Planning

The annual cycle is strong and predictable (amplitude ~400 pageviews). Peak traffic occurs in Q1 (March-April) and minimum traffic in Q3 (August-September).

**Recommendation:** Align product launches, campaigns, and infrastructure scaling with the seasonal cycle. Q1 is optimal for conversion experiments due to higher traffic volume.

### 5.3 Day-of-Week Patterns

Monday and Sunday are the highest-traffic days; Thursday is the lowest. This is consistent across all years.

**Recommendation:** Schedule maintenance and deployments for Thursdays. Prioritize content/feature launches for Mondays.

### 5.4 Forecast

Assuming the linear trend and seasonal patterns continue, the model projects:
- Average daily pageviews in 2025: ~1,500-1,600
- Peak daily pageviews (March 2025): ~1,800-2,000
- Trough daily pageviews (September 2025): ~1,100-1,300

The 95% confidence interval is approximately +/- 150 pageviews around the point forecast.

---

## 6. Plots Reference

| Plot | Description |
|---|---|
| `01_time_series_overview.png` | All 6 metrics with 30-day moving averages |
| `02_correlation_matrix.png` | Pairwise correlations |
| `03_day_of_week.png` | Boxplots by day of week |
| `04_seasonal_decomposition.png` | Additive decomposition (trend, seasonal, residual) |
| `05_distributions.png` | Histograms with mean/median |
| `06_pageviews_vs_visitors.png` | Scatter plot colored by date |
| `07_monthly_trends.png` | Monthly aggregates with linear trend |
| `08_annual_seasonality.png` | Year-over-year monthly comparison |
| `09_autocorrelation.png` | ACF/PACF for raw and differenced pageviews |
| `10_pages_per_visit.png` | Engagement ratio stability |
| `11_periodogram.png` | Spectral analysis showing 365-day and 7-day peaks |
| `12_model_comparison.png` | Linear+Fourier vs SARIMAX on test set |
| `13_residual_diagnostics.png` | Residual plots, Q-Q, heteroscedasticity check |
| `14_rate_metrics.png` | Conversion rate and ticket rate over time |
| `15_full_model_forecast.png` | Model fit with 90-day forecast and confidence interval |

---

## 7. Methodology Notes

- **Stationarity:** Tested with Augmented Dickey-Fuller (ADF)
- **Spectral analysis:** Periodogram on detrended pageviews
- **Modeling:** Compared parametric (Linear + Fourier) and ARIMA-based (SARIMAX) approaches
- **Validation:** 90-day holdout + 5-fold time series cross-validation
- **Residual diagnostics:** Breusch-Pagan (heteroscedasticity), Durbin-Watson (autocorrelation), Ljung-Box (serial correlation), Q-Q plot (normality)
- **All analysis performed in Python** using pandas, numpy, scipy, statsmodels, scikit-learn, matplotlib, and seaborn
