# Dataset Analysis Report

## Scope
This report inspects `dataset.csv`, performs exploratory analysis, fits interpretable and predictive models where appropriate, checks core modeling assumptions, and summarizes evidence-based findings.

## Data Overview
- Rows: 1200
- Columns: 8
- Numeric columns: patient_id, age, severity_index, length_of_stay_days, recovery_score, readmitted
- Categorical columns: department, treatment
- Exact duplicate rows: 0
- Duplicate `patient_id` values: 0

### Column Summary
| index | dtype | non_null | nulls | null_pct | unique |
| --- | --- | --- | --- | --- | --- |
| patient_id | int64 | 1200 | 0 | 0.00 | 1200 |
| department | str | 1200 | 0 | 0.00 | 3 |
| age | int64 | 1200 | 0 | 0.00 | 41 |
| severity_index | float64 | 1200 | 0 | 0.00 | 581 |
| treatment | str | 1200 | 0 | 0.00 | 2 |
| length_of_stay_days | int64 | 1200 | 0 | 0.00 | 24 |
| recovery_score | float64 | 1200 | 0 | 0.00 | 293 |
| readmitted | int64 | 1200 | 0 | 0.00 | 2 |

### Numeric Summary
| index | count | mean | std | min | 25% | 50% | 75% | max | skew | kurtosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| patient_id | 1200.000 | 600.500 | 346.554 | 1.000 | 300.750 | 600.500 | 900.250 | 1200.000 | 0.000 | -1.200 |
| age | 1200.000 | 54.533 | 7.411 | 35.000 | 49.000 | 54.000 | 59.000 | 78.000 | 0.078 | -0.327 |
| severity_index | 1200.000 | 5.011 | 1.880 | 1.000 | 3.500 | 5.030 | 6.512 | 9.760 | 0.007 | -0.920 |
| length_of_stay_days | 1200.000 | 13.805 | 3.965 | 2.000 | 11.000 | 14.000 | 17.000 | 25.000 | 0.032 | -0.275 |
| recovery_score | 1200.000 | 67.462 | 6.948 | 47.900 | 62.400 | 67.450 | 72.225 | 88.500 | 0.074 | -0.280 |
| readmitted | 1200.000 | 0.108 | 0.311 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 2.524 | 4.375 |

### Categorical Summaries
#### `department`
| department | count | pct |
| --- | --- | --- |
| Orthopedics | 400 | 33.33 |
| Neurology | 400 | 33.33 |
| Cardiology | 400 | 33.33 |

#### `treatment`
| treatment | count | pct |
| --- | --- | --- |
| B | 629 | 52.42 |
| A | 571 | 47.58 |

### Data Quality Checks
- Missing values: none detected
- Outlier counts by 1.5*IQR rule: `age`=1, `severity_index`=0, `length_of_stay_days`=0, `recovery_score`=5, `readmitted`=130
- The dataset appears structurally clean: no nulls, no duplicate rows, balanced department counts, and unique patient identifiers.

## Exploratory Analysis
### Key Visualizations
- [`plots/numeric_distributions.png`](plots/numeric_distributions.png)
- [`plots/correlation_heatmap.png`](plots/correlation_heatmap.png)
- [`plots/recovery_group_boxplots.png`](plots/recovery_group_boxplots.png)
- [`plots/severity_group_boxplots.png`](plots/severity_group_boxplots.png)
- [`plots/severity_vs_recovery.png`](plots/severity_vs_recovery.png)
- [`plots/readmission_rates.png`](plots/readmission_rates.png)
- [`plots/ols_diagnostics.png`](plots/ols_diagnostics.png)

### Correlation Structure
| index | age | severity_index | length_of_stay_days | recovery_score | readmitted |
| --- | --- | --- | --- | --- | --- |
| age | 1.000 | 0.710 | 0.613 | -0.471 | 0.055 |
| severity_index | 0.710 | 1.000 | 0.853 | -0.658 | 0.011 |
| length_of_stay_days | 0.613 | 0.853 | 1.000 | -0.614 | 0.029 |
| recovery_score | -0.471 | -0.658 | -0.614 | 1.000 | -0.047 |
| readmitted | 0.055 | 0.011 | 0.029 | -0.047 | 1.000 |

### Group Means
| department | treatment | age | severity_index | length_of_stay_days | recovery_score | readmitted |
| --- | --- | --- | --- | --- | --- | --- |
| Cardiology | A | 49.242 | 2.990 | 9.091 | 76.621 | 0.091 |
| Cardiology | B | 48.959 | 3.031 | 10.605 | 71.521 | 0.112 |
| Neurology | A | 54.648 | 5.059 | 13.005 | 69.412 | 0.088 |
| Neurology | B | 54.716 | 5.004 | 14.349 | 65.218 | 0.124 |
| Orthopedics | A | 59.986 | 6.946 | 16.992 | 63.730 | 0.101 |
| Orthopedics | B | 59.500 | 7.210 | 18.864 | 59.975 | 0.159 |

### EDA Findings
- `recovery_score` declines strongly as `severity_index` rises (correlation -0.658).
- `severity_index` and `length_of_stay_days` are strongly positively correlated (0.853), which raises multicollinearity concerns for regression.
- Departments are highly stratified by severity: mean `severity_index` is 3.027 in Cardiology, 5.029 in Neurology, and 6.975 in Orthopedics.
- The raw treatment comparison is confounded: treatment A patients are older and sicker on average than treatment B patients (mean severity 6.116 vs 4.007).
- Readmission is rare (10.8% positive class) and shows only weak marginal correlations with measured predictors.

## Hypothesis Tests
- Welch t-test for `recovery_score` by treatment A vs B: statistic=-5.670, p-value=1.789e-08. Unadjusted recovery differs, but this should not be interpreted causally because treatment assignment is not balanced.
- Chi-square test for `readmitted` vs treatment: chi2=1.398, p-value=0.237. No statistically significant association was detected.

## Modeling
### 1. Recovery Score Regression
A linear model is appropriate as the primary inferential model because the target is continuous and the EDA suggests an approximately monotonic relationship with severity.
| index | Coef. | Std.Err. | t | P>|t| | [0.025 | 0.975] |
| --- | --- | --- | --- | --- | --- | --- |
| Intercept | 85.7834 | 1.2801 | 67.0108 | 0.0000 | 83.2718 | 88.2950 |
| C(treatment)[T.B] | -4.0034 | 0.3942 | -10.1557 | 0.0000 | -4.7769 | -3.2300 |
| C(department)[T.Neurology] | -0.2023 | 0.4809 | -0.4207 | 0.6740 | -1.1458 | 0.7411 |
| C(department)[T.Orthopedics] | 0.2082 | 0.7495 | 0.2778 | 0.7812 | -1.2623 | 1.6788 |
| age | -0.0096 | 0.0273 | -0.3496 | 0.7267 | -0.0632 | 0.0441 |
| severity_index | -2.8615 | 0.2231 | -12.8251 | 0.0000 | -3.2993 | -2.4238 |
| length_of_stay_days | -0.0989 | 0.0724 | -1.3662 | 0.1721 | -0.2410 | 0.0431 |

- OLS R-squared: 0.497
- Adjusted R-squared: 0.494
- Strongest adjusted predictor: `severity_index` coefficient -2.862 points per unit (p=2.285e-35).
- After adjustment, treatment B is associated with -4.003 lower recovery-score points than treatment A (p=2.682e-23). This is the opposite direction of the unadjusted mean difference, which is a strong sign of confounding.

#### Regression Validation
| model | cv_rmse_mean | cv_rmse_std | cv_mae_mean | cv_r2_mean |
| --- | --- | --- | --- | --- |
| LinearRegression | 4.953 | 0.275 | 3.982 | 0.487 |
| RandomForestRegressor | 5.275 | 0.292 | 4.210 | 0.418 |

#### Holdout Regression Performance
| model | test_rmse | test_mae | test_r2 |
| --- | --- | --- | --- |
| LinearRegression | 4.772 | 3.689 | 0.470 |
| RandomForestRegressor | 5.031 | 4.012 | 0.411 |

- Linear regression performs slightly better than the random forest on cross-validation, indicating that the main signal is already captured by a simple additive structure.

#### OLS Assumption Checks
- Residual normality: Jarque-Bera statistic=1.705, p-value=0.426. Residuals are close to normal.
- Heteroskedasticity: Breusch-Pagan p-value=0.504. No strong evidence of heteroskedasticity.
- Multicollinearity diagnostics (VIF): `Intercept`=80.59, `C(treatment)[T.B]`=1.91, `C(department)[T.Neurology]`=2.53, `C(department)[T.Orthopedics]`=6.14, `age`=2.02, `severity_index`=8.64, `length_of_stay_days`=4.05
- Most influential observation by Cook's distance: patient_id=88, Cook's D=0.0094. No single point dominates the fit.

### 2. Readmission Classification
A binary classification model was still fit because `readmitted` is a clinically relevant endpoint, but the data show weak signal and class imbalance.
#### Logistic Regression Odds Ratios
| index | odds_ratio | p_value | ci_lower | ci_upper |
| --- | --- | --- | --- | --- |
| Intercept | 0.0816 | 0.1716 | 0.0022 | 2.9640 |
| C(treatment)[T.B] | 1.3096 | 0.3225 | 0.7675 | 2.2344 |
| C(department)[T.Neurology] | 0.9569 | 0.8872 | 0.5204 | 1.7593 |
| C(department)[T.Orthopedics] | 1.0069 | 0.9888 | 0.3837 | 2.6427 |
| age | 1.0419 | 0.0220 | 1.0059 | 1.0792 |
| severity_index | 0.8379 | 0.2538 | 0.6184 | 1.1353 |
| length_of_stay_days | 1.0347 | 0.4687 | 0.9436 | 1.1346 |
| recovery_score | 0.9767 | 0.2143 | 0.9410 | 1.0137 |

#### Classification Validation
| model | cv_roc_auc_mean | cv_pr_auc_mean | cv_bal_acc_mean | cv_brier_mean |
| --- | --- | --- | --- | --- |
| LogisticRegression | 0.547 | 0.144 | 0.546 | 0.247 |
| RandomForestClassifier | 0.530 | 0.154 | 0.519 | 0.136 |

#### Holdout Classification Performance
| model | test_roc_auc | test_pr_auc | test_bal_acc | test_brier |
| --- | --- | --- | --- | --- |
| LogisticRegression | 0.573 | 0.138 | 0.583 | 0.242 |
| RandomForestClassifier | 0.546 | 0.139 | 0.503 | 0.131 |

- Baseline positive rate is 0.108; a useful classifier should meaningfully exceed this signal in ROC-AUC / PR-AUC. The fitted models do not.
- Neither logistic regression nor random forest produces strong discrimination. This suggests readmission is largely unexplained by the available variables.

#### Logistic Diagnostics
- Box-Tidwell linearity-in-logit p-values: `age`=0.515, `severity_index`=0.703, `length_of_stay_days`=0.122, `recovery_score`=0.498
- None of the measured predictors has a strong, stable odds-ratio signal after adjustment; confidence intervals remain close to 1 for most effects.

## Interpretation
- The dataset is unusually tidy and balanced across departments, which is consistent with either highly curated operational data or synthetic generation.
- Severity is the dominant driver of recovery outcomes. Higher severity tracks lower recovery and longer stays.
- Department-level differences in raw recovery mostly reflect differences in case mix; once severity and treatment are modeled, department terms lose significance.
- The treatment comparison is not randomized. Raw averages favor treatment B, but adjusted regression flips the sign, indicating severe confounding by baseline severity and department.
- Readmission cannot be modeled reliably from the current feature set. Any operational use of a readmission model built on these columns would be weakly supported.

## Caveats
- Cross-sectional observational data cannot establish causal treatment effects.
- `length_of_stay_days` may partly lie on the pathway from severity to recovery; including it improves prediction but may complicate causal interpretation.
- The absence of nulls and the near-regular structure should be treated cautiously; real hospital data are typically messier.

## Bottom Line
For `recovery_score`, a simple linear model is well supported and explains about half of the variance, with severity as the main negative predictor. For `readmitted`, the available variables provide little predictive value, and model performance remains weak after validation.