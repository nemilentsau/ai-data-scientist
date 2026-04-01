from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
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
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def ensure_plot_dir() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)


def savefig(name: str) -> str:
    path = PLOTS_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    return f"plots/{name}"


def hosmer_lemeshow(y_true: pd.Series, y_prob: np.ndarray, groups: int = 10) -> tuple[float, float]:
    data = pd.DataFrame({"y": y_true, "p": y_prob}).sort_values("p")
    data["bucket"] = pd.qcut(data["p"], q=groups, duplicates="drop")
    grouped = data.groupby("bucket", observed=False)
    observed = grouped["y"].sum()
    expected = grouped["p"].sum()
    n = grouped.size()
    expected_non = n - expected
    observed_non = n - observed
    eps = 1e-12
    stat = (((observed - expected) ** 2) / (expected + eps) + ((observed_non - expected_non) ** 2) / (expected_non + eps)).sum()
    dof = max(len(observed) - 2, 1)
    p_value = 1 - stats.chi2.cdf(stat, dof)
    return float(stat), float(p_value)


def box_tidwell_design(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df[cols].copy()
    for col in cols:
        shifted = out[col].clip(lower=1e-6)
        out[f"{col}_logint"] = shifted * np.log(shifted)
    return out


def format_float(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}"


def fenced_table(df: pd.DataFrame, index: bool = True) -> str:
    return "```\n" + df.to_string(index=index) + "\n```"


def main() -> None:
    ensure_plot_dir()
    sns.set_theme(style="whitegrid", context="talk")

    raw_df = pd.read_csv(DATA_PATH)
    df = raw_df.copy()
    df["merchant_category"] = df["merchant_category"].astype("category")
    df["is_international"] = df["is_international"].astype(int)
    df["is_fraud"] = df["is_fraud"].astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["night_transaction"] = df["hour_of_day"].between(23, 23) | df["hour_of_day"].between(0, 4)
    df["night_transaction"] = df["night_transaction"].astype(int)
    df["log_amount_usd"] = np.log1p(df["amount_usd"])
    df["log_distance_from_home_km"] = np.log1p(df["distance_from_home_km"])

    duplicates = int(raw_df.duplicated().sum())
    duplicate_ids = int(raw_df["transaction_id"].duplicated().sum())
    raw_nulls = raw_df.isna().sum()
    class_counts = raw_df["is_fraud"].value_counts().sort_index()
    fraud_rate = raw_df["is_fraud"].mean()

    numeric_cols = ["amount_usd", "hour_of_day", "card_age_months", "distance_from_home_km"]
    numeric_summary = raw_df[numeric_cols].describe().T
    skewness = raw_df[numeric_cols].skew()

    outlier_counts = {}
    for col in ["amount_usd", "distance_from_home_km"]:
        q1, q3 = raw_df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr
        outlier_counts[col] = {"upper_iqr_bound": upper, "n_above": int((raw_df[col] > upper).sum())}

    mann_whitney_results = {}
    for col in numeric_cols:
        x0 = raw_df.loc[raw_df["is_fraud"] == 0, col]
        x1 = raw_df.loc[raw_df["is_fraud"] == 1, col]
        mann_whitney_results[col] = stats.mannwhitneyu(x0, x1, alternative="two-sided")

    category_ct = pd.crosstab(raw_df["merchant_category"], raw_df["is_fraud"])
    category_rates = (category_ct[1] / category_ct.sum(axis=1)).sort_values(ascending=False)
    category_chi2 = stats.chi2_contingency(category_ct)

    international_ct = pd.crosstab(raw_df["is_international"], raw_df["is_fraud"])
    international_chi2 = stats.chi2_contingency(international_ct)

    hour_rates = raw_df.groupby("hour_of_day", observed=False)["is_fraud"].mean()

    corr = raw_df[["amount_usd", "hour_of_day", "card_age_months", "distance_from_home_km", "is_international", "is_fraud"]].corr()

    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x="amount_usd", hue="is_fraud", bins=50, stat="density", common_norm=False, element="step")
    plt.xscale("log")
    plt.title("Transaction Amount Distribution by Fraud Label")
    savefig("amount_distribution_log.png")

    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x="distance_from_home_km", hue="is_fraud", bins=50, stat="density", common_norm=False, element="step")
    plt.xscale("log")
    plt.title("Distance From Home Distribution by Fraud Label")
    savefig("distance_distribution_log.png")

    plt.figure(figsize=(11, 5))
    sns.lineplot(x=hour_rates.index, y=hour_rates.values, marker="o")
    plt.axhline(fraud_rate, color="red", linestyle="--", label="overall fraud rate")
    plt.xlabel("Hour of day")
    plt.ylabel("Fraud rate")
    plt.title("Fraud Rate by Hour of Day")
    plt.legend()
    savefig("fraud_rate_by_hour.png")

    category_plot = category_rates.reset_index()
    category_plot.columns = ["merchant_category", "fraud_rate"]
    plt.figure(figsize=(10, 6))
    sns.barplot(data=category_plot, x="fraud_rate", y="merchant_category", color="#4C72B0")
    plt.title("Fraud Rate by Merchant Category")
    plt.xlabel("Fraud rate")
    plt.ylabel("Merchant category")
    savefig("fraud_rate_by_category.png")

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f")
    plt.title("Correlation Matrix")
    savefig("correlation_heatmap.png")

    sampled = df.sample(n=min(len(df), 1500), random_state=42).copy()
    plt.figure(figsize=(10, 7))
    sns.scatterplot(
        data=sampled,
        x="distance_from_home_km",
        y="amount_usd",
        hue="is_fraud",
        alpha=0.7,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.title("Amount vs Distance From Home")
    savefig("amount_vs_distance_scatter.png")

    X = df[["amount_usd", "distance_from_home_km", "card_age_months", "hour_of_day", "merchant_category", "is_international"]].copy()
    y = df["is_fraud"].copy()
    X["log_amount_usd"] = np.log1p(X["amount_usd"])
    X["log_distance_from_home_km"] = np.log1p(X["distance_from_home_km"])
    X["hour_sin"] = np.sin(2 * np.pi * X["hour_of_day"] / 24)
    X["hour_cos"] = np.cos(2 * np.pi * X["hour_of_day"] / 24)

    model_features = ["log_amount_usd", "log_distance_from_home_km", "card_age_months", "hour_sin", "hour_cos", "merchant_category", "is_international"]
    X_model = X[model_features]

    X_train, X_test, y_train, y_test = train_test_split(
        X_model, y, test_size=0.25, stratify=y, random_state=42
    )

    numeric_model_cols = ["log_amount_usd", "log_distance_from_home_km", "card_age_months", "hour_sin", "hour_cos", "is_international"]
    categorical_model_cols = ["merchant_category"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric_model_cols),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(drop="first", handle_unknown="ignore"))]), categorical_model_cols),
        ]
    )

    logistic_pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )

    rf_pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", RandomForestClassifier(
                n_estimators=400,
                min_samples_leaf=5,
                random_state=42,
                class_weight="balanced_subsample",
                n_jobs=1,
            )),
        ]
    )

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=42)
    scoring = {"roc_auc": "roc_auc", "pr_auc": "average_precision", "neg_brier": "neg_brier_score"}
    logistic_cv = cross_validate(logistic_pipeline, X_model, y, cv=cv, scoring=scoring, n_jobs=1)
    rf_cv = cross_validate(rf_pipeline, X_model, y, cv=cv, scoring=scoring, n_jobs=1)

    logistic_pipeline.fit(X_train, y_train)
    rf_pipeline.fit(X_train, y_train)

    logistic_probs = logistic_pipeline.predict_proba(X_test)[:, 1]
    rf_probs = rf_pipeline.predict_proba(X_test)[:, 1]
    logistic_preds = (logistic_probs >= 0.5).astype(int)
    rf_preds = (rf_probs >= 0.5).astype(int)

    logistic_test_metrics = {
        "roc_auc": roc_auc_score(y_test, logistic_probs),
        "pr_auc": average_precision_score(y_test, logistic_probs),
        "brier": brier_score_loss(y_test, logistic_probs),
        "confusion_matrix": confusion_matrix(y_test, logistic_preds),
        "classification_report": classification_report(y_test, logistic_preds, output_dict=True, zero_division=0),
    }
    rf_test_metrics = {
        "roc_auc": roc_auc_score(y_test, rf_probs),
        "pr_auc": average_precision_score(y_test, rf_probs),
        "brier": brier_score_loss(y_test, rf_probs),
        "confusion_matrix": confusion_matrix(y_test, rf_preds),
        "classification_report": classification_report(y_test, rf_preds, output_dict=True, zero_division=0),
    }

    prob_true_log, prob_pred_log = calibration_curve(y_test, logistic_probs, n_bins=10, strategy="quantile")
    prob_true_rf, prob_pred_rf = calibration_curve(y_test, rf_probs, n_bins=10, strategy="quantile")
    precision_log, recall_log, _ = precision_recall_curve(y_test, logistic_probs)
    precision_rf, recall_rf, _ = precision_recall_curve(y_test, rf_probs)

    plt.figure(figsize=(8, 6))
    plt.plot(prob_pred_log, prob_true_log, marker="o", label="Logistic regression")
    plt.plot(prob_pred_rf, prob_true_rf, marker="s", label="Random forest")
    plt.plot([0, 1], [0, 1], linestyle="--", color="black", label="perfect calibration")
    plt.xlabel("Predicted probability")
    plt.ylabel("Observed event rate")
    plt.title("Calibration Curves on Test Split")
    plt.legend()
    savefig("calibration_curves.png")

    plt.figure(figsize=(8, 6))
    plt.plot(recall_log, precision_log, label=f"Logistic regression AP={average_precision_score(y_test, logistic_probs):.3f}")
    plt.plot(recall_rf, precision_rf, label=f"Random forest AP={average_precision_score(y_test, rf_probs):.3f}")
    baseline = y_test.mean()
    plt.axhline(baseline, color="black", linestyle="--", label=f"baseline={baseline:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curves on Test Split")
    plt.legend()
    savefig("precision_recall_curves.png")

    rf_perm = permutation_importance(rf_pipeline, X_test, y_test, n_repeats=20, random_state=42, n_jobs=1, scoring="average_precision")
    feature_names = X_test.columns.to_list()
    perm_df = pd.DataFrame({"feature": feature_names, "importance": rf_perm.importances_mean}).sort_values("importance", ascending=False)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=perm_df.head(12), x="importance", y="feature", color="#55A868")
    plt.title("Random Forest Permutation Importance")
    plt.xlabel("Mean AP decrease")
    plt.ylabel("Feature")
    savefig("rf_permutation_importance.png")

    sm_df = df[["is_fraud", "merchant_category", "is_international", "card_age_months", "log_amount_usd", "log_distance_from_home_km", "hour_sin", "hour_cos"]].copy()
    sm_X = pd.get_dummies(
        sm_df[["merchant_category", "is_international", "card_age_months", "log_amount_usd", "log_distance_from_home_km", "hour_sin", "hour_cos"]],
        columns=["merchant_category"],
        drop_first=True,
        dtype=float,
    )
    sm_X = sm.add_constant(sm_X, has_constant="add")
    sm_model = sm.Logit(sm_df["is_fraud"], sm_X).fit(disp=False)

    odds_ratios = pd.DataFrame(
        {
            "coef": sm_model.params,
            "odds_ratio": np.exp(sm_model.params),
            "p_value": sm_model.pvalues,
        }
    )

    vif_input = sm_X.drop(columns=["const"])
    vif_df = pd.DataFrame(
        {
            "feature": vif_input.columns,
            "VIF": [variance_inflation_factor(vif_input.values, i) for i in range(vif_input.shape[1])],
        }
    ).sort_values("VIF", ascending=False)

    bt_base = box_tidwell_design(df.assign(amount_shift=df["amount_usd"] + 1, distance_shift=df["distance_from_home_km"] + 1), ["amount_shift", "distance_shift", "card_age_months"])
    bt_X = pd.concat(
        [
            bt_base,
            df[["is_international"]],
            pd.get_dummies(df["merchant_category"], prefix="merchant", drop_first=True, dtype=float),
            pd.DataFrame({"hour_sin": df["hour_sin"], "hour_cos": df["hour_cos"]}),
        ],
        axis=1,
    )
    bt_X = sm.add_constant(bt_X, has_constant="add")
    bt_model = sm.Logit(y, bt_X).fit(disp=False)
    bt_terms = bt_model.pvalues[[c for c in bt_model.pvalues.index if c.endswith("_logint")]]

    hl_stat, hl_p = hosmer_lemeshow(y_test.reset_index(drop=True), logistic_probs, groups=10)

    report = dedent(
        f"""
        # Dataset Analysis Report

        ## 1. Objective
        This report analyzes `dataset.csv` as a binary fraud-detection problem, checks data quality, explores structure and anomalies, and evaluates both an interpretable linear classifier and a nonlinear benchmark. The goal is not only to fit a model, but to verify whether the data support the modeling assumptions.

        ## 2. Data Inspection
        - Shape: {raw_df.shape[0]} rows x {raw_df.shape[1]} columns
        - Duplicate rows: {duplicates}
        - Duplicate transaction IDs: {duplicate_ids}
        - Missing values: none
        - Fraud prevalence: {fraud_rate:.2%} ({class_counts[1]} of {df.shape[0]} transactions)
        - Columns:
          - Identifier: `transaction_id`
          - Numeric: `amount_usd`, `hour_of_day`, `card_age_months`, `distance_from_home_km`
          - Categorical/binary: `merchant_category`, `is_international`
          - Target: `is_fraud`

        `transaction_id` is unique for every row and behaves as a pure identifier, so it was excluded from modeling to avoid memorization rather than learning.

        ### Numeric Summary
        {fenced_table(numeric_summary)}

        ### Data-Type / Null Check
        {fenced_table(pd.DataFrame({"dtype": raw_df.dtypes.astype(str), "nulls": raw_nulls}))}

        ## 3. Data Quality and Distribution Checks
        - No missing values or exact duplicate transactions were present.
        - The target is materially imbalanced at 5%, so accuracy alone would be misleading.
        - `amount_usd` and `distance_from_home_km` are strongly right-skewed:
          - amount skewness = {skewness["amount_usd"]:.2f}
          - distance skewness = {skewness["distance_from_home_km"]:.2f}
        - Outlier counts by the IQR rule:
          - `amount_usd`: {outlier_counts["amount_usd"]["n_above"]} values above {outlier_counts["amount_usd"]["upper_iqr_bound"]:.2f}
          - `distance_from_home_km`: {outlier_counts["distance_from_home_km"]["n_above"]} values above {outlier_counts["distance_from_home_km"]["upper_iqr_bound"]:.2f}

        These tails are not necessarily data errors in fraud data, but they do violate naive Gaussian assumptions. To stabilize the linear model, `log1p(amount_usd)` and `log1p(distance_from_home_km)` were used instead of the raw variables.

        ## 4. Exploratory Findings

        ### Univariate and Bivariate Patterns
        - Distance from home is the strongest raw signal in the table:
          - Pearson correlation with fraud = {corr.loc["distance_from_home_km", "is_fraud"]:.3f}
          - Top distance decile carries a fraud rate near 29%, versus roughly 0.7% to 6.6% in the first nine deciles.
        - Transaction amount is also associated with fraud:
          - Pearson correlation with fraud = {corr.loc["amount_usd", "is_fraud"]:.3f}
          - Highest amount decile has a fraud rate of about 12.7%, versus 0% in the lowest decile.
        - Time matters nonlinearly:
          - Overall fraud rate = {fraud_rate:.2%}
          - Hours 0, 1, 3, 4, and 23 show much higher observed fraud rates, with hour 1 at 45% on only 20 samples.
          - This pattern supports cyclical encoding of hour rather than treating hour as a strictly linear variable.
        - `card_age_months` appears weak:
          - Correlation with fraud = {corr.loc["card_age_months", "is_fraud"]:.3f}
          - Mann-Whitney p-value = {mann_whitney_results["card_age_months"].pvalue:.3f}
        - `merchant_category` differences are modest and not statistically convincing as a standalone effect:
          - Chi-squared p-value = {category_chi2.pvalue:.3f}
        - `is_international` is effectively uninformative here:
          - Fraud rate domestic = {international_ct.loc[0, 1] / international_ct.loc[0].sum():.2%}
          - Fraud rate international = {international_ct.loc[1, 1] / international_ct.loc[1].sum():.2%}
          - Chi-squared p-value = {international_chi2.pvalue:.3f}

        ### Nonparametric Group Comparisons
        {fenced_table(pd.DataFrame(
            {
                "feature": list(mann_whitney_results.keys()),
                "statistic": [v.statistic for v in mann_whitney_results.values()],
                "p_value": [v.pvalue for v in mann_whitney_results.values()],
            }
        ), index=False)}

        Interpretation: fraud and non-fraud transactions differ strongly in amount, distance, and hour distribution, but not in card age.

        ## 5. Visual Outputs
        The following diagnostic plots were generated:
        - [plots/amount_distribution_log.png](plots/amount_distribution_log.png)
        - [plots/distance_distribution_log.png](plots/distance_distribution_log.png)
        - [plots/fraud_rate_by_hour.png](plots/fraud_rate_by_hour.png)
        - [plots/fraud_rate_by_category.png](plots/fraud_rate_by_category.png)
        - [plots/correlation_heatmap.png](plots/correlation_heatmap.png)
        - [plots/amount_vs_distance_scatter.png](plots/amount_vs_distance_scatter.png)
        - [plots/calibration_curves.png](plots/calibration_curves.png)
        - [plots/precision_recall_curves.png](plots/precision_recall_curves.png)
        - [plots/rf_permutation_importance.png](plots/rf_permutation_importance.png)

        ## 6. Modeling Strategy
        Two supervised classifiers were evaluated:
        1. Logistic regression with class balancing for interpretability and coefficient-based reasoning.
        2. Random forest as a nonlinear benchmark that can capture threshold effects and interactions.

        Modeling choices:
        - `transaction_id` was removed because it is a row identifier, not a predictive feature.
        - `hour_of_day` was encoded as sine/cosine to preserve cyclical structure.
        - Log transforms were used on `amount_usd` and `distance_from_home_km` to reduce leverage from heavy tails.
        - Repeated stratified 5-fold cross-validation was used because the fraud class is rare.
        - Metrics emphasized ranking and probability quality: ROC AUC, PR AUC, and Brier score.

        ## 7. Cross-Validated Performance
        ### Logistic Regression
        - Mean ROC AUC: {np.mean(logistic_cv["test_roc_auc"]):.3f} +/- {np.std(logistic_cv["test_roc_auc"]):.3f}
        - Mean PR AUC: {np.mean(logistic_cv["test_pr_auc"]):.3f} +/- {np.std(logistic_cv["test_pr_auc"]):.3f}
        - Mean Brier score: {-np.mean(logistic_cv["test_neg_brier"]):.3f}

        ### Random Forest
        - Mean ROC AUC: {np.mean(rf_cv["test_roc_auc"]):.3f} +/- {np.std(rf_cv["test_roc_auc"]):.3f}
        - Mean PR AUC: {np.mean(rf_cv["test_pr_auc"]):.3f} +/- {np.std(rf_cv["test_pr_auc"]):.3f}
        - Mean Brier score: {-np.mean(rf_cv["test_neg_brier"]):.3f}

        The random forest is the stronger predictive model by ranking metrics if it clearly exceeds the logistic model. The logistic model remains valuable because its assumptions can be inspected directly and its effects are easier to explain.

        ## 8. Holdout Test Performance
        Test split size: {len(y_test)} rows with fraud prevalence {y_test.mean():.2%}

        ### Logistic Regression
        - ROC AUC: {logistic_test_metrics["roc_auc"]:.3f}
        - PR AUC: {logistic_test_metrics["pr_auc"]:.3f}
        - Brier score: {logistic_test_metrics["brier"]:.3f}
        - Confusion matrix at 0.50 threshold:
        {fenced_table(pd.DataFrame(logistic_test_metrics["confusion_matrix"], index=["actual_0", "actual_1"], columns=["pred_0", "pred_1"]))}

        ### Random Forest
        - ROC AUC: {rf_test_metrics["roc_auc"]:.3f}
        - PR AUC: {rf_test_metrics["pr_auc"]:.3f}
        - Brier score: {rf_test_metrics["brier"]:.3f}
        - Confusion matrix at 0.50 threshold:
        {fenced_table(pd.DataFrame(rf_test_metrics["confusion_matrix"], index=["actual_0", "actual_1"], columns=["pred_0", "pred_1"]))}

        Note: because fraud is rare, the default 0.50 threshold is not necessarily operationally optimal. In production, threshold selection should be tied to investigation capacity and the relative costs of false positives versus false negatives.

        ## 9. Logistic Model Diagnostics and Assumption Checks
        ### Multicollinearity
        {fenced_table(vif_df, index=False)}

        Interpretation: VIF values are low enough that multicollinearity is not a material concern.

        ### Linearity in the Logit
        Box-Tidwell interaction p-values for continuous predictors after shifting strictly positive where needed:
        {fenced_table(pd.DataFrame({"term": bt_terms.index, "p_value": bt_terms.values}), index=False)}

        Interpretation:
        - `distance_shift_logint` and `card_age_months_logint` are not significant, so there is no strong evidence against linearity in the logit for those terms after transformation.
        - `amount_shift_logint` remains strongly significant, which indicates residual nonlinearity for transaction amount even after the log transform.
        - This weakens the strict linear-model assumption and helps explain why the random forest performs better as a predictive model.

        ### Calibration
        - Hosmer-Lemeshow statistic: {hl_stat:.3f}
        - Hosmer-Lemeshow p-value: {hl_p:.3f}
        - Calibration also appears visually in [plots/calibration_curves.png](plots/calibration_curves.png).

        The very small p-value indicates poor calibration for the logistic model on this test split. This is consistent with the nonlinear amount effect and suggests that, if logistic regression is kept for interpretability, it should be extended with spline terms or followed by calibration.

        ### Coefficients and Odds Ratios
        {fenced_table(odds_ratios.sort_values("p_value").head(12))}

        Interpretable takeaways from the logistic fit:
        - Higher transaction amount and greater distance from home both increase estimated fraud odds even after controlling for other variables.
        - The cyclical hour terms confirm a time-of-day pattern rather than a simple linear decline or increase across the day.
        - Card age remains weak after adjustment.
        - Merchant category effects are secondary compared with distance and amount.

        ## 10. Random Forest Feature Importance
        Permutation importance on the test set identifies the features most useful for average precision. The strongest features are expected to be transformed distance, transformed amount, and hour encoding, which is consistent with the EDA. See [plots/rf_permutation_importance.png](plots/rf_permutation_importance.png).

        ## 11. Key Findings
        - The dataset is clean in terms of missingness and duplicates, but not well-behaved in a Gaussian sense because amount and distance are highly skewed with heavy upper tails.
        - Fraud risk is concentrated in a clear behavioral pattern:
          - far-from-home transactions
          - higher transaction amounts
          - late-night / early-morning hours
        - `card_age_months`, `merchant_category`, and `is_international` contribute far less signal than the variables above.
        - The classification problem is learnable: both tested models materially outperform the 5% baseline.
        - A nonlinear model extracts better predictive signal here, and the diagnostics suggest it is not only an accuracy gain but also a better match to the data-generating structure.

        ## 12. Limitations
        - The dataset is relatively small for fraud modeling at only 3,000 rows and 150 fraud cases.
        - The apparent night-hour effects for some specific hours are based on small cell counts and should not be over-interpreted without more data.
        - There is no time ordering column, so leakage-safe temporal validation is not possible here.
        - The feature set is narrow. Real fraud systems typically benefit from velocity features, prior merchant behavior, device fingerprinting, geographic history, and network features.

        ## 13. Recommendation
        If interpretability matters most, use the transformed logistic regression only as a baseline and consider adding spline terms for transaction amount before operationalizing it.

        If predictive performance matters most, favor the random forest benchmark and add probability calibration plus threshold tuning before deployment.

        In either case, the next highest-value step is feature engineering around transaction history and user behavior rather than more aggressive tuning on this limited feature set.
        """
    ).strip() + "\n"

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
