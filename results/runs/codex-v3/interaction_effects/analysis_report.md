# Analysis Report

## What this dataset is about

This dataset contains **1,500 web sessions** with a binary conversion outcome (`converted`). Each row appears to represent one marketing-driven session with session-level inputs: spend (`ad_budget_usd`), visit timing (`time_of_day_hour`), channel quality (`channel_score`), device type, page performance (`page_load_time_sec`), and prior engagement (`previous_visits`).

The data is structurally clean:

- Shape: **1500 rows x 8 columns**
- Missing values: **none**
- Outcome rate: **29.3%** (439 conversions)
- Device mix: mobile is the largest group, with desktop and tablet smaller

The main caveat from orientation is conceptual rather than technical: this is observational session data. The variables look plausible, but they do not identify causal effects on their own.

## Key findings

### 1. Conversion rises sharply later in the day

**Hypothesis.** Sessions later in the day convert more often than early-morning sessions.

**Evidence.**

- The raw conversion rate climbs from **15.2%** in the `0-6` band to **42.0%** in the `18-24` band, shown in [`conversion_by_time_band.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpis8z0vei/plots/conversion_by_time_band.png).
- In a multivariable logistic regression that controls for budget, channel score, device, page load time, and previous visits, a **1 standard deviation increase in `time_of_day_hour`** is associated with an odds ratio of **1.73** (95% CI **1.53** to **1.95**, p < 0.001), shown in [`adjusted_odds_ratios.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpis8z0vei/plots/adjusted_odds_ratios.png).

**Interpretation.** Later-day traffic appears materially more purchase-ready. This is a large effect in both the raw rates and the adjusted model, so it is unlikely to be explained purely by device mix or spend.

### 2. Channel quality is another strong driver, with a clear monotonic pattern

**Hypothesis.** Higher `channel_score` reflects higher-intent traffic and should increase conversion.

**Evidence.**

- Conversion increases from **17.9%** in the lowest score quartile to **43.5%** in the highest quartile, shown in [`conversion_by_channel_score_quartile.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpis8z0vei/plots/conversion_by_channel_score_quartile.png).
- In the adjusted logistic model, a **1 standard deviation increase in `channel_score`** has an odds ratio of **1.72** (95% CI **1.52** to **1.94**, p < 0.001).

**Interpretation.** `channel_score` behaves like a genuine quality or intent measure. The monotonic lift across quartiles makes the effect easy to operationalize: better channels are not just slightly better on average; they step up conversion consistently.

### 3. Time of day and channel score compound, while budget and page speed add little signal here

**Hypothesis.** The best conversion outcomes occur when high-intent traffic arrives at high-intent times, and some seemingly important operational variables may matter less than expected.

**Evidence.**

- The interaction heatmap in [`time_channel_interaction_heatmap.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpis8z0vei/plots/time_channel_interaction_heatmap.png) shows the lowest-converting segment at **13.3%** (`0-6` plus bottom channel-score quartile) and the highest at **72.9%** (`18-24` plus top channel-score quartile).
- In the adjusted model, `ad_budget_usd`, `page_load_time_sec`, `previous_visits`, and device indicators all have confidence intervals that cross 1.0 in [`adjusted_odds_ratios.png`](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpis8z0vei/plots/adjusted_odds_ratios.png).
- A predictive logistic regression evaluated with 5-fold cross-validation reached ROC AUC **0.69 +/- 0.03**. That is useful but not high, which suggests the dataset contains real structure without being close to deterministic.

**Interpretation.**

- The strongest practical signal is to align delivery toward sessions that are both late-day and high-channel-score.
- The lack of a detectable budget effect does **not** prove spend is irrelevant; it only shows no clear session-level linear relationship in this dataset after adjustment.
- The weak page-speed signal may mean performance is already acceptable for most sessions, or that page speed is too coarsely measured here to expose the real friction.

## What the findings mean

If this dataset reflects acquisition or conversion operations, the immediate implication is prioritization:

- **When to push traffic:** later-day sessions appear substantially more conversion-ready.
- **Where to push traffic:** higher `channel_score` sources look materially better.
- **What not to overstate:** more spend per session, faster pages within the observed range, and device category do not show strong independent effects in this sample.

This suggests a targeting or allocation strategy should emphasize **traffic quality and timing** before assuming that marginal budget increases or device-specific treatments will move conversion as much.

## Limitations and self-critique

### Alternative explanations

- `time_of_day_hour` may proxy for unmeasured factors such as audience segment, campaign scheduling, or offer timing rather than a pure clock-time effect.
- `channel_score` could itself be a composite of other latent variables. If so, it is predictive, but not necessarily a mechanistic cause.

### Assumptions

- The logistic model assumes additive linear effects on the log-odds scale for the standardized continuous features.
- Sessions are treated as independent observations. If multiple sessions belong to the same user, standard errors may be somewhat optimistic.
- This analysis focuses on association, not causation.

### What I did not investigate

- I did not test non-linear effects beyond a simple quadratic check for time-of-day, which did not improve fit.
- I did not analyze user-level recurrence because there is no stable user identifier.
- I did not examine campaign, geography, landing page, or creative effects because those fields are absent.

### Bottom line

The evidence supports a clear story: **conversion is most strongly associated with session timing and channel quality**, and those factors compound. The data does **not** support strong independent effects for budget, device, or page-load time within the ranges observed here. These are defensible association findings, but they should not be interpreted as causal without experimental or richer observational controls.
