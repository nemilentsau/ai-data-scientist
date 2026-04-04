# Manufacturing Process Defect Rate Analysis

## 1. Dataset Overview

This dataset contains **1,500 manufacturing process observations** recorded at 30-minute intervals from June 1 to July 2, 2023 (31 days). Each record includes four continuous process variables (temperature, pressure, vibration, speed), a categorical operator/shift label, and a defect rate outcome.

| Variable | Type | Mean | Std | Range |
|---|---|---|---|---|
| temperature_c | Continuous | 200.2 | 5.0 | 183.8 -- 219.3 |
| pressure_bar | Continuous | 50.0 | 3.0 | 40.9 -- 61.8 |
| vibration_mm_s | Continuous | 1.94 | 1.92 | 0.0 -- 12.2 |
| speed_rpm | Continuous (int) | 2993 | 199 | 2365 -- 3623 |
| operator | Categorical | -- | -- | Shift_A (498), Shift_B (520), Shift_C (482) |
| defect_rate | Continuous | 0.862 | 0.192 | 0.011 -- 1.000 |

There are **no missing values** in any column.

## 2. Key Findings

### Finding 1: Defect rate follows a one-inflated Beta distribution

The defect rate has a distinctive two-component structure (see `plots/06_defect_rate_distribution_analysis.png`):

- **47.5% of observations** are exactly 1.0 (a point mass)
- **52.5% of observations** fall below 1.0 and follow a **Beta(2.92, 1.05)** distribution (K-S test p = 0.48, cannot reject)

The sub-1.0 component has mean 0.738 and is left-skewed, with most values concentrated between 0.6 and 1.0. This is a classic **one-inflated Beta** distribution. The placement of the 1.0 values in the time series is random (Wald-Wolfowitz runs test p = 0.44).

### Finding 2: Process variables have zero predictive power for defect rate

This is the central and most important finding. Every method tested confirms that the measured process variables cannot predict defect rate:

| Method | Metric | Value | Interpretation |
|---|---|---|---|
| Pearson correlation | max |r| | 0.063 (pressure) | Negligible |
| Mutual information | max MI | 0.020 nats (speed) | Near zero |
| Random Forest regression | 5-fold CV R² | -0.075 | Worse than mean baseline |
| Gradient Boosting regression | 5-fold CV R² | -0.218 | Worse than mean baseline |
| Random Forest classification (=1.0 vs <1.0) | 5-fold CV AUC | 0.494 | Worse than random |
| Permutation test (200 permutations) | p-value | 0.73 | No signal above chance |

The actual vs. predicted plot (`plots/09_model_validation.png`) shows the Random Forest essentially predicts the mean for every observation. The permutation test confirms the real model's R² (-0.03) is indistinguishable from models trained on shuffled labels.

Binned mean analyses (`plots/02_scatter_nonlinear.png`) show flat relationships across the full range of each variable, ruling out nonlinear effects. Extreme conditions (top/bottom 1% of each variable) show no significant deviation from the overall mean defect rate. Two-way interaction heatmaps (`plots/04_interactions_distance.png`) show no systematic patterns.

### Finding 3: All variables are mutually independent

The four process variables are uncorrelated with each other (maximum absolute Pearson r = 0.034 between temperature and pressure; see `plots/07_process_correlations_mi.png`). This is notable because in real manufacturing processes, temperature, pressure, vibration, and speed are typically physically coupled.

The operator/shift variable is approximately uniformly distributed across three shifts and is also independent of all process variables and defect rate. No shift performs meaningfully differently from any other (defect rate means: Shift_A = 0.861, Shift_B = 0.853, Shift_C = 0.875).

### Finding 4: No temporal structure exists

- **Autocorrelation**: The defect rate shows zero autocorrelation at all lags tested (1 through 50 half-hour intervals), including lag-48 (24 hours). See `plots/05_temporal_autocorrelation.png`.
- **Hourly patterns**: Mean defect rate varies only between 0.84 and 0.90 across hours with no systematic pattern (`plots/03_temporal_patterns.png`).
- **Day-of-week patterns**: Mean defect rate varies only between 0.84 and 0.89 across days of the week.
- **Trends**: No meaningful linear trends in any process variable over the 31-day period.

### Finding 5: Each variable fits a known parametric distribution

Every variable is well-described by a standard distribution (see `plots/08_distribution_fits_summary.png`):

| Variable | Distribution | Parameters | K-S p-value |
|---|---|---|---|
| temperature_c | Normal | mu=200.2, sigma=5.0 | 0.79 |
| pressure_bar | Normal | mu=50.0, sigma=3.0 | 0.99 |
| vibration_mm_s | Exponential | scale=1.94 | 0.91 |
| speed_rpm | Normal | mu=2993, sigma=199 | 0.97 |
| defect_rate (sub-1.0) | Beta | a=2.92, b=1.05 | 0.48 |

All K-S p-values are high, indicating excellent fits. The vibration distribution is particularly clean: a Gamma fit yields shape parameter a=1.02, which is effectively Exponential (Gamma with shape=1).

## 3. Interpretation

The complete independence of all variables, their clean parametric distributions, the absence of temporal structure, and the zero predictive signal from process variables to defect rate collectively point to a clear conclusion:

**This dataset appears to be synthetically generated from independent random distributions.** The data generating process can be fully described as:

```
temperature_c  ~ Normal(200.2, 5.0^2)
pressure_bar   ~ Normal(50.0, 3.0^2)
vibration_mm_s ~ Exponential(scale = 1.94)
speed_rpm      ~ Normal(2993, 199^2)
operator       ~ Uniform{Shift_A, Shift_B, Shift_C}
defect_rate    ~ 0.475 * delta(1.0) + 0.525 * Beta(2.92, 1.05)
```

All variables drawn independently.

### Practical implications

If this dataset were presented as real manufacturing data for the purpose of identifying process improvements:
- **No actionable levers exist** among the measured variables. Adjusting temperature, pressure, vibration, or speed would not be expected to change defect rates.
- **Shift reassignment would not help** -- all operators perform identically.
- **The defect rate appears driven by factors not captured in this dataset**, or is inherently stochastic at this measurement granularity.
- Before investing in process optimization based on these variables, one should either (a) instrument additional variables that may be causally linked to defects, or (b) verify the data collection and measurement pipeline.

## 4. Limitations and Self-Critique

### What I tested and confirmed
- Linear, nonlinear (binned means, RF, GBM), and information-theoretic (mutual information) relationships between all features and defect rate
- All pairwise interactions between process variables via heatmaps
- Temporal patterns at multiple scales (half-hourly, hourly, daily, weekly)
- Autocorrelation structure of defect rate
- Distribution fits via K-S tests and Q-Q plots
- Randomness of the binary (=1.0 vs <1.0) sequence via runs test
- Permutation test to confirm zero signal above chance

### Assumptions that could be wrong
- **The measurement interval matters**: 30-minute aggregation may wash out transient effects. If defects are caused by brief process excursions (seconds to minutes), these wouldn't appear in 30-minute averages.
- **The right variables may not be measured**: Root causes of defects could involve raw material properties, humidity, tooling wear, or other factors not in the dataset.
- **Lagged effects**: I checked autocorrelation and concurrent relationships but did not exhaustively test whether process conditions at time t predict defect rates at time t+k for all possible k. However, the zero autocorrelation in defect rate makes delayed effects unlikely.

### What I did not investigate
- **Multivariate extreme regions**: I checked 2-way interactions and individual extremes, but not 3-way or 4-way combinations. With 1,500 observations, these higher-order interactions would be very sparsely populated and unreliable.
- **Change-point detection**: The data could in principle contain structural breaks, though the daily average plot shows no obvious regime changes.
- **Causal inference methods**: Granger causality or instrument-based approaches were not applied, as the zero-correlation baseline makes them unlikely to yield different conclusions.

## 5. Plots Reference

| File | Description |
|---|---|
| `plots/01_distributions_overview.png` | Histograms of all variables and defect rate time series |
| `plots/02_scatter_nonlinear.png` | Scatter plots with binned means: each process variable vs defect rate |
| `plots/03_temporal_patterns.png` | Defect rate by hour, day of week, and daily average over time |
| `plots/04_interactions_distance.png` | Distance from operating center and 2-way interaction heatmaps |
| `plots/05_temporal_autocorrelation.png` | Autocorrelation function, lag plot, consecutive differences, trends |
| `plots/06_defect_rate_distribution_analysis.png` | Defect rate distribution analysis: Beta fit, Q-Q plot, runs test |
| `plots/07_process_correlations_mi.png` | Process variable cross-correlations and mutual information |
| `plots/08_distribution_fits_summary.png` | Parametric distribution fits for all variables |
| `plots/09_model_validation.png` | RF actual vs predicted, residuals, and permutation test |
