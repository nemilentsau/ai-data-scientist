# Fraud Detection Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 3,000 |
| Columns | 8 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Fraud rate | 5.00% (150 fraud, 2,850 non-fraud) |

**Features:**
- `transaction_id` — unique identifier (dropped for modeling)
- `amount_usd` — transaction amount in USD (continuous, range: $1.00 - $4,565.29)
- `hour_of_day` — hour of transaction (integer 0-23)
- `merchant_category` — 7 categories: Grocery, Travel, ATM, Gas, Restaurant, Online, Electronics (roughly balanced at ~400-470 each)
- `card_age_months` — age of the card in months (integer 1-119)
- `distance_from_home_km` — distance of transaction from cardholder's home (continuous, 0 - 286.1 km)
- `is_international` — binary flag for international transactions (15.3% international)
- `is_fraud` — target variable (binary)

**Data quality:** The dataset is clean with no nulls, no negative values, no out-of-range values, and no duplicates. All features have plausible ranges.

## 2. Exploratory Data Analysis

### 2.1 Key Discriminating Features

**Distance from home** is by far the strongest predictor of fraud:
- Fraud transactions: median 34.5 km, mean 51.4 km
- Non-fraud transactions: median 6.9 km, mean 10.1 km
- Cohen's d = 2.68 (very large effect); Mann-Whitney p < 1e-39

**Transaction amount** is the second-strongest predictor:
- Fraud transactions: median $86.64, mean $162.59
- Non-fraud transactions: median $34.12, mean $70.27
- Cohen's d = 0.61 (medium effect); Mann-Whitney p < 1e-20

**Hour of day** has a weak but statistically significant association (Cohen's d = -0.29, p = 0.0095). Fraud skews slightly earlier in the day.

**Card age** has no meaningful association with fraud (Cohen's d = -0.02, p = 0.86).

### 2.2 Categorical Features

**Merchant category** does not significantly discriminate fraud (chi-squared p = 0.28). Restaurant (6.3%) and ATM (6.0%) have slightly elevated fraud rates, while Gas (3.3%) and Grocery (3.6%) are slightly below average, but these differences are not statistically significant.

**International status** has zero association with fraud (chi-squared p = 1.00). The fraud rate is 5.0% for both domestic and international transactions. This is a non-informative feature.

### 2.3 Correlation Structure

All features have low inter-correlations (max pairwise r < 0.05 among numeric features). There is no multicollinearity concern (all VIF values < 1.8). This means each feature provides independent information, which is favorable for linear models.

### 2.4 Distribution Notes

- `amount_usd` is heavily right-skewed (skew driven by high-value fraud transactions up to $4,565)
- `distance_from_home_km` is also right-skewed, more so for fraud
- The scatter plots (plot 08) show fraud transactions concentrated in the high-distance, high-amount region, though overlap with non-fraud exists

## 3. Modeling

### 3.1 Approach

Given the binary classification task with 5% class imbalance, I trained three models using **stratified 5-fold cross-validation** to get unbiased performance estimates. Merchant category was one-hot encoded (6 dummies, drop-first). Logistic Regression used standardized features; tree-based models used raw features.

- **Logistic Regression** — `class_weight='balanced'` to handle imbalance
- **Random Forest** — 200 trees, `class_weight='balanced'`
- **Gradient Boosting** — 200 trees, max_depth=4, learning_rate=0.1

### 3.2 Results (5-fold cross-validated)

| Model | ROC-AUC | PR-AUC | F1 (Fraud) | Precision | Recall |
|---|---|---|---|---|---|
| Logistic Regression | 0.842 | 0.505 | 0.330 | 0.22 | 0.71 |
| Random Forest | 0.868 | 0.545 | 0.424 | 0.81 | 0.29 |
| Gradient Boosting | 0.851 | 0.521 | 0.490 | 0.65 | 0.39 |

**Interpretation:**
- **Random Forest** has the best discriminative ability (ROC-AUC = 0.868, PR-AUC = 0.545) but at the default 0.5 threshold is highly conservative (81% precision, only 29% recall).
- **Gradient Boosting** achieves the best F1 balance at the default threshold (0.49) with 65% precision and 39% recall.
- **Logistic Regression** with balanced weights favors recall (71%) at the cost of very low precision (22%), flagging too many legitimate transactions.
- All models achieve ROC-AUC > 0.84, meaning the features provide strong signal, but the 5% base rate makes the precision-recall tradeoff challenging.

### 3.3 Threshold Optimization

Tuning the decision threshold for Gradient Boosting, the optimal F1 is **0.528** at threshold **0.29** (lowering from the default 0.50). In a real-world deployment, the threshold should be chosen based on the relative cost of false positives (blocking legitimate transactions) vs. false negatives (missing fraud).

### 3.4 Model Calibration

The Gradient Boosting model shows reasonable calibration (Brier score = 0.039), meaning predicted probabilities roughly correspond to actual fraud rates. The calibration curve shows slight overconfidence in the mid-range probabilities.

### 3.5 Feature Importance

Across all models, the feature ranking is consistent:

| Rank | Feature | RF Importance | LR Coefficient (std) |
|---|---|---|---|
| 1 | distance_from_home_km | 0.412 | +1.361 |
| 2 | amount_usd | 0.236 | +0.667 |
| 3 | hour_of_day | 0.161 | -0.199 |
| 4 | card_age_months | 0.115 | -0.014 |
| 5-11 | Merchant categories + is_international | <0.013 each | <0.27 each |

**Distance from home** alone accounts for 41% of the Random Forest's splitting power and has the largest logistic regression coefficient. **Amount** is the second driver. Merchant category and international status contribute negligibly.

## 4. Key Findings

1. **Distance from home is the dominant fraud signal.** Fraudulent transactions occur dramatically farther from the cardholder's home (median 35 km vs 7 km). This single feature provides most of the predictive power.

2. **Higher-value transactions are more likely to be fraudulent.** Fraud amounts are roughly 2.5x higher on average than legitimate transactions.

3. **International status is uninformative.** Despite intuition, international transactions have identical fraud rates to domestic ones in this dataset.

4. **Merchant category has no statistically significant effect.** Slight variations exist (Restaurant/ATM slightly higher) but are not significant.

5. **The class imbalance (5% fraud) makes high precision difficult.** Even the best model (Gradient Boosting at optimized threshold) achieves F1 of only 0.53. In production, this would need to be supplemented with additional features (e.g., transaction velocity, device fingerprinting, behavioral patterns).

6. **No data quality issues were found.** The dataset is clean with no nulls, outliers beyond explainable high-value transactions, or impossible values.

## 5. Model Assumptions Check

- **Multicollinearity:** VIF values all < 1.8 — no issues.
- **Logistic regression linearity:** The log-odds relationship with distance and amount is approximately monotonic, though the right-skewed distributions suggest a log-transform could improve the linear model.
- **Independence:** Transactions appear independent (no repeated card IDs or temporal sequence structure in the data).
- **Sample size adequacy:** With 150 fraud cases and ~11 features, we have roughly 14 events per variable, meeting the minimum of 10 EPV recommended for logistic regression.

## 6. Recommendations

- **For deployment:** Use Gradient Boosting with threshold tuned to business-specific cost ratios. At threshold 0.29, expect ~53% of flagged transactions to be fraud, catching ~50% of all fraud.
- **For improvement:** Collect additional features — transaction velocity (number of recent transactions), device/IP metadata, time since last transaction, and historical spending patterns would likely improve discrimination significantly.
- **Monitoring:** Track the distribution of `distance_from_home_km` over time, since it dominates predictions. If this feature degrades (e.g., due to GPS inaccuracy), model performance will drop substantially.

## 7. Plots Reference

| Plot | File |
|---|---|
| Target distribution | `plots/01_target_distribution.png` |
| Amount distribution by fraud | `plots/02_amount_distribution.png` |
| Feature boxplots by fraud | `plots/03_boxplots_by_fraud.png` |
| Fraud rate by merchant category | `plots/04_fraud_rate_by_category.png` |
| Fraud rate by hour of day | `plots/05_fraud_rate_by_hour.png` |
| Correlation heatmap | `plots/06_correlation_heatmap.png` |
| International vs fraud | `plots/07_international_vs_fraud.png` |
| Pairwise scatter plots | `plots/08_pairwise_scatter.png` |
| ROC and PR curves | `plots/09_roc_pr_curves.png` |
| Confusion matrices | `plots/10_confusion_matrices.png` |
| Feature importance (RF) | `plots/11_feature_importance.png` |
| Calibration curve | `plots/12_calibration_curve.png` |
| Threshold analysis | `plots/13_threshold_analysis.png` |
| Predicted probability distribution | `plots/14_probability_distribution.png` |
