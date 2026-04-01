# Dataset Analysis Report

## 1. Scope and approach
This analysis treats the file as an unknown dataset rather than assuming it is clean or informative. The workflow covered data quality checks, descriptive statistics, visual exploratory analysis, inferential testing, predictive modeling, and model diagnostics. The main modeling question was whether the available covariates can explain or predict `gpa`.

## 2. Dataset overview
- Rows: 600
- Columns: 7
- Numeric columns: 7
- Missing values: 0
- Duplicate rows: 0
- Duplicate `student_id` values: 0

`student_id` was treated as an identifier and excluded from modeling.

### Column types and quality
| index | dtype | missing_count | missing_pct | unique_values |
| --- | --- | --- | --- | --- |
| student_id | int64 | 0 | 0.0000 | 600 |
| weekly_study_hours | float64 | 0 | 0.0000 | 167 |
| gpa | float64 | 0 | 0.0000 | 197 |
| extracurriculars | int64 | 0 | 0.0000 | 6 |
| commute_minutes | int64 | 0 | 0.0000 | 70 |
| part_time_job_hours | float64 | 0 | 0.0000 | 190 |
| absences | int64 | 0 | 0.0000 | 10 |

### Descriptive statistics
| index | count | mean | std | min | 25% | 50% | 75% | max | iqr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| student_id | 600.000 | 300.500 | 173.349 | 1.000 | 150.750 | 300.500 | 450.250 | 600.000 | 299.500 |
| weekly_study_hours | 600.000 | 11.481 | 4.071 | 0.000 | 9.000 | 11.400 | 14.600 | 26.000 | 5.600 |
| gpa | 600.000 | 3.142 | 0.582 | 1.550 | 2.758 | 3.150 | 3.572 | 4.000 | 0.815 |
| extracurriculars | 600.000 | 2.527 | 1.722 | 0.000 | 1.000 | 3.000 | 4.000 | 5.000 | 3.000 |
| commute_minutes | 600.000 | 30.152 | 14.615 | 0.000 | 20.000 | 30.000 | 40.000 | 80.000 | 20.000 |
| part_time_job_hours | 600.000 | 8.159 | 5.477 | 0.000 | 3.900 | 7.950 | 11.725 | 27.200 | 7.825 |
| absences | 600.000 | 2.893 | 1.692 | 0.000 | 2.000 | 3.000 | 4.000 | 9.000 | 2.000 |

## 3. Exploratory data analysis
The variables are all numeric, mostly centered in plausible ranges, and only mildly skewed. A few values exceed 3 standard deviations from their column means, but the counts are small and there is no immediate sign of corrupted records.

### Potential outliers by z-score threshold (> 3 SD)
| column | count_gt_3sd |
| --- | --- |
| weekly_study_hours | 1 |
| gpa | 0 |
| extracurriculars | 0 |
| commute_minutes | 3 |
| part_time_job_hours | 2 |
| absences | 5 |

### Correlation matrix
| index | weekly_study_hours | gpa | extracurriculars | commute_minutes | part_time_job_hours | absences |
| --- | --- | --- | --- | --- | --- | --- |
| weekly_study_hours | 1.000 | -0.003 | 0.030 | 0.024 | -0.054 | 0.042 |
| gpa | -0.003 | 1.000 | -0.008 | 0.058 | 0.003 | -0.018 |
| extracurriculars | 0.030 | -0.008 | 1.000 | -0.034 | 0.004 | -0.012 |
| commute_minutes | 0.024 | 0.058 | -0.034 | 1.000 | 0.024 | -0.023 |
| part_time_job_hours | -0.054 | 0.003 | 0.004 | 0.024 | 1.000 | -0.020 |
| absences | 0.042 | -0.018 | -0.012 | -0.023 | -0.020 | 1.000 |

### Monotonic association with GPA (Spearman)
| feature | spearman_rho | p_value |
| --- | --- | --- |
| commute_minutes | 0.0412 | 0.3132 |
| absences | -0.0198 | 0.6284 |
| weekly_study_hours | 0.0128 | 0.7552 |
| part_time_job_hours | 0.0066 | 0.8720 |
| extracurriculars | -0.0049 | 0.9046 |

### Group comparison for extracurricular participation
- One-way ANOVA on `gpa ~ extracurriculars`: F = 0.092, p = 0.993
- Kruskal-Wallis on `gpa ~ extracurriculars`: H = 0.344, p = 0.997

## 4. Modeling strategy
The response variable `gpa` is continuous, so regression is appropriate if signal exists. I compared a mean-only baseline against:

- Ordinary least squares linear regression
- Ridge regression
- Lasso regression
- Degree-2 polynomial features with ridge regularization
- Random forest regression

All models were evaluated using 10-fold cross-validation with shuffled splits and a fixed random seed.

### Cross-validated model performance
| model | mean_cv_r2 | std_cv_r2 | mean_cv_rmse | std_cv_rmse |
| --- | --- | --- | --- | --- |
| DummyMean | -0.0329 | 0.0324 | 0.5828 | 0.0312 |
| Lasso | -0.0367 | 0.0336 | 0.5838 | 0.0300 |
| Ridge | -0.0379 | 0.0356 | 0.5841 | 0.0298 |
| PolynomialRidge | -0.0432 | 0.0386 | 0.5856 | 0.0291 |
| LinearRegression | -0.0507 | 0.0456 | 0.5875 | 0.0271 |
| RandomForest | -0.1240 | 0.1020 | 0.6064 | 0.0181 |

### Interpretation
The model comparison is the central result. Every predictive model achieved negative cross-validated R^2, meaning each one performed worse than predicting the training-fold mean GPA for every observation in the test fold. This is consistent with the near-zero correlations seen during EDA and indicates that the supplied features do not contain stable predictive information for GPA in this sample.

## 5. OLS fit and assumptions
Although the cross-validated results already argue against useful prediction, I still fit an OLS model to inspect assumptions and coefficient behavior.

### OLS coefficients
| index | Coef. | Std.Err. | t | P>|t| | [0.025 | 0.975] |
| --- | --- | --- | --- | --- | --- | --- |
| const | 3.0982 | 0.1078 | 28.7392 | 0.0000 | 2.8865 | 3.3100 |
| weekly_study_hours | -0.0005 | 0.0059 | -0.0843 | 0.9329 | -0.0120 | 0.0110 |
| extracurriculars | -0.0019 | 0.0139 | -0.1383 | 0.8901 | -0.0292 | 0.0253 |
| commute_minutes | 0.0023 | 0.0016 | 1.4072 | 0.1599 | -0.0009 | 0.0055 |
| part_time_job_hours | 0.0001 | 0.0044 | 0.0216 | 0.9828 | -0.0085 | 0.0087 |
| absences | -0.0056 | 0.0141 | -0.3941 | 0.6936 | -0.0333 | 0.0222 |

### Global fit
- R-squared: 0.0037
- Adjusted R-squared: -0.0047
- F-statistic p-value: 0.8197

### Assumption checks
- Breusch-Pagan heteroskedasticity test: LM p = 0.2668, F p = 0.2680
- Ramsey RESET specification test: F = 0.7796, p = 0.3776
- Shapiro-Wilk residual normality test: W = 0.9722, p = 2.966e-09
- D'Agostino-Pearson residual normality test: statistic = 21.5176, p = 2.126e-05
- Maximum Cook's distance: 0.0200
- Observations with Cook's distance > 4/n: 25
- Observations with |studentized residual| > 3: 0

### Multicollinearity
| feature | vif |
| --- | --- |
| const | 20.459 |
| weekly_study_hours | 1.006 |
| extracurriculars | 1.002 |
| commute_minutes | 1.003 |
| part_time_job_hours | 1.004 |
| absences | 1.003 |

### Assumption summary
- Multicollinearity is negligible: all feature VIF values are essentially 1.
- There is no evidence of strong heteroskedasticity.
- The RESET test does not suggest obvious omitted nonlinear structure detectable by this diagnostic.
- Residual normality tests reject exact normality, but with n=600 these tests are sensitive to mild deviations. The Q-Q plot shows only modest tail departures, likely helped by the bounded 0 to 4 GPA scale. This matters less than the larger issue: the model has almost no explanatory power.

## 6. Key findings
- The dataset has 600 rows and 7 columns with no missing values, duplicate rows, or duplicate `student_id` values.
- All observed features show near-zero linear and monotonic association with GPA; the largest absolute Pearson correlation with `gpa` is 0.058 and the largest absolute Spearman rho is 0.041.
- One-way ANOVA and Kruskal-Wallis tests both show no evidence that GPA differs by extracurricular count (`p=0.993` and `p=0.997`).
- Out-of-sample validation indicates no predictive signal: the best model was `DummyMean` with mean 10-fold CV R^2 = -0.033 and RMSE = 0.583.
- Because every fitted model performs at or below a mean-only baseline, the defensible conclusion is that this dataset does not support useful GPA prediction from the provided variables.

## 7. Limitations and next steps
- The analysis can only use the variables present in the file. Important drivers of GPA may simply be absent.
- Negative out-of-sample R^2 across both linear and nonlinear models is evidence against useful prediction from the available columns, not evidence that GPA is inherently unpredictable.
- If this dataset was intended to encode real academic effects, it is worth checking how it was generated. The current structure is consistent with weakly related or effectively random predictors.

## 8. Generated artifacts
Plots were saved under `./plots/`:

- `missingness.png`
- `distributions.png`
- `boxplots.png`
- `correlation_heatmap.png`
- `gpa_vs_numeric_features.png`
- `gpa_by_extracurriculars.png`
- `model_comparison.png`
- `ols_diagnostics.png`
