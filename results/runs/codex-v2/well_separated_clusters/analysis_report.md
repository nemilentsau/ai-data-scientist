# Analysis Report

## What This Dataset Appears To Be

This is a customer-level dataset with 600 rows and 7 columns:

- `customer_id`: unique identifier, 600 unique values
- `avg_order_value`: continuous, range 16.16 to 128.76
- `purchase_frequency_monthly`: continuous, range 0.10 to 18.41
- `days_since_last_purchase`: continuous, range 0.00 to 54.26
- `total_lifetime_spend`: continuous, range 1632.24 to 4299.18
- `support_contacts`: integer count, range 0 to 6
- `account_age_months`: integer, range 1 to 59

There are no null values and no duplicate rows. The raw rows are internally consistent with customer-commerce metrics. Two things stood out during orientation:

1. `avg_order_value`, `purchase_frequency_monthly`, and `days_since_last_purchase` are extremely structured rather than loosely related.
2. The dataset splits very cleanly into equal-sized groups, which is unusual for organic customer data and suggests possible synthetic generation or pre-engineered segments.

## Key Findings

### 1. The customer base is not one continuous population; it is three very distinct behavioral segments.

**Hypothesis.** Customers fall into a small number of behavioral archetypes defined by order value, purchase frequency, and recency.

**Test.** I examined pairwise correlations and then fit K-means clustering on standardized versions of `avg_order_value`, `purchase_frequency_monthly`, and `days_since_last_purchase`.

**Result.**

- `avg_order_value` vs `purchase_frequency_monthly`: Pearson `r = -0.946`
- `avg_order_value` vs `days_since_last_purchase`: Pearson `r = 0.961`
- `purchase_frequency_monthly` vs `days_since_last_purchase`: Pearson `r = -0.908`
- Best clustering signal among `k = 2..6` occurred at `k = 3` with silhouette score `0.453`

The three inferred segments are shown in `plots/customer_behavior_segments.png`:

- Low AOV / High freq / Recent: mean AOV `25.11`, frequency `15.09`, recency `5.46`
- Mid-range balance: mean AOV `74.93`, frequency `7.90`, recency `19.64`
- High AOV / Low freq / Lapsed: mean AOV `119.78`, frequency `3.05`, recency `44.81`

Each segment contains exactly 200 customers. That symmetry is analytically useful, but it is also a reason to be cautious about treating the sample as naturally occurring.

### 2. The middle segment is dramatically more valuable than either extreme.

**Hypothesis.** The most valuable customers are not the most frequent buyers or the highest-ticket buyers, but the customers with balanced behavior.

**Test.** I compared `total_lifetime_spend` across the three inferred segments using distribution plots and omnibus tests.

**Result.**

- Low AOV / High freq / Recent: mean lifetime spend `2248.15`
- Mid-range balance: mean lifetime spend `3601.25`
- High AOV / Low freq / Lapsed: mean lifetime spend `2196.12`

The lift for the mid-range segment is large:

- `+60.2%` vs the low-AOV/high-frequency segment
- `+64.0%` vs the high-AOV/low-frequency segment
- `+62.1%` vs the two non-mid segments combined

The separation is not subtle:

- One-way ANOVA across segments: `F = 3330.25`, `p < 1e-300`
- Kruskal-Wallis: `H = 402.62`, `p = 3.74e-88`
- Cohen's `d = 7.03` for mid-range segment vs all others combined

The spend distributions are shown in `plots/lifetime_spend_by_segment.png`. The mid-range group is clearly shifted upward, not just driven by a few outliers.

### 3. Lifetime spend is strongly nonlinear and mostly explained by segment structure; support contacts and account age add little.

**Hypothesis.** A linear model will underfit this dataset because lifetime spend peaks in the middle of the behavior ranges rather than increasing monotonically.

**Test.** I compared linear, quadratic, and segment-based predictive models using 10-fold cross-validation, and then checked regression diagnostics.

**Result.**

- Linear model CV `R^2 = 0.438` and mean CV RMSE `498.0`
- Quadratic model CV `R^2 = 0.858` and mean CV RMSE `247.3`
- Segment-only model CV `R^2 = 0.913` and mean CV RMSE `194.8`

This means a simple model that knows only which segment a customer belongs to predicts lifetime spend better than a smooth quadratic curve. That is strong evidence that the data are governed by discrete regimes, not a single continuous response surface.

The nonlinear shape is visible in `plots/nonlinear_spend_patterns.png`: spend peaks at mid-range values of order size, purchase cadence, and recency, then drops off at both extremes.

I also tested whether `support_contacts` and `account_age_months` contribute once those main behavior variables are accounted for:

- Nested-model test adding `support_contacts` and `account_age_months`: `F = 1.58`, `p = 0.207`
- `support_contacts` by itself vs spend: ANOVA `p = 0.692`
- `account_age_months` coefficient in full model: `p = 0.245`

So the dataset does **not** support a meaningful relationship between customer value and either support burden or account age.

For model diagnostics (`plots/quadratic_model_diagnostics.png`):

- Residual normality looks acceptable: Shapiro-Wilk on a 500-row sample `p = 0.812`, Jarque-Bera `p = 0.233`
- Heteroskedasticity is borderline: Breusch-Pagan `p ≈ 0.05`
- Residual-vs-fitted structure still shows some clustering, consistent with the segment interpretation outperforming a smooth regression

## What The Findings Mean

If this dataset reflects a real business process, the highest-value customers are the ones in a behavioral middle ground:

- not the cheapest customers buying very often
- not the premium-ticket customers buying rarely after long lapses
- but customers with moderate ticket size, moderate cadence, and moderate recency

Operationally, that suggests value is tied to **balance**, not extremity. If this were a retention or CRM problem, the most useful interventions would likely be those that move customers toward the mid-range behavioral regime rather than maximizing a single metric such as order value or order frequency in isolation.

At the same time, the segment-only model outperforming the continuous models suggests something important about the data-generating process: this looks more like a dataset built from a few customer templates or commercial tiers than one generated from noisy real-world customer behavior.

## Limitations And Self-Critique

### Alternative explanations

The clean three-group pattern may reflect:

- synthetic data generation
- customers assigned to latent pricing or loyalty tiers
- business rules that already bundle customers into fixed regimes

I cannot distinguish among those explanations from this file alone.

### Assumptions and risks

- This is cross-sectional data, so none of these relationships should be interpreted causally.
- The strong multicollinearity among AOV, frequency, and recency makes individual regression coefficients unstable and hard to interpret in isolation.
- The equal segment sizes are suspiciously tidy and reduce confidence that this distribution reflects a live customer base.
- There is no temporal transaction history, so I could not test whether these patterns hold over time or whether recency is simply a proxy for current segment membership.

### What I did not investigate

- I did not infer customer trajectories over time because no event-level data are present.
- I did not model churn or survival because there is no censoring structure or explicit outcome date.
- I did not test external drivers such as geography, channel, pricing tier, or campaign exposure because those fields are absent.

## Plot References

- `plots/customer_behavior_segments.png`
- `plots/lifetime_spend_by_segment.png`
- `plots/nonlinear_spend_patterns.png`
- `plots/quadratic_model_diagnostics.png`
