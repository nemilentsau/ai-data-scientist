# Customer Behavior Segmentation Analysis

## Dataset Overview

The dataset contains 600 customer records with 6 behavioral and demographic features:

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| `avg_order_value` | float | $16.16 – $128.76 | Average spend per order |
| `purchase_frequency_monthly` | float | 0.10 – 18.41 | Orders per month |
| `days_since_last_purchase` | float | 0.00 – 54.26 | Recency of last purchase |
| `total_lifetime_spend` | float | $1,632 – $4,299 | Cumulative revenue from customer |
| `support_contacts` | int | 0 – 6 | Number of support interactions |
| `account_age_months` | int | 1 – 59 | Tenure in months |

No missing values. All 600 customer IDs are unique.

---

## Key Findings

### 1. Three Distinct Customer Segments Exist Along a Single Behavioral Dimension

K-means clustering (k=3, silhouette score = 0.78) identifies three well-separated customer segments of equal size (n=200 each), defined by purchasing behavior:

| Segment | Avg Order Value | Purchase Freq (monthly) | Days Since Last Purchase | Lifetime Spend |
|---------|:-:|:-:|:-:|:-:|
| **Frequent Small-Basket** | $25.11 | 15.09 | 5.46 | $2,248 |
| **Balanced Moderate** | $74.93 | 7.90 | 19.64 | **$3,601** |
| **Infrequent Big-Ticket** | $119.78 | 3.05 | 44.81 | $2,196 |

The three purchasing variables (`avg_order_value`, `purchase_frequency_monthly`, `days_since_last_purchase`) are extremely highly correlated with each other (|r| = 0.91–0.96), forming a single behavioral axis from "frequent, small, recent" to "infrequent, large, dormant." See: `plots/04_cluster_visualization.png`, `plots/09_segment_profiles.png`.

Cluster selection was validated by both silhouette score (k=3 scores 0.78, far above k=2 at 0.65 and k=4 at 0.63) and the elbow method (inertia drops from 509 at k=2 to 78 at k=3). See: `plots/03_cluster_selection.png`.

### 2. Lifetime Spend Follows an Inverted-U Relationship with Order Value

**This is the central finding.** Total lifetime spend has a strong quadratic (inverted-U) relationship with average order value, peaking at approximately **$72 AOV**. A single quadratic regression in AOV explains **85% of the variance in lifetime spend** (R² = 0.85, 5-fold cross-validated).

The model: `spend = -0.570 * AOV² + 82.089 * AOV + 589.3`

This means:
- Customers who buy frequently but cheaply (~$25/order) generate **$2,248** in lifetime spend
- Customers who buy at moderate prices (~$75/order) generate **$3,601** — 60% more
- Customers who buy expensive but rarely (~$120/order) generate **$2,196** — the lowest

The mechanism is the **product effect**: implied monthly spend = AOV × frequency. The Balanced Moderate segment achieves $592/month, versus ~$370–380/month for the extremes, because neither factor is driven to a minimum.

See: `plots/08_key_finding_inverted_u.png` (key visualization), `plots/05_lifetime_spend_by_segment.png`.

### 3. Support Contacts and Account Age Are Independent of Purchasing Behavior

`support_contacts` and `account_age_months` show near-zero correlations with all purchasing variables (|r| < 0.03) and with each other (r = -0.03). Their distributions are effectively identical across all three segments.

Neither variable predicts lifetime spend, either globally or within any segment (all p > 0.10). After accounting for the quadratic AOV effect, residuals show no relationship with support contacts (Kruskal-Wallis p = 0.89) or account age (r = -0.04, p = 0.28).

See: `plots/07_residual_analysis.png`, `plots/10_correlation_heatmap.png`.

### 4. Segment Differences Are Statistically Massive

- **ANOVA**: F = 3,330, p ≈ 0 (lifetime spend differs significantly across segments)
- **Effect sizes**: Cohen's d = 6.9 between Frequent Small-Basket and Balanced Moderate; d = 7.1 between Balanced Moderate and Infrequent Big-Ticket. These are extremely large effects.
- **Pairwise t-tests** (Bonferroni-corrected): all pairs significant at p < 0.02. The Frequent and Infrequent segments differ modestly (d = 0.27, p = 0.02), while both differ enormously from the Balanced Moderate segment.

### 5. Within-Segment Variation Is Pure Noise

Within each segment, no feature predicts lifetime spend. All within-segment correlations between any feature and lifetime spend are non-significant (p > 0.10 for all 15 tests). The quadratic model's residuals (std = $264) are normally distributed (Shapiro-Wilk p = 0.59) and show no systematic patterns.

---

## Interpretation and Practical Implications

### The "Goldilocks Effect" in Customer Value

The data reveals a clear Goldilocks principle: **customers who spend moderately per order but at a reasonable frequency are the most valuable overall.** Neither extreme purchasing behavior — frequent tiny orders nor rare large ones — maximizes lifetime value.

This has direct implications for customer strategy:

1. **Retention priority**: The Balanced Moderate segment (33% of customers) contributes disproportionately to revenue. These customers should receive the highest retention investment.

2. **Migration opportunity**: If Frequent Small-Basket customers could be nudged toward slightly larger basket sizes (even from $25 to $50), or if Infrequent Big-Ticket customers could be encouraged to purchase slightly more often, the inverted-U curve predicts substantial lifetime value gains.

3. **Support contacts are not a lever**: Despite intuition, support interaction frequency has no relationship with purchasing behavior or lifetime value. Support optimization should focus on cost efficiency, not on using support as a value driver.

4. **Account age doesn't accumulate value differently**: Newer and older customers within each segment spend similarly. Tenure-based loyalty programs may not be effective without considering purchasing pattern.

---

## Limitations and Caveats

### Data Limitations

- **Equal segment sizes (200 each)** and very clean separation suggest this may be synthetic or heavily curated data. Real customer data typically has messier boundaries and unequal segment sizes.
- **No temporal dimension**: We see a snapshot (current AOV, frequency, recency) but cannot observe how customers transition between segments over time. The lifetime spend metric is cumulative but we don't know over what period.
- **No external factors**: Pricing, promotions, product categories, and channel information are absent. The inverted-U could be confounded by product mix (moderate-AOV customers may buy a more profitable product category).

### Analytical Caveats

- **Correlation, not causation**: The inverted-U between AOV and lifetime spend does not mean *changing* a customer's AOV will change their lifetime spend. The segments may reflect fundamentally different customer types rather than movable behaviors.
- **The quadratic model is descriptive**: R² = 0.85 describes the data well, but the remaining 15% is unexplained random variation with no identifiable structure. There may be latent factors not captured in this dataset.
- **Support contacts may matter in ways not captured here**: The count of contacts (0–6 range) may be too coarse. Sentiment, resolution quality, or contact type might be more informative than count alone.

### What Was Not Investigated

- **Temporal dynamics**: Do customers migrate between segments? Is "Balanced Moderate" a stable state or a transitional one?
- **Customer acquisition channels**: Are the segments recruited differently?
- **Churn risk**: `days_since_last_purchase` varies hugely across segments (5 vs 45 days), but without a churn label we cannot assess whether the Infrequent Big-Ticket segment is at risk or simply has a different natural cadence.

---

## Summary of Plots

| File | Description |
|------|-------------|
| `plots/01_distributions.png` | Histograms of all 6 features showing trimodal distributions |
| `plots/02_correlated_vars_scatter.png` | Pairwise scatter plots of the three highly correlated behavioral variables |
| `plots/03_cluster_selection.png` | Silhouette score and elbow plots confirming k=3 |
| `plots/04_cluster_visualization.png` | Scatter plots with segment coloring showing clean cluster separation |
| `plots/05_lifetime_spend_by_segment.png` | Boxplots of lifetime spend by segment with means annotated |
| `plots/06_nonlinear_relationships.png` | Three panels showing AOV-frequency relationship, monthly spend rate, and inverted-U |
| `plots/07_residual_analysis.png` | Residual diagnostics for the quadratic model |
| `plots/08_key_finding_inverted_u.png` | **Key figure**: Inverted-U relationship with quadratic fit and segment coloring |
| `plots/09_segment_profiles.png` | Bar charts comparing all metrics across segments |
| `plots/10_correlation_heatmap.png` | Full correlation matrix heatmap |
