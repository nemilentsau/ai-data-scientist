# Hospital Patient Outcomes Analysis Report

## 1. Dataset Overview

| Property | Value |
|----------|-------|
| Rows | 1,193 patients |
| Columns | 8 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Duplicate patient IDs | 0 |

**Variables:**

| Variable | Type | Range / Levels | Description |
|----------|------|----------------|-------------|
| `patient_id` | int | 1 -- 1193 | Unique identifier |
| `department` | categorical | Cardiology (402), Neurology (415), Orthopedics (376) | Hospital department |
| `age` | int | 31 -- 79, mean=54.3 | Patient age |
| `severity_index` | float | 1.0 -- 10.0, mean=5.0 | Illness severity score |
| `treatment` | categorical | A (619), B (574) | Treatment administered |
| `length_of_stay_days` | int | 4 -- 29, mean=14.4 | Hospital length of stay |
| `recovery_score` | float | 43.0 -- 90.0, mean=67.7 | Post-treatment recovery score |
| `readmitted` | binary | 0 (1058), 1 (135) | 30-day readmission flag (11.3% rate) |

The data is clean: no missing values, no duplicates, no obvious encoding errors, and all numeric distributions are approximately symmetric with minimal outliers.

---

## 2. Exploratory Data Analysis

### 2.1 Department Profiles

Departments differ dramatically in patient characteristics, reflecting fundamentally different patient populations:

| Department | Mean Age | Mean Severity | Mean LOS (days) | Mean Recovery | Readmission Rate |
|------------|----------|---------------|------------------|---------------|------------------|
| Cardiology | 48.6 | 3.0 | 10.3 | 73.5 | 9.2% |
| Neurology | 54.6 | 5.1 | 15.2 | 67.0 | 12.3% |
| Orthopedics | 59.9 | 7.0 | 18.6 | 62.5 | 12.5% |

Orthopedics patients are oldest, most severe, stay longest, and recover least. Cardiology patients are youngest with the best outcomes. All department differences in severity, LOS, and recovery score are highly significant (one-way ANOVA, all p < 10^-100).

### 2.2 Correlation Structure

Strong pairwise correlations among clinical variables:

| Pair | Pearson r |
|------|-----------|
| severity_index -- length_of_stay_days | 0.891 |
| severity_index -- age | 0.727 |
| severity_index -- recovery_score | -0.708 |
| age -- length_of_stay_days | 0.643 |
| age -- recovery_score | -0.521 |
| length_of_stay_days -- recovery_score | -0.639 |

**Readmission (`readmitted`) has near-zero correlation with every variable** (all |r| < 0.05).

### 2.3 Treatment Assignment

Treatment assignment is **not balanced across departments**:

| Department | Treatment A | Treatment B |
|------------|-------------|-------------|
| Cardiology | 145 (36%) | 257 (64%) |
| Neurology | 210 (51%) | 205 (49%) |
| Orthopedics | 264 (70%) | 112 (30%) |

However, **within each department**, age and severity are balanced between treatments (all p > 0.2), consistent with randomization within department strata.

*(See plots: `01_distributions.png`, `02_correlation_heatmap.png`, `03_pairplot_department.png`, `04_boxplots_department.png`)*

---

## 3. Key Finding: Treatment A Improves Recovery Scores

### 3.1 Within-Department Treatment Effect

Treatment A yields significantly higher recovery scores in every department:

| Department | Treatment A | Treatment B | Difference | Cohen's d | p-value |
|------------|-------------|-------------|------------|-----------|---------|
| Cardiology | 76.4 | 71.9 | +4.5 | 0.76 | 4.3 x 10^-12 |
| Neurology | 69.5 | 64.4 | +5.1 | 0.84 | 1.9 x 10^-16 |
| Orthopedics | 63.9 | 58.7 | +5.1 | 0.86 | 2.3 x 10^-13 |

Effect sizes are large and consistent (Cohen's d = 0.76 -- 0.86). A two-way ANOVA confirms that treatment and department are both significant main effects, with **no significant interaction** (F(2,1187) = 0.29, p = 0.75). The treatment benefit is uniform across departments.

### 3.2 No Treatment Effect on Length of Stay or Readmission

Treatment does **not** significantly affect:
- **Length of stay** (coef = +0.08 days, p = 0.52 in OLS)
- **Readmission** (OR = 1.23, p = 0.33 in logistic regression; chi-square p = 0.92)

Treatment A improves recovery quality without changing resource utilization or readmission risk.

*(See plots: `05_treatment_comparison.png`, `06_treatment_by_department.png`, `09_effect_sizes.png`, `10_severity_recovery_treatment.png`)*

---

## 4. Regression Models

### 4.1 Model 1: Recovery Score (OLS)

After testing a full model with all predictors and interactions, the parsimonious model retains only severity and treatment as significant predictors:

```
recovery_score = 85.8 - 4.7 * treatment_B - 3.2 * severity_index
```

| Predictor | Coefficient | SE | t | p-value | 95% CI |
|-----------|-------------|-----|---|---------|--------|
| Intercept | 85.76 | 0.47 | 182.8 | < 0.001 | [84.8, 86.7] |
| Treatment B (vs A) | -4.70 | 0.30 | -15.5 | < 0.001 | [-5.3, -4.1] |
| Severity Index | -3.17 | 0.08 | -40.4 | < 0.001 | [-3.3, -3.0] |

**Model fit:** R^2 = 0.585, Adj. R^2 = 0.585

**Interpretation:** Holding severity constant, Treatment B patients score 4.7 points lower on recovery than Treatment A patients. Each unit increase in severity reduces recovery by 3.2 points. Department and age are not significant after controlling for severity (they are confounded with it).

**10-fold cross-validation:** R^2 = 0.579 +/- 0.054, RMSE = 5.09 +/- 0.40 (stable, no overfitting).

### 4.2 Model 2: Length of Stay (OLS)

```
length_of_stay_days = 4.6 + 2.0 * severity_index
```

Severity is the sole significant predictor (R^2 = 0.794). Treatment, department, and age are non-significant.

### 4.3 Model 3: Readmission (Logistic Regression)

No predictor achieves significance (all p > 0.27). The model has essentially no discriminative power:
- Pseudo R^2 = 0.005
- 10-fold CV AUC = 0.49 +/- 0.05 (no better than random)

Readmission appears to be driven by factors not captured in this dataset.

*(See plots: `11_cross_validation.png`, `12_readmission_patterns.png`)*

---

## 5. Model Diagnostics

The recovery score OLS model passes all standard diagnostics:

| Diagnostic | Test | Result | Conclusion |
|------------|------|--------|------------|
| Normality of residuals | Shapiro-Wilk | W=0.996, p=0.21 | Pass |
| Normality of residuals | Kolmogorov-Smirnov | D=0.022, p=0.59 | Pass |
| Homoscedasticity | Breusch-Pagan | LM=1.56, p=0.46 | Pass |
| Independence | Durbin-Watson | 1.91 | Pass (near 2.0) |
| Multicollinearity | VIF | severity=1.05, treatment=1.05 | Pass (all < 5) |
| Residuals vs Fitted | Visual (LOWESS) | Flat, centered at 0 | Pass |

All OLS assumptions are satisfied. Residuals are well-behaved: normally distributed, homoscedastic, independent, and show no non-linear patterns.

*(See plot: `08_model_diagnostics.png`)*

---

## 6. Summary of Findings

1. **Treatment A produces significantly better recovery scores** than Treatment B, with a consistent ~4.7-point advantage across all departments (partial eta^2 = 0.169, a large effect). This finding is robust: covariates are balanced within departments, the effect is uniform across departments, and the model passes all diagnostic checks.

2. **Severity is the dominant driver of all clinical outcomes.** It explains the vast majority of variance in length of stay (R^2 = 0.79) and, together with treatment, 58.5% of variance in recovery score. The apparent differences between departments are fully explained by their differing severity profiles.

3. **Length of stay is driven almost entirely by severity**, with no meaningful contribution from treatment, department (after severity adjustment), or age.

4. **Readmission (11.3% rate) is not predictable** from any variable in this dataset. It shows no significant association with treatment, department, age, severity, recovery score, or length of stay. The relevant predictors are likely social determinants, comorbidities, or post-discharge care factors not captured here.

5. **Data quality is excellent:** no missing values, no duplicates, well-behaved distributions, and covariate balance consistent with stratified randomization within departments.

## 7. Recommendations

- **Favor Treatment A** for improving recovery outcomes. The evidence for its superiority is strong and consistent.
- **Investigate readmission drivers** by collecting additional variables (e.g., comorbidity indices, social support, discharge planning, medication adherence, post-discharge follow-up).
- **Use severity index as the primary case-mix adjuster** when benchmarking outcomes across departments; department-level comparisons without severity adjustment are misleading.

---

## Appendix: Plot Index

| File | Description |
|------|-------------|
| `plots/01_distributions.png` | Histograms with KDE for all numeric variables |
| `plots/02_correlation_heatmap.png` | Correlation matrix heatmap |
| `plots/03_pairplot_department.png` | Pairplot colored by department |
| `plots/04_boxplots_department.png` | Boxplots of outcomes by department |
| `plots/05_treatment_comparison.png` | Treatment A vs B: recovery, LOS, readmission |
| `plots/06_treatment_by_department.png` | Treatment effect within each department |
| `plots/07_scatter_relationships.png` | Key scatter plots with correlations |
| `plots/08_model_diagnostics.png` | OLS residual diagnostic plots |
| `plots/09_effect_sizes.png` | Bar chart with 95% CIs by department x treatment |
| `plots/10_severity_recovery_treatment.png` | Severity vs recovery with treatment regression lines |
| `plots/11_cross_validation.png` | Cross-validation boxplots |
| `plots/12_readmission_patterns.png` | Readmission rates by severity, age, and recovery bins |
