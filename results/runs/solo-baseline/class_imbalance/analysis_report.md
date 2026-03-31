# Fraud Detection Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 3,000 transactions |
| Features | 6 predictive + 1 ID + 1 target |
| Missing values | 0 (none) |
| Duplicate rows | 0 |
| Target variable | `is_fraud` (binary) |
| Fraud rate | 5.0% (150 fraud / 2,850 legitimate) |

### Feature Summary

| Feature | Type | Description |
|---|---|---|
| `amount_usd` | Continuous | Transaction amount; right-skewed (median $36, mean $75, max $4,565) |
| `hour_of_day` | Integer (0-23) | Hour of transaction |
| `merchant_category` | Categorical (7 levels) | Grocery, Travel, ATM, Gas, Restaurant, Online, Electronics |
| `card_age_months` | Integer | Age of the card; uniform distribution (1-120) |
| `distance_from_home_km` | Continuous | Distance from cardholder's home; right-skewed |
| `is_international` | Binary | Whether the transaction is international (15.3% are) |

### Data Quality Assessment

- **No missing values** across all columns.
- **No duplicates** in transaction IDs or full rows.
- **No multicollinearity**: all VIF values ~1.0, indicating fully independent features.
- **amount_usd** has a heavy right tail (10.2% of transactions exceed the IQR upper fence of $171).
- Data appears synthetically generated (uniform card age distribution, clean integer hours).

---

## 2. Exploratory Data Analysis

### 2.1 Key Discriminating Features

**Distance from home is the dominant fraud signal** (Cohen's d = 2.68, a very large effect):
- Fraud transactions: median 34.5 km, mean 51.4 km
- Legitimate transactions: median 6.9 km, mean 10.1 km
- Mann-Whitney U test: p = 4.1e-40

**Transaction amount is a moderate signal** (Cohen's d = 0.61, medium effect):
- Fraud transactions: median $86.64, mean $162.59
- Legitimate transactions: median $34.12, mean $70.27
- Mann-Whitney U test: p = 3.9e-21

**Hour of day has a small but significant effect** (Cohen's d = -0.29):
- Fraud is heavily concentrated in early morning hours (0-6 AM): 19.2% fraud rate vs. 2.9-6.2% in other periods
- Mann-Whitney U test: p = 9.5e-03

### 2.2 Non-Discriminating Features

**Card age shows no relationship with fraud** (d = -0.016, p = 0.86). Fraud is equally likely for new and old cards.

**Merchant category differences are not statistically significant** (chi-squared p = 0.28). Rates range from 3.3% (Gas) to 6.3% (Restaurant), but this variation is consistent with random chance given sample sizes.

**International status has zero predictive value** (chi-squared p = 1.00). Fraud rate is 5.0% for both domestic and international transactions.

### 2.3 Interaction: Amount x Distance

The scatter plot (plot 04) reveals that fraud concentrates in the high-distance region. Within that region, higher amounts are more commonly fraudulent. There is no single clean decision boundary -- the classes overlap, particularly at moderate distances (10-30 km).

*(See plots: 01_feature_distributions.png, 02_fraud_rates.png, 03_correlation_heatmap.png, 04_amount_vs_distance.png, 05_boxplots.png, 10_class_imbalance.png)*

---

## 3. Modeling

### 3.1 Approach

- **Task**: Binary classification (fraud vs. legitimate)
- **Class imbalance handling**: `class_weight='balanced'` for Logistic Regression and Random Forest (inverse-frequency weighting)
- **Evaluation**: Stratified 5-fold cross-validation with predictions aggregated across all folds
- **Metrics**: ROC-AUC (discrimination), Average Precision (ranking under imbalance), F1 score (threshold-dependent), Brier score (calibration)

Three models were compared:

1. **Logistic Regression** -- linear baseline, fully interpretable
2. **Random Forest** (200 trees, max_depth=10) -- captures non-linear patterns
3. **Gradient Boosting** (200 estimators, max_depth=4) -- sequential ensemble

### 3.2 Results

| Model | ROC-AUC | Avg Precision | F1 | Brier Score |
|---|---|---|---|---|
| Logistic Regression | 0.842 | 0.505 | 0.331 | 0.123 |
| **Random Forest** | **0.872** | 0.506 | 0.485 | **0.038** |
| Gradient Boosting | 0.851 | **0.517** | **0.498** | 0.035 |

**Key observations:**

- **Random Forest achieves the best discrimination** (ROC-AUC = 0.872).
- **Gradient Boosting has the best F1 and Average Precision**, making it the strongest at the default threshold.
- **Logistic Regression trades specificity for recall** (71% recall but only 22% precision) due to class-weight rebalancing. It flags many false positives.
- Tree ensembles are better calibrated (Brier ~0.04 vs. 0.12 for LR).

### 3.3 Confusion Matrix Summary (5-Fold CV)

| Model | True Neg | False Pos | False Neg | True Pos | Recall | Precision |
|---|---|---|---|---|---|---|
| Logistic Regression | 2,465 | 385 | 44 | 106 | 70.7% | 21.6% |
| Random Forest | 2,825 | 25 | 94 | 56 | 37.3% | 69.1% |
| Gradient Boosting | 2,819 | 31 | 90 | 60 | 40.0% | 65.9% |

The precision-recall trade-off is stark: LR catches more fraud but with massive false alarm volume. The tree models are conservative but more precise. The right choice depends on the cost of false positives vs. missed fraud.

### 3.4 Feature Importance

**Both models agree on feature ranking:**

| Rank | Logistic Regression (coef) | Random Forest (importance) |
|---|---|---|
| 1 | distance_from_home_km (+1.36) | distance_from_home_km (0.426) |
| 2 | amount_usd (+0.67) | amount_usd (0.245) |
| 3 | hour_of_day (-0.20) | hour_of_day (0.158) |
| 4 | is_international (-0.10) | card_age_months (0.103) |
| 5 | card_age_months (-0.01) | is_international (0.012) |

Distance alone accounts for 43% of the Random Forest's splitting decisions. Amount and hour contribute meaningfully. Card age, international flag, and merchant category are near-irrelevant.

*(See plots: 06_model_curves.png, 07_feature_importance.png, 08_confusion_matrices.png, 09_calibration.png)*

---

## 4. Assumption Checks and Validation

### 4.1 Logistic Regression Assumptions

- **Linearity of log-odds**: Partially met. Distance and amount have monotonic relationships with fraud, but the amount relationship is non-linear (the log-odds curve flattens). This limits LR performance.
- **Independence**: Transactions appear independent (no time-series structure evident).
- **No multicollinearity**: Confirmed. All VIF values are ~1.0.
- **Sample size**: Adequate. With 150 fraud cases and ~11 features (after encoding), the events-per-variable ratio is ~14, above the commonly recommended minimum of 10.

### 4.2 Class Imbalance

The 19:1 imbalance ratio is moderate. Strategies used:
- `class_weight='balanced'` for LR and RF (upweights minority class in the loss function)
- Average Precision and ROC-AUC as primary metrics (insensitive to class prevalence)
- Stratified cross-validation (preserves class ratios in each fold)

### 4.3 Calibration

The calibration plot (plot 09) shows:
- **Gradient Boosting**: best calibrated, predicted probabilities closely match observed fraud rates
- **Random Forest**: slightly underestimates probabilities in the 0.2-0.5 range
- **Logistic Regression**: systematically over-predicts (many predictions in the 0.2-0.6 range for non-fraud cases), explaining its high false positive rate

---

## 5. Key Findings

1. **Distance from home is the single most powerful fraud indicator.** Fraudulent transactions occur at a median of 34.5 km from home vs. 6.9 km for legitimate ones. This one feature provides most of the model's discriminative power.

2. **Transaction amount is a secondary signal.** Fraud transactions are roughly 2.5x larger (median $87 vs. $34), but the distributions overlap considerably.

3. **Early morning transactions are suspicious.** The 0-6 AM window has a 19.2% fraud rate -- nearly 4x the overall rate. This likely reflects transactions occurring while the cardholder is asleep.

4. **International status and merchant category are not useful predictors.** Neither achieves statistical significance in distinguishing fraud from legitimate transactions.

5. **Model performance is moderate but meaningful.** The best model (Random Forest, ROC-AUC = 0.872) can meaningfully rank transactions by risk, but the 5% base rate and overlapping feature distributions limit achievable precision-recall trade-offs.

6. **Model selection depends on operational priorities:**
   - **Maximize fraud detection** (at cost of false alarms): Logistic Regression catches 71% of fraud
   - **Minimize false alarms** (at cost of missed fraud): Gradient Boosting achieves 66% precision
   - **Best overall discrimination**: Random Forest (ROC-AUC = 0.872)

---

## 6. Recommendations

- **Threshold tuning**: All models were evaluated at the default 0.5 threshold. In production, the threshold should be tuned based on the cost ratio of missed fraud to false alarms.
- **Feature engineering**: Log-transforming `amount_usd` and creating interaction features (e.g., distance x amount, distance x late_night) could improve LR performance.
- **Additional data**: Transaction velocity (frequency in recent hours), device fingerprint, and historical spending patterns would likely improve discrimination substantially.
- **Monitoring**: The 0-6 AM hour window warrants dedicated monitoring rules independent of the ML model.

---

## Appendix: Plots

| File | Description |
|---|---|
| `plots/01_feature_distributions.png` | Histograms of all features split by fraud status |
| `plots/02_fraud_rates.png` | Fraud rate by merchant category and hour of day |
| `plots/03_correlation_heatmap.png` | Pairwise correlation matrix |
| `plots/04_amount_vs_distance.png` | Scatter plot of amount vs distance, colored by fraud |
| `plots/05_boxplots.png` | Box plots comparing fraud vs legitimate distributions |
| `plots/06_model_curves.png` | ROC and Precision-Recall curves for all models |
| `plots/07_feature_importance.png` | LR coefficients and RF feature importances |
| `plots/08_confusion_matrices.png` | Confusion matrices for all three models |
| `plots/09_calibration.png` | Probability calibration plot |
| `plots/10_class_imbalance.png` | Class distribution visualization |
