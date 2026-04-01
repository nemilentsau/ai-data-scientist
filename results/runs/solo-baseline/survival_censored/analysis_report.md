# Survival Analysis Report: Drug A vs Drug B Clinical Trial

## 1. Dataset Overview

| Property | Value |
|---|---|
| Observations | 800 patients |
| Variables | 8 (patient_id, age, sex, stage, biomarker_level, treatment, months_on_study, event_occurred) |
| Missing values | None |
| Duplicate records | None |
| Event rate | 66.25% (530 events, 270 censored) |
| Follow-up range | 0.0 -- 29.7 months (median 9.0) |

### Variable Summary

- **age**: Range 30--90 (mean 62.0, SD 10.8). Approximately normally distributed.
- **sex**: F=415 (51.9%), M=385 (48.1%).
- **stage**: II (n=279, 34.9%), III (n=251, 31.4%), I (n=155, 19.4%), IV (n=115, 14.4%). Stage distribution is uneven.
- **biomarker_level**: Range 0.54--53.94 (mean 6.1, median 4.5). Heavily right-skewed (skewness=3.19, kurtosis=16.44). 16 extreme outliers identified (> 22.3 = Q3 + 3*IQR).
- **treatment**: Drug_B=414 (51.8%), Drug_A=386 (48.3%).
- **months_on_study**: Time-to-event variable. 3 patients had time = 0.0 months (all experienced events).
- **event_occurred**: Binary indicator (1 = event, 0 = censored).

### Data Quality Notes

1. **No missing data** -- all 800 rows are complete.
2. **3 patients with zero follow-up time** (P-0281, P-0332, P-0507) -- all had events. These may represent immediate events or data entry issues. They are retained for Cox PH analysis (which handles ties at time=0) but were adjusted to 0.01 for parametric AFT models that require positive durations.
3. **Biomarker outliers**: 16 patients have extreme biomarker values (> 22.3). A sensitivity analysis excluding these confirmed that results are robust (see Section 5).

## 2. Exploratory Data Analysis

### Treatment Group Balance

The treatment arms are reasonably well-balanced:

| Covariate | Drug A | Drug B | Test | p-value |
|---|---|---|---|---|
| Age (median) | 63.0 | 61.0 | Mann-Whitney U | 0.078 |
| Biomarker (median) | 4.31 | 4.56 | Mann-Whitney U | 0.224 |
| Sex (% female) | 52.3% | 51.4% | Chi-squared | 0.858 |
| Stage distribution | -- | -- | Chi-squared | **0.040** |

Stage shows a modest imbalance (p=0.04): Drug_A has more Stage II patients (145 vs 134) and fewer Stage I patients (59 vs 96). However, since stage is not a significant predictor of outcome in this dataset, this imbalance does not meaningfully confound the treatment comparison.

### Key Distributions

- Age is approximately normally distributed centered around 62.
- Biomarker is heavily right-skewed; log-transformation produces a more symmetric distribution. Log(1 + biomarker) is used in all models.
- Time on study is right-skewed as expected for survival data.

### Correlation Structure

Correlations among numeric variables are weak:
- Biomarker vs time: r = -0.04
- Age vs time: r = -0.03
- Age vs biomarker: r = 0.01
- Event vs time: r = -0.32 (expected: events tend to occur earlier)

No strong collinearity concerns for modeling.

*See plots: `01_distributions.png`, `02_biomarker_comparisons.png`, `03_correlations.png`*

## 3. Survival Analysis

### 3.1 Kaplan-Meier Estimates

| Group | Median Survival (months) | Event Rate |
|---|---|---|
| **Drug A** | **7.6** | 77.2% |
| **Drug B** | **13.5** | 56.0% |
| Overall | 10.7 | 66.3% |

### 3.2 Log-Rank Tests

| Comparison | Test Statistic | p-value | Significant? |
|---|---|---|---|
| Treatment (Drug A vs B) | 59.50 | **1.23e-14** | Yes |
| Stage (I/II/III/IV) | 1.42 | 0.702 | No |
| Sex (M vs F) | 1.70 | 0.193 | No |
| Biomarker tertile (Low/Med/High) | 0.85 | 0.655 | No |

**Treatment is the only variable with a statistically significant survival difference.** The absence of a stage effect is noteworthy -- in most clinical settings, stage is a strong prognostic factor. This could indicate that the "stage" variable in this dataset does not carry prognostic information, or that the event definition captures something other than disease progression/death.

*See plot: `04_kaplan_meier.png`*

## 4. Cox Proportional Hazards Model

### 4.1 Full Model

All covariates included: age, sex, treatment, log(biomarker), stage (dummy-coded, reference = Stage I).

| Covariate | Hazard Ratio | 95% CI | p-value |
|---|---|---|---|
| **treatment_A** | **1.96** | **1.65 -- 2.34** | **< 0.001** |
| sex_M | 0.88 | 0.74 -- 1.05 | 0.15 |
| age | 1.00 | 1.00 -- 1.01 | 0.30 |
| log_biomarker | 0.91 | 0.80 -- 1.05 | 0.21 |
| stage_II | 0.87 | 0.68 -- 1.11 | 0.26 |
| stage_III | 0.95 | 0.75 -- 1.22 | 0.71 |
| stage_IV | 0.83 | 0.61 -- 1.11 | 0.21 |

- **Concordance index**: 0.60
- **Likelihood ratio test**: chi2 = 65.1, p = 1.4e-11

**Interpretation**: Patients on Drug A have a 96% higher hazard (nearly double the risk of the event) compared to Drug B patients, after adjusting for age, sex, biomarker level, and stage. No other covariate reaches statistical significance.

### 4.2 Proportional Hazards Assumption

The Schoenfeld residual test shows **no violation of the PH assumption** for any covariate (all p > 0.05). Visual inspection of scaled Schoenfeld residuals over time confirms no systematic trends.

*See plots: `05_cox_forest_plot.png`, `06_schoenfeld_residuals.png`*

### 4.3 Residual Diagnostics

- **Deviance residuals**: Scattered symmetrically around zero with no obvious patterns, indicating reasonable model fit.
- **Martingale residuals vs log(biomarker)**: The LOWESS smoother is approximately flat, confirming that the log transformation is an appropriate functional form for biomarker.

*See plot: `07_residual_diagnostics.png`*

### 4.4 Treatment x Biomarker Interaction

An interaction model was tested to assess whether the treatment effect varies by biomarker level:

| Covariate | Coefficient | p-value |
|---|---|---|
| treatment_A | 0.36 | 0.17 |
| log_biomarker | -0.19 | 0.08 |
| treatment_A x log_biomarker | 0.18 | 0.21 |

The interaction term is not significant (p=0.21). However, a stratified analysis hints at a marginal biomarker effect within the Drug_B subgroup (HR=0.81, p=0.052), suggesting that higher biomarker levels may slightly improve outcomes for Drug_B patients. This would require a larger sample or targeted study to confirm.

## 5. Sensitivity Analyses

### 5.1 Excluding Biomarker Outliers

Removing 16 patients with extreme biomarker values (> 22.3):
- Treatment HR: 1.97 (95% CI: 1.66--2.35), p < 0.001
- Concordance: 0.60
- All other covariates remain non-significant.

**Results are robust to outlier exclusion.**

### 5.2 Parametric AFT Models

Three parametric models were compared (treatment, log_biomarker, age as covariates):

| Model | AIC | Concordance | Treatment p-value |
|---|---|---|---|
| **Weibull** | **3902** | 0.599 | 6.5e-14 |
| Log-Logistic | 3922 | 0.599 | 3.2e-13 |
| Log-Normal | 3971 | 0.597 | 2.5e-12 |

Weibull provides the best fit (lowest AIC). All parametric models confirm the highly significant treatment effect with consistent direction and magnitude.

*See plot: `08_adjusted_survival.png`*

## 6. Key Findings

1. **Drug A is associated with significantly worse survival outcomes compared to Drug B.** The hazard ratio is 1.96 (95% CI: 1.65--2.34, p < 0.001), meaning Drug A patients have approximately double the event rate. Median survival is 7.6 months for Drug A vs 13.5 months for Drug B.

2. **Treatment is the only significant predictor.** Age, sex, cancer stage, and biomarker level do not significantly affect time-to-event in this dataset. This is consistent across univariate (log-rank) and multivariable (Cox PH) analyses.

3. **The absence of a stage effect is unexpected** and warrants clinical investigation. Possible explanations include: (a) the event being measured may not be stage-dependent (e.g., a treatment side effect rather than disease progression), (b) the stage variable may have data quality issues, or (c) treatment effects may dominate stage effects in this disease context.

4. **The proportional hazards assumption holds**, and results are robust across model specifications (Cox semi-parametric, Weibull/LogLogistic/LogNormal parametric), sensitivity analyses (outlier exclusion), and subgroup analyses.

5. **Modest model discrimination** (concordance ~0.60) indicates that while treatment is a strong predictor, substantial unexplained variability remains. Unmeasured confounders or inherent randomness in event times may explain this.

6. **A suggestive treatment-biomarker interaction** (Drug_B patients with higher biomarker levels may have slightly better outcomes, p=0.052) could be explored in future studies with larger samples.

## 7. Limitations

- **Observational vs. experimental**: Without knowing the study design (randomized trial vs observational), the causal interpretation of the treatment effect should be cautious. The modest stage imbalance (p=0.04) between arms suggests possible non-random assignment.
- **Moderate concordance**: The model explains limited variation beyond treatment assignment. Important prognostic factors may be unmeasured.
- **Zero follow-up times**: 3 patients had months_on_study = 0, which may reflect data collection issues.
- **Right-skewed biomarker**: The heavy right skew and extreme outliers in biomarker_level suggest possible measurement issues or a biologically distinct subpopulation.

## 8. Plots Generated

| File | Description |
|---|---|
| `plots/01_distributions.png` | Distributions of age, biomarker, time, stage, treatment |
| `plots/02_biomarker_comparisons.png` | Biomarker boxplots by treatment, stage, event |
| `plots/03_correlations.png` | Correlation heatmap and biomarker vs time scatter |
| `plots/04_kaplan_meier.png` | Kaplan-Meier curves by treatment, stage, sex, biomarker tertile |
| `plots/05_cox_forest_plot.png` | Cox PH hazard ratio forest plot |
| `plots/06_schoenfeld_residuals.png` | Schoenfeld residual plots (PH assumption check) |
| `plots/07_residual_diagnostics.png` | Deviance and martingale residual diagnostics |
| `plots/08_adjusted_survival.png` | Adjusted Cox survival curves and KM with confidence bands |
