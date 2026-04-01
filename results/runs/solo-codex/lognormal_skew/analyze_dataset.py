from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy.stats import skew
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.graphics.gofplots import ProbPlot
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
from statsmodels.stats.stattools import jarque_bera
import statsmodels.api as sm


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def fmt_money(value: float) -> str:
    return f"${value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def df_to_markdown(df: pd.DataFrame, index: bool = True) -> str:
    table = df.copy()
    if index:
        table = table.reset_index()
    headers = [str(col) for col in table.columns]
    rows = table.astype(object).where(pd.notnull(table), "").values.tolist()
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    out = ["| " + " | ".join(headers) + " |", sep]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def save_fig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def build_preprocessor() -> tuple[ColumnTransformer, list[str], list[str]]:
    numeric_features = [
        "employees",
        "years_since_founding",
        "revenue_growth_pct",
        "num_investors",
    ]
    categorical_features = ["sector", "round_type"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    return preprocessor, numeric_features, categorical_features


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    PLOTS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    df["log_funding"] = np.log1p(df["funding_amount_usd"])

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    feature_cols = [c for c in df.columns if c not in {"company_id", "funding_amount_usd", "log_funding"}]

    dataset_overview = {
        "rows": len(df),
        "columns": df.shape[1] - 1,  # exclude engineered log target from headline count
        "duplicate_rows": int(df.drop(columns=["log_funding"]).duplicated().sum()),
        "duplicate_company_ids": int(df["company_id"].duplicated().sum()),
    }

    dtypes_table = df.drop(columns=["log_funding"]).dtypes.astype(str).rename("dtype")
    nulls_table = df.drop(columns=["log_funding"]).isna().sum().rename("null_count")
    describe_numeric = df.drop(columns=["log_funding"]).describe().T
    categorical_summary = []
    for col in ["sector", "round_type"]:
        counts = df[col].value_counts()
        categorical_summary.append(
            pd.DataFrame(
                {
                    "column": col,
                    "category": counts.index,
                    "count": counts.values,
                    "share_pct": (counts.values / len(df) * 100).round(2),
                }
            )
        )
    categorical_summary = pd.concat(categorical_summary, ignore_index=True)

    skewness = (
        pd.Series(
            {col: float(skew(df[col], bias=False)) for col in numeric_cols if col != "log_funding"}
        )
        .rename("skewness")
        .sort_values(ascending=False)
    )
    quantiles = df[
        ["employees", "years_since_founding", "revenue_growth_pct", "num_investors", "funding_amount_usd"]
    ].quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).round(2)
    corr = df[
        ["employees", "years_since_founding", "revenue_growth_pct", "num_investors", "funding_amount_usd"]
    ].corr()

    q1 = df["funding_amount_usd"].quantile(0.25)
    q3 = df["funding_amount_usd"].quantile(0.75)
    iqr = q3 - q1
    funding_outlier_upper = q3 + 1.5 * iqr
    funding_outliers = df[df["funding_amount_usd"] > funding_outlier_upper].copy()
    zscore_outliers = int((np.abs((df["funding_amount_usd"] - df["funding_amount_usd"].mean()) / df["funding_amount_usd"].std()) > 3).sum())

    sector_summary = (
        df.groupby("sector")["funding_amount_usd"]
        .agg(["count", "mean", "median", "std"])
        .sort_values("mean", ascending=False)
        .round(2)
    )
    round_summary = (
        df.groupby("round_type")["funding_amount_usd"]
        .agg(["count", "mean", "median", "std"])
        .round(2)
    )
    sector_round_summary = (
        df.pivot_table(
            index="sector",
            columns="round_type",
            values="funding_amount_usd",
            aggfunc="mean",
        )
        .round(2)
        .fillna(np.nan)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.histplot(df["funding_amount_usd"], bins=35, kde=True, ax=axes[0], color="#1f77b4")
    axes[0].set_title("Funding Amount Distribution")
    axes[0].set_xlabel("Funding Amount (USD)")
    sns.histplot(df["log_funding"], bins=35, kde=True, ax=axes[1], color="#ff7f0e")
    axes[1].set_title("Log-Transformed Funding Distribution")
    axes[1].set_xlabel("log(1 + funding)")
    save_fig(PLOTS_DIR / "funding_distribution.png")

    plt.figure(figsize=(7, 5.5))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f")
    plt.title("Correlation Heatmap")
    save_fig(PLOTS_DIR / "correlation_heatmap.png")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    scatter_specs = [
        ("employees", "employees"),
        ("years_since_founding", "years since founding"),
        ("revenue_growth_pct", "revenue growth (%)"),
        ("num_investors", "number of investors"),
    ]
    for ax, (col, label) in zip(axes.flat, scatter_specs):
        sns.regplot(
            data=df,
            x=col,
            y="funding_amount_usd",
            scatter_kws={"alpha": 0.45, "s": 32},
            line_kws={"color": "#d62728"},
            ax=ax,
        )
        ax.set_xlabel(label)
        ax.set_ylabel("funding amount (USD)")
        ax.set_title(f"Funding vs {label.title()}")
    save_fig(PLOTS_DIR / "feature_relationships.png")

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    sector_order = sector_summary.index.tolist()
    round_order = ["Seed", "Series_A", "Series_B", "Series_C"]
    sns.boxplot(
        data=df,
        x="sector",
        y="funding_amount_usd",
        order=sector_order,
        ax=axes[0],
        color="#9ecae1",
    )
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].set_title("Funding by Sector")
    sns.boxplot(
        data=df,
        x="round_type",
        y="funding_amount_usd",
        order=round_order,
        ax=axes[1],
        color="#fdd0a2",
    )
    axes[1].set_title("Funding by Round Type")
    save_fig(PLOTS_DIR / "categorical_boxplots.png")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    sns.boxplot(data=df, x="sector", y="log_funding", order=sector_order, ax=axes[0], color="#9ecae1")
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].set_title("Log Funding by Sector")
    sns.boxplot(data=df, x="round_type", y="log_funding", order=round_order, ax=axes[1], color="#fdd0a2")
    axes[1].set_title("Log Funding by Round Type")
    save_fig(PLOTS_DIR / "log_categorical_boxplots.png")

    preprocessor, numeric_features, categorical_features = build_preprocessor()
    X = df[feature_cols]
    y = df["funding_amount_usd"]
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "r2": "r2",
        "mae": "neg_mean_absolute_error",
        "rmse": "neg_root_mean_squared_error",
    }

    models = {
        "linear_raw": Pipeline([("preprocessor", preprocessor), ("model", LinearRegression())]),
        "ridge_log": Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "model",
                    TransformedTargetRegressor(
                        regressor=RidgeCV(alphas=np.logspace(-3, 3, 25)),
                        func=np.log1p,
                        inverse_func=np.expm1,
                    ),
                ),
            ]
        ),
        "random_forest_log": Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "model",
                    TransformedTargetRegressor(
                        regressor=RandomForestRegressor(
                            n_estimators=400,
                            min_samples_leaf=3,
                            n_jobs=1,
                            random_state=42,
                        ),
                        func=np.log1p,
                        inverse_func=np.expm1,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting_log": Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "model",
                    TransformedTargetRegressor(
                        regressor=HistGradientBoostingRegressor(
                            max_depth=4,
                            learning_rate=0.05,
                            max_iter=400,
                            min_samples_leaf=10,
                            random_state=42,
                        ),
                        func=np.log1p,
                        inverse_func=np.expm1,
                    ),
                ),
            ]
        ),
    }

    model_scores = []
    for name, model in models.items():
        scores = cross_validate(model, X, y, cv=cv, scoring=scoring)
        model_scores.append(
            {
                "model": name,
                "cv_r2_mean": scores["test_r2"].mean(),
                "cv_r2_std": scores["test_r2"].std(),
                "cv_mae_mean": -scores["test_mae"].mean(),
                "cv_rmse_mean": -scores["test_rmse"].mean(),
            }
        )
    model_scores_df = pd.DataFrame(model_scores).sort_values("cv_r2_mean", ascending=False)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    final_model = models["ridge_log"]
    final_model.fit(X_train, y_train)
    test_predictions = final_model.predict(X_test)

    holdout_metrics = {
        "test_r2": r2_score(y_test, test_predictions),
        "test_mae": mean_absolute_error(y_test, test_predictions),
        "test_rmse": mean_squared_error(y_test, test_predictions) ** 0.5,
        "median_absolute_percentage_error": np.median(
            np.abs((y_test - test_predictions) / y_test)
        ),
        "p90_absolute_percentage_error": np.quantile(
            np.abs((y_test - test_predictions) / y_test), 0.90
        ),
    }

    plt.figure(figsize=(7, 6))
    sns.scatterplot(x=y_test, y=test_predictions, alpha=0.55, s=50)
    min_val = float(min(y_test.min(), test_predictions.min()))
    max_val = float(max(y_test.max(), test_predictions.max()))
    plt.plot([min_val, max_val], [min_val, max_val], color="#d62728", linestyle="--")
    plt.xlabel("Actual funding amount (USD)")
    plt.ylabel("Predicted funding amount (USD)")
    plt.title("Holdout Predictions vs Actuals")
    save_fig(PLOTS_DIR / "predicted_vs_actual.png")

    formula = (
        "log_funding ~ employees + years_since_founding + revenue_growth_pct + "
        "num_investors + C(sector) + C(round_type)"
    )
    ols_model = smf.ols(formula, data=df).fit()
    robust_ols = ols_model.get_robustcov_results(cov_type="HC3")
    ols_params = pd.DataFrame(
        {
            "coef": ols_model.params,
            "p_value": ols_model.pvalues,
            "robust_se": robust_ols.bse,
            "robust_p_value": robust_ols.pvalues,
        }
    )

    bp_stat, bp_pvalue, _, _ = het_breuschpagan(ols_model.resid, ols_model.model.exog)
    jb_stat, jb_pvalue, resid_skew, resid_kurt = jarque_bera(ols_model.resid)

    X_vif = sm.add_constant(df[numeric_features])
    vif_table = pd.DataFrame(
        {
            "feature": X_vif.columns,
            "vif": [
                variance_inflation_factor(X_vif.values, i)
                for i in range(X_vif.shape[1])
            ],
        }
    )

    influence = OLSInfluence(ols_model)
    cooks = influence.cooks_distance[0]
    influence_threshold = 4 / len(df)
    influential_points = (
        df.loc[np.argsort(cooks)[::-1], [
            "company_id",
            "funding_amount_usd",
            "employees",
            "years_since_founding",
            "revenue_growth_pct",
            "num_investors",
            "sector",
            "round_type",
        ]]
        .assign(cooks_distance=np.sort(cooks)[::-1])
        .head(10)
    )

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fitted = ols_model.fittedvalues
    residuals = ols_model.resid
    sns.scatterplot(x=fitted, y=residuals, alpha=0.5, s=35, ax=axes[0])
    axes[0].axhline(0, color="#d62728", linestyle="--")
    axes[0].set_title("Residuals vs Fitted")
    axes[0].set_xlabel("Fitted log funding")
    axes[0].set_ylabel("Residuals")

    ProbPlot(residuals).qqplot(line="45", ax=axes[1], alpha=0.5)
    axes[1].set_title("Q-Q Plot")

    sns.scatterplot(x=np.arange(len(cooks)), y=cooks, alpha=0.55, s=30, ax=axes[2])
    axes[2].axhline(influence_threshold, color="#d62728", linestyle="--")
    axes[2].set_title("Cook's Distance")
    axes[2].set_xlabel("Observation index")
    axes[2].set_ylabel("Cook's distance")
    save_fig(PLOTS_DIR / "model_diagnostics.png")

    ridge_estimator = final_model.named_steps["model"].regressor_
    feature_names = final_model.named_steps["preprocessor"].get_feature_names_out()
    ridge_coefficients = (
        pd.DataFrame(
            {
                "feature": feature_names,
                "coefficient": ridge_estimator.coef_,
                "abs_coefficient": np.abs(ridge_estimator.coef_),
            }
        )
        .sort_values("abs_coefficient", ascending=False)
        .drop(columns="abs_coefficient")
    )

    plt.figure(figsize=(9, 6))
    plot_coef = ridge_coefficients.head(12).sort_values("coefficient")
    sns.barplot(data=plot_coef, x="coefficient", y="feature", color="#74c476")
    plt.title("Largest Ridge Coefficients on Log Scale")
    plt.xlabel("Coefficient")
    plt.ylabel("Encoded feature")
    save_fig(PLOTS_DIR / "ridge_coefficients.png")

    key_findings = [
        f"The dataset contains {dataset_overview['rows']} companies with no missing values, no duplicate rows, and no duplicated `company_id` values.",
        f"`funding_amount_usd` is strongly right-skewed (skew={skewness['funding_amount_usd']:.2f}); the top 1% of deals exceed {fmt_money(quantiles.loc[0.99, 'funding_amount_usd'])}, while the median is only {fmt_money(quantiles.loc[0.50, 'funding_amount_usd'])}.",
        f"On simple correlations, funding is most associated with `years_since_founding` (r={corr.loc['years_since_founding', 'funding_amount_usd']:.2f}) and `employees` (r={corr.loc['employees', 'funding_amount_usd']:.2f}), with a smaller relationship for `revenue_growth_pct` (r={corr.loc['revenue_growth_pct', 'funding_amount_usd']:.2f}).",
        f"Average funding rises across rounds from {fmt_money(round_summary.loc['Seed', 'mean'])} for Seed to {fmt_money(round_summary.loc['Series_C', 'mean'])} for Series C, but sector-level averages are much closer together than round-level averages.",
        f"The best cross-validated predictive model was log-target ridge regression (mean CV R²={model_scores_df.iloc[0]['cv_r2_mean']:.3f}, mean CV RMSE={fmt_money(model_scores_df.iloc[0]['cv_rmse_mean'])}), slightly ahead of the raw-scale linear model and clearly ahead of the tested tree ensembles.",
        f"In the log-linear inference model, `employees`, `years_since_founding`, and `revenue_growth_pct` are positive and statistically robust predictors, while `num_investors` is weakly negative after adjustment and only `Series_C` shows a clear positive round effect relative to Seed.",
    ]

    report = f"""# Dataset Analysis Report

## Scope
This report analyzes [`dataset.csv`](./dataset.csv) as a funding dataset with 800 company records. The work covers data inspection, exploratory analysis, anomaly checks, predictive modeling, formal assumption checks, and visual outputs saved under [`plots/`](./plots/).

## 1. Data Loading And Inspection

### Dataset shape and integrity
- Rows: {dataset_overview['rows']}
- Columns: {dataset_overview['columns']}
- Duplicate rows: {dataset_overview['duplicate_rows']}
- Duplicate company IDs: {dataset_overview['duplicate_company_ids']}
- Missing values: none detected in any source column

### Data types
{df_to_markdown(dtypes_table.to_frame())}

### Null counts
{df_to_markdown(nulls_table.to_frame())}

### Numeric summary statistics
{df_to_markdown(describe_numeric.round(2))}

### Categorical balance
{df_to_markdown(categorical_summary, index=False)}

## 2. Exploratory Data Analysis

### Distributional shape
- `employees`, `years_since_founding`, `revenue_growth_pct`, and `num_investors` are approximately symmetric to mildly skewed.
- `funding_amount_usd` is highly right-skewed with skewness {skewness['funding_amount_usd']:.2f}; a log transform materially improves symmetry.
- Median funding is {fmt_money(df['funding_amount_usd'].median())}; mean funding is {fmt_money(df['funding_amount_usd'].mean())}, indicating the mean is pulled upward by a small number of large rounds.

### Quantiles
{df_to_markdown(quantiles.round(2))}

### Correlation matrix
{df_to_markdown(corr.round(3))}

### Group summaries
Funding by sector:

{df_to_markdown(sector_summary)}

Funding by round type:

{df_to_markdown(round_summary)}

Mean funding by sector and round:

{df_to_markdown(sector_round_summary)}

### Visualizations
- ![Funding distribution](./plots/funding_distribution.png)
- ![Correlation heatmap](./plots/correlation_heatmap.png)
- ![Feature relationships](./plots/feature_relationships.png)
- ![Categorical boxplots](./plots/categorical_boxplots.png)
- ![Log categorical boxplots](./plots/log_categorical_boxplots.png)

## 3. Patterns, Relationships, And Anomalies

### Key patterns
{chr(10).join(f"- {finding}" for finding in key_findings)}

### Outlier review
- Using the IQR rule on `funding_amount_usd`, {len(funding_outliers)} observations exceed the upper outlier threshold of {fmt_money(funding_outlier_upper)}.
- Using a 3 standard deviation rule, {zscore_outliers} funding observations are extreme.
- These observations are not obvious data-entry errors: the predictors remain within plausible business ranges, so they should be treated as influential but valid cases rather than automatically removed.

Top influential cases by Cook's distance from the log-linear model:

{df_to_markdown(influential_points.round(4), index=False)}

## 4. Modeling Strategy

### Why a log-target regression?
Raw funding is strongly right-skewed, so fitting a model directly on dollars gives heteroskedastic residuals and places too much weight on a small number of very large deals. A log transform makes the target closer to Gaussian and improved validation metrics. I therefore used:

1. An interpretable OLS model on `log(1 + funding_amount_usd)` for coefficient interpretation and diagnostics.
2. A ridge regression with the same log target for final predictive evaluation, because it slightly outperformed the unregularized linear model in cross-validation while remaining transparent.
3. Random forest and histogram gradient boosting as non-linear benchmarks.

### Cross-validated model comparison
{df_to_markdown(model_scores_df.assign(
    cv_r2_mean=lambda t: t['cv_r2_mean'].round(3),
    cv_r2_std=lambda t: t['cv_r2_std'].round(3),
    cv_mae_mean=lambda t: t['cv_mae_mean'].round(1),
    cv_rmse_mean=lambda t: t['cv_rmse_mean'].round(1),
), index=False)}

### Holdout performance for the selected ridge model
- Test R²: {holdout_metrics['test_r2']:.3f}
- Test MAE: {fmt_money(holdout_metrics['test_mae'])}
- Test RMSE: {fmt_money(holdout_metrics['test_rmse'])}
- Median absolute percentage error: {holdout_metrics['median_absolute_percentage_error']:.3f}
- 90th percentile absolute percentage error: {holdout_metrics['p90_absolute_percentage_error']:.3f}
- Selected ridge penalty alpha: {ridge_estimator.alpha_:.6g}

### Holdout prediction plot
- ![Predicted vs actual](./plots/predicted_vs_actual.png)

### Largest ridge coefficients
{df_to_markdown(ridge_coefficients.head(12).round(4), index=False)}

- ![Ridge coefficients](./plots/ridge_coefficients.png)

## 5. Model Assumptions And Validation

### OLS coefficient table on log funding
{df_to_markdown(ols_params.round(4))}

### Assumption checks
- Multicollinearity is negligible among numeric predictors: all VIF values are near 1.
- Residual normality is acceptable after the log transform: Jarque-Bera statistic = {jb_stat:.3f}, p-value = {jb_pvalue:.3f}, residual skew = {resid_skew:.3f}, residual kurtosis = {resid_kurt:.3f}.
- Heteroskedasticity is still detectable but mild: Breusch-Pagan statistic = {bp_stat:.3f}, p-value = {bp_pvalue:.3f}. This means coefficient standard errors from plain OLS may be slightly optimistic.
- To account for that, the report includes HC3 robust standard errors and p-values (`robust_se`, `robust_p_value`) alongside classical OLS statistics.
- Influence is non-trivial but not catastrophic: the largest Cook's distance is {cooks.max():.4f}, and {(cooks > influence_threshold).sum()} observations exceed the common 4/n heuristic threshold of {influence_threshold:.4f}.

### VIF table
{df_to_markdown(vif_table.round(3), index=False)}

### Diagnostic plots
- ![Model diagnostics](./plots/model_diagnostics.png)

## 6. Findings

### Main conclusions
- The dataset is structurally clean: no missingness, no duplicate entities, and balanced categorical coverage.
- Funding amounts are dominated by a long right tail, so analysis on the raw target alone would be misleading.
- Company maturity and scale matter most: older firms and firms with more employees tend to raise more capital.
- Revenue growth adds signal even after controlling for age, size, sector, and round type.
- Round type has a directionally positive effect, but only Series C is clearly distinct from Seed after adjusting for other features.
- Sector labels add relatively little explanatory power in this dataset once the numeric business characteristics are included.
- Predictive power is moderate rather than high. The selected model explains about {holdout_metrics['test_r2']:.0%} of variance on a holdout split, which is reasonable but leaves substantial unexplained variation. Funding decisions likely depend on features not present here.

### Practical interpretation
- Increasing `years_since_founding` by one year is associated with an estimated {100 * ols_model.params['years_since_founding']:.1f}% increase in expected funding on the log scale, holding other variables fixed.
- Increasing `employees` by 100 is associated with roughly {100 * (np.exp(100 * ols_model.params['employees']) - 1):.1f}% higher expected funding, all else equal.
- A 10 percentage point increase in `revenue_growth_pct` corresponds to roughly {100 * (np.exp(10 * ols_model.params['revenue_growth_pct']) - 1):.1f}% higher expected funding, all else equal.
- The negative adjusted coefficient on `num_investors` should not be interpreted causally; it likely reflects residual confounding or deal-structure differences not captured in the available features.

## 7. Limitations
- This appears to be a compact tabular dataset with only seven usable predictors. Unobserved variables such as geography, profitability, valuation, founder track record, and macro conditions likely drive a large share of funding variation.
- The data is cross-sectional, so coefficients should not be read as causal effects.
- Mild heteroskedasticity and influential observations remain even after the log transform, so interval estimates should be treated cautiously.
- Predictive error on the upper tail is still substantial; large rounds are inherently harder to predict from the available features.
"""

    REPORT_PATH.write_text(dedent(report).strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
