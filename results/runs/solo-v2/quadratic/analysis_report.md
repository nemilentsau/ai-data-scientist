# Fuel Consumption Analysis Report

## 1. Dataset Overview

This dataset contains 600 engine test observations measuring fuel consumption under varying conditions. Each row represents a single test with the following variables:

| Variable | Type | Range | Description |
|---|---|---|---|
| `engine_rpm` | Continuous (int) | 826 -- 5,999 | Engine speed in revolutions per minute |
| `ambient_temp_c` | Continuous (float) | 3.4 -- 49.6 | Ambient temperature in degrees Celsius |
| `humidity_pct` | Continuous (float) | 10.0 -- 95.0 | Relative humidity percentage |
| `octane_rating` | Categorical (int) | {87, 89, 91, 93} | Fuel octane rating (4 levels, roughly balanced) |
| `vehicle_age_years` | Discrete (int) | 0 -- 14 | Vehicle age in years |
| `fuel_consumption_lph` | Continuous (float) | 0.5 -- 74.2 | Fuel consumption in liters per hour (target) |

The data is clean: no missing values, no apparent coding errors, and all value ranges are physically plausible.

## 2. Key Findings

### Finding 1: Fuel consumption follows a quadratic law with RPM

The dominant relationship in this dataset is between engine RPM and fuel consumption. The relationship is **not linear but quadratic** -- fuel consumption scales with the square of RPM:

**fuel_consumption = 2.0 x 10^-6 x RPM^2**

Evidence:
- A linear model yields R^2 = 0.958 with clear curvature in residuals (see `plots/03_linear_vs_quadratic_fit.png`)
- A quadratic model yields R^2 = 0.9954 with RMSE = 1.46 L/h -- a 67% reduction in error
- An F-test comparing linear vs quadratic models is overwhelmingly significant (F = 4,891, p < 10^-300)
- Adding a cubic term provides essentially zero improvement (R^2 = 0.99542 vs 0.99541)
- In the quadratic OLS model, the linear RPM coefficient is non-significant (t = -0.16, p = 0.87), confirming the relationship is purely RPM^2, not a mix of RPM and RPM^2
- A power-law fit (log-log regression) estimates the exponent as 2.085 +/- 0.020, consistent with an exact square law

This relationship is physically intuitive: fuel consumption is proportional to power output, and engine power output scales approximately with RPM^2 (since both torque demand and frictional losses increase with engine speed).

See: `plots/02_rpm_vs_consumption_by_octane.png`, `plots/03_linear_vs_quadratic_fit.png`, `plots/06_final_model.png`

### Finding 2: No other variable has a meaningful effect on fuel consumption

After accounting for RPM^2, none of the remaining variables -- ambient temperature, humidity, octane rating, or vehicle age -- contribute significantly to predicting fuel consumption.

| Predictor | Coefficient | t-statistic | p-value |
|---|---|---|---|
| Ambient temperature | +0.010 L/h per degree C | +1.37 | 0.172 |
| Humidity | +0.001 L/h per % | +0.34 | 0.736 |
| Vehicle age | +0.023 L/h per year | +1.70 | 0.091 |
| Octane 89 (vs 87) | +0.139 L/h | +0.82 | 0.413 |
| Octane 91 (vs 87) | -0.031 L/h | -0.19 | 0.850 |
| Octane 93 (vs 87) | +0.156 L/h | +0.95 | 0.344 |

A partial F-test comparing the RPM^2-only model to the full model with all predictors yields F = 1.089 (p = 0.368). Adding all five extra predictors explains only 1.1% of the residual sum of squares and worsens the AIC from 2,157 to 2,162.

Vehicle age comes closest to significance (p = 0.091), but the effect size is negligible: +0.023 L/h per year of age, meaning a 14-year-old vehicle would consume only ~0.3 L/h more than a new vehicle at the same RPM -- well within the noise level (sigma = 1.46 L/h).

See: `plots/05_residuals_by_covariates.png`, `plots/07_correlation_heatmap.png`

### Finding 3: No interaction effects exist

The RPM^2 coefficient is remarkably stable across subgroups:

| Octane Rating | RPM^2 Coefficient | R^2 | RMSE |
|---|---|---|---|
| 87 | 1.987 x 10^-6 | 0.9953 | 1.50 |
| 89 | 2.005 x 10^-6 | 0.9955 | 1.46 |
| 91 | 1.994 x 10^-6 | 0.9959 | 1.41 |
| 93 | 2.021 x 10^-6 | 0.9951 | 1.44 |

Formal interaction tests (RPM^2 x octane: F = 1.186, p = 0.312; RPM^2 x temperature: t = -0.06, p = 0.951; RPM^2 x humidity: t = -0.44, p = 0.662; RPM^2 x vehicle age: t = +0.16, p = 0.874) are all non-significant. Environmental conditions and fuel type do not modify the RPM-consumption relationship.

## 3. Model Validation

The final model `fuel_consumption = 2.0 x 10^-6 x RPM^2 + 0.02` was validated using:

- **10-fold cross-validation**: R^2 = 0.9952 +/- 0.0010, RMSE = 1.454 +/- 0.117 L/h
- **80/20 holdout split**: Train R^2 = 0.9953, Test R^2 = 0.9960, Test RMSE = 1.41 L/h

The model shows no signs of overfitting (test performance matches or exceeds training performance).

Residual diagnostics confirm all classical regression assumptions are met:
- **Normality**: Shapiro-Wilk test W = 0.998, p = 0.677; QQ plot correlation r = 0.999 (`plots/04_residual_diagnostics.png`)
- **Homoscedasticity**: Breusch-Pagan test statistic = 0.043, p = 0.835
- **No residual patterns**: Residuals show no structure vs fitted values, RPM, or any covariate

See: `plots/04_residual_diagnostics.png`

## 4. Interpretation and Practical Implications

1. **Engine RPM is the sole driver of fuel consumption** in this dataset. A single-variable model explains 99.5% of the variance. In practical terms, knowing the RPM alone predicts fuel consumption to within ~1.5 L/h (about 5% of the mean consumption of 28.2 L/h).

2. **The quadratic relationship has physical meaning.** Fuel consumption being proportional to RPM^2 aligns with engine physics: power output (and hence fuel demand) scales with the square of rotational speed when load increases with speed. This is consistent with aerodynamic drag and internal friction models.

3. **Octane rating does not affect fuel consumption** in this dataset. While higher-octane fuel prevents engine knock and can enable higher compression ratios, the tests here show no consumption difference across the 87-93 octane range. This could mean the engines were not knock-limited during testing, or that octane affects performance (power output) rather than efficiency (fuel per unit time at a given RPM).

4. **Environmental conditions (temperature, humidity) are irrelevant** at the precision of these measurements. Any effect of air density on combustion efficiency is too small to detect above the ~1.5 L/h noise floor.

5. **Vehicle age has no practical impact.** The hint of a positive trend (+0.023 L/h per year, p = 0.091) might reflect gradual engine wear, but the effect is far too small to be actionable.

## 5. Limitations and Caveats

### What this analysis assumes
- **Observational data interpreted as-is.** The test conditions (RPM, temperature, etc.) appear to be experimentally varied, given their near-zero intercorrelations. If this is indeed controlled experimentation, the lack of confounding strengthens causal interpretability.
- **The RPM range (826-6,000) defines the model's validity.** Extrapolation beyond this range is not supported -- particularly at very low RPM where idle dynamics differ, or beyond redline where the quadratic law may break down.

### What might be missing
- **Engine load/throttle position** is not recorded. RPM alone determines consumption in this dataset, suggesting load may have been held constant or varied in lockstep with RPM. Under real driving conditions with variable load, RPM alone would be insufficient.
- **Vehicle/engine type** is not identified. If all 600 tests used the same engine type, the model is engine-specific. If multiple engines are represented, the stable RPM^2 coefficient across subgroups suggests the relationship generalizes.
- **Driving conditions** (speed, gear, road grade) are absent. The quadratic RPM law likely applies to bench-test or dynamometer conditions rather than real-world driving.

### Alternative explanations considered
- Could the near-perfect quadratic fit be an artifact of the data generation process? The residuals (sigma = 1.46 L/h) are well-behaved and proportionate to real measurement noise, making this unlikely.
- Could octane effects exist but be masked by noise? The power to detect a 0.5 L/h octane effect at alpha = 0.05 is approximately 80% with n = 600, so only very small effects (<0.5 L/h) could plausibly be hidden.

### Self-assessment
This analysis thoroughly tested the main relationships, interactions, and model assumptions. The conclusions are robust. The primary limitation is contextual: without knowing the experimental setup (constant load? single engine type? bench test?), the practical generalizability of the RPM^2 law remains uncertain.
