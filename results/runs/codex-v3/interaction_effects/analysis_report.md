# Dataset Analysis Report

## What this dataset is about

This appears to be a session-level digital conversion dataset with **1,500 sessions** and **8 columns**. Each row represents one visit identified by `session_id`, with a binary outcome `converted`. The predictors describe media spend (`ad_budget_usd`), timing (`time_of_day_hour`), traffic quality (`channel_score`), experience quality (`page_load_time_sec`), return behavior (`previous_visits`), and device type.

The data is unusually clean: there are **no missing values**, no duplicate `session_id`s, and all columns have plausible ranges. The only categorical feature is `device` with **833 mobile**, **509 desktop**, and **158 tablet** sessions. The outcome is moderately imbalanced: **29.3%** of sessions converted.

## Key findings

### 1. Conversion is driven mainly by a time-by-channel-quality interaction

The strongest pattern is not a simple main effect. Conversion rises later in the day, but the increase is much steeper for high-`channel_score` traffic than for low-score traffic. Adding the interaction `channel_score:time_of_day_hour` improved logistic model fit with a likelihood-ratio statistic of **18.81** on **1** degree of freedom (**p = 1.44e-05**).

Observed conversion rates make the interaction concrete. In the lowest `channel_score` tercile during **00-06**, the conversion rate is **10.9%**. In the highest `channel_score` tercile during **18-24**, it reaches **75.0%**. The plot [plots/conversion_by_time_and_score.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/conversion_by_time_and_score.png) shows both the observed heatmap and the fitted probability curves.

At representative median values for the other features, the interaction-aware model predicts:

- For `channel_score = 0.1`, conversion rises only from **13.9%** at hour 2 to **18.8%** at hour 22.
- For `channel_score = 0.9`, conversion rises from **17.6%** at hour 2 to **74.7%** at hour 22.

Interpretation: later-day demand appears to be concentrated in higher-quality channels. If this pattern is real operationally, scheduling and channel allocation matter more than uniformly increasing spend.

### 2. `channel_score` is a strong monotonic ranking signal

Even before considering interaction, `channel_score` has a clear positive association with conversion. In quintile summaries, the conversion rate rises from **16.3%** in the lowest fifth of scores to **43.7%** in the highest fifth. The decile view in [plots/conversion_vs_channel_score.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/conversion_vs_channel_score.png) is close to monotonic, which is what a useful ranking variable should look like.

The predictive model reinforces this. A regularized logistic regression evaluated with 5-fold stratified cross-validation achieved mean **ROC AUC = 0.692** and mean **Brier score = 0.186**. That is materially better than chance, but far from deterministic, implying `channel_score` carries useful information without fully determining the outcome. The calibration curve in [plots/model_calibration.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/model_calibration.png) is reasonably close to the diagonal, so predicted probabilities are directionally credible.

Interpretation: `channel_score` is likely the best single feature for prioritization or targeting, especially when combined with time-of-day.

### 3. More budget does not translate into more conversion in this sample

`ad_budget_usd` looks important by name, but not by evidence. Across budget quintiles, conversion rates remain in a narrow band from **26.3%** to **31.3%**. In the interaction-aware logistic model, dropping `ad_budget_usd` barely changes fit (likelihood-ratio statistic **0.233**, **p = 0.629**).

The budget decile plot [plots/ad_budget_vs_conversion.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/ad_budget_vs_conversion.png) is effectively flat within sampling noise. Device type is also uninformative after adjustment (**p = 0.929**), and page load time is not distinguishable from noise here (**p = 0.784**).

Interpretation: in this dataset, outcomes appear to depend more on *who* is arriving and *when* they arrive than on raw spend level, device mix, or page latency. If the practical question is where to invest effort, reallocating timing or channel quality would have stronger support than increasing budget alone.

## What the findings mean

The dataset behaves like a marketing or acquisition funnel where traffic quality and timing matter most. The strongest operational implication is that the same hour of day is not equally valuable for all traffic sources. High-quality channels become much more productive late in the day, while low-quality channels stay relatively weak throughout.

That makes two decisions look especially leverageable:

- Prioritize late-day delivery for higher-scoring channels.
- Be skeptical of budget increases that are not paired with channel-quality or timing improvements.

## Limitations and self-critique

- This is observational data, so none of the relationships should be interpreted causally. A late-day uplift could reflect unobserved user intent or campaign targeting rather than time itself.
- I assumed rows are independent sessions. If repeated users or campaign clusters exist but are not encoded, standard errors may be too optimistic.
- `page_load_time_sec` being null in the model is counter-intuitive. That could mean load time truly has little effect in this range, but it could also mean the dataset is synthetic, the variation is too small, or more severe latency occurs too rarely to detect cleanly.
- The interaction result is strong, but I did not test richer nonlinear specifications beyond that interaction. A smoother or tree-based model might find additional threshold effects.
- The predictive model is only moderately discriminative (AUC about **0.69**), so important drivers are likely missing.

## Files produced

- [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/analysis_report.md)
- [plots/conversion_by_time_and_score.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/conversion_by_time_and_score.png)
- [plots/conversion_vs_channel_score.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/conversion_vs_channel_score.png)
- [plots/ad_budget_vs_conversion.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/ad_budget_vs_conversion.png)
- [plots/model_calibration.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/model_calibration.png)
