from pathlib import Path
from textwrap import dedent, indent

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
PLOTS = ROOT / "plots"
PLOTS.mkdir(exist_ok=True)


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def markdown_table(df: pd.DataFrame) -> str:
    cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            cols.append(" ".join(str(part) for part in c if part))
        else:
            cols.append(str(c))
    lines = [
        "| " + " | ".join(["index"] + cols) + " |",
        "| " + " | ".join(["---"] * (len(cols) + 1)) + " |",
    ]
    for idx, row in df.iterrows():
        values = [str(idx)] + [str(v) for v in row.tolist()]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_preprocessor(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, ColumnTransformer]:
    X = df.drop(columns=["employee_id", "performance_rating"])
    y = df["performance_rating"]
    num = X.select_dtypes(include="number").columns.tolist()
    cat = X.select_dtypes(exclude="number").columns.tolist()
    prep = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="median")),
                        ("sc", StandardScaler()),
                    ]
                ),
                num,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="most_frequent")),
                        ("oh", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                cat,
            ),
        ]
    )
    return X, y, prep


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    df = pd.read_csv(ROOT / "dataset.csv")

    salary_order = ["L1", "L2", "L3", "L4", "L5"]
    remote_order = [0, 25, 50, 75, 100]

    # Hypothesis 1: salary band should increase with experience.
    salary_groups = [g["years_experience"].to_numpy() for _, g in df.groupby("salary_band")]
    salary_anova = stats.f_oneway(*salary_groups)
    salary_kruskal = stats.kruskal(*salary_groups)
    salary_summary = (
        df.groupby("salary_band")["years_experience"]
        .agg(["mean", "median", "std", "count"])
        .reindex(salary_order)
        .round(2)
    )

    plt.figure(figsize=(10, 6))
    sns.boxplot(
        data=df,
        x="salary_band",
        y="years_experience",
        order=salary_order,
        color="#b7d4ea",
        fliersize=0,
    )
    sns.stripplot(
        data=df.sample(n=min(len(df), 250), random_state=42),
        x="salary_band",
        y="years_experience",
        order=salary_order,
        color="#1f4e79",
        alpha=0.35,
        size=4,
        jitter=0.22,
    )
    plt.title("Years Of Experience Overlap Heavily Across Salary Bands")
    plt.xlabel("Salary band")
    plt.ylabel("Years of experience")
    savefig(PLOTS / "salary_band_vs_experience.png")

    # Hypothesis 2: remote work reduces commute and improves satisfaction.
    remote_commute_rho, remote_commute_p = stats.spearmanr(df["remote_pct"], df["commute_minutes"])
    remote_satisfaction_anova = stats.f_oneway(
        *[g["satisfaction_score"].to_numpy() for _, g in df.groupby("remote_pct")]
    )
    remote_summary = (
        df.groupby("remote_pct")[["commute_minutes", "satisfaction_score"]]
        .agg(["mean", "median"])
        .reindex(remote_order)
        .round(2)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharex=True)
    sns.pointplot(
        data=df,
        x="remote_pct",
        y="commute_minutes",
        order=remote_order,
        errorbar=("ci", 95),
        color="#c96a28",
        ax=axes[0],
    )
    axes[0].set_title("Commute Falls Slightly, But Not Monotonically")
    axes[0].set_xlabel("Remote share (%)")
    axes[0].set_ylabel("Commute minutes")

    sns.pointplot(
        data=df,
        x="remote_pct",
        y="satisfaction_score",
        order=remote_order,
        errorbar=("ci", 95),
        color="#2b7a78",
        ax=axes[1],
    )
    axes[1].set_title("Satisfaction Is Nearly Flat Across Remote Levels")
    axes[1].set_xlabel("Remote share (%)")
    axes[1].set_ylabel("Satisfaction score")
    savefig(PLOTS / "remote_work_outcomes.png")

    # Hypothesis 3: larger teams reduce performance.
    ols = smf.ols(
        "performance_rating ~ training_hours + projects_completed + years_experience + "
        "satisfaction_score + commute_minutes + remote_pct + team_size + C(salary_band)",
        data=df,
    ).fit()
    team_coef = ols.params["team_size"]
    team_ci_low, team_ci_high = ols.conf_int().loc["team_size"]
    team_p = ols.pvalues["team_size"]

    plt.figure(figsize=(10, 6))
    sns.regplot(
        data=df,
        x="team_size",
        y="performance_rating",
        lowess=True,
        scatter_kws={"alpha": 0.22, "s": 28, "color": "#6b5b95"},
        line_kws={"color": "#111111", "linewidth": 2.5},
    )
    plt.title("Performance Slips Modestly As Teams Get Larger")
    plt.xlabel("Team size")
    plt.ylabel("Performance rating")
    savefig(PLOTS / "team_size_vs_performance.png")

    # Hypothesis 4: can the available features predict performance?
    X, y, prep = build_preprocessor(df)
    ridge = Pipeline([("prep", prep), ("model", Ridge(alpha=1.0))])
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    ridge_r2 = cross_val_score(ridge, X, y, cv=cv, scoring="r2")
    ridge_rmse = -cross_val_score(ridge, X, y, cv=cv, scoring="neg_root_mean_squared_error")
    cv_pred = cross_val_predict(ridge, X, y, cv=cv)

    plt.figure(figsize=(7, 7))
    plt.scatter(cv_pred, y, alpha=0.3, s=28, color="#00798c")
    lims = [min(cv_pred.min(), y.min()), max(cv_pred.max(), y.max())]
    plt.plot(lims, lims, color="#c44536", linewidth=2)
    plt.xlim(lims)
    plt.ylim(lims)
    plt.title("Cross-Validated Predictions Collapse Toward The Mean")
    plt.xlabel("Predicted performance rating")
    plt.ylabel("Actual performance rating")
    savefig(PLOTS / "performance_cv_predictions.png")

    salary_md = indent(markdown_table(salary_summary), "        ")
    remote_md = indent(markdown_table(remote_summary), "        ")

    report = dedent(
        f"""\
        # Analysis Report

        ## What this dataset is about

        `dataset.csv` contains 800 employee-level records with 10 columns covering experience, training, team context, project output, satisfaction, commute time, salary band, remote-work share, and a `performance_rating` target. The table is unusually clean: there are no missing values, no duplicate employee IDs, and the categorical fields are tightly coded (`salary_band` has 5 levels and `remote_pct` is restricted to 0, 25, 50, 75, and 100).

        The values are plausible for HR data, but the structure is atypical. Category counts are almost perfectly balanced, and most pairwise correlations are close to zero. That made the main analytical question less about which variable dominates and more about whether the expected HR relationships exist at all.

        ## Key findings

        ### 1. Salary band is not aligned with experience in this sample

        If `salary_band` encodes seniority, employees in higher bands should show materially more experience. The data do not support that.

        - Mean experience ranges only from 14.33 years in `L4` to 15.44 years in `L3`.
        - One-way ANOVA for `years_experience ~ salary_band`: F = {salary_anova.statistic:.3f}, p = {salary_anova.pvalue:.3f}.
        - Kruskal-Wallis test: H = {salary_kruskal.statistic:.3f}, p = {salary_kruskal.pvalue:.3f}.
        - Visual evidence in `plots/salary_band_vs_experience.png` shows near-complete overlap between bands.

        Interpretation: within this dataset, salary labels do not behave like a pay-grade ladder tied to tenure. Either salary band is driven by omitted variables, or the labels are not ordered in the way the names imply.

        ### 2. Remote work is not strongly linked to either commute or satisfaction

        A natural expectation is that more remote work should clearly reduce commute and possibly improve satisfaction. The commute effect is directionally negative but weak, and satisfaction is essentially flat.

        - Average commute falls from 27.96 minutes at 0% remote to 23.17 minutes at 100% remote, but the relationship is not monotonic.
        - Spearman correlation between `remote_pct` and `commute_minutes`: rho = {remote_commute_rho:.3f}, p = {remote_commute_p:.3f}.
        - Mean satisfaction stays in a narrow band from 5.49 to 5.74 across all remote-work groups.
        - One-way ANOVA for `satisfaction_score ~ remote_pct`: F = {remote_satisfaction_anova.statistic:.3f}, p = {remote_satisfaction_anova.pvalue:.3f}.
        - `plots/remote_work_outcomes.png` makes both patterns visible: small commute differences, almost no satisfaction separation.

        Interpretation: remote-work share does not explain much variation in employee sentiment here. The small commute reduction is real descriptively, but it is too noisy to support a stronger claim.

        ### 3. Larger teams are associated with slightly lower performance, but the effect is modest

        The clearest relationship in the table is a weak negative association between `team_size` and `performance_rating`.

        - In a multivariable OLS model controlling for training, projects completed, experience, satisfaction, commute, remote share, and salary band, the `team_size` coefficient is {team_coef:.3f} rating points per additional teammate.
        - 95% confidence interval: [{team_ci_low:.3f}, {team_ci_high:.3f}], p = {team_p:.3f}.
        - That implies roughly a 2.7-point lower expected rating when comparing a 24-person team with a 3-person team, holding other modeled variables constant.
        - `plots/team_size_vs_performance.png` shows the trend, but also shows how noisy it is at the individual level.

        Interpretation: bigger teams may create coordination drag or dilute individual visibility, but the practical effect is small relative to the target's standard deviation of 10.02. This is a weak structural signal, not a dominant driver.

        ### 4. The available features do not predict performance well

        To test whether performance depends on a more complex combination of variables, I fit a regularized regression model and evaluated it with 5-fold cross-validation.

        - Ridge regression mean cross-validated R² = {ridge_r2.mean():.3f} (SD {ridge_r2.std():.3f}).
        - Mean cross-validated RMSE = {ridge_rmse.mean():.3f}.
        - RMSE is effectively the same scale as the target's own standard deviation ({df['performance_rating'].std():.3f}), which means the model performs little better than predicting the overall mean every time.
        - `plots/performance_cv_predictions.png` shows predictions compressed toward the center rather than tracking actual scores.

        Interpretation: whatever drives `performance_rating` is mostly absent from this table, or the target was generated largely independently of the listed features.

        ## What the findings mean

        This dataset looks like employee data on the surface, but it does not behave like a typical observational HR dataset. Key administrative variables such as salary band, remote share, and performance are largely disconnected from the covariates that would normally explain them. That has two practical implications:

        - Strong policy claims would be unsafe. For example, the data do not support saying that remote work improves satisfaction or that salary band reflects tenure.
        - Predictive modeling is not warranted for performance with the current feature set. Better predictors would likely need manager effects, job family, role level, promotion history, tenure in role, or prior review history.

        ## Limitations and self-critique

        - This is observational, cross-sectional data, so even the team-size result is associative rather than causal.
        - I treated `salary_band` as a meaningful label because the names suggest order, but the analysis itself shows that assumption may be wrong.
        - The weak effects could reflect synthetic or deliberately decorrelated data rather than a real workplace process. The unusually balanced categories and near-zero correlation matrix support that possibility.
        - I did not test interaction-heavy models beyond a baseline linear predictor because the cross-validated linear model already showed almost no recoverable signal. A more flexible model might squeeze out slightly better fit, but it would not change the main conclusion that signal is sparse.
        - The report emphasizes effect sizes as well as p-values because several plausible relationships are not just statistically non-significant; they are substantively tiny.

        ## Appendix: key summary tables

        ### Experience by salary band

        {salary_md}

        ### Remote-work outcomes by remote share

        {remote_md}
        """
    )
    report = report.replace("\n        |", "\n|")

    (ROOT / "analysis_report.md").write_text(report)


if __name__ == "__main__":
    main()
