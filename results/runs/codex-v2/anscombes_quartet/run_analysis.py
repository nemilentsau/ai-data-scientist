from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats


sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 150


ROOT = Path(__file__).resolve().parent
PLOTS = ROOT / "plots"
PLOTS.mkdir(exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "dataset.csv")
    df["batch"] = pd.Categorical(
        df["batch"], categories=sorted(df["batch"].unique()), ordered=True
    )
    df["technician"] = pd.Categorical(
        df["technician"],
        categories=sorted(df["technician"].unique()),
        ordered=True,
    )
    return df


def batch_model_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for batch, group in df.groupby("batch", observed=True):
        model = smf.ols("response ~ dosage_mg", data=group).fit()
        influence = model.get_influence().summary_frame()
        top_idx = influence["cooks_d"].idxmax()
        trimmed = group.drop(index=top_idx)
        trimmed_model = smf.ols("response ~ dosage_mg", data=trimmed).fit()
        rows.append(
            {
                "batch": batch,
                "corr": group["dosage_mg"].corr(group["response"]),
                "slope": model.params["dosage_mg"],
                "r2": model.rsquared,
                "top_obs": int(group.loc[top_idx, "observation_id"]),
                "top_cooks_d": influence.loc[top_idx, "cooks_d"],
                "drop_slope": trimmed_model.params["dosage_mg"],
                "drop_r2": trimmed_model.rsquared,
            }
        )
    return pd.DataFrame(rows)


def make_batch_scatter(df: pd.DataFrame, batch_stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), sharex=True, sharey=True)
    palette = sns.color_palette("Set2", n_colors=4)
    xlim = (df["dosage_mg"].min() - 1, df["dosage_mg"].max() + 1)
    ylim = (df["response"].min() - 0.8, df["response"].max() + 0.8)

    for ax, (batch, group), color in zip(
        axes.flatten(), df.groupby("batch", observed=True), palette
    ):
        sns.regplot(
            data=group,
            x="dosage_mg",
            y="response",
            ci=None,
            scatter_kws={
                "s": 90,
                "alpha": 0.9,
                "color": color,
                "edgecolor": "black",
                "linewidths": 0.6,
            },
            line_kws={"color": "black", "linewidth": 2},
            ax=ax,
        )
        for _, row in group.iterrows():
            if row["observation_id"] in [25, 41]:
                ax.text(
                    row["dosage_mg"] + 0.15,
                    row["response"] + 0.12,
                    f"obs {int(row['observation_id'])}",
                    fontsize=10,
                )

        stats_row = batch_stats.loc[batch_stats["batch"] == batch].iloc[0]
        ax.set_title(
            f"{batch}\nr={stats_row['corr']:.3f}, "
            f"slope={stats_row['slope']:.3f}, R^2={stats_row['r2']:.3f}",
            fontsize=14,
        )
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_xlabel("Dosage (mg)")
        ax.set_ylabel("Response")

    fig.suptitle("Identical Linear Summaries Hide Different Batch Structures", y=1.02)
    fig.tight_layout()
    fig.savefig(PLOTS / "batch_scatter.png", bbox_inches="tight")
    plt.close(fig)


def make_adjusted_coefficients(model) -> None:
    params = model.params
    conf = model.conf_int()
    coef_df = pd.DataFrame(
        {
            "term": params.index,
            "coef": params.values,
            "low": conf[0].values,
            "high": conf[1].values,
            "pvalue": model.pvalues.values,
        }
    )
    coef_df = coef_df[coef_df["term"] != "Intercept"].copy()

    label_map = {
        "dosage_mg": "Dosage (mg)",
        "lab_temp_c": "Lab temperature (C)",
        "weight_kg": "Weight (kg)",
        "C(batch)[T.batch_Q2]": "Batch Q2 vs Q1",
        "C(batch)[T.batch_Q3]": "Batch Q3 vs Q1",
        "C(batch)[T.batch_Q4]": "Batch Q4 vs Q1",
        "C(technician)[T.Kim]": "Technician Kim vs Alex",
        "C(technician)[T.Pat]": "Technician Pat vs Alex",
    }
    coef_df["label"] = coef_df["term"].map(label_map)
    coef_df = coef_df.sort_values("coef")

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = [
        "#c44e52" if pvalue < 0.05 else "#4c72b0"
        for pvalue in coef_df["pvalue"]
    ]
    ax.hlines(
        y=coef_df["label"],
        xmin=coef_df["low"],
        xmax=coef_df["high"],
        color=colors,
        linewidth=3,
        alpha=0.9,
    )
    ax.scatter(coef_df["coef"], coef_df["label"], color=colors, s=90, zorder=3)
    ax.axvline(0, color="black", linestyle="--", linewidth=1.5)
    ax.set_title("Adjusted Effects on Response from Multivariable OLS")
    ax.set_xlabel("Coefficient estimate with 95% CI")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(PLOTS / "adjusted_coefficients.png", bbox_inches="tight")
    plt.close(fig)


def make_influence_plot(df: pd.DataFrame) -> None:
    x = sm.add_constant(
        pd.get_dummies(df[["dosage_mg", "batch", "technician"]], drop_first=True, dtype=float)
    )
    x["lab_temp_c"] = df["lab_temp_c"]
    x["weight_kg"] = df["weight_kg"]

    model = sm.OLS(df["response"], x).fit()
    influence = model.get_influence().summary_frame()
    inf_df = df.join(influence[["hat_diag", "student_resid", "cooks_d"]])

    fig, ax = plt.subplots(figsize=(11, 8))
    scatter = ax.scatter(
        inf_df["hat_diag"],
        inf_df["student_resid"],
        s=900 * inf_df["cooks_d"] + 60,
        c=inf_df["batch"].cat.codes,
        cmap="Set2",
        alpha=0.8,
        edgecolors="black",
        linewidths=0.7,
    )
    ax.axhline(0, color="black", linewidth=1)
    ax.axhline(2, color="grey", linestyle="--", linewidth=1)
    ax.axhline(-2, color="grey", linestyle="--", linewidth=1)
    ax.axvline(2 * x.shape[1] / len(df), color="grey", linestyle="--", linewidth=1)

    highlight_ids = set(inf_df.nlargest(5, "cooks_d")["observation_id"].astype(int).tolist())
    highlight_ids.add(41)
    for _, row in inf_df.loc[inf_df["observation_id"].isin(sorted(highlight_ids))].iterrows():
        ax.text(
            row["hat_diag"] + 0.005,
            row["student_resid"] + 0.05,
            f"obs {int(row['observation_id'])}",
            fontsize=10,
        )

    ax.set_title("Influence Diagnostic: Large Bubbles Exert Disproportionate Pull")
    ax.set_xlabel("Leverage (hat value)")
    ax.set_ylabel("Externally studentized residual")
    legend_handles, _ = scatter.legend_elements(prop="colors", num=4)
    ax.legend(legend_handles, sorted(df["batch"].unique()), title="Batch", loc="upper right")
    fig.tight_layout()
    fig.savefig(PLOTS / "influence_diagnostic.png", bbox_inches="tight")
    plt.close(fig)


def write_report(df: pd.DataFrame, batch_stats: pd.DataFrame) -> None:
    model_base = smf.ols("response ~ dosage_mg", data=df).fit()
    model_full = smf.ols(
        "response ~ dosage_mg + C(batch) + C(technician) + lab_temp_c + weight_kg",
        data=df,
    ).fit()

    batch_means = df.groupby("batch", observed=True).agg(
        n=("observation_id", "size"),
        dosage_mean=("dosage_mg", "mean"),
        response_mean=("response", "mean"),
        response_sd=("response", "std"),
    )
    tech_means = df.groupby("technician", observed=True)["response"].agg(["mean", "std", "count"])
    raw_tech_p = stats.f_oneway(
        *[group["response"].values for _, group in df.groupby("technician", observed=True)]
    ).pvalue
    batch_anova_p = stats.f_oneway(
        *[group["response"].values for _, group in df.groupby("batch", observed=True)]
    ).pvalue

    lines = [
        "# Analysis Report",
        "",
        "## What this dataset appears to be about",
        "This dataset contains 44 observations from what looks like a small laboratory dose-response study. "
        "Each row records an `observation_id`, `batch`, administered `dosage_mg`, measured `response`, "
        "`lab_temp_c`, `technician`, and subject `weight_kg`.",
        "",
        "Key orientation facts:",
        "- Shape: 44 rows x 7 columns.",
        "- No missing values were present.",
        "- `batch` has 4 levels with exactly 11 rows each; `technician` has 3 levels.",
        f"- `dosage_mg` ranges from {df['dosage_mg'].min()} to {df['dosage_mg'].max()} mg, "
        f"`response` from {df['response'].min():.2f} to {df['response'].max():.2f}, "
        f"`lab_temp_c` from {df['lab_temp_c'].min():.1f} to {df['lab_temp_c'].max():.1f} C, "
        f"and `weight_kg` from {df['weight_kg'].min():.1f} to {df['weight_kg'].max():.1f} kg.",
        f"- Each batch has the same mean dosage ({batch_means['dosage_mean'].iloc[0]:.1f} mg) and nearly identical "
        "mean response (about 7.50) and response SD (about 2.03).",
        "",
        "That last point turned out to be the central feature of the dataset.",
        "",
        "## Key findings",
        "",
        "### 1. Batch-level summary statistics are almost identical, but the underlying shapes are not",
        "Hypothesis: if the batches are truly comparable, then not only their means and correlations but also their point patterns should look similar.",
        "",
        "Result: the summaries are nearly identical across all four batches, but the raw scatterplots are qualitatively different. "
        "In every batch, the dosage-response correlation is about 0.816 and the fitted slope is about 0.500, "
        "yet [batch_scatter.png](./plots/batch_scatter.png) shows four distinct geometries:",
        "- `batch_Q1` is roughly linear but moderately noisy.",
        "- `batch_Q2` is curved, so a linear fit is an oversimplification.",
        "- `batch_Q3` is almost perfectly linear except for one large outlier (`observation_id` 25).",
        "- `batch_Q4` has almost no dosage variation for 10 of 11 points; the apparent slope is created largely by one high-dosage leverage point (`observation_id` 41 at 19 mg).",
        "",
        "Evidence:",
        f"- Overall model: `response ~ dosage_mg` estimated a slope of {model_base.params['dosage_mg']:.3f} response units per mg "
        f"(95% CI {model_base.conf_int().loc['dosage_mg', 0]:.3f} to {model_base.conf_int().loc['dosage_mg', 1]:.3f}, "
        f"p={model_base.pvalues['dosage_mg']:.2e}).",
        f"- Batch means are statistically indistinguishable by ANOVA (p={batch_anova_p:.6f}), which would wrongly suggest the batches are interchangeable.",
        "- Batch-by-dosage interaction terms are near zero in a linear model, but that is misleading because the problem is geometry, not average slope alone.",
        "",
        "Interpretation: a report that only gave means, standard deviations, correlations, or a single pooled regression line would miss the real structure of the data. "
        "Visualization changes the conclusion.",
        "",
        "### 2. Two batches are heavily shaped by single influential observations",
        "Hypothesis: if the apparent linear relationships are genuine within each batch, then removing the most influential point in each batch should not radically change the fit.",
        "",
        "Result: this hypothesis failed for the most suspicious batches. The influence diagnostic in [influence_diagnostic.png](./plots/influence_diagnostic.png) "
        "shows that a small number of observations exert disproportionate pull on the fitted models.",
        "",
        "Most influential cases by Cook's distance:",
    ]

    for _, row in batch_stats.iterrows():
        lines.append(
            f"- {row['batch']}: obs {row['top_obs']} had Cook's distance {row['top_cooks_d']:.3f}; "
            f"slope changed from {row['slope']:.3f} to {row['drop_slope']:.3f} when removed, and "
            f"R^2 changed from {row['r2']:.3f} to {row['drop_r2']:.3f}."
        )

    q3 = batch_stats.loc[batch_stats["batch"] == "batch_Q3"].iloc[0]
    lines.extend(
        [
            "",
            f"The strongest example is `batch_Q3`: removing obs 25 changes the story from a noisy linear pattern "
            f"(R^2={q3['r2']:.3f}) to a perfect line (R^2={q3['drop_r2']:.3f}). "
            "`batch_Q4` is the opposite problem: the fit looks linear mostly because of one leverage point at 19 mg "
            "while the other ten observations are all at 8 mg.",
            "",
            "Interpretation: the common slope of about 0.5 is not equally trustworthy across batches. "
            "In at least two batches, the fitted relationship is fragile and observation-dependent.",
            "",
            "### 3. After accounting for dosage and batch, there is no strong evidence that technician, temperature, or weight matter",
            "Hypothesis: differences in technician handling, lab temperature, or subject weight might explain response variation beyond dosage.",
            "",
            "Test: I fit `response ~ dosage_mg + C(batch) + C(technician) + lab_temp_c + weight_kg` and inspected coefficient estimates with confidence intervals.",
            "",
            "Result: dosage remains the only clearly supported predictor. The coefficient plot in "
            "[adjusted_coefficients.png](./plots/adjusted_coefficients.png) shows:",
            f"- Dosage: {model_full.params['dosage_mg']:.3f} per mg "
            f"(95% CI {model_full.conf_int().loc['dosage_mg', 0]:.3f} to {model_full.conf_int().loc['dosage_mg', 1]:.3f}, "
            f"p={model_full.pvalues['dosage_mg']:.2e}).",
            f"- Technician Kim vs Alex: {model_full.params['C(technician)[T.Kim]']:.3f} "
            f"(95% CI {model_full.conf_int().loc['C(technician)[T.Kim]', 0]:.3f} to "
            f"{model_full.conf_int().loc['C(technician)[T.Kim]', 1]:.3f}, p={model_full.pvalues['C(technician)[T.Kim]']:.3f}).",
            f"- Technician Pat vs Alex: {model_full.params['C(technician)[T.Pat]']:.3f} "
            f"(95% CI {model_full.conf_int().loc['C(technician)[T.Pat]', 0]:.3f} to "
            f"{model_full.conf_int().loc['C(technician)[T.Pat]', 1]:.3f}, p={model_full.pvalues['C(technician)[T.Pat]']:.3f}).",
            f"- Lab temperature: {model_full.params['lab_temp_c']:.3f} per C "
            f"(95% CI {model_full.conf_int().loc['lab_temp_c', 0]:.3f} to {model_full.conf_int().loc['lab_temp_c', 1]:.3f}, "
            f"p={model_full.pvalues['lab_temp_c']:.3f}).",
            f"- Weight: {model_full.params['weight_kg']:.4f} per kg "
            f"(95% CI {model_full.conf_int().loc['weight_kg', 0]:.4f} to {model_full.conf_int().loc['weight_kg', 1]:.4f}, "
            f"p={model_full.pvalues['weight_kg']:.3f}).",
            "",
            f"Even the raw technician mean differences were not statistically convincing (one-way ANOVA p={raw_tech_p:.3f}); "
            f"Kim had the highest raw mean response ({tech_means.loc['Kim', 'mean']:.3f}) but also the widest variability.",
            "",
            "Interpretation: there is no strong evidence here that technician, temperature, or weight are driving the outcome. "
            "The dominant signal is dosage, but that signal itself must be interpreted batch-by-batch because of the structural issues above.",
            "",
            "## Practical meaning",
            "If this were a real experiment, the main operational lesson would be caution rather than optimization. "
            "A naive pooled analysis would conclude that increasing dosage raises response by about 0.5 units per mg and that batch does not matter. "
            "That conclusion is incomplete. The pooled slope exists, but its credibility varies sharply by batch because some batches reflect curvature, "
            "outliers, or leverage rather than stable within-batch linear behavior.",
            "",
            "In practice, I would not use this dataset to justify a single global linear dose-response rule without first resolving why the batch geometries differ so much. "
            "The next step would be to inspect the experimental process behind batches Q2 through Q4, especially obs 25 and obs 41, and verify whether those are measurement issues, "
            "real rare events, or intentionally different regimes.",
            "",
            "## Limitations and self-critique",
            "- Small sample: only 44 observations total and 11 per batch, so inference is sensitive to single points.",
            "- Non-random structure: the batches appear intentionally constructed rather than naturally sampled, which limits external validity.",
            "- Model assumptions are shaky within some batches because linearity is visibly violated (`batch_Q2`) or depends on influential points (`batch_Q3`, `batch_Q4`).",
            "- I treated observations as independent and did not model any repeated-measures or hierarchical structure because none was explicit in the data.",
            "- Alternative explanation: apparent batch differences could reflect undocumented protocol changes or data-generation artifacts rather than biological differences.",
            "- I did not attempt nonlinear dose-response models because the dataset is too small for that to be stable, and the stronger issue was first-order data geometry rather than predictive performance.",
            "",
            "## Bottom line",
            "The dataset looks like a dose-response study, but its main lesson is methodological: identical summary statistics can conceal radically different underlying patterns. "
            "The dose-response effect is real in the pooled data, yet some batch-level relationships are fragile, nonlinear, or driven by single observations. "
            "Any substantive conclusion should therefore be based on the raw plots, not on aggregate metrics alone.",
        ]
    )

    (ROOT / "analysis_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    df = load_data()
    batch_stats = batch_model_stats(df)
    model_full = smf.ols(
        "response ~ dosage_mg + C(batch) + C(technician) + lab_temp_c + weight_kg",
        data=df,
    ).fit()
    make_batch_scatter(df, batch_stats)
    make_adjusted_coefficients(model_full)
    make_influence_plot(df)
    write_report(df, batch_stats)


if __name__ == "__main__":
    main()
