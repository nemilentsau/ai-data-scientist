# Dataset Analysis Report

## Executive Summary

This dataset is a disguised variant of **Anscombe's Quartet** — a classic statistical demonstration that summary statistics alone are insufficient for understanding data. All four batches share nearly identical means, variances, correlations (r ~ 0.816), and OLS regression lines (response = 0.500 * dosage + 3.00), yet each exhibits a fundamentally different data-generating process. A naive pooled analysis would entirely miss these critical differences.

**Key takeaway:** Always visualize your data. Summary statistics can be deeply misleading.

---

## 1. Data Description

| Property | Value |
|---|---|
| Rows | 44 |
| Columns | 7 |
| Missing values | 0 |
| Batches | 4 (batch_Q1 through batch_Q4, 11 obs each) |

**Columns:**
- `observation_id`: Integer identifier (1-44)
- `batch`: Categorical grouping variable (batch_Q1, batch_Q2, batch_Q3, batch_Q4)
- `dosage_mg`: Integer predictor variable (4-19 mg)
- `response`: Continuous outcome variable (3.10-12.74)
- `lab_temp_c`: Continuous nuisance variable (20.7-23.3 C)
- `technician`: Categorical nuisance variable (Alex, Kim, Pat)
- `weight_kg`: Continuous nuisance variable (48.8-89.0 kg)

---

## 2. The Anscombe Trap: Identical Statistics, Different Realities

All four batches produce the same summary statistics:

| Statistic | batch_Q1 | batch_Q2 | batch_Q3 | batch_Q4 |
|---|---|---|---|---|
| Mean dosage | 9.00 | 9.00 | 9.00 | 9.00 |
| Var dosage | 11.00 | 11.00 | 11.00 | 11.00 |
| Mean response | 7.50 | 7.50 | 7.50 | 7.50 |
| Var response | 4.13 | 4.13 | 4.12 | 4.12 |
| Pearson r | 0.8164 | 0.8162 | 0.8163 | 0.8165 |
| OLS intercept | 3.000 | 3.001 | 3.002 | 3.002 |
| OLS slope | 0.500 | 0.500 | 0.500 | 0.500 |
| R-squared | 0.667 | 0.666 | 0.666 | 0.667 |

Yet the scatter plots (see `plots/01_anscombe_quartet_scatter.png`) reveal four completely different relationships.

---

## 3. Per-Batch Analysis

### batch_Q1: Well-Behaved Linear Relationship

A genuine linear relationship between dosage and response with moderate scatter.

- **Model assumptions met:** Residuals are normally distributed (Shapiro-Wilk p=0.55), homoscedastic (Breusch-Pagan p=0.42), and no significant nonlinearity (quadratic F-test p=0.49).
- **OLS is appropriate here.** The linear model adequately captures the data-generating process.
- One mildly influential point (obs 3, Cook's D=0.49) but not severely distorting.

**Conclusion:** Standard linear regression is valid for this batch.

### batch_Q2: Curvilinear (Quadratic) Relationship

The relationship between dosage and response is a perfect parabola, not a line.

- **Nonlinearity detected:** The quadratic term F-test is overwhelmingly significant (p ~ 0.0). The quadratic model achieves R-squared = 1.000 (essentially a perfect fit).
- Residual normality is borderline (Shapiro-Wilk p=0.09) — consistent with systematic nonlinear misspecification.
- Both endpoint observations (obs 17 at dosage=14, obs 19 at dosage=4) are influential because the linear model systematically misses the curvature.

**Conclusion:** A linear model is inappropriate. A quadratic model (or polynomial regression) should be used. The linear R-squared of 0.67 dramatically understates the explanatory power of dosage — the true relationship is deterministic once the correct functional form is used.

### batch_Q3: Linear With One Outlier

An almost-perfect linear relationship is distorted by a single influential outlier.

- **Outlier identified:** Observation 25 (dosage=13, response=12.74) has Cook's D = 1.39 — well above any conventional threshold (4/n = 0.36). This single point inflates the OLS slope from 0.345 to 0.500.
- Residual normality is violated (Shapiro-Wilk p=0.002) — driven entirely by the outlier.
- **Robust regression (Huber M-estimator)** recovers the true slope: intercept=4.003, slope=0.346.
- Removing the outlier yields an essentially perfect linear fit (R-squared = 1.000, slope = 0.345).

**Conclusion:** The OLS regression line is biased by a single outlier. Robust regression or outlier removal reveals the true linear relationship. The outlier should be investigated — it may represent a measurement error, data entry mistake, or genuinely anomalous biological response.

### batch_Q4: Regression Driven by a Single Leverage Point

All 10 of 11 observations have dosage = 8, and one observation has dosage = 19. The entire regression is determined by the single outlying leverage point.

- The regression line is completely determined by one observation (obs 41, dosage=19, response=12.5). Remove it, and there is no variation in dosage — the correlation and slope become undefined.
- Standard diagnostic tests (Shapiro-Wilk p=0.78, Breusch-Pagan p=0.28) do not flag issues because the residual distribution at dosage=8 happens to look normal. This is a case where **diagnostics are deceived**.
- The quadratic F-test (p=1.0) correctly fails to detect nonlinearity — but only because two points cannot distinguish any polynomial form.

**Conclusion:** There is no real evidence for a dosage-response relationship in this batch. The data can only tell us what the response is at dosage=8 (mean 6.89, SD 1.17). The apparent linear relationship is an artifact of a single high-leverage observation.

---

## 4. Nuisance Variable Analysis

The three additional variables (`lab_temp_c`, `technician`, `weight_kg`) were investigated for potential confounding effects.

| Variable | Test | Result |
|---|---|---|
| lab_temp_c | Pearson r with response | r = -0.248, p = 0.10 (not significant) |
| weight_kg | Pearson r with response | r = -0.054, p = 0.73 (not significant) |
| technician | One-way ANOVA on dosage-adjusted residuals | F = 1.01, p = 0.37 (not significant) |

A multivariate model (dosage + lab_temp + weight) pooled across all batches yields:
- dosage_mg coefficient: 0.489 (p < 0.001) — the only significant predictor
- lab_temp_c coefficient: -0.349 (p = 0.32) — not significant
- weight_kg coefficient: -0.007 (p = 0.67) — not significant

**Conclusion:** The nuisance variables do not significantly predict response after accounting for dosage. They appear to be noise columns added for realism and are not confounders. Technician assignment is also balanced across batches with no detectable effect.

---

## 5. Model Recommendation Summary

| Batch | Appropriate Model | Notes |
|---|---|---|
| batch_Q1 | Simple linear regression | Assumptions satisfied |
| batch_Q2 | Polynomial (quadratic) regression | Deterministic quadratic; linear model inadequate |
| batch_Q3 | Robust linear regression (or OLS after outlier review) | Single outlier (obs 25) distorts OLS |
| batch_Q4 | No regression — insufficient dosage variation | Relationship is an artifact of one leverage point |

---

## 6. Plots Generated

| File | Description |
|---|---|
| `plots/01_anscombe_quartet_scatter.png` | Core scatter plots with OLS lines — reveals the four different patterns |
| `plots/02_residual_diagnostics.png` | Residuals vs fitted + Q-Q plots for each batch |
| `plots/03_nuisance_variables.png` | Distributions of lab temperature, weight; technician assignment by batch |
| `plots/04_correlation_heatmap.png` | Correlation matrix of all numeric variables (pooled) |
| `plots/05_linear_vs_quadratic.png` | Linear vs quadratic fit comparison per batch |
| `plots/06_leverage_cooks_distance.png` | Leverage vs residuals with Cook's distance coloring |
| `plots/07_robust_vs_ols_Q3.png` | OLS vs robust regression for batch_Q3 outlier analysis |
| `plots/08_boxplots.png` | Response and dosage distributions by batch |

---

## 7. Key Takeaways

1. **Summary statistics lie by omission.** All four batches have identical means, variances, correlations, and regression slopes — yet describe four fundamentally different phenomena.

2. **Always visualize before modeling.** A single scatter plot per batch would have immediately revealed that a unified linear model is inappropriate.

3. **Diagnostic tests are necessary but not sufficient.** Standard tests failed to flag batch_Q4's pathology (all tests pass because the residuals at dosage=8 happen to be well-behaved). Visual inspection of leverage plots caught what automated tests missed.

4. **Outliers can dominate results.** In batch_Q3, one observation shifted the regression slope by 45% (from 0.345 to 0.500). In batch_Q4, one observation is the sole source of the entire linear relationship.

5. **Nuisance variables are just that.** Neither lab temperature, subject weight, nor technician identity contributes meaningfully to the response — the dosage-response relationship (where it exists) is the only signal.

6. **The right model depends on the data.** No single modeling approach is correct for all four batches. Domain knowledge and visual diagnostics must guide model selection.
