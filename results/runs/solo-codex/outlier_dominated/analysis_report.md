# Dataset Analysis Report

## Executive Summary

The dataset contains **1200 rows** and **8 raw columns** describing e-commerce-like orders with a binary return flag. The data has **no missing values**, but it is **not clean**: `order_total_usd` is frequently inconsistent with the quantity, unit price, shipping, and discount fields, with some discrepancies approaching **$19,867.89** and **28 negative order totals**. Those anomalies are materially important and dominate the data-quality assessment.

From a predictive standpoint, the available fields contain **little to no reliable signal** for `returned`. Both classical inference and cross-validated machine learning stayed near chance-level performance. The strongest conclusion is therefore about **data quality and weak separability**, not a meaningful return-risk model.

## 1. Data Loading and Inspection

- File analyzed: `dataset.csv`
- Raw file shape: `1200 x 8`
- Analysis frame shape after derived features: `1200 x 13`
- Positive class prevalence: `8.750%`
- Customer segments: Returning=541, New=480, VIP=179
- Shipping levels observed: [0.0, 4.99, 9.99, 14.99]
- Discount levels observed: [0, 5, 10, 15, 20]

### Dtypes

```text
                        dtype
order_id                int64
customer_segment     category
items_qty               int64
unit_price_usd        float64
shipping_usd          float64
discount_pct            int64
order_total_usd       float64
returned                int64
expected_total_usd    float64
total_error_usd       float64
abs_total_error_usd   float64
negative_total_flag     int64
large_error_flag        int64
```

### Null Counts

```text
                     null_count
order_id                      0
customer_segment              0
items_qty                     0
unit_price_usd                0
shipping_usd                  0
discount_pct                  0
order_total_usd               0
returned                      0
expected_total_usd            0
total_error_usd               0
abs_total_error_usd           0
negative_total_flag           0
large_error_flag              0
```

### Basic Statistics

```text
       items_qty  unit_price_usd  shipping_usd  discount_pct  order_total_usd  expected_total_usd  abs_total_error_usd  returned
count   1200.000        1200.000      1200.000      1200.000         1200.000            1200.000             1200.000  1200.000
mean       9.781         103.763         7.384         9.562         1093.429             926.417              704.295     0.088
std        5.631          56.723         5.684         7.182         3044.678             785.926             2843.616     0.283
min        1.000           5.630         0.000         0.000       -19240.640               8.168                0.000     0.000
25%        5.000          53.145         0.000         5.000          287.522             275.282                5.569     0.000
50%       10.000         105.990         4.990        10.000          764.285             699.050               53.301     0.000
75%       15.000         153.292        14.990        15.000         1596.655            1392.152              155.668     0.000
max       19.000         199.890        14.990        20.000        21438.550            3598.790            19867.890     1.000
```

## 2. Exploratory Data Analysis

Plots were saved to `./plots/`:

- `numeric_distributions.png`
- `boxplots_by_returned.png`
- `segment_return_counts.png`
- `segment_return_rate.png`
- `order_total_consistency.png`
- `order_total_error_distribution.png`
- `correlation_heatmap.png`
- `model_roc_curves.png`
- `predicted_probability_distributions.png`

### Distributional Checks

Shapiro-Wilk tests were run on a random sample of 500 observations per numeric feature. These tests reject normality for most variables, so non-parametric comparisons were preferred:

- `items_qty`: W=0.935, p=6.03e-14
- `unit_price_usd`: W=0.950, p=6.41e-12
- `shipping_usd`: W=0.852, p=3.06e-21
- `discount_pct`: W=0.886, p=8.98e-19
- `order_total_usd`: W=0.519, p=1.12e-34
- `abs_total_error_usd`: W=0.262, p=2.1e-40

### Return Patterns by Segment

```text
                  return_rate  count
customer_segment                    
New                    0.0875    480
Returning              0.0813    541
VIP                    0.1061    179
```

Chi-square test for association between `customer_segment` and `returned`:

- chi-square = 1.037
- p-value = 0.595

There is no statistically credible evidence that return propensity differs by segment in this sample.

### Numeric Relationships With Returns

Point-biserial correlations between numeric fields and `returned` were uniformly weak:

- `items_qty`: r=-0.019, p=0.514
- `unit_price_usd`: r=0.025, p=0.389
- `shipping_usd`: r=0.041, p=0.157
- `discount_pct`: r=-0.012, p=0.679
- `order_total_usd`: r=-0.015, p=0.606
- `expected_total_usd`: r=0.015, p=0.592
- `abs_total_error_usd`: r=-0.003, p=0.915

Mann-Whitney tests comparing returned vs non-returned orders also found no meaningful univariate separation:

- `items_qty`: p=0.510
- `unit_price_usd`: p=0.372
- `shipping_usd`: p=0.156
- `discount_pct`: p=0.699
- `order_total_usd`: p=0.755
- `expected_total_usd`: p=0.582
- `abs_total_error_usd`: p=0.564

## 3. Data Quality and Anomaly Investigation

`order_total_usd` was checked against the accounting identity:

`expected_total_usd = items_qty * unit_price_usd * (1 - discount_pct / 100) + shipping_usd`

This check failed often and sometimes catastrophically.

- Median absolute discrepancy: **$53.30**
- Mean absolute discrepancy: **$704.29**
- Rows with absolute discrepancy > $1,000: **60** (5.0%)
- Negative `order_total_usd` rows: **28** (2.3%)

Fisher tests on anomaly indicators vs `returned`:

- Negative total flag: odds ratio = 1.259, p = 0.730
- Large error flag: odds ratio = 0.945, p = 1.000

The anomaly indicators themselves are not predictive of returns, but they do show that the dataset cannot be treated as accounting-consistent.

### Most Extreme Order Total Anomalies

```text
      order_id customer_segment  items_qty  unit_price_usd  shipping_usd  discount_pct  order_total_usd  expected_total_usd  total_error_usd  returned
621      10621        Returning         15          122.12          9.99            20         21343.32            1475.430        19867.890         0
954      10954              New         18           31.39         14.99             5        -19240.64             551.759       -19792.399         0
797      10797              VIP         10           29.98          9.99             5         20064.84             294.800        19770.040         0
856      10856              New          8          147.95          9.99            15        -18384.54            1016.050       -19400.590         0
238      10238        Returning          4          197.40         14.99            15        -18289.99             686.150       -18976.140         1
408      10408        Returning         18          168.43          9.99            15         21438.55            2586.969        18851.581         0
361      10361        Returning          5           37.57          9.99            15        -18170.59             169.662       -18340.252         0
416      10416        Returning          7          186.53          9.99            10         19483.79            1185.129        18298.661         0
1027     11027        Returning         16           44.27          0.00            20         18576.69             566.656        18010.034         1
766      10766              New          6          156.06          0.00             0         18898.81             936.360        17962.450         0
```

## 4. Modeling

Because `returned` is binary and class-imbalanced, the primary task was framed as **classification**. Stratified 5-fold cross-validation was used to preserve the low positive rate in each fold.

Models evaluated:

- `dummy_prior`: baseline that predicts the class prior
- `logistic_regression`: interpretable linear classifier with class balancing
- `random_forest`: flexible non-linear model with class balancing

### Cross-Validated Performance

**dummy_prior**
- `roc_auc`: mean=0.500, std=0.000
- `pr_auc`: mean=0.087, std=0.000
- `bal_acc`: mean=0.500, std=0.000
- `brier`: mean=0.080, std=0.000
**logistic_regression**
- `roc_auc`: mean=0.478, std=0.053
- `pr_auc`: mean=0.092, std=0.013
- `bal_acc`: mean=0.475, std=0.034
- `brier`: mean=0.251, std=0.004
**random_forest**
- `roc_auc`: mean=0.509, std=0.047
- `pr_auc`: mean=0.096, std=0.009
- `bal_acc`: mean=0.497, std=0.015
- `brier`: mean=0.131, std=0.003

Interpretation:

- The baseline PR AUC is the class prevalence, about **0.088**.
- Logistic regression performed **worse than or approximately equal to baseline**, indicating no stable linear signal.
- Random forest improved only marginally over the baseline PR AUC and stayed near **0.509 ROC AUC**, which is effectively chance-level discrimination.
- The random forest produced lower Brier loss than the logistic model, but discrimination remained too weak to justify operational use.

## 5. Model Assumptions and Diagnostics

For inferential checks, a parsimonious logistic regression used:

- `customer_segment`
- `items_qty`
- `unit_price_usd`
- `shipping_usd`
- `discount_pct`
- `abs_total_error_usd`
- `negative_total_flag`

### Multicollinearity

Variance inflation factors were modest:

- `items_qty`: 1.012
- `unit_price_usd`: 1.006
- `shipping_usd`: 1.005
- `discount_pct`: 1.012
- `abs_total_error_usd`: 1.539
- `negative_total_flag`: 1.536
- `customer_segment_Returning`: 1.179
- `customer_segment_VIP`: 1.176

These values do not indicate problematic collinearity in the parsimonious inferential model.

### Linearity of the Logit

Box-Tidwell-style interaction terms were tested for continuous predictors:

- `items_qty` interaction p-value: 0.632
- `unit_price_usd` interaction p-value: 0.284
- `shipping_usd` interaction p-value: 0.234
- `discount_pct` interaction p-value: 0.312
- `abs_total_error_usd` interaction p-value: 0.543

No interaction term was significant at conventional thresholds, so the linearity-in-the-logit assumption was not contradicted by these checks.

### Logistic Regression Fit

- McFadden pseudo-R²: 0.0067
- AIC: 725.35
- Positive predictions at threshold 0.5 on the full sample: 0
- Hosmer-Lemeshow statistic: 8.156 on 8 df, p = 0.418

Coefficient table:

```text
                              coef  pvalue
const                      -2.5392  0.0000
items_qty                  -0.0125  0.4961
unit_price_usd              0.0015  0.4052
shipping_usd                0.0265  0.1435
discount_pct               -0.0066  0.6440
abs_total_error_usd        -0.0000  0.7020
negative_total_flag         0.4186  0.6079
customer_segment_Returning -0.0585  0.7966
customer_segment_VIP        0.2452  0.4034
```

None of the fitted coefficients were statistically compelling, which is consistent with the cross-validated near-chance performance.

## 6. Findings

1. **The dataset is complete but not trustworthy as-is for revenue-like fields.** `order_total_usd` fails a simple consistency check on many rows and includes implausible negative totals.
2. **There is no strong evidence of segment-level return differences.** VIP customers show a slightly higher raw return rate, but the difference is not statistically persuasive.
3. **The available features do not separate returned from non-returned orders well.** Univariate tests, logistic regression, and random forest all point to weak signal.
4. **A production return-prediction model is not supported by this dataset in its current form.** The best model barely improves over a naive baseline and would likely be unstable in deployment.

## 7. Recommendations

1. Audit how `order_total_usd` was generated or exported. The discrepancies are too large to be rounding noise.
2. Verify whether negative totals represent refunds, reversals, chargebacks, or data corruption; encode those cases explicitly if they are real business events.
3. Before further modeling, collect stronger behavioral features such as product category, time-to-ship, payment method, geography, customer history, or fulfillment issues.
4. If return prediction is the business goal, re-run modeling only after the accounting fields are validated and the feature set is expanded.
