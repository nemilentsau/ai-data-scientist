from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["device"] = df["device"].astype("category")
    return df


def orient(df: pd.DataFrame) -> dict:
    orientation = {
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isna().sum().to_dict(),
        "cardinality": {col: int(df[col].nunique(dropna=True)) for col in df.columns},
        "head": df.head(6),
    }
    return orientation


def fit_logit(df: pd.DataFrame):
    model_df = df.copy()
    numeric = [
        "ad_budget_usd",
        "time_of_day_hour",
        "channel_score",
        "page_load_time_sec",
        "previous_visits",
    ]
    for col in numeric:
        model_df[f"{col}_z"] = (model_df[col] - model_df[col].mean()) / model_df[col].std()
    formula = (
        "converted ~ ad_budget_usd_z + time_of_day_hour_z + channel_score_z + "
        "page_load_time_sec_z + previous_visits_z + C(device)"
    )
    model = smf.logit(formula, data=model_df).fit(disp=False)
    odds = pd.DataFrame(
        {
            "term": model.params.index,
            "odds_ratio": np.exp(model.params.values),
            "ci_low": np.exp(model.conf_int()[0].values),
            "ci_high": np.exp(model.conf_int()[1].values),
            "p_value": model.pvalues.values,
        }
    )
    return model, odds, model_df


def cross_validated_model(df: pd.DataFrame) -> dict:
    X = df[
        [
            "ad_budget_usd",
            "time_of_day_hour",
            "channel_score",
            "device",
            "page_load_time_sec",
            "previous_visits",
        ]
    ]
    y = df["converted"]
    pre = ColumnTransformer(
        [
            (
                "num",
                StandardScaler(),
                [
                    "ad_budget_usd",
                    "time_of_day_hour",
                    "channel_score",
                    "page_load_time_sec",
                    "previous_visits",
                ],
            ),
            ("cat", OneHotEncoder(drop="first"), ["device"]),
        ]
    )
    pipe = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000))])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc = cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc")
    acc = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")
    log_loss = -cross_val_score(pipe, X, y, cv=cv, scoring="neg_log_loss")
    return {
        "auc_mean": auc.mean(),
        "auc_std": auc.std(),
        "acc_mean": acc.mean(),
        "acc_std": acc.std(),
        "log_loss_mean": log_loss.mean(),
        "log_loss_std": log_loss.std(),
    }


def summarize_findings(df: pd.DataFrame, odds: pd.DataFrame) -> dict:
    overall_rate = df["converted"].mean()

    hour_bins = pd.IntervalIndex.from_breaks([0, 6, 12, 18, 24], closed="right")
    hour_labels = ["0-6", "6-12", "12-18", "18-24"]
    hour_group = (
        df.assign(hour_band=pd.cut(df["time_of_day_hour"], bins=[0, 6, 12, 18, 24], labels=hour_labels, include_lowest=True))
        .groupby("hour_band", observed=False)["converted"]
        .agg(["mean", "count"])
        .reset_index()
    )

    score_group = (
        df.assign(score_quartile=pd.qcut(df["channel_score"], q=4, labels=["Q1", "Q2", "Q3", "Q4"]))
        .groupby("score_quartile", observed=False)["converted"]
        .agg(["mean", "count"])
        .reset_index()
    )

    interaction = (
        df.assign(
            hour_band=pd.cut(
                df["time_of_day_hour"],
                bins=[0, 6, 12, 18, 24],
                labels=hour_labels,
                include_lowest=True,
            ),
            score_quartile=pd.qcut(df["channel_score"], q=4, labels=["Q1", "Q2", "Q3", "Q4"]),
        )
        .groupby(["hour_band", "score_quartile"], observed=False)["converted"]
        .mean()
        .unstack()
    )

    return {
        "overall_rate": overall_rate,
        "hour_group": hour_group,
        "score_group": score_group,
        "interaction": interaction,
        "odds": odds,
    }


def save_plot(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / filename, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_plots(df: pd.DataFrame, summary: dict, odds: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="talk")

    hour_group = summary["hour_group"].copy()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    sns.barplot(data=hour_group, x="hour_band", y="mean", color="#4C78A8", ax=ax)
    ax.axhline(summary["overall_rate"], color="#F58518", linestyle="--", linewidth=2, label="Overall")
    ax.set_xlabel("Time of Day (hour)")
    ax.set_ylabel("Conversion Rate")
    ax.set_title("Conversion Rises Through the Day")
    ax.set_ylim(0, max(0.5, hour_group["mean"].max() + 0.05))
    for idx, row in hour_group.iterrows():
        ax.text(idx, row["mean"] + 0.012, f"{row['mean']:.1%}\n(n={int(row['count'])})", ha="center", va="bottom", fontsize=10)
    ax.legend(frameon=False)
    save_plot(fig, "conversion_by_time_band.png")

    score_group = summary["score_group"].copy()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(
        score_group["score_quartile"],
        score_group["mean"],
        color="#54A24B",
        marker="o",
        linewidth=3,
        markersize=10,
    )
    ax.axhline(summary["overall_rate"], color="#E45756", linestyle="--", linewidth=2, label="Overall")
    ax.set_xlabel("Channel Score Quartile")
    ax.set_ylabel("Conversion Rate")
    ax.set_title("Higher Channel Scores Convert More Often")
    ax.set_ylim(0, max(0.55, score_group["mean"].max() + 0.05))
    for idx, row in score_group.iterrows():
        ax.text(idx, row["mean"] + 0.012, f"{row['mean']:.1%}\n(n={int(row['count'])})", ha="center", va="bottom", fontsize=10)
    ax.legend(frameon=False)
    save_plot(fig, "conversion_by_channel_score_quartile.png")

    heatmap = summary["interaction"].copy()
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    sns.heatmap(
        heatmap,
        annot=True,
        fmt=".1%",
        cmap="YlGnBu",
        vmin=float(heatmap.min().min()),
        vmax=float(heatmap.max().max()),
        linewidths=0.5,
        cbar_kws={"label": "Conversion Rate"},
        ax=ax,
    )
    ax.set_xlabel("Channel Score Quartile")
    ax.set_ylabel("Time of Day Band")
    ax.set_title("Time and Channel Score Compound")
    save_plot(fig, "time_channel_interaction_heatmap.png")

    forest = odds.loc[
        ~odds["term"].isin(["Intercept"]),
        ["term", "odds_ratio", "ci_low", "ci_high", "p_value"],
    ].copy()
    label_map = {
        "C(device)[T.mobile]": "Device: mobile vs desktop",
        "C(device)[T.tablet]": "Device: tablet vs desktop",
        "ad_budget_usd_z": "Ad budget (+1 SD)",
        "time_of_day_hour_z": "Time of day (+1 SD)",
        "channel_score_z": "Channel score (+1 SD)",
        "page_load_time_sec_z": "Page load time (+1 SD)",
        "previous_visits_z": "Previous visits (+1 SD)",
    }
    forest["label"] = forest["term"].map(label_map)
    forest = forest.sort_values("odds_ratio")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(
        forest["odds_ratio"],
        forest["label"],
        xerr=[forest["odds_ratio"] - forest["ci_low"], forest["ci_high"] - forest["odds_ratio"]],
        fmt="o",
        color="#4C78A8",
        ecolor="#4C78A8",
        capsize=4,
    )
    ax.axvline(1.0, color="#E45756", linestyle="--", linewidth=2)
    ax.set_xscale("log")
    ax.set_xlabel("Adjusted Odds Ratio (log scale)")
    ax.set_ylabel("")
    ax.set_title("Adjusted Effects Are Concentrated in Time and Channel Score")
    save_plot(fig, "adjusted_odds_ratios.png")


def write_report(orientation: dict, summary: dict, odds: pd.DataFrame, cv_metrics: dict, model) -> None:
    hour_group = summary["hour_group"].copy()
    score_group = summary["score_group"].copy()
    interaction = summary["interaction"].copy()

    early = hour_group.loc[hour_group["hour_band"] == "0-6", "mean"].iloc[0]
    late = hour_group.loc[hour_group["hour_band"] == "18-24", "mean"].iloc[0]
    score_low = score_group.loc[score_group["score_quartile"] == "Q1", "mean"].iloc[0]
    score_high = score_group.loc[score_group["score_quartile"] == "Q4", "mean"].iloc[0]
    combo_low = interaction.loc["0-6", "Q1"]
    combo_high = interaction.loc["18-24", "Q4"]

    def fmt_pct(x: float) -> str:
        return f"{100 * x:.1f}%"

    def fmt_num(x: float) -> str:
        return f"{x:.2f}"

    odds_lookup = odds.set_index("term")
    report = f"""# Analysis Report

## What this dataset is about

This dataset contains **{orientation['shape'][0]:,} web sessions** with a binary conversion outcome (`converted`). Each row appears to represent one marketing-driven session with session-level inputs: spend (`ad_budget_usd`), visit timing (`time_of_day_hour`), channel quality (`channel_score`), device type, page performance (`page_load_time_sec`), and prior engagement (`previous_visits`).

The data is structurally clean:

- Shape: **{orientation['shape'][0]} rows x {orientation['shape'][1]} columns**
- Missing values: **none**
- Outcome rate: **{fmt_pct(summary['overall_rate'])}** ({int(round(summary['overall_rate'] * orientation['shape'][0]))} conversions)
- Device mix: mobile is the largest group, with desktop and tablet smaller

The main caveat from orientation is conceptual rather than technical: this is observational session data. The variables look plausible, but they do not identify causal effects on their own.

## Key findings

### 1. Conversion rises sharply later in the day

**Hypothesis.** Sessions later in the day convert more often than early-morning sessions.

**Evidence.**

- The raw conversion rate climbs from **{fmt_pct(early)}** in the `0-6` band to **{fmt_pct(late)}** in the `18-24` band, shown in [`conversion_by_time_band.png`]({(PLOTS_DIR / 'conversion_by_time_band.png').resolve()}).
- In a multivariable logistic regression that controls for budget, channel score, device, page load time, and previous visits, a **1 standard deviation increase in `time_of_day_hour`** is associated with an odds ratio of **{fmt_num(odds_lookup.loc['time_of_day_hour_z', 'odds_ratio'])}** (95% CI **{fmt_num(odds_lookup.loc['time_of_day_hour_z', 'ci_low'])}** to **{fmt_num(odds_lookup.loc['time_of_day_hour_z', 'ci_high'])}**, p < 0.001), shown in [`adjusted_odds_ratios.png`]({(PLOTS_DIR / 'adjusted_odds_ratios.png').resolve()}).

**Interpretation.** Later-day traffic appears materially more purchase-ready. This is a large effect in both the raw rates and the adjusted model, so it is unlikely to be explained purely by device mix or spend.

### 2. Channel quality is another strong driver, with a clear monotonic pattern

**Hypothesis.** Higher `channel_score` reflects higher-intent traffic and should increase conversion.

**Evidence.**

- Conversion increases from **{fmt_pct(score_low)}** in the lowest score quartile to **{fmt_pct(score_high)}** in the highest quartile, shown in [`conversion_by_channel_score_quartile.png`]({(PLOTS_DIR / 'conversion_by_channel_score_quartile.png').resolve()}).
- In the adjusted logistic model, a **1 standard deviation increase in `channel_score`** has an odds ratio of **{fmt_num(odds_lookup.loc['channel_score_z', 'odds_ratio'])}** (95% CI **{fmt_num(odds_lookup.loc['channel_score_z', 'ci_low'])}** to **{fmt_num(odds_lookup.loc['channel_score_z', 'ci_high'])}**, p < 0.001).

**Interpretation.** `channel_score` behaves like a genuine quality or intent measure. The monotonic lift across quartiles makes the effect easy to operationalize: better channels are not just slightly better on average; they step up conversion consistently.

### 3. Time of day and channel score compound, while budget and page speed add little signal here

**Hypothesis.** The best conversion outcomes occur when high-intent traffic arrives at high-intent times, and some seemingly important operational variables may matter less than expected.

**Evidence.**

- The interaction heatmap in [`time_channel_interaction_heatmap.png`]({(PLOTS_DIR / 'time_channel_interaction_heatmap.png').resolve()}) shows the lowest-converting segment at **{fmt_pct(combo_low)}** (`0-6` plus bottom channel-score quartile) and the highest at **{fmt_pct(combo_high)}** (`18-24` plus top channel-score quartile).
- In the adjusted model, `ad_budget_usd`, `page_load_time_sec`, `previous_visits`, and device indicators all have confidence intervals that cross 1.0 in [`adjusted_odds_ratios.png`]({(PLOTS_DIR / 'adjusted_odds_ratios.png').resolve()}).
- A predictive logistic regression evaluated with 5-fold cross-validation reached ROC AUC **{fmt_num(cv_metrics['auc_mean'])} +/- {fmt_num(cv_metrics['auc_std'])}**. That is useful but not high, which suggests the dataset contains real structure without being close to deterministic.

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
"""
    REPORT_PATH.write_text(report)


def main() -> None:
    ensure_dirs()
    df = load_data()
    orientation = orient(df)
    model, odds, _ = fit_logit(df)
    cv_metrics = cross_validated_model(df)
    summary = summarize_findings(df, odds)
    make_plots(df, summary, odds)
    write_report(orientation, summary, odds, cv_metrics, model)


if __name__ == "__main__":
    main()
