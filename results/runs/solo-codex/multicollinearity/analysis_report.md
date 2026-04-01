# Dataset Analysis Report

## 1. Scope

This analysis examines `dataset.csv` as a supervised regression problem with `price_usd` as the response variable. The workflow includes data quality checks, exploratory analysis, model comparison, regression diagnostics, and anomaly review. All outputs were generated from a fresh run of `analyze_dataset.py`.

## 2. Data Loading And Inspection

- Shape: 800 rows x 9 columns
- Duplicate rows: 0
- Duplicate `listing_id` values: 0
- Missing values: none detected

### Column Types
```
                  dtype
listing_id        int64
sq_ft             int64
num_rooms         int64
lot_size_acres  float64
garage_spaces     int64
year_built        int64
neighborhood        str
has_pool          int64
price_usd         int64
```

### Null Counts
```
                null_count
listing_id               0
sq_ft                    0
num_rooms                0
lot_size_acres           0
garage_spaces            0
year_built               0
neighborhood             0
has_pool                 0
price_usd                0
```

### Numeric Summary
```
                count       mean       std       min        25%        50%        75%        max
sq_ft           800.0    1796.97    393.07    600.00    1519.00    1805.00    2051.25    3341.00
num_rooms       800.0       6.01      1.39      2.00       5.00       6.00       7.00      11.00
lot_size_acres  800.0       0.90      0.20      0.32       0.76       0.89       1.04       1.72
garage_spaces   800.0       1.98      0.56      1.00       2.00       2.00       2.00       4.00
year_built      800.0    1986.21     20.90   1950.00    1968.00    1987.00    2004.00    2023.00
price_usd       800.0  287148.00  61285.37  83600.00  244575.00  288400.00  328900.00  496700.00
```

## 3. Data Quality And Structure

- The dataset is unusually clean for real estate data: no nulls, no duplicate rows, and no duplicate listing identifiers.
- `listing_id` behaves like a surrogate key and was excluded from modeling.
- The feature set is a mix of continuous structural attributes (`sq_ft`, `lot_size_acres`, `year_built`), low-cardinality counts (`num_rooms`, `garage_spaces`), and categorical indicators (`neighborhood`, `has_pool`).
- Outliers exist, but only in small numbers. Counts of values with absolute z-score above 3 are shown below.

### Outlier Counts
```
                count_abs_z_gt_3
sq_ft                          3
num_rooms                      1
lot_size_acres                 2
garage_spaces                  2
year_built                     0
price_usd                      5
```

## 4. Exploratory Data Analysis

### Relationships With Price
```
                correlation_with_price
sq_ft                            0.955
lot_size_acres                   0.926
num_rooms                        0.921
garage_spaces                    0.751
year_built                       0.177
```

Interpretation:

- Price is dominated by property size signals. `sq_ft`, `lot_size_acres`, and `num_rooms` are all strongly positively correlated with price.
- `garage_spaces` is moderately correlated with price, but much of that appears to reflect larger homes rather than a standalone garage effect.
- `year_built` has a positive but much smaller marginal correlation with price.
- `has_pool` has nearly zero raw correlation with price and also weak adjusted effect after controlling for the other features.

### Group Summaries

Neighborhood-level price summary:
```
              count       mean    median       std
neighborhood                                      
Downtown        158  278852.53  291000.0  61044.35
Eastwood        163  285794.48  285900.0  59739.50
Hillcrest       162  289157.41  281800.0  68418.53
Lakeside        132  292421.97  292100.0  55745.97
Suburbs         185  289902.70  285400.0  59896.34
```

Pool indicator price summary:
```
          count       mean    median       std
has_pool                                      
0           557  287680.79  287200.0  60250.70
1           243  285926.75  291400.0  63703.82
```

Interpretation:

- Raw neighborhood differences are modest relative to overall price variation.
- Homes with pools are not more expensive on average in this sample. That does not imply pools reduce value; it implies pool ownership overlaps with other characteristics in a way that does not create a strong standalone price premium here.

### Visualizations

Generated PNG files:

- `plots/target_distribution.png`
- `plots/correlation_heatmap.png`
- `plots/top_numeric_relationships.png`
- `plots/categorical_price_patterns.png`
- `plots/model_diagnostics.png`
- `plots/actual_vs_predicted.png`
- `plots/permutation_importance.png`

Key visual findings:

- The price distribution is roughly unimodal with a few low-price and high-price tail observations.
- Scatterplots show strong, close-to-linear positive relationships between price and the main size variables, especially `sq_ft`.
- Boxplots suggest neighborhood differences are smaller than the effects of size and age.
- Diagnostic plots do not show strong curvature or severe variance explosions, though a handful of points deserve review.

## 5. Modeling Strategy

I compared five candidate models using 5-fold cross-validation:

1. Linear regression
2. Ridge regression
3. Lasso regression
4. Random forest regression
5. Log-linear regression

The comparison prioritized out-of-sample R^2 and error metrics rather than in-sample fit.

### Cross-Validated Performance
```
                   model  cv_r2_mean  cv_r2_std    cv_mae   cv_rmse
0      Linear regression      0.9425     0.0064  11559.32  14624.80
1       Ridge regression      0.9425     0.0064  11561.16  14626.23
2       Lasso regression      0.9423     0.0063  11599.63  14643.73
3          Random forest      0.9304     0.0071  12728.85  16099.78
4  Log-linear regression      0.9135     0.0070  13626.19  17961.15
```

Model choice:

- Plain linear regression performed best overall: mean CV R^2 = 0.9425, mean CV RMSE = 14624.80.
- Ridge and lasso were nearly identical but slightly worse, implying regularization was not needed for predictive accuracy.
- Random forest underperformed the linear model, which suggests the underlying signal is mostly additive and close to linear.
- Log-transforming the target degraded performance materially, so the original price scale was retained.

### Holdout Performance For The Selected Model

- Test R^2: 0.9491
- Test MAE: $10,987.41
- Test RMSE: $13,486.40

### Permutation Importance On The Test Set
```
          feature  importance_mean  importance_std
0           sq_ft           1.5301          0.1404
4      year_built           0.0659          0.0104
1       num_rooms           0.0071          0.0020
2  lot_size_acres           0.0026          0.0013
5    neighborhood           0.0006          0.0007
6        has_pool           0.0000          0.0006
3   garage_spaces          -0.0003          0.0003
```

Interpretation:

- `sq_ft` is the dominant driver of predictive performance.
- `year_built` contributes meaningful incremental signal.
- Other size-related variables matter, but their importance is partly distributed across correlated measurements.

## 6. Regression Diagnostics And Assumptions

An interpretable OLS model was fit on the full dataset to evaluate assumptions and coefficient stability:

`price_usd ~ sq_ft + num_rooms + lot_size_acres + garage_spaces + year_built + C(neighborhood) + has_pool`

### Multicollinearity
```
                  feature     vif
0                   sq_ft  29.234
2          lot_size_acres  17.263
1               num_rooms  12.070
3           garage_spaces   2.663
9    neighborhood_Suburbs   1.686
7  neighborhood_Hillcrest   1.629
6   neighborhood_Eastwood   1.621
8   neighborhood_Lakeside   1.542
4              year_built   1.007
5                has_pool   1.004
```

Interpretation:

- Multicollinearity is substantial among the size-related predictors.
- `sq_ft`, `lot_size_acres`, and `num_rooms` have especially high VIF values.
- Because of that, predictive performance is reliable, but coefficient-level causal interpretations for these overlapping size measures should be treated cautiously.

### Robust Coefficient Table (HC3 Standard Errors)
```
                                      coef     std_err        z  p_value        ci_low      ci_high
Intercept                    -1.012206e+06  51589.0860 -19.6206   0.0000 -1.113319e+06 -911093.7314
C(neighborhood)[T.Eastwood]  -4.471574e+02   1485.5378  -0.3010   0.7634 -3.358758e+03    2464.4432
C(neighborhood)[T.Hillcrest] -1.270392e+03   1660.7103  -0.7650   0.4443 -4.525324e+03    1984.5408
C(neighborhood)[T.Lakeside]   2.053642e+03   1640.1238   1.2521   0.2105 -1.160942e+03    5268.2256
C(neighborhood)[T.Suburbs]   -1.780195e+03   1542.7435  -1.1539   0.2485 -4.803917e+03    1243.5270
sq_ft                         1.422222e+02      6.4770  21.9580   0.0000  1.295275e+02     154.9169
num_rooms                     1.628360e+03   1256.3603   1.2961   0.1949 -8.340612e+02    4090.7805
lot_size_acres                2.532745e+03   9905.8383   0.2557   0.7982 -1.688234e+04   21947.8318
garage_spaces                -1.860150e+01   1543.7351  -0.0120   0.9904 -3.044267e+03    3007.0637
year_built                    5.199492e+02     25.9455  20.0401   0.0000  4.690970e+02     570.8014
has_pool                     -1.828989e+03   1090.8068  -1.6767   0.0936 -3.966931e+03     308.9531
```

Interpretation:

- `sq_ft` and `year_built` are strongly and consistently associated with higher prices.
- After accounting for `sq_ft`, `year_built`, and the other controls, the neighborhood indicators are not statistically distinguishable from the reference category.
- `num_rooms`, `lot_size_acres`, and `garage_spaces` lose significance once the more dominant size signal in `sq_ft` is included. This is consistent with multicollinearity rather than proof of no relationship.
- The pool effect remains weak and statistically marginal even with heteroskedasticity-robust standard errors.

### Assumption Checks

- Linearity: Ramsey RESET F-test = 0.633, p = 0.4263. No evidence of meaningful omitted nonlinear structure.
- Residual normality: Jarque-Bera statistic = 4.178, p = 0.1238. Residuals are compatible with approximate normality.
- Homoskedasticity: Breusch-Pagan LM p = 0.0637, F p = 0.0629. This is borderline around the 10% level, but not a strong rejection at 5%. HC3 robust standard errors were therefore reported.
- Independence: the data are cross-sectional, there are no duplicate listings, and no repeated IDs were found. Independence cannot be proven from the file alone, but there is no immediate structural evidence against it.
- Influence: maximum Cook's distance = 0.0149; 39 observations exceed the common threshold 4/n = 0.0050. These points are worth review but do not dominate the fit.

## 7. Notable Anomalies

The five largest externally studentized residuals are below. These appear to be properties priced materially below what the fitted model expects given their recorded attributes.

```
     listing_id  sq_ft  num_rooms  lot_size_acres  garage_spaces  year_built neighborhood  has_pool  price_usd  fitted_price  residual
638         639   1284          4           0.622              1        1998      Suburbs         0     161000     215555.37 -54555.37
389         390   1569          5           0.806              2        1965     Downtown         0     197800     242786.37 -44986.37
380         381   1464          5           0.683              2        2016    Hillcrest         0     209100     252788.52 -43688.52
562         563   2148          7           1.099              2        1959      Suburbs         0     281100     324231.96 -43131.96
287         288   2035          7           1.039              2        1953    Hillcrest         0     262800     305398.99 -42598.99
```

Interpretation:

- These observations could reflect unobserved condition issues, distressed sales, data-entry noise, or omitted variables such as renovation quality, school district, or micro-location.
- They are useful candidates for domain review, but not extreme enough to invalidate the overall model.

## 8. Conclusions

- The dataset is clean and well-structured, with no missing values and no duplicate keys.
- Residential price in this sample is explained primarily by home size, especially square footage, with newer construction providing a secondary premium.
- A standard linear regression is both the most interpretable and the best-performing predictive model among the candidates tested.
- The main modeling caveat is multicollinearity among size-related variables. This limits coefficient interpretation but does not materially hurt predictive accuracy.
- There is mild evidence of a few influential or underpriced listings, but no severe assumption failure that would force a different model family.

## 9. Reproducibility

Artifacts generated by this analysis:

- `analysis_report.md`
- `plots/target_distribution.png`
- `plots/correlation_heatmap.png`
- `plots/top_numeric_relationships.png`
- `plots/categorical_price_patterns.png`
- `plots/model_diagnostics.png`
- `plots/actual_vs_predicted.png`
- `plots/permutation_importance.png`
