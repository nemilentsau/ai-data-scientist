# Analysis Report

## What this dataset appears to be

This is a session-level web conversion dataset with **1,500 sessions** and **8 columns**. Each row appears to represent one browsing session with a unique `session_id`, a binary outcome `converted`, and session attributes such as ad budget, time of day, device, page load time, previous visits, and a `channel_score`.

Key orientation facts:

- No columns contain missing values.
- `converted` is moderately imbalanced: **29.3%** of sessions converted (439 of 1500).
- `device` has 3 levels: mobile (833), desktop (509), and tablet (158).
- Numeric ranges are plausible for session-level data: `time_of_day_hour` spans **0.0 to 24.0**, `channel_score` spans **0.0 to 1.0**, `page_load_time_sec` spans **0.3 to 15.0**, and `previous_visits` spans **0 to 10**.
- Values in the raw rows are internally consistent with the column names; there were no obvious coded missing values or malformed date strings.

## Key findings

### 1. Sessions later in the day convert substantially more often than early-day sessions

**Hypothesis.** Conversion probability increases as the day progresses.

**Test.** I first plotted empirical conversion rates by rounded hour of day ([`conversion_by_hour.png`](./plots/conversion_by_hour.png)), then fit a logistic regression controlling for `channel_score`.

**Evidence.**

- In the adjusted logistic model, `time_of_day_hour` has coefficient **0.0788** (95% CI **0.0611 to 0.0965**, p < 1e-17), equivalent to an odds ratio of **1.082 per hour**.
- Empirically, rounded-hour conversion rises from **10.5% at 1:00** and **13.5% at 0:00** to **45.5% at 21:00**, **39.6% at 22:00**, **55.6% at 23:00**, and **47.2% at 24:00** in [`conversion_by_hour.png`](./plots/conversion_by_hour.png).
- Moving from the 10th to the 90th percentile of `time_of_day_hour` (about **2.29** to **21.5** hours), while holding `channel_score` at its median, raises predicted conversion by **29.0 percentage points**.

**Interpretation.** Time of day is not a minor nuisance variable here; it is one of the two dominant signals in the dataset. This is a correlational result. It could reflect user intent, campaign scheduling, audience composition, or unobserved operational factors rather than a direct causal effect of the clock.

### 2. `channel_score` is the strongest quality signal in the data

**Hypothesis.** Higher `channel_score` marks higher-intent sessions and should strongly predict conversion.

**Test.** I examined conversion by score decile in [`conversion_by_channel_score_decile.png`](./plots/conversion_by_channel_score_decile.png) and estimated an adjusted logistic model.

**Evidence.**

- In the adjusted model, `channel_score` has coefficient **1.8928** (95% CI **1.4630 to 2.3226**, p < 1e-17), which corresponds to an odds ratio of **6.64** for a one-unit increase.
- Score-bin conversion rises steadily from **8.7% in the bottom decile** to **50.0% in the top decile**, as shown in [`conversion_by_channel_score_decile.png`](./plots/conversion_by_channel_score_decile.png).
- Moving from the 10th to the 90th percentile of `channel_score` (about **0.092** to **0.885**), while holding `time_of_day_hour` at its median, raises predicted conversion by **29.2 percentage points**.

**Interpretation.** `channel_score` behaves like a compact summary of lead or traffic quality. Operationally, it is at least as important as time of day: the 10th-to-90th percentile contrast is almost identical in magnitude.

### 3. Several intuitive variables add little once time of day and channel score are known

**Hypothesis.** Variables that sound important on paper, especially `ad_budget_usd`, `page_load_time_sec`, `device`, and `previous_visits`, may not materially improve explanation or prediction after controlling for the two dominant signals.

**Test.** I fit a full logistic model, visualized adjusted odds ratios in [`adjusted_odds_ratios.png`](./plots/adjusted_odds_ratios.png), and compared it with a two-variable model using likelihood-ratio testing and 5-fold cross-validation.

**Evidence.**

- In the full model, the following adjusted effects are statistically weak and centered near no effect:
  - `ad_budget_usd`: OR **0.99998** per dollar, p = **0.597**
  - `page_load_time_sec`: OR **0.989** per second, p = **0.729**
  - `previous_visits`: OR **1.047** per visit, p = **0.165**
  - `device` differences are small: mobile vs desktop OR **1.07** (p = **0.601**), tablet vs desktop OR **1.06** (p = **0.777**)
- The five added variables do **not** significantly improve fit over the two-variable model: likelihood-ratio statistic **2.59** on **5** degrees of freedom, p = **0.763**.
- Out of sample, the simpler model slightly outperforms the full one:
  - Core model (`time_of_day_hour` + `channel_score`): mean 5-fold ROC AUC **0.696**, log loss **0.554**
  - Full model: mean 5-fold ROC AUC **0.692**, log loss **0.556**

**Interpretation.** This is the most counter-intuitive result in the dataset. It suggests that spending more budget on a session, serving a different device type, or even having slower page loads within the observed range does not explain much additional variation in conversion once session timing and channel quality are already accounted for. In practical terms, a simpler targeting story explains the data better than a richer operational one.

### Practical combined effect

The two-variable model implies a large difference between low-quality early sessions and high-quality late sessions, shown in [`predicted_probability_heatmap.png`](./plots/predicted_probability_heatmap.png):

- At **2:00** with `channel_score = 0.1`, predicted conversion is **7.4%**
- At **2:00** with `channel_score = 0.9`, predicted conversion is **26.8%**
- At **23:00** with `channel_score = 0.1`, predicted conversion is **29.4%**
- At **23:00** with `channel_score = 0.9`, predicted conversion is **65.6%**

This means timing and traffic quality operate as two roughly comparable levers, and the best-case combination is far better than either lever alone.

## What the findings mean

If this dataset is representative of actual acquisition performance, the strongest practical implication is prioritization:

1. Optimize for **better channel quality** and for **late-day high-intent traffic windows** before spending effort on device segmentation or small page-speed differences.
2. A simple scoring-and-timing model may be sufficient for forecasting or ranking session quality.
3. Additional data collection should focus on latent drivers that could explain *why* late sessions convert better, such as campaign type, geography, weekday, referrer, landing page, or user intent markers.

## Limitations and self-critique

- **No causal identification.** None of these variables were experimentally manipulated, so the time-of-day effect could be confounded by campaign scheduling or audience mix.
- **Possible synthetic structure.** The clean ranges, lack of missingness, and unusually sharp dominance of two variables make the data look somewhat simulated. That does not invalidate the analysis, but it limits how confidently these findings should be generalized.
- **No timestamp granularity beyond hour.** I could not separate weekday effects, seasonality, or campaign pacing from within-day timing.
- **Limited feature space.** Strong null results for `ad_budget_usd` and `page_load_time_sec` only apply within the observed ranges and in the presence of the other available columns.
- **Model form.** I checked for a quadratic hour effect and found no support beyond a linear increase on the log-odds scale, but more flexible nonlinear models could reveal finer structure if more data were available.
- **Visual review.** After saving each plot, I loaded it back from disk to verify it rendered correctly and retained nontrivial visual structure:

- adjusted_odds_ratios.png: shape=(900, 1500, 4), mean_pixel=0.981, std_pixel=0.108
- conversion_by_channel_score_decile.png: shape=(900, 1650, 4), mean_pixel=0.861, std_pixel=0.284
- conversion_by_hour.png: shape=(900, 1500, 4), mean_pixel=0.967, std_pixel=0.107
- predicted_probability_heatmap.png: shape=(1050, 1500, 4), mean_pixel=0.880, std_pixel=0.243
