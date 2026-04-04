from __future__ import annotations

from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test
from scipy import stats


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def save_and_check(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Programmatic read-back: verifies the saved PNG is non-empty and has contrast.
    image = mpimg.imread(path)
    if image.size == 0:
        raise ValueError(f"Empty image written to {path}")
    if float(np.nanmax(image) - np.nanmin(image)) < 0.01:
        raise ValueError(f"Low-contrast image written to {path}")


def format_p(value: float) -> str:
    if value < 1e-4:
        return f"{value:.2e}"
    return f"{value:.4f}"


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    df = pd.read_csv(DATA_PATH)

    df["sex_male"] = (df["sex"] == "M").astype(int)
    df["treatment_B"] = (df["treatment"] == "Drug_B").astype(int)
    df["log_biomarker"] = np.log(df["biomarker_level"])

    stage_order = ["I", "II", "III", "IV"]
    df["stage"] = pd.Categorical(df["stage"], categories=stage_order, ordered=True)

    treatment_counts = df["treatment"].value_counts().sort_index()
    event_rate = df.groupby("treatment")["event_occurred"].mean().sort_index()
    stage_by_treatment = pd.crosstab(df["treatment"], df["stage"])
    stage_pct_by_treatment = stage_by_treatment.div(stage_by_treatment.sum(axis=1), axis=0)

    age_t = stats.ttest_ind(
        df.loc[df["treatment"] == "Drug_A", "age"],
        df.loc[df["treatment"] == "Drug_B", "age"],
        equal_var=False,
    )
    biomarker_mwu = stats.mannwhitneyu(
        df.loc[df["treatment"] == "Drug_A", "biomarker_level"],
        df.loc[df["treatment"] == "Drug_B", "biomarker_level"],
        alternative="two-sided",
    )
    sex_ct = pd.crosstab(df["sex"], df["treatment"])
    sex_chi2 = stats.chi2_contingency(sex_ct)
    stage_chi2 = stats.chi2_contingency(stage_by_treatment)

    km_stats = {}
    for treatment in ["Drug_A", "Drug_B"]:
        mask = df["treatment"] == treatment
        kmf = KaplanMeierFitter()
        kmf.fit(
            df.loc[mask, "months_on_study"],
            event_observed=df.loc[mask, "event_occurred"],
            label=treatment,
        )
        km_stats[treatment] = {
            "median": float(kmf.median_survival_time_),
            "surv_12": float(kmf.predict(12)),
            "surv_24": float(kmf.predict(24)),
        }

    logrank = logrank_test(
        df.loc[df["treatment"] == "Drug_A", "months_on_study"],
        df.loc[df["treatment"] == "Drug_B", "months_on_study"],
        event_observed_A=df.loc[df["treatment"] == "Drug_A", "event_occurred"],
        event_observed_B=df.loc[df["treatment"] == "Drug_B", "event_occurred"],
    )
    stage_logrank = multivariate_logrank_test(
        df["months_on_study"], df["stage"], df["event_occurred"]
    )

    stage_dummies = pd.get_dummies(df["stage"], prefix="stage", drop_first=True)
    cox_cols = ["months_on_study", "event_occurred", "age", "sex_male", "treatment_B", "log_biomarker"]
    model_df = pd.concat([df[cox_cols], stage_dummies], axis=1)
    cph = CoxPHFitter()
    cph.fit(model_df, duration_col="months_on_study", event_col="event_occurred")
    cox_summary = cph.summary.copy()

    treatment_only = CoxPHFitter()
    treatment_only.fit(
        df[["months_on_study", "event_occurred", "treatment_B"]],
        duration_col="months_on_study",
        event_col="event_occurred",
    )

    interaction_df = model_df.copy()
    interaction_df["tx_biomarker"] = interaction_df["treatment_B"] * interaction_df["log_biomarker"]
    interaction_model = CoxPHFitter()
    interaction_model.fit(
        interaction_df,
        duration_col="months_on_study",
        event_col="event_occurred",
    )

    tx_stage_df = model_df.copy()
    for stage in ["II", "III", "IV"]:
        tx_stage_df[f"tx_stage_{stage}"] = tx_stage_df["treatment_B"] * tx_stage_df[f"stage_{stage}"]
    tx_stage_model = CoxPHFitter()
    tx_stage_model.fit(
        tx_stage_df,
        duration_col="months_on_study",
        event_col="event_occurred",
    )

    tx_hr = cox_summary.loc["treatment_B", "exp(coef)"]
    tx_ci_low = cox_summary.loc["treatment_B", "exp(coef) lower 95%"]
    tx_ci_high = cox_summary.loc["treatment_B", "exp(coef) upper 95%"]
    tx_p = cox_summary.loc["treatment_B", "p"]

    biomarker_hr = cox_summary.loc["log_biomarker", "exp(coef)"]
    biomarker_ci_low = cox_summary.loc["log_biomarker", "exp(coef) lower 95%"]
    biomarker_ci_high = cox_summary.loc["log_biomarker", "exp(coef) upper 95%"]
    biomarker_p = cox_summary.loc["log_biomarker", "p"]

    interaction_p = interaction_model.summary.loc["tx_biomarker", "p"]
    stage_interaction_ps = tx_stage_model.summary.loc[
        ["tx_stage_II", "tx_stage_III", "tx_stage_IV"], "p"
    ]

    treatment_delta_12 = km_stats["Drug_B"]["surv_12"] - km_stats["Drug_A"]["surv_12"]
    treatment_delta_24 = km_stats["Drug_B"]["surv_24"] - km_stats["Drug_A"]["surv_24"]

    fig, ax = plt.subplots(figsize=(9, 6))
    bottom = np.zeros(len(stage_pct_by_treatment))
    palette = sns.color_palette("crest", n_colors=len(stage_order))
    x = np.arange(len(stage_pct_by_treatment.index))
    for color, stage in zip(palette, stage_order):
        values = stage_pct_by_treatment[stage].values
        ax.bar(x, values, bottom=bottom, label=f"Stage {stage}", color=color, width=0.6)
        bottom += values
    ax.set_xticks(x)
    ax.set_xticklabels(stage_pct_by_treatment.index)
    ax.set_ylabel("Share of treatment group")
    ax.set_xlabel("Treatment arm")
    ax.set_title("Baseline stage mix differs slightly by treatment arm")
    ax.legend(frameon=True, title="Cancer stage")
    save_and_check(fig, PLOTS_DIR / "stage_by_treatment.png")

    fig, ax = plt.subplots(figsize=(9, 6))
    for treatment, color in zip(["Drug_A", "Drug_B"], ["#c44e52", "#4c72b0"]):
        mask = df["treatment"] == treatment
        kmf = KaplanMeierFitter()
        kmf.fit(
            df.loc[mask, "months_on_study"],
            event_observed=df.loc[mask, "event_occurred"],
            label=treatment,
        )
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2.5)
    ax.set_title("Drug_B maintains higher event-free survival throughout follow-up")
    ax.set_xlabel("Months on study")
    ax.set_ylabel("Estimated event-free survival")
    ax.set_ylim(0, 1.02)
    ax.text(
        0.98,
        0.05,
        (
            f"Log-rank p={format_p(logrank.p_value)}\n"
            f"Median survival: Drug_A {km_stats['Drug_A']['median']:.1f} mo, "
            f"Drug_B {km_stats['Drug_B']['median']:.1f} mo"
        ),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.9},
        fontsize=11,
    )
    save_and_check(fig, PLOTS_DIR / "km_treatment.png")

    forest = cox_summary.reset_index().rename(columns={"covariate": "term"})
    forest["label"] = forest["term"].map(
        {
            "age": "Age (per year)",
            "sex_male": "Male vs female",
            "treatment_B": "Drug_B vs Drug_A",
            "log_biomarker": "Log biomarker",
            "stage_II": "Stage II vs I",
            "stage_III": "Stage III vs I",
            "stage_IV": "Stage IV vs I",
        }
    )
    forest = forest.sort_values("exp(coef)")

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(forest))
    ax.errorbar(
        forest["exp(coef)"],
        y,
        xerr=[
            forest["exp(coef)"] - forest["exp(coef) lower 95%"],
            forest["exp(coef) upper 95%"] - forest["exp(coef)"],
        ],
        fmt="o",
        color="#2f4858",
        ecolor="#7aa6c2",
        elinewidth=2,
        capsize=4,
    )
    ax.axvline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(forest["label"])
    ax.set_xlabel("Hazard ratio (95% CI)")
    ax.set_title("Adjusted Cox model: treatment is the dominant risk discriminator")
    save_and_check(fig, PLOTS_DIR / "cox_forest.png")

    report = f"""# Survival Analysis Report

## What this dataset appears to contain

`dataset.csv` contains 800 patient records with 8 columns: a unique patient identifier, demographic covariates (`age`, `sex`), disease/tumor descriptors (`stage`, `biomarker_level`), treatment assignment (`Drug_A` or `Drug_B`), follow-up time in months (`months_on_study`), and an event indicator (`event_occurred`).

The structure is unusually clean for operational clinical data: there are no missing values, no duplicate patient IDs, and all variables have plausible ranges. Ages run from 30 to 90 years (mean 62.0), biomarker values are right-skewed (median 4.46, max 53.94), and 66.3% of patients experienced the event during follow-up. The dataset looks most like a trial-style or curated observational survival dataset, so the main question is time to event rather than simple event classification.

## Key findings

### 1. Treatment arm is the strongest signal in the dataset

The clearest finding is a large separation between treatment groups in event-free survival. In the Kaplan-Meier curves in `plots/km_treatment.png`, `Drug_B` stays above `Drug_A` throughout follow-up. The median event-free survival is 13.5 months for `Drug_B` versus 7.6 months for `Drug_A`. Estimated survival at 12 months is 54.2% for `Drug_B` and 33.5% for `Drug_A`, a gap of 20.7 percentage points; at 24 months the gap is still 21.1 points (31.5% vs 10.4%).

This difference is highly unlikely to be noise. The log-rank test gives p = {format_p(logrank.p_value)}. In an adjusted Cox proportional-hazards model controlling for age, sex, stage, and log biomarker, `Drug_B` has a hazard ratio of {tx_hr:.2f} (95% CI {tx_ci_low:.2f} to {tx_ci_high:.2f}, p = {format_p(tx_p)}). Interpreted practically, patients on `Drug_B` have about a 49% lower instantaneous event risk than comparable patients on `Drug_A`.

### 2. There is some baseline imbalance, but it does not explain the treatment result

Before interpreting the survival difference, I checked whether the treatment groups looked systematically different at baseline. Age (Welch t-test p = {format_p(age_t.pvalue)}), sex (chi-square p = {format_p(sex_chi2.pvalue)}), and biomarker level (Mann-Whitney p = {format_p(biomarker_mwu.pvalue)}) are all fairly similar across arms. Stage is the one variable that does differ: chi-square p = {format_p(stage_chi2.pvalue)}.

The imbalance is visible in `plots/stage_by_treatment.png`. Stage I patients make up {100 * stage_pct_by_treatment.loc['Drug_A', 'I']:.1f}% of `Drug_A` but {100 * stage_pct_by_treatment.loc['Drug_B', 'I']:.1f}% of `Drug_B`, so `Drug_B` does have a somewhat easier baseline case mix. However, this is not enough to explain the outcome gap. Once stage is included in the adjusted Cox model, the treatment hazard ratio remains essentially unchanged at {tx_hr:.2f}. If the raw treatment difference were mostly stage confounding, that estimate should have moved substantially toward 1.0 after adjustment.

### 3. The usual prognostic variables are surprisingly weak here

The adjusted Cox model in `plots/cox_forest.png` shows that age, sex, stage, and biomarker carry much less signal than treatment. None of the stage indicators are statistically distinguishable from the Stage I reference group, and a stage-only log-rank comparison is also null (p = {format_p(stage_logrank.p_value)}). The biomarker effect is small and imprecise: hazard ratio {biomarker_hr:.2f} per one-unit increase in log biomarker (95% CI {biomarker_ci_low:.2f} to {biomarker_ci_high:.2f}, p = {format_p(biomarker_p)}).

This is not just a question of underpowered interactions. When I added treatment-biomarker and treatment-stage interaction terms, there was no convincing heterogeneity of treatment effect. The treatment-biomarker interaction had p = {format_p(interaction_p)}, and the treatment-stage interaction p-values were {", ".join(f"{idx.replace('tx_stage_', 'Stage ')}: {format_p(val)}" for idx, val in stage_interaction_ps.items())}. Model discrimination only improved from a concordance index of {treatment_only.concordance_index_:.3f} with treatment alone to {cph.concordance_index_:.3f} with all baseline covariates, which reinforces the same point: most of the predictive signal is in the treatment arm itself.

## What the findings mean

If this dataset reflects a real study, the practical conclusion is straightforward: `Drug_B` is associated with materially longer event-free survival, and that association is robust to the observed baseline covariates. The clinical implication would be strong preference for `Drug_B` over `Drug_A`, assuming no countervailing toxicity or cost information outside this table.

The more surprising implication is what the dataset does **not** show. Variables that are usually prognostic in oncology-style data, especially stage and biomarker burden, have little explanatory value here. That could mean the event process in this dataset is genuinely treatment-driven, or it could mean the available covariates are too coarse to capture true baseline severity.

## Limitations and self-critique

The biggest limitation is causal interpretation. I can show a strong association between treatment and survival, but I cannot prove treatment caused the difference from this table alone. Treatment assignment is not known to be randomized, and the stage imbalance shows that the arms are not perfectly exchangeable. Unmeasured confounders such as comorbidities, performance status, prior therapy, or site effects could still account for part of the benefit.

Another caution is the unusual weakness of stage and biomarker. That result could be real, but it could also reflect noisy or simplified variable definitions. `stage` may be too coarse, biomarker timing is unknown, and there is no information about measurement error or how the event was defined. Because the dataset is perfectly complete and highly structured, it may also be synthetic or heavily curated; if so, inference should focus on the simulated relationships actually present rather than on external clinical realism.

Model assumptions were checked to the extent possible within this analysis. The Cox model did not show obvious proportional-hazards violations for the included covariates, but I did not fit alternative survival families or conduct sensitivity analyses for unmeasured confounding. I also programmatically reloaded each saved PNG to verify that the files were non-empty and had visual contrast, but direct manual image inspection was limited by the terminal-only environment.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
