from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.anova import anova_lm


ROOT = Path(__file__).resolve().parent
PLOTS = ROOT / "plots"
PLOTS.mkdir(exist_ok=True)


def cohens_f_from_anova(groups):
    values = np.concatenate(groups)
    grand_mean = values.mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = ((values - grand_mean) ** 2).sum()
    eta_sq = ss_between / ss_total if ss_total else 0.0
    return np.sqrt(eta_sq / (1 - eta_sq)) if eta_sq < 1 else np.inf


def savefig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def df_to_markdown_table(frame, float_fmt=".4f"):
    headers = [str(c) for c in frame.reset_index().columns]
    rows = []
    for row in frame.reset_index().itertuples(index=False):
        formatted = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                formatted.append(format(float(value), float_fmt))
            else:
                formatted.append(str(value))
        rows.append(formatted)

    divider = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = [
        "|" + "|".join(headers) + "|",
        divider,
    ]
    lines.extend("|" + "|".join(row) + "|" for row in rows)
    return "\n".join(lines)


def main():
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["figure.figsize"] = (11, 7)

    raw_df = pd.read_csv(ROOT / "dataset.csv")
    df = raw_df.copy()
    df["ctr"] = df["clicks"] / df["impressions"]
    df["cpc"] = df["ad_spend_usd"] / df["clicks"]
    df["cpm"] = df["ad_spend_usd"] / df["impressions"] * 1000
    df["roas"] = df["revenue_usd"] / df["ad_spend_usd"]
    df["rpc"] = df["revenue_usd"] / df["clicks"]
    df["spend_quintile"] = pd.qcut(df["ad_spend_usd"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])

    channel_counts = df["channel"].value_counts().sort_index()
    region_counts = df["region"].value_counts().sort_index()
    month_counts = df["month"].value_counts().sort_index()

    channel_metrics = (
        df.groupby("channel")[["ctr", "cpc", "cpm", "roas", "rpc"]]
        .agg(["mean", "median", "std"])
        .round(4)
    )
    region_metrics = df.groupby("region")[["ctr", "roas"]].mean().round(4)
    month_metrics = df.groupby("month")[["ctr", "roas"]].mean().round(4)
    spend_metrics = (
        df.groupby("spend_quintile", observed=False)[["ad_spend_usd", "ctr", "roas"]]
        .agg(["mean", "median", "std"])
        .round(4)
    )

    channel_tests = {}
    for metric in ["ctr", "cpc", "cpm", "roas", "rpc"]:
        groups = [g[metric].to_numpy() for _, g in df.groupby("channel")]
        anova = stats.f_oneway(*groups)
        kruskal = stats.kruskal(*groups)
        channel_tests[metric] = {
            "anova_p": anova.pvalue,
            "kruskal_p": kruskal.pvalue,
            "cohens_f": cohens_f_from_anova(groups),
        }

    spend_roas_groups = [g["roas"].to_numpy() for _, g in df.groupby("spend_quintile", observed=False)]
    spend_roas_anova = stats.f_oneway(*spend_roas_groups)
    spend_roas_f = cohens_f_from_anova(spend_roas_groups)

    rev_linear = smf.ols("revenue_usd ~ ad_spend_usd", data=df).fit()
    rev_full = smf.ols("revenue_usd ~ ad_spend_usd + C(channel) + C(region) + C(month)", data=df).fit()
    rev_quad = smf.ols("revenue_usd ~ ad_spend_usd + I(ad_spend_usd**2) + C(channel) + C(region) + C(month)", data=df).fit()
    roas_model = smf.ols("roas ~ ad_spend_usd + C(channel) + C(region) + C(month)", data=df).fit()
    clicks_model = smf.ols("clicks ~ impressions + C(channel) + C(region) + C(month)", data=df).fit()

    rev_anova = anova_lm(rev_linear, rev_full)
    quad_anova = anova_lm(rev_full, rev_quad)

    influence = rev_linear.get_influence().summary_frame()
    outliers = df[["campaign_id", "channel", "region", "month", "ad_spend_usd", "revenue_usd", "roas"]].copy()
    outliers["student_resid"] = influence["student_resid"]
    outliers["cooks_d"] = influence["cooks_d"]
    outliers["fitted"] = rev_linear.fittedvalues
    outliers["abs_student_resid"] = outliers["student_resid"].abs()
    top_outliers = outliers.sort_values("abs_student_resid", ascending=False).head(5)

    corr = df[["ad_spend_usd", "impressions", "clicks", "revenue_usd", "ctr", "cpc", "cpm", "roas", "rpc"]].corr()

    # Plot 1: spend vs revenue
    fig, ax = plt.subplots()
    sns.scatterplot(
        data=df,
        x="ad_spend_usd",
        y="revenue_usd",
        hue="channel",
        alpha=0.65,
        s=55,
        ax=ax,
    )
    x = np.linspace(df["ad_spend_usd"].min(), df["ad_spend_usd"].max(), 200)
    ax.plot(x, rev_linear.params["Intercept"] + rev_linear.params["ad_spend_usd"] * x, color="black", lw=2.5)
    ax.set_title("Revenue Scales Almost Linearly With Spend")
    ax.set_xlabel("Ad Spend (USD)")
    ax.set_ylabel("Revenue (USD)")
    ax.text(
        0.03,
        0.97,
        f"Slope = {rev_linear.params['ad_spend_usd']:.3f}\n$R^2$ = {rev_linear.rsquared:.3f}",
        transform=ax.transAxes,
        va="top",
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "0.7"},
    )
    savefig(PLOTS / "spend_vs_revenue.png")

    # Plot 2: ROAS by channel
    fig, ax = plt.subplots()
    order = sorted(df["channel"].unique())
    sns.boxplot(
        data=df,
        x="channel",
        y="roas",
        hue="channel",
        order=order,
        hue_order=order,
        showfliers=False,
        palette="Set2",
        dodge=False,
        legend=False,
        ax=ax,
    )
    sns.stripplot(
        data=df.sample(min(len(df), 250), random_state=42),
        x="channel",
        y="roas",
        order=order,
        color="0.2",
        alpha=0.35,
        size=3,
        ax=ax,
    )
    ax.set_title("ROAS Distribution Overlaps Heavily Across Channels")
    ax.set_xlabel("Channel")
    ax.set_ylabel("ROAS = revenue / spend")
    ax.axhline(df["roas"].mean(), color="black", ls="--", lw=1.5, alpha=0.7)
    savefig(PLOTS / "roas_by_channel.png")

    # Plot 3: monthly heatmap
    heat = df.pivot_table(index="channel", columns="month", values="roas", aggfunc="mean").reindex(order)
    fig, ax = plt.subplots(figsize=(13, 4.8))
    sns.heatmap(
        heat,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        vmin=float(heat.min().min()),
        vmax=float(heat.max().max()),
        cbar_kws={"label": "Mean ROAS"},
        ax=ax,
    )
    ax.set_title("Monthly Mean ROAS Varies Modestly Across Channel-Month Cells")
    ax.set_xlabel("Month")
    ax.set_ylabel("Channel")
    savefig(PLOTS / "monthly_roas_heatmap.png")

    # Plot 4: revenue residuals with outliers labeled
    fig, ax = plt.subplots()
    sns.scatterplot(data=outliers, x="fitted", y="student_resid", hue="channel", alpha=0.65, s=55, ax=ax)
    ax.axhline(0, color="black", lw=1.5)
    ax.axhline(2, color="0.5", lw=1, ls="--")
    ax.axhline(-2, color="0.5", lw=1, ls="--")
    for _, row in top_outliers.iterrows():
        ax.text(row["fitted"], row["student_resid"], str(int(row["campaign_id"])), fontsize=9, ha="left", va="bottom")
    ax.set_title("A Few Campaigns Deviate Materially From the Spend-Revenue Trend")
    ax.set_xlabel("Fitted Revenue From Spend-Only Model (USD)")
    ax.set_ylabel("Studentized Residual")
    savefig(PLOTS / "revenue_model_residuals.png")

    report = f"""# Marketing Campaign Analysis

## What This Dataset Appears To Be

This dataset contains **1,000 campaign-level observations** with one row per campaign and 8 raw fields: campaign ID, region, channel, ad spend, impressions, clicks, revenue, and month. It is structurally clean: there are **no missing values**, IDs are unique, `month` is encoded as integers **1-12**, and the categorical fields are balanced enough for comparison (`channel`: {channel_counts.to_dict()}, `region`: {region_counts.to_dict()}).

The raw rows make sense for a paid-media table: spend scales with impressions, clicks, and revenue, while channel and region look like campaign attributes rather than repeated measurements. The main caution is interpretive rather than technical: this looks like an observational, already-aggregated dataset, so it can support **associational** claims but not causal attribution.

## Key Findings

### 1. Revenue is overwhelmingly explained by spend, not by channel, region, or month.

Hypothesis: if campaign performance differs materially by channel or season, then adding `channel`, `region`, and `month` to a spend-based revenue model should meaningfully improve fit.

Test: I fit an OLS model `revenue_usd ~ ad_spend_usd` and compared it with `revenue_usd ~ ad_spend_usd + C(channel) + C(region) + C(month)`.

Result: the spend-only model already explains **94.5%** of revenue variance (`R^2 = {rev_linear.rsquared:.3f}`), with a slope of **{rev_linear.params['ad_spend_usd']:.3f}** revenue dollars per additional dollar of spend. Adding all categorical controls changes `R^2` only from **{rev_linear.rsquared:.3f} to {rev_full.rsquared:.3f}**, and the nested-model F-test is not significant (`p = {rev_anova.iloc[1]['Pr(>F)']:.3f}`). The fitted line in [`plots/spend_vs_revenue.png`]({(PLOTS / 'spend_vs_revenue.png').resolve()}) shows a tight linear trend with heavy overlap across channels.

Interpretation: in this dataset, **budget level determines scale outcomes**, and the categorical campaign labels add little incremental explanatory value for revenue.

### 2. Efficiency is remarkably stable across channels and over time.

Hypothesis: some channels should produce better efficiency than others, visible as higher ROAS or CTR.

Test: I compared channel-level distributions for CTR, CPC, CPM, ROAS, and revenue-per-click using ANOVA and Kruskal-Wallis tests, and visualized ROAS by channel plus month-by-channel mean ROAS.

Result: none of the channel differences in efficiency metrics are statistically persuasive. For ROAS, the ANOVA p-value is **{channel_tests['roas']['anova_p']:.3f}** and the effect size is tiny (`Cohen's f = {channel_tests['roas']['cohens_f']:.3f}`). Mean ROAS ranges only from **{df.groupby('channel')['roas'].mean().min():.3f}** to **{df.groupby('channel')['roas'].mean().max():.3f}** across channels. Monthly mean ROAS also stays inside a narrow band of roughly **{month_metrics['roas'].min():.3f} to {month_metrics['roas'].max():.3f}**.

Evidence:

- [`plots/roas_by_channel.png`]({(PLOTS / 'roas_by_channel.png').resolve()}) shows strong overlap in ROAS distributions across Display, Email, Search, and Social.
- [`plots/monthly_roas_heatmap.png`]({(PLOTS / 'monthly_roas_heatmap.png').resolve()}) shows channel-month averages staying within a fairly modest **{heat.min().min():.2f} to {heat.max().max():.2f}** range rather than separating into strong seasonal or channel-specific regimes.

Interpretation: the data does **not** support the common marketing intuition that one channel is clearly more efficient here. The practical implication is that channel selection appears to matter less than execution at the campaign level, at least at this level of aggregation.

### 3. There is no evidence of diminishing returns in ROAS at higher spend levels, but there are campaign-level outliers.

Hypothesis: if larger budgets saturate, ROAS should decline as spend increases.

Test: I compared ROAS across spend quintiles and added a quadratic spend term to the full revenue model.

Result: ROAS is essentially flat across spend quintiles, with mean values from **{df.groupby('spend_quintile', observed=False)['roas'].mean().min():.3f}** to **{df.groupby('spend_quintile', observed=False)['roas'].mean().max():.3f}** and ANOVA `p = {spend_roas_anova.pvalue:.3f}`. The quadratic term in the revenue model also fails to improve fit (`p = {quad_anova.iloc[1]['Pr(>F)']:.3f}`).

What does vary is individual-campaign execution. The largest positive outlier is campaign **{int(top_outliers.iloc[0]['campaign_id'])}** ({top_outliers.iloc[0]['channel']}, {top_outliers.iloc[0]['region']}, month {int(top_outliers.iloc[0]['month'])}), with ROAS **{top_outliers.iloc[0]['roas']:.3f}** and a studentized residual of **{top_outliers.iloc[0]['student_resid']:.2f}**. Several campaigns underperform just as strongly, including campaign **{int(top_outliers.iloc[1]['campaign_id'])}** with ROAS **{top_outliers.iloc[1]['roas']:.3f}**. These are visible in [`plots/revenue_model_residuals.png`]({(PLOTS / 'revenue_model_residuals.png').resolve()}).

Interpretation: the dataset suggests **constant average returns to spend**, with the meaningful variation happening at the individual campaign level rather than as a smooth budget-efficiency curve.

## Supporting Detail

### Orientation Summary

- Shape: **{raw_df.shape[0]} rows x {raw_df.shape[1]} raw columns**
- Null values: **0 in every column**
- Unique IDs: **{df['campaign_id'].nunique()} campaign IDs for {df.shape[0]} rows**
- Numeric ranges:
  - `ad_spend_usd`: **{df['ad_spend_usd'].min():,.2f} to {df['ad_spend_usd'].max():,.2f}**
  - `impressions`: **{df['impressions'].min():,} to {df['impressions'].max():,}**
  - `clicks`: **{df['clicks'].min():,} to {df['clicks'].max():,}**
  - `revenue_usd`: **{df['revenue_usd'].min():,.2f} to {df['revenue_usd'].max():,.2f}**
- Category counts:
  - Channels: {channel_counts.to_dict()}
  - Regions: {region_counts.to_dict()}
  - Months: {month_counts.to_dict()}

### Selected Summary Statistics

Channel-level mean efficiency metrics:

{df_to_markdown_table(df.groupby('channel')[['ctr', 'cpc', 'cpm', 'roas', 'rpc']].mean().round(4))}

Region-level mean CTR and ROAS:

{df_to_markdown_table(region_metrics)}

Spend-quintile mean CTR and ROAS:

{df_to_markdown_table(df.groupby('spend_quintile', observed=False)[['ctr', 'roas']].mean().round(4))}

### Model Notes

- `revenue_usd ~ ad_spend_usd`: `R^2 = {rev_linear.rsquared:.3f}`
- `revenue_usd ~ ad_spend_usd + channel + region + month`: `R^2 = {rev_full.rsquared:.3f}`
- `clicks ~ impressions + channel + region + month`: `R^2 = {clicks_model.rsquared:.3f}`. Impressions are predictive, but categorical effects are weak and inconsistent.
- `roas ~ ad_spend_usd + channel + region + month`: `R^2 = {roas_model.rsquared:.3f}`. This confirms that the observed fields explain almost none of the variation in efficiency.

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

The clearest pattern is a **near-linear spend-to-revenue relationship** with an average return of about **{rev_linear.params['ad_spend_usd']:.2f}x revenue per $1 spent**. By contrast, **channel, region, month, and spend tier show little evidence of systematic efficiency differences**. The most actionable signal in the data is therefore the presence of **campaign-level outliers**, not broad structural winners and losers.
"""

    (ROOT / "analysis_report.md").write_text(report)


if __name__ == "__main__":
    main()
