# Dataset Analysis Report

## Scope
This report analyzes `dataset.csv` as a supervised tabular problem, with `fuel_consumption_lph` treated as the outcome of interest. The workflow covered data inspection, exploratory analysis, anomaly checks, model building, diagnostic testing, and validation.

## Data Inspection
- Shape: `600 rows x 7 columns`
- Numeric columns: `test_id, engine_rpm, ambient_temp_c, humidity_pct, octane_rating, vehicle_age_years, fuel_consumption_lph`
- Missing values: `0`
- Duplicate rows: `0`
- Duplicate `test_id` values: `0`

### Dtypes
```
test_id                   int64
engine_rpm                int64
ambient_temp_c          float64
humidity_pct            float64
octane_rating             int64
vehicle_age_years         int64
fuel_consumption_lph    float64
```


### Basic Statistics
```
       test_id  engine_rpm  ambient_temp_c  humidity_pct  octane_rating  vehicle_age_years  fuel_consumption_lph
count  600.000     600.000         600.000       600.000        600.000            600.000               600.000
mean   300.500    3415.713          25.391        51.009         89.970              7.333                28.166
std    173.349    1551.410           7.880        15.250          2.276              4.359                21.500
min      1.000     826.000           3.400        10.000         87.000              0.000                 0.500
25%    150.750    2058.750          20.275        40.300         87.000              4.000                 8.712
50%    300.500    3490.000          25.300        50.750         91.000              7.000                23.460
75%    450.250    4769.750          30.325        61.000         93.000             11.000                44.940
max    600.000    5999.000          49.600        95.000         93.000             14.000                74.220
```


### Missing Values by Column
```
test_id                 0
engine_rpm              0
ambient_temp_c          0
humidity_pct            0
octane_rating           0
vehicle_age_years       0
fuel_consumption_lph    0
```


### Distribution Shape
Skewness values:
```
engine_rpm             -0.033
ambient_temp_c          0.086
humidity_pct            0.014
octane_rating          -0.000
vehicle_age_years      -0.093
fuel_consumption_lph    0.455
```


Shapiro-Wilk tests were run on random samples of up to 500 observations per variable. These tests reject normality for several variables, but that is not a modeling requirement for predictors; regression assumptions concern the residuals.
```
            variable      W      p_value
          engine_rpm 0.9470 2.159155e-12
      ambient_temp_c 0.9985 9.520344e-01
        humidity_pct 0.9973 5.888645e-01
       octane_rating 0.8525 3.137892e-21
   vehicle_age_years 0.9404 2.829459e-13
fuel_consumption_lph 0.9167 5.671181e-16
```


### Outlier Screening
IQR-rule outlier counts:
```
ambient_temp_c          6
humidity_pct            1
test_id                 0
engine_rpm              0
octane_rating           0
vehicle_age_years       0
fuel_consumption_lph    0
```


Interpretation:
- No obvious data quality failures were detected.
- `ambient_temp_c` contains a small number of tail observations, and `humidity_pct` contains one IQR outlier.
- `fuel_consumption_lph` shows no IQR outliers despite a right-skewed distribution.

## Exploratory Data Analysis
Saved plots:
- `plots/distributions.png`
- `plots/correlation_heatmap.png`
- `plots/predictor_relationships.png`
- `plots/rpm_quadratic_fit.png`
- `plots/final_model_diagnostics.png`
- `plots/observed_vs_predicted.png`
- `plots/fuel_by_octane.png`

### Correlation Matrix
```
                      engine_rpm  ambient_temp_c  humidity_pct  octane_rating  vehicle_age_years  fuel_consumption_lph
engine_rpm                 1.000          -0.025        -0.007         -0.026              0.058                 0.979
ambient_temp_c            -0.025           1.000         0.043         -0.013             -0.010                -0.026
humidity_pct              -0.007           0.043         1.000         -0.036             -0.080                -0.013
octane_rating             -0.026          -0.013        -0.036          1.000             -0.002                -0.028
vehicle_age_years          0.058          -0.010        -0.080         -0.002              1.000                 0.057
fuel_consumption_lph       0.979          -0.026        -0.013         -0.028              0.057                 1.000
```


### EDA Findings
- The dataset contains 600 rows and 7 columns with no missing values, no duplicate rows, and no duplicated `test_id` values.
- The response variable is strongly associated with `engine_rpm` (Pearson r = 0.979), while the other predictors have near-zero marginal correlation with fuel consumption.
- A naive linear model is mis-specified: Ramsey RESET rejects linear functional form (F = 4883.6, p = 1.91e-288), and its residuals fail normality.
- Adding only a quadratic term in centered RPM materially improves fit and remains parsimonious: R^2 = 0.9954, RMSE = 1.455, 10-fold CV RMSE = 1.459.
- The quadratic RPM model satisfies the main regression checks more cleanly: Breusch-Pagan p = 0.228, Jarque-Bera p = 0.626, Durbin-Watson = 2.035.
- Extending the quadratic model with temperature, humidity, octane, and vehicle age does not add meaningful explanatory power; their coefficients remain statistically weak after controlling for RPM curvature.
- A random forest benchmark performs similarly to the quadratic RPM model out of sample, suggesting the remaining signal is limited and mostly captured by simple curvature rather than complex interactions.
- IQR-based univariate outliers appear only in ambient temperature (6 points) and humidity (1 point); they do not translate into highly influential observations in the final model.


## Modeling Strategy
I treated this as a regression problem and compared three model classes:
1. Linear regression using all measured predictors.
2. A parsimonious quadratic regression using only engine RPM and its squared term.
3. A random forest benchmark to test whether materially nonlinear structure remained after the quadratic specification.

The quadratic model used centered RPM:

```
fuel_consumption_lph ~ engine_rpm_kc + I(engine_rpm_kc**2)  # centered RPM in thousands
```


Centering improves numerical stability and makes the intercept interpretable as expected fuel consumption at mean RPM.

### Model Comparison
```
                           model  test_r2  test_rmse  test_mae  cv_r2_mean  cv_r2_sd  cv_rmse_mean  cv_rmse_sd
        Quadratic RPM regression   0.9960     1.4108    1.1172      0.9952    0.0010        1.4588      0.1178
         Random forest benchmark   0.9951     1.5576    1.2356      0.9948    0.0010        1.5223      0.1108
Linear regression (all features)   0.9572     4.6008    4.0326      0.9551    0.0087        4.4612      0.3117
```


### In-Sample OLS Summaries
Baseline linear model:
```
                             OLS Regression Results                             
================================================================================
Dep. Variable:     fuel_consumption_lph   R-squared:                       0.958
Model:                              OLS   Adj. R-squared:                  0.958
Method:                   Least Squares   F-statistic:                     2701.
Date:                  Tue, 31 Mar 2026   Prob (F-statistic):               0.00
Time:                          17:48:28   Log-Likelihood:                -1741.6
No. Observations:                   600   AIC:                             3495.
Df Residuals:                       594   BIC:                             3522.
Df Model:                             5                                         
Covariance Type:              nonrobust                                         
=====================================================================================
                        coef    std err          t      P>|t|      [0.025      0.975]
-------------------------------------------------------------------------------------
Intercept           -15.4500      7.275     -2.124      0.034     -29.737      -1.163
engine_rpm            0.0136      0.000    115.916      0.000       0.013       0.014
ambient_temp_c       -0.0019      0.023     -0.084      0.933      -0.047       0.043
humidity_pct         -0.0089      0.012     -0.747      0.455      -0.032       0.015
octane_rating        -0.0244      0.080     -0.306      0.759      -0.181       0.132
vehicle_age_years    -0.0009      0.042     -0.021      0.983      -0.083       0.081
==============================================================================
Omnibus:                      106.241   Durbin-Watson:                   1.919
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               34.132
Skew:                           0.341   Prob(JB):                     3.88e-08
Kurtosis:                       2.052   Cond. No.                     1.51e+05
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
[2] The condition number is large, 1.51e+05. This might indicate that there are
strong multicollinearity or other numerical problems.
```


Final quadratic RPM model:
```
                             OLS Regression Results                             
================================================================================
Dep. Variable:     fuel_consumption_lph   R-squared:                       0.995
Model:                              OLS   Adj. R-squared:                  0.995
Method:                   Least Squares   F-statistic:                 6.476e+04
Date:                  Tue, 31 Mar 2026   Prob (F-statistic):               0.00
Time:                          17:48:28   Log-Likelihood:                -1076.4
No. Observations:                   600   AIC:                             2159.
Df Residuals:                       597   BIC:                             2172.
Df Model:                             2                                         
Covariance Type:              nonrobust                                         
=========================================================================================
                            coef    std err          t      P>|t|      [0.025      0.975]
-----------------------------------------------------------------------------------------
Intercept                23.3487      0.091    256.406      0.000      23.170      23.528
engine_rpm_kc            13.6648      0.038    355.409      0.000      13.589      13.740
I(engine_rpm_kc ** 2)     2.0050      0.029     69.936      0.000       1.949       2.061
==============================================================================
Omnibus:                        1.110   Durbin-Watson:                   2.035
Prob(Omnibus):                  0.574   Jarque-Bera (JB):                0.936
Skew:                           0.042   Prob(JB):                        0.626
Kurtosis:                       3.174   Cond. No.                         5.15
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
```


Quadratic RPM model with all additional controls:
```
                            coef   p_value
Intercept              21.451667  0.000000
engine_rpm_kc          13.663057  0.000000
I(engine_rpm_kc ** 2)   2.007587  0.000000
ambient_temp_c          0.010162  0.180001
humidity_pct            0.001160  0.767768
octane_rating           0.015595  0.551896
vehicle_age_years       0.023241  0.091144
```


## Assumption Checks and Validation
### Baseline Linear Model Diagnostics
- Breusch-Pagan test: statistic = 1.795, p = 0.877
- Jarque-Bera test: statistic = 34.132, p = 3.876e-08
- Ramsey RESET test: F = 4883.645, p = 1.911e-288

Interpretation:
- Homoskedasticity is not the main issue.
- Functional form is the issue: the RESET test strongly rejects the linear specification.
- Residual normality is also poor under the purely linear model.

### Final Quadratic RPM Model Diagnostics
- In-sample R^2 = 0.9954
- In-sample RMSE = 1.4552
- Breusch-Pagan test: statistic = 2.960, p = 0.228
- Jarque-Bera test: statistic = 0.936, p = 0.626
- Residual skew = 0.0420
- Residual kurtosis = 3.1743
- Durbin-Watson = 2.035
- Maximum Cook's distance = 0.02378
- Observations with Cook's distance > 4/n: 26

Interpretation:
- Residual variance is consistent with homoskedasticity at conventional thresholds.
- Residual normality is acceptable after adding the quadratic term.
- Independence looks reasonable in the observed row order, though this is still a cross-sectional dataset rather than a true time series.
- Some observations are moderately influential by the 4/n rule, but Cook's distances remain small in absolute terms.

### Final Model Coefficients
```
                            coef   std_err        p_value     ci_low    ci_high
Intercept              23.348722  0.091062   0.000000e+00  23.169882  23.527562
engine_rpm_kc          13.664754  0.038448   0.000000e+00  13.589245  13.740264
I(engine_rpm_kc ** 2)   2.004955  0.028668  8.928558e-290   1.948652   2.061259
```


### Most Influential Observations
```
 test_id  engine_rpm  fuel_consumption_lph  fitted  residual  cooks_d  leverage
     564         876                  5.08   1.576     3.504  0.02378   0.01207
     582        5896                 66.65  69.575    -2.925  0.01610   0.01173
     533        5983                 74.22  71.645     2.575  0.01435   0.01344
     325        5765                 63.52  66.517    -2.997  0.01368   0.00954
     532        5999                 69.57  72.029    -2.459  0.01341   0.01378
     398        3031                 23.04  18.388     4.652  0.01286   0.00377
     335        1039                  5.12   2.197     2.923  0.01276   0.00936
      50        1761                 10.91   6.227     4.683  0.01242   0.00359
     128        5276                 59.81  55.708     4.102  0.01218   0.00458
     117        4979                 45.05  49.610    -4.560  0.01104   0.00337
```


## Conclusions
- `engine_rpm` is the dominant driver of fuel consumption in this dataset.
- The relationship is clearly nonlinear and convex; fuel consumption rises faster at higher RPM.
- Once RPM curvature is modeled, ambient temperature, humidity, octane rating, and vehicle age add little incremental predictive value.
- A simple quadratic RPM model is both accurate and easier to justify than a black-box alternative here.
- The final model passes the main residual diagnostics well enough to support inference and prediction on this dataset.

## Recommended Next Steps
- If this dataset is operational, collect additional covariates tied to engine load or driving conditions; the current non-RPM variables appear weak.
- If the downstream use case requires uncertainty quantification, keep the quadratic OLS model because it is interpretable and diagnostically defensible.
- If the use case is pure prediction and future data may drift, monitor the RPM range closely; extrapolating the quadratic fit beyond the observed `826` to `5999` RPM range would be risky.
