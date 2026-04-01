# Dataset Analysis Report

## 1. Scope and analytic framing

The dataset contains one row per patient, with follow-up time in `months_on_study` and an event indicator in `event_occurred`. That makes this a survival-analysis problem rather than a plain classification or regression task. The analysis therefore emphasizes:

- data-quality auditing before modeling
- distributional checks and EDA
- non-parametric survival estimation
- multivariable time-to-event modeling
- assumption checks and internal validation

## 2. Data loading and inspection

- Shape: `800` rows x `8` columns
- Duplicate rows: `0`
- Duplicate patient IDs: `0`
- Missing values: none in any column
- Event rate: `0.662` (530 events, 270 censored)

### Column types

```text
patient_id              str
age                   int64
sex                category
stage              category
biomarker_level     float64
treatment          category
months_on_study     float64
event_occurred        int64
```

### Numeric summary

```text
           age  biomarker_level  months_on_study
count  800.000          800.000          800.000
mean    61.990            6.144           10.157
std     10.816            5.707            7.205
min     30.000            0.540            0.000
25%     55.000            2.658            4.500
50%     62.000            4.460            9.000
75%     69.000            7.570           14.300
max     90.000           53.940           29.700
```

### Distribution diagnostics

- `age` is roughly symmetric (sample Shapiro test did not suggest a major deviation).
- `biomarker_level` is strongly right-skewed (skewness `3.187`), so a log transform is more defensible than using the raw scale in proportional hazards modeling.
- `months_on_study` is moderately right-skewed.
- Three rows have zero recorded follow-up time. These were retained but adjusted to `0.01` months for survival-model fitting so the event ordering is preserved while avoiding zero-time numerical edge cases.

### Zero-time rows

```text
patient_id  age sex stage  biomarker_level treatment  months_on_study  event_occurred
    P-0281   56   M    II            10.92    Drug_B              0.0               1
    P-0332   32   M    II            10.12    Drug_B              0.0               1
    P-0507   77   F     I             4.26    Drug_A              0.0               1
```

## 3. Exploratory data analysis

### Categorical balance

- Sex is well balanced: 415 F, 385 M.
- Stage distribution: I 155, II 279, III 251, IV 115.
- Treatment distribution: Drug_A 386, Drug_B 414.

### Covariate balance by treatment

Potential confounding was checked before interpreting crude outcome differences:

- Stage by treatment: chi-square p = `0.0400`
- Sex by treatment: chi-square p = `0.8581`
- Age by treatment: Mann-Whitney p = `0.0780`
- Biomarker by treatment: Mann-Whitney p = `0.2240`

Interpretation:

- Treatment assignment is not perfectly balanced by stage.
- Drug_B has more stage I patients than Drug_A, so any crude treatment comparison should be adjusted for covariates.
- Sex balance is effectively equal across treatment groups.

### Visualizations produced

- `plots/numeric_distributions.png`
- `plots/group_boxplots.png`
- `plots/stacked_bars.png`
- `plots/correlation_heatmap.png`
- `plots/km_treatment.png`
- `plots/km_stage.png`
- `plots/cox_forest_plot.png`

## 4. Key patterns and anomalies

- The biomarker is highly skewed with a long upper tail, consistent with a log-normal-like distribution rather than a Gaussian one.
- The crude event rate is substantially higher for Drug_A (0.772) than Drug_B (0.560), and median follow-up is shorter for Drug_A, which already suggests worse survival under Drug_A.
- Stage proportions differ by treatment, indicating at least modest confounding in the treatment-outcome relationship.
- The recorded stage variable does not show a strong crude separation in event fractions by itself, so its role needs to be evaluated in a time-to-event model rather than from simple proportions alone.
- Zero-time events are uncommon but real enough to document; they can materially influence likelihood-based survival models if ignored.

## 5. Survival analysis

### Kaplan-Meier analysis

- Log-rank test by treatment: p = `1.23e-14`
- Log-rank test by stage: p = `0.7021`

Interpretation:

- Survival differs strongly by treatment in the unadjusted analysis.
- Stage does not show statistically detectable survival separation in this sample.

### Multivariable Cox proportional hazards model

Model specification:

- Outcome: time to event
- Duration: `months_on_study_adj`
- Event indicator: `event_occurred`
- Covariates: age, log biomarker, sex, stage dummies, treatment

The biomarker was log-transformed in the primary specification because its raw distribution is strongly right-skewed. A raw-biomarker Cox model was also fit as a sensitivity check because the log-transformed model did not improve partial AIC.

- Cox partial AIC with log biomarker: `6339.66`
- Cox partial AIC with raw biomarker: `6338.61`
- Apparent concordance index: `0.605`
- 5-fold cross-validated concordance index: mean `0.597`, SD `0.019`

#### Cox model coefficients

```text
                    coef  hazard_ratio  se(coef)       p  hr_ci_lower  hr_ci_upper
covariate                                                                         
treatment_Drug_B -0.6741        0.5096    0.0890  0.0000       0.4280       0.6068
sex_M            -0.1266        0.8811    0.0873  0.1472       0.7425       1.0456
log_biomarker    -0.0743        0.9284    0.0569  0.1916       0.8305       1.0379
stage_IV         -0.1921        0.8252    0.1530  0.2092       0.6114       1.1137
stage_II         -0.1409        0.8686    0.1241  0.2562       0.6810       1.1077
age               0.0042        1.0042    0.0041  0.2983       0.9963       1.0123
stage_III        -0.0458        0.9552    0.1252  0.7146       0.7473       1.2210
```

Interpretation of the main effects:

- `treatment_Drug_B` is the only clearly supported predictor in the adjusted Cox model, with hazard ratio `0.510` (95% CI `0.428` to `0.607`, p = `3.71e-14`).
- Age, sex, stage, and biomarker all have confidence intervals crossing the null and should be treated as weak or inconclusive signals in this dataset.
- The negative biomarker coefficient is not statistically distinguishable from zero, so it should not be over-interpreted as protective.
- Stage effects are estimated relative to stage I, but the fitted model does not provide strong evidence of a monotonic stage gradient here.

### Parametric sensitivity model

A Weibull AFT model was fit as a sensitivity analysis. Its AIC was `3905.69` and it reproduced the strong treatment signal while leaving the other covariates non-significant, which supports the stability of the main conclusion.

## 6. Assumption checks and validation

### Proportional hazards test

Global and covariate-specific Schoenfeld-type tests:

```text
                  test_statistic       p  -log2(p)
age                       0.0012  0.9721    0.0409
log_biomarker             0.8817  0.3477    1.5239
sex_M                     0.7816  0.3767    1.4087
stage_II                  0.0596  0.8071    0.3092
stage_III                 0.0277  0.8677    0.2047
stage_IV                  0.4535  0.5007    0.9981
treatment_Drug_B          0.8394  0.3596    1.4756
```

Interpretation:

- Covariates with large p-values do not show evidence against the proportional hazards assumption.
- Any term with small p-values would warrant time-varying effects or stratification; in this dataset the main treatment effect did not show a meaningful PH violation.

### Validation and modeling choices

- Internal validation used 5-fold cross-validated concordance rather than relying only on in-sample fit.
- Non-normal predictors were not forced into Gaussian assumptions; the biomarker was log-transformed based on observed skewness.
- No missing-data imputation was needed because completeness was 100%.
- The analysis avoided naive classification models because censoring would make them statistically inappropriate.

## 7. Conclusions

1. The dataset is structurally clean: no missing values, no duplicate patients, and only a small zero-time edge case.
2. This is a survival-analysis dataset, and using survival methods is necessary to respect censoring and follow-up time.
3. Drug_B is associated with better survival than Drug_A in both unadjusted Kaplan-Meier analysis and adjusted Cox modeling.
4. Biomarker level is strongly right-skewed, but after adjustment its association with hazard is weak and statistically inconclusive.
5. Treatment groups are not perfectly stage-balanced, so the adjusted model is more trustworthy than crude event rates alone.
6. Model discrimination is moderate rather than exceptional, and most predictive signal appears to come from treatment rather than from the baseline covariates provided.

## 8. Limitations

- This appears to be observational data, so treatment effects should not be interpreted as causal without stronger design assumptions.
- The stage variable does not necessarily encode enough disease severity by itself; unmeasured confounding may remain.
- There are only a small number of predictors, so omitted clinical factors could matter materially.
- External validation is not available from this single dataset.
