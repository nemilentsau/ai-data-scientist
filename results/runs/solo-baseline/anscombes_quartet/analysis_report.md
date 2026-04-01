# Dataset Analysis Report

## 1. Data Overview

| Property | Value |
|----------|-------|
| Observations | 44 |
| Variables | 7 |
| Missing values | 0 |

**Variables:**

| Column | Type | Description |
|--------|------|-------------|
| `observation_id` | int | Unique identifier (1-44) |
| `batch` | str | Batch label (Q1, Q2, Q3, Q4), 11 observations each |
| `dosage_mg` | int | Predictor variable (4-19 mg) |
| `response` | float | Outcome variable |
| `lab_temp_c` | float | Lab temperature (20.7-23.3 C) |
| `technician` | str | Technician (Alex: 18, Kim: 14, Pat: 12) |
| `weight_kg` | float | Subject weight (48.8-89.0 kg) |

No missing values, no obvious data entry errors at first glance.

## 2. Critical Finding: This Is Anscombe's Quartet

The most important finding in this dataset is that **all four batches share nearly identical summary statistics despite having fundamentally different data-generating processes**. This is a variant of Anscombe's quartet (1973), one of the most famous demonstrations in statistics of why visualization must accompany numerical summaries.

### Identical Statistics Across All Four Batches

| Statistic | Q1 | Q2 | Q3 | Q4 |
|-----------|----|----|----|----|
| Mean dosage | 9.00 | 9.00 | 9.00 | 9.00 |
| SD dosage | 3.32 | 3.32 | 3.32 | 3.32 |
| Mean response | 7.50 | 7.50 | 7.50 | 7.50 |
| SD response | 2.03 | 2.03 | 2.03 | 2.03 |
| Regression slope | 0.500 | 0.500 | 0.500 | 0.500 |
| Regression intercept | 3.00 | 3.00 | 3.00 | 3.00 |
| R-squared | 0.667 | 0.666 | 0.666 | 0.667 |
| F-statistic | 17.99 | 17.97 | 17.97 | 18.00 |
| p-value (slope) | 0.002 | 0.002 | 0.002 | 0.002 |

A naive analyst looking only at these statistics would conclude that all four batches behave identically. **They do not.**

### Visualizations Reveal the Truth

See: `plots/01_anscombe_scatterplots.png` and `plots/05_appropriate_models.png`

## 3. Per-Batch Analysis

### Batch Q1: True Linear Relationship

**Pattern:** Classic linear relationship with normally distributed residuals around the regression line.

**Diagnostics:**
- Shapiro-Wilk normality test: p=0.546 (residuals are normal)
- Breusch-Pagan heteroscedasticity test: p=0.418 (constant variance)
- Quadratic term p-value: 0.487 (no non-linearity)
- Max Cook's distance: 0.49 (borderline but acceptable for n=11)

**Conclusion:** The simple linear model `response = 0.50 * dosage + 3.00` is appropriate. All OLS assumptions are met. This is the only batch where the linear model is truly correct.

---

### Batch Q2: Non-Linear (Quadratic) Relationship

**Pattern:** A perfect quadratic (parabolic) relationship. The data follows a curved path that the linear model cannot capture.

**Diagnostics:**
- Quadratic term p-value: <0.0001 (highly significant non-linearity)
- Quadratic model R-squared: 1.000 (perfect fit)
- Linear model R-squared: 0.666 (misleadingly decent)
- AIC: linear = 37.69, quadratic = -106.94 (overwhelming evidence for quadratic)

**Conclusion:** The linear model is **wrong** for Q2 despite the seemingly good R-squared. The correct model is quadratic: `response = a * dosage^2 + b * dosage + c`. The linear regression provides a systematically biased fit, underestimating response at both extremes and overestimating in the middle. This is the classic case where R-squared is misleading because the model form is wrong.

---

### Batch Q3: Linear with a Y-Outlier

**Pattern:** A near-perfect linear relationship for 10 of 11 observations, with one extreme outlier (observation 25: dosage=13, response=12.74).

**Diagnostics:**
- Shapiro-Wilk normality test: p=0.0016 (residuals **fail** normality)
- Cook's distance for outlier: 1.39 (extremely influential; threshold is ~0.36 = 4/n)
- Without outlier: the remaining 10 points fall almost exactly on a line

**Conclusion:** The outlier pulls the regression line toward it, degrading the fit for all other observations. The correct approach is to either (a) investigate and remove the outlier if it's a measurement error, or (b) use robust regression methods (e.g., RANSAC, Huber, or Theil-Sen). The linear model's R-squared of 0.667 masks the fact that the true underlying relationship is much tighter.

---

### Batch Q4: Regression Determined by a Single Leverage Point

**Pattern:** All observations have dosage=8 **except one** at dosage=19. That single point has leverage=1.0 (the maximum possible), meaning it completely determines the slope of the regression line.

**Diagnostics:**
- Leverage of outlier: 1.000 (completely controls the fit)
- Cook's distance: NaN (undefined because leverage is exactly 1.0 -- residual is forced to zero)
- Without the leverage point, all x-values are identical, so no regression is possible

**Conclusion:** This batch has **no evidence of a dosage-response relationship**. The regression line exists only because of a single extreme observation. The "slope" and "R-squared" are artifacts of one data point, not evidence of a pattern. If that single observation were removed, there would be zero x-variation and regression would be impossible. No scientifically valid conclusions can be drawn about the dosage-response relationship from Q4.

## 4. Covariate Analysis

The additional variables (`lab_temp_c`, `weight_kg`, `technician`) were assessed as potential confounders or effect modifiers.

| Covariate | Test | Statistic | p-value | Significant? |
|-----------|------|-----------|---------|-------------|
| Lab temperature | Pearson r vs response | r=-0.248 | 0.104 | No |
| Weight | Pearson r vs response | r=-0.054 | 0.727 | No |
| Technician | One-way ANOVA | F=1.282 | 0.288 | No |

**None of the covariates have a statistically significant relationship with the response.** Lab temperature shows the largest (but still non-significant) association, with a weak negative correlation. These covariates appear to be noise variables that do not confound the dosage-response relationship.

The batch dummies are also completely non-significant when added to a pooled regression (all p=1.000), which is expected given the identical regression statistics across batches.

## 5. Model Recommendations by Batch

| Batch | Recommended Model | Rationale |
|-------|------------------|-----------|
| Q1 | Simple linear regression | All assumptions met |
| Q2 | Quadratic (polynomial degree 2) | Perfect quadratic fit; linear is systematically biased |
| Q3 | Robust linear regression or outlier removal | One extreme y-outlier distorts OLS fit |
| Q4 | No regression possible | Only one distinct x-value pair; insufficient data for modeling |

## 6. Key Takeaways

1. **Never trust summary statistics alone.** All four batches are statistically identical by every standard measure (mean, SD, correlation, regression coefficients, R-squared, p-values), yet they represent four fundamentally different data patterns.

2. **Always visualize your data.** The scatterplots immediately reveal what the statistics hide: a linear trend (Q1), a quadratic curve (Q2), an outlier-contaminated line (Q3), and a leverage-driven artifact (Q4).

3. **Check regression diagnostics.** Residual plots, normality tests, heteroscedasticity tests, and influence measures (Cook's distance, leverage) are essential. The residual diagnostics for Q2, Q3, and Q4 all show clear violations that the summary R-squared conceals.

4. **Covariates are noise.** Lab temperature, subject weight, and technician identity show no significant relationship with the response variable and are not confounders.

5. **The pooled analysis is meaningless.** Running a single regression across all 44 observations would yield the same misleading R-squared=0.667, hiding the fact that three of four batches violate the linear model's assumptions in different ways.

## 7. Plots

| File | Description |
|------|-------------|
| `plots/01_anscombe_scatterplots.png` | Per-batch scatterplots with identical regression lines |
| `plots/02_residual_diagnostics.png` | Residual vs fitted and Q-Q plots per batch |
| `plots/03_distributions.png` | Variable distributions and boxplots |
| `plots/04_covariate_analysis.png` | Response vs covariates (temp, weight, technician) |
| `plots/05_appropriate_models.png` | Per-batch plots with correct model for each |
| `plots/06_influence_diagnostics.png` | Cook's distance vs leverage per batch |

## References

- Anscombe, F.J. (1973). "Graphs in Statistical Analysis." *The American Statistician*, 27(1), 17-21.
