# Dataset Analysis Report

## 1. Data loading and inspection
The dataset contains **600 rows** and **7 columns**. It is a customer-level table with one identifier (`customer_id`) and six quantitative variables.

- Missing values: **0**
- Duplicate rows: **0**
- Duplicate customer IDs: **0**

### Column types
|  | value |
| --- | --- |
| customer_id | str |
| avg_order_value | float64 |
| purchase_frequency_monthly | float64 |
| days_since_last_purchase | float64 |
| total_lifetime_spend | float64 |
| support_contacts | int64 |
| account_age_months | int64 |

### Descriptive statistics
|  | count | unique | top | freq | mean | std | min | 25% | 50% | 75% | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| customer_id | 600 | 600 | C-00110 | 1 | nan | nan | nan | nan | nan | nan | nan |
| avg_order_value | 600.0 | nan | nan | nan | 73.27166666666666 | 38.91017820359193 | 16.16 | 27.7875 | 75.11500000000001 | 117.13749999999999 | 128.76 |
| purchase_frequency_monthly | 600.0 | nan | nan | nan | 8.681083333333333 | 5.182887889118786 | 0.1 | 4.095 | 7.82 | 14.0925 | 18.41 |
| days_since_last_purchase | 600.0 | nan | nan | nan | 23.30385 | 16.557951038150918 | 0.0 | 7.5825 | 19.57 | 42.8425 | 54.26 |
| total_lifetime_spend | 600.0 | nan | nan | nan | 2681.8412 | 679.5603244091568 | 1632.24 | 2178.8525 | 2347.8599999999997 | 3458.5424999999996 | 4299.18 |
| support_contacts | 600.0 | nan | nan | nan | 1.6416666666666666 | 1.3588013556424334 | 0.0 | 0.75 | 1.0 | 3.0 | 6.0 |
| account_age_months | 600.0 | nan | nan | nan | 31.101666666666667 | 17.08325866943522 | 1.0 | 16.0 | 32.0 | 46.0 | 59.0 |

### Skewness
|  | value |
| --- | --- |
| total_lifetime_spend | 0.634 |
| support_contacts | 0.557 |
| days_since_last_purchase | 0.319 |
| purchase_frequency_monthly | 0.22 |
| avg_order_value | -0.064 |
| account_age_months | -0.101 |

### Kurtosis
|  | value |
| --- | --- |
| support_contacts | -0.33 |
| account_age_months | -1.192 |
| total_lifetime_spend | -1.232 |
| purchase_frequency_monthly | -1.271 |
| days_since_last_purchase | -1.399 |
| avg_order_value | -1.471 |

### IQR-based outlier counts
| column | iqr_outliers | lower | upper |
| --- | --- | --- | --- |
| avg_order_value | 0 | -106.237 | 251.162 |
| purchase_frequency_monthly | 0 | -10.901 | 29.089 |
| days_since_last_purchase | 0 | -45.308 | 95.733 |
| total_lifetime_spend | 0 | 259.318 | 5378.077 |
| support_contacts | 0 | -2.625 | 6.375 |
| account_age_months | 0 | -29.0 | 91.0 |

## 2. Exploratory data analysis
The core EDA plots were saved in `./plots/`:

- `correlation_heatmap.png`
- `numeric_distributions.png`
- `numeric_boxplots.png`
- `target_relationships.png`
- `selected_pairplot.png`

Key distributional findings:

- The dataset is unusually clean: no missing data, no duplicate IDs, and no extreme z-score outliers in most continuous variables.
- `total_lifetime_spend` is only moderately right-skewed (skew = 0.634), so a raw-scale regression is not automatically inappropriate.
- `support_contacts` is discrete and slightly right-skewed; it has the only notable extreme values.
- Most variables have negative kurtosis, indicating flatter-than-normal distributions rather than heavy tails.

### Correlation matrix
|  | avg_order_value | purchase_frequency_monthly | days_since_last_purchase | total_lifetime_spend | support_contacts | account_age_months |
| --- | --- | --- | --- | --- | --- | --- |
| avg_order_value | 1.0 | -0.946 | 0.961 | -0.002 | 0.001 | 0.029 |
| purchase_frequency_monthly | -0.946 | 1.0 | -0.908 | -0.076 | 0.002 | -0.03 |
| days_since_last_purchase | 0.961 | -0.908 | 1.0 | -0.18 | -0.006 | 0.014 |
| total_lifetime_spend | -0.002 | -0.076 | -0.18 | 1.0 | 0.015 | 0.026 |
| support_contacts | 0.001 | 0.002 | -0.006 | 0.015 | 1.0 | -0.028 |
| account_age_months | 0.029 | -0.03 | 0.014 | 0.026 | -0.028 | 1.0 |

## 3. Key patterns, relationships, and anomalies
Several relationships are strong enough to shape the analysis:

- `avg_order_value` and `days_since_last_purchase` are strongly positively correlated (0.961).
- `avg_order_value` and `purchase_frequency_monthly` are strongly negatively correlated (-0.946).
- `purchase_frequency_monthly` and `days_since_last_purchase` are also strongly negatively correlated (-0.908).
- Pairwise linear correlations with `total_lifetime_spend` are weak to modest; the strongest is with `days_since_last_purchase` (days_since_last_purchase = 0.180 in absolute value).

Interpretation:

- The behavioral predictors are highly collinear. That makes coefficient-based linear interpretation unstable.
- Weak pairwise correlation with lifetime spend does **not** imply the outcome is unpredictable; it suggests the relationship may be nonlinear or interaction-driven.
- The combination of very clean data and strong geometric structure is somewhat unusual for raw operational data, so any business interpretation should be made cautiously.

## 4. Supervised modeling
There is no explicit label column beyond `total_lifetime_spend`, so I treated lifetime spend as the most defensible business outcome to model. Features used:

- `avg_order_value`
- `purchase_frequency_monthly`
- `days_since_last_purchase`
- `support_contacts`
- `account_age_months`

Models were evaluated with **10-fold cross-validation** and a held-out **20% test split**.

| model | cv_r2_mean | cv_r2_std | cv_mae_mean | cv_rmse_mean | test_r2 | test_mae | test_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random forest | 0.909 | 0.016 | 164.269 | 203.212 | 0.897 | 177.818 | 219.84 |
| Polynomial regression (degree 2) | 0.866 | 0.025 | 197.266 | 246.45 | 0.849 | 212.656 | 266.514 |
| Linear regression | 0.455 | 0.042 | 402.021 | 498.242 | 0.437 | 421.332 | 513.882 |

Modeling takeaways:

- A plain linear regression performs only moderately well, with mean CV R² of **0.455**.
- Adding second-order interactions/nonlinear terms sharply improves performance: polynomial regression reaches mean CV R² of **0.866**.
- The best predictive performance comes from a random forest, with mean CV R² of **0.909** and test R² of **0.897**.
- This pattern strongly supports a nonlinear data-generating process.

### Random forest permutation importance
|  | value |
| --- | --- |
| avg_order_value | 0.988 |
| days_since_last_purchase | 0.24 |
| purchase_frequency_monthly | -0.0 |
| support_contacts | -0.001 |
| account_age_months | -0.001 |

Supporting plots:

- `rf_permutation_importance.png`
- `rf_actual_vs_predicted.png`
- `rf_residual_diagnostics.png`

## 5. Assumption checks and validation
I explicitly checked linear model assumptions because they matter for interpretation.

### Multicollinearity
|  | value |
| --- | --- |
| avg_order_value | 21.623 |
| days_since_last_purchase | 13.019 |
| purchase_frequency_monthly | 9.486 |
| account_age_months | 1.004 |
| support_contacts | 1.002 |

- VIF values above 5 are usually concerning, and above 10 are severe.
- Here, the main behavioral predictors clearly exceed those thresholds, so OLS coefficients are not stable enough for strong causal-style interpretation.

### Residual diagnostics for OLS
- Breusch-Pagan test p-value: **0.001013**
- Shapiro-Wilk test p-value: **0.5412**
- High-influence points using Cook's distance > 4/n: **24**

See `ols_diagnostics.png`.

Interpretation:

- The residual diagnostics should be read in combination with the VIF results: even if residual shape were acceptable, multicollinearity still limits interpretability.
- The strong performance gap between linear and nonlinear models indicates that linearity is the main misspecification, not just noise.
- For prediction, the random forest is preferable because it does not require linearity or normal residuals.

## 6. Unsupervised segmentation
Since the dataset has no explicit class label and exhibits strong structure, I also ran KMeans clustering on the standardized numeric variables.

### Cluster validation
| k | silhouette_score | inertia |
| --- | --- | --- |
| 2 | 0.392 | 2155.16 |
| 3 | 0.453 | 1325.285 |
| 4 | 0.393 | 1165.756 |
| 5 | 0.36 | 1011.66 |
| 6 | 0.313 | 870.146 |

- The best silhouette score occurs at **k = 3**, which supports a three-segment solution.

### Mean profile by cluster
| cluster | avg_order_value | purchase_frequency_monthly | days_since_last_purchase | support_contacts | account_age_months | total_lifetime_spend |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 74.93 | 7.9 | 19.64 | 1.71 | 32.12 | 3601.25 |
| 1 | 25.11 | 15.09 | 5.46 | 1.6 | 30.05 | 2248.15 |
| 0 | 119.78 | 3.05 | 44.81 | 1.61 | 31.14 | 2196.12 |

Supporting plots:

- `cluster_silhouette_scores.png`
- `cluster_pca_projection.png`

Broad segment interpretation:

- One segment has high lifetime spend with relatively high order values and longer recency.
- Another segment appears lower-value and more purchase-frequent.
- A third segment sits between them, suggesting the data may encode distinct customer regimes rather than one smooth population.

## 7. Conclusions
Main conclusions from the analysis:

- The dataset is structurally clean and numerically well-behaved, but not simple.
- Behavioral features are strongly interdependent, so naive coefficient interpretation is unreliable.
- `total_lifetime_spend` is predictable, but mainly through **nonlinear** relationships and interactions rather than simple pairwise linear trends.
- A random forest is the strongest predictive model among those tested.
- A 3-cluster segmentation is also well supported and may be more actionable than a single global linear model.

Recommended next steps if this were a production analysis:

1. Confirm how `total_lifetime_spend` was computed and whether any leakage exists relative to the behavioral features.
2. Add time-based variables or cohort metadata; `account_age_months` alone explains little.
3. If interpretability matters, fit a regularized GAM or monotonic boosting model and compare it with the random forest.
4. Validate the segmentation externally against retention, margin, or churn outcomes before operationalizing it.
