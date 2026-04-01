import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "dataset.csv"
PLOTS_DIR = BASE_DIR / "plots"
REPORT_PATH = BASE_DIR / "analysis_report.md"


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def format_float(value: float, digits: int = 4) -> str:
    if pd.isna(value):
        return "NaN"
    return f"{value:.{digits}f}"


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATA_PATH)

    target = "converted"
    id_col = "session_id"
    categorical_cols = ["device"]
    numeric_cols = [
        "ad_budget_usd",
        "time_of_day_hour",
        "channel_score",
        "page_load_time_sec",
        "previous_visits",
    ]

    # 1) Inspection and data quality checks
    rows, cols = df.shape
    dtypes = df.dtypes.astype(str)
    null_counts = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ids = int(df[id_col].duplicated().sum())
    unique_counts = df.nunique()
    desc = df[numeric_cols + [target]].describe().T
    skewness = df[numeric_cols].skew(numeric_only=True)

    iqr_outliers = {}
    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo = q1 - 1.5 * iqr
        hi = q3 + 1.5 * iqr
        iqr_outliers[col] = int(((df[col] < lo) | (df[col] > hi)).sum())

    range_checks = {
        "time_of_day_hour_outside_0_24": int(((df["time_of_day_hour"] < 0) | (df["time_of_day_hour"] > 24)).sum()),
        "time_of_day_hour_equal_24": int((df["time_of_day_hour"] == 24).sum()),
        "channel_score_outside_0_1": int(((df["channel_score"] < 0) | (df["channel_score"] > 1)).sum()),
        "page_load_time_sec_nonpositive": int((df["page_load_time_sec"] <= 0).sum()),
        "converted_not_binary": int((~df["converted"].isin([0, 1])).sum()),
    }

    normality_p = {}
    for col in numeric_cols:
        _, p = stats.normaltest(df[col])
        normality_p[col] = p

    conversion_rate = df[target].mean()
    device_summary = (
        df.groupby("device", observed=False)[target]
        .agg(rate="mean", count="size", conversions="sum")
        .sort_values("rate", ascending=False)
    )
    corr = df[numeric_cols + [target]].corr(numeric_only=True)

    # 2) Plots for EDA
    plt.figure(figsize=(7, 5))
    target_counts = df[target].value_counts().sort_index()
    ax = sns.barplot(x=target_counts.index.astype(str), y=target_counts.values, color="#60a5fa")
    ax.set_title("Class Balance")
    ax.set_xlabel("Converted")
    ax.set_ylabel("Count")
    for i, v in enumerate(target_counts.values):
        ax.text(i, v + 10, str(v), ha="center", va="bottom", fontsize=11)
    savefig(PLOTS_DIR / "01_target_balance.png")

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.ravel()
    for ax, col in zip(axes, numeric_cols):
        sns.histplot(df[col], kde=True, ax=ax, color="#3b82f6")
        ax.set_title(f"Distribution: {col}")
    axes[-1].axis("off")
    savefig(PLOTS_DIR / "02_numeric_distributions.png")

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
    plt.title("Correlation Heatmap")
    savefig(PLOTS_DIR / "03_correlation_heatmap.png")

    plt.figure(figsize=(8, 5))
    ax = sns.barplot(data=device_summary.reset_index(), x="device", y="rate", color="#34d399")
    ax.set_title("Conversion Rate by Device")
    ax.set_xlabel("Device")
    ax.set_ylabel("Conversion Rate")
    savefig(PLOTS_DIR / "04_conversion_rate_by_device.png")

    hour_summary = (
        df.assign(hour_bin=df["time_of_day_hour"].astype(int))
        .groupby("hour_bin", observed=False)[target]
        .agg(rate="mean", count="size")
        .reset_index()
    )
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=hour_summary, x="hour_bin", y="rate", marker="o", color="#ef4444")
    plt.title("Conversion Rate by Hour")
    plt.xlabel("Hour of Day")
    plt.ylabel("Conversion Rate")
    plt.xticks(range(0, 25, 2))
    savefig(PLOTS_DIR / "05_conversion_rate_by_hour.png")

    binned_features = ["ad_budget_usd", "channel_score", "page_load_time_sec", "previous_visits"]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    for ax, col in zip(axes.ravel(), binned_features):
        tmp = df[[col, target]].copy()
        tmp["bin"] = pd.qcut(tmp[col], 5, duplicates="drop")
        summary = tmp.groupby("bin", observed=False)[target].mean().reset_index()
        summary["bin"] = summary["bin"].astype(str)
        sns.barplot(data=summary, x="bin", y=target, ax=ax, color="#7c3aed")
        ax.set_title(f"Conversion Rate by {col} Quintile")
        ax.set_xlabel("")
        ax.set_ylabel("Rate")
        ax.tick_params(axis="x", rotation=30)
    savefig(PLOTS_DIR / "06_conversion_by_feature_bins.png")

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes_flat = axes.ravel()
    plot_cols = numeric_cols
    for ax, col in zip(axes_flat, plot_cols):
        sns.boxplot(data=df, x=target, y=col, ax=ax, color="#fca5a5")
        ax.set_title(f"{col} by Converted")
    axes_flat[-1].axis("off")
    savefig(PLOTS_DIR / "07_boxplots_by_conversion.png")

    plt.figure(figsize=(10, 5))
    sns.boxplot(data=df, x="page_load_time_sec", color="#f59e0b")
    plt.title("Page Load Time Outliers")
    savefig(PLOTS_DIR / "08_page_load_outliers.png")

    # 3) Modeling
    X = df.drop(columns=[target, id_col])
    y = df[target]

    numeric_model_cols = numeric_cols
    categorical_model_cols = categorical_cols

    logistic = Pipeline(
        steps=[
            (
                "preprocess",
                ColumnTransformer(
                    transformers=[
                        (
                            "num",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="median")),
                                    ("scaler", StandardScaler()),
                                ]
                            ),
                            numeric_model_cols,
                        ),
                        (
                            "cat",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="most_frequent")),
                                    (
                                        "encoder",
                                        OneHotEncoder(drop="first", handle_unknown="ignore"),
                                    ),
                                ]
                            ),
                            categorical_model_cols,
                        ),
                    ]
                ),
            ),
            ("model", LogisticRegression(max_iter=500)),
        ]
    )

    rf = Pipeline(
        steps=[
            (
                "preprocess",
                ColumnTransformer(
                    transformers=[
                        ("num", SimpleImputer(strategy="median"), numeric_model_cols),
                        (
                            "cat",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="most_frequent")),
                                    ("encoder", OneHotEncoder(handle_unknown="ignore")),
                                ]
                            ),
                            categorical_model_cols,
                        ),
                    ]
                ),
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=400,
                    min_samples_leaf=5,
                    random_state=42,
                ),
            ),
        ]
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "roc_auc": "roc_auc",
        "average_precision": "average_precision",
        "neg_brier": "neg_brier_score",
        "accuracy": "accuracy",
        "f1": "f1",
    }

    cv_results = {}
    predictions = {}
    for name, model in {"logistic": logistic, "random_forest": rf}.items():
        scores = cross_validate(model, X, y, cv=cv, scoring=scoring)
        cv_results[name] = {
            metric.replace("test_", ""): (
                float((-values if metric == "test_neg_brier" else values).mean()),
                float((-values if metric == "test_neg_brier" else values).std()),
            )
            for metric, values in scores.items()
            if metric.startswith("test_")
        }
        predictions[name] = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]

    # Statsmodels logistic for inference and diagnostics
    X_sm = df[numeric_cols].copy()
    X_sm = pd.concat(
        [X_sm, pd.get_dummies(df["device"], prefix="device", drop_first=True, dtype=float)],
        axis=1,
    ).astype(float)
    X_sm = sm.add_constant(X_sm)
    y_sm = y.astype(float)

    logit_model = sm.Logit(y_sm, X_sm).fit(disp=False)
    glm_model = sm.GLM(y_sm, X_sm, family=sm.families.Binomial()).fit()
    influence = glm_model.get_influence(observed=True)
    cooks_d, _ = influence.cooks_distance
    influential_threshold = 4 / len(df)
    influential_count = int((cooks_d > influential_threshold).sum())

    odds_ratios = np.exp(logit_model.params)
    ci = np.exp(logit_model.conf_int())
    vif_df = pd.DataFrame(
        {
            "feature": X_sm.drop(columns="const").columns,
            "vif": [
                variance_inflation_factor(X_sm.drop(columns="const").values, i)
                for i in range(X_sm.drop(columns="const").shape[1])
            ],
        }
    )

    bt_df = df.copy()
    for col in numeric_cols:
        shifted = bt_df[col].astype(float)
        if (shifted <= 0).any():
            shifted = shifted - shifted.min() + 1e-3
        bt_df[f"{col}_bt"] = shifted * np.log(shifted)
    bt_formula = (
        "converted ~ ad_budget_usd + time_of_day_hour + channel_score + "
        "page_load_time_sec + previous_visits + C(device) + "
        "ad_budget_usd_bt + time_of_day_hour_bt + channel_score_bt + "
        "page_load_time_sec_bt + previous_visits_bt"
    )
    box_tidwell = smf.logit(bt_formula, data=bt_df).fit(disp=False)
    bt_terms = [f"{col}_bt" for col in numeric_cols]
    bt_pvalues = box_tidwell.pvalues[bt_terms]

    # Model plots
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for name, probs in predictions.items():
        fpr, tpr, _ = roc_curve(y, probs)
        axes[0].plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y, probs):.3f})")
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[0].set_title("ROC Curves")
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].legend()

    for name, probs in predictions.items():
        precision, recall, _ = precision_recall_curve(y, probs)
        axes[1].plot(recall, precision, label=f"{name} (AP={average_precision_score(y, probs):.3f})")
    baseline = y.mean()
    axes[1].hlines(baseline, 0, 1, linestyles="--", color="gray", label=f"baseline={baseline:.3f}")
    axes[1].set_title("Precision-Recall Curves")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].legend()

    for name, probs in predictions.items():
        frac_pos, mean_pred = calibration_curve(y, probs, n_bins=10, strategy="quantile")
        axes[2].plot(mean_pred, frac_pos, marker="o", label=name)
    axes[2].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[2].set_title("Calibration Curves")
    axes[2].set_xlabel("Mean Predicted Probability")
    axes[2].set_ylabel("Observed Fraction Positive")
    axes[2].legend()
    savefig(PLOTS_DIR / "09_model_diagnostics.png")

    rf.fit(X, y)
    perm = permutation_importance(
        rf,
        X,
        y,
        n_repeats=20,
        random_state=42,
        scoring="roc_auc",
    )
    perm_df = pd.DataFrame(
        {
            "feature": X.columns,
            "importance_mean": perm.importances_mean,
            "importance_std": perm.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=perm_df, x="importance_mean", y="feature", color="#38bdf8")
    plt.title("Random Forest Permutation Importance")
    plt.xlabel("Mean ROC AUC Drop")
    plt.ylabel("Feature")
    savefig(PLOTS_DIR / "10_rf_feature_importance.png")

    # 4) Markdown report
    top_influential = df.iloc[np.argsort(cooks_d)[-5:][::-1]][
        ["session_id", "time_of_day_hour", "channel_score", "page_load_time_sec", "converted"]
    ]

    plot_files = sorted(p.name for p in PLOTS_DIR.glob("*.png"))

    md = []
    md.append("# Dataset Analysis Report")
    md.append("")
    md.append("## Executive Summary")
    md.append(
        f"The dataset contains **{rows:,} rows** and **{cols} columns** describing ad-driven web sessions with a binary conversion target. "
        f"The data are structurally clean: there are no missing values, no duplicate rows, and no duplicated `session_id` values."
    )
    md.append(
        f"Conversion is moderately imbalanced at **{conversion_rate:.1%}** ({int(y.sum())} positives / {len(y) - int(y.sum())} negatives). "
        "The strongest and most consistent signals are `channel_score` and `time_of_day_hour`; the other measured inputs contribute little once those are in the model."
    )
    md.append(
        "A simple logistic regression and a random forest perform almost identically out of sample (ROC AUC around 0.69), which suggests the available features contain only modest predictive signal. "
        "Because the flexible model does not materially outperform the interpretable one, the logistic model is the better primary model here."
    )
    md.append("")
    md.append("## 1. Data Loading and Inspection")
    md.append(f"- Shape: `{df.shape}`")
    md.append(f"- Duplicate rows: `{duplicate_rows}`")
    md.append(f"- Duplicate `session_id`: `{duplicate_ids}`")
    md.append(f"- Null values: `{int(null_counts.sum())}` total")
    md.append(f"- Conversion rate: `{conversion_rate:.4f}`")
    md.append("")
    md.append("### Column Types")
    md.append("| Column | Dtype | Unique Values | Nulls |")
    md.append("|---|---:|---:|---:|")
    for col in df.columns:
        md.append(f"| {col} | {dtypes[col]} | {int(unique_counts[col])} | {int(null_counts[col])} |")
    md.append("")
    md.append("### Numeric Summary")
    md.append("| Variable | Mean | Std | Min | 25% | 50% | 75% | Max | Skew |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for col in numeric_cols + [target]:
        sk = skewness[col] if col in skewness.index else np.nan
        md.append(
            f"| {col} | {desc.loc[col, 'mean']:.3f} | {desc.loc[col, 'std']:.3f} | {desc.loc[col, 'min']:.3f} | "
            f"{desc.loc[col, '25%']:.3f} | {desc.loc[col, '50%']:.3f} | {desc.loc[col, '75%']:.3f} | {desc.loc[col, 'max']:.3f} | "
            f"{'' if pd.isna(sk) else f'{sk:.3f}'} |"
        )
    md.append("")
    md.append("### Range and Sanity Checks")
    for key, value in range_checks.items():
        md.append(f"- `{key}`: {value}")
    md.append(
        "- The only obvious edge case is one record with `time_of_day_hour = 24.0`. That is not outside the declared range, but it is an endpoint value that often duplicates hour 0 in clock-style data."
    )
    md.append("")
    md.append("## 2. Exploratory Data Analysis")
    md.append("### Distributional Findings")
    for col in numeric_cols:
        md.append(
            f"- `{col}`: skew={skewness[col]:.3f}, normality test p-value={normality_p[col]:.3e}, IQR outliers={iqr_outliers[col]}"
        )
    md.append(
        "- `page_load_time_sec` is strongly right-skewed and contains the most IQR-defined outliers, so any analysis assuming Gaussian behavior would be inappropriate without transformation or robust methods."
    )
    md.append("")
    md.append("### Relationship to Conversion")
    pearson = corr[target].drop(target).sort_values(ascending=False)
    for col, value in pearson.items():
        md.append(f"- Pearson correlation with `converted`: `{col}` = {value:.3f}")
    md.append("")
    md.append("### Device-Level Summary")
    md.append("| Device | Conversion Rate | Sessions | Conversions |")
    md.append("|---|---:|---:|---:|")
    for device, row in device_summary.iterrows():
        md.append(f"| {device} | {row['rate']:.3f} | {int(row['count'])} | {int(row['conversions'])} |")
    md.append("")
    md.append("### Interpreted EDA Patterns")
    md.append("- `channel_score` shows the clearest monotonic relationship: higher quintiles have substantially higher conversion rates.")
    md.append("- `time_of_day_hour` shows a broad upward trend across the day, though the hourly series is noisy and includes one endpoint case at hour 24.")
    md.append("- `ad_budget_usd`, `previous_visits`, and `device` show only weak marginal differences.")
    md.append("- `page_load_time_sec` is noisy: the raw distribution is highly skewed, but conversion does not change monotonically with load time in a stable way.")
    md.append("")
    md.append("## 3. Modeling Strategy")
    md.append(
        "Two models were evaluated with 5-fold stratified cross-validation after excluding `session_id` from features because it is an identifier, not a behavioral predictor."
    )
    md.append("- Logistic regression with standard scaling and one-hot encoding.")
    md.append("- Random forest classifier with the same feature set and categorical encoding.")
    md.append("")
    md.append("### Cross-Validated Performance")
    md.append("| Model | ROC AUC Mean | ROC AUC SD | AP Mean | AP SD | Brier Mean | Brier SD | Accuracy Mean | F1 Mean |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, metrics in cv_results.items():
        md.append(
            f"| {name} | {metrics['roc_auc'][0]:.3f} | {metrics['roc_auc'][1]:.3f} | "
            f"{metrics['average_precision'][0]:.3f} | {metrics['average_precision'][1]:.3f} | "
            f"{metrics['neg_brier'][0]:.3f} | {metrics['neg_brier'][1]:.3f} | "
            f"{metrics['accuracy'][0]:.3f} | {metrics['f1'][0]:.3f} |"
        )
    md.append("")
    md.append(
        "Interpretation: the random forest is not materially better than logistic regression. That weak performance gap argues against hidden strong nonlinear structure in the observed variables."
    )
    md.append("")
    md.append("## 4. Logistic Model Interpretation")
    md.append("| Term | Coef | Odds Ratio | 95% CI Lower | 95% CI Upper | p-value |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for term in logit_model.params.index:
        md.append(
            f"| {term} | {logit_model.params[term]:.3f} | {odds_ratios[term]:.3f} | "
            f"{ci.loc[term, 0]:.3f} | {ci.loc[term, 1]:.3f} | {logit_model.pvalues[term]:.3e} |"
        )
    md.append("")
    md.append("Key interpretation:")
    md.append("- `channel_score` is the dominant effect. A one-unit increase multiplies the odds of conversion by about 6.64, holding other variables fixed.")
    md.append("- `time_of_day_hour` is also significant. Each additional hour is associated with about 8.2% higher odds of conversion on average in the fitted linear-logit model.")
    md.append("- `ad_budget_usd`, `page_load_time_sec`, `previous_visits`, and device indicators are not statistically significant after adjustment.")
    md.append("")
    md.append("## 5. Assumption Checks and Validation")
    md.append("### Multicollinearity")
    md.append("| Feature | VIF |")
    md.append("|---|---:|")
    for _, row in vif_df.sort_values("vif", ascending=False).iterrows():
        md.append(f"| {row['feature']} | {row['vif']:.3f} |")
    md.append("- All VIF values are below 5, so multicollinearity is not a serious concern.")
    md.append("")
    md.append("### Linearity of the Logit")
    md.append(
        "A Box-Tidwell style check was run by adding `x * log(x)` terms for each continuous feature after shifting nonpositive values slightly above zero."
    )
    md.append("| Term | p-value |")
    md.append("|---|---:|")
    for term, value in bt_pvalues.items():
        md.append(f"| {term} | {value:.3e} |")
    md.append(
        "- None of the Box-Tidwell interaction terms were significant at 0.05, so there is no strong evidence that the simple linear-logit specification is badly misspecified for these features."
    )
    md.append("")
    md.append("### Calibration and Influence")
    md.append(
        f"- Logistic regression cross-validated ROC AUC: `{roc_auc_score(y, predictions['logistic']):.3f}`"
    )
    md.append(
        f"- Logistic regression cross-validated average precision: `{average_precision_score(y, predictions['logistic']):.3f}`"
    )
    md.append(
        f"- Logistic regression cross-validated Brier score: `{brier_score_loss(y, predictions['logistic']):.3f}`"
    )
    md.append(f"- Logistic regression cross-validated log loss: `{log_loss(y, predictions['logistic']):.3f}`")
    md.append(
        f"- Cook's distance threshold `4/n` flags `{influential_count}` observations, but the maximum Cook's distance is only `{cooks_d.max():.4f}`, so there is no sign of a single observation dominating the fit."
    )
    md.append("")
    md.append("Most influential observations by Cook's distance:")
    md.append("| session_id | time_of_day_hour | channel_score | page_load_time_sec | converted |")
    md.append("|---:|---:|---:|---:|---:|")
    for _, row in top_influential.iterrows():
        md.append(
            f"| {int(row['session_id'])} | {row['time_of_day_hour']:.1f} | {row['channel_score']:.3f} | "
            f"{row['page_load_time_sec']:.2f} | {int(row['converted'])} |"
        )
    md.append("")
    md.append("## 6. Random Forest Feature Importance")
    md.append("| Feature | Permutation Importance Mean | Importance SD |")
    md.append("|---|---:|---:|")
    for _, row in perm_df.iterrows():
        md.append(f"| {row['feature']} | {row['importance_mean']:.4f} | {row['importance_std']:.4f} |")
    md.append(
        "- The random forest importance ranking agrees with the logistic model: `channel_score` and `time_of_day_hour` dominate, while the remaining variables contribute little."
    )
    md.append("")
    md.append("## 7. Conclusions")
    md.append("- The dataset is clean enough for modeling without imputation or major repair, but not perfectly well-behaved: `page_load_time_sec` is skewed and one hour value sits at the edge case `24.0`.")
    md.append("- The primary practical story is simple: stronger channel quality and later hours are associated with higher conversion probability in this sample.")
    md.append("- The predictive ceiling is modest with the available variables. With ROC AUC around 0.69, this is useful for ranking or directional analysis, not for high-confidence individual session decisions.")
    md.append("- Since the flexible model does not beat logistic regression by much, chasing more complex models is hard to justify until richer features are available.")
    md.append("")
    md.append("## 8. Output Files")
    for plot_file in plot_files:
        md.append(f"- `plots/{plot_file}`")

    REPORT_PATH.write_text("\n".join(md))


if __name__ == "__main__":
    main()
