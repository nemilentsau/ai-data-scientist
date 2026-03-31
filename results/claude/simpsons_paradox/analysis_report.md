# Hospital Patient Outcomes Analysis Report

## 1. Dataset Overview

- **Size**: 1,193 patients, 8 variables, no missing values or duplicates
- **Variables**:
  - `patient_id`: Unique identifier (1–1193)
  - `department`: Cardiology (402), Neurology (415), Orthopedics (376)
  - `age`: 31–79, mean 54.3 (SD 7.4)
  - `severity_index`: 1.0–10.0, mean 5.0 (SD 1.9)
  - `treatment`: A (619) or B (574) — roughly balanced
  - `length_of_stay_days`: 4–29, mean 14.4 (SD 4.3)
  - `recovery_score`: 43–90, mean 67.7 (SD 7.9)
  - `readmitted`: Binary, 11.3% readmission rate (135/1193)

## 2. Key Findings

### 2.1. Departments Reflect Patient Severity, Not Independent Effects

Departments differ dramatically in raw outcomes, but this is driven entirely by patient composition:

| Department | Mean Age | Mean Severity | Mean LOS | Mean Recovery |
|---|---|---|---|---|
| Cardiology | 48.6 | 2.97 | 10.4 | 73.5 |
| Neurology | 54.6 | 5.08 | 14.7 | 67.0 |
| Orthopedics | 60.0 | 6.99 | 18.5 | 62.3 |

After controlling for severity in regression, **department has no significant effect** on recovery score (p=0.23 for Neurology, p=0.76 for Orthopedics) or length of stay (p>0.8). The apparent department differences are fully explained by the severity mix.

### 2.2. Treatment A Consistently Outperforms Treatment B

Treatment A produces recovery scores ~4.7 points higher than Treatment B, and this effect is:
- **Highly significant**: p < 0.0001
- **Consistent across all departments**: +4.5 (Cardiology), +5.1 (Neurology), +5.1 (Orthopedics)
- **Moderate-to-large effect**: Cohen's d = 0.76–0.86
- **No interaction**: The treatment effect does not vary by department (interaction p=0.75)

Treatment has **no effect on length of stay** (p=0.52) or **readmission** (p=0.92).

### 2.3. Severity Index Is the Dominant Predictor

- **Recovery score**: Each unit increase in severity reduces recovery by 3.17 points (p<0.0001)
- **Length of stay**: Each unit increase in severity adds 2.04 days (p<0.0001, R²=0.79)
- The relationship is linear — adding a quadratic severity term was not significant (p=0.70)
- Severity correlates strongly with age (r=0.73) and LOS (r=0.89)

### 2.4. Readmission Is Essentially Unpredictable from These Variables

The logistic regression for readmission found:
- No significant predictors (all p>0.27)
- Pseudo R² = 0.005 (near zero)
- Cross-validated AUC = 0.45 ± 0.04 (worse than random)
- Readmission appears to be driven by factors not captured in this dataset

## 3. Models

### Model 1: Recovery Score (Parsimonious OLS)

```
recovery_score = 85.76 − 3.17 × severity_index − 4.70 × treatment_B
```

- **R² = 0.585** — severity and treatment explain 58.5% of recovery variance
- Residuals are well-behaved: normally distributed (Shapiro p=0.14, Jarque-Bera p=0.39), no heteroscedasticity, Durbin-Watson ≈ 2.0
- Adding department, age, or LOS does not improve the model (R² = 0.587, added variables not significant)
- Multicollinearity is eliminated in this parsimonious specification (condition number = 18.6)

### Model 2: Length of Stay (OLS)

```
length_of_stay_days = 4.58 + 2.04 × severity_index
```

- **R² = 0.794** — severity alone explains nearly 80% of LOS
- Department, treatment, and age are not significant predictors after accounting for severity

### Model 3: Readmission (Logistic Regression)

- No predictive power from available variables
- Suggests readmission depends on unmeasured factors (e.g., social support, comorbidities, medication adherence)

## 4. Assumptions Checked

| Assumption | Status |
|---|---|
| Residual normality (recovery model) | Satisfied — Shapiro p=0.14, Jarque-Bera p=0.39 |
| Homoscedasticity | Satisfied — residuals vs. fitted shows constant spread |
| Linearity (severity → recovery) | Satisfied — quadratic term not significant |
| No multicollinearity (parsimonious model) | Satisfied — condition number 18.6 |
| Independence | Satisfied — Durbin-Watson ≈ 2.0 |

Note: The full model including severity_index and length_of_stay_days has elevated VIF (severity=6.0, LOS=4.8) due to their r=0.89 correlation. The parsimonious model avoids this by dropping LOS (which is itself predicted by severity).

## 5. Recommendations

1. **Adopt Treatment A as the preferred protocol** — it yields significantly better recovery scores (+4.7 points, d≈0.8) with no increase in length of stay, consistent across all departments.
2. **Severity index is the key driver** of outcomes and resource use. Clinical efforts to reduce severity at admission (earlier intervention, better triage) would have the highest leverage.
3. **Investigate readmission drivers** — the available clinical variables cannot predict readmission. Additional data collection on social determinants, comorbidities, and post-discharge factors is needed.
4. **Do not benchmark departments against each other** without adjusting for severity — raw comparisons are misleading since departments serve fundamentally different patient populations.

## 6. Plots

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all numeric variables |
| `plots/02_correlation_heatmap.png` | Pairwise correlation matrix |
| `plots/03_by_department.png` | Boxplots of key metrics by department |
| `plots/04_by_treatment.png` | Boxplots by treatment and department |
| `plots/05_severity_vs_recovery.png` | Scatter plot colored by department |
| `plots/06_readmission_rates.png` | Readmission rates by department, treatment, severity |
| `plots/07_ols_diagnostics.png` | Residual diagnostics for recovery model |
| `plots/08_treatment_effects.png` | Bar charts of treatment effects with 95% CI |
| `plots/09_key_relationships.png` | Regression plots: severity vs. LOS and recovery |
| `plots/10_treatment_adjusted.png` | Recovery vs. severity by treatment with regression lines |
