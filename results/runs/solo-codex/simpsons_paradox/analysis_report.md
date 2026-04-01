# Dataset Analysis Report

## Executive Summary

This analysis covers `dataset.csv`, a patient-level tabular dataset with **1193 rows** and **8 columns**. The data are structurally clean: there are **no missing values**, **no duplicated rows**, and **no duplicated `patient_id` values**.

The main findings are:

1. `severity_index` is the dominant driver of both outcomes that appear clinically meaningful in this dataset. Higher severity is strongly associated with **longer length of stay** and **lower recovery score**.
2. Treatment groups are **not balanced at baseline**. Patients receiving treatment `A` are older, more severe, and are concentrated in different departments than patients receiving treatment `B`. Raw treatment comparisons are therefore confounded.
3. After adjustment for age, severity, and department, treatment `B` is associated with an approximately **4.72-point lower recovery score** relative to treatment `A` (HC3-robust p < 0.001).
4. For `length_of_stay_days`, once severity is in the model, treatment and department effects are negligible. Severity explains most of the variation.
5. `readmitted` appears to contain **little or no predictive signal** in the available features. Cross-validated classification performance is near chance, so no strong conclusions about readmission drivers are warranted.

## 1. Data Loading and Inspection

### Dataset shape

- Rows: **1193**
- Columns: **8**

### Data types

```text
patient_id                int64
department             category
age                       int64
severity_index          float64
treatment              category
length_of_stay_days       int64
recovery_score          float64
readmitted                int64
```

### Missing values

```text
patient_id             0
department             0
age                    0
severity_index         0
treatment              0
length_of_stay_days    0
recovery_score         0
readmitted             0
```

### Numeric summary

```text
                      count     mean      std   min     25%     50%     75%     max
age                  1193.0   54.293    7.414  31.0   49.00   54.00   60.00    79.0
severity_index       1193.0    4.969    1.924   1.0    3.44    4.97    6.51    10.0
length_of_stay_days  1193.0   14.425    4.344   4.0   11.00   14.00   18.00    29.0
recovery_score       1193.0   67.725    7.908  43.0   62.10   67.50   73.30    90.0
patient_id           1193.0  597.000  344.534   1.0  299.00  597.00  895.00  1193.0
```

### Categorical distributions

#### `department`
```text
department
Neurology      415
Cardiology     402
Orthopedics    376
```

#### `treatment`
```text
treatment
A    619
B    574
```

#### `readmitted`
```text
readmitted
0    1058
1     135
```

### Duplicate checks

- Duplicated rows: **0**
- Duplicated `patient_id`: **0**

### IQR-based outlier screen

These are mild edge-case checks, not grounds for deletion by themselves.

```text
                     lower_bound  upper_bound  count
age                       32.500       76.500    3.0
severity_index            -1.165       11.115    0.0
length_of_stay_days        0.500       28.500    1.0
recovery_score            45.300       90.100    4.0
```

## 2. Exploratory Data Analysis

### Visualizations generated

- `plots/numeric_distributions.png`
- `plots/correlation_heatmap.png`
- `plots/recovery_vs_severity.png`
- `plots/los_vs_severity.png`
- `plots/treatment_boxplots.png`
- `plots/readmission_rates.png`
- `plots/missing_values.png`
- `plots/recovery_model_diagnostics.png`
- `plots/readmission_classifier_curves.png`

### Core EDA observations

- The numeric variables are well-behaved overall, with only a handful of IQR-defined outliers.
- `severity_index` has a **strong positive** linear relationship with `length_of_stay_days` and a **strong negative** linear relationship with `recovery_score`.
- `age` is strongly positively correlated with `severity_index`, which means age can look important in univariate analysis but largely fades after severity adjustment.
- Readmission prevalence is low (**0.113**), creating a class-imbalance problem for classification.

### Key correlations

```text
                   pair  pearson_r  p_value
0  severity vs recovery    -0.7078      0.0
1       severity vs LOS     0.8907      0.0
2       age vs severity     0.7269      0.0
```

### Group summaries by treatment

The treatment groups differ at baseline, which is important for interpretation.

```text
              age              severity_index              length_of_stay_days              recovery_score              readmitted             
             mean    std count           mean    std count                mean    std count           mean    std count       mean    std count
treatment                                                                                                                                      
A          55.567  7.298   619          5.371  1.889   619              15.194  4.329   619         68.714  7.729   619      0.111  0.315   619
B          52.920  7.297   574          4.536  1.868   574              13.596  4.210   574         66.658  7.966   574      0.115  0.319   574
```

### Department-treatment mix

Treatment assignment also varies by department.

```text
treatment        A      B
department               
Cardiology   0.361  0.639
Neurology    0.506  0.494
Orthopedics  0.702  0.298
```

### Group summaries by department

```text
                age              severity_index              length_of_stay_days              recovery_score              readmitted             
               mean    std count           mean    std count                mean    std count           mean    std count       mean    std count
department                                                                                                                                       
Cardiology   48.612  5.389   402          2.966  1.008   402              10.403  2.871   402         73.519  6.456   402      0.092  0.289   402
Neurology    54.639  6.045   415          5.083  1.080   415              14.665  2.865   415         67.006  6.531   415      0.123  0.329   415
Orthopedics  59.987  6.007   376          6.987  1.000   376              18.460  2.896   376         62.322  6.426   376      0.125  0.331   376
```

## 3. Patterns, Relationships, and Anomalies

### Strong patterns

- `severity_index` vs `length_of_stay_days`: Pearson r = **0.891**, p < 1e-16.
- `severity_index` vs `recovery_score`: Pearson r = **-0.708**, p < 1e-16.
- `age` vs `severity_index`: Pearson r = **0.727**, p < 1e-16.

### Treatment comparisons before adjustment

Raw group comparisons suggest treatment `A` patients are:

- Older
- More severe
- Longer-stay
- Slightly higher-recovery on average

That pattern is not causal evidence because treatment assignment is clearly confounded by baseline case mix.

### Statistical group tests

- Recovery by treatment: ANOVA p = **6.704e-06**, Kruskal p = **3.029e-05**
- Length of stay by treatment: ANOVA p = **1.567e-10**, Kruskal p = **4.944e-10**
- Readmission vs treatment: chi-square p = **0.9204**
- Readmission vs department: chi-square p = **0.2588**

Interpretation:

- Treatment groups differ strongly in recovery and LOS *before adjustment*.
- Readmission rate differences by treatment or department are not statistically compelling even before multivariable modeling.

### Anomalies and data-quality concerns

- No missingness or duplicates were found.
- Outlier counts are low and influence diagnostics do not indicate a handful of points dominating the recovery model.
- Maximum Cook's distance in the recovery model is **0.0135**; observations above the common `4/n` heuristic: **57**, but values are still small in absolute magnitude.

## 4. Modeling

### 4.1 Recovery Score Regression

I modeled `recovery_score` with OLS using:

`recovery_score ~ age + severity_index + C(treatment) + C(department)`

This model was chosen because:

- The outcome is continuous.
- EDA suggested approximately linear relationships.
- Residual diagnostics were acceptable.
- More complex nonlinear models did not outperform linear regression in cross-validation.

#### HC3-robust coefficient table

```text
                                 coef  std_err  p_value   ci_low  ci_high
Intercept                     87.0103   1.2510   0.0000  84.5558  89.4648
C(treatment)[T.B]             -4.7175   0.3031   0.0000  -5.3121  -4.1229
C(department)[T.Neurology]    -0.5655   0.4763   0.2353  -1.5000   0.3689
C(department)[T.Orthopedics]  -0.2106   0.6830   0.7579  -1.5505   1.1293
age                           -0.0294   0.0289   0.3095  -0.0862   0.0273
severity_index                -3.0497   0.1648   0.0000  -3.3731  -2.7263
```

#### Interpretation

- **Severity is the main predictor**: each 1-unit increase in `severity_index` is associated with an estimated **3.05-point decrease** in recovery score, holding age, treatment, and department constant.
- **Treatment matters after adjustment**: treatment `B` is associated with a **4.72-point lower** recovery score than treatment `A`, 95% CI [-5.31, -4.12].
- Age and department do not add much once severity is included.

#### Validation

```text
                       r2_mean  r2_std  mae_mean  rmse_mean
LinearRegression        0.5843  0.0392    4.0821     5.0894
RandomForestRegressor   0.5396  0.0363    4.2827     5.3593
```

Interpretation:

- Cross-validated `R^2` for linear regression is about **0.584**, indicating moderate explanatory power.
- The random forest underperformed the linear model, which supports the choice of a linear specification.

### 4.2 Length of Stay Regression

I also fit an adjusted model for `length_of_stay_days`:

`length_of_stay_days ~ age + severity_index + C(treatment) + C(department)`

#### HC3-robust coefficient table

```text
                                coef  std_err  p_value  ci_low  ci_high
Intercept                     4.5756   0.4890   0.0000  3.6163   5.5350
C(treatment)[T.B]             0.0768   0.1154   0.5059 -0.1497   0.3033
C(department)[T.Neurology]   -0.0155   0.1885   0.9343 -0.3854   0.3543
C(department)[T.Orthopedics] -0.0633   0.2782   0.8200 -0.6092   0.4826
age                          -0.0057   0.0113   0.6105 -0.0278   0.0164
severity_index                2.0423   0.0679   0.0000  1.9092   2.1755
```

Interpretation:

- Severity has a large positive association with LOS: about **2.04 additional days** per 1-unit increase in `severity_index`.
- Once severity is included, treatment is no longer meaningfully associated with LOS.
- This strongly suggests the raw LOS difference between treatments is largely explained by case-mix severity.

### 4.3 Readmission Classification

I fit a multivariable logistic regression and compared it with a random forest classifier under stratified 5-fold cross-validation.

#### Logistic regression odds ratios

```text
                                coef  odds_ratio  p_value
Intercept                    -4.0262      0.0178   0.0243
C(treatment)[T.B]             0.2054      1.2280   0.3267
C(department)[T.Neurology]    0.3122      1.3664   0.2934
C(department)[T.Orthopedics]  0.3109      1.3647   0.4706
age                          -0.0033      0.9967   0.8546
severity_index                0.0710      1.0736   0.6335
length_of_stay_days           0.0096      1.0096   0.8370
recovery_score                0.0197      1.0199   0.2763
```

#### Cross-validated classification metrics

```text
                        roc_auc_mean  average_precision_mean  balanced_accuracy_mean  brier_mean
LogisticRegression            0.4924                  0.1180                  0.4989      0.2505
RandomForestClassifier        0.4504                  0.1278                  0.5029      0.1438
```

Interpretation:

- ROC AUC is approximately **0.492** for logistic regression, which is essentially chance-level discrimination.
- Average precision is only slightly above the base event rate, and balanced accuracy is about **0.499**.
- The random forest does not improve the picture.

Conclusion: the available features do **not** support a useful predictive model for `readmitted`.

## 5. Assumption Checks and Model Diagnostics

### Recovery model assumptions

- **Linearity**: Scatterplots and model comparison tests did not support adding a quadratic severity term.
- **Interaction check**: A severity-by-treatment interaction did not materially improve fit.
- **Residual normality**: Jarque-Bera p = **0.3762**, which is consistent with approximately normal residuals.
- **Homoscedasticity**: Breusch-Pagan p = **0.0424**. There is mild evidence of heteroscedasticity, so I report **HC3-robust standard errors**.
- **Multicollinearity**: VIF values are acceptable for the substantive predictors.

```text
                  feature     VIF
0                   const  76.856
1                     age   2.123
2          severity_index   4.560
3             treatment_B   1.085
4    department_Neurology   2.314
5  department_Orthopedics   4.765
```

### Model specification checks

- Adding `severity_index^2` to the recovery model did not materially improve fit (p = **0.2460**).
- Adding a severity-by-treatment interaction also did not materially improve fit (p = **0.3938**).

### Readmission model caveats

- The target is imbalanced (135 positives out of 1193 rows).
- Poor cross-validated discrimination suggests either near-random variation or omitted predictors.
- Under these conditions, coefficient interpretation should be conservative.

## 6. Conclusions

The dataset is clean and internally consistent, but the substantive story is dominated by **severity**:

1. Higher severity is strongly associated with worse recovery and longer hospitalization.
2. Treatment assignment is confounded by severity and department, so raw comparisons are misleading.
3. After adjustment, treatment `A` is associated with meaningfully better recovery than treatment `B`, while LOS differences mostly disappear.
4. Readmission is not usefully explained by the available features, so any operational readmission model built from this dataset would be unreliable.

## 7. Recommended Next Steps

1. If this dataset is intended for causal treatment evaluation, collect or include additional pre-treatment covariates and use a design that addresses treatment assignment bias.
2. For readmission modeling, add clinically richer predictors such as comorbidities, discharge disposition, prior utilization history, medication burden, and social determinants.
3. If this is a synthetic benchmark dataset, treat the recovery and LOS models as structurally informative, but do not over-interpret the readmission target.
