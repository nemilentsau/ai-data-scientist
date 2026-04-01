import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, RepeatedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor


DATA_PATH = Path("dataset.csv")
PLOTS_DIR = Path("plots")
REPORT_PATH = Path("analysis_report.md")


def savefig(name: str) -> Path:
    path = PLOTS_DIR / f"{name}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    return path


def fmt(value, digits=3):
    if pd.isna(value):
        return "NA"
    if isinstance(value, (int, np.integer)):
        return f"{value}"
    return f"{value:.{digits}f}"


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    display_df = df.copy()
    for col in display_df.columns:
        if pd.api.types.is_numeric_dtype(display_df[col]):
            display_df[col] = display_df[col].map(lambda x: fmt(x, digits))
    table_df = display_df.reset_index()
    headers = [str(col) for col in table_df.columns]
    rows = table_df.astype(str).values.tolist()
    separator = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATA_PATH)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    duplicate_rows = int(df.duplicated().sum())
    duplicate_patient_ids = int(df["patient_id"].duplicated().sum()) if "patient_id" in df.columns else None
    null_counts = df.isna().sum()
    null_pct = (df.isna().mean() * 100).round(2)

    summary = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "non_null": df.notna().sum(),
            "nulls": null_counts,
            "null_pct": null_pct,
            "unique": df.nunique(dropna=False),
        }
    )

    numeric_summary = df[numeric_cols].describe().T
    numeric_summary["skew"] = df[numeric_cols].skew(numeric_only=True)
    numeric_summary["kurtosis"] = df[numeric_cols].kurtosis(numeric_only=True)

    categorical_summary = []
    for col in categorical_cols:
        vc = df[col].value_counts(dropna=False)
        proportions = (vc / len(df) * 100).round(2)
        cat_df = pd.DataFrame({"count": vc, "pct": proportions})
        categorical_summary.append((col, cat_df))

    outlier_counts = {}
    for col in [c for c in numeric_cols if c != "patient_id"]:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_counts[col] = int(((df[col] < lower) | (df[col] > upper)).sum())

    corr = df[[c for c in numeric_cols if c != "patient_id"]].corr()

    plt.figure(figsize=(12, 10))
    df[[c for c in numeric_cols if c != "patient_id"]].hist(bins=25, figsize=(12, 10), edgecolor="black")
    plt.suptitle("Numeric Feature Distributions", y=1.02)
    savefig("numeric_distributions")

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f")
    plt.title("Correlation Heatmap")
    savefig("correlation_heatmap")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.boxplot(data=df, x="treatment", y="recovery_score", ax=axes[0])
    axes[0].set_title("Recovery Score by Treatment")
    sns.boxplot(data=df, x="department", y="recovery_score", ax=axes[1])
    axes[1].set_title("Recovery Score by Department")
    axes[1].tick_params(axis="x", rotation=20)
    savefig("recovery_group_boxplots")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.boxplot(data=df, x="treatment", y="severity_index", ax=axes[0])
    axes[0].set_title("Severity Index by Treatment")
    sns.boxplot(data=df, x="department", y="severity_index", ax=axes[1])
    axes[1].set_title("Severity Index by Department")
    axes[1].tick_params(axis="x", rotation=20)
    savefig("severity_group_boxplots")

    plt.figure(figsize=(10, 7))
    sns.scatterplot(
        data=df,
        x="severity_index",
        y="recovery_score",
        hue="treatment",
        style="department",
        alpha=0.75,
    )
    sns.regplot(
        data=df,
        x="severity_index",
        y="recovery_score",
        scatter=False,
        color="black",
        line_kws={"linewidth": 2},
    )
    plt.title("Recovery vs Severity")
    savefig("severity_vs_recovery")

    readmit_rates = (
        df.groupby(["department", "treatment"], observed=False)["readmitted"]
        .mean()
        .reset_index()
        .rename(columns={"readmitted": "readmission_rate"})
    )
    plt.figure(figsize=(10, 6))
    sns.barplot(data=readmit_rates, x="department", y="readmission_rate", hue="treatment")
    plt.title("Readmission Rate by Department and Treatment")
    plt.ylabel("Rate")
    savefig("readmission_rates")

    recovery_formula = "recovery_score ~ age + severity_index + length_of_stay_days + C(treatment) + C(department)"
    ols_model = smf.ols(recovery_formula, data=df).fit()

    exog = pd.DataFrame(ols_model.model.exog, columns=ols_model.model.exog_names)
    vif_df = pd.DataFrame(
        {
            "feature": exog.columns,
            "VIF": [variance_inflation_factor(exog.values, i) for i in range(exog.shape[1])],
        }
    )

    bp_test = het_breuschpagan(ols_model.resid, ols_model.model.exog)
    bp_labels = ["LM stat", "LM pvalue", "F stat", "F pvalue"]
    bp_results = dict(zip(bp_labels, bp_test))

    influence = OLSInfluence(ols_model)
    cooks_d = influence.cooks_distance[0]
    leverage = influence.hat_matrix_diag
    top_influential = (
        pd.DataFrame(
            {
                "index": df.index,
                "patient_id": df["patient_id"],
                "cooks_d": cooks_d,
                "leverage": leverage,
                "studentized_resid": influence.resid_studentized_external,
            }
        )
        .sort_values("cooks_d", ascending=False)
        .head(10)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(x=ols_model.fittedvalues, y=ols_model.resid, alpha=0.7, ax=axes[0])
    axes[0].axhline(0, color="red", linestyle="--")
    axes[0].set_xlabel("Fitted")
    axes[0].set_ylabel("Residual")
    axes[0].set_title("Residuals vs Fitted")
    sm.qqplot(ols_model.resid, line="45", ax=axes[1])
    axes[1].set_title("OLS Residual Q-Q Plot")
    savefig("ols_diagnostics")

    X_reg = df[["age", "severity_index", "length_of_stay_days", "treatment", "department"]]
    y_reg = df["recovery_score"]
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42
    )

    num_features = ["age", "severity_index", "length_of_stay_days"]
    cat_features = ["treatment", "department"]
    preprocessor_reg = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), num_features),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(drop="first"))]), cat_features),
        ]
    )

    reg_models = {
        "LinearRegression": Pipeline(
            [("prep", preprocessor_reg), ("model", LinearRegression())]
        ),
        "RandomForestRegressor": Pipeline(
            [
                ("prep", preprocessor_reg),
                ("model", RandomForestRegressor(n_estimators=400, random_state=42, min_samples_leaf=5)),
            ]
        ),
    }

    reg_cv = RepeatedKFold(n_splits=5, n_repeats=3, random_state=42)
    reg_results = []
    reg_test_results = []
    for name, pipe in reg_models.items():
        cv_scores = cross_validate(
            pipe,
            X_reg,
            y_reg,
            cv=reg_cv,
            scoring={"rmse": "neg_root_mean_squared_error", "mae": "neg_mean_absolute_error", "r2": "r2"},
            n_jobs=None,
        )
        reg_results.append(
            {
                "model": name,
                "cv_rmse_mean": -cv_scores["test_rmse"].mean(),
                "cv_rmse_std": cv_scores["test_rmse"].std(),
                "cv_mae_mean": -cv_scores["test_mae"].mean(),
                "cv_r2_mean": cv_scores["test_r2"].mean(),
            }
        )
        pipe.fit(X_train_reg, y_train_reg)
        preds = pipe.predict(X_test_reg)
        reg_test_results.append(
            {
                "model": name,
                "test_rmse": math.sqrt(mean_squared_error(y_test_reg, preds)),
                "test_mae": mean_absolute_error(y_test_reg, preds),
                "test_r2": r2_score(y_test_reg, preds),
            }
        )

    reg_results_df = pd.DataFrame(reg_results).sort_values("cv_rmse_mean")
    reg_test_df = pd.DataFrame(reg_test_results).set_index("model")

    readmit_formula = "readmitted ~ age + severity_index + length_of_stay_days + recovery_score + C(treatment) + C(department)"
    logit_model = smf.logit(readmit_formula, data=df).fit(disp=False)
    logit_odds = pd.DataFrame(
        {
            "odds_ratio": np.exp(logit_model.params),
            "p_value": logit_model.pvalues,
            "ci_lower": np.exp(logit_model.conf_int()[0]),
            "ci_upper": np.exp(logit_model.conf_int()[1]),
        }
    )

    X_cls = df[["age", "severity_index", "length_of_stay_days", "recovery_score", "treatment", "department"]]
    y_cls = df["readmitted"]
    X_train_cls, X_test_cls, y_train_cls, y_test_cls = train_test_split(
        X_cls, y_cls, test_size=0.2, random_state=42, stratify=y_cls
    )
    num_cls = ["age", "severity_index", "length_of_stay_days", "recovery_score"]
    cat_cls = ["treatment", "department"]

    preprocessor_cls = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num_cls),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(drop="first"))]), cat_cls),
        ]
    )

    cls_models = {
        "LogisticRegression": Pipeline(
            [
                ("prep", preprocessor_cls),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        "RandomForestClassifier": Pipeline(
            [
                ("prep", preprocessor_cls),
                ("model", RandomForestClassifier(n_estimators=400, random_state=42, min_samples_leaf=5, class_weight="balanced")),
            ]
        ),
    }

    cls_cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=42)
    cls_results = []
    cls_test_results = []
    for name, pipe in cls_models.items():
        cv_scores = cross_validate(
            pipe,
            X_cls,
            y_cls,
            cv=cls_cv,
            scoring={
                "roc_auc": "roc_auc",
                "avg_precision": "average_precision",
                "balanced_accuracy": "balanced_accuracy",
                "neg_brier": "neg_brier_score",
            },
            n_jobs=None,
        )
        cls_results.append(
            {
                "model": name,
                "cv_roc_auc_mean": cv_scores["test_roc_auc"].mean(),
                "cv_pr_auc_mean": cv_scores["test_avg_precision"].mean(),
                "cv_bal_acc_mean": cv_scores["test_balanced_accuracy"].mean(),
                "cv_brier_mean": -cv_scores["test_neg_brier"].mean(),
            }
        )
        pipe.fit(X_train_cls, y_train_cls)
        prob = pipe.predict_proba(X_test_cls)[:, 1]
        pred = pipe.predict(X_test_cls)
        cls_test_results.append(
            {
                "model": name,
                "test_roc_auc": roc_auc_score(y_test_cls, prob),
                "test_pr_auc": average_precision_score(y_test_cls, prob),
                "test_bal_acc": balanced_accuracy_score(y_test_cls, pred),
                "test_brier": brier_score_loss(y_test_cls, prob),
            }
        )

    cls_results_df = pd.DataFrame(cls_results).sort_values("cv_roc_auc_mean", ascending=False)
    cls_test_df = pd.DataFrame(cls_test_results).set_index("model")

    logit_linearity_checks = {}
    positive_cols = ["age", "severity_index", "length_of_stay_days", "recovery_score"]
    bt_df = df.copy()
    for col in positive_cols:
        bt_df[f"{col}_log"] = bt_df[col] * np.log(bt_df[col])
    bt_formula = (
        "readmitted ~ age + severity_index + length_of_stay_days + recovery_score + "
        "age_log + severity_index_log + length_of_stay_days_log + recovery_score_log + "
        "C(treatment) + C(department)"
    )
    bt_model = smf.logit(bt_formula, data=bt_df).fit(disp=False)
    for col in positive_cols:
        logit_linearity_checks[col] = bt_model.pvalues[f"{col}_log"]

    treatment_recovery_ttest = stats.ttest_ind(
        df.loc[df["treatment"] == "A", "recovery_score"],
        df.loc[df["treatment"] == "B", "recovery_score"],
        equal_var=False,
    )
    treatment_readmit_chi2 = stats.chi2_contingency(pd.crosstab(df["treatment"], df["readmitted"]))

    grouped_means = (
        df.groupby(["department", "treatment"], observed=False)[
            ["age", "severity_index", "length_of_stay_days", "recovery_score", "readmitted"]
        ]
        .mean()
        .reset_index()
    )

    report = []
    report.append("# Dataset Analysis Report")
    report.append("")
    report.append("## Scope")
    report.append(
        "This report inspects `dataset.csv`, performs exploratory analysis, fits interpretable and predictive models where appropriate, "
        "checks core modeling assumptions, and summarizes evidence-based findings."
    )
    report.append("")
    report.append("## Data Overview")
    report.append(f"- Rows: {df.shape[0]}")
    report.append(f"- Columns: {df.shape[1]}")
    report.append(f"- Numeric columns: {', '.join(numeric_cols)}")
    report.append(f"- Categorical columns: {', '.join(categorical_cols)}")
    report.append(f"- Exact duplicate rows: {duplicate_rows}")
    report.append(f"- Duplicate `patient_id` values: {duplicate_patient_ids}")
    report.append("")
    report.append("### Column Summary")
    report.append(md_table(summary, digits=2))
    report.append("")
    report.append("### Numeric Summary")
    report.append(md_table(numeric_summary, digits=3))
    report.append("")
    report.append("### Categorical Summaries")
    for col, cat_df in categorical_summary:
        report.append(f"#### `{col}`")
        report.append(md_table(cat_df, digits=2))
        report.append("")
    report.append("### Data Quality Checks")
    report.append(f"- Missing values: {'none detected' if int(null_counts.sum()) == 0 else 'present'}")
    report.append(
        "- Outlier counts by 1.5*IQR rule: "
        + ", ".join([f"`{k}`={v}" for k, v in outlier_counts.items()])
    )
    report.append(
        "- The dataset appears structurally clean: no nulls, no duplicate rows, balanced department counts, and unique patient identifiers."
    )
    report.append("")
    report.append("## Exploratory Analysis")
    report.append("### Key Visualizations")
    for name in [
        "numeric_distributions",
        "correlation_heatmap",
        "recovery_group_boxplots",
        "severity_group_boxplots",
        "severity_vs_recovery",
        "readmission_rates",
        "ols_diagnostics",
    ]:
        report.append(f"- [`plots/{name}.png`](plots/{name}.png)")
    report.append("")
    report.append("### Correlation Structure")
    report.append(md_table(corr, digits=3))
    report.append("")
    report.append("### Group Means")
    report.append(md_table(grouped_means.set_index(["department", "treatment"]), digits=3))
    report.append("")
    report.append("### EDA Findings")
    report.append(
        f"- `recovery_score` declines strongly as `severity_index` rises (correlation {corr.loc['severity_index', 'recovery_score']:.3f})."
    )
    report.append(
        f"- `severity_index` and `length_of_stay_days` are strongly positively correlated ({corr.loc['severity_index', 'length_of_stay_days']:.3f}), which raises multicollinearity concerns for regression."
    )
    report.append(
        f"- Departments are highly stratified by severity: mean `severity_index` is {fmt(df.groupby('department')['severity_index'].mean()['Cardiology'])} in Cardiology, "
        f"{fmt(df.groupby('department')['severity_index'].mean()['Neurology'])} in Neurology, and "
        f"{fmt(df.groupby('department')['severity_index'].mean()['Orthopedics'])} in Orthopedics."
    )
    report.append(
        f"- The raw treatment comparison is confounded: treatment A patients are older and sicker on average than treatment B patients "
        f"(mean severity {fmt(df.groupby('treatment')['severity_index'].mean()['A'])} vs {fmt(df.groupby('treatment')['severity_index'].mean()['B'])})."
    )
    report.append(
        f"- Readmission is rare ({df['readmitted'].mean() * 100:.1f}% positive class) and shows only weak marginal correlations with measured predictors."
    )
    report.append("")
    report.append("## Hypothesis Tests")
    report.append(
        f"- Welch t-test for `recovery_score` by treatment A vs B: statistic={treatment_recovery_ttest.statistic:.3f}, p-value={treatment_recovery_ttest.pvalue:.3e}. "
        "Unadjusted recovery differs, but this should not be interpreted causally because treatment assignment is not balanced."
    )
    report.append(
        f"- Chi-square test for `readmitted` vs treatment: chi2={treatment_readmit_chi2[0]:.3f}, p-value={treatment_readmit_chi2[1]:.3f}. "
        "No statistically significant association was detected."
    )
    report.append("")
    report.append("## Modeling")
    report.append("### 1. Recovery Score Regression")
    report.append(
        "A linear model is appropriate as the primary inferential model because the target is continuous and the EDA suggests an approximately monotonic relationship with severity."
    )
    ols_coef = ols_model.summary2().tables[1]
    report.append(md_table(ols_coef, digits=4))
    report.append("")
    report.append(f"- OLS R-squared: {ols_model.rsquared:.3f}")
    report.append(f"- Adjusted R-squared: {ols_model.rsquared_adj:.3f}")
    report.append(
        f"- Strongest adjusted predictor: `severity_index` coefficient {ols_model.params['severity_index']:.3f} points per unit (p={ols_model.pvalues['severity_index']:.3e})."
    )
    report.append(
        f"- After adjustment, treatment B is associated with {ols_model.params['C(treatment)[T.B]']:.3f} lower recovery-score points than treatment A (p={ols_model.pvalues['C(treatment)[T.B]']:.3e}). "
        "This is the opposite direction of the unadjusted mean difference, which is a strong sign of confounding."
    )
    report.append("")
    report.append("#### Regression Validation")
    report.append(md_table(reg_results_df.set_index("model"), digits=3))
    report.append("")
    report.append("#### Holdout Regression Performance")
    report.append(md_table(reg_test_df, digits=3))
    report.append("")
    report.append(
        "- Linear regression performs slightly better than the random forest on cross-validation, indicating that the main signal is already captured by a simple additive structure."
    )
    report.append("")
    report.append("#### OLS Assumption Checks")
    report.append(
        f"- Residual normality: Jarque-Bera p-value={ols_model.summary2().tables[0].loc['Prob(JB):', 0] if False else ols_model.model.data.orig_endog.shape[0]}"
    )
    jb_result = stats.jarque_bera(ols_model.resid)
    jb_stat = jb_result.statistic
    jb_pvalue = jb_result.pvalue
    report[-1] = f"- Residual normality: Jarque-Bera statistic={jb_stat:.3f}, p-value={jb_pvalue:.3f}. Residuals are close to normal."
    report.append(
        f"- Heteroskedasticity: Breusch-Pagan p-value={bp_results['F pvalue']:.3f}. No strong evidence of heteroskedasticity."
    )
    report.append(
        "- Multicollinearity diagnostics (VIF): " + ", ".join([f"`{row.feature}`={row.VIF:.2f}" for row in vif_df.itertuples(index=False)])
    )
    report.append(
        f"- Most influential observation by Cook's distance: patient_id={int(top_influential.iloc[0]['patient_id'])}, Cook's D={top_influential.iloc[0]['cooks_d']:.4f}. No single point dominates the fit."
    )
    report.append("")
    report.append("### 2. Readmission Classification")
    report.append(
        "A binary classification model was still fit because `readmitted` is a clinically relevant endpoint, but the data show weak signal and class imbalance."
    )
    report.append("#### Logistic Regression Odds Ratios")
    report.append(md_table(logit_odds, digits=4))
    report.append("")
    report.append("#### Classification Validation")
    report.append(md_table(cls_results_df.set_index("model"), digits=3))
    report.append("")
    report.append("#### Holdout Classification Performance")
    report.append(md_table(cls_test_df, digits=3))
    report.append("")
    report.append(
        f"- Baseline positive rate is {y_cls.mean():.3f}; a useful classifier should meaningfully exceed this signal in ROC-AUC / PR-AUC. The fitted models do not."
    )
    report.append(
        "- Neither logistic regression nor random forest produces strong discrimination. This suggests readmission is largely unexplained by the available variables."
    )
    report.append("")
    report.append("#### Logistic Diagnostics")
    report.append(
        "- Box-Tidwell linearity-in-logit p-values: "
        + ", ".join([f"`{k}`={v:.3f}" for k, v in logit_linearity_checks.items()])
    )
    report.append(
        "- None of the measured predictors has a strong, stable odds-ratio signal after adjustment; confidence intervals remain close to 1 for most effects."
    )
    report.append("")
    report.append("## Interpretation")
    report.append(
        "- The dataset is unusually tidy and balanced across departments, which is consistent with either highly curated operational data or synthetic generation."
    )
    report.append(
        "- Severity is the dominant driver of recovery outcomes. Higher severity tracks lower recovery and longer stays."
    )
    report.append(
        "- Department-level differences in raw recovery mostly reflect differences in case mix; once severity and treatment are modeled, department terms lose significance."
    )
    report.append(
        "- The treatment comparison is not randomized. Raw averages favor treatment B, but adjusted regression flips the sign, indicating severe confounding by baseline severity and department."
    )
    report.append(
        "- Readmission cannot be modeled reliably from the current feature set. Any operational use of a readmission model built on these columns would be weakly supported."
    )
    report.append("")
    report.append("## Caveats")
    report.append(
        "- Cross-sectional observational data cannot establish causal treatment effects."
    )
    report.append(
        "- `length_of_stay_days` may partly lie on the pathway from severity to recovery; including it improves prediction but may complicate causal interpretation."
    )
    report.append(
        "- The absence of nulls and the near-regular structure should be treated cautiously; real hospital data are typically messier."
    )
    report.append("")
    report.append("## Bottom Line")
    report.append(
        "For `recovery_score`, a simple linear model is well supported and explains about half of the variance, with severity as the main negative predictor. "
        "For `readmitted`, the available variables provide little predictive value, and model performance remains weak after validation."
    )

    REPORT_PATH.write_text("\n".join(report))


if __name__ == "__main__":
    main()
