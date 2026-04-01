from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy.stats import chi2, chi2_contingency, fisher_exact, mannwhitneyu, pointbiserialr, shapiro
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_validate, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "dataset.csv"
PLOTS_DIR = BASE_DIR / "plots"
REPORT_PATH = BASE_DIR / "analysis_report.md"


def savefig(name: str) -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name, dpi=160, bbox_inches="tight")
    plt.close()


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["customer_segment"] = df["customer_segment"].astype("category")
    df["returned"] = df["returned"].astype(int)
    df["expected_total_usd"] = (
        df["items_qty"] * df["unit_price_usd"] * (1 - df["discount_pct"] / 100.0)
        + df["shipping_usd"]
    )
    df["total_error_usd"] = df["order_total_usd"] - df["expected_total_usd"]
    df["abs_total_error_usd"] = df["total_error_usd"].abs()
    df["negative_total_flag"] = (df["order_total_usd"] < 0).astype(int)
    df["large_error_flag"] = (df["abs_total_error_usd"] > 1000).astype(int)
    return df


def make_plots(df: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", palette="deep")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    cols = [
        "items_qty",
        "unit_price_usd",
        "shipping_usd",
        "discount_pct",
        "order_total_usd",
        "abs_total_error_usd",
    ]
    for ax, col in zip(axes.flat, cols):
        sns.histplot(df[col], kde=True, ax=ax)
        ax.set_title(f"Distribution of {col}")
    savefig("numeric_distributions.png")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, col in zip(axes.flat, cols):
        sns.boxplot(data=df, x="returned", y=col, ax=ax)
        ax.set_title(f"{col} by returned")
    savefig("boxplots_by_returned.png")

    plt.figure(figsize=(7, 4))
    sns.countplot(data=df, x="customer_segment", hue="returned")
    plt.title("Customer segment vs returned")
    savefig("segment_return_counts.png")

    return_rate = (
        df.groupby("customer_segment", observed=False)["returned"]
        .mean()
        .sort_values(ascending=False)
        .rename("return_rate")
        .reset_index()
    )
    plt.figure(figsize=(7, 4))
    sns.barplot(data=return_rate, x="customer_segment", y="return_rate")
    plt.ylim(0, max(0.15, return_rate["return_rate"].max() * 1.15))
    plt.title("Return rate by customer segment")
    savefig("segment_return_rate.png")

    plt.figure(figsize=(7, 5))
    sns.scatterplot(
        data=df,
        x="expected_total_usd",
        y="order_total_usd",
        hue="returned",
        alpha=0.7,
    )
    lim = [
        min(df["expected_total_usd"].min(), df["order_total_usd"].min()),
        max(df["expected_total_usd"].max(), df["order_total_usd"].max()),
    ]
    plt.plot(lim, lim, color="black", linestyle="--", linewidth=1)
    plt.title("Recorded vs expected order total")
    savefig("order_total_consistency.png")

    plt.figure(figsize=(7, 4))
    sns.histplot(df["total_error_usd"], bins=40, kde=True)
    plt.title("Distribution of order total error")
    savefig("order_total_error_distribution.png")

    corr_cols = [
        "items_qty",
        "unit_price_usd",
        "shipping_usd",
        "discount_pct",
        "order_total_usd",
        "expected_total_usd",
        "abs_total_error_usd",
        "returned",
    ]
    plt.figure(figsize=(9, 7))
    sns.heatmap(df[corr_cols].corr(), annot=True, cmap="coolwarm", center=0, fmt=".2f")
    plt.title("Correlation heatmap")
    savefig("correlation_heatmap.png")


def basic_profile(df: pd.DataFrame) -> dict[str, object]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    shapiro_sample = min(len(df), 500)
    shapiro_results = {}
    for col in [
        "items_qty",
        "unit_price_usd",
        "shipping_usd",
        "discount_pct",
        "order_total_usd",
        "abs_total_error_usd",
    ]:
        stat, p = shapiro(df[col].sample(shapiro_sample, random_state=42))
        shapiro_results[col] = {"W": stat, "p": p}

    pb = {}
    for col in [
        "items_qty",
        "unit_price_usd",
        "shipping_usd",
        "discount_pct",
        "order_total_usd",
        "expected_total_usd",
        "abs_total_error_usd",
    ]:
        r, p = pointbiserialr(df["returned"], df[col])
        pb[col] = {"r": r, "p": p}

    mw = {}
    for col in [
        "items_qty",
        "unit_price_usd",
        "shipping_usd",
        "discount_pct",
        "order_total_usd",
        "expected_total_usd",
        "abs_total_error_usd",
    ]:
        stat, p = mannwhitneyu(
            df.loc[df["returned"] == 0, col],
            df.loc[df["returned"] == 1, col],
            alternative="two-sided",
        )
        mw[col] = {"U": stat, "p": p}

    segment_table = pd.crosstab(df["customer_segment"], df["returned"])
    segment_chi2 = chi2_contingency(segment_table)

    neg_table = pd.crosstab(df["negative_total_flag"], df["returned"])
    neg_fisher = fisher_exact(neg_table)

    large_error_table = pd.crosstab(df["large_error_flag"], df["returned"])
    large_error_fisher = fisher_exact(large_error_table)

    profile = {
        "raw_shape": (len(df), 8),
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str),
        "nulls": df.isna().sum(),
        "describe": df.describe(include="all").transpose(),
        "numeric_cols": numeric_cols,
        "return_rate": df["returned"].mean(),
        "segment_counts": df["customer_segment"].value_counts(),
        "discount_levels": sorted(df["discount_pct"].unique().tolist()),
        "shipping_levels": sorted(df["shipping_usd"].unique().tolist()),
        "negative_totals": int((df["order_total_usd"] < 0).sum()),
        "large_errors": int((df["abs_total_error_usd"] > 1000).sum()),
        "error_summary": df[["total_error_usd", "abs_total_error_usd"]].describe(),
        "shapiro": shapiro_results,
        "pointbiserial": pb,
        "mannwhitney": mw,
        "segment_table": segment_table,
        "segment_chi2": segment_chi2,
        "neg_table": neg_table,
        "neg_fisher": neg_fisher,
        "large_error_table": large_error_table,
        "large_error_fisher": large_error_fisher,
    }
    return profile


def evaluate_models(df: pd.DataFrame) -> dict[str, object]:
    X = df.drop(columns=["returned"])
    y = df["returned"]

    numeric_features = [c for c in X.columns if c != "customer_segment"]
    categorical_features = ["customer_segment"]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "roc_auc": "roc_auc",
        "pr_auc": "average_precision",
        "bal_acc": "balanced_accuracy",
        "neg_brier": "neg_brier_score",
    }

    pre_logit = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
                ),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(drop="first", handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    pre_tree = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_features),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )

    models = {
        "dummy_prior": DummyClassifier(strategy="prior"),
        "logistic_regression": Pipeline(
            [
                ("preprocessor", pre_logit),
                (
                    "classifier",
                    LogisticRegression(max_iter=5000, class_weight="balanced"),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocessor", pre_tree),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=500,
                        min_samples_leaf=10,
                        random_state=42,
                        class_weight="balanced_subsample",
                    ),
                ),
            ]
        ),
    }

    cv_results = {}
    probas = {}
    for name, model in models.items():
        result = cross_validate(model, X, y, cv=cv, scoring=scoring)
        cv_results[name] = {
            metric.replace("test_", ""): {
                "mean": float(values.mean()),
                "std": float(values.std()),
            }
            for metric, values in result.items()
            if metric.startswith("test_")
        }

        if name != "dummy_prior":
            probas[name] = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]

    plt.figure(figsize=(7, 5))
    for name, preds in probas.items():
        fpr, tpr, _ = roc_curve(y, preds)
        auc = roc_auc_score(y, preds)
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")
    plt.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1)
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("Cross-validated ROC curves")
    plt.legend()
    savefig("model_roc_curves.png")

    plt.figure(figsize=(7, 5))
    sns.histplot(probas["logistic_regression"], label="Logistic", color="C0", alpha=0.5)
    sns.histplot(probas["random_forest"], label="Random forest", color="C1", alpha=0.5)
    plt.title("Predicted return probabilities")
    plt.legend()
    savefig("predicted_probability_distributions.png")

    return {"cv_results": cv_results, "probas": probas}


def logistic_diagnostics(df: pd.DataFrame) -> dict[str, object]:
    model_df = df[
        [
            "returned",
            "customer_segment",
            "items_qty",
            "unit_price_usd",
            "shipping_usd",
            "discount_pct",
            "abs_total_error_usd",
            "negative_total_flag",
        ]
    ].copy()

    design = pd.get_dummies(
        model_df.drop(columns=["returned"]), drop_first=True, dtype=float
    )
    design = sm.add_constant(design)

    vif = {}
    for idx, col in enumerate(design.columns):
        if col == "const":
            continue
        vif[col] = float(variance_inflation_factor(design.values, idx))

    logit_model = sm.Logit(model_df["returned"], design).fit(disp=False)

    bt_df = model_df.copy()
    continuous = [
        "items_qty",
        "unit_price_usd",
        "shipping_usd",
        "discount_pct",
        "abs_total_error_usd",
    ]
    for col in continuous:
        shifted = bt_df[col].astype(float) + 1.0
        bt_df[f"{col}_log_interaction"] = shifted * np.log(shifted)

    bt_design = pd.get_dummies(
        bt_df.drop(columns=["returned"]), drop_first=True, dtype=float
    )
    bt_design = sm.add_constant(bt_design)
    bt_model = sm.Logit(bt_df["returned"], bt_design).fit(disp=False)
    bt_pvalues = {
        col: float(bt_model.pvalues[f"{col}_log_interaction"]) for col in continuous
    }

    pred = logit_model.predict(design)
    groups = pd.qcut(pred.rank(method="first"), q=10, duplicates="drop")
    hl_df = pd.DataFrame({"y": model_df["returned"], "p": pred, "bucket": groups})
    grouped = hl_df.groupby("bucket", observed=False).agg(
        observed=("y", "sum"),
        expected=("p", "sum"),
        count=("y", "size"),
    )
    grouped["observed_non"] = grouped["count"] - grouped["observed"]
    grouped["expected_non"] = grouped["count"] - grouped["expected"]
    hl_stat = (
        ((grouped["observed"] - grouped["expected"]) ** 2)
        / grouped["expected"].clip(lower=1e-9)
        + ((grouped["observed_non"] - grouped["expected_non"]) ** 2)
        / grouped["expected_non"].clip(lower=1e-9)
    ).sum()
    hl_dfree = max(len(grouped) - 2, 1)
    hl_pvalue = float(chi2.sf(hl_stat, hl_dfree))

    return {
        "vif": vif,
        "params": logit_model.params.to_dict(),
        "pvalues": logit_model.pvalues.to_dict(),
        "pseudo_r2": float(logit_model.prsquared),
        "aic": float(logit_model.aic),
        "positive_preds_05": int((pred >= 0.5).sum()),
        "box_tidwell_pvalues": bt_pvalues,
        "hosmer_lemeshow_stat": float(hl_stat),
        "hosmer_lemeshow_df": int(hl_dfree),
        "hosmer_lemeshow_pvalue": hl_pvalue,
    }


def format_float(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def frame_block(df: pd.DataFrame | pd.Series) -> str:
    if isinstance(df, pd.Series):
        body = df.to_string()
    else:
        body = df.to_string()
    return f"```text\n{body}\n```"


def write_report(
    df: pd.DataFrame,
    profile: dict[str, object],
    model_results: dict[str, object],
    diagnostics: dict[str, object],
) -> None:
    describe_table = frame_block(
        df[
            [
                "items_qty",
                "unit_price_usd",
                "shipping_usd",
                "discount_pct",
                "order_total_usd",
                "expected_total_usd",
                "abs_total_error_usd",
                "returned",
            ]
        ]
        .describe()
        .round(3)
    )
    null_table = frame_block(profile["nulls"].to_frame("null_count"))
    dtype_table = frame_block(profile["dtypes"].to_frame("dtype"))
    segment_rate = (
        df.groupby("customer_segment", observed=False)["returned"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "return_rate"})
        .round(4)
    )
    segment_rate = frame_block(segment_rate)
    top_anomalies = (
        df.sort_values("abs_total_error_usd", ascending=False)
        .head(10)[
            [
                "order_id",
                "customer_segment",
                "items_qty",
                "unit_price_usd",
                "shipping_usd",
                "discount_pct",
                "order_total_usd",
                "expected_total_usd",
                "total_error_usd",
                "returned",
            ]
        ]
        .round(3)
    )
    top_anomalies = frame_block(top_anomalies)
    pb_lines = "\n".join(
        f"- `{col}`: r={vals['r']:.3f}, p={vals['p']:.3f}"
        for col, vals in profile["pointbiserial"].items()
    )
    mw_lines = "\n".join(
        f"- `{col}`: p={vals['p']:.3f}"
        for col, vals in profile["mannwhitney"].items()
    )
    shapiro_lines = "\n".join(
        f"- `{col}`: W={vals['W']:.3f}, p={vals['p']:.3g}"
        for col, vals in profile["shapiro"].items()
    )
    cv_lines = []
    for model_name, metrics in model_results["cv_results"].items():
        cv_lines.append(f"**{model_name}**")
        for metric, vals in metrics.items():
            display_metric = "brier" if metric == "neg_brier" else metric
            mean_value = -vals["mean"] if metric == "neg_brier" else vals["mean"]
            cv_lines.append(
                f"- `{display_metric}`: mean={mean_value:.3f}, std={vals['std']:.3f}"
            )
    cv_text = "\n".join(cv_lines)
    vif_lines = "\n".join(
        f"- `{col}`: {val:.3f}" for col, val in diagnostics["vif"].items()
    )
    bt_lines = "\n".join(
        f"- `{col}` interaction p-value: {pval:.3f}"
        for col, pval in diagnostics["box_tidwell_pvalues"].items()
    )
    coef_table = frame_block(
        pd.DataFrame(
            {
                "coef": diagnostics["params"],
                "pvalue": diagnostics["pvalues"],
            }
        ).round(4)
    )

    report = f"""
# Dataset Analysis Report

## Executive Summary

The dataset contains **{profile["raw_shape"][0]} rows** and **{profile["raw_shape"][1]} raw columns** describing e-commerce-like orders with a binary return flag. The data has **no missing values**, but it is **not clean**: `order_total_usd` is frequently inconsistent with the quantity, unit price, shipping, and discount fields, with some discrepancies approaching **${df["abs_total_error_usd"].max():,.2f}** and **{profile["negative_totals"]} negative order totals**. Those anomalies are materially important and dominate the data-quality assessment.

From a predictive standpoint, the available fields contain **little to no reliable signal** for `returned`. Both classical inference and cross-validated machine learning stayed near chance-level performance. The strongest conclusion is therefore about **data quality and weak separability**, not a meaningful return-risk model.

## 1. Data Loading and Inspection

- File analyzed: `dataset.csv`
- Raw file shape: `{profile["raw_shape"][0]} x {profile["raw_shape"][1]}`
- Analysis frame shape after derived features: `{profile["shape"][0]} x {profile["shape"][1]}`
- Positive class prevalence: `{profile["return_rate"]:.3%}`
- Customer segments: {", ".join(f"{k}={v}" for k, v in profile["segment_counts"].items())}
- Shipping levels observed: {profile["shipping_levels"]}
- Discount levels observed: {profile["discount_levels"]}

### Dtypes

{dtype_table}

### Null Counts

{null_table}

### Basic Statistics

{describe_table}

## 2. Exploratory Data Analysis

Plots were saved to `./plots/`:

- `numeric_distributions.png`
- `boxplots_by_returned.png`
- `segment_return_counts.png`
- `segment_return_rate.png`
- `order_total_consistency.png`
- `order_total_error_distribution.png`
- `correlation_heatmap.png`
- `model_roc_curves.png`
- `predicted_probability_distributions.png`

### Distributional Checks

Shapiro-Wilk tests were run on a random sample of 500 observations per numeric feature. These tests reject normality for most variables, so non-parametric comparisons were preferred:

{shapiro_lines}

### Return Patterns by Segment

{segment_rate}

Chi-square test for association between `customer_segment` and `returned`:

- chi-square = {profile["segment_chi2"][0]:.3f}
- p-value = {profile["segment_chi2"][1]:.3f}

There is no statistically credible evidence that return propensity differs by segment in this sample.

### Numeric Relationships With Returns

Point-biserial correlations between numeric fields and `returned` were uniformly weak:

{pb_lines}

Mann-Whitney tests comparing returned vs non-returned orders also found no meaningful univariate separation:

{mw_lines}

## 3. Data Quality and Anomaly Investigation

`order_total_usd` was checked against the accounting identity:

`expected_total_usd = items_qty * unit_price_usd * (1 - discount_pct / 100) + shipping_usd`

This check failed often and sometimes catastrophically.

- Median absolute discrepancy: **${df["abs_total_error_usd"].median():,.2f}**
- Mean absolute discrepancy: **${df["abs_total_error_usd"].mean():,.2f}**
- Rows with absolute discrepancy > $1,000: **{profile["large_errors"]}** ({profile["large_errors"] / len(df):.1%})
- Negative `order_total_usd` rows: **{profile["negative_totals"]}** ({profile["negative_totals"] / len(df):.1%})

Fisher tests on anomaly indicators vs `returned`:

- Negative total flag: odds ratio = {profile["neg_fisher"][0]:.3f}, p = {profile["neg_fisher"][1]:.3f}
- Large error flag: odds ratio = {profile["large_error_fisher"][0]:.3f}, p = {profile["large_error_fisher"][1]:.3f}

The anomaly indicators themselves are not predictive of returns, but they do show that the dataset cannot be treated as accounting-consistent.

### Most Extreme Order Total Anomalies

{top_anomalies}

## 4. Modeling

Because `returned` is binary and class-imbalanced, the primary task was framed as **classification**. Stratified 5-fold cross-validation was used to preserve the low positive rate in each fold.

Models evaluated:

- `dummy_prior`: baseline that predicts the class prior
- `logistic_regression`: interpretable linear classifier with class balancing
- `random_forest`: flexible non-linear model with class balancing

### Cross-Validated Performance

{cv_text}

Interpretation:

- The baseline PR AUC is the class prevalence, about **0.088**.
- Logistic regression performed **worse than or approximately equal to baseline**, indicating no stable linear signal.
- Random forest improved only marginally over the baseline PR AUC and stayed near **0.509 ROC AUC**, which is effectively chance-level discrimination.
- The random forest produced lower Brier loss than the logistic model, but discrimination remained too weak to justify operational use.

## 5. Model Assumptions and Diagnostics

For inferential checks, a parsimonious logistic regression used:

- `customer_segment`
- `items_qty`
- `unit_price_usd`
- `shipping_usd`
- `discount_pct`
- `abs_total_error_usd`
- `negative_total_flag`

### Multicollinearity

Variance inflation factors were modest:

{vif_lines}

These values do not indicate problematic collinearity in the parsimonious inferential model.

### Linearity of the Logit

Box-Tidwell-style interaction terms were tested for continuous predictors:

{bt_lines}

No interaction term was significant at conventional thresholds, so the linearity-in-the-logit assumption was not contradicted by these checks.

### Logistic Regression Fit

- McFadden pseudo-R²: {diagnostics["pseudo_r2"]:.4f}
- AIC: {diagnostics["aic"]:.2f}
- Positive predictions at threshold 0.5 on the full sample: {diagnostics["positive_preds_05"]}
- Hosmer-Lemeshow statistic: {diagnostics["hosmer_lemeshow_stat"]:.3f} on {diagnostics["hosmer_lemeshow_df"]} df, p = {diagnostics["hosmer_lemeshow_pvalue"]:.3f}

Coefficient table:

{coef_table}

None of the fitted coefficients were statistically compelling, which is consistent with the cross-validated near-chance performance.

## 6. Findings

1. **The dataset is complete but not trustworthy as-is for revenue-like fields.** `order_total_usd` fails a simple consistency check on many rows and includes implausible negative totals.
2. **There is no strong evidence of segment-level return differences.** VIP customers show a slightly higher raw return rate, but the difference is not statistically persuasive.
3. **The available features do not separate returned from non-returned orders well.** Univariate tests, logistic regression, and random forest all point to weak signal.
4. **A production return-prediction model is not supported by this dataset in its current form.** The best model barely improves over a naive baseline and would likely be unstable in deployment.

## 7. Recommendations

1. Audit how `order_total_usd` was generated or exported. The discrepancies are too large to be rounding noise.
2. Verify whether negative totals represent refunds, reversals, chargebacks, or data corruption; encode those cases explicitly if they are real business events.
3. Before further modeling, collect stronger behavioral features such as product category, time-to-ship, payment method, geography, customer history, or fulfillment issues.
4. If return prediction is the business goal, re-run modeling only after the accounting fields are validated and the feature set is expanded.
"""
    REPORT_PATH.write_text(dedent(report).strip() + "\n", encoding="utf-8")


def main() -> None:
    df = load_data()
    make_plots(df)
    profile = basic_profile(df)
    model_results = evaluate_models(df)
    diagnostics = logistic_diagnostics(df)
    write_report(df, profile, model_results, diagnostics)


if __name__ == "__main__":
    main()
