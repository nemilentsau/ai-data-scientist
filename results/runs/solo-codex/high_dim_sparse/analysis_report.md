# Dataset Analysis Report

## Executive Summary
This dataset contains **600 samples** and **104 columns**: 100 continuous gene-expression-style features (`gene_000` to `gene_099`), demographics (`age`, `sex`), a unique identifier (`sample_id`), and a binary target (`outcome`).

The data quality is unusually clean: there are **no missing values**, **no duplicated rows**, and **no duplicated sample IDs**. The target is nearly balanced (**315 positive**, **285 negative**), which supports standard discriminative modeling without rebalancing.

Across exploratory analysis and validated modeling, the main signal is concentrated in a small subset of features, especially **`gene_001`**, **`gene_000`**, and **`gene_002`**. These three variables dominate both the univariate tests and the predictive models, while `age` and `sex` add limited marginal signal.

## 1. Data Inspection

### Structure and Types
- Shape: **600 rows x 104 columns**
- Numeric columns: **102**
- Non-numeric columns: **2**
- Null values: **0**
- Duplicate rows: **0**
- Duplicate `sample_id` values: **0**

### Basic Statistics
| index | age | outcome |
| --- | --- | --- |
| count | 600.0000 | 600.0000 |
| mean | 54.6550 | 0.5250 |
| std | 11.8590 | 0.5000 |
| min | 20.0000 | 0.0000 |
| 25% | 46.0000 | 0.0000 |
| 50% | 55.0000 | 1.0000 |
| 75% | 63.0000 | 1.0000 |
| max | 85.0000 | 1.0000 |

Categorical distributions:
- `sex`: {'M': 305, 'F': 295}
- `sample_id`: all IDs are unique

Gene-level scale check:
- Gene means range from **-0.108** to **0.093**
- Gene standard deviations range from **0.904** to **1.100**

Interpretation: the gene features appear already standardized or close to standardized, with no immediate evidence of large-scale preprocessing artifacts.

## 2. Exploratory Data Analysis

### Visualizations
- Overview plot: `plots/overview.png`
- Top-feature boxplots: `plots/top_features_boxplot.png`
- Correlation heatmap: `plots/correlation_heatmap.png`
- PCA scatter: `plots/pca_scatter.png`

### Main EDA Findings
1. The class distribution is balanced and similar across sex categories, so sex is not a dominant confounder.
2. Age distributions overlap substantially by outcome, suggesting only weak univariate age signal.
3. PCA does **not** reveal a strong low-dimensional separation: PC1 and PC2 explain only **1.88%** and **1.83%** of total variance, respectively. This means outcome-related structure is embedded in a higher-dimensional space rather than a simple global cluster.
4. Signal is sparse rather than diffuse: only a handful of features show strong group differences.

### Top Univariate Associations with Outcome
| feature | mean_diff | cohens_d | p_value | q_value |
| --- | --- | --- | --- | --- |
| gene_001 | -0.8207 | -1.0123 | 0.0000 | 0.0000 |
| gene_000 | 0.7880 | 0.8902 | 0.0000 | 0.0000 |
| gene_002 | 0.5061 | 0.5037 | 0.0000 | 0.0000 |
| gene_089 | 0.2012 | 0.2027 | 0.0133 | 0.3362 |
| gene_093 | 0.1762 | 0.1852 | 0.0238 | 0.3978 |
| gene_053 | -0.1775 | -0.1791 | 0.0288 | 0.3978 |
| gene_017 | 0.1801 | 0.1755 | 0.0324 | 0.3978 |
| gene_096 | -0.1790 | -0.1727 | 0.0351 | 0.3978 |
| gene_098 | 0.1634 | 0.1660 | 0.0431 | 0.3978 |
| gene_027 | -0.1683 | -0.1653 | 0.0433 | 0.3978 |

Interpretation:
- `gene_001` is strongly **lower** in the positive class.
- `gene_000` and `gene_002` are higher in the positive class.
- After false-discovery-rate control, only the top few genes remain convincingly significant, which argues against a broad weak-signal pattern across all genes.

## 3. Patterns, Relationships, and Anomalies

### Relationships
- The strongest predictive genes are only weakly correlated with each other, which is useful because it means they carry complementary signal rather than redundant copies of the same measurement.
- `age` has only a small negative correlation with the target and does not materially change model performance.
- `sex` is close to balanced across outcomes, limiting its explanatory contribution.

### Anomalies and Quality Checks
- No missingness pattern had to be modeled.
- No constant or near-constant numeric variables were found.
- No duplicate records or ID collisions were found.
- There is no evidence of one simple latent subgroup driving the labels; the weak PCA separation suggests a more targeted feature-level mechanism.

## 4. Predictive Modeling

### Modeling Strategy
I treated the task as **binary classification** and compared:
1. **Elastic-net logistic regression** for a regularized, interpretable linear decision rule.
2. **Random forest** as a nonlinear benchmark that can capture interactions and threshold effects.

Evaluation used **5-fold stratified cross-validation repeated 5 times** for stable estimates, followed by a **20% stratified holdout set** for final out-of-sample testing.

### Cross-Validated Performance
Best model by mean ROC AUC: **elastic_net_logistic**

Elastic-net logistic regression:
| index | mean | std |
| --- | --- | --- |
| roc_auc | 0.8618 | 0.0249 |
| average_precision | 0.8779 | 0.0268 |
| accuracy | 0.7753 | 0.0329 |
| f1 | 0.7876 | 0.0268 |

Random forest:
| index | mean | std |
| --- | --- | --- |
| roc_auc | 0.8505 | 0.0282 |
| average_precision | 0.8653 | 0.0292 |
| accuracy | 0.7677 | 0.0362 |
| f1 | 0.7912 | 0.0300 |

### Holdout Performance for Best Model
| index | value |
| --- | --- |
| roc_auc | 0.8519 |
| average_precision | 0.8713 |
| accuracy | 0.7667 |
| f1 | 0.7812 |
| brier | 0.1646 |

Confusion matrix (`[[TN, FP], [FN, TP]]`):
`[[42, 15], [13, 50]]`

Saved model plots:
- ROC comparison: `plots/model_roc_curve.png`
- Calibration curve: `plots/calibration_curve.png`
- Permutation importance: `plots/permutation_importance.png`

Interpretation:
- The best model achieves strong discrimination on both cross-validation and the holdout set, indicating genuine predictive signal rather than pure overfitting.
- Here the elastic-net logistic model slightly outperforms the random forest on mean ROC AUC, which suggests the decision boundary is largely additive and can be captured without a heavily nonlinear model.

### Most Important Predictors in the Best Model
| feature | importance |
| --- | --- |
| gene_001 | 0.1354 |
| gene_000 | 0.0929 |
| gene_002 | 0.0454 |
| gene_089 | 0.0267 |
| gene_035 | 0.0175 |
| gene_079 | 0.0121 |
| gene_078 | 0.0108 |
| gene_050 | 0.0100 |

## 5. Assumption Checks and Validation

For interpretability and diagnostics, I fit a simpler logistic regression on the most important predictors: `gene_000`, `gene_001`, `gene_002`, `age`, and `sex`.

### Logistic Inference
| index | coef | odds_ratio | ci_low | ci_high | p_value |
| --- | --- | --- | --- | --- | --- |
| gene_000 | 1.7205 | 5.5871 | 4.0072 | 7.7901 | 0.0000 |
| gene_001 | -1.8166 | 0.1626 | 0.1164 | 0.2271 | 0.0000 |
| gene_002 | 1.0500 | 2.8575 | 2.1911 | 3.7267 | 0.0000 |
| age | -0.2230 | 0.8001 | 0.6359 | 1.0067 | 0.0570 |
| sex_M | -0.0669 | 0.9352 | 0.5952 | 1.4697 | 0.7716 |

### Multicollinearity (VIF)
| feature | vif |
| --- | --- |
| const | 2.0370 |
| gene_000 | 1.0010 |
| gene_001 | 1.0000 |
| gene_002 | 1.0030 |
| age | 1.0030 |
| sex_M | 1.0030 |

### Diagnostics
- Logistic diagnostic plot: `plots/logistic_diagnostics.png`
- Model AIC: **480.51**
- Cox-Snell pseudo-R²: **0.453**
- Maximum absolute Pearson residual: **8.946**
- Number of observations with Cook's distance > 4/n: **35**
- Likelihood-ratio test for nonlinear age effect (`age` + `age²` vs linear `age`): **p = 0.6835**

Interpretation:
- VIF values near 1 indicate negligible multicollinearity in the interpretable model.
- The age nonlinearity test does not support introducing a quadratic age term unless the p-value is small; this supports keeping age linear or even deprioritizing it altogether.
- The residual and Cook's-distance diagnostics indicate a modest set of influential observations, including a few confidently misclassified samples. They do not invalidate the model, but they are the right place to look for hidden subgroups, measurement error, or label noise.

## 6. Conclusions
1. The dataset is clean and structurally well-behaved, so the main challenge is identifying real signal rather than repairing the table.
2. Predictive information is concentrated in a few gene variables, especially **`gene_001`**, **`gene_000`**, and **`gene_002`**.
3. Demographics contribute relatively little compared with the gene features.
4. A regularized logistic model is a strong default here because it is competitive predictively and easier to justify scientifically than a more opaque nonlinear alternative.
5. There is no strong evidence that age requires nonlinear treatment, and the interpretable model shows low multicollinearity.

## 7. Limitations and Next Steps
- The dataset is modest in size, so external validation on an independent cohort would still be necessary before treating the model as production-ready.
- If these are genuine biological measurements, feature stability should be rechecked under batch effects, laboratory drift, and cohort shift.
- If decision costs are asymmetric, the classification threshold should be tuned using a domain-specific utility function rather than the default 0.5 cutoff.
- If causal interpretation matters, additional confounders and study-design context are needed; current results are predictive, not causal.
