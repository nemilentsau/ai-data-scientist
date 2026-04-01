# Dataset Analysis Report

## Executive Summary
This analysis covers `dataset.csv`, a 1,000-row campaign-performance dataset with 8 original columns: campaign identifier, geography, channel, spend, impressions, clicks, revenue, and month. The data are structurally clean: there are no missing values, no duplicate rows, and all core business metrics are strictly positive.

The strongest empirical finding is that **revenue is overwhelmingly explained by ad spend**. A simple spend-only linear model explains **0.945 R-squared** in-sample and achieves **0.945 mean 5-fold CV R-squared** when using all features, while the spend-only model itself reaches **0.945 mean CV R-squared**. More complex models did not materially improve predictive accuracy, which suggests the dataset follows a largely deterministic spend-to-revenue relationship rather than strong channel-, region-, or month-specific effects.

The main caveat is inferential rather than predictive: residual diagnostics show **heteroscedasticity**, **heavy tails**, and **a modest set of influential campaigns**. Because of that, classical OLS standard errors are optimistic. For inference, heteroscedasticity-robust standard errors are more appropriate than plain OLS standard errors.

## 1. Data Loading and Inspection
- Shape: **1000 rows x 8 original columns** (plus engineered analysis columns during EDA).
- Original columns: `campaign_id, region, channel, ad_spend_usd, impressions, clicks, revenue_usd, month`.
- Duplicate rows: **0**
- Duplicate `campaign_id` values: **0**
- Missing values: **0 total**
- Non-positive counts in core measures: `{'ad_spend_usd': 0, 'impressions': 0, 'clicks': 0, 'revenue_usd': 0}`

### Data Types
```
                     0
campaign_id      int64
region        category
channel       category
ad_spend_usd   float64
impressions      int64
clicks           int64
revenue_usd    float64
month            int64
```

### Missingness
```
              null_count
campaign_id            0
region                 0
channel                0
ad_spend_usd           0
impressions            0
clicks                 0
revenue_usd            0
month                  0
ctr                    0
cpc                    0
cpm                    0
roas                   0
log_spend              0
log_revenue            0
```

### Summary Statistics
```
               count        mean         std       min         25%         50%         75%         max
ad_spend_usd  1000.0   24767.699   14460.799   729.290   12180.680   25091.965   37343.818   49986.020
impressions   1000.0  284199.699  177137.579  7126.000  127329.000  272571.000  417551.750  709259.000
clicks        1000.0    8422.728    6442.990   145.000    3237.000    6860.500   12427.750   34102.000
revenue_usd   1000.0   61978.971   37100.879  1480.530   29737.852   61328.060   92083.098  155837.950
ctr           1000.0       0.030       0.011     0.010       0.020       0.029       0.040       0.050
cpc           1000.0       3.636       1.886     1.388       2.281       3.023       4.492      11.932
cpm           1000.0      90.136      16.387    66.683      75.971      87.345     103.194     124.997
roas          1000.0       2.507       0.352     0.975       2.283       2.500       2.725       4.273
```

## 2. Data Quality and Sanity Checks
- No nulls, duplicate rows, or duplicate campaign IDs were found.
- All business-volume columns (`ad_spend_usd`, `impressions`, `clicks`, `revenue_usd`) are strictly positive, so log transforms are feasible if needed.
- `month` only takes values 1 through 12, so there is no obvious invalid temporal coding.
- The categorical distributions are reasonably balanced:
  - Regions: {'North': 261, 'South': 258, 'West': 241, 'East': 240}
  - Channels: {'Email': 266, 'Search': 258, 'Social': 250, 'Display': 226}
- IQR-based outlier screening suggests the strongest univariate anomalies are in:
  - `clicks`: **16** points outside the 1.5 IQR rule
  - `roas`: **18** points outside the 1.5 IQR rule
  - `ad_spend_usd`, `impressions`, and `revenue_usd` show **0** IQR outliers under that rule, indicating broad ranges but not isolated extreme tails in the raw monetary/volume variables.

## 3. Exploratory Data Analysis

### Engineered Metrics
To make campaign efficiency interpretable, I engineered:
- `ctr = clicks / impressions`
- `cpc = ad_spend_usd / clicks`
- `cpm = ad_spend_usd / impressions * 1000`
- `roas = revenue_usd / ad_spend_usd`

Their key averages are:
- Mean CTR: **2.98%**
- Mean CPC: **$3.64**
- Mean CPM: **$90.14**
- Mean ROAS: **2.507x**

### Main Patterns
1. **Spend and revenue move almost one-for-one on a strong linear scale.**
   - Pearson correlation(`ad_spend_usd`, `revenue_usd`) = **0.972**
   - The scatterplot in [plots/04_spend_vs_revenue.png](./plots/04_spend_vs_revenue.png) shows a tight linear band.

2. **Impressions and clicks are also strongly correlated with spend, which creates redundancy rather than much new information.**
   - Correlation(`ad_spend_usd`, `impressions`) = **0.945**
   - Correlation(`ad_spend_usd`, `clicks`) = **0.773**

3. **Efficiency metrics are surprisingly stable across categories.**
   - Channel-level mean ROAS ranges only from **2.493x** to **2.527x**
   - Region-level mean ROAS ranges only from **2.469x** to **2.547x**
   - ANOVA does not show strong evidence that ROAS differs by channel (`p = 0.680`) or region (`p = 0.076`).

4. **There is visible month-to-month volume variation, but little independent month effect once spend is controlled for.**
   - Highest mean revenue month: **month 11** at **$72,523.88**
   - Lowest mean revenue month: **month 9** at **$53,996.76**
   - The multivariable model finds month indicators mostly insignificant after accounting for spend and delivery metrics.

### Group-Level Summaries
#### By Channel
```
           ctr           cpc            cpm           roas        revenue_usd            ad_spend_usd           
          mean median   mean median    mean  median   mean median        mean     median         mean     median
channel                                                                                                         
Display  0.031  0.032  3.453  2.838  90.602  87.679  2.493  2.493   60814.708  61164.565    24505.922  25684.760
Email    0.030  0.029  3.709  2.926  89.792  85.417  2.496  2.500   61020.518  58835.410    24582.835  24882.115
Search   0.029  0.027  3.764  3.259  90.392  88.836  2.513  2.491   61522.913  60049.170    24541.372  23382.380
Social   0.030  0.031  3.591  2.963  89.814  87.431  2.527  2.528   64521.910  64801.785    25434.612  25901.605
```

#### By Region
```
          ctr           cpc            cpm           roas       
         mean median   mean median    mean  median   mean median
region                                                          
East    0.031  0.032  3.568  2.807  90.163  86.999  2.521  2.536
North   0.029  0.027  3.620  3.063  88.831  84.875  2.469  2.493
South   0.029  0.029  3.699  2.923  89.981  88.012  2.496  2.479
West    0.030  0.029  3.653  3.086  91.687  90.972  2.547  2.521
```

## 4. Modeling Strategy
I treated this primarily as a **regression** problem with `revenue_usd` as the outcome. I compared:
- A simple interpretable OLS benchmark: `revenue_usd ~ ad_spend_usd`
- A slightly richer linear model: `revenue_usd ~ ad_spend_usd + clicks`
- A full OLS model with spend, impressions, clicks, and categorical controls for region, channel, and month
- Machine-learning regressors for predictive comparison: linear regression pipeline, ridge, random forest, and histogram gradient boosting

I excluded `campaign_id` from modeling because it behaves like an identifier, not a meaningful signal.

### Model Comparison
#### OLS Family
| model | adjusted_r2 | AIC | Breusch-Pagan p | Jarque-Bera p |
|---|---:|---:|---:|---:|
| Spend only | 0.945380 | 20975.31 | 9.697e-37 | 8.082e-42 |
| Spend + clicks | 0.945574 | 20972.75 | 1.713e-36 | 4.819e-35 |
| Full linear model | 0.945355 | 20994.55 | 1.223e-26 | 2.008e-33 |

The richer linear models do **not** improve adjusted R-squared or AIC enough to justify the added complexity. The best practical model is therefore the **spend-only model**: it is simpler, easier to explain, and just as accurate out of sample.

#### Cross-Validated Predictive Models
```
                               cv_r2_mean  cv_r2_std  cv_rmse_mean  cv_mae_mean
model                                                                          
LinearRegression                   0.9447     0.0034       8702.93      6231.70
RidgeCV                            0.9447     0.0033       8703.10      6232.06
RandomForestRegressor              0.9432     0.0031       8823.15      6336.97
HistGradientBoostingRegressor      0.9371     0.0039       9280.71      6616.52
```

The simplest linear models perform best. Tree-based ensembles do not help here, which is consistent with the near-linear structure seen in the EDA.

## 5. Preferred Model and Interpretation
### Preferred model
`revenue_usd ~ ad_spend_usd`

Using heteroscedasticity-robust HC3 standard errors:
- Intercept: **192.50** (p = 0.588)
- Spend slope: **2.4946** (95% CI: **[2.4541, 2.5351]**)

Interpretation:
- On average, an additional **$1** of ad spend is associated with approximately **$2.49** in revenue.
- The implied average ROAS from the slope is consistent with the observed dataset-wide mean ROAS of **2.507x**.

### Why not the full model?
- In the full model, `impressions` is not significant and `clicks` is only borderline.
- Channel, region, and month indicators are broadly insignificant after controlling for spend.
- Multicollinearity is non-trivial:
  - `ad_spend_usd` VIF = **9.484**
  - `impressions` VIF = **10.810**

#### VIF Table for Full Model
```
                   vif
variable              
impressions     10.810
ad_spend_usd     9.484
clicks           2.894
C(month)[T.10]   1.964
C(month)[T.2]    1.952
C(month)[T.5]    1.905
C(month)[T.7]    1.899
C(month)[T.6]    1.881
C(month)[T.4]    1.861
C(month)[T.12]   1.835
```

## 6. Assumption Checks and Validation

### Linearity
- The spend-revenue scatter is strongly linear, so the mean trend is well captured.
- Log-log regression yields a near-unit elasticity estimate (`log_revenue ~ log_spend` slope = **0.9996**), reinforcing the proportional relationship.

### Heteroscedasticity
- Breusch-Pagan test for the preferred model: **p = 9.697e-37**
- Conclusion: residual variance is not constant. Prediction is still strong, but inference should rely on robust standard errors.

### Normality of Residuals
- Jarque-Bera test: **p = 8.082e-42**
- Residuals are approximately centered but have heavier tails than Gaussian residuals, visible in [plots/07_residual_diagnostics.png](./plots/07_residual_diagnostics.png).

### Independence
- Durbin-Watson for the preferred model: **2.073**
- There is no obvious autocorrelation signal, though this is cross-sectional campaign data rather than a strict time series.

### Influence and Anomalies
- Cook's distance threshold (`4/n`) = **0.0040**
- Observations above that threshold: **61**
- Studentized residuals with absolute value > 3: **10**

These campaigns deserve business review because they substantially over- or under-perform relative to their spend levels.

#### Largest Positive Residuals
```
            region  channel  month  ad_spend_usd  revenue_usd      residual
campaign_id                                                                
406          North  Display      8      44828.40    155837.95  43814.768019
569           West   Search      6      45255.86    147101.45  34011.909526
249           West   Social      5      48199.19    148939.33  28507.242993
484           West   Social     10      31564.12    106422.00  27488.411485
383          South  Display      9      31632.67    105498.14  26393.543965
```

#### Largest Negative Residuals
```
            region  channel  month  ad_spend_usd  revenue_usd      residual
campaign_id                                                                
199          South   Social      3      44410.78     73659.54 -37321.830739
532          South    Email      6      49986.02     89383.88 -35505.703252
420           West  Display      1      37742.54     59592.83 -34753.687529
265          South    Email      8      43929.97     80390.26 -29391.663243
938          North  Display      8      45757.79     87082.64 -27259.034751
```

## 7. Conclusions
1. The dataset is clean and well-structured, with no missingness or duplicate-record issues.
2. Revenue is driven primarily by spend. The relationship is strong enough that a simple one-variable linear model performs as well as or better than more complex alternatives.
3. Channel, region, and month matter far less than expected once spend is included, and there is no strong evidence of systematic ROAS differences across those groups in this dataset.
4. The main statistical caution is heteroscedasticity plus a small set of influential campaigns. That affects uncertainty estimates more than it affects predictive accuracy.
5. Operationally, the most valuable next step is not adding model complexity but investigating the campaigns with the largest residuals. Those are the places where performance is materially above or below what spend alone would predict.

## 8. Deliverables
- Report: [analysis_report.md](./analysis_report.md)
- Plots:
  - [plots/01_missingness_map.png](./plots/01_missingness_map.png)
  - [plots/02_distributions.png](./plots/02_distributions.png)
  - [plots/03_correlation_heatmap.png](./plots/03_correlation_heatmap.png)
  - [plots/04_spend_vs_revenue.png](./plots/04_spend_vs_revenue.png)
  - [plots/05_monthly_trends.png](./plots/05_monthly_trends.png)
  - [plots/06_roas_by_group.png](./plots/06_roas_by_group.png)
  - [plots/07_residual_diagnostics.png](./plots/07_residual_diagnostics.png)
  - [plots/08_cooks_distance.png](./plots/08_cooks_distance.png)
