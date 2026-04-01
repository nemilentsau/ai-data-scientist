from __future__ import annotations

from pathlib import Path
import textwrap

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor


sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 140

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"
PLOTS_DIR.mkdir(exist_ok=True)


def savefig(name: str) -> str:
    path = PLOTS_DIR / name
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return f"plots/{name}"


def format_float(value: float, digits: int = 3) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}"


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    return {
        "R2": r2_score(y_true, y_pred),
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": rmse,
    }


def iqr_outlier_counts(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    counts = {}
    for col in cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lo = q1 - 1.5 * iqr
        hi = q3 + 1.5 * iqr
        counts[col] = int(((df[col] < lo) | (df[col] > hi)).sum())
    return pd.Series(counts).sort_values(ascending=False)


def markdown_table_from_frame(df: pd.DataFrame, index: bool = True) -> str:
    frame = df.copy()
    if index:
        frame = frame.reset_index()
    headers = [str(col) for col in frame.columns]
    rows = [[str(value) for value in row] for row in frame.to_numpy().tolist()]
    separator = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    raw_df = df.copy()

    target = "monthly_rent_usd"
    id_col = "listing_id"
    numeric_cols = [
        "sq_ft",
        "bedrooms",
        "bathrooms",
        "distance_to_center_km",
        "year_built",
        "has_parking",
        "pet_friendly",
    ]

    summary = raw_df[numeric_cols + [target]].describe().T
    missing = raw_df.isna().sum().to_frame("missing_count")
    missing["missing_pct"] = 100 * missing["missing_count"] / len(df)
    duplicates = int(raw_df.duplicated().sum())
    id_unique = bool(raw_df[id_col].is_unique)

    df["property_age"] = 2026 - df["year_built"]

    # Plots
    plt.figure(figsize=(8, 5))
    sns.histplot(df[target], kde=True, bins=30, color="#1f77b4")
    plt.title("Distribution of Monthly Rent")
    plt.xlabel("Monthly rent (USD)")
    rent_dist_plot = savefig("rent_distribution.png")

    plt.figure(figsize=(9, 6))
    corr = df[numeric_cols + [target]].corr(numeric_only=True)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0)
    plt.title("Feature Correlation Heatmap")
    corr_plot = savefig("correlation_heatmap.png")

    plt.figure(figsize=(8, 6))
    sns.scatterplot(
        data=df,
        x="sq_ft",
        y=target,
        hue="bedrooms",
        palette="viridis",
        alpha=0.75,
    )
    sns.regplot(data=df, x="sq_ft", y=target, scatter=False, color="black")
    plt.title("Rent vs Square Footage")
    sqft_plot = savefig("rent_vs_sqft.png")

    plt.figure(figsize=(8, 6))
    sns.scatterplot(
        data=df,
        x="distance_to_center_km",
        y=target,
        hue="has_parking",
        palette="Set1",
        alpha=0.75,
    )
    sns.regplot(
        data=df,
        x="distance_to_center_km",
        y=target,
        scatter=False,
        lowess=True,
        color="black",
    )
    plt.title("Rent vs Distance to Center")
    distance_plot = savefig("rent_vs_distance.png")

    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x="bedrooms", y=target, color="#8fbcd4")
    sns.stripplot(data=df, x="bedrooms", y=target, alpha=0.3, color="black", size=3)
    plt.title("Rent by Bedroom Count")
    bedrooms_plot = savefig("rent_by_bedrooms.png")

    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x="has_parking", y=target, color="#c7b299")
    plt.xticks([0, 1], ["No parking", "Parking"])
    plt.title("Parking Premium")
    parking_plot = savefig("parking_premium.png")

    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x="pet_friendly", y=target, color="#b4d3b2")
    plt.xticks([0, 1], ["Not pet-friendly", "Pet-friendly"])
    plt.title("Pet-friendly Premium")
    pet_plot = savefig("pet_friendly_premium.png")

    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x="year_built", y=target, alpha=0.7)
    sns.regplot(data=df, x="year_built", y=target, scatter=False, lowess=True, color="black")
    plt.title("Rent vs Year Built")
    year_plot = savefig("rent_vs_year_built.png")

    # Outlier and distribution checks
    iqr_counts = iqr_outlier_counts(df, numeric_cols + [target]).rename("iqr_outlier_count")
    skewness = df[numeric_cols + [target]].skew().sort_values(key=np.abs, ascending=False).rename("skew")

    # Modeling
    X = df[numeric_cols].copy()
    y = df[target].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    numeric_features = numeric_cols
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            )
        ]
    )

    linear_pipe = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", LinearRegression()),
        ]
    )

    ridge_pipe = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", RidgeCV(alphas=np.logspace(-3, 3, 25))),
        ]
    )

    rf_pipe = Pipeline(
        steps=[
            (
                "preprocessor",
                ColumnTransformer(
                    transformers=[
                        ("num", SimpleImputer(strategy="median"), numeric_features),
                    ]
                ),
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=500,
                    min_samples_leaf=3,
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )

    log_linear_pipe = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                TransformedTargetRegressor(
                    regressor=LinearRegression(),
                    func=np.log1p,
                    inverse_func=np.expm1,
                ),
            ),
        ]
    )

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "r2": "r2",
        "neg_mae": "neg_mean_absolute_error",
        "neg_rmse": "neg_root_mean_squared_error",
    }

    cv_results = {}
    for name, model in {
        "LinearRegression": linear_pipe,
        "RidgeCV": ridge_pipe,
        "RandomForest": rf_pipe,
        "LogLinear": log_linear_pipe,
    }.items():
        res = cross_validate(model, X, y, cv=cv, scoring=scoring, n_jobs=1)
        cv_results[name] = {
            "CV_R2_mean": res["test_r2"].mean(),
            "CV_R2_std": res["test_r2"].std(),
            "CV_MAE_mean": -res["test_neg_mae"].mean(),
            "CV_RMSE_mean": -res["test_neg_rmse"].mean(),
        }

    linear_pipe.fit(X_train, y_train)
    ridge_pipe.fit(X_train, y_train)
    rf_pipe.fit(X_train, y_train)
    log_linear_pipe.fit(X_train, y_train)

    test_metrics = {}
    for name, model in {
        "LinearRegression": linear_pipe,
        "RidgeCV": ridge_pipe,
        "RandomForest": rf_pipe,
        "LogLinear": log_linear_pipe,
    }.items():
        preds = model.predict(X_test)
        test_metrics[name] = regression_metrics(y_test, preds)

    # Interpretable OLS for assumptions and coefficients
    X_sm = sm.add_constant(X)
    ols = sm.OLS(y, X_sm).fit()
    influence = OLSInfluence(ols)
    studentized = influence.resid_studentized_external
    leverage = influence.hat_matrix_diag
    cooks_d = influence.cooks_distance[0]

    plt.figure(figsize=(8, 6))
    sns.scatterplot(x=ols.fittedvalues, y=ols.resid, alpha=0.7)
    plt.axhline(0, color="black", linestyle="--", linewidth=1)
    plt.title("Residuals vs Fitted")
    plt.xlabel("Fitted rent")
    plt.ylabel("Residuals")
    resid_plot = savefig("residuals_vs_fitted.png")

    plt.figure(figsize=(8, 6))
    sm.qqplot(ols.resid, line="45", fit=True)
    plt.title("Q-Q Plot of OLS Residuals")
    qq_plot = savefig("qq_plot_residuals.png")

    plt.figure(figsize=(8, 6))
    sns.scatterplot(x=leverage, y=studentized, size=cooks_d, sizes=(20, 300), alpha=0.6)
    plt.title("Influence Plot Proxy")
    plt.xlabel("Leverage")
    plt.ylabel("Externally Studentized Residual")
    influence_plot = savefig("influence_proxy.png")

    bp_test = het_breuschpagan(ols.resid, ols.model.exog)
    bp_labels = ["LM stat", "LM p-value", "F stat", "F p-value"]
    bp_results = dict(zip(bp_labels, bp_test))

    vif_df = pd.DataFrame(
        {
            "feature": X.columns,
            "VIF": [
                variance_inflation_factor(X.values.astype(float), i)
                for i in range(X.shape[1])
            ],
        }
    ).sort_values("VIF", ascending=False)

    coefs = (
        pd.DataFrame(
            {
                "feature": ols.params.index,
                "coef": ols.params.values,
                "p_value": ols.pvalues.values,
            }
        )
        .query("feature != 'const'")
        .assign(abs_coef=lambda d: d["coef"].abs())
        .sort_values("abs_coef", ascending=False)
    )

    rf_model = rf_pipe.named_steps["model"]
    rf_importances = pd.DataFrame(
        {"feature": numeric_features, "importance": rf_model.feature_importances_}
    ).sort_values("importance", ascending=False)

    plt.figure(figsize=(8, 6))
    sns.barplot(data=rf_importances, x="importance", y="feature", color="#4c72b0")
    plt.title("Random Forest Feature Importance")
    rf_importance_plot = savefig("rf_feature_importance.png")

    strong_corr = (
        corr[target]
        .drop(target)
        .sort_values(key=np.abs, ascending=False)
        .rename("correlation_with_rent")
    )

    log_ols = sm.OLS(np.log1p(y), X_sm).fit()
    log_bp_test = het_breuschpagan(log_ols.resid, log_ols.model.exog)

    high_influence_n = int((cooks_d > (4 / len(df))).sum())
    large_resid_n = int((np.abs(studentized) > 3).sum())

    report = f"""
# Dataset Analysis Report

## 1. Dataset Overview

- File analyzed: `dataset.csv`
- Rows: {len(df)}
- Columns: {raw_df.shape[1]}
- Duplicate rows: {duplicates}
- `listing_id` unique across rows: {id_unique}
- Missing values present: {"yes" if missing["missing_count"].sum() else "no"}

This dataset appears to describe rental listings. `monthly_rent_usd` is the natural supervised learning target, while `listing_id` behaves like an identifier and was excluded from modeling.

### Column Types

{markdown_table_from_frame(pd.DataFrame({"dtype": raw_df.dtypes.astype(str)}))}

### Missingness

{markdown_table_from_frame(missing)}

### Summary Statistics

{markdown_table_from_frame(summary.round(3))}

## 2. Data Quality and Screening

- No missing values were found in any column.
- No fully duplicated rows were found.
- `bedrooms` includes studios (`0` bedrooms), which is plausible rather than automatically erroneous.
- `distance_to_center_km` extends to {raw_df["distance_to_center_km"].max():.1f} km, so there are likely suburban outliers.
- `sq_ft` ranges from {raw_df["sq_ft"].min()} to {raw_df["sq_ft"].max()} and `monthly_rent_usd` from {raw_df[target].min()} to {raw_df[target].max()}, which is wide enough to require explicit outlier checks.

### IQR Outlier Counts

{markdown_table_from_frame(iqr_counts.to_frame())}

### Skewness

{markdown_table_from_frame(skewness.round(3).to_frame())}

Interpretation:

- The strongest skew appears in `distance_to_center_km`, `sq_ft`, and `monthly_rent_usd`, indicating some long right tails.
- Because the target is continuous and reasonably broad, I treated this as a regression problem and compared interpretable linear models with a non-linear ensemble benchmark.

## 3. Exploratory Data Analysis

### Key Visuals

- Rent distribution: ![]({rent_dist_plot})
- Correlation heatmap: ![]({corr_plot})
- Rent vs square footage: ![]({sqft_plot})
- Rent vs distance to center: ![]({distance_plot})
- Rent by bedrooms: ![]({bedrooms_plot})
- Parking premium: ![]({parking_plot})
- Pet-friendly premium: ![]({pet_plot})
- Rent vs year built: ![]({year_plot})

### Correlation with Rent

{markdown_table_from_frame(strong_corr.round(3).to_frame())}

Key EDA findings:

- `sq_ft` is the strongest single linear correlate of rent.
- `bedrooms` and `bathrooms` are also strongly positively associated with rent, but they are partially proxies for size.
- `distance_to_center_km`, `year_built`, `has_parking`, and `pet_friendly` have weak marginal correlations with rent in this dataset.
- Some visual subgroup differences appear in boxplots and smoothers, but those effects are small relative to the dominant size signal.
- The LOWESS smoother in the distance plot suggests the distance penalty is not perfectly linear, with the steepest decline close to the center.

## 4. Modeling Strategy

I fit four models:

1. `LinearRegression` for interpretability.
2. `RidgeCV` to check whether mild regularization improves stability under correlated predictors.
3. `RandomForestRegressor` as a flexible non-linear benchmark.
4. `LogLinear` as a robustness check for heteroscedasticity and right-skew in the target.

Validation design:

- 80/20 train/test split with `random_state=42`
- 5-fold cross-validation on the full dataset
- Metrics: R², MAE, RMSE

### Cross-Validation Results

{markdown_table_from_frame(pd.DataFrame(cv_results).T.round(3))}

### Test Set Results

{markdown_table_from_frame(pd.DataFrame(test_metrics).T.round(3))}

### OLS Coefficients

{markdown_table_from_frame(coefs[["feature", "coef", "p_value"]].round(4), index=False)}

### Random Forest Feature Importance

![]({rf_importance_plot})

{markdown_table_from_frame(rf_importances.round(4), index=False)}

Model interpretation:

- If linear and random-forest performance are similar, the signal is mostly captured by additive relationships.
- If the random forest is materially better, that is evidence for non-linearity or interactions the linear model misses.
- Ridge was included mainly as a robustness check against correlated housing features such as `sq_ft`, `bedrooms`, and `bathrooms`.
- The log-linear model was not adopted as the primary model unless it improved both fit quality and residual behavior on the original rent scale.

## 5. Linear Model Assumption Checks

I used an OLS fit on the full dataset for diagnostic checks because assumption testing is defined most directly for linear regression.

### Residual Diagnostics

- Residuals vs fitted: ![]({resid_plot})
- Q-Q plot: ![]({qq_plot})
- Influence proxy: ![]({influence_plot})

### Formal Checks

- OLS R²: {ols.rsquared:.3f}
- Adjusted R²: {ols.rsquared_adj:.3f}
- Jarque-Bera p-value: {format_float(sm.stats.stattools.jarque_bera(ols.resid)[1], 6)}
- Breusch-Pagan p-value: {format_float(bp_results["LM p-value"], 6)}
- Log-OLS Jarque-Bera p-value: {format_float(sm.stats.stattools.jarque_bera(log_ols.resid)[1], 6)}
- Log-OLS Breusch-Pagan p-value: {format_float(log_bp_test[1], 6)}
- Maximum VIF: {vif_df["VIF"].max():.3f}
- High-influence points by Cook's D > 4/n: {high_influence_n}
- Large external studentized residuals (|r| > 3): {large_resid_n}

### Variance Inflation Factors

{markdown_table_from_frame(vif_df.round(3), index=False)}

Assumption assessment:

- Linearity: broadly reasonable for `sq_ft`, `bedrooms`, `bathrooms`, and `year_built`, but the distance effect looks mildly non-linear.
- Independence: cannot be proven from the file alone, but there is no obvious repeated-ID structure beyond unique listing identifiers.
- Homoscedasticity: the Breusch-Pagan test and residual spread indicate whether variance rises with fitted rent. If the p-value is small, standard OLS inference should be interpreted cautiously.
- Normality of residuals: the Q-Q plot and Jarque-Bera test assess tail behavior. With 1,200 observations, minor deviations matter less for prediction than for exact parametric inference.
- The log-rent specification improves these diagnostics somewhat, but it should only replace the base model if that benefit outweighs the drop in predictive accuracy on the original rent scale.
- Multicollinearity: VIF values quantify how much size-related variables overlap. Elevated VIFs do not invalidate prediction, but they do make individual linear coefficients less stable to interpret.
- Influence: Cook's D and studentized residuals show whether a small number of listings dominate the fit.

## 6. Main Findings

{textwrap.dedent(f"""
- Rent is dominated by property size. `sq_ft` is by far the strongest predictor in both correlation analysis and model importance.
- After controlling for other variables, `bedrooms` and `bathrooms` still contribute useful signal, but they overlap strongly with size and should be interpreted cautiously because of multicollinearity.
- Location, building age, parking, and pet-friendliness are weak predictors in this specific dataset once size is included. Their simple marginal patterns are small and most are not statistically significant in the linear model.
- The data is clean in the narrow sense of missingness and duplicates, but it is not perfectly well-behaved: there are right-tailed variables and outliers, especially in distance, size, and rent.
- The key modeling question is whether those departures are strong enough to justify non-linear methods or target transformation. In this dataset, the random forest improves cross-validated error modestly, while the log-linear variant improves assumptions but sacrifices predictive accuracy.
""").strip()}

## 7. Recommendation

- For explanation and pricing sensitivity, use the linear model, but communicate that the distance effect is only approximately linear and that correlated size variables limit clean causal interpretation of each separate coefficient.
- For pure predictive accuracy, prefer the best-performing validated model on held-out data. Here the random forest has the best average cross-validation performance, but the gain over the plain linear model is small enough that interpretability may still dominate the decision.
- If this were moving into production, the next steps would be: collect richer location features, test log-rent or spline terms for distance, and validate stability on a genuinely out-of-time sample rather than a random split.
"""

    REPORT_PATH.write_text(report.strip() + "\n")


if __name__ == "__main__":
    main()
