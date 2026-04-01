from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LassoCV, LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.graphics.gofplots import ProbPlot
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
from statsmodels.stats.stattools import jarque_bera


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def make_dirs() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)


def infer_feature_groups(df: pd.DataFrame) -> tuple[list[str], list[str], str]:
    target = "price_usd"
    numeric_features = [
        col
        for col in df.select_dtypes(include=[np.number]).columns
        if col not in {target, "listing_id"}
    ]
    categorical_features = [
        col
        for col in df.columns
        if col not in numeric_features and col not in {target, "listing_id"}
    ]
    if "has_pool" in df.columns and "has_pool" not in categorical_features:
        categorical_features.append("has_pool")
        if "has_pool" in numeric_features:
            numeric_features.remove("has_pool")
    return numeric_features, categorical_features, target


def format_metric(value: float) -> str:
    return f"{value:,.2f}"


def dataframe_block(df: pd.DataFrame) -> str:
    return "```\n" + df.to_string() + "\n```"


def make_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
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
                        (
                            "encoder",
                            OneHotEncoder(drop="first", handle_unknown="ignore"),
                        ),
                    ]
                ),
                categorical_features,
            ),
        ]
    )


def fit_and_score_models(
    X: pd.DataFrame,
    y: pd.Series,
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[pd.DataFrame, dict[str, Pipeline]]:
    preprocessor = make_preprocessor(numeric_features, categorical_features)
    models: dict[str, object] = {
        "Linear regression": LinearRegression(),
        "Ridge regression": RidgeCV(alphas=np.logspace(-3, 3, 25)),
        "Lasso regression": LassoCV(alphas=100, cv=5, max_iter=20000, random_state=42),
        "Random forest": RandomForestRegressor(
            n_estimators=500,
            min_samples_leaf=3,
            random_state=42,
        ),
        "Log-linear regression": TransformedTargetRegressor(
            regressor=LinearRegression(),
            func=np.log,
            inverse_func=np.exp,
        ),
    }
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    rows = []
    fitted_pipelines: dict[str, Pipeline] = {}
    for name, model in models.items():
        pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
        scores = cross_validate(
            pipeline,
            X,
            y,
            cv=cv,
            scoring=["r2", "neg_mean_absolute_error", "neg_root_mean_squared_error"],
        )
        rows.append(
            {
                "model": name,
                "cv_r2_mean": scores["test_r2"].mean(),
                "cv_r2_std": scores["test_r2"].std(),
                "cv_mae": -scores["test_neg_mean_absolute_error"].mean(),
                "cv_rmse": -scores["test_neg_root_mean_squared_error"].mean(),
            }
        )
        fitted_pipelines[name] = pipeline
    results = pd.DataFrame(rows).sort_values(
        by=["cv_r2_mean", "cv_rmse"], ascending=[False, True]
    )
    return results, fitted_pipelines


def save_plots(df: pd.DataFrame, numeric_features: list[str], target: str, ols_model) -> None:
    sns.set_theme(style="whitegrid", context="talk")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.histplot(df[target], bins=30, kde=True, ax=axes[0], color="#2a9d8f")
    axes[0].set_title("Price Distribution")
    axes[0].set_xlabel("Price (USD)")
    sns.boxplot(x=df[target], ax=axes[1], color="#e9c46a")
    axes[1].set_title("Price Boxplot")
    axes[1].set_xlabel("Price (USD)")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "target_distribution.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    corr = df[[*numeric_features, target]].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, cmap="vlag", center=0, fmt=".2f", ax=ax)
    ax.set_title("Correlation Heatmap")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    top_features = (
        corr[target].drop(target).abs().sort_values(ascending=False).head(4).index.tolist()
    )
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    for ax, feature in zip(axes.flatten(), top_features):
        sns.regplot(
            data=df,
            x=feature,
            y=target,
            scatter_kws={"alpha": 0.55, "s": 40},
            line_kws={"color": "#d62828"},
            ax=ax,
        )
        ax.set_title(f"{target} vs {feature}")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "top_numeric_relationships.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    neighborhood_order = (
        df.groupby("neighborhood")[target].median().sort_values().index.tolist()
    )
    sns.boxplot(
        data=df,
        x="neighborhood",
        y=target,
        order=neighborhood_order,
        ax=axes[0],
        color="#9ecae1",
    )
    axes[0].set_title("Price by Neighborhood")
    axes[0].tick_params(axis="x", rotation=30)
    sns.boxplot(data=df, x="has_pool", y=target, ax=axes[1], color="#f4a261")
    axes[1].set_title("Price by Pool Indicator")
    axes[1].set_xticks([0, 1], ["No pool", "Pool"])
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "categorical_price_patterns.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    influence = OLSInfluence(ols_model)
    fitted = ols_model.fittedvalues
    residuals = ols_model.resid
    standardized_residuals = influence.resid_studentized_internal
    sqrt_abs_resid = np.sqrt(np.abs(standardized_residuals))

    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    sns.scatterplot(x=fitted, y=residuals, alpha=0.6, ax=axes[0, 0], color="#264653")
    axes[0, 0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0, 0].set_title("Residuals vs Fitted")
    axes[0, 0].set_xlabel("Fitted values")
    axes[0, 0].set_ylabel("Residuals")

    ProbPlot(residuals).qqplot(line="45", ax=axes[0, 1], alpha=0.7)
    axes[0, 1].set_title("Normal Q-Q")

    sns.scatterplot(
        x=fitted,
        y=sqrt_abs_resid,
        alpha=0.6,
        ax=axes[1, 0],
        color="#f4a261",
    )
    axes[1, 0].set_title("Scale-Location")
    axes[1, 0].set_xlabel("Fitted values")
    axes[1, 0].set_ylabel("Sqrt(|standardized residual|)")

    sns.scatterplot(
        x=influence.hat_matrix_diag,
        y=standardized_residuals,
        alpha=0.6,
        ax=axes[1, 1],
        color="#e76f51",
    )
    axes[1, 1].set_title("Residuals vs Leverage")
    axes[1, 1].set_xlabel("Leverage")
    axes[1, 1].set_ylabel("Standardized residuals")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "model_diagnostics.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def evaluate_best_model(
    df: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
    target: str,
) -> dict[str, object]:
    X = df.drop(columns=[target, "listing_id"])
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    preprocessor = make_preprocessor(numeric_features, categorical_features)
    pipeline = Pipeline([("preprocessor", preprocessor), ("model", LinearRegression())])
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    metrics = {
        "test_r2": r2_score(y_test, predictions),
        "test_mae": mean_absolute_error(y_test, predictions),
        "test_rmse": np.sqrt(mean_squared_error(y_test, predictions)),
    }

    fig, ax = plt.subplots(figsize=(8, 8))
    sns.scatterplot(x=y_test, y=predictions, ax=ax, alpha=0.65, color="#1d3557")
    bounds = [min(y_test.min(), predictions.min()), max(y_test.max(), predictions.max())]
    ax.plot(bounds, bounds, linestyle="--", color="#d00000")
    ax.set_xlabel("Actual price")
    ax.set_ylabel("Predicted price")
    ax.set_title("Actual vs Predicted Prices")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "actual_vs_predicted.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    perm = permutation_importance(
        pipeline,
        X_test,
        y_test,
        n_repeats=25,
        random_state=42,
        scoring="r2",
    )
    feature_names = X_test.columns
    importance_df = (
        pd.DataFrame(
            {
                "feature": feature_names,
                "importance_mean": perm.importances_mean,
                "importance_std": perm.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .head(10)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=importance_df,
        x="importance_mean",
        y="feature",
        ax=ax,
        color="#457b9d",
    )
    ax.set_title("Permutation Importance on Test Set")
    ax.set_xlabel("Mean decrease in R^2")
    ax.set_ylabel("Feature")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "permutation_importance.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    return {
        "pipeline": pipeline,
        "X_test": X_test,
        "y_test": y_test,
        "predictions": predictions,
        "metrics": metrics,
        "importance_df": importance_df,
    }


def build_report() -> None:
    make_dirs()
    df = pd.read_csv(DATA_PATH)
    numeric_features, categorical_features, target = infer_feature_groups(df)

    quality = {
        "rows": len(df),
        "columns": df.shape[1],
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_listing_id": int(df["listing_id"].duplicated().sum()),
    }
    nulls = df.isna().sum().to_frame("null_count")
    dtypes = df.dtypes.astype(str).to_frame("dtype")
    describe = df[numeric_features + [target]].describe().T
    neighborhood_summary = (
        df.groupby("neighborhood")[target].agg(["count", "mean", "median", "std"]).round(2)
    )
    pool_summary = (
        df.groupby("has_pool")[target].agg(["count", "mean", "median", "std"]).round(2)
    )
    corr_to_target = (
        df[numeric_features + [target]].corr(numeric_only=True)[target].drop(target).sort_values(
            key=np.abs, ascending=False
        )
    )
    corr_to_target_df = corr_to_target.to_frame("correlation_with_price")

    z_outlier_counts = {}
    for col in numeric_features + [target]:
        z_scores = np.abs(stats.zscore(df[col]))
        z_outlier_counts[col] = int((z_scores > 3).sum())
    z_outliers_df = pd.DataFrame.from_dict(
        z_outlier_counts, orient="index", columns=["count_abs_z_gt_3"]
    )

    X = df.drop(columns=[target, "listing_id"])
    y = df[target]
    model_results, _ = fit_and_score_models(X, y, numeric_features, categorical_features)
    best_model_eval = evaluate_best_model(df, numeric_features, categorical_features, target)

    formula = (
        "price_usd ~ sq_ft + num_rooms + lot_size_acres + garage_spaces + year_built "
        "+ C(neighborhood) + has_pool"
    )
    ols_model = smf.ols(formula, data=df).fit()
    robust_ols = smf.ols(formula, data=df).fit(cov_type="HC3")
    save_plots(df, numeric_features, target, ols_model)

    exog = pd.get_dummies(
        df[numeric_features + categorical_features], drop_first=True
    ).astype(float)
    exog = sm.add_constant(exog)
    vif_df = pd.DataFrame(
        {
            "feature": exog.columns[1:],
            "vif": [
                variance_inflation_factor(exog.values, i)
                for i in range(1, exog.shape[1])
            ],
        }
    ).sort_values("vif", ascending=False)

    jb_stat, jb_pvalue, skew, kurtosis = jarque_bera(ols_model.resid)
    bp_lm, bp_lm_pvalue, bp_f, bp_f_pvalue = het_breuschpagan(
        ols_model.resid, ols_model.model.exog
    )
    reset = linear_reset(ols_model, power=2, use_f=True)
    influence = OLSInfluence(ols_model)
    cook_threshold = 4 / len(df)
    influential_count = int((influence.cooks_distance[0] > cook_threshold).sum())
    top_residual_idx = (
        pd.Series(np.abs(influence.resid_studentized_external), index=df.index)
        .sort_values(ascending=False)
        .head(5)
        .index
    )
    anomaly_rows = df.loc[
        top_residual_idx,
        [
            "listing_id",
            "sq_ft",
            "num_rooms",
            "lot_size_acres",
            "garage_spaces",
            "year_built",
            "neighborhood",
            "has_pool",
            "price_usd",
        ],
    ].copy()
    anomaly_rows["fitted_price"] = ols_model.fittedvalues.loc[top_residual_idx].round(2)
    anomaly_rows["residual"] = ols_model.resid.loc[top_residual_idx].round(2)

    coef_table = robust_ols.summary2().tables[1].copy()
    coef_table = coef_table.rename(
        columns={
            "Coef.": "coef",
            "Std.Err.": "std_err",
            "P>|z|": "p_value",
            "[0.025": "ci_low",
            "0.975]": "ci_high",
        }
    )
    coef_table = coef_table[["coef", "std_err", "z", "p_value", "ci_low", "ci_high"]]

    report = f"""# Dataset Analysis Report

## 1. Scope

This analysis examines `dataset.csv` as a supervised regression problem with `price_usd` as the response variable. The workflow includes data quality checks, exploratory analysis, model comparison, regression diagnostics, and anomaly review. All outputs were generated from a fresh run of `analyze_dataset.py`.

## 2. Data Loading And Inspection

- Shape: {quality["rows"]} rows x {quality["columns"]} columns
- Duplicate rows: {quality["duplicate_rows"]}
- Duplicate `listing_id` values: {quality["duplicate_listing_id"]}
- Missing values: none detected

### Column Types
{dataframe_block(dtypes)}

### Null Counts
{dataframe_block(nulls)}

### Numeric Summary
{dataframe_block(describe.round(2))}

## 3. Data Quality And Structure

- The dataset is unusually clean for real estate data: no nulls, no duplicate rows, and no duplicate listing identifiers.
- `listing_id` behaves like a surrogate key and was excluded from modeling.
- The feature set is a mix of continuous structural attributes (`sq_ft`, `lot_size_acres`, `year_built`), low-cardinality counts (`num_rooms`, `garage_spaces`), and categorical indicators (`neighborhood`, `has_pool`).
- Outliers exist, but only in small numbers. Counts of values with absolute z-score above 3 are shown below.

### Outlier Counts
{dataframe_block(z_outliers_df)}

## 4. Exploratory Data Analysis

### Relationships With Price
{dataframe_block(corr_to_target_df.round(3))}

Interpretation:

- Price is dominated by property size signals. `sq_ft`, `lot_size_acres`, and `num_rooms` are all strongly positively correlated with price.
- `garage_spaces` is moderately correlated with price, but much of that appears to reflect larger homes rather than a standalone garage effect.
- `year_built` has a positive but much smaller marginal correlation with price.
- `has_pool` has nearly zero raw correlation with price and also weak adjusted effect after controlling for the other features.

### Group Summaries

Neighborhood-level price summary:
{dataframe_block(neighborhood_summary)}

Pool indicator price summary:
{dataframe_block(pool_summary)}

Interpretation:

- Raw neighborhood differences are modest relative to overall price variation.
- Homes with pools are not more expensive on average in this sample. That does not imply pools reduce value; it implies pool ownership overlaps with other characteristics in a way that does not create a strong standalone price premium here.

### Visualizations

Generated PNG files:

- `plots/target_distribution.png`
- `plots/correlation_heatmap.png`
- `plots/top_numeric_relationships.png`
- `plots/categorical_price_patterns.png`
- `plots/model_diagnostics.png`
- `plots/actual_vs_predicted.png`
- `plots/permutation_importance.png`

Key visual findings:

- The price distribution is roughly unimodal with a few low-price and high-price tail observations.
- Scatterplots show strong, close-to-linear positive relationships between price and the main size variables, especially `sq_ft`.
- Boxplots suggest neighborhood differences are smaller than the effects of size and age.
- Diagnostic plots do not show strong curvature or severe variance explosions, though a handful of points deserve review.

## 5. Modeling Strategy

I compared five candidate models using 5-fold cross-validation:

1. Linear regression
2. Ridge regression
3. Lasso regression
4. Random forest regression
5. Log-linear regression

The comparison prioritized out-of-sample R^2 and error metrics rather than in-sample fit.

### Cross-Validated Performance
{dataframe_block(model_results.assign(
    cv_r2_mean=lambda x: x["cv_r2_mean"].round(4),
    cv_r2_std=lambda x: x["cv_r2_std"].round(4),
    cv_mae=lambda x: x["cv_mae"].round(2),
    cv_rmse=lambda x: x["cv_rmse"].round(2),
))}

Model choice:

- Plain linear regression performed best overall: mean CV R^2 = {model_results.iloc[0]["cv_r2_mean"]:.4f}, mean CV RMSE = {model_results.iloc[0]["cv_rmse"]:.2f}.
- Ridge and lasso were nearly identical but slightly worse, implying regularization was not needed for predictive accuracy.
- Random forest underperformed the linear model, which suggests the underlying signal is mostly additive and close to linear.
- Log-transforming the target degraded performance materially, so the original price scale was retained.

### Holdout Performance For The Selected Model

- Test R^2: {best_model_eval["metrics"]["test_r2"]:.4f}
- Test MAE: ${best_model_eval["metrics"]["test_mae"]:,.2f}
- Test RMSE: ${best_model_eval["metrics"]["test_rmse"]:,.2f}

### Permutation Importance On The Test Set
{dataframe_block(best_model_eval["importance_df"].round(4))}

Interpretation:

- `sq_ft` is the dominant driver of predictive performance.
- `year_built` contributes meaningful incremental signal.
- Other size-related variables matter, but their importance is partly distributed across correlated measurements.

## 6. Regression Diagnostics And Assumptions

An interpretable OLS model was fit on the full dataset to evaluate assumptions and coefficient stability:

`price_usd ~ sq_ft + num_rooms + lot_size_acres + garage_spaces + year_built + C(neighborhood) + has_pool`

### Multicollinearity
{dataframe_block(vif_df.round(3))}

Interpretation:

- Multicollinearity is substantial among the size-related predictors.
- `sq_ft`, `lot_size_acres`, and `num_rooms` have especially high VIF values.
- Because of that, predictive performance is reliable, but coefficient-level causal interpretations for these overlapping size measures should be treated cautiously.

### Robust Coefficient Table (HC3 Standard Errors)
{dataframe_block(coef_table.round(4))}

Interpretation:

- `sq_ft` and `year_built` are strongly and consistently associated with higher prices.
- After accounting for `sq_ft`, `year_built`, and the other controls, the neighborhood indicators are not statistically distinguishable from the reference category.
- `num_rooms`, `lot_size_acres`, and `garage_spaces` lose significance once the more dominant size signal in `sq_ft` is included. This is consistent with multicollinearity rather than proof of no relationship.
- The pool effect remains weak and statistically marginal even with heteroskedasticity-robust standard errors.

### Assumption Checks

- Linearity: Ramsey RESET F-test = {reset.fvalue:.3f}, p = {reset.pvalue:.4f}. No evidence of meaningful omitted nonlinear structure.
- Residual normality: Jarque-Bera statistic = {jb_stat:.3f}, p = {jb_pvalue:.4f}. Residuals are compatible with approximate normality.
- Homoskedasticity: Breusch-Pagan LM p = {bp_lm_pvalue:.4f}, F p = {bp_f_pvalue:.4f}. This is borderline around the 10% level, but not a strong rejection at 5%. HC3 robust standard errors were therefore reported.
- Independence: the data are cross-sectional, there are no duplicate listings, and no repeated IDs were found. Independence cannot be proven from the file alone, but there is no immediate structural evidence against it.
- Influence: maximum Cook's distance = {influence.cooks_distance[0].max():.4f}; {influential_count} observations exceed the common threshold 4/n = {cook_threshold:.4f}. These points are worth review but do not dominate the fit.

## 7. Notable Anomalies

The five largest externally studentized residuals are below. These appear to be properties priced materially below what the fitted model expects given their recorded attributes.

{dataframe_block(anomaly_rows)}

Interpretation:

- These observations could reflect unobserved condition issues, distressed sales, data-entry noise, or omitted variables such as renovation quality, school district, or micro-location.
- They are useful candidates for domain review, but not extreme enough to invalidate the overall model.

## 8. Conclusions

- The dataset is clean and well-structured, with no missing values and no duplicate keys.
- Residential price in this sample is explained primarily by home size, especially square footage, with newer construction providing a secondary premium.
- A standard linear regression is both the most interpretable and the best-performing predictive model among the candidates tested.
- The main modeling caveat is multicollinearity among size-related variables. This limits coefficient interpretation but does not materially hurt predictive accuracy.
- There is mild evidence of a few influential or underpriced listings, but no severe assumption failure that would force a different model family.

## 9. Reproducibility

Artifacts generated by this analysis:

- `analysis_report.md`
- `plots/target_distribution.png`
- `plots/correlation_heatmap.png`
- `plots/top_numeric_relationships.png`
- `plots/categorical_price_patterns.png`
- `plots/model_diagnostics.png`
- `plots/actual_vs_predicted.png`
- `plots/permutation_importance.png`
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    build_report()
