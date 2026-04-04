# Marketing Campaign Analysis

## What This Dataset Appears To Be

This dataset contains **1,000 campaign-level observations** with one row per campaign and 8 raw fields: campaign ID, region, channel, ad spend, impressions, clicks, revenue, and month. It is structurally clean: there are **no missing values**, IDs are unique, `month` is encoded as integers **1-12**, and the categorical fields are balanced enough for comparison (`channel`: {'Display': 226, 'Email': 266, 'Search': 258, 'Social': 250}, `region`: {'East': 240, 'North': 261, 'South': 258, 'West': 241}).

The raw rows make sense for a paid-media table: spend scales with impressions, clicks, and revenue, while channel and region look like campaign attributes rather than repeated measurements. The main caution is interpretive rather than technical: this looks like an observational, already-aggregated dataset, so it can support **associational** claims but not causal attribution.

## Key Findings

### 1. Revenue is overwhelmingly explained by spend, not by channel, region, or month.

Hypothesis: if campaign performance differs materially by channel or season, then adding `channel`, `region`, and `month` to a spend-based revenue model should meaningfully improve fit.

Test: I fit an OLS model `revenue_usd ~ ad_spend_usd` and compared it with `revenue_usd ~ ad_spend_usd + C(channel) + C(region) + C(month)`.

Result: the spend-only model already explains **94.5%** of revenue variance (`R^2 = 0.945`), with a slope of **2.495** revenue dollars per additional dollar of spend. Adding all categorical controls changes `R^2` only from **0.945 to 0.946**, and the nested-model F-test is not significant (`p = 0.748`). The fitted line in [`plots/spend_vs_revenue.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpjt_ydnir/plots/spend_vs_revenue.png) shows a tight linear trend with heavy overlap across channels.

Interpretation: in this dataset, **budget level determines scale outcomes**, and the categorical campaign labels add little incremental explanatory value for revenue.

### 2. Efficiency is remarkably stable across channels and over time.

Hypothesis: some channels should produce better efficiency than others, visible as higher ROAS or CTR.

Test: I compared channel-level distributions for CTR, CPC, CPM, ROAS, and revenue-per-click using ANOVA and Kruskal-Wallis tests, and visualized ROAS by channel plus month-by-channel mean ROAS.

Result: none of the channel differences in efficiency metrics are statistically persuasive. For ROAS, the ANOVA p-value is **0.680** and the effect size is tiny (`Cohen's f = 0.039`). Mean ROAS ranges only from **2.493** to **2.527** across channels. Monthly mean ROAS also stays inside a narrow band of roughly **2.454 to 2.544**.

Evidence:

- [`plots/roas_by_channel.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpjt_ydnir/plots/roas_by_channel.png) shows strong overlap in ROAS distributions across Display, Email, Search, and Social.
- [`plots/monthly_roas_heatmap.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpjt_ydnir/plots/monthly_roas_heatmap.png) shows channel-month averages staying within a fairly modest **2.34 to 2.70** range rather than separating into strong seasonal or channel-specific regimes.

Interpretation: the data does **not** support the common marketing intuition that one channel is clearly more efficient here. The practical implication is that channel selection appears to matter less than execution at the campaign level, at least at this level of aggregation.

### 3. There is no evidence of diminishing returns in ROAS at higher spend levels, but there are campaign-level outliers.

Hypothesis: if larger budgets saturate, ROAS should decline as spend increases.

Test: I compared ROAS across spend quintiles and added a quadratic spend term to the full revenue model.

Result: ROAS is essentially flat across spend quintiles, with mean values from **2.497** to **2.517** and ANOVA `p = 0.985`. The quadratic term in the revenue model also fails to improve fit (`p = 0.466`).

What does vary is individual-campaign execution. The largest positive outlier is campaign **406** (Display, North, month 8), with ROAS **3.476** and a studentized residual of **5.12**. Several campaigns underperform just as strongly, including campaign **199** with ROAS **1.659**. These are visible in [`plots/revenue_model_residuals.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpjt_ydnir/plots/revenue_model_residuals.png).

Interpretation: the dataset suggests **constant average returns to spend**, with the meaningful variation happening at the individual campaign level rather than as a smooth budget-efficiency curve.

## Supporting Detail

### Orientation Summary

- Shape: **1000 rows x 8 raw columns**
- Null values: **0 in every column**
- Unique IDs: **1000 campaign IDs for 1000 rows**
- Numeric ranges:
  - `ad_spend_usd`: **729.29 to 49,986.02**
  - `impressions`: **7,126 to 709,259**
  - `clicks`: **145 to 34,102**
  - `revenue_usd`: **1,480.53 to 155,837.95**
- Category counts:
  - Channels: {'Display': 226, 'Email': 266, 'Search': 258, 'Social': 250}
  - Regions: {'East': 240, 'North': 261, 'South': 258, 'West': 241}
  - Months: {1: 83, 2: 94, 3: 81, 4: 84, 5: 88, 6: 87, 7: 88, 8: 64, 9: 79, 10: 97, 11: 73, 12: 82}

### Selected Summary Statistics

Channel-level mean efficiency metrics:

|channel|ctr|cpc|cpm|roas|rpc|
|---|---|---|---|---|---|
|Display|0.0308|3.4527|90.6021|2.4925|8.6001|
|Email|0.0297|3.7091|89.7924|2.4961|9.2717|
|Search|0.0287|3.7638|90.3922|2.5130|9.4907|
|Social|0.0301|3.5915|89.8144|2.5269|9.1107|

Region-level mean CTR and ROAS:

|region|ctr|roas|
|---|---|---|
|East|0.0307|2.5207|
|North|0.0292|2.4687|
|South|0.0295|2.4964|
|West|0.0298|2.5475|

Spend-quintile mean CTR and ROAS:

|spend_quintile|ctr|roas|
|---|---|---|
|Q1|0.0305|2.5060|
|Q2|0.0292|2.5169|
|Q3|0.0303|2.5119|
|Q4|0.0285|2.5050|
|Q5|0.0304|2.4968|

### Model Notes

- `revenue_usd ~ ad_spend_usd`: `R^2 = 0.945`
- `revenue_usd ~ ad_spend_usd + channel + region + month`: `R^2 = 0.946`
- `clicks ~ impressions + channel + region + month`: `R^2 = 0.653`. Impressions are predictive, but categorical effects are weak and inconsistent.
- `roas ~ ad_spend_usd + channel + region + month`: `R^2 = 0.017`. This confirms that the observed fields explain almost none of the variation in efficiency.

## What These Findings Mean

If this were a real marketing reporting table, the strongest operational message would be: **budget allocation changes total output far more reliably than swapping channels, regions, or months**. That does not mean channels are irrelevant in general; it means this particular dataset does not contain strong evidence of channel-specific or seasonal efficiency differences.

A second implication is organizational: because average ROAS is stable, optimization effort should probably focus on **campaign-level diagnostics and creative/execution review**, not broad reallocations based solely on the provided channel or region labels.

## Limitations And Self-Critique

- This is aggregated campaign data. Important causal drivers such as audience, creative, offer, bidding strategy, and conversion definition are absent.
- The lack of channel effects may reflect the data-generating process rather than the real world. A synthetic or heavily normalized dataset can make channels look artificially similar.
- I assumed campaigns are independent. If some rows are repeated campaigns over time or share hidden grouping structure, standard errors may be optimistic.
- I used OLS mainly as a descriptive tool. The residual plot also shows **wider variance at higher fitted revenue**, so exact standard-error-based inference should be interpreted cautiously even though the high-level signal is clear.
- I did not investigate interaction terms such as `channel x month` in depth because the main effects were already negligible and the cell counts are modest.
- The dataset contains no outcome definition beyond `revenue_usd`. If revenue capture differs across channels, ROAS comparisons could still be biased.

## Bottom Line

The clearest pattern is a **near-linear spend-to-revenue relationship** with an average return of about **2.49x revenue per $1 spent**. By contrast, **channel, region, month, and spend tier show little evidence of systematic efficiency differences**. The most actionable signal in the data is therefore the presence of **campaign-level outliers**, not broad structural winners and losers.
