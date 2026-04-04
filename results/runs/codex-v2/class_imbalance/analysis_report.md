# Fraud Transaction Analysis

## What this dataset is about

This dataset contains **3,000 payment transactions** with one binary outcome, `is_fraud`, and seven predictors describing transaction amount, time of day, merchant category, card tenure, travel distance from home, and whether the transaction was international. The data are clean and fully populated: there are **no missing values**, `hour_of_day` spans **0-23**, `merchant_category` has **7 levels**, and the target is imbalanced with **150 fraud cases (5.0%)**.

The fields behave consistently with their names. `transaction_id` is a unique identifier, `amount_usd` and `distance_from_home_km` are strongly right-skewed, and `is_international` / `is_fraud` are coded as 0/1 flags. One early surprise was that `is_international` is nearly perfectly uninformative here: both domestic and international transactions have the same observed fraud rate of roughly **5.0%**.

## Key findings

### 1. Fraud is concentrated in overnight transactions

**Hypothesis.** Transactions made overnight are more likely to be fraudulent than daytime transactions.

**Test.** I first plotted fraud rate by hour ([`fraud_rate_by_hour.png`](./plots/fraud_rate_by_hour.png)), then tested whether fraudulent and non-fraudulent transactions differ in transaction hour using a Mann-Whitney U test. To rule out confounding by amount and distance, I fit a logistic regression with `night` (hours 23:00-04:59), log amount, log distance, international status, and card age.

**Result.** The hourly plot shows a sharp overnight spike, with fraud rates of **30.6% at 00:00**, **45.0% at 01:00**, and **23.1% at 23:00**, versus mostly **1.5%-7.1%** during the rest of the day. Aggregating the night window, the fraud rate is **27.9%** at night versus **3.6%** otherwise. The hour distribution difference is statistically significant (Mann-Whitney U p = 0.009534). In the multivariate logistic model, the night indicator remains large and significant with an **odds ratio of 10.88** (95% CI 6.61-17.89, p = 5.5e-21), so the overnight effect is not just a side effect of larger or more distant transactions.

**Interpretation.** Time of day is a major behavioral marker in this dataset. Overnight activity appears to reflect a qualitatively different transaction regime, and it should be a first-class feature in any alerting or review strategy.

### 2. Distance from home is the strongest continuous risk signal

**Hypothesis.** Fraud probability rises as transactions occur farther from the cardholder's home location.

**Test.** I compared distance distributions between fraud and non-fraud groups using a Mann-Whitney U test and visualized fraud rate by distance decile ([`fraud_rate_by_distance_decile.png`](./plots/fraud_rate_by_distance_decile.png)). I then checked whether the effect survives after adjusting for amount, time, and other variables in logistic regression.

**Result.** Fraudulent transactions occur much farther from home on average: **51.4 km** versus **10.1 km** for non-fraud, with medians **34.5 km** versus **6.9 km**. The distribution shift is extremely strong (Mann-Whitney U p = 4.11e-40, Cohen's d = 2.68). The decile plot shows a nonlinear pattern: the first nine distance deciles stay below **6.7%** fraud, but the farthest decile jumps to **29.2%** compared with **2.3%** for the other 90% of transactions. In the multivariate model, each one-unit increase in `log(1 + distance)` multiplies fraud odds by **5.46** (95% CI 4.24-7.04, p = 3.4e-39), making distance the strongest continuous predictor.

**Interpretation.** Distance looks like a threshold-driven risk factor rather than a smooth linear trend. Most transactions close to home are low risk, but very distant transactions represent a materially different population and should receive sharply higher scrutiny.

### 3. Larger transactions are riskier, but merchant category and international status add little

**Hypothesis.** High-value transactions are more fraud-prone, while intuitive flags such as merchant category and international status may not add much incremental information.

**Test.** I compared transaction amounts across fraud labels with a Mann-Whitney U test, plotted fraud rate by amount decile ([`fraud_rate_by_amount_decile.png`](./plots/fraud_rate_by_amount_decile.png)), and tested merchant category and international status using chi-squared tests. I also used the multivariate logistic model to quantify the amount effect after controlling for distance and time.

**Result.** Fraudulent transactions are larger: mean **$162.59** versus **$70.27**, and median **$86.64** versus **$34.12** (Mann-Whitney U p = 3.948e-21, Cohen's d = 0.61). The top amount decile has a fraud rate of **12.7%**, compared with **4.1%** in the other nine deciles. After adjustment, `log(1 + amount)` still has a significant odds ratio of **2.07** (95% CI 1.73-2.48, p = 3.1e-15).

The intuitive alternatives were weaker than expected. `is_international` has identical observed fraud rates for domestic and international transactions (**5.0%** each; chi-squared p = 1.000), and merchant category differences are also not statistically significant (chi-squared p = 0.279). Card age is similarly negligible in the logistic model (p = 0.736). The odds-ratio summary in [`logistic_odds_ratios.png`](./plots/logistic_odds_ratios.png) makes this contrast clear.

**Interpretation.** In this dataset, risk is driven much more by transaction behavior than by static cardholder or merchant descriptors. High amount matters, but it is secondary to distance and especially to overnight timing.

### 4. The highest-risk segment combines night timing and long distance

[`fraud_rate_night_distance_heatmap.png`](./plots/fraud_rate_night_distance_heatmap.png) shows that risk compounds when the strongest signals coincide. Transactions that are both in the night window and in the farthest distance decile have a fraud rate of **69.4%**. The low-risk baseline, daytime transactions outside the top distance decile, is only **1.5%**. That is roughly a **45.6x** difference in observed fraud rate.

This segment analysis matters operationally because it turns broad findings into a screening rule: distance alone is powerful, but distance plus overnight timing isolates a very high-risk subset that may justify manual review or stricter authorization controls.

## Predictive signal

I trained a regularized logistic regression with 5-fold stratified cross-validation using all available fields. The out-of-fold ROC AUC is **0.876**, which indicates strong separability for such a small feature set. That model result supports the descriptive analysis: the fraud signal here is real and concentrated in a few interpretable variables rather than hidden in weak diffuse patterns.

## Limitations and self-critique

- This dataset appears highly stylized or synthetic. The very clean schemas, exact parity in domestic vs. international fraud rate, and unusually strong overnight effect suggest it may not reflect real production fraud data.
- The analysis is associative, not causal. For example, night transactions may proxy for unmeasured behaviors or geographies rather than cause fraud directly.
- Distance is treated as a single scalar with no geography, merchant location, or travel context. A real cardholder legitimately traveling could generate the same pattern.
- Merchant category was tested only at a coarse 7-level grouping. Finer-grained merchant, channel, or user-level structure could matter but is not available.
- The night effect was summarized with a binary window after reviewing the hourly plot. That is evidence-based, but still a modeling choice; a cyclic time model could be more nuanced.
- I checked one alternative explanation directly: night transactions are indeed somewhat farther from home on average, but the night effect remained large after controlling for distance and amount. Even so, unobserved confounders may remain.

## Bottom line

This dataset is about **fraud risk in card transactions**, and the dominant story is behavioral concentration: **fraud is much more likely for overnight, far-from-home, and high-value transactions**, while merchant category, card age, and international status contribute little. If this were an operational scoring problem, I would prioritize **time-of-day and distance interactions** first, then use amount as a secondary signal.
