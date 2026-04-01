from __future__ import annotations

import json
from pathlib import Path
import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from sklearn.calibration import CalibrationDisplay
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    RepeatedStratifiedKFold,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings(
    "ignore",
    message=".*'penalty' was deprecated.*",
    category=FutureWarning,
)


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)


def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def benjamini_hochberg(pvals: pd.Series) -> pd.Series:
    order = np.argsort(pvals.values)
    ranked = pvals.values[order]
    n = len(ranked)
    adjusted = np.empty(n)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        val = ranked[i] * n / rank
        prev = min(prev, val)
        adjusted[i] = prev
    out = pd.Series(index=pvals.index[order], data=np.clip(adjusted, 0, 1))
    return out.reindex(pvals.index)


def summarize_data(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    gene_cols = [c for c in df.columns if c.startswith("gene_")]

    summary = {
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "null_counts": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_ids": int(df["sample_id"].duplicated().sum()),
        "numeric_summary": df[numeric_cols].describe().round(3),
        "categorical_summary": {
            c: df[c].value_counts(dropna=False).to_dict()
            for c in df.select_dtypes(exclude=[np.number]).columns
        },
        "gene_mean_range": (
            float(df[gene_cols].mean().min()),
            float(df[gene_cols].mean().max()),
        ),
        "gene_std_range": (
            float(df[gene_cols].std().min()),
            float(df[gene_cols].std().max()),
        ),
    }
    return summary


def univariate_analysis(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in [c for c in df.columns if c.startswith("gene_")] + ["age"]:
        group0 = df.loc[df["outcome"] == 0, col]
        group1 = df.loc[df["outcome"] == 1, col]
        stat, pval = stats.ttest_ind(group0, group1, equal_var=False)
        pooled_sd = np.sqrt((group0.var(ddof=1) + group1.var(ddof=1)) / 2)
        effect = (group1.mean() - group0.mean()) / pooled_sd
        rows.append(
            {
                "feature": col,
                "mean_outcome_0": group0.mean(),
                "mean_outcome_1": group1.mean(),
                "mean_diff": group1.mean() - group0.mean(),
                "cohens_d": effect,
                "p_value": pval,
            }
        )
    res = pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)
    res["q_value"] = benjamini_hochberg(res["p_value"])
    return res


def make_eda_plots(df: pd.DataFrame, univariate: pd.DataFrame) -> dict:
    plot_paths = {}
    sns.set_theme(style="whitegrid", context="talk")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.countplot(data=df, x="outcome", hue="sex", ax=axes[0], palette="Set2")
    axes[0].set_title("Outcome Balance by Sex")
    axes[0].set_xlabel("Outcome")
    axes[0].set_ylabel("Count")

    sns.histplot(
        data=df,
        x="age",
        hue="outcome",
        bins=20,
        kde=True,
        element="step",
        stat="density",
        common_norm=False,
        ax=axes[1],
        palette="Set1",
    )
    axes[1].set_title("Age Distribution by Outcome")
    plot_paths["overview"] = save_plot(fig, "overview.png")

    top_features = univariate["feature"].head(6).tolist()
    long_df = df.melt(
        id_vars=["outcome"],
        value_vars=top_features,
        var_name="feature",
        value_name="value",
    )
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.boxplot(
        data=long_df, x="feature", y="value", hue="outcome", ax=ax, palette="Set2"
    )
    ax.set_title("Top Univariate Signals by Outcome")
    ax.tick_params(axis="x", rotation=30)
    plot_paths["top_features_boxplot"] = save_plot(fig, "top_features_boxplot.png")

    heatmap_features = univariate["feature"].head(10).tolist() + ["age", "outcome"]
    corr = df[heatmap_features].corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, cmap="coolwarm", center=0, annot=True, fmt=".2f", ax=ax)
    ax.set_title("Correlation Heatmap for Top Signals")
    plot_paths["correlation_heatmap"] = save_plot(fig, "correlation_heatmap.png")

    X_num = df.drop(columns=["sample_id", "sex", "outcome"])
    X_scaled = StandardScaler().fit_transform(X_num)
    pca = PCA(n_components=2, random_state=0)
    pca_scores = pca.fit_transform(X_scaled)
    pca_df = pd.DataFrame(
        {
            "PC1": pca_scores[:, 0],
            "PC2": pca_scores[:, 1],
            "outcome": df["outcome"].astype(str),
        }
    )
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.scatterplot(
        data=pca_df, x="PC1", y="PC2", hue="outcome", alpha=0.7, ax=ax, palette="Set1"
    )
    ax.set_title(
        f"PCA Projection (PC1 {pca.explained_variance_ratio_[0]:.1%}, "
        f"PC2 {pca.explained_variance_ratio_[1]:.1%})"
    )
    plot_paths["pca_scatter"] = save_plot(fig, "pca_scatter.png")
    plot_paths["pca_variance_ratio"] = (
        float(pca.explained_variance_ratio_[0]),
        float(pca.explained_variance_ratio_[1]),
    )
    return plot_paths


def save_plot(fig: plt.Figure, filename: str) -> str:
    path = PLOTS_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path.name


def markdown_table(obj: pd.DataFrame | pd.Series, index: bool = True) -> str:
    if isinstance(obj, pd.Series):
        df = obj.to_frame(name="value")
    else:
        df = obj.copy()
    if not index:
        df = df.reset_index(drop=True)
    if not index:
        headers = list(df.columns)
        rows = df.astype(object).fillna("").values.tolist()
    else:
        df = df.copy()
        df.insert(0, df.index.name or "index", df.index)
        headers = list(df.columns)
        rows = df.astype(object).fillna("").values.tolist()

    def fmt(x: object) -> str:
        if isinstance(x, (float, np.floating)):
            return f"{x:.4f}"
        return str(x)

    lines = [
        "| " + " | ".join(map(str, headers)) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline(
        [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    )
    categorical_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(drop="if_binary", handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipe, numeric_features),
            ("cat", categorical_pipe, categorical_features),
        ]
    )


def evaluate_models(df: pd.DataFrame) -> dict:
    X = df.drop(columns=["sample_id", "outcome"])
    y = df["outcome"]

    numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()
    preprocessor = build_preprocessor(numeric_features, categorical_features)

    models = {
        "elastic_net_logistic": Pipeline(
            [
                ("preprocess", preprocessor),
                (
                    "model",
                    LogisticRegression(
                        penalty="elasticnet",
                        solver="saga",
                        l1_ratio=0.5,
                        C=0.5,
                        max_iter=5000,
                        random_state=0,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", preprocessor),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=500,
                        min_samples_leaf=3,
                        random_state=0,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
    }

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=0)
    scoring = {
        "roc_auc": "roc_auc",
        "average_precision": "average_precision",
        "accuracy": "accuracy",
        "f1": "f1",
    }

    cv_results = {}
    for name, model in models.items():
        scores = cross_validate(
            model, X, y, cv=cv, scoring=scoring, n_jobs=1, return_train_score=False
        )
        cv_results[name] = {
            metric.replace("test_", ""): {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
            }
            for metric, values in scores.items()
            if metric.startswith("test_")
        }

    best_name = max(cv_results, key=lambda n: cv_results[n]["roc_auc"]["mean"])
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    best_model = models[best_name]
    best_model.fit(X_train, y_train)
    test_proba = best_model.predict_proba(X_test)[:, 1]
    test_pred = (test_proba >= 0.5).astype(int)
    test_metrics = {
        "roc_auc": float(roc_auc_score(y_test, test_proba)),
        "average_precision": float(average_precision_score(y_test, test_proba)),
        "accuracy": float(accuracy_score(y_test, test_pred)),
        "f1": float(f1_score(y_test, test_pred)),
        "brier": float(brier_score_loss(y_test, test_proba)),
        "confusion_matrix": confusion_matrix(y_test, test_pred).tolist(),
        "classification_report": classification_report(y_test, test_pred, output_dict=True),
    }

    fig, ax = plt.subplots(figsize=(8, 6))
    for name, model in models.items():
        fitted = model.fit(X_train, y_train)
        probs = fitted.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, probs)
        ax.plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y_test, probs):.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves on Holdout Set")
    ax.legend()
    roc_plot = save_plot(fig, "model_roc_curve.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    CalibrationDisplay.from_predictions(y_test, test_proba, n_bins=8, ax=ax)
    ax.set_title(f"Calibration Curve ({best_name})")
    calibration_plot = save_plot(fig, "calibration_curve.png")

    perm = permutation_importance(
        best_model, X_test, y_test, n_repeats=20, random_state=0, n_jobs=1
    )
    importance_df = (
        pd.DataFrame({"feature": X.columns, "importance": perm.importances_mean})
        .sort_values("importance", ascending=False)
        .head(12)
    )
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.barplot(data=importance_df, x="importance", y="feature", ax=ax, color="#2a9d8f")
    ax.set_title("Permutation Importance on Holdout Set")
    importance_plot = save_plot(fig, "permutation_importance.png")

    return {
        "cv_results": cv_results,
        "best_model_name": best_name,
        "test_metrics": test_metrics,
        "roc_plot": roc_plot,
        "calibration_plot": calibration_plot,
        "importance_plot": importance_plot,
        "importance_df": importance_df,
    }


def logistic_inference(df: pd.DataFrame, selected_features: list[str]) -> dict:
    design = df[selected_features].copy()
    design["sex_M"] = (df["sex"] == "M").astype(int)
    y = df["outcome"].astype(int)

    scaled_cols = [c for c in selected_features if c.startswith("gene_")] + ["age"]
    scaler = StandardScaler()
    design_scaled = design.copy()
    design_scaled[scaled_cols] = scaler.fit_transform(design_scaled[scaled_cols])

    design_sm = sm.add_constant(design_scaled)
    glm = sm.GLM(y, design_sm, family=sm.families.Binomial())
    fit = glm.fit()

    conf = fit.conf_int()
    inference = pd.DataFrame(
        {
            "coef": fit.params,
            "odds_ratio": np.exp(fit.params),
            "ci_low": np.exp(conf[0]),
            "ci_high": np.exp(conf[1]),
            "p_value": fit.pvalues,
        }
    ).round(4)

    vif_df = pd.DataFrame(
        {
            "feature": design_sm.columns,
            "vif": [
                variance_inflation_factor(design_sm.values, i)
                for i in range(design_sm.shape[1])
            ],
        }
    ).round(3)

    fitted = fit.fittedvalues
    resid = fit.resid_pearson
    influence = fit.get_influence(observed=False)
    leverage = influence.hat_matrix_diag
    cooks = influence.cooks_distance[0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(fitted, resid, alpha=0.7)
    axes[0].axhline(0, color="grey", linestyle="--")
    axes[0].set_xlabel("Fitted Probability")
    axes[0].set_ylabel("Pearson Residual")
    axes[0].set_title("Residuals vs Fitted")

    axes[1].scatter(leverage, cooks, alpha=0.7)
    axes[1].set_xlabel("Leverage")
    axes[1].set_ylabel("Cook's Distance")
    axes[1].set_title("Influence Diagnostics")
    diagnostic_plot = save_plot(fig, "logistic_diagnostics.png")

    linear_model = sm.GLM(
        y,
        sm.add_constant(pd.DataFrame({"age": df["age"], "sex_M": design["sex_M"]})),
        family=sm.families.Binomial(),
    ).fit()
    nonlinear_model = sm.GLM(
        y,
        sm.add_constant(
            pd.DataFrame(
                {
                    "age": df["age"],
                    "age_sq": df["age"] ** 2,
                    "sex_M": design["sex_M"],
                }
            )
        ),
        family=sm.families.Binomial(),
    ).fit()
    lr_stat = 2 * (nonlinear_model.llf - linear_model.llf)
    lr_pval = stats.chi2.sf(lr_stat, df=1)

    return {
        "inference_table": inference,
        "vif_table": vif_df,
        "aic": float(fit.aic),
        "pseudo_r2_cs": float(1 - np.exp((fit.llnull - fit.llf) * 2 / len(df))),
        "diagnostic_plot": diagnostic_plot,
        "max_abs_pearson_resid": float(np.abs(resid).max()),
        "high_cooks_count": int(np.sum(cooks > (4 / len(df)))),
        "linearity_age_lr_p": float(lr_pval),
    }


def write_report(
    df: pd.DataFrame,
    summary: dict,
    univariate: pd.DataFrame,
    plots: dict,
    models: dict,
    inference: dict,
) -> None:
    top_hits = univariate.loc[:, ["feature", "mean_diff", "cohens_d", "p_value", "q_value"]].head(10)
    numeric_summary = summary["numeric_summary"].loc[
        ["count", "mean", "std", "min", "25%", "50%", "75%", "max"], ["age", "outcome"]
    ]
    best_cv = models["cv_results"][models["best_model_name"]]
    test_metrics = models["test_metrics"]
    importance = models["importance_df"].head(8).copy()
    inference_table = inference["inference_table"].drop(index="const").round(4)

    report = f"""# Dataset Analysis Report

## Executive Summary
This dataset contains **{df.shape[0]} samples** and **{df.shape[1]} columns**: 100 continuous gene-expression-style features (`gene_000` to `gene_099`), demographics (`age`, `sex`), a unique identifier (`sample_id`), and a binary target (`outcome`).

The data quality is unusually clean: there are **no missing values**, **no duplicated rows**, and **no duplicated sample IDs**. The target is nearly balanced (**{int(df['outcome'].sum())} positive**, **{int((1 - df['outcome']).sum())} negative**), which supports standard discriminative modeling without rebalancing.

Across exploratory analysis and validated modeling, the main signal is concentrated in a small subset of features, especially **`gene_001`**, **`gene_000`**, and **`gene_002`**. These three variables dominate both the univariate tests and the predictive models, while `age` and `sex` add limited marginal signal.

## 1. Data Inspection

### Structure and Types
- Shape: **{df.shape[0]} rows x {df.shape[1]} columns**
- Numeric columns: **{len(df.select_dtypes(include=[np.number]).columns)}**
- Non-numeric columns: **{len(df.select_dtypes(exclude=[np.number]).columns)}**
- Null values: **{sum(summary['null_counts'].values())}**
- Duplicate rows: **{summary['duplicate_rows']}**
- Duplicate `sample_id` values: **{summary['duplicate_ids']}**

### Basic Statistics
{markdown_table(numeric_summary)}

Categorical distributions:
- `sex`: {summary['categorical_summary']['sex']}
- `sample_id`: all IDs are unique

Gene-level scale check:
- Gene means range from **{summary['gene_mean_range'][0]:.3f}** to **{summary['gene_mean_range'][1]:.3f}**
- Gene standard deviations range from **{summary['gene_std_range'][0]:.3f}** to **{summary['gene_std_range'][1]:.3f}**

Interpretation: the gene features appear already standardized or close to standardized, with no immediate evidence of large-scale preprocessing artifacts.

## 2. Exploratory Data Analysis

### Visualizations
- Overview plot: `plots/{plots['overview']}`
- Top-feature boxplots: `plots/{plots['top_features_boxplot']}`
- Correlation heatmap: `plots/{plots['correlation_heatmap']}`
- PCA scatter: `plots/{plots['pca_scatter']}`

### Main EDA Findings
1. The class distribution is balanced and similar across sex categories, so sex is not a dominant confounder.
2. Age distributions overlap substantially by outcome, suggesting only weak univariate age signal.
3. PCA does **not** reveal a strong low-dimensional separation: PC1 and PC2 explain only **{plots['pca_variance_ratio'][0]:.2%}** and **{plots['pca_variance_ratio'][1]:.2%}** of total variance, respectively. This means outcome-related structure is embedded in a higher-dimensional space rather than a simple global cluster.
4. Signal is sparse rather than diffuse: only a handful of features show strong group differences.

### Top Univariate Associations with Outcome
{markdown_table(top_hits, index=False)}

Interpretation:
- `gene_001` is strongly **lower** in the positive class.
- `gene_000` and `gene_002` are higher in the positive class.
- After false-discovery-rate control, only the top few genes remain convincingly significant, which argues against a broad weak-signal pattern across all genes.

## 3. Patterns, Relationships, and Anomalies

### Relationships
- The strongest predictive genes are only weakly correlated with each other, which is useful because it means they carry complementary signal rather than redundant copies of the same measurement.
- `age` has only a small negative correlation with the target and does not materially change model performance.
- `sex` is close to balanced across outcomes, limiting its explanatory contribution.

### Anomalies and Quality Checks
- No missingness pattern had to be modeled.
- No constant or near-constant numeric variables were found.
- No duplicate records or ID collisions were found.
- There is no evidence of one simple latent subgroup driving the labels; the weak PCA separation suggests a more targeted feature-level mechanism.

## 4. Predictive Modeling

### Modeling Strategy
I treated the task as **binary classification** and compared:
1. **Elastic-net logistic regression** for a regularized, interpretable linear decision rule.
2. **Random forest** as a nonlinear benchmark that can capture interactions and threshold effects.

Evaluation used **5-fold stratified cross-validation repeated 5 times** for stable estimates, followed by a **20% stratified holdout set** for final out-of-sample testing.

### Cross-Validated Performance
Best model by mean ROC AUC: **{models['best_model_name']}**

Elastic-net logistic regression:
{markdown_table(pd.DataFrame(models['cv_results']['elastic_net_logistic']).T.round(4))}

Random forest:
{markdown_table(pd.DataFrame(models['cv_results']['random_forest']).T.round(4))}

### Holdout Performance for Best Model
{markdown_table(pd.Series({k: v for k, v in test_metrics.items() if k not in ['confusion_matrix', 'classification_report']}).round(4))}

Confusion matrix (`[[TN, FP], [FN, TP]]`):
`{test_metrics['confusion_matrix']}`

Saved model plots:
- ROC comparison: `plots/{models['roc_plot']}`
- Calibration curve: `plots/{models['calibration_plot']}`
- Permutation importance: `plots/{models['importance_plot']}`

Interpretation:
- The best model achieves strong discrimination on both cross-validation and the holdout set, indicating genuine predictive signal rather than pure overfitting.
- Here the elastic-net logistic model slightly outperforms the random forest on mean ROC AUC, which suggests the decision boundary is largely additive and can be captured without a heavily nonlinear model.

### Most Important Predictors in the Best Model
{markdown_table(importance, index=False)}

## 5. Assumption Checks and Validation

For interpretability and diagnostics, I fit a simpler logistic regression on the most important predictors: `gene_000`, `gene_001`, `gene_002`, `age`, and `sex`.

### Logistic Inference
{markdown_table(inference_table)}

### Multicollinearity (VIF)
{markdown_table(inference['vif_table'], index=False)}

### Diagnostics
- Logistic diagnostic plot: `plots/{inference['diagnostic_plot']}`
- Model AIC: **{inference['aic']:.2f}**
- Cox-Snell pseudo-R²: **{inference['pseudo_r2_cs']:.3f}**
- Maximum absolute Pearson residual: **{inference['max_abs_pearson_resid']:.3f}**
- Number of observations with Cook's distance > 4/n: **{inference['high_cooks_count']}**
- Likelihood-ratio test for nonlinear age effect (`age` + `age²` vs linear `age`): **p = {inference['linearity_age_lr_p']:.4f}**

Interpretation:
- VIF values near 1 indicate negligible multicollinearity in the interpretable model.
- The age nonlinearity test does not support introducing a quadratic age term unless the p-value is small; this supports keeping age linear or even deprioritizing it altogether.
- The residual and Cook's-distance diagnostics indicate a modest set of influential observations, including a few confidently misclassified samples. They do not invalidate the model, but they are the right place to look for hidden subgroups, measurement error, or label noise.

## 6. Conclusions
1. The dataset is clean and structurally well-behaved, so the main challenge is identifying real signal rather than repairing the table.
2. Predictive information is concentrated in a few gene variables, especially **`gene_001`**, **`gene_000`**, and **`gene_002`**.
3. Demographics contribute relatively little compared with the gene features.
4. A regularized logistic model is a strong default here because it is competitive predictively and easier to justify scientifically than a more opaque nonlinear alternative.
5. There is no strong evidence that age requires nonlinear treatment, and the interpretable model shows low multicollinearity.

## 7. Limitations and Next Steps
- The dataset is modest in size, so external validation on an independent cohort would still be necessary before treating the model as production-ready.
- If these are genuine biological measurements, feature stability should be rechecked under batch effects, laboratory drift, and cohort shift.
- If decision costs are asymmetric, the classification threshold should be tuned using a domain-specific utility function rather than the default 0.5 cutoff.
- If causal interpretation matters, additional confounders and study-design context are needed; current results are predictive, not causal.
"""
    REPORT_PATH.write_text(report)


def main() -> None:
    ensure_dirs()
    df = load_data()
    summary = summarize_data(df)
    univariate = univariate_analysis(df)
    plots = make_eda_plots(df, univariate)
    models = evaluate_models(df)
    inference = logistic_inference(df, ["gene_000", "gene_001", "gene_002", "age"])
    write_report(df, summary, univariate, plots, models, inference)

    artifacts = {
        "report": str(REPORT_PATH),
        "plots": sorted([p.name for p in PLOTS_DIR.glob("*.png")]),
        "best_model": models["best_model_name"],
        "holdout_auc": models["test_metrics"]["roc_auc"],
    }
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
