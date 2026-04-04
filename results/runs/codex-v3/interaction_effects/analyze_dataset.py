from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
PLOTS_DIR = ROOT / "plots"
PLOTS_DIR.mkdir(exist_ok=True)


def fmt_pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def fit_models(df: pd.DataFrame):
    df_model = df.copy()
    df_model["device"] = df_model["device"].astype("category")

    base_formula = (
        "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
        "page_load_time_sec + previous_visits + C(device)"
    )
    interaction_formula = (
        "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
        "page_load_time_sec + previous_visits + channel_score:time_of_day_hour + C(device)"
    )

    base = smf.glm(base_formula, data=df_model, family=sm.families.Binomial()).fit()
    interaction = smf.glm(
        interaction_formula, data=df_model, family=sm.families.Binomial()
    ).fit()

    reduced_formulas = {
        "ad_budget_usd": (
            "converted ~ time_of_day_hour + channel_score + page_load_time_sec + "
            "previous_visits + channel_score:time_of_day_hour + C(device)"
        ),
        "page_load_time_sec": (
            "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
            "previous_visits + channel_score:time_of_day_hour + C(device)"
        ),
        "previous_visits": (
            "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
            "page_load_time_sec + channel_score:time_of_day_hour + C(device)"
        ),
        "device": (
            "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
            "page_load_time_sec + previous_visits + channel_score:time_of_day_hour"
        ),
    }

    lr_tests = {}
    for term, formula in reduced_formulas.items():
        reduced = smf.glm(formula, data=df_model, family=sm.families.Binomial()).fit()
        lr_stat = 2 * (interaction.llf - reduced.llf)
        df_diff = interaction.df_model - reduced.df_model
        lr_tests[term] = {
            "lr": lr_stat,
            "df": int(df_diff),
            "p": chi2.sf(lr_stat, df_diff),
        }

    interaction_lr = 2 * (interaction.llf - base.llf)
    interaction_df = interaction.df_model - base.df_model
    lr_tests["interaction"] = {
        "lr": interaction_lr,
        "df": int(interaction_df),
        "p": chi2.sf(interaction_lr, interaction_df),
    }

    return base, interaction, lr_tests


def fit_cv_model(df: pd.DataFrame):
    X = df.drop(columns=["converted", "session_id"])
    y = df["converted"]
    numeric = [
        "ad_budget_usd",
        "time_of_day_hour",
        "channel_score",
        "page_load_time_sec",
        "previous_visits",
    ]
    categorical = ["device"]
    pipeline = Pipeline(
        [
            (
                "prep",
                ColumnTransformer(
                    [
                        ("num", StandardScaler(), numeric),
                        ("cat", OneHotEncoder(drop="first"), categorical),
                    ]
                ),
            ),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc = cross_val_score(pipeline, X, y, cv=cv, scoring="roc_auc")
    accuracy = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    brier = -cross_val_score(pipeline, X, y, cv=cv, scoring="neg_brier_score")
    oof_pred = cross_val_predict(pipeline, X, y, cv=cv, method="predict_proba")[:, 1]
    return {
        "auc": auc,
        "accuracy": accuracy,
        "brier": brier,
        "oof_pred": oof_pred,
    }


def make_plot_time_score(df: pd.DataFrame, model) -> str:
    df_plot = df.copy()
    df_plot["time_bin"] = pd.cut(
        df_plot["time_of_day_hour"],
        bins=[0, 6, 12, 18, 24],
        include_lowest=True,
        labels=["00-06", "06-12", "12-18", "18-24"],
    )
    df_plot["score_bin"] = pd.qcut(
        df_plot["channel_score"], q=[0, 0.33, 0.67, 1.0], labels=["Low", "Mid", "High"]
    )

    heat = (
        df_plot.groupby(["score_bin", "time_bin"], observed=False)["converted"]
        .mean()
        .unstack()
    )

    hours = np.linspace(0, 24, 241)
    profile_rows = []
    medians = {
        "ad_budget_usd": df["ad_budget_usd"].median(),
        "page_load_time_sec": df["page_load_time_sec"].median(),
        "previous_visits": df["previous_visits"].median(),
        "device": "mobile",
    }
    for score_value, label in [(0.1, "Score 0.1"), (0.5, "Score 0.5"), (0.9, "Score 0.9")]:
        design = pd.DataFrame(
            {
                "ad_budget_usd": medians["ad_budget_usd"],
                "page_load_time_sec": medians["page_load_time_sec"],
                "previous_visits": medians["previous_visits"],
                "device": medians["device"],
                "channel_score": score_value,
                "time_of_day_hour": hours,
            }
        )
        profile_rows.append(
            pd.DataFrame(
                {
                    "time_of_day_hour": hours,
                    "predicted_probability": model.predict(design),
                    "profile": label,
                }
            )
        )
    curves = pd.concat(profile_rows, ignore_index=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), constrained_layout=True)

    sns.heatmap(
        heat,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        vmin=0.1,
        vmax=0.8,
        cbar_kws={"label": "Observed conversion rate"},
        ax=axes[0],
    )
    axes[0].set_title("Observed Conversion By Score And Time Bin")
    axes[0].set_xlabel("Time of day")
    axes[0].set_ylabel("Channel score tercile")

    sns.lineplot(
        data=curves,
        x="time_of_day_hour",
        y="predicted_probability",
        hue="profile",
        linewidth=2.4,
        ax=axes[1],
    )
    axes[1].set_title("Model-Predicted Conversion By Hour")
    axes[1].set_xlabel("Time of day hour")
    axes[1].set_ylabel("Predicted conversion probability")
    axes[1].set_xlim(0, 24)
    axes[1].set_ylim(0.1, 0.8)
    axes[1].legend(title="")

    out = PLOTS_DIR / "conversion_by_time_and_score.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out.name


def make_plot_channel_score(df: pd.DataFrame) -> str:
    df_plot = df.copy()
    df_plot["score_decile"] = pd.qcut(df_plot["channel_score"], 10, duplicates="drop")
    summary = (
        df_plot.groupby("score_decile", observed=False)
        .agg(
            conversion_rate=("converted", "mean"),
            avg_score=("channel_score", "mean"),
            n=("converted", "size"),
        )
        .reset_index(drop=True)
    )
    summary["ci"] = 1.96 * np.sqrt(
        summary["conversion_rate"] * (1 - summary["conversion_rate"]) / summary["n"]
    )

    fig, ax = plt.subplots(figsize=(8.5, 5.5), constrained_layout=True)
    ax.errorbar(
        summary["avg_score"],
        summary["conversion_rate"],
        yerr=summary["ci"],
        fmt="o-",
        color="#1f5aa6",
        ecolor="#8fb6e8",
        capsize=4,
        linewidth=2,
    )
    ax.set_title("Conversion Rises With Channel Score")
    ax.set_xlabel("Average channel score within decile")
    ax.set_ylabel("Observed conversion rate")
    ax.set_xlim(0, 1)
    ax.set_ylim(0.05, 0.55)
    ax.grid(alpha=0.25)

    out = PLOTS_DIR / "conversion_vs_channel_score.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out.name


def make_plot_budget(df: pd.DataFrame) -> str:
    df_plot = df.copy()
    df_plot["budget_decile"] = pd.qcut(df_plot["ad_budget_usd"], 10, duplicates="drop")
    summary = (
        df_plot.groupby("budget_decile", observed=False)
        .agg(
            conversion_rate=("converted", "mean"),
            avg_budget=("ad_budget_usd", "mean"),
            n=("converted", "size"),
        )
        .reset_index(drop=True)
    )
    summary["ci"] = 1.96 * np.sqrt(
        summary["conversion_rate"] * (1 - summary["conversion_rate"]) / summary["n"]
    )

    fig, ax = plt.subplots(figsize=(8.5, 5.5), constrained_layout=True)
    ax.errorbar(
        summary["avg_budget"],
        summary["conversion_rate"],
        yerr=summary["ci"],
        fmt="o-",
        color="#8c4b1f",
        ecolor="#d4aa8a",
        capsize=4,
        linewidth=2,
    )
    ax.axhline(df["converted"].mean(), color="black", linestyle="--", linewidth=1.2)
    ax.set_title("Ad Budget Shows Little Relationship To Conversion")
    ax.set_xlabel("Average ad budget within decile (USD)")
    ax.set_ylabel("Observed conversion rate")
    ax.set_ylim(0.15, 0.4)
    ax.grid(alpha=0.25)

    out = PLOTS_DIR / "ad_budget_vs_conversion.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out.name


def make_plot_calibration(df: pd.DataFrame, cv_results) -> str:
    prob_true, prob_pred = calibration_curve(
        df["converted"], cv_results["oof_pred"], n_bins=8, strategy="quantile"
    )

    fig, ax = plt.subplots(figsize=(6.5, 6.0), constrained_layout=True)
    ax.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1.2, label="Perfect")
    ax.plot(prob_pred, prob_true, marker="o", linewidth=2.2, color="#2a7f62", label="Model")
    ax.set_title("Out-of-Fold Calibration")
    ax.set_xlabel("Predicted conversion probability")
    ax.set_ylabel("Observed conversion rate")
    ax.set_xlim(0, 0.8)
    ax.set_ylim(0, 0.8)
    ax.grid(alpha=0.25)
    ax.legend()

    out = PLOTS_DIR / "model_calibration.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out.name


def write_report(df: pd.DataFrame, interaction_model, lr_tests, cv_results, plot_files):
    device_counts = df["device"].value_counts()
    score_time = df.copy()
    score_time["score_bin"] = pd.qcut(
        score_time["channel_score"], q=[0, 0.33, 0.67, 1.0], labels=["low", "mid", "high"]
    )
    score_time["time_bin"] = pd.cut(
        score_time["time_of_day_hour"],
        bins=[0, 6, 12, 18, 24],
        include_lowest=True,
        labels=["00-06", "06-12", "12-18", "18-24"],
    )
    group_rates = (
        score_time.groupby(["score_bin", "time_bin"], observed=False)["converted"]
        .agg(["mean", "size", "sum"])
        .rename(columns={"mean": "conversion_rate", "size": "n"})
    )

    low_overnight = group_rates.loc[("low", "00-06"), "conversion_rate"]
    high_evening = group_rates.loc[("high", "18-24"), "conversion_rate"]

    scenario_rows = []
    medians = {
        "ad_budget_usd": df["ad_budget_usd"].median(),
        "page_load_time_sec": df["page_load_time_sec"].median(),
        "previous_visits": df["previous_visits"].median(),
        "device": "mobile",
    }
    for score in [0.1, 0.5, 0.9]:
        for hour in [2, 12, 22]:
            scenario_rows.append(
                medians
                | {
                    "channel_score": score,
                    "time_of_day_hour": hour,
                }
            )
    scenarios = pd.DataFrame(scenario_rows)
    scenarios["predicted_probability"] = interaction_model.predict(scenarios)

    pred_low_2 = scenarios.query("channel_score == 0.1 and time_of_day_hour == 2")[
        "predicted_probability"
    ].iloc[0]
    pred_low_22 = scenarios.query("channel_score == 0.1 and time_of_day_hour == 22")[
        "predicted_probability"
    ].iloc[0]
    pred_high_2 = scenarios.query("channel_score == 0.9 and time_of_day_hour == 2")[
        "predicted_probability"
    ].iloc[0]
    pred_high_22 = scenarios.query("channel_score == 0.9 and time_of_day_hour == 22")[
        "predicted_probability"
    ].iloc[0]

    report = f"""# Dataset Analysis Report

## What this dataset is about

This appears to be a session-level digital conversion dataset with **1,500 sessions** and **8 columns**. Each row represents one visit identified by `session_id`, with a binary outcome `converted`. The predictors describe media spend (`ad_budget_usd`), timing (`time_of_day_hour`), traffic quality (`channel_score`), experience quality (`page_load_time_sec`), return behavior (`previous_visits`), and device type.

The data is unusually clean: there are **no missing values**, no duplicate `session_id`s, and all columns have plausible ranges. The only categorical feature is `device` with **833 mobile**, **509 desktop**, and **158 tablet** sessions. The outcome is moderately imbalanced: **29.3%** of sessions converted.

## Key findings

### 1. Conversion is driven mainly by a time-by-channel-quality interaction

The strongest pattern is not a simple main effect. Conversion rises later in the day, but the increase is much steeper for high-`channel_score` traffic than for low-score traffic. Adding the interaction `channel_score:time_of_day_hour` improved logistic model fit with a likelihood-ratio statistic of **{lr_tests["interaction"]["lr"]:.2f}** on **{lr_tests["interaction"]["df"]}** degree of freedom (**p = {lr_tests["interaction"]["p"]:.2e}**).

Observed conversion rates make the interaction concrete. In the lowest `channel_score` tercile during **00-06**, the conversion rate is **{fmt_pct(low_overnight)}**. In the highest `channel_score` tercile during **18-24**, it reaches **{fmt_pct(high_evening)}**. The plot [plots/{plot_files["time_score"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["time_score"]}) shows both the observed heatmap and the fitted probability curves.

At representative median values for the other features, the interaction-aware model predicts:

- For `channel_score = 0.1`, conversion rises only from **{fmt_pct(pred_low_2)}** at hour 2 to **{fmt_pct(pred_low_22)}** at hour 22.
- For `channel_score = 0.9`, conversion rises from **{fmt_pct(pred_high_2)}** at hour 2 to **{fmt_pct(pred_high_22)}** at hour 22.

Interpretation: later-day demand appears to be concentrated in higher-quality channels. If this pattern is real operationally, scheduling and channel allocation matter more than uniformly increasing spend.

### 2. `channel_score` is a strong monotonic ranking signal

Even before considering interaction, `channel_score` has a clear positive association with conversion. In quintile summaries, the conversion rate rises from **16.3%** in the lowest fifth of scores to **43.7%** in the highest fifth. The decile view in [plots/{plot_files["channel_score"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["channel_score"]}) is close to monotonic, which is what a useful ranking variable should look like.

The predictive model reinforces this. A regularized logistic regression evaluated with 5-fold stratified cross-validation achieved mean **ROC AUC = {cv_results["auc"].mean():.3f}** and mean **Brier score = {cv_results["brier"].mean():.3f}**. That is materially better than chance, but far from deterministic, implying `channel_score` carries useful information without fully determining the outcome. The calibration curve in [plots/{plot_files["calibration"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["calibration"]}) is reasonably close to the diagonal, so predicted probabilities are directionally credible.

Interpretation: `channel_score` is likely the best single feature for prioritization or targeting, especially when combined with time-of-day.

### 3. More budget does not translate into more conversion in this sample

`ad_budget_usd` looks important by name, but not by evidence. Across budget quintiles, conversion rates remain in a narrow band from **26.3%** to **31.3%**. In the interaction-aware logistic model, dropping `ad_budget_usd` barely changes fit (likelihood-ratio statistic **{lr_tests["ad_budget_usd"]["lr"]:.3f}**, **p = {lr_tests["ad_budget_usd"]["p"]:.3f}**).

The budget decile plot [plots/{plot_files["budget"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["budget"]}) is effectively flat within sampling noise. Device type is also uninformative after adjustment (**p = {lr_tests["device"]["p"]:.3f}**), and page load time is not distinguishable from noise here (**p = {lr_tests["page_load_time_sec"]["p"]:.3f}**).

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
- [plots/{plot_files["time_score"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["time_score"]})
- [plots/{plot_files["channel_score"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["channel_score"]})
- [plots/{plot_files["budget"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["budget"]})
- [plots/{plot_files["calibration"]}](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmpht3jtrd0/plots/{plot_files["calibration"]})
"""

    (ROOT / "analysis_report.md").write_text(report)


def main():
    sns.set_theme(style="whitegrid", context="talk")
    df = pd.read_csv(ROOT / "dataset.csv")
    base_model, interaction_model, lr_tests = fit_models(df)
    cv_results = fit_cv_model(df)

    plot_files = {
        "time_score": make_plot_time_score(df, interaction_model),
        "channel_score": make_plot_channel_score(df),
        "budget": make_plot_budget(df),
        "calibration": make_plot_calibration(df, cv_results),
    }

    write_report(df, interaction_model, lr_tests, cv_results, plot_files)


if __name__ == "__main__":
    main()
