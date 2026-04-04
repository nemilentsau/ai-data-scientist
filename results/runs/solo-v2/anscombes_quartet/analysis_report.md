# Analysis Report: Dose-Response Experimental Data

## 1. Dataset Overview

This dataset contains 44 observations from a dose-response experiment across four batches (Q1-Q4), each with 11 observations. Variables include:

- **dosage_mg**: Drug dosage in milligrams (range: 4-19)
- **response**: Measured response (continuous, range: 3.10-12.74)
- **batch**: Experimental batch (Q1, Q2, Q3, Q4)
- **lab_temp_c**: Laboratory temperature in Celsius (20.7-23.3)
- **technician**: Lab technician who ran the experiment (Alex, Kim, Pat)
- **weight_kg**: Subject weight in kilograms (48.8-89.0)

There are no missing values. The dataset is small but carefully constructed.

## 2. Key Finding: This Is Anscombe's Quartet

The central finding is that this dataset is a domain-dressed version of **Anscombe's Quartet** (1973) — a classic statistical demonstration that identical summary statistics can describe fundamentally different data structures.

### 2.1 The Statistical Illusion

All four batches share **identical** summary statistics to two decimal places:

| Statistic | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| Mean dosage | 9.00 | 9.00 | 9.00 | 9.00 |
| Mean response | 7.50 | 7.50 | 7.50 | 7.50 |
| Std dosage | 3.32 | 3.32 | 3.32 | 3.32 |
| Std response | 2.03 | 2.03 | 2.03 | 2.03 |
| Correlation (r) | 0.816 | 0.816 | 0.816 | 0.817 |
| Regression slope | 0.50 | 0.50 | 0.50 | 0.50 |
| Regression intercept | 3.00 | 3.00 | 3.00 | 3.00 |
| R-squared | 0.667 | 0.666 | 0.666 | 0.667 |

An analyst relying solely on these statistics would conclude that all four batches exhibit the same dose-response relationship: a moderate linear association where each additional milligram of dosage increases response by 0.50 units.

**This conclusion would be wrong for three out of four batches.**

See: `plots/06_statistics_comparison_table.png` for a visual summary, and `plots/01_anscombe_quartet_overview.png` for the scatter plots that reveal the truth.

### 2.2 What Each Batch Actually Shows

#### Batch Q1: Genuine Linear Relationship
- Dosages span 4-14 mg evenly. Points scatter randomly around the regression line.
- Residuals are normally distributed (Shapiro-Wilk W=0.94, p=0.55).
- The linear model `response = 3.0 + 0.5 * dosage` is an appropriate fit.
- **Conclusion**: The only batch where the summary statistics tell the true story.

#### Batch Q2: Curvilinear (Quadratic) Relationship
- Same dosage range as Q1, but the dose-response relationship is **parabolic**, not linear.
- Response peaks around dosage 9-11 mg, then declines at higher doses.
- A quadratic model fits perfectly (R-squared = 1.000): `response = -0.127 * dosage^2 + 2.781 * dosage - 5.996`.
- The F-test for the quadratic term is overwhelmingly significant (p < 0.0001).
- The linear model misses this curvature entirely, as visible in the U-shaped residual pattern.
- **Conclusion**: A linear model is fundamentally wrong here. The data suggest a dose-response ceiling or toxicity effect at higher doses. See `plots/03_q2_quadratic_fit.png`.

#### Batch Q3: Linear Relationship Corrupted by a Single Outlier
- Ten of eleven observations follow a tight linear relationship: `response = 4.01 + 0.35 * dosage` with R-squared = 1.000.
- One observation (dosage=13 mg, response=12.74) is a dramatic outlier with a residual of +3.24.
- This single outlier shifts the slope from 0.35 to 0.50 and the intercept from 4.01 to 3.00, and degrades R-squared from 1.00 to 0.67.
- **Conclusion**: The true dose-response relationship is steeper and tighter than the pooled regression suggests. The outlier — potentially a recording error or anomalous subject — dominates the fit. See `plots/04_q3_outlier_impact.png`.

#### Batch Q4: No Dose-Response Relationship (Leverage Point Artifact)
- Ten of eleven observations have dosage = 8 mg with responses ranging from 5.25 to 8.84 (mean 7.00, std 1.17).
- A single observation at dosage = 19 mg with response = 12.50 creates the illusion of a dose-response relationship.
- Without this leverage point, regression is **undefined** (zero variance in dosage).
- The apparent R-squared of 0.667 and slope of 0.50 are entirely artifacts of one data point.
- **Conclusion**: This batch provides no evidence of a dose-response relationship. The experimental design is fundamentally flawed — you cannot estimate a dose-response curve from one dosage level plus one outlier. See `plots/05_q4_leverage_point.png`.

### 2.3 Residual Analysis Confirms the Diagnoses

Residual plots (`plots/02_residual_diagnostics.png`) reveal what summary statistics hide:

- **Q1**: Random scatter around zero — assumptions met.
- **Q2**: Clear U-shaped pattern — systematic misfit from imposing a linear model on curved data.
- **Q3**: One extreme residual (+3.24) dwarfs the rest (all < |0.7|) — outlier influence.
- **Q4**: Residuals at dosage=8 show no structure, with the leverage point residual near zero by construction.

## 3. Auxiliary Variables Are Not Informative

Three additional variables were examined for potential effects on response:

- **Subject weight** (weight_kg): No correlation with response (r = -0.05, p = 0.73) or with dosage (r = -0.01, p = 0.93). Partial correlation controlling for dosage is also negligible (r = -0.07, p = 0.64).
- **Lab temperature** (lab_temp_c): Weak negative correlation with response (r = -0.25, p = 0.10), not statistically significant. The temperature range is narrow (2.6 degrees C), making meaningful biological effects unlikely.
- **Technician**: No significant effect on residuals (one-way ANOVA: F = 1.01, p = 0.37). Apparent differences in mean response across technicians (Alex: 7.01, Kim: 8.12, Pat: 7.52) are explained by differences in which dosage levels they administered.

See `plots/07_auxiliary_variables.png`.

## 4. Implications

### Practical Implications for Dose-Response Analysis
1. **Never trust summary statistics alone.** Four datasets with identical means, variances, correlations, and regression lines tell four completely different stories.
2. **Always visualize your data.** A simple scatter plot would immediately reveal that only one batch supports a linear dose-response model.
3. **Check residuals.** Even without visualization of raw data, residual patterns diagnose model misspecification (Q2), outlier influence (Q3), and leverage effects (Q4).
4. **Experimental design matters.** Batch Q4 demonstrates that no amount of statistical sophistication can rescue a study where dosage variation is absent.

### What Appropriate Analysis Looks Like for Each Batch
- **Q1**: Linear regression is appropriate. Estimated dose-response: +0.50 units per mg.
- **Q2**: Use polynomial or nonlinear regression. The response peaks near 11 mg, suggesting an optimal dose.
- **Q3**: Investigate the outlier. If it is an error, exclude it; if genuine, use robust regression. The true slope (without the outlier) is 0.35, not 0.50.
- **Q4**: Redesign the experiment with varied dosage levels before drawing any conclusions.

## 5. Limitations and Self-Critique

- **Sample size**: With only 11 observations per batch, statistical power is low. The perfect R-squared values for the "true" models in Q2 and Q3 (after appropriate adjustments) suggest the data may be exactly constructed rather than empirically collected — consistent with Anscombe's original demonstration.
- **Anscombe's Quartet is a teaching tool, not a natural dataset.** The values are engineered to produce identical summary statistics. In real dose-response data, batches would not typically share such precise statistical agreement.
- **Auxiliary variable analysis is limited.** With n=44 and three technicians, we have limited power to detect technician effects. The weak temperature correlation (p=0.10) might reach significance in a larger study, though the narrow temperature range makes a meaningful effect unlikely.
- **Causal claims are not supported.** Even for batch Q1 where the linear model fits well, this observational analysis cannot establish that dosage *causes* the response — only that a linear association exists.
- **I did not investigate potential interactions** (e.g., dosage x weight, dosage x temperature) due to the small sample size and the dataset's nature as a statistical demonstration.

## 6. Conclusion

This dataset is a powerful demonstration of why visualization and diagnostic checking are indispensable in statistical analysis. Four batches with identical summary statistics — the same means, variances, correlations, and regression parameters — describe a genuine linear relationship (Q1), a quadratic curve (Q2), a corrupted linear fit (Q3), and an artifactual relationship driven by a single leverage point (Q4). Any automated pipeline that reports only regression coefficients and R-squared would conclude these four batches are equivalent. They are not.
