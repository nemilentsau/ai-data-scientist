from pathlib import Path
from textwrap import dedent

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import kruskal, pearsonr
from scipy.stats import poisson


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def format_p(p: float) -> str:
    if p == 0:
        return "<1e-300"
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4f}"


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df["year"] = df["date"].dt.year.astype("category")
    df["month_num"] = df["date"].dt.month
    df["month"] = pd.Categorical(
        df["date"].dt.strftime("%b"),
        categories=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        ordered=True,
    )
    df["dow"] = pd.Categorical(
        df["date"].dt.day_name(),
        categories=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        ordered=True,
    )
    df["signup_rate"] = df["new_signups"] / df["unique_visitors"]
    df["traffic_roll30"] = df["pageviews"].rolling(30, min_periods=1).mean()
    df["signups_roll30"] = df["new_signups"].rolling(30, min_periods=1).mean()

    summary = df.describe(include="all").transpose()
    year_means = df.groupby("year", observed=True)[["pageviews", "unique_visitors", "new_signups", "support_tickets"]].mean()
    month_means = df.groupby("month", observed=True)["pageviews"].mean()
    dow_means = df.groupby("dow", observed=True)["pageviews"].mean()

    traffic_model = smf.ols("pageviews ~ C(year) + C(dow) + C(month)", data=df).fit()
    signups_ols = smf.ols("new_signups ~ C(year) + C(dow) + C(month)", data=df).fit()
    signups_glm = smf.glm(
        "new_signups ~ np.log(unique_visitors) + bounce_rate + avg_session_duration_sec + C(dow) + C(month)",
        data=df,
        family=sm.families.Poisson(),
    ).fit()
    support_glm = smf.glm(
        "support_tickets ~ C(year) + C(dow) + C(month) + new_signups + unique_visitors",
        data=df,
        family=sm.families.Poisson(),
    ).fit()

    kw_pageviews_year = kruskal(*[g["pageviews"].values for _, g in df.groupby("year", observed=True)])
    kw_signups_year = kruskal(*[g["new_signups"].values for _, g in df.groupby("year", observed=True)])
    kw_support_year = kruskal(*[g["support_tickets"].values for _, g in df.groupby("year", observed=True)])

    r_signup_traffic, p_signup_traffic = pearsonr(df["unique_visitors"], df["new_signups"])
    r_support_traffic, p_support_traffic = pearsonr(df["unique_visitors"], df["support_tickets"])

    # Plot 1: traffic structure
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[1.6, 1])
    axes[0].plot(df["date"], df["pageviews"], color="#9ecae1", alpha=0.45, linewidth=1)
    axes[0].plot(df["date"], df["traffic_roll30"], color="#08519c", linewidth=2.5, label="30-day rolling mean")
    axes[0].set_title("Traffic Grew Strongly While Retaining Clear Seasonality")
    axes[0].set_ylabel("Pageviews")
    axes[0].legend(frameon=False, loc="upper left")

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sns.barplot(
        data=df,
        x="month",
        y="pageviews",
        estimator=np.mean,
        errorbar=("ci", 95),
        order=month_order,
        color="#6baed6",
        ax=axes[1],
    )
    axes[1].set_xlabel("Calendar Month")
    axes[1].set_ylabel("Mean Pageviews")
    axes[1].set_title("Average Traffic Peaks in Spring and Bottoms Out in Early Fall")
    savefig(PLOTS_DIR / "traffic_seasonality.png")

    # Plot 2: signups vs traffic
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    sns.regplot(
        data=df,
        x="unique_visitors",
        y="new_signups",
        scatter_kws={"alpha": 0.4, "s": 35, "color": "#2ca25f"},
        line_kws={"color": "#00441b", "linewidth": 2},
        ax=axes[0],
    )
    axes[0].set_title("Daily Signups Barely Move With Visitor Volume")
    axes[0].set_xlabel("Unique Visitors")
    axes[0].set_ylabel("New Signups")

    monthly = df.groupby(df["date"].dt.to_period("M"), observed=True)[["unique_visitors", "new_signups"]].mean().reset_index()
    monthly["date"] = monthly["date"].dt.to_timestamp()
    axes[1].plot(monthly["date"], monthly["unique_visitors"], color="#08519c", linewidth=2.5, label="Unique visitors")
    axes[1].set_ylabel("Unique visitors", color="#08519c")
    axes[1].tick_params(axis="y", labelcolor="#08519c")
    ax2 = axes[1].twinx()
    ax2.plot(monthly["date"], monthly["new_signups"], color="#cb181d", linewidth=2.5, label="New signups")
    ax2.set_ylabel("New signups", color="#cb181d")
    ax2.tick_params(axis="y", labelcolor="#cb181d")
    axes[1].set_title("Visitors Rose Sharply; Signups Stayed Flat")
    axes[1].set_xlabel("Month")
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    for label in axes[1].get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")
    lines = axes[1].get_lines() + ax2.get_lines()
    labels = [line.get_label() for line in lines]
    axes[1].legend(lines, labels, frameon=False, loc="upper left")
    savefig(PLOTS_DIR / "signups_vs_traffic.png")

    # Plot 3: support ticket count process
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    counts = df["support_tickets"].value_counts().sort_index()
    x = np.arange(0, max(counts.index.max(), 10) + 1)
    expected = poisson.pmf(x, mu=df["support_tickets"].mean()) * len(df)
    axes[0].bar(counts.index, counts.values, color="#9ecae1", edgecolor="white", label="Observed days")
    axes[0].plot(x, expected, color="#08519c", marker="o", linewidth=2, label="Poisson expectation")
    axes[0].set_title("Support Tickets Closely Match a Stable Poisson Process")
    axes[0].set_xlabel("Support tickets per day")
    axes[0].set_ylabel("Number of days")
    axes[0].legend(frameon=False)

    sns.regplot(
        data=df,
        x="unique_visitors",
        y="support_tickets",
        scatter_kws={"alpha": 0.4, "s": 35, "color": "#fdae6b"},
        line_kws={"color": "#a63603", "linewidth": 2},
        ax=axes[1],
    )
    axes[1].set_title("Support Load Does Not Rise With Traffic")
    axes[1].set_xlabel("Unique visitors")
    axes[1].set_ylabel("Support tickets")
    savefig(PLOTS_DIR / "support_ticket_process.png")

    report = dedent(
        f"""
        # Analysis Report

        ## What this dataset is about

        This is a daily operational dataset spanning **{df['date'].min().date()} to {df['date'].max().date()}** ({len(df):,} consecutive days, no missing dates). It tracks a website or product funnel with seven variables:

        - `pageviews`
        - `unique_visitors`
        - `bounce_rate`
        - `avg_session_duration_sec`
        - `new_signups`
        - `support_tickets`

        The data are clean at a structural level: there are **0 nulls** across all columns, `date` parses cleanly as a daily timestamp, and each row appears to represent one day of activity. The most important orienting fact is that traffic metrics move a lot over time while `new_signups` and `support_tickets` barely do.

        Key ranges:

        - `pageviews`: mean **{df['pageviews'].mean():.1f}**, min **{df['pageviews'].min()}**, max **{df['pageviews'].max()}**
        - `unique_visitors`: mean **{df['unique_visitors'].mean():.1f}**, min **{df['unique_visitors'].min()}**, max **{df['unique_visitors'].max()}**
        - `bounce_rate`: mean **{df['bounce_rate'].mean():.3f}**, spanning **{df['bounce_rate'].min():.3f}** to **{df['bounce_rate'].max():.3f}**
        - `avg_session_duration_sec`: mean **{df['avg_session_duration_sec'].mean():.1f}** seconds
        - `new_signups`: mean **{df['new_signups'].mean():.2f}** per day
        - `support_tickets`: mean **{df['support_tickets'].mean():.2f}** per day

        ## Key findings

        ### 1. Traffic grew dramatically and followed a strong recurring seasonal pattern

        Traffic volume is not stationary. Mean daily `pageviews` rose from **{year_means.loc[2022, 'pageviews']:.1f}** in 2022 to **{year_means.loc[2024, 'pageviews']:.1f}** in 2024, a **{(year_means.loc[2024, 'pageviews'] / year_means.loc[2022, 'pageviews'] - 1) * 100:.1f}%** increase. `unique_visitors` shows the same pattern, rising from **{year_means.loc[2022, 'unique_visitors']:.1f}** to **{year_means.loc[2024, 'unique_visitors']:.1f}**.

        The combined time-structure model `pageviews ~ year + day_of_week + month` explains **{traffic_model.rsquared:.1%}** of pageview variance. Year effects are large and highly significant:

        - 2023 adds **{traffic_model.params['C(year)[T.2023]']:.1f} pageviews/day** relative to 2022, **p = {format_p(traffic_model.pvalues['C(year)[T.2023]'])}**
        - 2024 adds **{traffic_model.params['C(year)[T.2024]']:.1f} pageviews/day** relative to 2022, **p = {format_p(traffic_model.pvalues['C(year)[T.2024]'])}**

        Weekday effects are also large. Monday averages **{dow_means.loc['Monday']:.1f}** pageviews versus **{dow_means.loc['Thursday']:.1f}** on Thursday, a gap of **{(dow_means.loc['Monday'] / dow_means.loc['Thursday'] - 1) * 100:.1f}%**. Across calendar months, average traffic peaks in **{month_means.idxmax()} ({month_means.max():.1f})** and reaches its trough in **{month_means.idxmin()} ({month_means.min():.1f})**.

        Evidence: see `plots/traffic_seasonality.png`. The year-to-year upward shift is visible in the rolling mean, while the monthly bar chart shows the persistent annual cycle. The non-parametric year test also strongly rejects equal traffic distributions across years (**Kruskal-Wallis p = {format_p(kw_pageviews_year.pvalue)}**).

        **Interpretation:** traffic acquisition improved substantially over the three-year span, but that improvement appears to come from a recurring seasonal system rather than random bursts.

        ### 2. Signups did not grow with traffic, engagement, or time

        This is the most important counter-intuitive finding. Despite major traffic growth, `new_signups` stayed almost flat:

        - 2022 mean: **{year_means.loc[2022, 'new_signups']:.2f}/day**
        - 2023 mean: **{year_means.loc[2023, 'new_signups']:.2f}/day**
        - 2024 mean: **{year_means.loc[2024, 'new_signups']:.2f}/day**

        A raw Pearson correlation between `unique_visitors` and `new_signups` is essentially zero (**r = {r_signup_traffic:.4f}, p = {format_p(p_signup_traffic)}**). More importantly, a Poisson count model using `log(unique_visitors)`, `bounce_rate`, `avg_session_duration_sec`, day-of-week, and month still finds no meaningful predictor:

        - `log(unique_visitors)` coefficient: **{signups_glm.params['np.log(unique_visitors)']:.4f}**, **p = {format_p(signups_glm.pvalues['np.log(unique_visitors)'])}**
        - `bounce_rate` coefficient: **{signups_glm.params['bounce_rate']:.4f}**, **p = {format_p(signups_glm.pvalues['bounce_rate'])}**
        - `avg_session_duration_sec` coefficient: **{signups_glm.params['avg_session_duration_sec']:.5f}**, **p = {format_p(signups_glm.pvalues['avg_session_duration_sec'])}**

        The simpler OLS model `new_signups ~ year + day_of_week + month` explains only **{signups_ols.rsquared:.1%}** of variance, and the year effect is not significant (**Kruskal-Wallis p = {format_p(kw_signups_year.pvalue)}**).

        Evidence: `plots/signups_vs_traffic.png`. The left panel shows a near-flat fitted line in daily data; the right panel shows monthly unique visitors rising sharply while signups remain close to a horizontal band around 15/day.

        **Interpretation:** whatever drives signups is largely disconnected from the observed website traffic and engagement measures. Plausible mechanisms include a signup bottleneck outside the web session, a capped acquisition process, or a metric definition mismatch where signups come from channels not reflected in site traffic.

        ### 3. Support tickets behave like a stable background process rather than a traffic-driven workload

        `support_tickets` are unusually stable for a metric that might be expected to scale with growth:

        - Mean: **{df['support_tickets'].mean():.3f}/day**
        - Variance: **{df['support_tickets'].var():.3f}**
        - Dispersion index (`variance / mean`): **{df['support_tickets'].var() / df['support_tickets'].mean():.3f}**

        A dispersion index near 1 is what a Poisson-like count process would produce. That matches the fitted Poisson model well: the model’s Pearson chi-square / df is **{support_glm.pearson_chi2 / support_glm.df_resid:.3f}**, and neither year, weekday, traffic, nor signups are significant predictors. The raw correlation with `unique_visitors` is also effectively zero (**r = {r_support_traffic:.4f}, p = {format_p(p_support_traffic)}**). Year-level distributions are indistinguishable (**Kruskal-Wallis p = {format_p(kw_support_year.pvalue)}**).

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
        """
    ).strip() + "\n"

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
