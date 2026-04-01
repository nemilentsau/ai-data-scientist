# Dataset Analysis Report

## Scope
This report analyzes `dataset.csv` as a student-performance dataset. The response variable treated as most meaningful for modeling is `gpa`. `student_id` was inspected but treated as an identifier rather than a legitimate academic predictor.

## 1. Data Loading and Inspection
- Rows: 600
- Columns: 7
- Missing values: 0
- Duplicate rows: 0
- Duplicate `student_id` values: 0
- GPA range: 1.55 to 4.00
- GPA ceiling at 4.0: 66 rows (11.0%)

### Schema Summary
```text
                       dtype  null_count  null_pct  n_unique
student_id             int64         0.0       0.0     600.0
weekly_study_hours   float64         0.0       0.0     167.0
gpa                  float64         0.0       0.0     197.0
extracurriculars       int64         0.0       0.0       6.0
commute_minutes        int64         0.0       0.0      70.0
part_time_job_hours  float64         0.0       0.0     190.0
absences               int64         0.0       0.0      10.0
```

### Descriptive Statistics
```text
                     count      mean       std   min       25%     50%       75%    max
student_id           600.0  300.5000  173.3494  1.00  150.7500  300.50  450.2500  600.0
weekly_study_hours   600.0   11.4813    4.0709  0.00    9.0000   11.40   14.6000   26.0
gpa                  600.0    3.1417    0.5824  1.55    2.7575    3.15    3.5725    4.0
extracurriculars     600.0    2.5267    1.7217  0.00    1.0000    3.00    4.0000    5.0
commute_minutes      600.0   30.1517   14.6145  0.00   20.0000   30.00   40.0000   80.0
part_time_job_hours  600.0    8.1593    5.4768  0.00    3.9000    7.95   11.7250   27.2
absences             600.0    2.8933    1.6922  0.00    2.0000    3.00    4.0000    9.0
```

### Outlier Screening by IQR Rule
```text
                     iqr_outlier_count  lower_bound  upper_bound
feature                                                         
student_id                         0.0    -298.5000     899.5000
weekly_study_hours                 3.0       0.6000      23.0000
gpa                                0.0       1.5350       4.7950
extracurriculars                   0.0      -3.5000       8.5000
commute_minutes                    3.0     -10.0000      70.0000
part_time_job_hours                4.0      -7.8375      23.4625
absences                           5.0      -1.0000       7.0000
```

## 2. Exploratory Data Analysis
Saved plots:
- `plots/distributions.png`
- `plots/boxplots.png`
- `plots/correlation_heatmap.png`
- `plots/gpa_relationships.png`
- `plots/gpa_vs_student_id.png`
- `plots/model_diagnostics.png`

### Correlation Summary with GPA
```text
                     pearson_r  spearman_rho  spearman_p
feature                                                 
student_id             -0.2012       -0.1976      0.0000
commute_minutes         0.0582        0.0412      0.3132
absences               -0.0176       -0.0198      0.6284
extracurriculars       -0.0075       -0.0049      0.9046
weekly_study_hours     -0.0030        0.0128      0.7552
part_time_job_hours     0.0027        0.0066      0.8720
```

### EDA Findings
1. The dataset is structurally clean: no missing values, no duplicate rows, and no duplicate IDs.
2. Every field is numeric. `student_id` is a unique sequence from 1 to 600 and should be considered metadata, not behavior.
3. The substantive predictors (`weekly_study_hours`, `extracurriculars`, `commute_minutes`, `part_time_job_hours`, `absences`) show near-zero Pearson and Spearman association with GPA.
4. `student_id` has the largest correlation with GPA (Pearson -0.201), which is not a credible real-world mechanism and therefore suggests leakage, synthetic structure, or a chance artifact.
5. GPA has a visible upper bound effect: 11.0% of observations are exactly 4.0, so ceiling behavior is present.
6. IQR screening flags only a small number of high-end observations in study hours, commute, job hours, and absences. These are plausible extremes, not clear data-entry errors.

## 3. Modeling Strategy
Two modeling scenarios were evaluated:
- `with_id`: includes every column except `gpa`
- `no_id`: excludes `student_id`, which is the realistic modeling setup

Models compared under 10-fold shuffled cross-validation:
- Mean-only baseline
- Linear regression
- Ridge regression
- Random forest regression

### Cross-Validated Performance
```text
  feature_set          model  cv_r2_mean  cv_r2_sd  cv_rmse_mean  cv_mae_mean
0       no_id     dummy_mean     -0.0329    0.0324        0.5828       0.4773
1       no_id          ridge     -0.0379    0.0356        0.5841       0.4786
2       no_id         linear     -0.0507    0.0456        0.5875       0.4814
3       no_id  random_forest     -0.1240    0.1020        0.6064       0.4911
4     with_id  random_forest     -0.0161    0.1074        0.5761       0.4711
5     with_id         linear     -0.0201    0.0871        0.5781       0.4747
6     with_id          ridge     -0.0194    0.0705        0.5783       0.4745
7     with_id     dummy_mean     -0.0329    0.0324        0.5828       0.4773
```

Best model in each feature set:
```text
                           cv_r2_mean  cv_r2_sd  cv_rmse_mean  cv_mae_mean
feature_set model                                                         
no_id       dummy_mean        -0.0329    0.0324        0.5828       0.4773
with_id     random_forest     -0.0161    0.1074        0.5761       0.4711
```

### Interpretation of Model Performance
1. Excluding `student_id`, all models perform at or worse than the mean baseline. That means the observed features contain little usable predictive signal for GPA.
2. Including `student_id` improves RMSE only trivially, and cross-validated R^2 remains negative. This confirms the identifier does not yield a useful predictive model even if it is statistically associated with GPA.
3. The cross-validated linear model without ID has:
   - R^2 = -0.0212
   - RMSE = 0.5881
   - MAE = 0.4814
4. Random forest does not uncover hidden nonlinear structure; its `no_id` performance is materially worse than the baseline.

### Permutation Importance for Random Forest (`no_id`)
```text
                     importance_mean  importance_std
feature                                             
weekly_study_hours            0.3319          0.0146
part_time_job_hours           0.2750          0.0086
commute_minutes               0.2296          0.0087
absences                      0.1061          0.0056
extracurriculars              0.0902          0.0057
```

This ranking is in-sample only. It can show which variables the fitted forest split on most often, but it should not be mistaken for evidence of useful predictive signal because the same model fails under cross-validation.

## 4. Linear Model Assumption Checks
Assumption checks were run on OLS models with and without `student_id`.

### OLS Without `student_id`
- Breusch-Pagan p-value: 0.2668
- Jarque-Bera p-value: 0.0002
- Durbin-Watson: 2.0619
- Ramsey RESET p-value: 0.3776

Coefficients:
```text
                      Coef.  Std.Err.        t   P>|t|  [0.025  0.975]
const                3.0982    0.1078  28.7392  0.0000  2.8865  3.3100
weekly_study_hours  -0.0005    0.0059  -0.0843  0.9329 -0.0120  0.0110
extracurriculars    -0.0019    0.0139  -0.1383  0.8901 -0.0292  0.0253
commute_minutes      0.0023    0.0016   1.4072  0.1599 -0.0009  0.0055
part_time_job_hours  0.0001    0.0044   0.0216  0.9828 -0.0085  0.0087
absences            -0.0056    0.0141  -0.3941  0.6936 -0.0333  0.0222
```

VIF:
```text
weekly_study_hours     1.0063
extracurriculars       1.0023
commute_minutes        1.0030
part_time_job_hours    1.0039
absences               1.0028
```

Largest Cook's distances:
```text
       student_id  cooks_distance  standardized_resid  leverage
index                                                          
436         108.0          0.0200             -2.6217    0.0172
548         509.0          0.0194             -2.5258    0.0179
293          38.0          0.0179             -1.5349    0.0436
341         526.0          0.0172             -2.3824    0.0179
319         578.0          0.0147             -2.7952    0.0112
376         513.0          0.0143             -1.9761    0.0215
176         494.0          0.0141             -2.2105    0.0170
98          413.0          0.0098             -2.1494    0.0126
568         476.0          0.0091             -1.8067    0.0164
32           83.0          0.0088              1.4479    0.0247
```

### OLS With `student_id`
- Breusch-Pagan p-value: 0.3577
- Jarque-Bera p-value: 0.0001
- Durbin-Watson: 2.0330
- Ramsey RESET p-value: 0.0030

Coefficients:
```text
                      Coef.  Std.Err.        t   P>|t|  [0.025  0.975]
const                3.2844    0.1122  29.2607  0.0000  3.0639  3.5048
student_id          -0.0007    0.0001  -4.9430  0.0000 -0.0009 -0.0004
weekly_study_hours   0.0027    0.0058   0.4614  0.6447 -0.0087  0.0141
extracurriculars    -0.0021    0.0136  -0.1535  0.8781 -0.0288  0.0246
commute_minutes      0.0018    0.0016   1.1088  0.2680 -0.0014  0.0049
part_time_job_hours -0.0012    0.0043  -0.2806  0.7791 -0.0096  0.0072
absences            -0.0032    0.0139  -0.2306  0.8177 -0.0304  0.0240
```

VIF:
```text
student_id             1.0228
weekly_study_hours     1.0188
extracurriculars       1.0023
commute_minutes        1.0073
part_time_job_hours    1.0077
absences               1.0040
```

Largest Cook's distances:
```text
       student_id  cooks_distance  standardized_resid  leverage
index                                                          
293          38.0          0.0256             -1.8918    0.0477
436         108.0          0.0250             -2.9366    0.0199
548         509.0          0.0163             -2.2961    0.0212
319         578.0          0.0153             -2.4722    0.0172
341         526.0          0.0143             -2.1298    0.0216
112         576.0          0.0138              1.9762    0.0242
176         494.0          0.0115             -2.0628    0.0185
376         513.0          0.0108             -1.6937    0.0257
529          53.0          0.0096             -2.0987    0.0150
397         581.0          0.0094             -2.2568    0.0127
```

### Assumption Assessment
1. Multicollinearity is negligible; all VIF values are approximately 1.
2. Residual normality is not the primary concern here. Even if residual diagnostics are acceptable, the coefficients are near zero and predictive performance is poor.
3. The key model risk is not assumption violation but signal absence: the dataset does not support a meaningful GPA prediction model from the available non-ID variables.
4. The significant `student_id` coefficient should not be interpreted substantively. It is likely an artifact and should not be used for decision-making.

## 5. Key Patterns, Relationships, and Anomalies
1. The dataset appears clean but weakly informative.
2. The main anomaly is an implausible relationship between GPA and `student_id`.
3. Common-sense academic drivers such as study hours and absences do not show detectable signal here, which is unusual and may indicate synthetic data, omitted variables, or intentionally noisy generation.
4. Because GPA is capped at 4.0, a censored or ordinal formulation could be argued in a richer dataset. In this dataset, that change would not solve the signal problem.

## 6. Conclusion
This dataset supports descriptive analysis but does not support a strong predictive model of GPA from the observed behavioral variables. The only notable association is with `student_id`, which should be treated as non-causal and likely spurious. The rigorous conclusion is therefore negative: after checking data quality, visual structure, cross-validated performance, and OLS assumptions, there is no evidence that the available substantive predictors explain GPA in a practically useful way.

## 7. Recommendations
1. Drop `student_id` from any downstream modeling pipeline.
2. Collect more meaningful covariates if GPA prediction is the goal, such as prior GPA, course load, socioeconomic indicators, attendance detail, major, exam scores, and semester information.
3. If this is synthetic data, review the generation logic because the identifier appears more informative than the behavioral features.

