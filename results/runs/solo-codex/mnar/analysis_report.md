# Dataset Analysis Report

## Executive Summary

This report analyzes `dataset.csv` (1000 rows, 8 raw columns) with a focus on data quality, exploratory structure, missingness, and whether the tabular features support meaningful predictive modeling.

The most important finding is that `reported_annual_income` is missing for 49.5% of respondents. That missingness is not consistent with a purely random process: older respondents, respondents with more education, and respondents with higher satisfaction were more likely to have missing income. Because of that, any model using only observed income values should be interpreted as a conditional analysis on responders, not as fully representative of the entire sample.

Income is moderately structured by age and education and can be modeled with modest predictive skill. Satisfaction, by contrast, is only weakly predictable from the available variables. The data support descriptive findings more strongly than causal claims.

## 1. Data Loading and Inspection

- Rows: 1000
- Raw columns: 8
- Derived analysis columns added: 1 (`income_missing`)
- Duplicate full rows: 0
- Duplicate `respondent_id` values: 0

### Column Overview
```
                          dtype  non_null_count  null_count  null_pct  n_unique
respondent_id             int64            1000           0       0.0      1000
age                       int64            1000           0       0.0        58
gender                      str            1000           0       0.0         3
region                      str            1000           0       0.0         5
education_years           int64            1000           0       0.0        14
reported_annual_income  float64             505         495      49.5       301
satisfaction_score      float64            1000           0       0.0        82
num_children              int64            1000           0       0.0         5
income_missing            int64            1000           0       0.0         2
```

### Numeric Summary
```
                         count       mean        std      min      25%      50%      75%       max
age                     1000.0     41.805     11.554     18.0     34.0     42.0     49.0      80.0
education_years         1000.0     14.322      2.279      8.0     13.0     14.0     16.0      21.0
reported_annual_income   505.0  48994.257  12552.628  15000.0  39800.0  48600.0  58200.0  102800.0
satisfaction_score      1000.0      6.975      1.943      1.0      5.6      7.0      8.4      10.0
num_children            1000.0      1.460      1.172      0.0      1.0      1.0      2.0       4.0
```

### Categorical Counts
```
           gender  region
F           496.0     0.0
M           464.0     0.0
Other        40.0     0.0
Southeast     0.0   230.0
Southwest     0.0   211.0
West          0.0   201.0
Northeast     0.0   182.0
Midwest       0.0   176.0
```

### Basic Validity Checks
```
age_out_of_expected_range    0
education_years_negative     0
income_non_positive          0
satisfaction_out_of_1_10     0
num_children_negative        0
```

No obvious impossible values were found in the observed fields. The key quality issue is missing income, not invalid ranges.

## 2. Exploratory Data Analysis

### Distribution Shape
```
                         skew  kurtosis
age                     0.185    -0.213
education_years         0.016     0.223
reported_annual_income  0.176     0.082
satisfaction_score     -0.284    -0.558
num_children            0.440    -0.680
```

`reported_annual_income` is only mildly right-skewed, so modeling it on the raw scale is defensible for interpretability. `satisfaction_score` is bounded between 1 and 10 and slightly left-skewed, but not strongly enough to make basic linear diagnostics meaningless.

### Correlations
```
                          age  education_years  reported_annual_income  satisfaction_score  num_children
age                     1.000            0.469                   0.363               0.037         0.006
education_years         0.469            1.000                   0.369              -0.001        -0.004
reported_annual_income  0.363            0.369                   1.000               0.122        -0.086
satisfaction_score      0.037           -0.001                   0.122               1.000        -0.043
num_children            0.006           -0.004                  -0.086              -0.043         1.000
```

Key bivariate patterns:

- Income rises with age (`r = 0.363`) and education (`r = 0.369`).
- Satisfaction has only a weak linear association with income (`r = 0.122`) and is nearly unrelated to age and education.
- Number of children is weakly negatively associated with income and satisfaction.

### Outlier Review
```
                  feature       q1       q3      iqr  lower_fence  upper_fence  n_outliers
0                     age     34.0     49.0     15.0         11.5         71.5           7
1         education_years     13.0     16.0      3.0          8.5         20.5          14
2  reported_annual_income  39800.0  58200.0  18400.0      12200.0      85800.0           1
3      satisfaction_score      5.6      8.4      2.8          1.4         12.6           2
4            num_children      1.0      2.0      1.0         -0.5          3.5          58
```

The IQR rule flags some high-child-count observations as outliers because `num_children` is discrete and concentrated at low values. Those are not necessarily data errors. Income has only one IQR-based outlier, so extreme-income distortion is limited.

### Saved Visualizations

- `plots/missingness_by_column.png`
- `plots/numeric_distributions.png`
- `plots/categorical_counts.png`
- `plots/correlation_heatmap.png`
- `plots/income_boxplots.png`
- `plots/income_scatter_relationships.png`
- `plots/satisfaction_boxplots.png`
- `plots/satisfaction_scatter_relationships.png`
- `plots/income_model_diagnostics.png`
- `plots/satisfaction_model_diagnostics.png`

## 3. Missing-Data Investigation

Because nearly half the income values are missing, missingness itself was modeled.

### Group Means by Income Missingness
```
                   age  education_years  satisfaction_score  num_children
income_missing                                                           
0               40.378            14.03               6.794         1.455
1               43.261            14.62               7.161         1.465
```

### Two-Sample Tests
```
             variable  welch_t_pvalue  mannwhitney_pvalue
0                 age        0.000076            0.000075
1     education_years        0.000039            0.000100
2  satisfaction_score        0.002753            0.003664
3        num_children        0.901312            0.915469
```

### Logistic Regression for Income Missingness
```
                         Coef.  Std.Err.       z   P>|z|  [0.025  0.975]
Intercept              -2.4559    0.5168 -4.7518  0.0000 -3.4688 -1.4429
C(gender)[T.M]         -0.2279    0.1330 -1.7142  0.0865 -0.4885  0.0327
C(gender)[T.Other]     -0.8688    0.3554 -2.4447  0.0145 -1.5653 -0.1723
C(region)[T.Northeast] -0.2353    0.2177 -1.0808  0.2798 -0.6619  0.1914
C(region)[T.Southeast]  0.2079    0.2046  1.0163  0.3095 -0.1931  0.6089
C(region)[T.Southwest]  0.0390    0.2087  0.1868  0.8518 -0.3701  0.4481
C(region)[T.West]       0.2296    0.2124  1.0808  0.2798 -0.1868  0.6459
age                     0.0154    0.0064  2.3926  0.0167  0.0028  0.0280
education_years         0.0808    0.0326  2.4781  0.0132  0.0169  0.1446
satisfaction_score      0.1003    0.0337  2.9799  0.0029  0.0343  0.1663
num_children            0.0108    0.0554  0.1944  0.8459 -0.0978  0.1193
```

Odds ratios:
```
Intercept                 0.086
C(gender)[T.M]            0.796
C(gender)[T.Other]        0.419
C(region)[T.Northeast]    0.790
C(region)[T.Southeast]    1.231
C(region)[T.Southwest]    1.040
C(region)[T.West]         1.258
age                       1.016
education_years           1.084
satisfaction_score        1.106
num_children              1.011
```

Interpretation:

- Higher age, education, and satisfaction are each associated with higher odds of missing income after adjusting for the other observed features.
- Respondents in the `Other` gender category were less likely than the reference group to have missing income.
- Region effects were not statistically strong in this model.
- Pseudo R-squared is low (0.033), so the observed variables explain only part of the missingness process, but they explain enough to reject a naive MCAR interpretation.

This is the central modeling caveat in the dataset.

## 4. Income Modeling

Income was modeled only on rows where income is observed (`n = 505`), with OLS for inference and cross-validated machine-learning models for predictive validation.

### OLS: `reported_annual_income ~ age + education_years + num_children + gender + region`
```
                             Coef.   Std.Err.       t   P>|t|      [0.025      0.975]
Intercept               19030.9988  3456.2324  5.5063  0.0000  12240.3039  25821.6936
C(gender)[T.M]            -42.2170  1043.6631 -0.0405  0.9678  -2092.7729   2008.3389
C(gender)[T.Other]       4277.4897  2293.2465  1.8653  0.0627   -228.2077   8783.1870
C(region)[T.Northeast]   -292.8508  1615.4123 -0.1813  0.8562  -3466.7612   2881.0597
C(region)[T.Southeast]    438.1389  1603.3983  0.2733  0.7848  -2712.1667   3588.4446
C(region)[T.Southwest]    186.6126  1618.7028  0.1153  0.9083  -2993.7629   3366.9881
C(region)[T.West]       -3103.9158  1668.3255 -1.8605  0.0634  -6381.7884    173.9568
age                       271.7250    49.9054  5.4448  0.0000    173.6725    369.7776
education_years          1472.8262   248.1427  5.9354  0.0000    985.2833   1960.3690
num_children             -948.4747   432.4454 -2.1933  0.0288  -1798.1295    -98.8199
```

Model fit:

- R-squared: 0.210
- Adjusted R-squared: 0.196
- Residual normality Shapiro p-value: 0.028573
- Breusch-Pagan p-value for heteroskedasticity: 0.854274

Interpretation:

- Age and education are the strongest positive predictors of reported income.
- Each additional child is associated with lower reported income, conditional on the other variables.
- Region and gender effects are comparatively weak and mostly not statistically distinguishable from zero in this sample.
- Residuals are not perfectly normal, but the deviation is modest in the plots and there is no strong evidence of heteroskedasticity.

### Cross-Validated Predictive Performance
```
                   model  mean_r2  std_r2   mean_rmse  std_rmse
0       LinearRegression   0.1573  0.0538  11385.9498  665.2758
1  RandomForestRegressor   0.1071  0.0536  11718.4583  633.0691
```

The cross-validated results show modest predictive skill. Linear regression and random forest are broadly similar, which suggests the signal is mostly simple and additive rather than strongly nonlinear.

### Income by Group
Income by gender:
```
        count      mean   median       std
gender                                    
F         236  48108.90  47350.0  12381.38
M         242  49424.79  49100.0  12702.11
Other      27  52874.07  56000.0  12199.04
```

Income by region:
```
           count      mean   median       std
region                                       
Midwest       91  49801.10  49000.0  13116.95
Northeast    106  48799.06  48000.0  11210.64
Southeast    108  50080.56  49450.0  12345.97
Southwest    107  49611.21  49500.0  13418.60
West          93  46455.91  47300.0  12557.36
```

## 5. Satisfaction Modeling

Satisfaction was analyzed in two ways:

1. A full-sample OLS model without income, avoiding the missing-data problem.
2. A complete-case OLS model adding log-income, used only as a conditional analysis on income responders.

### OLS Without Income (All Rows)
```
                         Coef.  Std.Err.        t   P>|t|  [0.025  0.975]
Intercept               6.9274    0.4274  16.2072  0.0000  6.0886  7.7661
C(gender)[T.M]          0.0738    0.1265   0.5836  0.5597 -0.1745  0.3222
C(gender)[T.Other]      0.3164    0.3208   0.9865  0.3241 -0.3130  0.9459
C(region)[T.Northeast]  0.0136    0.2064   0.0661  0.9473 -0.3913  0.4186
C(region)[T.Southeast]  0.0738    0.1951   0.3782  0.7053 -0.3090  0.4566
C(region)[T.Southwest]  0.0862    0.1991   0.4327  0.6653 -0.3046  0.4769
C(region)[T.West]       0.1826    0.2020   0.9039  0.3663 -0.2139  0.5791
age                     0.0083    0.0061   1.3693  0.1712 -0.0036  0.0203
education_years        -0.0221    0.0307  -0.7179  0.4730 -0.0823  0.0382
num_children           -0.0722    0.0527  -1.3708  0.1707 -0.1755  0.0312
```

Model fit:

- R-squared: 0.006
- Adjusted R-squared: -0.003
- Residual normality Shapiro p-value: 0.000000
- Breusch-Pagan p-value: 0.275025

This model explains almost none of the variance in satisfaction.

### OLS With Log-Income (Income Observed Only)
```
                         Coef.  Std.Err.       t   P>|t|   [0.025  0.975]
Intercept              -3.6319    3.7407 -0.9709  0.3321 -10.9814  3.7177
C(gender)[T.M]          0.3650    0.1854  1.9687  0.0495   0.0007  0.7293
C(gender)[T.Other]      0.2506    0.4086  0.6132  0.5400  -0.5523  1.0534
C(region)[T.Northeast]  0.0082    0.2870  0.0287  0.9771  -0.5556  0.5720
C(region)[T.Southeast]  0.1094    0.2849  0.3840  0.7012  -0.4503  0.6690
C(region)[T.Southwest]  0.0387    0.2875  0.1344  0.8931  -0.5263  0.6036
C(region)[T.West]       0.3860    0.2975  1.2976  0.1950  -0.1985  0.9704
age                    -0.0017    0.0091 -0.1863  0.8523  -0.0196  0.0162
education_years        -0.0890    0.0454 -1.9593  0.0506  -0.1783  0.0002
num_children           -0.1320    0.0771 -1.7124  0.0875  -0.2835  0.0195
log_income              1.0816    0.3642  2.9702  0.0031   0.3661  1.7971
```

Model fit:

- Observations: 505
- R-squared: 0.038
- Adjusted R-squared: 0.019
- Residual normality Shapiro p-value: 0.000040
- Breusch-Pagan p-value: 0.576340

Interpretation:

- Conditional on income being observed, higher income is associated with higher satisfaction.
- The effect size is statistically detectable but practically limited because overall explanatory power remains low.
- Education becomes slightly negative when income enters, which is consistent with correlated predictors and weak net effects rather than a strong substantive relationship.

### Cross-Validated Predictive Performance
```
                   model  mean_r2  std_r2  mean_rmse  std_rmse
0         DummyRegressor  -0.0067  0.0051     1.9405    0.1266
1       LinearRegression  -0.0079  0.0248     1.9413    0.1237
2  RandomForestRegressor  -0.0635  0.0277     1.9948    0.1390
```

Even after imputing income and including a missingness indicator, predictive performance is weak. The available features do not strongly determine satisfaction in this dataset.

### Satisfaction by Group
Satisfaction by gender:
```
        count  mean  median   std
gender                           
F         496  6.92    7.00  1.94
M         464  7.01    7.05  1.96
Other      40  7.25    7.20  1.78
```

Satisfaction by region:
```
           count  mean  median   std
region                              
Midwest      176  6.91    7.00  1.93
Northeast    182  6.92    7.10  2.13
Southeast    230  6.97    6.85  1.86
Southwest    211  6.99    7.10  1.99
West         201  7.07    7.20  1.84
```

## 6. Assumptions and Validation

The following checks were used to avoid over-claiming:

- Missingness was explicitly modeled rather than ignored.
- OLS residual plots and Q-Q plots were generated for the income and satisfaction models.
- Breusch-Pagan tests were used to check heteroskedasticity.
- Shapiro-Wilk tests were used to check residual normality. With sample sizes this large, even mild deviations can produce small p-values, so the diagnostic plots matter more than the p-values alone.
- Predictive models were validated with 5-fold cross-validation instead of reporting in-sample fit only.

Modeling choices were therefore guided by both interpretability and validation:

- OLS was used because the strongest relationships are approximately linear and the primary need is explanation.
- Random forest was used as a nonlinear benchmark. It did not materially outperform the linear baseline.
- Satisfaction was not modeled as an ordinal outcome here because the score behaves more like a dense bounded scale than a sparse ordered category, and the main result is low signal regardless.

## 7. Conclusions

1. The dataset is mostly clean in terms of ranges and duplicates, but it has a major missing-data problem in `reported_annual_income`.
2. Income missingness is associated with observed respondent characteristics, so analyses restricted to observed income are not safely representative of the whole sample.
3. Among respondents who reported income, age and education are the clearest positive correlates of income, while number of children has a modest negative association.
4. Satisfaction is only weakly explained by the observed variables. Income has a positive conditional association with satisfaction, but the total predictive power remains low.
5. There is limited evidence that more complex nonlinear models materially improve on simple linear structure.

## 8. Limitations

- The dataset is cross-sectional, so none of these associations should be interpreted causally.
- High income missingness likely biases complete-case estimates if nonresponse depends on unobserved factors as well as observed ones.
- Satisfaction is bounded and possibly subjective, so small coefficient estimates should not be over-interpreted.
- Without domain context or a designated target variable, the modeling section is exploratory rather than productized.
