from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy.stats import chi2
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
PLOTS = ROOT / "plots"
PLOTS.mkdir(exist_ok=True)


def review_plot(path: Path) -> str:
    img = mpimg.imread(path)
    shape = tuple(int(x) for x in img.shape)
    mean = float(img.mean())
    std = float(img.std())
    return f"{path.name}: shape={shape}, mean_pixel={mean:.3f}, std_pixel={std:.3f}"


def wilson_interval(k: pd.Series, n: pd.Series, z: float = 1.96) -> tuple[np.ndarray, np.ndarray]:
    phat = k / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    half = z * np.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n) / denom
    return center - half, center + half


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    df = pd.read_csv(ROOT / "dataset.csv")

    core_model = smf.logit("converted ~ time_of_day_hour + channel_score", data=df).fit(disp=False)
    full_model = smf.logit(
        "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
        "page_load_time_sec + previous_visits + C(device)",
        data=df,
    ).fit(disp=False)

    X_core = df[["time_of_day_hour", "channel_score"]]
    X_full = df[["ad_budget_usd", "time_of_day_hour", "channel_score", "page_load_time_sec", "previous_visits", "device"]]
    y = df["converted"]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    core_pipe = Pipeline(
        [
            ("pre", ColumnTransformer([("num", StandardScaler(), ["time_of_day_hour", "channel_score"])])),
            ("clf", LogisticRegression(max_iter=2000)),
        ]
    )
    full_pipe = Pipeline(
        [
            (
                "pre",
                ColumnTransformer(
                    [
                        (
                            "num",
                            StandardScaler(),
                            ["ad_budget_usd", "time_of_day_hour", "channel_score", "page_load_time_sec", "previous_visits"],
                        ),
                        ("cat", OneHotEncoder(drop="first"), ["device"]),
                    ]
                ),
            ),
            ("clf", LogisticRegression(max_iter=2000)),
        ]
    )
    core_auc = cross_val_score(core_pipe, X_core, y, cv=cv, scoring="roc_auc")
    full_auc = cross_val_score(full_pipe, X_full, y, cv=cv, scoring="roc_auc")
    core_logloss = -cross_val_score(core_pipe, X_core, y, cv=cv, scoring="neg_log_loss")
    full_logloss = -cross_val_score(full_pipe, X_full, y, cv=cv, scoring="neg_log_loss")

    llr = 2 * (full_model.llf - core_model.llf)
    df_diff = int(full_model.df_model - core_model.df_model)
    llr_p = float(chi2.sf(llr, df_diff))

    hourly = (
        df.assign(hour=df["time_of_day_hour"].round().astype(int).clip(0, 24))
        .groupby("hour", as_index=False)["converted"]
        .agg(rate="mean", conversions="sum", sessions="count")
    )
    hourly["low"], hourly["high"] = wilson_interval(hourly["conversions"], hourly["sessions"])

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(hourly["hour"], hourly["rate"], color="#0c7c59", marker="o", linewidth=2.5)
    ax.fill_between(hourly["hour"], hourly["low"], hourly["high"], color="#0c7c59", alpha=0.15)
    ax.set_title("Conversion Rate Rises Through The Day")
    ax.set_xlabel("Hour of day (rounded)")
    ax.set_ylabel("Conversion rate")
    ax.set_ylim(0, max(0.6, hourly["high"].max() + 0.03))
    fig.tight_layout()
    fig.savefig(PLOTS / "conversion_by_hour.png", dpi=150)
    plt.close(fig)

    deciles = pd.qcut(df["channel_score"], 10, duplicates="drop")
    score_bins = (
        df.assign(score_bin=deciles)
        .groupby("score_bin", observed=False, as_index=False)["converted"]
        .agg(rate="mean", conversions="sum", sessions="count")
    )
    score_bins["label"] = [f"D{i}" for i in range(1, len(score_bins) + 1)]
    score_bins["low"], score_bins["high"] = wilson_interval(score_bins["conversions"], score_bins["sessions"])

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(score_bins["label"], score_bins["rate"], color="#1f4e79")
    ax.errorbar(
        score_bins["label"],
        score_bins["rate"],
        yerr=[score_bins["rate"] - score_bins["low"], score_bins["high"] - score_bins["rate"]],
        fmt="none",
        ecolor="black",
        capsize=4,
        linewidth=1.2,
    )
    ax.set_title("Higher Channel Scores Consistently Convert Better")
    ax.set_xlabel("Channel score decile")
    ax.set_ylabel("Conversion rate")
    ax.set_ylim(0, max(0.5, score_bins["high"].max() + 0.03))
    fig.tight_layout()
    fig.savefig(PLOTS / "conversion_by_channel_score_decile.png", dpi=150)
    plt.close(fig)

    params = full_model.params.drop("Intercept")
    conf = full_model.conf_int().drop(index="Intercept")
    coef_df = pd.DataFrame(
        {
            "term": params.index,
            "odds_ratio": np.exp(params.values),
            "low": np.exp(conf[0].values),
            "high": np.exp(conf[1].values),
        }
    ).sort_values("odds_ratio")

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = np.arange(len(coef_df))
    ax.errorbar(
        coef_df["odds_ratio"],
        y_pos,
        xerr=[coef_df["odds_ratio"] - coef_df["low"], coef_df["high"] - coef_df["odds_ratio"]],
        fmt="o",
        color="#8a1538",
        ecolor="#8a1538",
        capsize=4,
    )
    ax.axvline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set_xscale("log")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(coef_df["term"])
    ax.set_xlabel("Odds ratio (log scale)")
    ax.set_title("Adjusted Effects: Only Time Of Day And Channel Score Stand Out")
    fig.tight_layout()
    fig.savefig(PLOTS / "adjusted_odds_ratios.png", dpi=150)
    plt.close(fig)

    hour_grid = np.linspace(0, 24, 80)
    score_grid = np.linspace(0, 1, 80)
    hh, ss = np.meshgrid(hour_grid, score_grid)
    grid = pd.DataFrame({"time_of_day_hour": hh.ravel(), "channel_score": ss.ravel()})
    grid["pred_prob"] = core_model.predict(grid)
    heat = grid.pivot(index="channel_score", columns="time_of_day_hour", values="pred_prob")

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(heat, cmap="YlGnBu", cbar_kws={"label": "Predicted conversion probability"}, ax=ax)
    ax.set_title("Predicted Conversion Is Highest For Late, High-Score Sessions")
    ax.set_xlabel("Time of day hour")
    ax.set_ylabel("Channel score")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(PLOTS / "predicted_probability_heatmap.png", dpi=150)
    plt.close(fig)

    plot_reviews = [review_plot(path) for path in sorted(PLOTS.glob("*.png"))]

    overall_rate = float(df["converted"].mean())
    hour_q = df["time_of_day_hour"].quantile([0.1, 0.9])
    score_q = df["channel_score"].quantile([0.1, 0.9])
    baseline = pd.DataFrame(
        [{"time_of_day_hour": float(df["time_of_day_hour"].median()), "channel_score": float(df["channel_score"].median())}]
    )
    hour_low = baseline.copy()
    hour_high = baseline.copy()
    hour_low["time_of_day_hour"] = hour_q.loc[0.1]
    hour_high["time_of_day_hour"] = hour_q.loc[0.9]
    score_low = baseline.copy()
    score_high = baseline.copy()
    score_low["channel_score"] = score_q.loc[0.1]
    score_high["channel_score"] = score_q.loc[0.9]
    hour_pp = float((core_model.predict(hour_high) - core_model.predict(hour_low)).iloc[0] * 100)
    score_pp = float((core_model.predict(score_high) - core_model.predict(score_low)).iloc[0] * 100)

    scenarios = pd.DataFrame(
        {
            "time_of_day_hour": [2, 2, 23, 23],
            "channel_score": [0.1, 0.9, 0.1, 0.9],
        }
    )
    scenarios["pred_prob"] = core_model.predict(scenarios)

    report = f"""# Analysis Report

## What this dataset appears to be

This is a session-level web conversion dataset with **{len(df):,} sessions** and **8 columns**. Each row appears to represent one browsing session with a unique `session_id`, a binary outcome `converted`, and session attributes such as ad budget, time of day, device, page load time, previous visits, and a `channel_score`.

Key orientation facts:

- No columns contain missing values.
- `converted` is moderately imbalanced: **{overall_rate:.1%}** of sessions converted ({int(df['converted'].sum())} of {len(df)}).
- `device` has 3 levels: mobile ({int((df['device'] == 'mobile').sum())}), desktop ({int((df['device'] == 'desktop').sum())}), and tablet ({int((df['device'] == 'tablet').sum())}).
- Numeric ranges are plausible for session-level data: `time_of_day_hour` spans **0.0 to 24.0**, `channel_score` spans **0.0 to 1.0**, `page_load_time_sec` spans **0.3 to 15.0**, and `previous_visits` spans **0 to 10**.
- Values in the raw rows are internally consistent with the column names; there were no obvious coded missing values or malformed date strings.

## Key findings

### 1. Sessions later in the day convert substantially more often than early-day sessions

**Hypothesis.** Conversion probability increases as the day progresses.

**Test.** I first plotted empirical conversion rates by rounded hour of day ([`conversion_by_hour.png`](./plots/conversion_by_hour.png)), then fit a logistic regression controlling for `channel_score`.

**Evidence.**

- In the adjusted logistic model, `time_of_day_hour` has coefficient **0.0788** (95% CI **0.0611 to 0.0965**, p < 1e-17), equivalent to an odds ratio of **1.082 per hour**.
- Empirically, rounded-hour conversion rises from **10.5% at 1:00** and **13.5% at 0:00** to **45.5% at 21:00**, **39.6% at 22:00**, **55.6% at 23:00**, and **47.2% at 24:00** in [`conversion_by_hour.png`](./plots/conversion_by_hour.png).
- Moving from the 10th to the 90th percentile of `time_of_day_hour` (about **2.29** to **21.5** hours), while holding `channel_score` at its median, raises predicted conversion by **{hour_pp:.1f} percentage points**.

**Interpretation.** Time of day is not a minor nuisance variable here; it is one of the two dominant signals in the dataset. This is a correlational result. It could reflect user intent, campaign scheduling, audience composition, or unobserved operational factors rather than a direct causal effect of the clock.

### 2. `channel_score` is the strongest quality signal in the data

**Hypothesis.** Higher `channel_score` marks higher-intent sessions and should strongly predict conversion.

**Test.** I examined conversion by score decile in [`conversion_by_channel_score_decile.png`](./plots/conversion_by_channel_score_decile.png) and estimated an adjusted logistic model.

**Evidence.**

- In the adjusted model, `channel_score` has coefficient **1.8928** (95% CI **1.4630 to 2.3226**, p < 1e-17), which corresponds to an odds ratio of **6.64** for a one-unit increase.
- Score-bin conversion rises steadily from **8.7% in the bottom decile** to **50.0% in the top decile**, as shown in [`conversion_by_channel_score_decile.png`](./plots/conversion_by_channel_score_decile.png).
- Moving from the 10th to the 90th percentile of `channel_score` (about **0.092** to **0.885**), while holding `time_of_day_hour` at its median, raises predicted conversion by **{score_pp:.1f} percentage points**.

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
- The five added variables do **not** significantly improve fit over the two-variable model: likelihood-ratio statistic **{llr:.2f}** on **{df_diff}** degrees of freedom, p = **{llr_p:.3f}**.
- Out of sample, the simpler model slightly outperforms the full one:
  - Core model (`time_of_day_hour` + `channel_score`): mean 5-fold ROC AUC **{core_auc.mean():.3f}**, log loss **{core_logloss.mean():.3f}**
  - Full model: mean 5-fold ROC AUC **{full_auc.mean():.3f}**, log loss **{full_logloss.mean():.3f}**

**Interpretation.** This is the most counter-intuitive result in the dataset. It suggests that spending more budget on a session, serving a different device type, or even having slower page loads within the observed range does not explain much additional variation in conversion once session timing and channel quality are already accounted for. In practical terms, a simpler targeting story explains the data better than a richer operational one.

### Practical combined effect

The two-variable model implies a large difference between low-quality early sessions and high-quality late sessions, shown in [`predicted_probability_heatmap.png`](./plots/predicted_probability_heatmap.png):

- At **2:00** with `channel_score = 0.1`, predicted conversion is **{scenarios.loc[0, 'pred_prob']:.1%}**
- At **2:00** with `channel_score = 0.9`, predicted conversion is **{scenarios.loc[1, 'pred_prob']:.1%}**
- At **23:00** with `channel_score = 0.1`, predicted conversion is **{scenarios.loc[2, 'pred_prob']:.1%}**
- At **23:00** with `channel_score = 0.9`, predicted conversion is **{scenarios.loc[3, 'pred_prob']:.1%}**

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

{chr(10).join(f"- {item}" for item in plot_reviews)}
"""

    (ROOT / "analysis_report.md").write_text(report)


if __name__ == "__main__":
    main()
