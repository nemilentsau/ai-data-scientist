# Analysis Report

## What this dataset is about

This dataset contains 1,000 marketing campaign records with 8 columns: `campaign_id`, `region`, `channel`, `ad_spend_usd`, `impressions`, `clicks`, `revenue_usd`, and `month`. There are no missing values. The categorical fields are low-cardinality and balanced enough for comparison: 4 regions, 4 channels, and all 12 months are represented. Each `campaign_id` is unique, so this is a campaign-level cross-section rather than a repeated-measures panel.

The raw rows are internally consistent with a standard acquisition funnel: higher spend usually comes with more impressions, more clicks, and more revenue. Derived metrics also look plausible on their face:

- CTR (`clicks / impressions`) averages 2.98% and ranges from 1.00% to 4.99%.
- ROAS (`revenue / spend`) averages 2.51 with a standard deviation of 0.35.
- Average campaign spend is $24,767.70 and average revenue is $61,978.97.

The main surprise during orientation was how regular the dataset is. There are no nulls, no obvious data-quality problems, no severe class imbalance, and several relationships are almost perfectly linear. That makes the dataset easy to analyze, but it also raises the possibility that it is simulated or heavily normalized.

## Key findings

### 1. Revenue is driven overwhelmingly by spend, with little evidence of diminishing returns

**Hypothesis:** campaigns with higher spend produce higher revenue in an approximately linear way.

**Test:** OLS regression of `revenue_usd ~ ad_spend_usd`, followed by a quadratic check `revenue_usd ~ ad_spend_usd + ad_spend_usd^2`.

**Result:** confirmed.

- Spend and revenue have a correlation of 0.972.
- The linear model explains 94.5% of revenue variance (`R^2 = 0.945`).
- The fitted slope is **2.49** additional revenue dollars per additional dollar of spend, with 95% CI **[2.46, 2.53]**.
- Adding a quadratic term does not improve the relationship materially; the quadratic coefficient is not significant (`p = 0.491`).

Interpretation: within the observed spend range, revenue behaves close to a constant-multiple return process. The residual plot in `plots/revenue_vs_spend.png` does not show a visible channel-specific or spend-specific pattern, which supports the conclusion that the dominant structure is linear scaling rather than nonlinear lift.

Practical implication: if this dataset reflects a real planning environment, budget size matters much more than channel identity for explaining gross revenue. If optimization is the goal, the marginal opportunity is unlikely to come from finding a dramatically better channel in this sample.

### 2. Differences across channels and months are mostly volume differences, not efficiency differences

**Hypothesis:** apparent peaks in revenue by channel or month reflect better efficiency, not just larger campaign scale.

**Test:** compare ROAS distributions across channel and month using boxplots and nonparametric Kruskal-Wallis tests; also model `roas ~ channel + region + month`.

**Result:** mostly refuted.

- Mean ROAS by channel is tightly clustered:
  - Display: 2.49
  - Email: 2.50
  - Search: 2.51
  - Social: 2.53
- Mean ROAS by month stays in a narrow band from **2.45** (October) to **2.54** (June and August).
- Kruskal-Wallis tests show no statistically significant ROAS differences:
  - By channel: `p = 0.442`
  - By month: `p = 0.695`
- In the OLS ANOVA for ROAS, channel (`p = 0.748`) and month (`p = 0.763`) are not significant; region is borderline at `p = 0.051`.

The monthly pattern is best read as a **scale effect**. For example, average revenue peaks in **November ($72.5k)** and **May ($71.5k)**, but those peaks coincide with high average spend, while efficiency remains stable. This is visible in `plots/monthly_volume_vs_efficiency.png` and `plots/roas_stability.png`.

Interpretation: the dataset does not support a claim that one channel or season is structurally more profitable than another. The main thing changing over time is campaign size, not return efficiency.

Practical implication: a planning team using only this dataset should be cautious about reallocating budget based on apparent monthly or channel winners. The evidence suggests that larger campaigns generate larger revenue, but not systematically better ROAS.

### 3. Most remaining variability sits in the click-generation step, not the revenue-generation step

**Hypothesis:** after accounting for volume, click generation is noisier than revenue generation.

**Test:** compare the strength of relationships in the funnel:

- `impressions` vs `clicks`
- `ad_spend_usd` vs `revenue_usd`
- linear model of `clicks ~ impressions + ad_spend_usd`

**Result:** confirmed.

- Impressions and clicks correlate at **0.804**, which is strong but notably weaker than spend and revenue.
- The click model explains **64.8%** of click variance (`R^2 = 0.648`), versus **94.5%** for revenue from spend.
- CTR spans a wide range from **1.0% to 5.0%**, with mean **2.98%** and standard deviation **1.15 percentage points**.
- CTR does not differ significantly by channel (`p = 0.223`) or month (`p = 0.528`).

This means the main uncertainty in the funnel is the step from exposure to click-through, not the step from spend to monetized revenue. `plots/click_funnel_variability.png` shows that campaigns with similar impression counts can land at noticeably different click totals because CTR varies substantially within every group.

Interpretation: the dataset behaves as if monetization after spend is highly standardized, while engagement quality is more variable. If future data collection adds creative, audience, or offer details, those variables would likely be more informative for explaining clicks than the current channel/month labels.

## What the findings mean

This looks like a marketing system in which top-line revenue is mostly a function of budget allocation, while operational differences across channel and timing are muted. If the goal is forecasting, a simple spend-based model is already very strong. If the goal is optimization, the current features are not rich enough to reveal strong levers beyond spend level.

A second implication is methodological: because ROAS is so stable, comparing raw revenue totals across segments is potentially misleading. Segments with more revenue in this dataset mostly appear to be the segments that ran bigger campaigns, not the segments that converted budget more efficiently.

## Limitations and self-critique

- This is observational campaign-level data, so none of the findings justify causal claims. Higher spend is associated with higher revenue, but this does not prove that increasing spend would preserve the same slope in a live system.
- The dataset lacks key funnel variables such as conversions, customer quality, audience targeting, creative, or product mix. Those omitted variables could explain CTR variation or any weak regional differences.
- Each campaign appears only once. That prevents within-campaign trend analysis and makes it impossible to separate persistent campaign quality from one-off noise.
- Region showed a borderline ROAS effect in the ANOVA (`p = 0.051`). I did not pursue that further with interaction-heavy models because the effect was small and unstable relative to the overall signal, but it could merit follow-up in a richer dataset.
- The data are unusually clean and regular. The near-constant ROAS, lack of missingness, and strong linearity suggest the possibility of synthetic or pre-aggregated data. If so, real-world variance is likely understated.

## Files produced

- `plots/revenue_vs_spend.png`
- `plots/roas_stability.png`
- `plots/monthly_volume_vs_efficiency.png`
- `plots/click_funnel_variability.png`
