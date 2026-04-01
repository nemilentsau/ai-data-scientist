# Hospital Patient Outcomes Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Observations | 1,200 patients |
| Features | 8 (1 ID, 2 categorical, 4 numeric, 1 binary outcome) |
| Missing values | None |
| Duplicates | None |

**Variables:**

| Variable | Type | Range / Levels | Description |
|---|---|---|---|
| `patient_id` | ID | 1–1200 | Unique identifier |
| `department` | Categorical | Orthopedics, Neurology, Cardiology (400 each) | Hospital department |
| `age` | Integer | 35–78 (mean 54.5) | Patient age |
| `severity_index` | Float | 1.0–9.76 (mean 5.01) | Illness severity score |
| `treatment` | Categorical | A (571), B (629) | Treatment type |
| `length_of_stay_days` | Integer | 2–25 (mean 13.8) | Hospital stay duration |
| `recovery_score` | Float | 47.9–88.5 (mean 67.5) | Recovery outcome score |
| `readmitted` | Binary | 0 (1070), 1 (130) | Whether patient was readmitted (10.8% rate) |

Data quality is excellent: no missing values, no duplicates, all values within plausible ranges. Only 1 outlier detected in age (IQR method) and 5 minor outliers in recovery score, none requiring removal.

## 2. Key Finding: Simpson's Paradox in Treatment Assignment

**This is the most important finding in the dataset.** Treatment assignment is severely confounded with department:

| Department | Treatment A | Treatment B |
|---|---|---|
| Orthopedics | 356 (89%) | 44 (11%) |
| Neurology | 182 (46%) | 218 (54%) |
| Cardiology | 33 (8%) | 367 (92%) |

Chi-squared test: χ² = 523.91, p < 10⁻¹¹⁴ — treatment is **not** randomly assigned.

### The paradox:

- **Naive analysis** (no controls): Treatment B appears **better** — recovery score +2.24 points (p < 10⁻⁸)
- **Adjusted analysis** (controlling for severity and department): Treatment A is actually **better** — Treatment B shows -4.14 points (p < 10⁻²⁶)

**Why?** Treatment B is disproportionately given to Cardiology patients, who have the lowest severity (mean 3.03 vs. 6.98 for Orthopedics). Low-severity patients naturally recover better regardless of treatment. The naive comparison conflates "easier patients" with "better treatment."

**Within every department**, Treatment A outperforms Treatment B:

| Department | Treatment B effect (adjusted) | p-value |
|---|---|---|
| Orthopedics | -3.00 | 0.0001 |
| Neurology | -4.36 | < 0.0001 |
| Cardiology | -4.97 | < 0.0001 |

This is a classic Simpson's Paradox: the direction of the treatment effect reverses when the confounding variable (department/severity) is controlled for.

## 3. Exploratory Data Analysis

### 3.1 Severity is the dominant driver

Severity index is the strongest predictor of both outcomes:

- Severity → Recovery Score: r = -0.658 (p ≈ 0)
- Severity → Length of Stay: r = 0.853 (p ≈ 0)

Each 1-unit increase in severity is associated with:
- **-3.06 points** in recovery score
- **+2.04 days** in length of stay

### 3.2 Department differences are mediated by severity

Departments differ sharply in mean severity:

| Department | Mean Severity | Mean Recovery | Mean LOS |
|---|---|---|---|
| Cardiology | 3.03 | 71.94 | 10.48 |
| Neurology | 5.03 | 67.13 | 13.74 |
| Orthopedics | 6.98 | 63.32 | 17.20 |

However, after controlling for severity in regression models, department effects become **non-significant** (p > 0.7). This means department differences in outcomes are almost entirely explained by the different severity profiles of their patients.

### 3.3 Age has minimal independent effect

Age correlates with severity (r = 0.71), but after controlling for severity, age has **no significant effect** on recovery (p = 0.70) or length of stay (p = 0.41). The age-outcome association is mediated through severity.

### 3.4 Readmission is essentially unpredictable

Readmission (10.8% rate) shows weak correlations with all features (|r| < 0.06). The logistic regression model achieves:
- Pseudo R² = 0.013
- In-sample AUC = 0.588
- Cross-validated AUC = 0.561 ± 0.064

Only age reaches marginal significance (OR = 1.04 per year, p = 0.022). Readmission likely depends on factors not captured in this dataset (e.g., patient compliance, comorbidities, social support).

## 4. Models

### 4.1 Recovery Score Model (OLS)

**Formula:** `recovery_score ~ severity_index + age + treatment + department`

| Predictor | Coefficient | 95% CI | p-value |
|---|---|---|---|
| Intercept | 85.53 | [83.05, 88.02] | < 0.001 |
| Severity index | -3.06 | [-3.39, -2.74] | < 0.001 |
| Treatment B (vs A) | -4.14 | [-4.89, -3.40] | < 0.001 |
| Neurology (vs Cardiology) | -0.17 | [-1.11, 0.78] | 0.727 |
| Orthopedics (vs Cardiology) | 0.24 | [-1.23, 1.71] | 0.752 |
| Age | -0.01 | [-0.06, 0.04] | 0.702 |

- **R² = 0.496** (severity and treatment explain ~50% of variance)
- Interaction between severity and treatment: not significant (p = 0.92) — the treatment effect is consistent across severity levels

**Diagnostics (all passed):**
- Residuals are normally distributed (Shapiro-Wilk p = 0.88)
- No heteroscedasticity (Breusch-Pagan p = 0.37)
- No autocorrelation (Durbin-Watson = 1.98)
- VIFs acceptable (max 6.13 for Orthopedics dummy, driven by collinearity with severity)

### 4.2 Length of Stay Model (OLS)

**Formula:** `length_of_stay_days ~ severity_index + age + treatment + department`

| Predictor | Coefficient | p-value |
|---|---|---|
| Severity index | +2.04 days | < 0.001 |
| Treatment B (vs A) | +1.42 days | < 0.001 |
| Department/Age | Not significant | > 0.05 |

- **R² = 0.753** — severity explains most of the variance in length of stay
- Treatment B is associated with 1.4 additional days of hospitalization after adjustment
- Diagnostics clean (Breusch-Pagan p = 0.90, Durbin-Watson = 1.98)

### 4.3 Readmission Model (Logistic Regression)

The model has very low predictive power (AUC = 0.56 cross-validated). No predictor is strongly significant except age (OR = 1.04, p = 0.02). This model is not practically useful for predicting readmission — the available features explain only ~1.3% of the variance in readmission.

## 5. Assumptions Checked

| Assumption | Test | Result |
|---|---|---|
| Normality of residuals | Shapiro-Wilk | Passed (p = 0.88) |
| Homoscedasticity | Breusch-Pagan | Passed (p = 0.37) |
| No autocorrelation | Durbin-Watson | Passed (DW = 1.98) |
| No multicollinearity | VIF | Acceptable (max 6.1) |
| Linearity | Residuals vs Fitted plot | No pattern detected |
| Treatment × severity interaction | F-test | Not significant (p = 0.92) |

## 6. Conclusions and Recommendations

1. **Treatment A produces better recovery outcomes.** After controlling for confounders, Treatment A yields ~4 points higher recovery scores and ~1.4 fewer days of hospitalization compared to Treatment B. This effect is consistent across all three departments.

2. **Do not interpret naive treatment comparisons.** The strong confounding between treatment and department creates a Simpson's Paradox. Any analysis that fails to adjust for department or severity will reach the wrong conclusion about treatment effectiveness.

3. **Severity is the primary driver of patient outcomes.** It explains the majority of variation in both recovery score and length of stay. Department differences in outcomes vanish after severity adjustment.

4. **Readmission requires additional data.** The 10.8% readmission rate cannot be predicted from the available variables. Collecting data on comorbidities, discharge planning, medication adherence, and social determinants of health would be necessary to build a useful readmission risk model.

5. **Treatment assignment should be investigated.** The near-complete segregation of treatments by department raises questions: is this protocol-driven, or could there be a clinical rationale? If Treatment A is indeed superior, its limited use in Cardiology (only 8% of patients) warrants review.

## 7. Plots

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of numeric variables |
| `plots/02_boxplots.png` | Boxplots for outlier detection |
| `plots/03_correlation_heatmap.png` | Correlation matrix |
| `plots/04_treatment_outcomes.png` | Treatment comparison (recovery, LOS, readmission) |
| `plots/05_department_outcomes.png` | Department comparison |
| `plots/06_severity_analysis.png` | Severity vs outcomes + severity by treatment |
| `plots/07_age_analysis.png` | Age group analysis |
| `plots/08_pairplot.png` | Pairwise relationships colored by treatment |
| `plots/09_recovery_diagnostics.png` | OLS model diagnostics |
| `plots/10_los_diagnostics.png` | LOS model diagnostics |
| `plots/11_readmission_roc.png` | ROC curve for readmission model |
| `plots/12_coefficient_plot.png` | Recovery model coefficient plot |
