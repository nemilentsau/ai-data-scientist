# Conversion Prediction Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 1,500 |
| Columns | 8 |
| Target | `converted` (binary: 0/1) |
| Conversion rate | 29.3% |
| Missing values | None |
| Duplicates | None |

**Features:**

| Feature | Type | Range / Values | Notes |
|---|---|---|---|
| `session_id` | ID | 1 -- 1500 | Unique identifier (not used in modeling) |
| `ad_budget_usd` | Continuous | 122.70 -- 4998.62 | Approximately uniform distribution |
| `time_of_day_hour` | Continuous | 0.0 -- 24.0 | Hour of session, roughly uniform |
| `channel_score` | Continuous | 0.0 -- 1.0 | Uniform distribution |
| `device` | Categorical | mobile (55.5%), desktop (33.9%), tablet (10.5%) | Three levels |
| `page_load_time_sec` | Continuous | 0.30 -- 15.00 | Right-skewed; see data quality note below |
| `previous_visits` | Integer | 0 -- 10 | Roughly Poisson-like (mean ~3) |
| `converted` | Binary | 0 (70.7%), 1 (29.3%) | Target variable |

## 2. Data Quality Notes

- **No missing values or duplicates.** Data is clean in that regard.
- **`page_load_time_sec` floor at 0.30:** 219 sessions (14.6%) have a page load time of exactly 0.30 seconds. This appears to be a floor/minimum value -- likely a measurement artifact (e.g., cached pages, bots, or a clipping threshold). These rows show a slightly lower conversion rate (26.9% vs 29.7%) but are not dramatically different. They were retained for analysis.
- **`page_load_time_sec` outliers:** 6 sessions exceed 10 seconds (max = 15.0s). None converted. These extreme values are plausible for slow connections and were retained.

## 3. Exploratory Data Analysis

### 3.1 Univariate Relationships with Conversion

| Feature | Correlation with `converted` | Significance |
|---|---|---|
| `time_of_day_hour` | 0.224 | Moderate positive |
| `channel_score` | 0.224 | Moderate positive |
| `previous_visits` | 0.028 | Negligible |
| `ad_budget_usd` | -0.012 | Negligible |
| `page_load_time_sec` | -0.014 | Negligible |

Key observations:
- **`time_of_day_hour`**: Conversion rate increases monotonically from ~11% (midnight--2am) to ~56% (11pm). Later sessions convert at much higher rates.
- **`channel_score`**: Higher scores associate with higher conversion. Sessions with score > 0.66 convert at roughly 2--3x the rate of score < 0.33.
- **`device`**: Minimal differences -- desktop 27.3%, mobile 30.3%, tablet 30.4%.
- **`ad_budget_usd`**: No meaningful relationship with conversion.
- **`page_load_time_sec`**: No meaningful linear relationship with conversion.
- **`previous_visits`**: Weak and noisy relationship; no clear monotonic trend.

### 3.2 Interaction Effect: Time of Day x Channel Score

The strongest pattern in the data is the **synergistic interaction** between time of day and channel score:

| | Low Channel | Medium Channel | High Channel |
|---|---|---|---|
| **Night (0--6h)** | 11.7% | 14.0% | 20.5% |
| **Morning (6--12h)** | 18.1% | 22.9% | 36.7% |
| **Afternoon (12--18h)** | 20.2% | 33.9% | 45.6% |
| **Evening (18--24h)** | 21.2% | 34.3% | **73.7%** |

Sessions in the evening with a high channel score convert at 73.7% -- over 6x the rate of nighttime sessions with a low channel score (11.7%). Neither feature alone produces this effect; it is the combination that drives conversions.

*(See: `plots/06_interaction_heatmap.png`)*

## 4. Modeling

### 4.1 Approach

Three models were trained on an 80/20 stratified train/test split (1200 train, 300 test):

1. **Logistic Regression** -- interpretable baseline
2. **Gradient Boosting** (200 trees, depth=4, lr=0.1, subsample=0.8) -- flexible nonlinear model
3. **Random Forest** (200 trees, depth=10) -- ensemble comparison

All models used the same features: `ad_budget_usd`, `time_of_day_hour`, `channel_score`, `page_load_time_sec`, `previous_visits`, `device` (one-hot), and an engineered interaction term `hour_x_channel = time_of_day_hour * channel_score`.

### 4.2 Results

| Model | CV ROC-AUC (5-fold) | Test ROC-AUC | Test Brier Score | Test Log Loss |
|---|---|---|---|---|
| **Logistic Regression** | **0.697 +/- 0.026** | **0.695** | **0.181** | **0.547** |
| Gradient Boosting | 0.647 +/- 0.021 | 0.650 | 0.207 | 0.632 |
| Random Forest | 0.675 +/- 0.035 | 0.696 | -- | -- |

**Logistic Regression is the best model** -- it matches or outperforms the tree-based models on all metrics, is better calibrated, and is fully interpretable. The data's dominant signal (the interaction term) is linear in the log-odds space, so there is no benefit to more complex models. Gradient Boosting actually overfits slightly despite regularization.

### 4.3 Logistic Regression: Statistical Details (Statsmodels)

Full-sample logistic regression (n=1500):

| Predictor | Coefficient | Odds Ratio | 95% CI (OR) | p-value |
|---|---|---|---|---|
| intercept | -1.989 | 0.137 | [0.072, 0.261] | < 0.001 *** |
| `hour_x_channel` | **0.142** | **1.152** | **[1.080, 1.229]** | **< 0.001 ***** |
| `previous_visits` | 0.047 | 1.048 | [0.982, 1.118] | 0.161 |
| `channel_score` | 0.063 | 1.065 | [0.425, 2.673] | 0.893 |
| `time_of_day_hour` | 0.004 | 1.004 | [0.967, 1.042] | 0.848 |
| `device_mobile` | 0.051 | 1.052 | [0.811, 1.365] | 0.701 |
| `ad_budget_usd` | -0.00002 | 1.000 | [1.000, 1.000] | 0.629 |
| `page_load_time_sec` | -0.009 | 0.991 | [0.931, 1.056] | 0.785 |
| `device_tablet` | 0.034 | 1.035 | [0.679, 1.578] | 0.874 |

**Only `hour_x_channel` is statistically significant** (p < 0.001). Its odds ratio of 1.152 means each unit increase in the product (time_of_day_hour x channel_score) increases the odds of conversion by ~15.2%.

- Pseudo R-squared: 0.099 (modest but typical for behavioral conversion data)
- Hosmer-Lemeshow test: chi2 = 6.79, p = 0.56 (adequate fit; p > 0.05 indicates no significant lack of fit)

### 4.4 Model Comparison: Interaction Term

| Metric | With Interaction | Without Interaction |
|---|---|---|
| AIC | **1652.7** | 1669.5 |
| BIC | **1700.5** | 1712.0 |
| Likelihood Ratio Test | chi2 = 18.81, **p = 1.44e-05** | -- |

The interaction term is highly significant and improves both AIC and BIC. Removing it degrades the model substantially.

### 4.5 Assumption Checks

- **Multicollinearity (VIF):** All base features have VIF < 4 -- no multicollinearity concerns.
- **Linearity of log-odds:** Empirical logit plots show approximately linear relationships for key features. The interaction term captures the main nonlinearity.
- **Calibration:** Logistic Regression shows good calibration across the probability range (see `plots/09_calibration.png`). Gradient Boosting is poorly calibrated.
- **Independence:** Sessions appear independent (unique session IDs, no repeated-measures structure apparent).

## 5. Key Findings

### Finding 1: Conversion is driven by the synergy of time-of-day and channel quality
The product of `time_of_day_hour` and `channel_score` is the only statistically significant predictor. Evening sessions through high-quality channels convert at dramatically higher rates (up to 73.7%), while early-morning sessions through low-quality channels rarely convert (11.7%).

### Finding 2: Ad budget does not predict conversion
Despite a wide range ($123 -- $4,999), `ad_budget_usd` has no relationship with conversion (r = -0.012, p = 0.63). Higher spending does not translate to higher conversion rates in this dataset.

### Finding 3: Device type is irrelevant
Desktop (27.3%), mobile (30.3%), and tablet (30.4%) have nearly identical conversion rates. Device is not a significant predictor in any model.

### Finding 4: Page load time and visit history have negligible effects
Neither `page_load_time_sec` nor `previous_visits` significantly predicts conversion. The 14.6% of sessions with a 0.30s floor value show no meaningful difference in conversion behavior.

### Finding 5: Simple models suffice
Logistic Regression with a single interaction term outperforms Gradient Boosting and matches Random Forest. The underlying signal is simple and linear in log-odds space -- complexity adds noise, not value.

## 6. Recommendations

1. **Prioritize evening + high-channel-score traffic.** The conversion rate for this segment is 5--7x the baseline. Campaigns and budgets should be concentrated here.
2. **Investigate ad budget allocation.** Budget has zero predictive value for conversion. Either the budget variable does not capture the right spend dimension, or spend is not being deployed in a way that influences session-level outcomes.
3. **Do not optimize by device type.** Device differences are not statistically significant. Device-specific strategies are unlikely to improve conversion.
4. **Consider the page load floor value.** The 14.6% of sessions at exactly 0.30s warrants investigation with the engineering team -- this may be a logging artifact that obscures the true distribution.

## 7. Limitations

- **Pseudo R-squared = 0.10 and ROC-AUC = 0.70:** The model captures a real pattern but explains only ~10% of conversion variance. Substantial unexplained variation remains, likely driven by unobserved factors (ad content, user intent, landing page quality, etc.).
- **Observational data:** All relationships are correlational. The time-of-day effect could reflect user behavior patterns (e.g., more motivated users browse in the evening) rather than a causal effect of timing.
- **Single dataset, no temporal validation:** Results should be validated on held-out time periods before operational deployment.

## 8. Plots Index

| File | Description |
|---|---|
| `plots/01_distributions.png` | Feature distributions by conversion status |
| `plots/02_correlation.png` | Correlation heatmap |
| `plots/03_conv_by_hour.png` | Conversion rate by time of day |
| `plots/04_conv_by_channel.png` | Conversion rate by channel score |
| `plots/05_page_load_time.png` | Page load time distribution and outliers |
| `plots/06_interaction_heatmap.png` | Conversion rate: time of day x channel score |
| `plots/07_pairplot.png` | Pairplot of key features |
| `plots/08_roc_pr_curves.png` | ROC and Precision-Recall curves (3 models) |
| `plots/09_calibration.png` | Calibration curves |
| `plots/10_feature_importance.png` | Gradient Boosting feature importances |
| `plots/11_confusion_matrices.png` | Confusion matrices |
| `plots/12_linearity_check.png` | Linearity of log-odds assumption check |
