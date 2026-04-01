# Conversion Prediction Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 1,500 |
| Features | 7 (5 numeric, 1 categorical, 1 binary target) |
| Target | `converted` (binary: 0/1) |
| Conversion rate | 29.3% (439 conversions) |
| Missing values | None |
| Duplicate rows | None |

**Features:**

| Feature | Type | Range | Notes |
|---|---|---|---|
| `ad_budget_usd` | float | 122.7 -- 4,998.6 | Uniformly distributed, symmetric (skew = -0.007) |
| `time_of_day_hour` | float | 0.0 -- 24.0 | Uniformly distributed across the day |
| `channel_score` | float | 0.0 -- 1.0 | Uniformly distributed quality/relevance score |
| `page_load_time_sec` | float | 0.3 -- 15.0 | Right-skewed (skew = 1.99); 219 observations at floor value 0.3s |
| `previous_visits` | int | 0 -- 10 | Approximately Poisson-like, median = 3 |
| `device` | categorical | mobile (56%), desktop (34%), tablet (10%) | Roughly representative of web traffic |

### Data Quality Notes

- **No nulls or duplicates.** The data is clean.
- **Floor value in `page_load_time_sec`:** 219 observations (14.6%) have a value of exactly 0.3 seconds, suggesting a measurement floor or cached-page artifact. This does not appear to bias results since page load time is not a meaningful predictor.
- **Feature independence:** All predictor-predictor correlations are near zero (max |r| = 0.062), indicating the features were generated or collected independently.

## 2. Exploratory Data Analysis

### Key Findings

#### Strong predictors of conversion:

1. **`channel_score`** (r = 0.224 with conversion): Monotonic positive relationship. Conversion rate rises from 17.9% (bottom quartile) to 43.5% (top quartile).

2. **`time_of_day_hour`** (r = 0.224 with conversion): Clear monotonic increase through the day -- Night (0-6h): 15.4%, Morning (6-12h): 25.7%, Afternoon (12-18h): 34.0%, Evening (18-24h): 42.0%.

3. **Interaction between time and channel score:** The strongest conversion rates occur when both factors are high simultaneously. Evening sessions with high channel scores convert at 61.3%, compared to just 18.7% for non-evening sessions with low channel scores. This multiplicative interaction is the dominant pattern in the data.

#### Non-predictors:

4. **`ad_budget_usd`** (r = -0.012): Essentially uncorrelated with conversion. Conversion rate is flat across all budget quartiles (~29%). Ad budget does not influence conversion likelihood in this data.

5. **`page_load_time_sec`** (r = -0.014): No meaningful relationship with conversion at any threshold tested (1s, 2s, 3s, 5s). Despite conventional wisdom about page speed affecting conversions, this dataset shows no such effect.

6. **`device`** (conversion rates: desktop 27.3%, mobile 30.3%, tablet 30.4%): Minimal variation, not statistically significant.

7. **`previous_visits`** (r = 0.028): Weak, noisy relationship. No consistent trend.

See: `plots/01_feature_distributions.png`, `plots/03_conversion_by_features.png`, `plots/09_interaction_heatmap.png`

## 3. Modeling

### Approach

Given a binary classification target, four models were evaluated using stratified 5-fold cross-validation on an 80/20 train-test split (stratified by target):

| Model | CV ROC-AUC | Test ROC-AUC | Test Brier Score |
|---|---|---|---|
| **Logistic Regression** | **0.691 +/- 0.024** | **0.698** | **0.184** |
| LR + Interaction Term | 0.697 +/- 0.026 | 0.695 | 0.181 |
| Random Forest (depth=6) | 0.682 +/- 0.020 | 0.695 | 0.182 |
| Gradient Boosting | 0.649 +/- 0.015 | 0.650 | 0.200 |

**Selected model: Logistic Regression.** It achieves the best test AUC, is the most interpretable, and its assumptions are well-satisfied (see Section 4). Tree-based models do not improve performance, confirming that the relationships are approximately linear in log-odds and that complex interactions beyond time x channel are not present.

### Logistic Regression Coefficients (statsmodels)

| Feature | Coefficient | Std. Error | z-value | p-value | Significant? |
|---|---|---|---|---|---|
| `channel_score` | +1.893 | 0.219 | 8.63 | <0.001 | Yes |
| `time_of_day_hour` | +0.079 | 0.009 | 8.72 | <0.001 | Yes |
| `ad_budget_usd` | -0.00002 | 0.00004 | -0.53 | 0.597 | No |
| `page_load_time_sec` | -0.011 | 0.032 | -0.35 | 0.729 | No |
| `previous_visits` | +0.046 | 0.033 | 1.39 | 0.165 | No |
| `device_mobile` | +0.069 | 0.132 | 0.52 | 0.601 | No |
| `device_tablet` | +0.060 | 0.212 | 0.28 | 0.777 | No |
| Intercept | -2.976 | 0.259 | -11.48 | <0.001 | -- |

**Interpretation:**
- A 1-unit increase in `channel_score` (0 to 1 scale) multiplies the odds of conversion by exp(1.893) = **6.6x**.
- Each additional hour later in the day multiplies the odds by exp(0.079) = **1.08x** (i.e., +8% per hour, or roughly 6x from midnight to midnight).
- All other features have non-significant coefficients with p > 0.15.

### Classification Performance (Test Set, default 0.5 threshold)

|  | Precision | Recall | F1 |
|---|---|---|---|
| Not Converted (0) | 0.74 | 0.95 | 0.83 |
| Converted (1) | 0.63 | 0.22 | 0.32 |
| **Accuracy** | | | **0.73** |

The model is conservative at the default threshold -- high precision for class 0 but low recall for class 1. This is expected given the moderate discriminative power (AUC ~0.70) and class imbalance. Threshold tuning could improve recall at the cost of precision depending on business objectives.

See: `plots/06_roc_pr_curves.png`, `plots/07_calibration.png`, `plots/10_confusion_matrix.png`

## 4. Assumption Checks

All standard logistic regression assumptions were formally tested:

| Assumption | Test | Result | Verdict |
|---|---|---|---|
| Linearity of log-odds | Box-Tidwell | `time_of_day_hour`: p=0.315; `channel_score`: p=0.947 | Satisfied |
| No multicollinearity | VIF | All VIF <= 1.18 | Satisfied |
| Adequate sample size | Events per variable | 439/7 = 62.7 (>>10) | Satisfied |
| No influential outliers | Cook's distance | Max = 0.009; 4.3% above 4/n threshold | Satisfied |
| Goodness of fit | Hosmer-Lemeshow | Chi-sq = 12.3, p = 0.138 | Acceptable fit |

The logistic regression assumptions are well-satisfied. The model is appropriate for this data.

## 5. Key Conclusions

1. **Only two features drive conversion: `channel_score` and `time_of_day_hour`.** Together they explain essentially all the predictable variance. Their interaction amplifies the effect -- evening + high-quality channels yield the highest conversion rates (>60%).

2. **Ad budget does not predict conversion.** Despite ranging from $123 to $5,000, budget has zero relationship with whether a session converts. This is the most actionable (and potentially surprising) finding.

3. **Page load time does not predict conversion** in this dataset, despite the common expectation that faster pages convert better.

4. **Device type and visit history are not significant predictors** after accounting for channel score and time of day.

5. **Model performance is moderate (AUC ~0.70).** This suggests substantial unexplained variance -- likely driven by factors not captured in this dataset (e.g., user demographics, ad creative quality, landing page content, product pricing). The two significant predictors provide meaningful lift over random, but the model should not be relied upon for high-stakes individual predictions.

6. **The data appears well-structured and clean**, with uniform feature distributions and near-zero inter-feature correlations, suggesting a controlled or synthetic data-generating process.

## 6. Recommendations

- **Optimize channel selection and timing:** Focus ad spend on high-scoring channels during evening hours when conversion probability is highest.
- **Re-evaluate ad budget allocation:** Since budget shows no correlation with conversion, investigate whether budget is being allocated effectively or whether the spend-conversion relationship is mediated by unmeasured factors.
- **Collect additional features:** The moderate AUC suggests important predictors are missing. User demographics, creative/content variables, and competitive context would likely improve predictions.
- **Consider threshold tuning:** If the business cost of missing a conversion is high relative to false positives, lower the classification threshold to increase recall.

## 7. Plots

| File | Description |
|---|---|
| `plots/01_feature_distributions.png` | Feature distributions split by conversion status |
| `plots/02_correlation_heatmap.png` | Pairwise correlation matrix |
| `plots/03_conversion_by_features.png` | Conversion rate by time-of-day and channel score bins |
| `plots/04_page_load_time.png` | Page load time distribution (raw and log-transformed) |
| `plots/05_pairwise_relationships.png` | Pairwise feature-target relationships |
| `plots/06_roc_pr_curves.png` | ROC and Precision-Recall curves |
| `plots/07_calibration.png` | Calibration curves and predicted probability distributions |
| `plots/08_feature_importance.png` | Feature importance comparison (LR vs RF) |
| `plots/09_interaction_heatmap.png` | Conversion rate heatmap: channel score x time of day |
| `plots/10_confusion_matrix.png` | Confusion matrix for logistic regression on test set |
