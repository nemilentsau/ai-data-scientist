from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
PLOTS_DIR.mkdir(exist_ok=True)


def cohens_f_from_anova(f_stat: float, df_between: int, df_within: int) -> float:
    return np.sqrt((f_stat * df_between) / df_within)


def cramers_v(table: pd.DataFrame) -> float:
    chi2 = stats.chi2_contingency(table)[0]
    n = table.to_numpy().sum()
    r, k = table.shape
    return np.sqrt(chi2 / (n * min(r - 1, k - 1)))


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    df = pd.read_csv(DATA_PATH)
    observed = df.dropna(subset=["reported_annual_income"]).copy()
    df["income_missing"] = df["reported_annual_income"].isna().astype(int)

    income_model = smf.ols(
        "reported_annual_income ~ age + education_years + C(gender) + C(region) + num_children",
        data=observed,
    ).fit()
    sat_model = smf.ols(
        "satisfaction_score ~ age + education_years + reported_annual_income + C(gender) + C(region) + num_children",
        data=observed,
    ).fit()
    missing_model = smf.logit(
        "income_missing ~ age + education_years + C(gender) + C(region) + num_children + satisfaction_score",
        data=df,
    ).fit(disp=0)

    gender_missing = (
        df.groupby("gender")["income_missing"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "missing_rate"})
        .reset_index()
    )
    gender_missing["se"] = np.sqrt(
        gender_missing["missing_rate"] * (1 - gender_missing["missing_rate"]) / gender_missing["count"]
    )
    gender_missing["ci95"] = 1.96 * gender_missing["se"]

    plt.figure(figsize=(8, 5.5))
    ax = sns.barplot(
        data=gender_missing.sort_values("missing_rate", ascending=False),
        x="gender",
        y="missing_rate",
        hue="gender",
        dodge=False,
        legend=False,
        palette=["#3a7ca5", "#7fb069", "#d1495b"],
    )
    ax.errorbar(
        x=np.arange(len(gender_missing)),
        y=gender_missing.sort_values("missing_rate", ascending=False)["missing_rate"],
        yerr=gender_missing.sort_values("missing_rate", ascending=False)["ci95"],
        fmt="none",
        c="black",
        capsize=5,
        lw=1.5,
    )
    ax.set(
        title="Income Nonresponse Rate by Gender",
        xlabel="Gender",
        ylabel="Share with missing income",
        ylim=(0, 0.65),
    )
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    savefig(PLOTS_DIR / "income_missing_by_gender.png")

    edu_summary = (
        observed.groupby("education_years")["reported_annual_income"]
        .agg(["mean", "count"])
        .reset_index()
    )
    plt.figure(figsize=(10, 6))
    ax = sns.regplot(
        data=edu_summary,
        x="education_years",
        y="mean",
        scatter_kws={"s": edu_summary["count"] * 6, "color": "#1d3557", "alpha": 0.9},
        line_kws={"color": "#e63946", "lw": 2.5},
        ci=None,
    )
    for _, row in edu_summary.iterrows():
        ax.text(row["education_years"], row["mean"] + 900, f"n={int(row['count'])}", ha="center", fontsize=9)
    ax.set(
        title="Mean Reported Income Rises with Education",
        xlabel="Education years",
        ylabel="Mean annual income (USD)",
    )
    savefig(PLOTS_DIR / "income_vs_education.png")

    coef = income_model.params.drop("Intercept")
    ci = income_model.conf_int().drop("Intercept")
    coef_df = (
        pd.DataFrame({"term": coef.index, "coef": coef.values, "low": ci[0].values, "high": ci[1].values})
        .sort_values("coef")
        .reset_index(drop=True)
    )
    plt.figure(figsize=(10, 6.5))
    ax = plt.gca()
    ax.hlines(coef_df["term"], coef_df["low"], coef_df["high"], color="#457b9d", lw=3)
    ax.plot(coef_df["coef"], coef_df["term"], "o", color="#1d3557", markersize=8)
    ax.axvline(0, color="black", ls="--", lw=1)
    ax.set(
        title="Income Model Coefficients with 95% Confidence Intervals",
        xlabel="Estimated income difference (USD)",
        ylabel="Predictor",
    )
    savefig(PLOTS_DIR / "income_model_coefficients.png")

    plt.figure(figsize=(9, 6))
    ax = sns.regplot(
        data=observed,
        x="reported_annual_income",
        y="satisfaction_score",
        lowess=True,
        scatter_kws={"s": 28, "alpha": 0.28, "color": "#457b9d"},
        line_kws={"color": "#d62828", "lw": 3},
    )
    ax.set(
        title="Satisfaction Increases Slightly with Income",
        xlabel="Reported annual income (USD)",
        ylabel="Satisfaction score",
    )
    savefig(PLOTS_DIR / "satisfaction_vs_income.png")

    with (ROOT / "analysis_stats.txt").open("w") as f:
        f.write(f"shape={df.shape}\n")
        f.write(f"missing_income={df['income_missing'].mean():.3f}\n")
        f.write("gender_counts\n")
        f.write(df["gender"].value_counts().to_string())
        f.write("\n\nregion_counts\n")
        f.write(df["region"].value_counts().to_string())
        f.write("\n\nchildren_counts\n")
        f.write(df["num_children"].value_counts().sort_index().to_string())
        f.write("\n\nincome_model_summary\n")
        f.write(income_model.summary().as_text())
        f.write("\n\nsatisfaction_model_summary\n")
        f.write(sat_model.summary().as_text())
        f.write("\n\nmissing_model_summary\n")
        f.write(missing_model.summary().as_text())

        rho, rho_p = stats.spearmanr(observed["education_years"], observed["reported_annual_income"])
        chi2_gender = pd.crosstab(df["gender"], df["income_missing"])
        chi2_stat, chi2_p, _, _ = stats.chi2_contingency(chi2_gender)
        anova_region = stats.f_oneway(*[g["satisfaction_score"].values for _, g in df.groupby("region")])
        anova_children = stats.f_oneway(*[g["satisfaction_score"].values for _, g in df.groupby("num_children")])

        f.write(
            "\n\nsummary_metrics\n"
            f"spearman_education_income_rho={rho:.4f}, p={rho_p:.4g}\n"
            f"chi2_gender_missing={chi2_stat:.4f}, p={chi2_p:.4g}, cramers_v={cramers_v(chi2_gender):.4f}\n"
            f"anova_region_satisfaction_F={anova_region.statistic:.4f}, p={anova_region.pvalue:.4g}, "
            f"cohens_f={cohens_f_from_anova(anova_region.statistic, 4, 995):.4f}\n"
            f"anova_children_satisfaction_F={anova_children.statistic:.4f}, p={anova_children.pvalue:.4g}, "
            f"cohens_f={cohens_f_from_anova(anova_children.statistic, 4, 995):.4f}\n"
            f"observed_income_share={len(observed) / len(df):.3f}\n"
            f"income_model_r2={income_model.rsquared:.4f}\n"
            f"satisfaction_model_r2={sat_model.rsquared:.4f}\n"
            f"missing_model_pr2={missing_model.prsquared:.4f}\n"
        )


if __name__ == "__main__":
    main()
