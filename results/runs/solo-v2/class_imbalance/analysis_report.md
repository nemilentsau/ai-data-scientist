# Credit Card Fraud Detection — Analysis Report

## 1. Dataset Overview

The dataset contains **3,000 credit card transactions** with 8 fields: transaction ID, amount (USD), hour of day, merchant category, card age (months), distance from home (km), international flag, and a binary fraud label.

**Key characteristics:**
- **Fraud prevalence:** 150 of 3,000 transactions (5.0%) are fraudulent — a moderate class imbalance.
- **No missing values.** All fields are complete.
- **7 merchant categories:** Grocery (469), Travel (444), ATM (431), Gas (430), Restaurant (427), Online (405), Electronics (394) — roughly balanced.
- **Amount distribution:** Right-skewed (median $36, mean $75, max $4,565). 95th percentile is $263.
- **Distance from home:** Right-skewed (median 7.3 km, mean 12.2 km, max 286 km).

## 2. Key Findings

### Finding 1: Distance from home is the dominant fraud signal

Fraudulent transactions occur dramatically farther from the cardholder's home than legitimate ones:

| Metric | Legitimate | Fraud |
|--------|-----------|-------|
| Median distance | 6.9 km | 34.5 km |
| Mean distance | 10.1 km | 51.4 km |
| IQR | 2.9–14.2 km | 15.1–70.9 km |

- **Effect size:** Cohen's d = 2.68 (very large — well above the 0.8 threshold for "large").
- **Statistical test:** Mann-Whitney U test, p < 2 × 10⁻⁴⁰.
- **Correlation with fraud:** r = 0.50 — far exceeding all other features.
- **Permutation importance** in a Random Forest model: 0.065, compared to ≤ 0.004 for every other feature — **distance is ~15x more important than any other predictor**.

The fraud rate rises sharply with distance: the bottom 8 deciles of distance (up to ~20 km) have fraud rates below 5%, while the top decile (~65 km mean) has a fraud rate of ~28%.

Even a simple threshold rule — flag transactions > 50 km from home — achieves 75% precision and 36% recall.

*See: `plots/01_distance_by_fraud.png`, `plots/09_distance_decile_and_calibration.png`*

### Finding 2: Nighttime transactions have 8x higher fraud odds

Transactions during nighttime hours (midnight to 5 AM) have a fraud rate of **19.2%**, compared to **4.0%** during daytime (6 AM–11 PM). The peak hour is 1 AM, with a ~44% fraud rate.

This effect is **independent of distance** — nighttime transactions have similar distance distributions to daytime ones (night median: 7.9 km, day median: 7.3 km). In a multivariate logistic regression controlling for distance and amount, nighttime remains highly significant:

- **Odds ratio:** 8.0 (95% CI: 4.8–13.4), p < 3 × 10⁻¹⁵

However, nighttime accounts for only 203 of 3,000 transactions (6.8%), so while the *rate* is high, the absolute number of nighttime fraud cases (39 of 150) is modest.

*See: `plots/03_hour_of_day.png`, `plots/06_night_vs_day_scatter.png`*

### Finding 3: Transaction amount is a moderate fraud indicator

Fraudulent transactions are significantly larger:

| Metric | Legitimate | Fraud |
|--------|-----------|-------|
| Median amount | $34.12 | $86.64 |
| Mean amount | $70.27 | $162.59 |

- **Effect size:** Cohen's d = 0.61 (medium).
- **Odds ratio** for log(amount) in logistic regression: 2.25 (95% CI: 1.86–2.73), p < 1 × 10⁻¹⁶.

The effect is real but much weaker than distance. Amount alone is not a reliable fraud indicator — many legitimate transactions are high-value.

*See: `plots/02_amount_by_fraud.png`*

### Finding 4: Distance and amount interact multiplicatively

A heatmap of fraud rates across distance and amount bins reveals a clear gradient:

| Distance \ Amount | $0–20 | $20–50 | $50–100 | $100–200 | $200+ |
|-------------------|-------|--------|---------|----------|-------|
| 0–5 km | 0.3% | 0.3% | 0.0% | 0.0% | 0.0% |
| 5–15 km | 1.0% | 1.2% | 4.7% | 1.4% | 4.4% |
| 15–30 km | 2.2% | 2.7% | 4.8% | 3.5% | 4.4% |
| 30–60 km | 8.3% | 9.8% | 14.5% | 43.8% | 3.8%* |
| 60+ km | 70.0% | 72.7% | 100%* | 82.4% | 100%* |

(*Small sample sizes — interpret with caution.)

Transactions that are both far from home (>60 km) and non-trivial in amount have fraud rates exceeding 70%. Close-to-home transactions are almost never fraudulent regardless of amount.

*See: `plots/05_fraud_heatmap.png`, `plots/04_distance_vs_amount_scatter.png`*

### Finding 5: Merchant category, international status, and card age do NOT predict fraud

After controlling for distance, amount, and time of day:

- **Merchant category:** No category is significantly different from the baseline (all p > 0.09 in logistic regression). Raw fraud rates vary modestly (3.3% for Gas to 6.3% for Restaurant), but these differences vanish after multivariate adjustment.
- **International transactions:** OR = 0.83 (p = 0.54). International transactions are not more fraudulent — a potentially counter-intuitive finding.
- **Card age:** OR ≈ 1.0 (p = 0.67). Neither new nor old cards are more fraud-prone.

## 3. Predictive Modeling

Three models were evaluated using stratified 5-fold cross-validation:

| Model | AUC-ROC | Average Precision | Precision (0.5) | Recall (0.5) |
|-------|---------|-------------------|-----------------|--------------|
| Logistic Regression | 0.872 | 0.592 | 0.21 | 0.75 |
| Random Forest | 0.879 | 0.520 | 0.78 | 0.28 |
| Gradient Boosting | 0.850 | 0.520 | 0.65 | 0.39 |

**Key observations:**

- **All models achieve similar AUC-ROC (~0.85–0.88)**, suggesting the signal is primarily in a single feature (distance) and additional model complexity yields diminishing returns.
- The **precision-recall tradeoff** is the practical decision: Logistic Regression (with balanced class weights) favors recall (catches 75% of fraud but flags many false positives), while Random Forest favors precision (78% of flagged transactions are truly fraud, but misses 72% of fraud cases).
- The **calibration plot** shows the Random Forest is reasonably well-calibrated at low predicted probabilities but has limited resolution at higher probabilities.
- A **parsimonious logistic regression** using only distance, log(amount), and a night indicator achieves pseudo-R² = 0.42, confirming that these three features capture nearly all the predictive signal.

*See: `plots/07_model_comparison.png`, `plots/08_feature_importance.png`, `plots/09_distance_decile_and_calibration.png`*

## 4. Practical Implications

1. **Distance-based monitoring is the single most effective fraud detection strategy.** A distance threshold alone outperforms complex rules that don't include distance.

2. **Nighttime transactions warrant heightened scrutiny.** The 8x odds ratio for fraud during midnight–5 AM hours suggests that applying lower flagging thresholds during these hours would catch more fraud.

3. **A combined rule — distance > 30 km AND (amount > $50 OR nighttime) — achieves 35% precision and 55% recall**, flagging 236 of 3,000 transactions. This provides a practical starting point for manual review, catching over half of all fraud while keeping the review queue manageable.

4. **International status should NOT be used as a fraud signal.** Despite common intuition, international transactions are no more likely to be fraudulent in this dataset.

## 5. Limitations and Caveats

### Assumptions that could be wrong
- **Distance causality:** We observe that fraud occurs far from home, but we cannot determine causal direction. It is possible that the dataset was constructed with distance as a primary generating feature, rather than reflecting real-world fraud patterns where many other signals (velocity, device fingerprint, IP geolocation) would be available.
- **Temporal structure:** We have no date information — only hour of day. We cannot assess trends, seasonality, or temporal autocorrelation.

### What we didn't investigate
- **Interaction between is_international and distance.** International transactions likely correlate with distance, yet neither is a strong predictor alone. The near-zero correlation of is_international with fraud may indicate that distance already captures the geographic signal.
- **Threshold sensitivity at different operating points.** We evaluated models at a 0.5 threshold; a real fraud detection system would optimize for a specific cost ratio (cost of missed fraud vs. cost of false alarm).
- **Non-linear hour effects.** We modeled hour as a binary night/day split. A more granular model (splines or cyclic encoding) might capture additional signal in the late-evening hours (10 PM–midnight show ~8% fraud rate vs. ~5% baseline).

### Data limitations
- **Sample size:** With only 150 fraud cases, statistical power for detecting subtle effects (e.g., merchant category differences) is limited. Some cells in the distance × amount heatmap have fewer than 10 observations.
- **Synthetic characteristics:** The data appears relatively clean and well-structured, which may indicate synthetic generation. Real-world fraud data would likely be messier, with more features, temporal patterns, and adversarial behavior from fraudsters who adapt to detection rules.
- **Missing features:** Real fraud detection systems use dozens of features (transaction velocity, device info, IP address, spending patterns). The available features represent only a subset of what would be used in practice.

## 6. Summary of Plots

| File | Description |
|------|-------------|
| `plots/01_distance_by_fraud.png` | Distance from home distributions and box plot, fraud vs. legitimate |
| `plots/02_amount_by_fraud.png` | Transaction amount distributions and box plot by fraud status |
| `plots/03_hour_of_day.png` | Fraud rate by hour of day and transaction volume breakdown |
| `plots/04_distance_vs_amount_scatter.png` | Scatter of distance vs. amount, colored by fraud status |
| `plots/05_fraud_heatmap.png` | Fraud rate heatmap across distance and amount bins |
| `plots/06_night_vs_day_scatter.png` | Day vs. night fraud patterns in distance-amount space |
| `plots/07_model_comparison.png` | ROC and Precision-Recall curves for three ML models |
| `plots/08_feature_importance.png` | Gini and permutation feature importance (Random Forest) |
| `plots/09_distance_decile_and_calibration.png` | Fraud rate by distance decile and model calibration plot |
| `plots/10_summary_dashboard.png` | Six-panel summary dashboard of key findings |
