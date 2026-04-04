# Spurious Correlations: Temperature as the Hidden Driver of Ice Cream Sales and Drowning Incidents

## 1. Dataset Overview

This dataset contains **730 daily observations** spanning January 1, 2023 through December 30, 2024 (two full years), with seven variables:

| Variable | Range | Mean | Description |
|----------|-------|------|-------------|
| `avg_temperature_c` | -11.0 to 33.3 | 9.96 | Daily average temperature (°C) |
| `ice_cream_sales_units` | 0 to 1,866 | 559 | Daily ice cream sales |
| `pool_visits` | 0 to 1,044 | 335 | Daily pool attendance |
| `drowning_incidents` | 0 to 5 | 0.58 | Daily drowning count |
| `uv_index` | 0.0 to 5.3 | 1.67 | Daily UV index |
| `humidity_pct` | 11 to 95 | 55.0 | Daily humidity percentage |

There are no missing values. The data shows strong seasonal patterns across all variables except humidity, which is essentially flat year-round (see `plots/01_time_series_overview.png`).

## 2. Key Findings

### Finding 1: Ice cream sales and drowning incidents are strongly correlated — but the relationship is spurious

A naive analysis finds a striking correlation between ice cream sales and drowning incidents: **r = 0.486, p < 10^-44** (`plots/03_spurious_correlation_triptych.png`, Panel A). This appears to suggest that ice cream sales somehow predict — or even cause — drowning.

However, this correlation is **entirely confounded by temperature**:

- Temperature correlates with ice cream sales at r = 0.973 (Panel C)
- Temperature correlates with drowning at r = 0.481 (Panel B)
- Both variables are driven by the same underlying cause: warm weather

**After controlling for temperature**, the ice cream-drowning correlation collapses from r = 0.486 to **r = 0.089** (`plots/04_partial_correlation_evidence.png`). While technically significant at p = 0.017 (due to the large sample size of 730 days), this residual explains less than 0.8% of variance — effectively zero practical significance.

### Finding 2: Poisson regression confirms temperature is the sole meaningful predictor

Since drowning incidents are count data (integers 0–5), Poisson regression is the appropriate model. Three models were compared:

| Model | AIC | Key Result |
|-------|-----|------------|
| Drowning ~ Ice Cream (naive) | 1317.3 | Ice cream significant (p < 0.001) |
| Drowning ~ Temperature | 1304.4 | Temperature significant (p < 0.001) |
| Drowning ~ Temperature + Ice Cream | 1306.3 | Ice cream **non-significant** (p = 0.881) |

The likelihood ratio test confirms that **adding ice cream sales to a temperature model provides zero improvement** (LR = 0.022, p = 0.881). The full model with all five predictors shows only temperature as significant (p = 0.002); ice cream (p = 0.918), pool visits (p = 0.187), UV index (p = 0.539), and humidity (p = 0.427) all fail to reach significance.

The Poisson model's dispersion ratio is 1.061 (close to 1.0), confirming that the Poisson assumption is appropriate and overdispersion is not a concern.

### Finding 3: Temperature's effect size is substantial

From the Poisson regression, each 1°C increase in temperature multiplies the expected drowning rate by **1.080** (95% CI: 1.069–1.092). In practical terms:

- **Each 10°C warmer:** 2.17x more drownings
- **Summer (25°C) vs Winter (-5°C):** 10.17x more drownings

Seasonally, summer averages **1.07 drownings/day** compared to winter's **0.16 drownings/day** — a 6.7x difference (`plots/05_seasonal_patterns.png`, `plots/06_drowning_rate_by_temperature.png`).

### Finding 4: All temperature-correlated variables show the same confounding pattern

The spurious correlation is not unique to ice cream. Pool visits (raw r = 0.468, partial r = 0.020) and UV index (raw r = 0.482, partial r = 0.092) also appear strongly correlated with drowning in naive analysis but collapse when temperature is controlled (`plots/09_effect_size_comparison.png`).

Likelihood ratio tests confirm neither adds predictive power beyond temperature:
- Pool visits: LRT p = 0.156
- UV index: LRT p = 0.486
- Humidity: LRT p = 0.319

This is consistent with a **fork structure** in the causal graph: Temperature is the common cause, and all apparent relationships between its downstream variables (ice cream, pool visits, UV index) and drowning are non-causal (`plots/07_causal_dag.png`).

### Finding 5: No day-of-week effect on drowning

A Kruskal-Wallis test found no significant variation in drowning incidents across days of the week (H = 3.085, p = 0.798), suggesting weekend recreational patterns do not independently drive drowning risk in this dataset (`plots/08_drowning_distribution.png`).

### Finding 6: Cold-weather anomalies exist but are minor

21 days show ice cream sales despite sub-zero temperatures. These are mostly just barely below 0°C (median: -1.2°C) with modest sales. None of these days had high drowning counts. These anomalies represent noise in the sales data and do not affect the overall conclusions.

## 3. Interpretation

This dataset is a textbook illustration of **confounding** — one of the most important concepts in causal inference. The structure is:

```
Temperature  ──→  Ice Cream Sales
     │
     └──────────→  Drowning Incidents
```

Temperature causes *both* ice cream sales and drowning incidents to increase in summer. If you only observe the two downstream variables, you see a correlation and might erroneously conclude that ice cream causes drowning (or vice versa). But the relationship is entirely explained by their shared cause.

**Practical implications:**

1. **Correlation is not causation.** A statistically significant correlation (even at p < 10^-44) can be entirely spurious if a confounding variable is present.
2. **Always ask: what could cause both?** Before interpreting a correlation, identify potential common causes and control for them.
3. **Partial correlation and regression are essential tools** for disentangling confounded relationships. The drop from r = 0.486 to r = 0.089 when controlling for temperature is the analytical smoking gun.
4. **Statistical significance is not practical significance.** The residual partial correlation of r = 0.089 is technically significant (p = 0.017) only because n = 730 provides enough power to detect trivially small effects. The R-squared contribution is 0.006 — practically zero.

## 4. Limitations and Self-Critique

### What I tested
- Spurious correlation between ice cream and drowning (confirmed: spurious)
- Temperature as the common cause (confirmed: sole significant predictor)
- Whether pool visits, UV index, or humidity add predictive power (they do not)
- Day-of-week effects (none found)
- Model appropriateness (Poisson fits well; minimal overdispersion)

### Assumptions that could be wrong
- **Independence of observations.** Daily drowning counts may exhibit autocorrelation (e.g., a heat wave spanning multiple days). I did not model temporal autocorrelation, which could inflate significance in some tests.
- **Linear effect of temperature.** The Poisson model assumes a log-linear relationship between temperature and drowning rate. The relationship could be non-linear (e.g., a threshold effect above 20°C). The binned analysis in `plots/06_drowning_rate_by_temperature.png` shows a roughly monotonic increase, but the highest bin (31°C, n=7) has very few observations.
- **No interaction effects tested.** Temperature might interact with humidity or UV index in ways not captured by additive models.

### What I did not investigate
- **Lagged effects.** Does yesterday's temperature predict today's drowning? Heat waves might have cumulative effects.
- **Year-over-year trends.** With only two years of data, I cannot distinguish trend from interannual variability.
- **The mechanism.** Temperature likely affects drowning through *behavior* (more swimming, more water exposure), but this dataset does not directly measure water exposure. Pool visits — the closest proxy — showed no independent effect, which is surprising and could be a data artifact.
- **Geographic or demographic factors.** This is aggregated data with no spatial or demographic resolution.

### What could change the conclusions
If a variable not in this dataset (e.g., total hours spent in water, alcohol consumption, lifeguard staffing) independently predicted drowning while also correlating with temperature, the picture would become more complex. Temperature's dominance here may partly reflect the absence of mediating variables from the dataset.

## 5. Plot Index

| File | Description |
|------|-------------|
| `plots/01_time_series_overview.png` | All variables over time with 30-day rolling means |
| `plots/02_correlation_matrix.png` | Pairwise Pearson correlation heatmap |
| `plots/03_spurious_correlation_triptych.png` | Three-panel scatter: ice cream vs drowning, with temperature as the link |
| `plots/04_partial_correlation_evidence.png` | Key evidence: correlation before and after controlling for temperature |
| `plots/05_seasonal_patterns.png` | Monthly averages for all four main variables |
| `plots/06_drowning_rate_by_temperature.png` | Drowning rate per day across temperature bins |
| `plots/07_causal_dag.png` | Causal directed acyclic graph showing the confounding structure |
| `plots/08_drowning_distribution.png` | Drowning count distribution and day-of-week analysis |
| `plots/09_effect_size_comparison.png` | Raw vs partial correlations for all variables |
