# Dataset Analysis Report

        ## 1. Objective
        This report analyzes `dataset.csv` as a binary fraud-detection problem, checks data quality, explores structure and anomalies, and evaluates both an interpretable linear classifier and a nonlinear benchmark. The goal is not only to fit a model, but to verify whether the data support the modeling assumptions.

        ## 2. Data Inspection
        - Shape: 3000 rows x 8 columns
        - Duplicate rows: 0
        - Duplicate transaction IDs: 0
        - Missing values: none
        - Fraud prevalence: 5.00% (150 of 3000 transactions)
        - Columns:
          - Identifier: `transaction_id`
          - Numeric: `amount_usd`, `hour_of_day`, `card_age_months`, `distance_from_home_km`
          - Categorical/binary: `merchant_category`, `is_international`
          - Target: `is_fraud`

        `transaction_id` is unique for every row and behaves as a pure identifier, so it was excluded from modeling to avoid memorization rather than learning.

        ### Numeric Summary
        ```
                        count       mean         std  min     25%   50%    75%      max
amount_usd             3000.0  74.890543  153.170350  1.0  16.025  36.0  78.19  4565.29
hour_of_day            3000.0  12.667000    5.221226  0.0   9.000  12.0  17.00    23.00
card_age_months        3000.0  59.737000   34.318757  1.0  29.000  60.0  89.00   119.00
distance_from_home_km  3000.0  12.172600   17.848181  0.0   3.000   7.3  15.30   286.10
```

        ### Data-Type / Null Check
        ```
                         dtype  nulls
transaction_id             str      0
amount_usd             float64      0
hour_of_day              int64      0
merchant_category          str      0
card_age_months          int64      0
distance_from_home_km  float64      0
is_international         int64      0
is_fraud                 int64      0
```

        ## 3. Data Quality and Distribution Checks
        - No missing values or exact duplicate transactions were present.
        - The target is materially imbalanced at 5%, so accuracy alone would be misleading.
        - `amount_usd` and `distance_from_home_km` are strongly right-skewed:
          - amount skewness = 13.85
          - distance skewness = 6.15
        - Outlier counts by the IQR rule:
          - `amount_usd`: 305 values above 171.44
          - `distance_from_home_km`: 177 values above 33.75

        These tails are not necessarily data errors in fraud data, but they do violate naive Gaussian assumptions. To stabilize the linear model, `log1p(amount_usd)` and `log1p(distance_from_home_km)` were used instead of the raw variables.

        ## 4. Exploratory Findings

        ### Univariate and Bivariate Patterns
        - Distance from home is the strongest raw signal in the table:
          - Pearson correlation with fraud = 0.505
          - Top distance decile carries a fraud rate near 29%, versus roughly 0.7% to 6.6% in the first nine deciles.
        - Transaction amount is also associated with fraud:
          - Pearson correlation with fraud = 0.131
          - Highest amount decile has a fraud rate of about 12.7%, versus 0% in the lowest decile.
        - Time matters nonlinearly:
          - Overall fraud rate = 5.00%
          - Hours 0, 1, 3, 4, and 23 show much higher observed fraud rates, with hour 1 at 45% on only 20 samples.
          - This pattern supports cyclical encoding of hour rather than treating hour as a strictly linear variable.
        - `card_age_months` appears weak:
          - Correlation with fraud = -0.003
          - Mann-Whitney p-value = 0.859
        - `merchant_category` differences are modest and not statistically convincing as a standalone effect:
          - Chi-squared p-value = 0.279
        - `is_international` is effectively uninformative here:
          - Fraud rate domestic = 5.00%
          - Fraud rate international = 5.01%
          - Chi-squared p-value = 1.000

        ### Nonparametric Group Comparisons
        ```
              feature  statistic      p_value
           amount_usd   116204.5 3.948454e-21
          hour_of_day   240512.0 9.534080e-03
      card_age_months   215586.0 8.590955e-01
distance_from_home_km    76677.5 4.109544e-40
```

        Interpretation: fraud and non-fraud transactions differ strongly in amount, distance, and hour distribution, but not in card age.

        ## 5. Visual Outputs
        The following diagnostic plots were generated:
        - [plots/amount_distribution_log.png](plots/amount_distribution_log.png)
        - [plots/distance_distribution_log.png](plots/distance_distribution_log.png)
        - [plots/fraud_rate_by_hour.png](plots/fraud_rate_by_hour.png)
        - [plots/fraud_rate_by_category.png](plots/fraud_rate_by_category.png)
        - [plots/correlation_heatmap.png](plots/correlation_heatmap.png)
        - [plots/amount_vs_distance_scatter.png](plots/amount_vs_distance_scatter.png)
        - [plots/calibration_curves.png](plots/calibration_curves.png)
        - [plots/precision_recall_curves.png](plots/precision_recall_curves.png)
        - [plots/rf_permutation_importance.png](plots/rf_permutation_importance.png)

        ## 6. Modeling Strategy
        Two supervised classifiers were evaluated:
        1. Logistic regression with class balancing for interpretability and coefficient-based reasoning.
        2. Random forest as a nonlinear benchmark that can capture threshold effects and interactions.

        Modeling choices:
        - `transaction_id` was removed because it is a row identifier, not a predictive feature.
        - `hour_of_day` was encoded as sine/cosine to preserve cyclical structure.
        - Log transforms were used on `amount_usd` and `distance_from_home_km` to reduce leverage from heavy tails.
        - Repeated stratified 5-fold cross-validation was used because the fraud class is rare.
        - Metrics emphasized ranking and probability quality: ROC AUC, PR AUC, and Brier score.

        ## 7. Cross-Validated Performance
        ### Logistic Regression
        - Mean ROC AUC: 0.877 +/- 0.037
        - Mean PR AUC: 0.488 +/- 0.098
        - Mean Brier score: 0.131

        ### Random Forest
        - Mean ROC AUC: 0.890 +/- 0.039
        - Mean PR AUC: 0.548 +/- 0.075
        - Mean Brier score: 0.044

        The random forest is the stronger predictive model by ranking metrics if it clearly exceeds the logistic model. The logistic model remains valuable because its assumptions can be inspected directly and its effects are easier to explain.

        ## 8. Holdout Test Performance
        Test split size: 750 rows with fraud prevalence 4.93%

        ### Logistic Regression
        - ROC AUC: 0.876
        - PR AUC: 0.500
        - Brier score: 0.130
        - Confusion matrix at 0.50 threshold:
        ```
          pred_0  pred_1
actual_0     573     140
actual_1       8      29
```

        ### Random Forest
        - ROC AUC: 0.892
        - PR AUC: 0.561
        - Brier score: 0.040
        - Confusion matrix at 0.50 threshold:
        ```
          pred_0  pred_1
actual_0     700      13
actual_1      19      18
```

        Note: because fraud is rare, the default 0.50 threshold is not necessarily operationally optimal. In production, threshold selection should be tied to investigation capacity and the relative costs of false positives versus false negatives.

        ## 9. Logistic Model Diagnostics and Assumption Checks
        ### Multicollinearity
        ```
                      feature      VIF
               log_amount_usd 6.900749
    log_distance_from_home_km 4.684979
              card_age_months 3.582362
    merchant_category_Grocery 1.770099
     merchant_category_Travel 1.747539
        merchant_category_Gas 1.736949
 merchant_category_Restaurant 1.708199
     merchant_category_Online 1.677032
merchant_category_Electronics 1.660576
                     hour_cos 1.341251
             is_international 1.177552
                     hour_sin 1.046371
```

        Interpretation: VIF values are low enough that multicollinearity is not a material concern.

        ### Linearity in the Logit
        Box-Tidwell interaction p-values for continuous predictors after shifting strictly positive where needed:
        ```
                  term      p_value
   amount_shift_logint 1.512742e-07
 distance_shift_logint 1.854922e-01
card_age_months_logint 5.047021e-01
```

        Interpretation:
        - `distance_shift_logint` and `card_age_months_logint` are not significant, so there is no strong evidence against linearity in the logit for those terms after transformation.
        - `amount_shift_logint` remains strongly significant, which indicates residual nonlinearity for transaction amount even after the log transform.
        - This weakens the strict linear-model assumption and helps explain why the random forest performs better as a predictive model.

        ### Calibration
        - Hosmer-Lemeshow statistic: 386.380
        - Hosmer-Lemeshow p-value: 0.000
        - Calibration also appears visually in [plots/calibration_curves.png](plots/calibration_curves.png).

        The very small p-value indicates poor calibration for the logistic model on this test split. This is consistent with the nonlinear amount effect and suggests that, if logistic regression is kept for interpretability, it should be extended with spline terms or followed by calibration.

        ### Coefficients and Odds Ratios
        ```
                                    coef  odds_ratio       p_value
const                         -10.123479    0.000040  4.281514e-53
log_distance_from_home_km       1.661498    5.267195  9.393564e-39
log_amount_usd                  0.744805    2.106031  2.625056e-16
hour_cos                        1.102469    3.011594  1.464581e-12
merchant_category_Gas          -0.734944    0.479532  6.802638e-02
hour_sin                        0.241091    1.272637  7.388043e-02
merchant_category_Grocery      -0.461665    0.630233  2.147806e-01
merchant_category_Electronics  -0.200140    0.818616  5.859959e-01
is_international               -0.085744    0.917829  7.520611e-01
merchant_category_Restaurant    0.086733    1.090606  8.006082e-01
merchant_category_Online       -0.084578    0.918900  8.125909e-01
merchant_category_Travel       -0.070012    0.932383  8.414920e-01
```

        Interpretable takeaways from the logistic fit:
        - Higher transaction amount and greater distance from home both increase estimated fraud odds even after controlling for other variables.
        - The cyclical hour terms confirm a time-of-day pattern rather than a simple linear decline or increase across the day.
        - Card age remains weak after adjustment.
        - Merchant category effects are secondary compared with distance and amount.

        ## 10. Random Forest Feature Importance
        Permutation importance on the test set identifies the features most useful for average precision. The strongest features are expected to be transformed distance, transformed amount, and hour encoding, which is consistent with the EDA. See [plots/rf_permutation_importance.png](plots/rf_permutation_importance.png).

        ## 11. Key Findings
        - The dataset is clean in terms of missingness and duplicates, but not well-behaved in a Gaussian sense because amount and distance are highly skewed with heavy upper tails.
        - Fraud risk is concentrated in a clear behavioral pattern:
          - far-from-home transactions
          - higher transaction amounts
          - late-night / early-morning hours
        - `card_age_months`, `merchant_category`, and `is_international` contribute far less signal than the variables above.
        - The classification problem is learnable: both tested models materially outperform the 5% baseline.
        - A nonlinear model extracts better predictive signal here, and the diagnostics suggest it is not only an accuracy gain but also a better match to the data-generating structure.

        ## 12. Limitations
        - The dataset is relatively small for fraud modeling at only 3,000 rows and 150 fraud cases.
        - The apparent night-hour effects for some specific hours are based on small cell counts and should not be over-interpreted without more data.
        - There is no time ordering column, so leakage-safe temporal validation is not possible here.
        - The feature set is narrow. Real fraud systems typically benefit from velocity features, prior merchant behavior, device fingerprinting, geographic history, and network features.

        ## 13. Recommendation
        If interpretability matters most, use the transformed logistic regression only as a baseline and consider adding spline terms for transaction amount before operationalizing it.

        If predictive performance matters most, favor the random forest benchmark and add probability calibration plus threshold tuning before deployment.

        In either case, the next highest-value step is feature engineering around transaction history and user behavior rather than more aggressive tuning on this limited feature set.
