# Analysis Report

## What this dataset is about

This dataset contains 1,000 marketing campaigns with one row per `campaign_id`. The fields describe campaign context (`region`, `channel`, `month`), media scale (`ad_spend_usd`, `impressions`, `clicks`), and outcome (`revenue_usd`).

The data is unusually clean:

- Shape: 1,000 rows x 8 raw columns
- Missing values: none
- Identifier structure: `campaign_id` is unique in every row
- Category balance: `region` has 4 levels with 240 to 261 rows each; `channel` has 4 levels with 226 to 266 rows each; `month` spans 1 to 12 with 64 to 97 rows per month
- Value ranges are plausible for campaign data: ad spend ranges from $729 to $49,986, impressions from 7,126 to 709,259, clicks from 145 to 34,102, and revenue from $1,481 to $155,838

The raw rows are internally consistent with the column names. For example, higher spend generally comes with higher impressions and clicks, and the ratio-derived metrics below stay in believable ranges:

- CTR (`clicks / impressions`): 1.0% to 5.0%, median 2.94%
- CPC (`ad_spend / clicks`): $1.39 to $11.93, median $3.02
- CPM (`1000 * ad_spend / impressions`): $66.68 to $125.00, median $87.35
- ROAS (`revenue / spend`): 0.97 to 4.27, median 2.50

Nothing in the orientation step suggested hidden missing codes, malformed dates, or multi-level dependence structures. The main caveat is that the dataset looks highly controlled: several business metrics are strikingly stable across segments.

## Key findings

### 1. Campaign revenue is driven overwhelmingly by spend scale, not by channel, region, or month

**Hypothesis.** Revenue should rise with ad spend, but if channel mix, region, or seasonality matter in a substantive way, they should add explanatory power beyond spend.

**Test.** I fit an OLS model of `revenue_usd ~ ad_spend_usd` and then compared it with an expanded model adding `channel`, `region`, and `month`. The relationship is visualized in `plots/revenue_vs_spend.png` and the regression assumptions are checked in `plots/revenue_model_diagnostics.png`.

**Result.**

- Pearson correlation between spend and revenue: 0.972
- OLS slope: 2.495 additional revenue dollars per $1 of spend
- 95% CI for slope with HC3 robust standard errors: [2.454, 2.535]
- R² from `revenue_usd ~ ad_spend_usd`: 0.945
- Adding `channel`, `region`, and `month` barely changed fit: R² rose from 0.9454 to 0.9461
- Joint nested F-test for adding those categorical factors: p = 0.748
- In the expanded model, the only strong term was spend itself; joint ANOVA p-values were 0.245 for channel, 0.524 for region, and 0.835 for month

**Interpretation.** In this dataset, campaign scale dominates everything else. A simple linear spend model already explains about 95% of revenue variation, and the segment labels add almost no incremental information once spend is known.

**Diagnostic note.** The residual plot in `plots/revenue_model_diagnostics.png` shows clear heteroskedasticity, confirmed by the Breusch-Pagan test (p < 1e-36). That means the residual spread widens at higher spend levels. I therefore relied on HC3 robust confidence intervals for the slope. This affects uncertainty estimates, not the basic conclusion that spend is the dominant driver.

### 2. ROAS is essentially the same across channels

**Hypothesis.** If some channels are structurally more efficient, they should produce materially different ROAS distributions.

**Test.** I compared ROAS across `Display`, `Email`, `Search`, and `Social` using ANOVA and visualized the full distributions in `plots/roas_by_channel.png`.

**Result.**

- Mean ROAS by channel:
  - Display: 2.493
  - Email: 2.496
  - Search: 2.513
  - Social: 2.527
- Overall mean ROAS: 2.507 with standard deviation 0.352
- ANOVA for `roas ~ channel`: p = 0.680
- Effect size was negligible: eta-squared = 0.0015, meaning channel explains about 0.15% of ROAS variance

The plot shows why the test is non-significant: the medians and interquartile ranges overlap heavily, and the small differences in means are tiny relative to within-channel spread.

**Interpretation.** The data does not support a practical claim that one channel is more profitable than another. Any ranking such as “Social is best” would be overstated here; the observed differences are too small relative to campaign-to-campaign variability.

### 3. Monthly revenue swings exist, but they are explained by spend allocation rather than better monthly efficiency

**Hypothesis.** The month effect might look real in raw revenue, but if ROAS is stable, then higher-revenue months are probably just higher-spend months.

**Test.** I first tested whether mean revenue differs by month, then checked whether the month effect survives after controlling for spend. I also compared monthly revenue, spend, and ROAS in `plots/monthly_revenue_and_roas.png`.

**Result.**

- ANOVA for `revenue_usd ~ month`: p = 0.0023
- Lowest mean revenue month: September, $53,997 on mean spend of $21,516
- Highest mean revenue month: November, $72,524 on mean spend of $28,862
- Monthly mean ROAS stays tightly clustered between 2.454 and 2.544
- After controlling for spend in `revenue_usd ~ ad_spend_usd + month`, no month coefficient was significant; month p-values ranged from 0.226 to 0.960, and the joint month test gave p = 0.835

The indexed lines in `plots/monthly_revenue_and_roas.png` move almost on top of each other for spend and revenue, while the ROAS panel is nearly flat.

**Interpretation.** There is apparent seasonality in revenue totals, but it is budget seasonality, not performance seasonality. Months with more revenue are mostly the months where more money was spent.

### 4. Higher-engagement campaigns also buy clicks more cheaply

**Hypothesis.** Campaigns with higher CTR may be rewarded with lower CPC, which would indicate a strong efficiency mechanism rather than simple volume scaling.

**Test.** I examined the relationship between CTR and CPC across all campaigns and channels, visualized in `plots/ctr_vs_cpc.png`.

**Result.**

- Spearman correlation between CTR and CPC: -0.910
- The inverse pattern is visible across the entire CTR range and is not confined to any single channel

**Interpretation.** Better engagement is associated with cheaper traffic acquisition. Practically, this suggests creative relevance or targeting quality matters for cost efficiency, even if it does not create large differences in final ROAS across channels in this specific dataset.

## What the findings mean

The strongest conclusion is simple: this dataset behaves like a tightly managed marketing system where campaign outcomes are mainly a function of how much money is deployed. Channel, region, and month labels do not meaningfully separate profitability once spend is known.

That has two practical implications:

- If the goal is forecasting revenue from campaign plans, a spend-based model is likely sufficient.
- If the goal is optimizing tactics, the interesting lever is not “which channel wins,” but “what improves engagement efficiency,” because CTR and CPC move together strongly while ROAS remains broadly constant.

## Limitations and self-critique

Several limitations matter here.

First, this is observational campaign data, so causal claims are limited. The fact that spend predicts revenue does not prove spend alone causes revenue; higher budgets may be assigned to better opportunities, stronger creatives, or higher-intent audiences.

Second, the dataset appears unusually regular. ROAS is centered near 2.5 in every segment, and the segment effects are very small. That pattern may reflect a synthetic dataset or a heavily normalized reporting process. If so, the lack of channel differences may say more about the data-generating process than about real marketing performance.

Third, the revenue model is heteroskedastic. Higher-spend campaigns have wider residual spread, so prediction intervals for large campaigns should be wider than for small campaigns even though the average linear relationship is strong.

Fourth, I did not investigate interactions such as `channel x month` or `channel x region` in depth, because the main effects were already close to null and the dominant spend effect made additional structure hard to justify. If the business question specifically concerns niche seasonal effects within a channel, that would need separate targeted testing.

Fifth, important confounders are missing: conversion rate, audience quality, product mix, creative, bidding strategy, and attribution rules. Without them, the CTR-to-CPC relationship is interpretable as an efficiency association, not a guaranteed optimization rule.

Overall, the evidence supports modest, operational conclusions rather than a grand strategic one: revenue scales predictably with spend, apparent monthly peaks are mostly budgeting effects, and channel-level ROAS differences are too small to treat as meaningful in this dataset.
