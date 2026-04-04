# E-Commerce Order Analysis Report

## 1. Dataset Overview

The dataset contains **1,200 e-commerce orders** with the following fields:

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | int | Sequential order identifier (10000–11199) |
| `customer_segment` | str | New (480), Returning (541), VIP (179) |
| `items_qty` | int | Items per order (1–19, uniform distribution) |
| `unit_price_usd` | float | Unit price ($5–$200, uniform) |
| `shipping_usd` | float | Shipping tier: $0.00, $4.99, $9.99, or $14.99 |
| `discount_pct` | int | Stated discount: 0%, 5%, 10%, 15%, or 20% |
| `order_total_usd` | float | Actual amount charged |
| `returned` | int | Whether the order was returned (0/1) |

No missing values. The dataset has no date/time fields, so temporal analysis is limited to order ID sequence. The overall return rate is **8.8%** (105 of 1,200 orders).

---

## 2. Key Findings

### Finding 1: Discounts Are Not Being Applied to Order Totals (Critical)

**This is the most important finding in the dataset.** The `discount_pct` field has **zero effect** on the actual order total charged to customers.

The order total follows this formula almost perfectly:

```
order_total = items_qty × unit_price_usd + shipping_usd    (R² = 0.99999)
```

The discount-adjusted formula — which should be correct — fits far worse:

```
order_total ≠ items_qty × unit_price_usd × (1 - discount_pct/100) + shipping_usd    (R² = 0.984)
```

The residuals from the no-discount formula are just rounding noise: mean = -$0.004, std = $1.97, max = $6.94. In contrast, the discounted formula produces systematic errors that grow proportionally with the discount level (see `plots/discount_bug_analysis.png`, top panels).

**Revenue impact:**

| Discount Level | Orders | Total Overcharge | Avg Overcharge/Order |
|:-:|:-:|:-:|:-:|
| 0% | 259 | -$66 (rounding) | -$0.26 |
| 5% | 232 | $11,940 | $51.47 |
| 10% | 215 | $19,740 | $91.81 |
| 15% | 216 | $33,493 | $155.06 |
| 20% | 218 | $44,630 | $204.72 |
| **Total** | **1,140** | **$109,737** | — |

Customers are being overcharged a combined **$109,737** — **10.4% of expected revenue** — due to unapplied discounts. This affects 881 of 1,140 clean orders (77%). The overcharge is distributed across all customer segments:

- New: $40,246 total overcharge
- Returning: $52,056 total overcharge
- VIP: $17,435 total overcharge

**Evidence:** `plots/discount_bug_analysis.png` (top-left: perfect y=x fit without discount; top-right: systematic deviation when discount is expected; bottom-left: overcharge scaling with discount level)

### Finding 2: Returns Are Unpredictable from Available Features

Despite testing every available feature, **no variable or combination of variables predicts whether an order will be returned**:

- **Customer segment:** χ² = 1.04, p = 0.60. New (8.8%), Returning (8.1%), VIP (10.6%) — no significant difference.
- **Discount level:** χ² = 1.74, p = 0.78. Rates range from 7.4% to 10.8% with no trend.
- **Unit price:** Mann-Whitney p = 0.37. No difference between returned and non-returned orders.
- **Items quantity:** Mann-Whitney p = 0.51. No difference.
- **Order total:** Mann-Whitney p = 0.76. No difference.

A logistic regression model with all features yields pseudo R² = 0.008 and overall model p = 0.60. Cross-validated AUC scores are 0.488 (logistic regression) and 0.519 (random forest) — **indistinguishable from random chance** (AUC = 0.5).

This strongly suggests that returns are driven by factors not captured in this dataset — product quality issues, customer expectations, fit/sizing problems, or other post-purchase experiences.

**Evidence:** `plots/return_rate_by_segment.png`, `plots/return_rate_by_order_features.png`, `plots/summary_dashboard.png` (return prediction panel)

### Finding 3: Free Shipping Shows a Marginal Association with Lower Returns

The one suggestive (but not statistically significant) pattern:

| Shipping | Return Rate | n |
|:-:|:-:|:-:|
| Free ($0.00) | 6.5% | 324 |
| Paid ($4.99–$14.99) | 9.6% | 876 |

Two-proportion z-test: z = -1.69, **p = 0.091**. Effect size: 3.1 percentage points. The pattern is consistent across all three customer segments (New: 5.3% vs 10.1%, Returning: 7.4% vs 8.4%, VIP: 7.1% vs 12.2%).

At p = 0.091 this does not meet conventional significance thresholds, but the direction and consistency suggest it warrants monitoring with more data. The effect size (3.1pp) would be practically meaningful if confirmed.

**Evidence:** `plots/return_rate_by_order_features.png` (top-right panel)

### Finding 4: 60 Anomalous Orders (5%) with Wildly Incorrect Totals

Sixty orders have totals that don't follow **any** pricing formula — 28 have negative totals (down to -$19,241) and 32 have extreme positive totals (up to $21,439) with no relationship to the order's items, prices, or discounts.

Key characteristics of anomalous orders:
- **Randomly distributed** across customer segments, discount levels, shipping tiers, and the order ID sequence
- **No distinguishing features** — item quantity, unit price, discount, and shipping are statistically identical to normal orders (all Mann-Whitney p > 0.18)
- **Low return rate** among anomalies: 8.3% (5/60), comparable to the overall rate

The random distribution and lack of feature correlations suggest **system-level pricing errors** (e.g., sign errors, decimal shifts, database corruption) rather than a systematic process like fraud.

**Evidence:** `plots/anomaly_investigation.png`, `plots/actual_vs_expected_total.png`

---

## 3. Segment Profiles

While segments don't differ in return behavior, they show some differences in ordering patterns (clean orders only):

| Metric | New (n=452) | Returning (n=514) | VIP (n=174) |
|--------|:-:|:-:|:-:|
| Avg items/order | 9.2 | 10.2 | 10.0 |
| Avg unit price | $103.30 | $101.60 | $108.15 |
| Median order total | $720 | $780 | $847 |
| Total revenue | $430,513 | $540,256 | $193,606 |
| Return rate | 9.1% | 8.2% | 9.8% |
| Avg discount | 9.3% | 9.9% | 9.5% |
| Free shipping rate | 27.5% | 25.1% | 31.3% |

Returning customers order significantly more items per order (ANOVA F=4.32, p=0.014), but segments do not differ in unit price (p=0.42), discount levels (p=0.44), or return rates (p=0.60).

VIP customers receive free shipping more often (31.3% vs 25-27%) and have slightly higher median order totals ($847 vs $720-780), but these differences are not statistically significant.

---

## 4. Limitations and Caveats

### Assumptions that could be wrong
- **Discount interpretation:** The `discount_pct` field is assumed to represent a discount that should have been applied. It's possible this field represents something else (e.g., a loyalty tier label, a post-hoc classification, or a future credit). However, the column name strongly implies it should reduce the price, and the fact that 0% discount orders exactly match `qty × price + shipping` supports the "unapplied discount" interpretation.
- **Anomaly definition:** Orders were classified as anomalous if `order_total < 0` or the ratio of actual to expected total was outside [0.5, 3.0]. This threshold is somewhat arbitrary; a different cutoff would reclassify a small number of borderline cases.

### What was not investigated
- **Temporal patterns:** Without timestamps, we cannot assess seasonality, trends, or whether the discount bug started at a specific point.
- **Product-level data:** Returns may be driven by specific products, categories, or product quality — none of which are available.
- **Customer-level repeat behavior:** Each row is an order, not a customer. We cannot analyze individual customer return patterns.
- **Post-return outcomes:** We don't know if returns were refunded, exchanged, or resulted in customer churn.

### Statistical power
- The return rate of 8.8% (105 events) limits our power to detect small effects. A sample of 1,200 orders can reliably detect ~5 percentage point differences in return rates between groups, but smaller effects would require more data.
- The free shipping finding (p=0.091) may be a true effect that this sample is underpowered to confirm.

---

## 5. Recommendations

1. **Investigate the discount pricing bug immediately.** $109,737 in overcharges across 881 orders represents a significant compliance and customer trust risk. Determine whether discounts were displayed to customers but not applied at checkout, or whether `discount_pct` is a non-customer-facing field.

2. **Investigate the 60 anomalous orders.** These include 28 orders with negative totals totaling -$286,322 and 32 with extreme overcharges. Root-cause analysis should determine whether these are system bugs, manual adjustments, or test orders.

3. **Collect additional data to understand returns.** Since no available feature predicts returns, the drivers are likely product quality, customer expectations, or fulfillment issues. Adding product category, customer satisfaction scores, or reason-for-return codes would enable actionable analysis.

4. **Consider A/B testing free shipping.** The suggestive 3.1pp reduction in return rate with free shipping (p=0.091) could translate to meaningful savings if confirmed. A controlled experiment would resolve the ambiguity.

---

## 6. Plots Reference

| File | Description |
|------|-------------|
| `plots/actual_vs_expected_total.png` | Actual vs expected order totals — all orders and clean orders |
| `plots/return_rate_by_segment.png` | Return rates by customer segment (overall and normal vs anomalous) |
| `plots/return_rate_by_order_features.png` | Return rates by discount, shipping, unit price, and quantity |
| `plots/discount_bug_analysis.png` | Evidence that discounts are not applied + overcharge analysis |
| `plots/anomaly_investigation.png` | Characterization of 60 anomalous orders |
| `plots/summary_dashboard.png` | Comprehensive 6-panel summary of all key findings |
