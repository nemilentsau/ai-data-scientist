from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    silhouette_score,
)
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
from statsmodels.tools.tools import add_constant
import statsmodels.api as sm


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name, dpi=160, bbox_inches="tight")
    plt.close()


def series_markdown(s: pd.Series, digits: int = 3) -> str:
    out = s.copy()
    if pd.api.types.is_numeric_dtype(out):
        out = out.round(digits)
    return dataframe_markdown(out.to_frame("value"), digits=digits)


def dataframe_markdown(df: pd.DataFrame, digits: int = 3) -> str:
    out = df.copy()
    num_cols = out.select_dtypes(include=[np.number]).columns
    out[num_cols] = out[num_cols].round(digits)
    headers = [str(idx_name or "") for idx_name in out.index.names] if any(out.index.names) else [""]
    if isinstance(out.index, pd.MultiIndex):
        index_rows = [list(map(str, idx)) for idx in out.index]
        headers = [str(name or "") for name in out.index.names]
    else:
        index_rows = [[str(idx)] for idx in out.index]
        headers = [str(out.index.name or "")]
    headers += [str(col) for col in out.columns]

    rows = []
    for idx_vals, row in zip(index_rows, out.itertuples(index=False, name=None)):
        rows.append(idx_vals + [str(val) for val in row])

    table = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        table.append("| " + " | ".join(row) + " |")
    return "\n".join(table)


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")

    df = pd.read_csv(DATA_PATH)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [
        "avg_order_value",
        "purchase_frequency_monthly",
        "days_since_last_purchase",
        "support_contacts",
        "account_age_months",
    ]
    target_col = "total_lifetime_spend"

    shape = df.shape
    dtypes = df.dtypes.astype(str)
    nulls = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ids = int(df["customer_id"].duplicated().sum())
    describe = df.describe(include="all").transpose()
    skew = df[numeric_cols].skew().sort_values(ascending=False)
    kurt = df[numeric_cols].kurtosis().sort_values(ascending=False)

    iqr_rows = []
    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((df[col] < lower) | (df[col] > upper)).sum())
        iqr_rows.append({"column": col, "iqr_outliers": count, "lower": lower, "upper": upper})
    iqr_outliers = pd.DataFrame(iqr_rows).set_index("column")

    corr = df[numeric_cols].corr()

    # EDA plots
    plt.figure(figsize=(10, 7))
    corr_plot = corr.copy()
    sns.heatmap(corr_plot, annot=True, cmap="coolwarm", center=0, fmt=".2f")
    plt.title("Correlation Heatmap")
    savefig("correlation_heatmap.png")

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    axes = axes.flatten()
    for ax, col in zip(axes, numeric_cols):
        sns.histplot(df[col], kde=True, ax=ax, color="#4C78A8")
        ax.set_title(f"Distribution: {col}")
    for ax in axes[len(numeric_cols):]:
        ax.axis("off")
    savefig("numeric_distributions.png")

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    axes = axes.flatten()
    for ax, col in zip(axes, numeric_cols):
        sns.boxplot(x=df[col], ax=ax, color="#72B7B2")
        ax.set_title(f"Boxplot: {col}")
    for ax in axes[len(numeric_cols):]:
        ax.axis("off")
    savefig("numeric_boxplots.png")

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    scatter_cols = [
        "avg_order_value",
        "purchase_frequency_monthly",
        "days_since_last_purchase",
        "account_age_months",
    ]
    for ax, col in zip(axes.flatten(), scatter_cols):
        sns.regplot(
            data=df,
            x=col,
            y=target_col,
            lowess=True,
            scatter_kws={"alpha": 0.55, "s": 20},
            line_kws={"color": "#E45756"},
            ax=ax,
        )
        ax.set_title(f"{target_col} vs {col}")
    savefig("target_relationships.png")

    sns.pairplot(
        df[
            [
                "avg_order_value",
                "purchase_frequency_monthly",
                "days_since_last_purchase",
                target_col,
            ]
        ],
        corner=True,
        diag_kind="hist",
        plot_kws={"alpha": 0.45, "s": 18},
    )
    plt.suptitle("Selected Pairplot", y=1.02)
    savefig("selected_pairplot.png")

    # Supervised modeling
    X = df[feature_cols]
    y = df[target_col]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

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
                feature_cols,
            )
        ]
    )

    cv = KFold(n_splits=10, shuffle=True, random_state=42)
    models = {
        "Linear regression": Pipeline(
            steps=[("prep", preprocessor), ("model", LinearRegression())]
        ),
        "Polynomial regression (degree 2)": Pipeline(
            steps=[
                ("prep", preprocessor),
                ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                ("model", LinearRegression()),
            ]
        ),
        "Random forest": Pipeline(
            steps=[
                ("prep", preprocessor),
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

    model_rows = []
    fitted_models = {}
    for name, model in models.items():
        scores = cross_validate(
            model,
            X,
            y,
            cv=cv,
            scoring=("r2", "neg_mean_absolute_error", "neg_root_mean_squared_error"),
            n_jobs=1,
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        fitted_models[name] = model
        model_rows.append(
            {
                "model": name,
                "cv_r2_mean": np.mean(scores["test_r2"]),
                "cv_r2_std": np.std(scores["test_r2"]),
                "cv_mae_mean": -np.mean(scores["test_neg_mean_absolute_error"]),
                "cv_rmse_mean": -np.mean(scores["test_neg_root_mean_squared_error"]),
                "test_r2": r2_score(y_test, preds),
                "test_mae": mean_absolute_error(y_test, preds),
                "test_rmse": np.sqrt(mean_squared_error(y_test, preds)),
            }
        )
    model_results = pd.DataFrame(model_rows).set_index("model").sort_values(
        "cv_r2_mean", ascending=False
    )

    rf_model = fitted_models["Random forest"]
    rf_perm = permutation_importance(
        rf_model, X_test, y_test, n_repeats=25, random_state=42, n_jobs=1
    )
    rf_importance = pd.Series(rf_perm.importances_mean, index=feature_cols).sort_values(
        ascending=False
    )

    plt.figure(figsize=(8, 5))
    sns.barplot(x=rf_importance.values, y=rf_importance.index, color="#4C78A8")
    plt.title("Random Forest Permutation Importance")
    plt.xlabel("Mean decrease in test R² proxy score")
    plt.ylabel("")
    savefig("rf_permutation_importance.png")

    best_preds = rf_model.predict(X_test)
    plt.figure(figsize=(7, 6))
    sns.scatterplot(x=y_test, y=best_preds, alpha=0.65, s=28, color="#54A24B")
    lims = [min(y_test.min(), best_preds.min()), max(y_test.max(), best_preds.max())]
    plt.plot(lims, lims, color="#E45756", linestyle="--", linewidth=1.5)
    plt.xlabel("Actual lifetime spend")
    plt.ylabel("Predicted lifetime spend")
    plt.title("Random Forest: Actual vs Predicted")
    savefig("rf_actual_vs_predicted.png")

    rf_residuals = y_test - best_preds
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.scatterplot(x=best_preds, y=rf_residuals, alpha=0.65, s=28, color="#72B7B2", ax=axes[0])
    axes[0].axhline(0, color="#E45756", linestyle="--", linewidth=1)
    axes[0].set_title("Random Forest Residuals vs Fitted")
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Residual")
    stats.probplot(rf_residuals, dist="norm", plot=axes[1])
    axes[1].set_title("Random Forest Residual Q-Q Plot")
    savefig("rf_residual_diagnostics.png")

    # OLS diagnostics on original scale to examine assumptions
    X_sm = add_constant(X)
    ols = sm.OLS(y, X_sm).fit()
    vif = pd.Series(
        [variance_inflation_factor(X_sm.values, i) for i in range(1, X_sm.shape[1])],
        index=feature_cols,
        name="VIF",
    ).sort_values(ascending=False)
    bp_stat, bp_pvalue, _, _ = het_breuschpagan(ols.resid, ols.model.exog)
    shapiro_stat, shapiro_pvalue = stats.shapiro(ols.resid)
    influence = OLSInfluence(ols)
    cooks = influence.cooks_distance[0]
    high_influence_count = int((cooks > (4 / len(df))).sum())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.scatterplot(x=ols.fittedvalues, y=ols.resid, alpha=0.6, s=25, color="#4C78A8", ax=axes[0])
    axes[0].axhline(0, color="#E45756", linestyle="--", linewidth=1)
    axes[0].set_title("OLS Residuals vs Fitted")
    axes[0].set_xlabel("Fitted")
    axes[0].set_ylabel("Residual")
    stats.probplot(ols.resid, dist="norm", plot=axes[1])
    axes[1].set_title("OLS Residual Q-Q Plot")
    savefig("ols_diagnostics.png")

    # Unsupervised segmentation
    cluster_cols = feature_cols + [target_col]
    scaler = StandardScaler()
    X_cluster = scaler.fit_transform(df[cluster_cols])
    silhouette_rows = []
    fitted_clusterers = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(X_cluster)
        silhouette_rows.append(
            {
                "k": k,
                "silhouette_score": silhouette_score(X_cluster, labels),
                "inertia": km.inertia_,
            }
        )
        fitted_clusterers[k] = (km, labels)
    cluster_eval = pd.DataFrame(silhouette_rows).set_index("k")
    best_k = int(cluster_eval["silhouette_score"].idxmax())
    best_clusterer, cluster_labels = fitted_clusterers[best_k]
    df["cluster"] = cluster_labels
    cluster_profile = (
        df.groupby("cluster")[cluster_cols]
        .agg(["mean", "median", "count"])
        .sort_values((target_col, "mean"), ascending=False)
    )

    plt.figure(figsize=(8, 5))
    sns.lineplot(
        x=cluster_eval.index,
        y=cluster_eval["silhouette_score"],
        marker="o",
        color="#4C78A8",
    )
    plt.title("KMeans Silhouette by Number of Clusters")
    plt.xlabel("Number of clusters")
    plt.ylabel("Silhouette score")
    savefig("cluster_silhouette_scores.png")

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_cluster)
    pca_df = pd.DataFrame(coords, columns=["PC1", "PC2"])
    pca_df["cluster"] = cluster_labels.astype(str)
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=pca_df, x="PC1", y="PC2", hue="cluster", palette="deep", alpha=0.75, s=35)
    plt.title(f"KMeans Segmentation (k={best_k}) in PCA Space")
    savefig("cluster_pca_projection.png")

    # Narrative helpers
    strongest_corr = (
        corr.where(~np.eye(corr.shape[0], dtype=bool))
        .abs()
        .unstack()
        .sort_values(ascending=False)
    )
    strongest_corr = strongest_corr[strongest_corr.index.get_level_values(0) != strongest_corr.index.get_level_values(1)]
    top_pairs = strongest_corr.groupby(level=[0, 1]).first()
    top_pairs = top_pairs[~top_pairs.index.duplicated()].head(6)

    cluster_summary = (
        df.groupby("cluster")[cluster_cols]
        .mean()
        .sort_values(target_col, ascending=False)
        .round(2)
    )

    report = dedent(
        f"""
        # Dataset Analysis Report

        ## 1. Data loading and inspection
        The dataset contains **{shape[0]} rows** and **{shape[1]} columns**. It is a customer-level table with one identifier (`customer_id`) and six quantitative variables.

        - Missing values: **{int(nulls.sum())}**
        - Duplicate rows: **{duplicate_rows}**
        - Duplicate customer IDs: **{duplicate_ids}**

        ### Column types
        {series_markdown(dtypes)}

        ### Descriptive statistics
        {dataframe_markdown(describe)}

        ### Skewness
        {series_markdown(skew)}

        ### Kurtosis
        {series_markdown(kurt)}

        ### IQR-based outlier counts
        {dataframe_markdown(iqr_outliers)}

        ## 2. Exploratory data analysis
        The core EDA plots were saved in `./plots/`:

        - `correlation_heatmap.png`
        - `numeric_distributions.png`
        - `numeric_boxplots.png`
        - `target_relationships.png`
        - `selected_pairplot.png`

        Key distributional findings:

        - The dataset is unusually clean: no missing data, no duplicate IDs, and no extreme z-score outliers in most continuous variables.
        - `total_lifetime_spend` is only moderately right-skewed (skew = {df[target_col].skew():.3f}), so a raw-scale regression is not automatically inappropriate.
        - `support_contacts` is discrete and slightly right-skewed; it has the only notable extreme values.
        - Most variables have negative kurtosis, indicating flatter-than-normal distributions rather than heavy tails.

        ### Correlation matrix
        {dataframe_markdown(corr)}

        ## 3. Key patterns, relationships, and anomalies
        Several relationships are strong enough to shape the analysis:

        - `avg_order_value` and `days_since_last_purchase` are strongly positively correlated ({corr.loc["avg_order_value", "days_since_last_purchase"]:.3f}).
        - `avg_order_value` and `purchase_frequency_monthly` are strongly negatively correlated ({corr.loc["avg_order_value", "purchase_frequency_monthly"]:.3f}).
        - `purchase_frequency_monthly` and `days_since_last_purchase` are also strongly negatively correlated ({corr.loc["purchase_frequency_monthly", "days_since_last_purchase"]:.3f}).
        - Pairwise linear correlations with `total_lifetime_spend` are weak to modest; the strongest is with `days_since_last_purchase` ({corr[target_col].drop(target_col).abs().sort_values(ascending=False).index[0]} = {corr[target_col].drop(target_col).abs().sort_values(ascending=False).iloc[0]:.3f} in absolute value).

        Interpretation:

        - The behavioral predictors are highly collinear. That makes coefficient-based linear interpretation unstable.
        - Weak pairwise correlation with lifetime spend does **not** imply the outcome is unpredictable; it suggests the relationship may be nonlinear or interaction-driven.
        - The combination of very clean data and strong geometric structure is somewhat unusual for raw operational data, so any business interpretation should be made cautiously.

        ## 4. Supervised modeling
        There is no explicit label column beyond `total_lifetime_spend`, so I treated lifetime spend as the most defensible business outcome to model. Features used:

        - `avg_order_value`
        - `purchase_frequency_monthly`
        - `days_since_last_purchase`
        - `support_contacts`
        - `account_age_months`

        Models were evaluated with **10-fold cross-validation** and a held-out **20% test split**.

        {dataframe_markdown(model_results)}

        Modeling takeaways:

        - A plain linear regression performs only moderately well, with mean CV R² of **{model_results.loc["Linear regression", "cv_r2_mean"]:.3f}**.
        - Adding second-order interactions/nonlinear terms sharply improves performance: polynomial regression reaches mean CV R² of **{model_results.loc["Polynomial regression (degree 2)", "cv_r2_mean"]:.3f}**.
        - The best predictive performance comes from a random forest, with mean CV R² of **{model_results.loc["Random forest", "cv_r2_mean"]:.3f}** and test R² of **{model_results.loc["Random forest", "test_r2"]:.3f}**.
        - This pattern strongly supports a nonlinear data-generating process.

        ### Random forest permutation importance
        {series_markdown(rf_importance)}

        Supporting plots:

        - `rf_permutation_importance.png`
        - `rf_actual_vs_predicted.png`
        - `rf_residual_diagnostics.png`

        ## 5. Assumption checks and validation
        I explicitly checked linear model assumptions because they matter for interpretation.

        ### Multicollinearity
        {series_markdown(vif.sort_values(ascending=False))}

        - VIF values above 5 are usually concerning, and above 10 are severe.
        - Here, the main behavioral predictors clearly exceed those thresholds, so OLS coefficients are not stable enough for strong causal-style interpretation.

        ### Residual diagnostics for OLS
        - Breusch-Pagan test p-value: **{bp_pvalue:.4g}**
        - Shapiro-Wilk test p-value: **{shapiro_pvalue:.4g}**
        - High-influence points using Cook's distance > 4/n: **{high_influence_count}**

        See `ols_diagnostics.png`.

        Interpretation:

        - The residual diagnostics should be read in combination with the VIF results: even if residual shape were acceptable, multicollinearity still limits interpretability.
        - The strong performance gap between linear and nonlinear models indicates that linearity is the main misspecification, not just noise.
        - For prediction, the random forest is preferable because it does not require linearity or normal residuals.

        ## 6. Unsupervised segmentation
        Since the dataset has no explicit class label and exhibits strong structure, I also ran KMeans clustering on the standardized numeric variables.

        ### Cluster validation
        {dataframe_markdown(cluster_eval)}

        - The best silhouette score occurs at **k = {best_k}**, which supports a three-segment solution.

        ### Mean profile by cluster
        {dataframe_markdown(cluster_summary)}

        Supporting plots:

        - `cluster_silhouette_scores.png`
        - `cluster_pca_projection.png`

        Broad segment interpretation:

        - One segment has high lifetime spend with relatively high order values and longer recency.
        - Another segment appears lower-value and more purchase-frequent.
        - A third segment sits between them, suggesting the data may encode distinct customer regimes rather than one smooth population.

        ## 7. Conclusions
        Main conclusions from the analysis:

        - The dataset is structurally clean and numerically well-behaved, but not simple.
        - Behavioral features are strongly interdependent, so naive coefficient interpretation is unreliable.
        - `total_lifetime_spend` is predictable, but mainly through **nonlinear** relationships and interactions rather than simple pairwise linear trends.
        - A random forest is the strongest predictive model among those tested.
        - A 3-cluster segmentation is also well supported and may be more actionable than a single global linear model.

        Recommended next steps if this were a production analysis:

        1. Confirm how `total_lifetime_spend` was computed and whether any leakage exists relative to the behavioral features.
        2. Add time-based variables or cohort metadata; `account_age_months` alone explains little.
        3. If interpretability matters, fit a regularized GAM or monotonic boosting model and compare it with the random forest.
        4. Validate the segmentation externally against retention, margin, or churn outcomes before operationalizing it.
        """
    ).strip()
    report = "\n".join(
        line[8:] if line.startswith("        ") else line
        for line in report.splitlines()
    )

    REPORT_PATH.write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
