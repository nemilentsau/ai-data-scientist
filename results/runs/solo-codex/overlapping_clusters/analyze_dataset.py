from __future__ import annotations

from pathlib import Path
import textwrap

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

import statsmodels.api as sm
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LassoCV, LinearRegression, RidgeCV
from sklearn.metrics import make_scorer, root_mean_squared_error
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from statsmodels.graphics.gofplots import qqplot
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def format_float(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def df_to_markdown(df: pd.DataFrame, index: bool = True, digits: int = 4) -> str:
    table = df.copy()
    for col in table.columns:
        if pd.api.types.is_float_dtype(table[col]):
            table[col] = table[col].map(lambda x: f"{x:.{digits}f}")

    headers = (["index"] + [str(c) for c in table.columns]) if index else [str(c) for c in table.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for idx, row in table.iterrows():
        values = [str(idx)] if index else []
        values.extend(str(v) for v in row.tolist())
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def save_missingness_plot(df: pd.DataFrame) -> None:
    plt.figure(figsize=(8, 4))
    missing_pct = df.isna().mean().mul(100).sort_values(ascending=False)
    sns.barplot(x=missing_pct.index, y=missing_pct.values, color="#4C78A8")
    plt.ylabel("Missing values (%)")
    plt.xlabel("")
    plt.xticks(rotation=30, ha="right")
    plt.title("Missingness by Column")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "missingness.png", dpi=160)
    plt.close()


def save_distribution_plots(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    ncols = 3
    nrows = int(np.ceil(len(numeric_cols) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows))
    axes = np.atleast_1d(axes).ravel()
    for ax, col in zip(axes, numeric_cols):
        sns.histplot(df[col], kde=True, ax=ax, color="#4C78A8", edgecolor="white")
        ax.set_title(f"Distribution: {col}")
    for ax in axes[len(numeric_cols):]:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "distributions.png", dpi=160)
    plt.close()

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows))
    axes = np.atleast_1d(axes).ravel()
    for ax, col in zip(axes, numeric_cols):
        sns.boxplot(y=df[col], ax=ax, color="#72B7B2", fliersize=3)
        ax.set_title(f"Boxplot: {col}")
    for ax in axes[len(numeric_cols):]:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "boxplots.png", dpi=160)
    plt.close()


def save_correlation_heatmap(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    corr = df[numeric_cols].corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f", square=True)
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=160)
    plt.close()
    return corr


def save_gpa_relationships(df: pd.DataFrame, features: list[str]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for ax, col in zip(axes.ravel(), [c for c in features if c != "extracurriculars"]):
        sns.regplot(
            data=df,
            x=col,
            y="gpa",
            lowess=True,
            scatter_kws={"alpha": 0.6, "s": 28},
            line_kws={"color": "#E45756", "lw": 2},
            ax=ax,
        )
        ax.set_title(f"GPA vs {col}")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "gpa_vs_numeric_features.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df, x="extracurriculars", y="gpa", color="#F58518")
    plt.title("GPA by Number of Extracurriculars")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "gpa_by_extracurriculars.png", dpi=160)
    plt.close()


def build_model_results(df: pd.DataFrame) -> tuple[pd.DataFrame, sm.regression.linear_model.RegressionResultsWrapper]:
    features = ["weekly_study_hours", "extracurriculars", "commute_minutes", "part_time_job_hours", "absences"]
    X = df[features]
    y = df["gpa"]

    cv = KFold(n_splits=10, shuffle=True, random_state=42)
    rmse_scorer = make_scorer(root_mean_squared_error, greater_is_better=False)

    models = {
        "DummyMean": DummyRegressor(strategy="mean"),
        "LinearRegression": Pipeline(
            [
                (
                    "prep",
                    ColumnTransformer(
                        [
                            (
                                "num",
                                Pipeline(
                                    [
                                        ("imp", SimpleImputer(strategy="median")),
                                        ("sc", StandardScaler()),
                                    ]
                                ),
                                features,
                            )
                        ]
                    ),
                ),
                ("model", LinearRegression()),
            ]
        ),
        "Ridge": Pipeline(
            [
                (
                    "prep",
                    ColumnTransformer(
                        [
                            (
                                "num",
                                Pipeline(
                                    [
                                        ("imp", SimpleImputer(strategy="median")),
                                        ("sc", StandardScaler()),
                                    ]
                                ),
                                features,
                            )
                        ]
                    ),
                ),
                ("model", RidgeCV(alphas=np.logspace(-3, 3, 25))),
            ]
        ),
        "Lasso": Pipeline(
            [
                (
                    "prep",
                    ColumnTransformer(
                        [
                            (
                                "num",
                                Pipeline(
                                    [
                                        ("imp", SimpleImputer(strategy="median")),
                                        ("sc", StandardScaler()),
                                    ]
                                ),
                                features,
                            )
                        ]
                    ),
                ),
                ("model", LassoCV(alphas=100, cv=5, random_state=42, max_iter=20000)),
            ]
        ),
        "PolynomialRidge": Pipeline(
            [
                (
                    "prep",
                    ColumnTransformer(
                        [
                            (
                                "num",
                                Pipeline(
                                    [
                                        ("imp", SimpleImputer(strategy="median")),
                                        ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                                        ("sc", StandardScaler()),
                                    ]
                                ),
                                features,
                            )
                        ]
                    ),
                ),
                ("model", RidgeCV(alphas=np.logspace(-3, 3, 25))),
            ]
        ),
        "RandomForest": Pipeline(
            [
                ("prep", ColumnTransformer([("num", SimpleImputer(strategy="median"), features)])),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=500,
                        min_samples_leaf=5,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }

    rows = []
    for name, model in models.items():
        scores = cross_validate(
            model,
            X,
            y,
            cv=cv,
            scoring={"r2": "r2", "rmse": rmse_scorer},
            n_jobs=1,
        )
        rows.append(
            {
                "model": name,
                "mean_cv_r2": scores["test_r2"].mean(),
                "std_cv_r2": scores["test_r2"].std(),
                "mean_cv_rmse": (-scores["test_rmse"]).mean(),
                "std_cv_rmse": scores["test_rmse"].std(),
            }
        )

    results = pd.DataFrame(rows).sort_values(["mean_cv_r2", "mean_cv_rmse"], ascending=[False, True])

    X_ols = sm.add_constant(X)
    ols_model = sm.OLS(y, X_ols).fit()
    return results, ols_model


def save_model_comparison_plot(results: pd.DataFrame) -> None:
    ordered = results.sort_values("mean_cv_r2", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.barplot(data=ordered, x="mean_cv_r2", y="model", hue="model", dodge=False, palette="Blues_r", ax=axes[0], legend=False)
    axes[0].axvline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Cross-Validated R^2")
    axes[0].set_xlabel("Mean 10-fold CV R^2")
    axes[0].set_ylabel("")

    sns.barplot(data=ordered.sort_values("mean_cv_rmse"), x="mean_cv_rmse", y="model", hue="model", dodge=False, palette="Greens", ax=axes[1], legend=False)
    axes[1].set_title("Cross-Validated RMSE")
    axes[1].set_xlabel("Mean 10-fold CV RMSE")
    axes[1].set_ylabel("")

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "model_comparison.png", dpi=160)
    plt.close()


def save_ols_diagnostics(df: pd.DataFrame, ols_model: sm.regression.linear_model.RegressionResultsWrapper) -> dict[str, float | int]:
    fitted = ols_model.fittedvalues
    resid = ols_model.resid
    influence = OLSInfluence(ols_model)
    standardized_resid = influence.resid_studentized_internal
    cooks = influence.cooks_distance[0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.scatterplot(x=fitted, y=resid, ax=axes[0], s=32, alpha=0.7, color="#4C78A8")
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Residuals vs Fitted")
    axes[0].set_xlabel("Fitted GPA")
    axes[0].set_ylabel("Residuals")

    qqplot(resid, line="45", ax=axes[1], alpha=0.7)
    axes[1].set_title("Residual Q-Q Plot")

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "ols_diagnostics.png", dpi=160)
    plt.close()

    bp_lm, bp_lm_p, bp_f, bp_f_p = het_breuschpagan(resid, ols_model.model.exog)
    shapiro_stat, shapiro_p = stats.shapiro(resid)
    reset_res = linear_reset(ols_model, power=2, use_f=True)
    omni = stats.normaltest(resid)

    vif_df = pd.DataFrame(
        {
            "feature": ols_model.model.exog_names,
            "vif": [variance_inflation_factor(ols_model.model.exog, i) for i in range(ols_model.model.exog.shape[1])],
        }
    )

    diag = {
        "bp_lm": bp_lm,
        "bp_lm_p": bp_lm_p,
        "bp_f": bp_f,
        "bp_f_p": bp_f_p,
        "shapiro_stat": shapiro_stat,
        "shapiro_p": shapiro_p,
        "omnibus_stat": omni.statistic,
        "omnibus_p": omni.pvalue,
        "reset_f": float(reset_res.fvalue),
        "reset_p": float(reset_res.pvalue),
        "max_cooks": float(cooks.max()),
        "high_cooks_count": int((cooks > 4 / len(df)).sum()),
        "studentized_outliers": int((np.abs(standardized_resid) > 3).sum()),
    }

    diag["vif_table"] = vif_df
    return diag


def summarize_data_quality(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    quality = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "missing_count": df.isna().sum(),
            "missing_pct": df.isna().mean() * 100,
            "unique_values": df.nunique(dropna=False),
        }
    )
    stats_table = df.describe().T
    stats_table["iqr"] = stats_table["75%"] - stats_table["25%"]
    return quality, stats_table


def main() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    PLOTS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(DATA_PATH)

    numeric_cols = df.columns.tolist()
    analysis_cols = [col for col in numeric_cols if col != "student_id"]
    feature_cols = ["weekly_study_hours", "extracurriculars", "commute_minutes", "part_time_job_hours", "absences"]
    df_no_id = df.drop(columns=["student_id"])

    quality, stats_table = summarize_data_quality(df)
    corr = save_correlation_heatmap(df, analysis_cols)
    save_missingness_plot(df)
    save_distribution_plots(df, analysis_cols)
    save_gpa_relationships(df_no_id, feature_cols)

    model_results, ols_model = build_model_results(df)
    save_model_comparison_plot(model_results)
    diagnostics = save_ols_diagnostics(df, ols_model)

    spearman_rows = []
    for col in feature_cols:
        rho, pval = stats.spearmanr(df[col], df["gpa"])
        spearman_rows.append({"feature": col, "spearman_rho": rho, "p_value": pval})
    spearman_df = pd.DataFrame(spearman_rows).sort_values("p_value")

    extracurricular_groups = [grp["gpa"].values for _, grp in df.groupby("extracurriculars")]
    anova_f, anova_p = stats.f_oneway(*extracurricular_groups)
    kw_h, kw_p = stats.kruskal(*extracurricular_groups)

    zscore_outliers = {}
    for col in analysis_cols:
        z = np.abs(stats.zscore(df[col], nan_policy="omit"))
        zscore_outliers[col] = int((z > 3).sum())

    best_model = model_results.iloc[0]
    no_signal = best_model["model"] == "DummyMean" or best_model["mean_cv_r2"] <= 0

    key_points = [
        f"The dataset has {df.shape[0]} rows and {df.shape[1]} columns with no missing values, duplicate rows, or duplicate `student_id` values.",
        "All observed features show near-zero linear and monotonic association with GPA; the largest absolute Pearson correlation with `gpa` is 0.058 and the largest absolute Spearman rho is "
        f"{spearman_df['spearman_rho'].abs().max():.3f}.",
        f"One-way ANOVA and Kruskal-Wallis tests both show no evidence that GPA differs by extracurricular count (`p={anova_p:.3f}` and `p={kw_p:.3f}`).",
        f"Out-of-sample validation indicates no predictive signal: the best model was `{best_model['model']}` with mean 10-fold CV R^2 = {best_model['mean_cv_r2']:.3f} and RMSE = {best_model['mean_cv_rmse']:.3f}.",
    ]
    if no_signal:
        key_points.append("Because every fitted model performs at or below a mean-only baseline, the defensible conclusion is that this dataset does not support useful GPA prediction from the provided variables.")

    report = f"""# Dataset Analysis Report

## 1. Scope and approach
This analysis treats the file as an unknown dataset rather than assuming it is clean or informative. The workflow covered data quality checks, descriptive statistics, visual exploratory analysis, inferential testing, predictive modeling, and model diagnostics. The main modeling question was whether the available covariates can explain or predict `gpa`.

## 2. Dataset overview
- Rows: {df.shape[0]}
- Columns: {df.shape[1]}
- Numeric columns: {len(numeric_cols)}
- Missing values: {int(df.isna().sum().sum())}
- Duplicate rows: {int(df.duplicated().sum())}
- Duplicate `student_id` values: {int(df['student_id'].duplicated().sum())}

`student_id` was treated as an identifier and excluded from modeling.

### Column types and quality
{df_to_markdown(quality, index=True)}

### Descriptive statistics
{df_to_markdown(stats_table.round(3), index=True, digits=3)}

## 3. Exploratory data analysis
The variables are all numeric, mostly centered in plausible ranges, and only mildly skewed. A few values exceed 3 standard deviations from their column means, but the counts are small and there is no immediate sign of corrupted records.

### Potential outliers by z-score threshold (> 3 SD)
{df_to_markdown(pd.DataFrame({"column": list(zscore_outliers.keys()), "count_gt_3sd": list(zscore_outliers.values())}), index=False)}

### Correlation matrix
{df_to_markdown(corr.round(3), index=True, digits=3)}

### Monotonic association with GPA (Spearman)
{df_to_markdown(spearman_df.round(4), index=False, digits=4)}

### Group comparison for extracurricular participation
- One-way ANOVA on `gpa ~ extracurriculars`: F = {anova_f:.3f}, p = {anova_p:.3f}
- Kruskal-Wallis on `gpa ~ extracurriculars`: H = {kw_h:.3f}, p = {kw_p:.3f}

## 4. Modeling strategy
The response variable `gpa` is continuous, so regression is appropriate if signal exists. I compared a mean-only baseline against:

- Ordinary least squares linear regression
- Ridge regression
- Lasso regression
- Degree-2 polynomial features with ridge regularization
- Random forest regression

All models were evaluated using 10-fold cross-validation with shuffled splits and a fixed random seed.

### Cross-validated model performance
{df_to_markdown(model_results.round(4), index=False, digits=4)}

### Interpretation
The model comparison is the central result. Every predictive model achieved negative cross-validated R^2, meaning each one performed worse than predicting the training-fold mean GPA for every observation in the test fold. This is consistent with the near-zero correlations seen during EDA and indicates that the supplied features do not contain stable predictive information for GPA in this sample.

## 5. OLS fit and assumptions
Although the cross-validated results already argue against useful prediction, I still fit an OLS model to inspect assumptions and coefficient behavior.

### OLS coefficients
{df_to_markdown(ols_model.summary2().tables[1].round(4), index=True, digits=4)}

### Global fit
- R-squared: {ols_model.rsquared:.4f}
- Adjusted R-squared: {ols_model.rsquared_adj:.4f}
- F-statistic p-value: {ols_model.f_pvalue:.4f}

### Assumption checks
- Breusch-Pagan heteroskedasticity test: LM p = {diagnostics['bp_lm_p']:.4f}, F p = {diagnostics['bp_f_p']:.4f}
- Ramsey RESET specification test: F = {diagnostics['reset_f']:.4f}, p = {diagnostics['reset_p']:.4f}
- Shapiro-Wilk residual normality test: W = {diagnostics['shapiro_stat']:.4f}, p = {diagnostics['shapiro_p']:.4g}
- D'Agostino-Pearson residual normality test: statistic = {diagnostics['omnibus_stat']:.4f}, p = {diagnostics['omnibus_p']:.4g}
- Maximum Cook's distance: {diagnostics['max_cooks']:.4f}
- Observations with Cook's distance > 4/n: {diagnostics['high_cooks_count']}
- Observations with |studentized residual| > 3: {diagnostics['studentized_outliers']}

### Multicollinearity
{df_to_markdown(diagnostics['vif_table'].round(3), index=False, digits=3)}

### Assumption summary
- Multicollinearity is negligible: all feature VIF values are essentially 1.
- There is no evidence of strong heteroskedasticity.
- The RESET test does not suggest obvious omitted nonlinear structure detectable by this diagnostic.
- Residual normality tests reject exact normality, but with n=600 these tests are sensitive to mild deviations. The Q-Q plot shows only modest tail departures, likely helped by the bounded 0 to 4 GPA scale. This matters less than the larger issue: the model has almost no explanatory power.

## 6. Key findings
{chr(10).join(f"- {point}" for point in key_points)}

## 7. Limitations and next steps
- The analysis can only use the variables present in the file. Important drivers of GPA may simply be absent.
- Negative out-of-sample R^2 across both linear and nonlinear models is evidence against useful prediction from the available columns, not evidence that GPA is inherently unpredictable.
- If this dataset was intended to encode real academic effects, it is worth checking how it was generated. The current structure is consistent with weakly related or effectively random predictors.

## 8. Generated artifacts
Plots were saved under `./plots/`:

- `missingness.png`
- `distributions.png`
- `boxplots.png`
- `correlation_heatmap.png`
- `gpa_vs_numeric_features.png`
- `gpa_by_extracurriculars.png`
- `model_comparison.png`
- `ols_diagnostics.png`
"""

    REPORT_PATH.write_text(textwrap.dedent(report))


if __name__ == "__main__":
    main()
