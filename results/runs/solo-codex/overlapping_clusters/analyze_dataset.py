from __future__ import annotations

import re
from inspect import cleandoc
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def fmt_float(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def table_from_frame(df: pd.DataFrame, digits: int = 4) -> str:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(lambda x: round(float(x), digits))
    return out.to_string(index=True)


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def make_histograms(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 3, figsize=(15, 11))
    axes = axes.flatten()
    for ax, col in zip(axes, df.columns):
        sns.histplot(df[col], kde=True, ax=ax, color="#2c7fb8", edgecolor="white")
        ax.set_title(col)
    for ax in axes[len(df.columns) :]:
        ax.axis("off")
    fig.suptitle("Distributions of Dataset Variables", y=1.02, fontsize=14)
    savefig(PLOTS_DIR / "distributions.png")


def make_boxplots(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 3, figsize=(15, 11))
    axes = axes.flatten()
    for ax, col in zip(axes, df.columns):
        sns.boxplot(y=df[col], ax=ax, color="#9ecae1", fliersize=3)
        ax.set_title(col)
        ax.set_ylabel("")
    for ax in axes[len(df.columns) :]:
        ax.axis("off")
    fig.suptitle("Boxplots for Outlier Screening", y=1.02, fontsize=14)
    savefig(PLOTS_DIR / "boxplots.png")


def make_heatmap(df: pd.DataFrame) -> None:
    corr = df.corr(numeric_only=True)
    plt.figure(figsize=(9, 7))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f", square=True)
    plt.title("Pearson Correlation Heatmap")
    savefig(PLOTS_DIR / "correlation_heatmap.png")


def make_gpa_relationships(df: pd.DataFrame) -> None:
    predictors = [c for c in df.columns if c != "gpa"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    for ax, col in zip(axes, predictors):
        sns.regplot(
            data=df,
            x=col,
            y="gpa",
            lowess=True,
            scatter_kws={"alpha": 0.55, "s": 24},
            line_kws={"color": "#d95f0e"},
            ax=ax,
        )
        ax.set_title(f"GPA vs {col}")
    fig.suptitle("GPA Relationships by Predictor", y=1.02, fontsize=14)
    savefig(PLOTS_DIR / "gpa_relationships.png")


def make_id_plot(df: pd.DataFrame) -> None:
    plt.figure(figsize=(11, 5))
    sns.regplot(
        data=df,
        x="student_id",
        y="gpa",
        lowess=True,
        scatter_kws={"alpha": 0.5, "s": 20},
        line_kws={"color": "#cb181d", "linewidth": 2},
    )
    plt.title("GPA vs Student ID")
    plt.xlabel("student_id")
    plt.ylabel("gpa")
    savefig(PLOTS_DIR / "gpa_vs_student_id.png")


def make_residual_plots(y_true: pd.Series, y_pred: np.ndarray, residuals: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    sns.scatterplot(x=y_pred, y=residuals, ax=axes[0, 0], s=28, alpha=0.7)
    axes[0, 0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0, 0].set_title("Residuals vs Fitted")
    axes[0, 0].set_xlabel("Predicted GPA")
    axes[0, 0].set_ylabel("Residual")

    sm.qqplot(residuals, line="45", ax=axes[0, 1], fit=True)
    axes[0, 1].set_title("Residual Q-Q Plot")

    sns.histplot(residuals, kde=True, ax=axes[1, 0], color="#31a354", edgecolor="white")
    axes[1, 0].set_title("Residual Distribution")

    sns.scatterplot(x=y_true, y=y_pred, ax=axes[1, 1], s=28, alpha=0.7)
    lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    axes[1, 1].plot(lims, lims, linestyle="--", color="black")
    axes[1, 1].set_title("Predicted vs Observed")
    axes[1, 1].set_xlabel("Observed GPA")
    axes[1, 1].set_ylabel("Predicted GPA")

    fig.suptitle("Cross-Validated Linear Model Diagnostics (No ID)", y=1.02, fontsize=14)
    savefig(PLOTS_DIR / "model_diagnostics.png")


def build_models(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float], pd.DataFrame]:
    y = df["gpa"]
    features_all = [c for c in df.columns if c != "gpa"]
    features_no_id = [c for c in features_all if c != "student_id"]

    cv = KFold(n_splits=10, shuffle=True, random_state=42)
    scoring = {
        "r2": "r2",
        "rmse": "neg_root_mean_squared_error",
        "mae": "neg_mean_absolute_error",
    }

    rows = []
    fitted = {}
    for feature_set_name, features in (("with_id", features_all), ("no_id", features_no_id)):
        X = df[features]
        prep_scaled = ColumnTransformer(
            [("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), features)]
        )
        prep_plain = ColumnTransformer([("num", SimpleImputer(strategy="median"), features)])
        models = {
            "dummy_mean": DummyRegressor(strategy="mean"),
            "linear": Pipeline([("prep", prep_scaled), ("model", LinearRegression())]),
            "ridge": Pipeline([("prep", prep_scaled), ("model", RidgeCV(alphas=np.logspace(-3, 3, 25)))]),
            "random_forest": Pipeline(
                [
                    ("prep", prep_plain),
                    ("model", RandomForestRegressor(n_estimators=500, random_state=42, min_samples_leaf=5)),
                ]
            ),
        }
        for model_name, model in models.items():
            scores = cross_validate(model, X, y, cv=cv, scoring=scoring)
            rows.append(
                {
                    "feature_set": feature_set_name,
                    "model": model_name,
                    "cv_r2_mean": scores["test_r2"].mean(),
                    "cv_r2_sd": scores["test_r2"].std(),
                    "cv_rmse_mean": -scores["test_rmse"].mean(),
                    "cv_mae_mean": -scores["test_mae"].mean(),
                }
            )
            fitted[(feature_set_name, model_name)] = (model, X)

    model_results = pd.DataFrame(rows).sort_values(["feature_set", "cv_rmse_mean", "cv_r2_mean"]).reset_index(drop=True)

    no_id_linear = fitted[("no_id", "linear")][0]
    X_no_id = fitted[("no_id", "linear")][1]
    cv_predictions = cross_val_predict(no_id_linear, X_no_id, y, cv=cv)
    residuals = y.to_numpy() - cv_predictions
    metrics = {
        "r2": r2_score(y, cv_predictions),
        "rmse": mean_squared_error(y, cv_predictions) ** 0.5,
        "mae": mean_absolute_error(y, cv_predictions),
    }
    make_residual_plots(y, cv_predictions, residuals)

    rf_model = fitted[("no_id", "random_forest")][0]
    rf_model.fit(X_no_id, y)
    perm = permutation_importance(rf_model, X_no_id, y, n_repeats=25, random_state=42)
    importance_df = pd.DataFrame(
        {"feature": X_no_id.columns, "importance_mean": perm.importances_mean, "importance_std": perm.importances_std}
    ).sort_values("importance_mean", ascending=False)

    return model_results, X_no_id, metrics, importance_df


def ols_diagnostics(df: pd.DataFrame, features: list[str]) -> dict[str, object]:
    X = sm.add_constant(df[features])
    y = df["gpa"]
    model = sm.OLS(y, X).fit()
    influence = OLSInfluence(model)
    jb_stat, jb_p, skew, kurtosis = jarque_bera(model.resid)
    bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, model.model.exog)
    reset_res = linear_reset(model, power=2, use_f=True)
    vif = pd.Series(
        [variance_inflation_factor(X.values, i) for i in range(1, X.shape[1])],
        index=features,
        name="VIF",
    )
    top_cooks = pd.DataFrame(
        {
            "index": np.arange(len(df)),
            "student_id": df["student_id"],
            "cooks_distance": influence.cooks_distance[0],
            "standardized_resid": influence.resid_studentized_internal,
            "leverage": influence.hat_matrix_diag,
        }
    ).sort_values("cooks_distance", ascending=False).head(10)

    return {
        "model": model,
        "jb_stat": jb_stat,
        "jb_p": jb_p,
        "skew": skew,
        "kurtosis": kurtosis,
        "bp_stat": bp_stat,
        "bp_p": bp_p,
        "dw": durbin_watson(model.resid),
        "reset_f": float(reset_res.fvalue),
        "reset_p": float(reset_res.pvalue),
        "vif": vif,
        "top_cooks": top_cooks,
    }


def summarize_correlations(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        if col == "gpa":
            continue
        pearson = df[[col, "gpa"]].corr().iloc[0, 1]
        spearman, spearman_p = spearmanr(df[col], df["gpa"])
        rows.append(
            {
                "feature": col,
                "pearson_r": pearson,
                "spearman_rho": spearman,
                "spearman_p": spearman_p,
            }
        )
    return pd.DataFrame(rows).sort_values("pearson_r", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")

    df = pd.read_csv(DATA_PATH)

    make_histograms(df)
    make_boxplots(df)
    make_heatmap(df)
    make_gpa_relationships(df)
    make_id_plot(df)

    basic_info = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "null_count": df.isna().sum(),
            "null_pct": df.isna().mean() * 100,
            "n_unique": df.nunique(),
        }
    )
    summary_stats = df.describe().T
    corr_summary = summarize_correlations(df)
    model_results, X_no_id, cv_metrics, importance_df = build_models(df)

    iqr_rows = []
    for col in df.columns:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = ((df[col] < lower) | (df[col] > upper)).sum()
        iqr_rows.append({"feature": col, "iqr_outlier_count": int(count), "lower_bound": lower, "upper_bound": upper})
    iqr_df = pd.DataFrame(iqr_rows).set_index("feature")

    gpa_ceiling_count = int((df["gpa"] == 4.0).sum())
    gpa_ceiling_pct = 100 * (df["gpa"] == 4.0).mean()

    no_id_diag = ols_diagnostics(df, list(X_no_id.columns))
    with_id_diag = ols_diagnostics(df, ["student_id", *list(X_no_id.columns)])

    best_rows = model_results.sort_values(["feature_set", "cv_rmse_mean"]).groupby("feature_set").head(1)

    report = (
        cleandoc(
            f"""
            # Dataset Analysis Report

            ## Scope
            This report analyzes `dataset.csv` as a student-performance dataset. The response variable treated as most meaningful for modeling is `gpa`. `student_id` was inspected but treated as an identifier rather than a legitimate academic predictor.

            ## 1. Data Loading and Inspection
            - Rows: {len(df)}
            - Columns: {df.shape[1]}
            - Missing values: {int(df.isna().sum().sum())}
            - Duplicate rows: {int(df.duplicated().sum())}
            - Duplicate `student_id` values: {int(df["student_id"].duplicated().sum())}
            - GPA range: {df["gpa"].min():.2f} to {df["gpa"].max():.2f}
            - GPA ceiling at 4.0: {gpa_ceiling_count} rows ({gpa_ceiling_pct:.1f}%)

            ### Schema Summary
            ```text
            {table_from_frame(basic_info)}
            ```

            ### Descriptive Statistics
            ```text
            {table_from_frame(summary_stats)}
            ```

            ### Outlier Screening by IQR Rule
            ```text
            {table_from_frame(iqr_df)}
            ```

            ## 2. Exploratory Data Analysis
            Saved plots:
            - `plots/distributions.png`
            - `plots/boxplots.png`
            - `plots/correlation_heatmap.png`
            - `plots/gpa_relationships.png`
            - `plots/gpa_vs_student_id.png`
            - `plots/model_diagnostics.png`

            ### Correlation Summary with GPA
            ```text
            {table_from_frame(corr_summary.set_index("feature"))}
            ```

            ### EDA Findings
            1. The dataset is structurally clean: no missing values, no duplicate rows, and no duplicate IDs.
            2. Every field is numeric. `student_id` is a unique sequence from 1 to 600 and should be considered metadata, not behavior.
            3. The substantive predictors (`weekly_study_hours`, `extracurriculars`, `commute_minutes`, `part_time_job_hours`, `absences`) show near-zero Pearson and Spearman association with GPA.
            4. `student_id` has the largest correlation with GPA (Pearson {corr_summary.loc[corr_summary["feature"].eq("student_id"), "pearson_r"].iat[0]:.3f}), which is not a credible real-world mechanism and therefore suggests leakage, synthetic structure, or a chance artifact.
            5. GPA has a visible upper bound effect: 11.0% of observations are exactly 4.0, so ceiling behavior is present.
            6. IQR screening flags only a small number of high-end observations in study hours, commute, job hours, and absences. These are plausible extremes, not clear data-entry errors.

            ## 3. Modeling Strategy
            Two modeling scenarios were evaluated:
            - `with_id`: includes every column except `gpa`
            - `no_id`: excludes `student_id`, which is the realistic modeling setup

            Models compared under 10-fold shuffled cross-validation:
            - Mean-only baseline
            - Linear regression
            - Ridge regression
            - Random forest regression

            ### Cross-Validated Performance
            ```text
            {table_from_frame(model_results)}
            ```

            Best model in each feature set:
            ```text
            {table_from_frame(best_rows.set_index(["feature_set", "model"]))}
            ```

            ### Interpretation of Model Performance
            1. Excluding `student_id`, all models perform at or worse than the mean baseline. That means the observed features contain little usable predictive signal for GPA.
            2. Including `student_id` improves RMSE only trivially, and cross-validated R^2 remains negative. This confirms the identifier does not yield a useful predictive model even if it is statistically associated with GPA.
            3. The cross-validated linear model without ID has:
               - R^2 = {cv_metrics["r2"]:.4f}
               - RMSE = {cv_metrics["rmse"]:.4f}
               - MAE = {cv_metrics["mae"]:.4f}
            4. Random forest does not uncover hidden nonlinear structure; its `no_id` performance is materially worse than the baseline.

            ### Permutation Importance for Random Forest (`no_id`)
            ```text
            {table_from_frame(importance_df.set_index("feature"))}
            ```

            This ranking is in-sample only. It can show which variables the fitted forest split on most often, but it should not be mistaken for evidence of useful predictive signal because the same model fails under cross-validation.

            ## 4. Linear Model Assumption Checks
            Assumption checks were run on OLS models with and without `student_id`.

            ### OLS Without `student_id`
            - Breusch-Pagan p-value: {no_id_diag["bp_p"]:.4f}
            - Jarque-Bera p-value: {no_id_diag["jb_p"]:.4f}
            - Durbin-Watson: {no_id_diag["dw"]:.4f}
            - Ramsey RESET p-value: {no_id_diag["reset_p"]:.4f}

            Coefficients:
            ```text
            {no_id_diag["model"].summary2().tables[1].round(4).to_string()}
            ```

            VIF:
            ```text
            {no_id_diag["vif"].round(4).to_string()}
            ```

            Largest Cook's distances:
            ```text
            {table_from_frame(no_id_diag["top_cooks"].set_index("index"))}
            ```

            ### OLS With `student_id`
            - Breusch-Pagan p-value: {with_id_diag["bp_p"]:.4f}
            - Jarque-Bera p-value: {with_id_diag["jb_p"]:.4f}
            - Durbin-Watson: {with_id_diag["dw"]:.4f}
            - Ramsey RESET p-value: {with_id_diag["reset_p"]:.4f}

            Coefficients:
            ```text
            {with_id_diag["model"].summary2().tables[1].round(4).to_string()}
            ```

            VIF:
            ```text
            {with_id_diag["vif"].round(4).to_string()}
            ```

            Largest Cook's distances:
            ```text
            {table_from_frame(with_id_diag["top_cooks"].set_index("index"))}
            ```

            ### Assumption Assessment
            1. Multicollinearity is negligible; all VIF values are approximately 1.
            2. Residual normality is not the primary concern here. Even if residual diagnostics are acceptable, the coefficients are near zero and predictive performance is poor.
            3. The key model risk is not assumption violation but signal absence: the dataset does not support a meaningful GPA prediction model from the available non-ID variables.
            4. The significant `student_id` coefficient should not be interpreted substantively. It is likely an artifact and should not be used for decision-making.

            ## 5. Key Patterns, Relationships, and Anomalies
            1. The dataset appears clean but weakly informative.
            2. The main anomaly is an implausible relationship between GPA and `student_id`.
            3. Common-sense academic drivers such as study hours and absences do not show detectable signal here, which is unusual and may indicate synthetic data, omitted variables, or intentionally noisy generation.
            4. Because GPA is capped at 4.0, a censored or ordinal formulation could be argued in a richer dataset. In this dataset, that change would not solve the signal problem.

            ## 6. Conclusion
            This dataset supports descriptive analysis but does not support a strong predictive model of GPA from the observed behavioral variables. The only notable association is with `student_id`, which should be treated as non-causal and likely spurious. The rigorous conclusion is therefore negative: after checking data quality, visual structure, cross-validated performance, and OLS assumptions, there is no evidence that the available substantive predictors explain GPA in a practically useful way.

            ## 7. Recommendations
            1. Drop `student_id` from any downstream modeling pipeline.
            2. Collect more meaningful covariates if GPA prediction is the goal, such as prior GPA, course load, socioeconomic indicators, attendance detail, major, exam scores, and semester information.
            3. If this is synthetic data, review the generation logic because the identifier appears more informative than the behavioral features.
            """
        )
        + "\n"
    )
    report = re.sub(r"(?m)^ {12}", "", report)

    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
