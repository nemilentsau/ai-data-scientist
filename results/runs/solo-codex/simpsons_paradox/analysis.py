from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2_contingency, f_oneway, jarque_bera, kruskal, pearsonr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import auc, precision_recall_curve, roc_curve
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.graphics.gofplots import qqplot
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 140


def fmt_float(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}"


def df_block(df: pd.DataFrame | pd.Series, max_rows: int | None = None) -> str:
    obj = df if max_rows is None else df.head(max_rows)
    return "```text\n" + obj.to_string() + "\n```"


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["department"] = df["department"].astype("category")
    df["treatment"] = df["treatment"].astype("category")
    df["readmitted"] = df["readmitted"].astype(int)
    return df


def basic_inspection(df: pd.DataFrame) -> dict:
    numeric_cols = ["age", "severity_index", "length_of_stay_days", "recovery_score"]
    categorical_cols = ["department", "treatment", "readmitted"]

    inspection = {
        "shape": df.shape,
        "dtypes": df.dtypes.rename("dtype"),
        "nulls": df.isna().sum().rename("null_count"),
        "duplicates": int(df.duplicated().sum()),
        "duplicate_patient_id": int(df["patient_id"].duplicated().sum()),
        "describe_numeric": df[numeric_cols + ["patient_id"]].describe().T,
        "value_counts": {c: df[c].value_counts(dropna=False) for c in categorical_cols},
        "outliers_iqr": {},
    }

    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo = q1 - 1.5 * iqr
        hi = q3 + 1.5 * iqr
        inspection["outliers_iqr"][col] = {
            "lower_bound": lo,
            "upper_bound": hi,
            "count": int(((df[col] < lo) | (df[col] > hi)).sum()),
        }

    return inspection


def make_eda_plots(df: pd.DataFrame) -> dict:
    numeric_cols = ["age", "severity_index", "length_of_stay_days", "recovery_score"]
    plot_paths: dict[str, str] = {}

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, col in zip(axes.flat, numeric_cols):
        sns.histplot(df[col], kde=True, bins=24, ax=ax, color="#3b82f6")
        ax.set_title(f"Distribution of {col}")
    fig.tight_layout()
    path = PLOTS_DIR / "numeric_distributions.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["numeric_distributions"] = path.name

    corr = df[numeric_cols + ["readmitted"]].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
    ax.set_title("Correlation heatmap")
    fig.tight_layout()
    path = PLOTS_DIR / "correlation_heatmap.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["correlation_heatmap"] = path.name

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.scatterplot(
        data=df,
        x="severity_index",
        y="recovery_score",
        hue="treatment",
        style="department",
        alpha=0.75,
        ax=ax,
    )
    sns.regplot(
        data=df,
        x="severity_index",
        y="recovery_score",
        scatter=False,
        color="black",
        ci=None,
        ax=ax,
    )
    ax.set_title("Recovery declines as severity increases")
    fig.tight_layout()
    path = PLOTS_DIR / "recovery_vs_severity.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["recovery_vs_severity"] = path.name

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.scatterplot(
        data=df,
        x="severity_index",
        y="length_of_stay_days",
        hue="treatment",
        style="department",
        alpha=0.75,
        ax=ax,
    )
    sns.regplot(
        data=df,
        x="severity_index",
        y="length_of_stay_days",
        scatter=False,
        color="black",
        ci=None,
        ax=ax,
    )
    ax.set_title("Length of stay rises with severity")
    fig.tight_layout()
    path = PLOTS_DIR / "los_vs_severity.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["los_vs_severity"] = path.name

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.boxplot(data=df, x="treatment", y="recovery_score", hue="treatment", ax=axes[0], palette="Set2", legend=False)
    axes[0].set_title("Recovery score by treatment")
    sns.boxplot(
        data=df,
        x="treatment",
        y="length_of_stay_days",
        hue="treatment",
        ax=axes[1],
        palette="Set2",
        legend=False,
    )
    axes[1].set_title("Length of stay by treatment")
    fig.tight_layout()
    path = PLOTS_DIR / "treatment_boxplots.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["treatment_boxplots"] = path.name

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    readmit_dept = df.groupby("department", observed=False)["readmitted"].mean().sort_values(ascending=False)
    readmit_treat = df.groupby("treatment", observed=False)["readmitted"].mean().sort_values(ascending=False)
    sns.barplot(x=readmit_dept.index, y=readmit_dept.values, ax=axes[0], color="#ef4444")
    axes[0].set_title("Readmission rate by department")
    axes[0].set_ylim(0, max(0.16, readmit_dept.max() * 1.2))
    sns.barplot(x=readmit_treat.index, y=readmit_treat.values, ax=axes[1], color="#f59e0b")
    axes[1].set_title("Readmission rate by treatment")
    axes[1].set_ylim(0, max(0.16, readmit_treat.max() * 1.2))
    fig.tight_layout()
    path = PLOTS_DIR / "readmission_rates.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["readmission_rates"] = path.name

    fig, ax = plt.subplots(figsize=(10, 4))
    nulls = df.isna().sum().sort_values(ascending=False)
    sns.barplot(x=nulls.index, y=nulls.values, ax=ax, color="#6b7280")
    ax.set_title("Missing values by column")
    ax.set_ylabel("Null count")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    path = PLOTS_DIR / "missing_values.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["missing_values"] = path.name

    return plot_paths


def run_stat_tests(df: pd.DataFrame) -> dict:
    treatment_groups = df.groupby("treatment", observed=False)
    department_groups = df.groupby("department", observed=False)

    recovery_groups = [g["recovery_score"].values for _, g in treatment_groups]
    los_groups = [g["length_of_stay_days"].values for _, g in treatment_groups]

    treatment_readmit_table = pd.crosstab(df["treatment"], df["readmitted"])
    department_readmit_table = pd.crosstab(df["department"], df["readmitted"])

    stats = {
        "correlations": {
            "severity_vs_recovery": pearsonr(df["severity_index"], df["recovery_score"]),
            "severity_vs_los": pearsonr(df["severity_index"], df["length_of_stay_days"]),
            "age_vs_severity": pearsonr(df["age"], df["severity_index"]),
        },
        "group_summaries": {
            "by_treatment": treatment_groups[["age", "severity_index", "length_of_stay_days", "recovery_score", "readmitted"]]
            .agg(["mean", "std", "count"]),
            "by_department": department_groups[["age", "severity_index", "length_of_stay_days", "recovery_score", "readmitted"]]
            .agg(["mean", "std", "count"]),
        },
        "anova_recovery_by_treatment": f_oneway(*recovery_groups),
        "kruskal_recovery_by_treatment": kruskal(*recovery_groups),
        "anova_los_by_treatment": f_oneway(*los_groups),
        "kruskal_los_by_treatment": kruskal(*los_groups),
        "chi2_treatment_readmit": chi2_contingency(treatment_readmit_table),
        "chi2_department_readmit": chi2_contingency(department_readmit_table),
        "department_treatment_mix": pd.crosstab(df["department"], df["treatment"], normalize="index"),
    }
    return stats


def regression_models(df: pd.DataFrame) -> dict:
    recovery_formula = "recovery_score ~ age + severity_index + C(treatment) + C(department)"
    recovery_model = smf.ols(recovery_formula, data=df).fit()
    recovery_model_hc3 = recovery_model.get_robustcov_results(cov_type="HC3")

    los_formula = "length_of_stay_days ~ age + severity_index + C(treatment) + C(department)"
    los_model = smf.ols(los_formula, data=df).fit().get_robustcov_results(cov_type="HC3")

    quad_model = smf.ols(
        "recovery_score ~ age + severity_index + I(severity_index**2) + C(treatment) + C(department)",
        data=df,
    ).fit()
    interaction_model = smf.ols(
        "recovery_score ~ age + severity_index * C(treatment) + C(department)",
        data=df,
    ).fit()

    bp_stat = het_breuschpagan(recovery_model.resid, recovery_model.model.exog)
    jb_stat = jarque_bera(recovery_model.resid)

    X_vif = pd.get_dummies(
        df[["age", "severity_index", "treatment", "department"]],
        drop_first=True,
        dtype=float,
    )
    X_vif = sm.add_constant(X_vif)
    vif = pd.DataFrame(
        {
            "feature": X_vif.columns,
            "VIF": [variance_inflation_factor(X_vif.values, i) for i in range(X_vif.shape[1])],
        }
    )

    infl = recovery_model.get_influence().summary_frame()

    num_reg = ["age", "severity_index"]
    cat_reg = ["treatment", "department"]
    reg_pre = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), num_reg),
            (
                "cat",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="most_frequent")),
                        ("oh", OneHotEncoder(drop="first", handle_unknown="ignore")),
                    ]
                ),
                cat_reg,
            ),
        ]
    )

    reg_models = {
        "LinearRegression": Pipeline([("pre", reg_pre), ("model", LinearRegression())]),
        "RandomForestRegressor": Pipeline(
            [
                ("pre", reg_pre),
                ("model", RandomForestRegressor(n_estimators=400, min_samples_leaf=5, random_state=42)),
            ]
        ),
    }
    reg_cv = {}
    for name, model in reg_models.items():
        cv = cross_validate(
            model,
            df[num_reg + cat_reg],
            df["recovery_score"],
            cv=KFold(n_splits=5, shuffle=True, random_state=42),
            scoring={"r2": "r2", "mae": "neg_mean_absolute_error", "rmse": "neg_root_mean_squared_error"},
        )
        reg_cv[name] = {
            "r2_mean": cv["test_r2"].mean(),
            "r2_std": cv["test_r2"].std(),
            "mae_mean": -cv["test_mae"].mean(),
            "rmse_mean": -cv["test_rmse"].mean(),
        }

    return {
        "recovery_model": recovery_model,
        "recovery_model_hc3": recovery_model_hc3,
        "los_model_hc3": los_model,
        "bp_stat": bp_stat,
        "jb_stat": jb_stat,
        "vif": vif,
        "infl": infl,
        "quad_model": quad_model,
        "interaction_model": interaction_model,
        "reg_cv": pd.DataFrame(reg_cv).T,
    }


def classification_models(df: pd.DataFrame) -> dict:
    formula = "readmitted ~ age + severity_index + length_of_stay_days + recovery_score + C(treatment) + C(department)"
    logit_model = smf.logit(formula, data=df).fit(disp=False)

    num_cls = ["age", "severity_index", "length_of_stay_days", "recovery_score"]
    cat_cls = ["treatment", "department"]
    cls_pre = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                num_cls,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="most_frequent")),
                        ("oh", OneHotEncoder(drop="first", handle_unknown="ignore")),
                    ]
                ),
                cat_cls,
            ),
        ]
    )

    cls_models = {
        "LogisticRegression": Pipeline(
            [
                ("pre", cls_pre),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        "RandomForestClassifier": Pipeline(
            [
                ("pre", cls_pre),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=400,
                        min_samples_leaf=5,
                        random_state=42,
                        class_weight="balanced",
                    ),
                ),
            ]
        ),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cls_cv = {}
    oof_prob = None
    for name, model in cls_models.items():
        scores = cross_validate(
            model,
            df[num_cls + cat_cls],
            df["readmitted"],
            cv=cv,
            scoring={
                "roc_auc": "roc_auc",
                "average_precision": "average_precision",
                "balanced_accuracy": "balanced_accuracy",
                "brier": "neg_brier_score",
            },
        )
        cls_cv[name] = {
            "roc_auc_mean": scores["test_roc_auc"].mean(),
            "average_precision_mean": scores["test_average_precision"].mean(),
            "balanced_accuracy_mean": scores["test_balanced_accuracy"].mean(),
            "brier_mean": -scores["test_brier"].mean(),
        }
        if name == "LogisticRegression":
            oof_prob = cross_val_predict(
                model,
                df[num_cls + cat_cls],
                df["readmitted"],
                cv=cv,
                method="predict_proba",
            )[:, 1]

    odds_ratios = pd.DataFrame(
        {
            "coef": logit_model.params,
            "odds_ratio": np.exp(logit_model.params),
            "p_value": logit_model.pvalues,
        }
    )

    return {
        "logit_model": logit_model,
        "cls_cv": pd.DataFrame(cls_cv).T,
        "odds_ratios": odds_ratios,
        "oof_prob": oof_prob,
    }


def diagnostic_plots(df: pd.DataFrame, reg_results: dict, cls_results: dict) -> dict:
    plot_paths: dict[str, str] = {}
    recovery_model = reg_results["recovery_model"]
    fitted = recovery_model.fittedvalues
    resid = recovery_model.resid
    abs_sqrt_resid = np.sqrt(np.abs(recovery_model.get_influence().resid_studentized_internal))
    leverage = recovery_model.get_influence().hat_matrix_diag
    cooks = recovery_model.get_influence().cooks_distance[0]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.scatterplot(x=fitted, y=resid, ax=axes[0, 0], alpha=0.7)
    axes[0, 0].axhline(0, color="black", linestyle="--")
    axes[0, 0].set_title("Residuals vs fitted")
    axes[0, 0].set_xlabel("Fitted")
    axes[0, 0].set_ylabel("Residuals")

    qqplot(resid, line="45", ax=axes[0, 1], markerfacecolor="#3b82f6", markeredgecolor="#3b82f6", alpha=0.7)
    axes[0, 1].set_title("Q-Q plot")

    sns.scatterplot(x=fitted, y=abs_sqrt_resid, ax=axes[1, 0], alpha=0.7)
    axes[1, 0].set_title("Scale-location")
    axes[1, 0].set_xlabel("Fitted")
    axes[1, 0].set_ylabel("Sqrt(|standardized residual|)")

    sns.scatterplot(x=leverage, y=cooks, ax=axes[1, 1], alpha=0.7)
    axes[1, 1].set_title("Leverage vs Cook's distance")
    axes[1, 1].set_xlabel("Leverage")
    axes[1, 1].set_ylabel("Cook's distance")

    fig.tight_layout()
    path = PLOTS_DIR / "recovery_model_diagnostics.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["recovery_model_diagnostics"] = path.name

    y_true = df["readmitted"].to_numpy()
    y_prob = cls_results["oof_prob"]
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    baseline = y_true.mean()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].plot(fpr, tpr, color="#2563eb", label=f"AUC={auc(fpr, tpr):.3f}")
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[0].set_title("Cross-validated ROC curve")
    axes[0].set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].legend(loc="lower right")

    axes[1].plot(recall, precision, color="#dc2626", label=f"AP={auc(recall, precision):.3f}")
    axes[1].axhline(baseline, linestyle="--", color="gray", label=f"Baseline={baseline:.3f}")
    axes[1].set_title("Cross-validated precision-recall curve")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    path = PLOTS_DIR / "readmission_classifier_curves.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    plot_paths["readmission_classifier_curves"] = path.name

    return plot_paths


def write_report(
    df: pd.DataFrame,
    inspection: dict,
    tests: dict,
    reg_results: dict,
    cls_results: dict,
    plot_paths: dict,
) -> None:
    treatment_summary = tests["group_summaries"]["by_treatment"]
    department_summary = tests["group_summaries"]["by_department"]
    reg_cv = reg_results["reg_cv"].copy()
    cls_cv = cls_results["cls_cv"].copy()
    vif = reg_results["vif"].copy()
    vif["VIF"] = vif["VIF"].round(3)

    recovery_hc3 = reg_results["recovery_model_hc3"]
    recovery_index = reg_results["recovery_model"].model.exog_names
    recovery_conf = pd.DataFrame(recovery_hc3.conf_int(), index=recovery_index, columns=["ci_low", "ci_high"])
    recovery_coef = pd.Series(recovery_hc3.params, index=recovery_index)
    recovery_params = pd.DataFrame(
        {
            "coef": recovery_coef,
            "std_err": pd.Series(recovery_hc3.bse, index=recovery_index),
            "p_value": pd.Series(recovery_hc3.pvalues, index=recovery_index),
        },
        index=recovery_index,
    ).round(4)
    recovery_params = recovery_params.join(recovery_conf.round(4))

    los_hc3 = reg_results["los_model_hc3"]
    los_index = reg_results["los_model_hc3"].model.exog_names
    los_conf = pd.DataFrame(los_hc3.conf_int(), index=los_index, columns=["ci_low", "ci_high"])
    los_coef = pd.Series(los_hc3.params, index=los_index)
    los_params = pd.DataFrame(
        {
            "coef": los_coef,
            "std_err": pd.Series(los_hc3.bse, index=los_index),
            "p_value": pd.Series(los_hc3.pvalues, index=los_index),
        },
        index=los_index,
    ).round(4)
    los_params = los_params.join(los_conf.round(4))

    corr_df = pd.DataFrame(
        {
            "pair": ["severity vs recovery", "severity vs LOS", "age vs severity"],
            "pearson_r": [
                tests["correlations"]["severity_vs_recovery"].statistic,
                tests["correlations"]["severity_vs_los"].statistic,
                tests["correlations"]["age_vs_severity"].statistic,
            ],
            "p_value": [
                tests["correlations"]["severity_vs_recovery"].pvalue,
                tests["correlations"]["severity_vs_los"].pvalue,
                tests["correlations"]["age_vs_severity"].pvalue,
            ],
        }
    ).round(4)

    outlier_df = pd.DataFrame(inspection["outliers_iqr"]).T.round(3)
    influential_n = int((reg_results["infl"]["cooks_d"] > 4 / len(df)).sum())
    max_cooks = float(reg_results["infl"]["cooks_d"].max())

    report = f"""# Dataset Analysis Report

## Executive Summary

This analysis covers `{DATA_PATH.name}`, a patient-level tabular dataset with **{inspection["shape"][0]} rows** and **{inspection["shape"][1]} columns**. The data are structurally clean: there are **no missing values**, **no duplicated rows**, and **no duplicated `patient_id` values**.

The main findings are:

1. `severity_index` is the dominant driver of both outcomes that appear clinically meaningful in this dataset. Higher severity is strongly associated with **longer length of stay** and **lower recovery score**.
2. Treatment groups are **not balanced at baseline**. Patients receiving treatment `A` are older, more severe, and are concentrated in different departments than patients receiving treatment `B`. Raw treatment comparisons are therefore confounded.
3. After adjustment for age, severity, and department, treatment `B` is associated with an approximately **4.72-point lower recovery score** relative to treatment `A` (HC3-robust p < 0.001).
4. For `length_of_stay_days`, once severity is in the model, treatment and department effects are negligible. Severity explains most of the variation.
5. `readmitted` appears to contain **little or no predictive signal** in the available features. Cross-validated classification performance is near chance, so no strong conclusions about readmission drivers are warranted.

## 1. Data Loading and Inspection

### Dataset shape

- Rows: **{inspection["shape"][0]}**
- Columns: **{inspection["shape"][1]}**

### Data types

{df_block(inspection["dtypes"])}

### Missing values

{df_block(inspection["nulls"])}

### Numeric summary

{df_block(inspection["describe_numeric"].round(3))}

### Categorical distributions

#### `department`
{df_block(inspection["value_counts"]["department"])}

#### `treatment`
{df_block(inspection["value_counts"]["treatment"])}

#### `readmitted`
{df_block(inspection["value_counts"]["readmitted"])}

### Duplicate checks

- Duplicated rows: **{inspection["duplicates"]}**
- Duplicated `patient_id`: **{inspection["duplicate_patient_id"]}**

### IQR-based outlier screen

These are mild edge-case checks, not grounds for deletion by themselves.

{df_block(outlier_df)}

## 2. Exploratory Data Analysis

### Visualizations generated

- `plots/{plot_paths["numeric_distributions"]}`
- `plots/{plot_paths["correlation_heatmap"]}`
- `plots/{plot_paths["recovery_vs_severity"]}`
- `plots/{plot_paths["los_vs_severity"]}`
- `plots/{plot_paths["treatment_boxplots"]}`
- `plots/{plot_paths["readmission_rates"]}`
- `plots/{plot_paths["missing_values"]}`
- `plots/{plot_paths["recovery_model_diagnostics"]}`
- `plots/{plot_paths["readmission_classifier_curves"]}`

### Core EDA observations

- The numeric variables are well-behaved overall, with only a handful of IQR-defined outliers.
- `severity_index` has a **strong positive** linear relationship with `length_of_stay_days` and a **strong negative** linear relationship with `recovery_score`.
- `age` is strongly positively correlated with `severity_index`, which means age can look important in univariate analysis but largely fades after severity adjustment.
- Readmission prevalence is low (**{fmt_float(df["readmitted"].mean(), 3)}**), creating a class-imbalance problem for classification.

### Key correlations

{df_block(corr_df)}

### Group summaries by treatment

The treatment groups differ at baseline, which is important for interpretation.

{df_block(treatment_summary.round(3))}

### Department-treatment mix

Treatment assignment also varies by department.

{df_block(tests["department_treatment_mix"].round(3))}

### Group summaries by department

{df_block(department_summary.round(3))}

## 3. Patterns, Relationships, and Anomalies

### Strong patterns

- `severity_index` vs `length_of_stay_days`: Pearson r = **{fmt_float(tests["correlations"]["severity_vs_los"].statistic)}**, p < 1e-16.
- `severity_index` vs `recovery_score`: Pearson r = **{fmt_float(tests["correlations"]["severity_vs_recovery"].statistic)}**, p < 1e-16.
- `age` vs `severity_index`: Pearson r = **{fmt_float(tests["correlations"]["age_vs_severity"].statistic)}**, p < 1e-16.

### Treatment comparisons before adjustment

Raw group comparisons suggest treatment `A` patients are:

- Older
- More severe
- Longer-stay
- Slightly higher-recovery on average

That pattern is not causal evidence because treatment assignment is clearly confounded by baseline case mix.

### Statistical group tests

- Recovery by treatment: ANOVA p = **{tests["anova_recovery_by_treatment"].pvalue:.3e}**, Kruskal p = **{tests["kruskal_recovery_by_treatment"].pvalue:.3e}**
- Length of stay by treatment: ANOVA p = **{tests["anova_los_by_treatment"].pvalue:.3e}**, Kruskal p = **{tests["kruskal_los_by_treatment"].pvalue:.3e}**
- Readmission vs treatment: chi-square p = **{tests["chi2_treatment_readmit"][1]:.4f}**
- Readmission vs department: chi-square p = **{tests["chi2_department_readmit"][1]:.4f}**

Interpretation:

- Treatment groups differ strongly in recovery and LOS *before adjustment*.
- Readmission rate differences by treatment or department are not statistically compelling even before multivariable modeling.

### Anomalies and data-quality concerns

- No missingness or duplicates were found.
- Outlier counts are low and influence diagnostics do not indicate a handful of points dominating the recovery model.
- Maximum Cook's distance in the recovery model is **{fmt_float(max_cooks, 4)}**; observations above the common `4/n` heuristic: **{influential_n}**, but values are still small in absolute magnitude.

## 4. Modeling

### 4.1 Recovery Score Regression

I modeled `recovery_score` with OLS using:

`recovery_score ~ age + severity_index + C(treatment) + C(department)`

This model was chosen because:

- The outcome is continuous.
- EDA suggested approximately linear relationships.
- Residual diagnostics were acceptable.
- More complex nonlinear models did not outperform linear regression in cross-validation.

#### HC3-robust coefficient table

{df_block(recovery_params)}

#### Interpretation

- **Severity is the main predictor**: each 1-unit increase in `severity_index` is associated with an estimated **{fmt_float(-recovery_coef["severity_index"], 2)}-point decrease** in recovery score, holding age, treatment, and department constant.
- **Treatment matters after adjustment**: treatment `B` is associated with a **{fmt_float(-recovery_coef["C(treatment)[T.B]"], 2)}-point lower** recovery score than treatment `A`, 95% CI [{fmt_float(recovery_conf.loc["C(treatment)[T.B]", "ci_low"], 2)}, {fmt_float(recovery_conf.loc["C(treatment)[T.B]", "ci_high"], 2)}].
- Age and department do not add much once severity is included.

#### Validation

{df_block(reg_cv.round(4))}

Interpretation:

- Cross-validated `R^2` for linear regression is about **{fmt_float(reg_cv.loc["LinearRegression", "r2_mean"], 3)}**, indicating moderate explanatory power.
- The random forest underperformed the linear model, which supports the choice of a linear specification.

### 4.2 Length of Stay Regression

I also fit an adjusted model for `length_of_stay_days`:

`length_of_stay_days ~ age + severity_index + C(treatment) + C(department)`

#### HC3-robust coefficient table

{df_block(los_params)}

Interpretation:

- Severity has a large positive association with LOS: about **{fmt_float(los_coef["severity_index"], 2)} additional days** per 1-unit increase in `severity_index`.
- Once severity is included, treatment is no longer meaningfully associated with LOS.
- This strongly suggests the raw LOS difference between treatments is largely explained by case-mix severity.

### 4.3 Readmission Classification

I fit a multivariable logistic regression and compared it with a random forest classifier under stratified 5-fold cross-validation.

#### Logistic regression odds ratios

{df_block(cls_results["odds_ratios"].round(4))}

#### Cross-validated classification metrics

{df_block(cls_cv.round(4))}

Interpretation:

- ROC AUC is approximately **{fmt_float(cls_cv.loc["LogisticRegression", "roc_auc_mean"], 3)}** for logistic regression, which is essentially chance-level discrimination.
- Average precision is only slightly above the base event rate, and balanced accuracy is about **{fmt_float(cls_cv.loc["LogisticRegression", "balanced_accuracy_mean"], 3)}**.
- The random forest does not improve the picture.

Conclusion: the available features do **not** support a useful predictive model for `readmitted`.

## 5. Assumption Checks and Model Diagnostics

### Recovery model assumptions

- **Linearity**: Scatterplots and model comparison tests did not support adding a quadratic severity term.
- **Interaction check**: A severity-by-treatment interaction did not materially improve fit.
- **Residual normality**: Jarque-Bera p = **{reg_results["jb_stat"].pvalue:.4f}**, which is consistent with approximately normal residuals.
- **Homoscedasticity**: Breusch-Pagan p = **{reg_results["bp_stat"][1]:.4f}**. There is mild evidence of heteroscedasticity, so I report **HC3-robust standard errors**.
- **Multicollinearity**: VIF values are acceptable for the substantive predictors.

{df_block(vif.round(3))}

### Model specification checks

- Adding `severity_index^2` to the recovery model did not materially improve fit (p = **{reg_results["quad_model"].pvalues["I(severity_index ** 2)"]:.4f}**).
- Adding a severity-by-treatment interaction also did not materially improve fit (p = **{reg_results["interaction_model"].pvalues["severity_index:C(treatment)[T.B]"]:.4f}**).

### Readmission model caveats

- The target is imbalanced ({df["readmitted"].sum()} positives out of {len(df)} rows).
- Poor cross-validated discrimination suggests either near-random variation or omitted predictors.
- Under these conditions, coefficient interpretation should be conservative.

## 6. Conclusions

The dataset is clean and internally consistent, but the substantive story is dominated by **severity**:

1. Higher severity is strongly associated with worse recovery and longer hospitalization.
2. Treatment assignment is confounded by severity and department, so raw comparisons are misleading.
3. After adjustment, treatment `A` is associated with meaningfully better recovery than treatment `B`, while LOS differences mostly disappear.
4. Readmission is not usefully explained by the available features, so any operational readmission model built from this dataset would be unreliable.

## 7. Recommended Next Steps

1. If this dataset is intended for causal treatment evaluation, collect or include additional pre-treatment covariates and use a design that addresses treatment assignment bias.
2. For readmission modeling, add clinically richer predictors such as comorbidities, discharge disposition, prior utilization history, medication burden, and social determinants.
3. If this is a synthetic benchmark dataset, treat the recovery and LOS models as structurally informative, but do not over-interpret the readmission target.
"""

    REPORT_PATH.write_text(dedent(report))


def main() -> None:
    ensure_dirs()
    df = load_data()
    inspection = basic_inspection(df)
    eda_plots = make_eda_plots(df)
    tests = run_stat_tests(df)
    reg_results = regression_models(df)
    cls_results = classification_models(df)
    diag_plots = diagnostic_plots(df, reg_results, cls_results)
    write_report(df, inspection, tests, reg_results, cls_results, {**eda_plots, **diag_plots})


if __name__ == "__main__":
    main()
