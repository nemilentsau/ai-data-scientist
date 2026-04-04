# Analysis Report

## What this dataset is about

This is a daily operational dataset spanning **2022-01-01 to 2024-12-30** (1,095 consecutive days, no missing dates). It tracks a website or product funnel with seven variables:

- `pageviews`
- `unique_visitors`
- `bounce_rate`
- `avg_session_duration_sec`
- `new_signups`
- `support_tickets`

The data are clean at a structural level: there are **0 nulls** across all columns, `date` parses cleanly as a daily timestamp, and each row appears to represent one day of activity. The most important orienting fact is that traffic metrics move a lot over time while `new_signups` and `support_tickets` barely do.

Key ranges:

- `pageviews`: mean **940.5**, min **100**, max **1864**
- `unique_visitors`: mean **611.1**, min **57**, max **1247**
- `bounce_rate`: mean **0.448**, spanning **0.172** to **0.695**
- `avg_session_duration_sec`: mean **180.1** seconds
- `new_signups`: mean **14.84** per day
- `support_tickets`: mean **2.96** per day

## Key findings

### 1. Traffic grew dramatically and followed a strong recurring seasonal pattern

Traffic volume is not stationary. Mean daily `pageviews` rose from **647.1** in 2022 to **1239.8** in 2024, a **91.6%** increase. `unique_visitors` shows the same pattern, rising from **419.5** to **806.1**.

The combined time-structure model `pageviews ~ year + day_of_week + month` explains **94.2%** of pageview variance. Year effects are large and highly significant:

- 2023 adds **287.0 pageviews/day** relative to 2022, **p = 1.38e-241**
- 2024 adds **591.8 pageviews/day** relative to 2022, **p = <1e-300**

Weekday effects are also large. Monday averages **1124.3** pageviews versus **747.7** on Thursday, a gap of **50.4%**. Across calendar months, average traffic peaks in **Apr (1265.1)** and reaches its trough in **Sep (616.5)**.

Evidence: see `plots/traffic_seasonality.png`. The year-to-year upward shift is visible in the rolling mean, while the monthly bar chart shows the persistent annual cycle. The non-parametric year test also strongly rejects equal traffic distributions across years (**Kruskal-Wallis p = 5.51e-106**).

**Interpretation:** traffic acquisition improved substantially over the three-year span, but that improvement appears to come from a recurring seasonal system rather than random bursts.

### 2. Signups did not grow with traffic, engagement, or time

This is the most important counter-intuitive finding. Despite major traffic growth, `new_signups` stayed almost flat:

- 2022 mean: **14.92/day**
- 2023 mean: **14.60/day**
- 2024 mean: **15.00/day**

A raw Pearson correlation between `unique_visitors` and `new_signups` is essentially zero (**r = -0.0064, p = 0.8312**). More importantly, a Poisson count model using `log(unique_visitors)`, `bounce_rate`, `avg_session_duration_sec`, day-of-week, and month still finds no meaningful predictor:

- `log(unique_visitors)` coefficient: **-0.0042**, **p = 0.8446**
- `bounce_rate` coefficient: **-0.1149**, **p = 0.2601**
- `avg_session_duration_sec` coefficient: **-0.00011**, **p = 0.5925**

The simpler OLS model `new_signups ~ year + day_of_week + month` explains only **1.2%** of variance, and the year effect is not significant (**Kruskal-Wallis p = 0.3308**).

Evidence: `plots/signups_vs_traffic.png`. The left panel shows a near-flat fitted line in daily data; the right panel shows monthly unique visitors rising sharply while signups remain close to a horizontal band around 15/day.

**Interpretation:** whatever drives signups is largely disconnected from the observed website traffic and engagement measures. Plausible mechanisms include a signup bottleneck outside the web session, a capped acquisition process, or a metric definition mismatch where signups come from channels not reflected in site traffic.

### 3. Support tickets behave like a stable background process rather than a traffic-driven workload

`support_tickets` are unusually stable for a metric that might be expected to scale with growth:

- Mean: **2.962/day**
- Variance: **2.905**
- Dispersion index (`variance / mean`): **0.981**

A dispersion index near 1 is what a Poisson-like count process would produce. That matches the fitted Poisson model well: the model’s Pearson chi-square / df is **0.987**, and neither year, weekday, traffic, nor signups are significant predictors. The raw correlation with `unique_visitors` is also effectively zero (**r = -0.0013, p = 0.9654**). Year-level distributions are indistinguishable (**Kruskal-Wallis p = 0.7830**).

Evidence: `plots/support_ticket_process.png`. The observed ticket-count histogram closely tracks the Poisson expectation, and the visitor-vs-ticket scatter has no visible slope.

**Interpretation:** support demand appears operationally steady and mostly independent of traffic growth. If this is real, staffing forecasts should be based on the historical daily average rather than on traffic peaks.

## What the findings mean

The dataset tells a very specific story:

1. The top of the funnel improved a lot. Traffic nearly doubled from 2022 to 2024 and follows a clear weekly and annual cycle.
2. That traffic growth did **not** translate into more signups. The conversion system appears constrained somewhere after the visit occurs, or the `new_signups` field is not measuring the same funnel represented by the traffic columns.
3. Downstream support load stayed flat as well. Operational demand did not rise with acquisition volume.

From a practical standpoint, the largest business question is not “how do we get more traffic?” but “why are additional visitors failing to produce additional signups?” The data point to a measurement or funnel-efficiency problem, not an awareness problem.

## Limitations and self-critique

- This is observational time-series data. The analysis can show stable associations and non-associations, but it cannot identify causal mechanisms.
- I assumed each row is an independent daily aggregate. In reality, adjacent days are autocorrelated, and omitted events such as campaigns, product launches, outages, or pricing changes could explain part of the patterns.
- The strongest “conversion” signal can be misread if one relies on `signups / visitors` ratios alone, because ratios can create spurious relationships with their denominator. I explicitly checked raw `new_signups` counts with Poisson models to avoid that artifact.
- I did not have channel-level acquisition data, experiment logs, cohort definitions, or a more detailed funnel. Any of those could distinguish between a real conversion bottleneck and a metric-definition mismatch.
- The support-ticket conclusion assumes the process is adequately summarized by daily counts. Severity, backlog, ticket resolution time, and customer mix are not observed here.

The main alternative explanation I could not rule out is that `new_signups` and `support_tickets` are generated by a mostly separate customer population than the web traffic. If that is true, the weak relationships are not surprising. That possibility should be checked before making operational decisions from the apparent disconnect.
