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
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.graphics.gofplots import qqplot
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "dataset.csv"
PLOTS_DIR = BASE_DIR / "plots"
REPORT_PATH = BASE_DIR / "analysis_report.md"

sns.set_theme(style="whitegrid", context="talk")
PLOTS_DIR.mkdir(exist_ok=True)


def savefig(name: str) -> str:
    path = PLOTS_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    return f"./plots/{name}"


def format_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def markdown_table_from_df(df_: pd.DataFrame, index: bool = True) -> str:
    df_fmt = df_.copy()
    if index:
        df_fmt = df_fmt.reset_index()
    headers = [str(col) for col in df_fmt.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in df_fmt.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


df = pd.read_csv(DATA_PATH)

numeric_cols = [
    "years_experience",
    "training_hours",
    "team_size",
    "projects_completed",
    "satisfaction_score",
    "commute_minutes",
    "performance_rating",
    "remote_pct",
]
categorical_cols = ["salary_band"]
feature_cols = [
    "years_experience",
    "training_hours",
    "team_size",
    "projects_completed",
    "satisfaction_score",
    "commute_minutes",
    "remote_pct",
    "salary_band",
]

# Data quality and descriptive summaries
shape = df.shape
dtypes = df.dtypes.astype(str)
nulls = df.isna().sum()
duplicate_rows = int(df.duplicated().sum())
duplicate_ids = int(df["employee_id"].duplicated().sum())
numeric_summary = df[numeric_cols + ["employee_id"]].describe().T
cat_summary = df[categorical_cols].describe().T
salary_counts = df["salary_band"].value_counts().sort_index()
remote_counts = df["remote_pct"].value_counts().sort_index()
corr = df[numeric_cols].corr()

# Outlier screening via IQR
outlier_rows = {}
for col in numeric_cols:
    q1, q3 = df[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_rows[col] = int(((df[col] < lower) | (df[col] > upper)).sum())

# Formal association tests
anova_results = []
for col in numeric_cols:
    groups = [g[col].values for _, g in df.groupby("salary_band")]
    f_stat, p_val = stats.f_oneway(*groups)
    eta_sq = (f_stat * (len(groups) - 1)) / (f_stat * (len(groups) - 1) + (len(df) - len(groups)))
    anova_results.append(
        {"variable": col, "F": f_stat, "p_value": p_val, "eta_sq": eta_sq}
    )
anova_df = pd.DataFrame(anova_results).sort_values("p_value")

chi2_table = pd.crosstab(df["salary_band"], df["remote_pct"])
chi2_stat, chi2_p, chi2_dof, _ = stats.chi2_contingency(chi2_table)
cramers_v = np.sqrt(chi2_stat / (len(df) * (min(chi2_table.shape) - 1)))

# Visualizations
plt.figure(figsize=(8, 4))
nulls.sort_values(ascending=False).plot(kind="bar", color="#4C78A8")
plt.title("Missing Values by Column")
plt.ylabel("Count")
nulls_plot = savefig("missing_values.png")

fig, axes = plt.subplots(4, 2, figsize=(14, 18))
for ax, col in zip(axes.flatten(), numeric_cols):
    sns.histplot(df[col], kde=True, bins=25, ax=ax, color="#2A9D8F")
    ax.set_title(f"Distribution of {col}")
dist_plot = savefig("numeric_distributions.png")

plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f")
plt.title("Correlation Heatmap")
corr_plot = savefig("correlation_heatmap.png")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
sns.boxplot(data=df, x="salary_band", y="years_experience", ax=axes[0, 0], palette="Set2")
axes[0, 0].set_title("Experience by Salary Band")
sns.boxplot(data=df, x="salary_band", y="performance_rating", ax=axes[0, 1], palette="Set2")
axes[0, 1].set_title("Performance by Salary Band")
sns.boxplot(data=df, x="salary_band", y="commute_minutes", ax=axes[1, 0], palette="Set2")
axes[1, 0].set_title("Commute by Salary Band")
sns.boxplot(data=df, x="salary_band", y="training_hours", ax=axes[1, 1], palette="Set2")
axes[1, 1].set_title("Training by Salary Band")
salary_box_plot = savefig("salary_band_boxplots.png")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
sns.countplot(data=df, x="salary_band", ax=axes[0], palette="Set3")
axes[0].set_title("Salary Band Counts")
sns.countplot(data=df, x="remote_pct", ax=axes[1], palette="Set3")
axes[1].set_title("Remote Percentage Counts")
counts_plot = savefig("category_counts.png")

selected_pairplot_df = df[
    ["years_experience", "training_hours", "commute_minutes", "performance_rating", "salary_band"]
]
pairgrid = sns.pairplot(
    selected_pairplot_df,
    hue="salary_band",
    corner=True,
    diag_kind="hist",
    plot_kws={"alpha": 0.6, "s": 28},
)
pairgrid.fig.suptitle("Pairwise Relationships for Selected Variables", y=1.02)
pairplot_path = PLOTS_DIR / "pairplot_selected.png"
pairgrid.savefig(pairplot_path, dpi=160, bbox_inches="tight")
plt.close("all")
pairplot_plot = "./plots/pairplot_selected.png"

# Regression modeling target: performance_rating
X_reg = df[feature_cols].copy()
y_reg = df["performance_rating"].copy()
X_reg_train, X_reg_test, y_reg_train, y_reg_test = train_test_split(
    X_reg, y_reg, test_size=0.2, random_state=42
)

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), [c for c in feature_cols if c != "salary_band"]),
        ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), ["salary_band"]),
    ]
)

sk_regression_models = {
    "dummy_mean": DummyRegressor(strategy="mean"),
    "linear_regression": __import__("sklearn.linear_model").linear_model.LinearRegression(),
    "random_forest": RandomForestRegressor(
        n_estimators=500,
        min_samples_leaf=5,
        random_state=42,
    ),
}

cv_reg = KFold(n_splits=5, shuffle=True, random_state=42)
regression_cv_rows = []
for name, model in sk_regression_models.items():
    pipe = Pipeline([("prep", preprocessor), ("model", model)])
    cv_result = cross_validate(
        pipe,
        X_reg,
        y_reg,
        cv=cv_reg,
        scoring={"rmse": "neg_root_mean_squared_error", "r2": "r2"},
        n_jobs=1,
    )
    regression_cv_rows.append(
        {
            "model": name,
            "rmse_mean": -cv_result["test_rmse"].mean(),
            "rmse_std": cv_result["test_rmse"].std(),
            "r2_mean": cv_result["test_r2"].mean(),
            "r2_std": cv_result["test_r2"].std(),
        }
    )
regression_cv = pd.DataFrame(regression_cv_rows).sort_values("rmse_mean")

best_reg_pipe = Pipeline(
    [("prep", preprocessor), ("model", sk_regression_models["linear_regression"])]
)
best_reg_pipe.fit(X_reg_train, y_reg_train)
y_reg_pred = best_reg_pipe.predict(X_reg_test)
reg_test_rmse = np.sqrt(mean_squared_error(y_reg_test, y_reg_pred))
reg_test_r2 = r2_score(y_reg_test, y_reg_pred)

# OLS diagnostics on full sample for assumptions and effect size review
ols_df = pd.get_dummies(df[feature_cols], columns=["salary_band"], drop_first=True)
X_ols = sm.add_constant(ols_df.astype(float))
ols_model = sm.OLS(y_reg, X_ols).fit()
ols_resid = ols_model.resid
ols_fitted = ols_model.fittedvalues
bp_lm, bp_lm_p, bp_f, bp_f_p = het_breuschpagan(ols_resid, X_ols)
jb_res = stats.jarque_bera(ols_resid)
jb_stat = float(jb_res.statistic)
jb_p = float(jb_res.pvalue)
reset_res = linear_reset(ols_model, power=2, use_f=True)
vif_df = pd.DataFrame(
    {
        "feature": X_ols.columns,
        "VIF": [variance_inflation_factor(X_ols.values, i) for i in range(X_ols.shape[1])],
    }
)

plt.figure(figsize=(8, 5))
sns.scatterplot(x=ols_fitted, y=ols_resid, alpha=0.7, color="#E76F51")
plt.axhline(0, color="black", linestyle="--", linewidth=1)
plt.xlabel("Fitted values")
plt.ylabel("Residuals")
plt.title("OLS Residuals vs Fitted")
resid_plot = savefig("ols_residuals_vs_fitted.png")

fig = qqplot(ols_resid, line="45", fit=True)
fig.suptitle("OLS Residual Q-Q Plot")
qq_plot = savefig("ols_qq_plot.png")

rf_reg = Pipeline(
    [("prep", preprocessor), ("model", sk_regression_models["random_forest"])]
)
rf_reg.fit(X_reg_train, y_reg_train)
perm_reg = permutation_importance(
    rf_reg, X_reg_test, y_reg_test, n_repeats=20, random_state=42, n_jobs=1
)
reg_importance = pd.DataFrame(
    {
        "feature": X_reg_test.columns,
        "importance_mean": perm_reg.importances_mean,
    }
).sort_values("importance_mean", ascending=False)
plt.figure(figsize=(9, 5))
sns.barplot(data=reg_importance, x="importance_mean", y="feature", color="#264653")
plt.title("Random Forest Permutation Importance for Performance Rating")
plt.xlabel("Mean importance decrease")
rf_reg_imp_plot = savefig("rf_regression_importance.png")

# Classification modeling target: salary_band
X_clf = df[[c for c in feature_cols if c != "salary_band"]].copy()
y_clf = df["salary_band"].copy()
X_clf_train, X_clf_test, y_clf_train, y_clf_test = train_test_split(
    X_clf, y_clf, test_size=0.2, random_state=42, stratify=y_clf
)

clf_preprocessor = ColumnTransformer(
    transformers=[("num", StandardScaler(), X_clf.columns.tolist())]
)

clf_models = {
    "dummy_most_frequent": DummyClassifier(strategy="most_frequent"),
    "multinomial_logistic": LogisticRegression(
        max_iter=2000,
        random_state=42,
    ),
    "random_forest": RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=5,
        random_state=42,
    ),
}

cv_clf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
classification_cv_rows = []
for name, model in clf_models.items():
    pipe = Pipeline([("prep", clf_preprocessor), ("model", model)])
    cv_result = cross_validate(
        pipe,
        X_clf,
        y_clf,
        cv=cv_clf,
        scoring={"accuracy": "accuracy", "balanced_accuracy": "balanced_accuracy"},
        n_jobs=1,
    )
    classification_cv_rows.append(
        {
            "model": name,
            "accuracy_mean": cv_result["test_accuracy"].mean(),
            "accuracy_std": cv_result["test_accuracy"].std(),
            "balanced_accuracy_mean": cv_result["test_balanced_accuracy"].mean(),
            "balanced_accuracy_std": cv_result["test_balanced_accuracy"].std(),
        }
    )
classification_cv = pd.DataFrame(classification_cv_rows).sort_values(
    "balanced_accuracy_mean", ascending=False
)

best_clf_pipe = Pipeline(
    [("prep", clf_preprocessor), ("model", clf_models["multinomial_logistic"])]
)
best_clf_pipe.fit(X_clf_train, y_clf_train)
y_clf_pred = best_clf_pipe.predict(X_clf_test)
clf_accuracy = accuracy_score(y_clf_test, y_clf_pred)
clf_bal_accuracy = balanced_accuracy_score(y_clf_test, y_clf_pred)
clf_report = classification_report(y_clf_test, y_clf_pred, output_dict=True)
clf_report_df = pd.DataFrame(clf_report).T.round(3)
cm = confusion_matrix(y_clf_test, y_clf_pred, labels=sorted(y_clf.unique()))

plt.figure(figsize=(7, 6))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=sorted(y_clf.unique()),
    yticklabels=sorted(y_clf.unique()),
)
plt.title("Confusion Matrix: Multinomial Logistic Salary Band Model")
plt.xlabel("Predicted")
plt.ylabel("Actual")
cm_plot = savefig("salary_band_confusion_matrix.png")

rf_clf = Pipeline([("prep", clf_preprocessor), ("model", clf_models["random_forest"])])
rf_clf.fit(X_clf_train, y_clf_train)
perm_clf = permutation_importance(
    rf_clf, X_clf_test, y_clf_test, n_repeats=20, random_state=42, n_jobs=1
)
clf_importance = pd.DataFrame(
    {
        "feature": X_clf_test.columns,
        "importance_mean": perm_clf.importances_mean,
    }
).sort_values("importance_mean", ascending=False)
plt.figure(figsize=(9, 5))
sns.barplot(data=clf_importance, x="importance_mean", y="feature", color="#1D3557")
plt.title("Random Forest Permutation Importance for Salary Band")
plt.xlabel("Mean importance decrease")
rf_clf_imp_plot = savefig("rf_classification_importance.png")

# Normality screening for key variables
dist_checks = []
for col in ["years_experience", "training_hours", "commute_minutes", "performance_rating", "satisfaction_score"]:
    stat, p_val = stats.normaltest(df[col])
    dist_checks.append({"variable": col, "statistic": stat, "p_value": p_val})
dist_checks_df = pd.DataFrame(dist_checks)

report = f"""# Dataset Analysis Report

## 1. Scope and approach

This report analyzes `dataset.csv` as an observational employee-style tabular dataset. The workflow covered:

1. structural inspection and data-quality checks,
2. exploratory data analysis with plots,
3. formal association testing,
4. supervised modeling where the data plausibly supports it,
5. assumption checks and validation.

The analysis treats `employee_id` as an identifier, not a predictive feature.

## 2. Data loading and inspection

- Shape: **{shape[0]} rows x {shape[1]} columns**
- Missing values: **{int(nulls.sum())} total**
- Duplicate rows: **{duplicate_rows}**
- Duplicate `employee_id` values: **{duplicate_ids}**

### Data types

| column | dtype |
|---|---|
""" + "\n".join([f"| {idx} | {dtype} |" for idx, dtype in dtypes.items()]) + f"""

### Numeric summary

{markdown_table_from_df(numeric_summary.round(3))}

### Categorical summary

{markdown_table_from_df(cat_summary)}

### Category balance

`salary_band` counts:

{markdown_table_from_df(salary_counts.to_frame('count'))}

`remote_pct` counts:

{markdown_table_from_df(remote_counts.to_frame('count'))}

## 3. Data quality findings

- The dataset is structurally clean: no nulls, duplicate rows, or duplicate IDs were found.
- `employee_id` behaves like a pure surrogate key and should be excluded from inference and predictive modeling.
- Several variables are discrete or semi-discrete despite numeric storage (`team_size`, `projects_completed`, `remote_pct`, `commute_minutes`).
- `remote_pct` takes only five values: 0, 25, 50, 75, 100.
- Outlier screening via the IQR rule found the following counts of potentially unusual observations:

{markdown_table_from_df(pd.Series(outlier_rows, name='iqr_outlier_count').to_frame())}

The largest outlier concentration is in `commute_minutes`, which is right-skewed with a long upper tail.

## 4. Exploratory data analysis

### Visualizations

- Missingness: ![]({nulls_plot})
- Numeric distributions: ![]({dist_plot})
- Correlations: ![]({corr_plot})
- Salary-band boxplots: ![]({salary_box_plot})
- Category counts: ![]({counts_plot})
- Selected pairwise relationships: ![]({pairplot_plot})

### Distribution checks

Normality tests for selected continuous variables:

{markdown_table_from_df(dist_checks_df.round(4), index=False)}

Interpretation:

- Formal normality is rejected for at least some variables because the sample is moderately large and several distributions are bounded or discrete.
- `commute_minutes` is visibly skewed.
- `performance_rating` is closer to bell-shaped than most other columns, but still should not be assumed perfectly normal without checking residuals after modeling.

### Correlation structure

The Pearson correlation matrix shows no strong pairwise linear relationships. The largest absolute correlations are still small, indicating weak linear dependence overall.

{markdown_table_from_df(corr.round(3))}

## 5. Group comparisons and relationship testing

To test whether salary bands separate the numeric variables meaningfully, one-way ANOVA was run for each numeric field.

{markdown_table_from_df(anova_df.round(4), index=False)}

Key interpretation:

- No ANOVA p-value is below 0.05.
- Effect sizes are negligible (`eta_sq` values near zero).
- `salary_band` does not appear to correspond to systematically different experience, training, commute, satisfaction, performance, or remote-work patterns in this dataset.

For `salary_band` versus `remote_pct`, a chi-square test was also run:

- Chi-square statistic: **{chi2_stat:.3f}**
- Degrees of freedom: **{chi2_dof}**
- p-value: **{format_p(chi2_p)}**
- Cramer's V: **{cramers_v:.3f}**

This indicates no evidence of categorical association and a negligible effect size.

## 6. Predictive modeling

Because there is no explicit target column defined by the problem statement, two reasonable supervised tasks were evaluated:

1. predicting `performance_rating` from workplace attributes,
2. predicting `salary_band` from the other measured variables.

These tasks answer whether the dataset contains usable predictive signal, not whether any relationship is causal.

### 6.1 Regression task: predict `performance_rating`

Features used: `years_experience`, `training_hours`, `team_size`, `projects_completed`, `satisfaction_score`, `commute_minutes`, `remote_pct`, and one-hot encoded `salary_band`.

Five-fold cross-validation results:

{markdown_table_from_df(regression_cv.round(4), index=False)}

Held-out test performance for linear regression:

- RMSE: **{reg_test_rmse:.3f}**
- R-squared: **{reg_test_r2:.3f}**

Interpretation:

- Linear regression does not outperform the mean-baseline by a useful margin.
- Random forest also fails to produce meaningful lift, suggesting the issue is not simply unmodeled nonlinearity.
- The dataset contains little to no predictive signal for `performance_rating`.

Permutation importance from the random forest confirms that no feature contributes strongly:

{markdown_table_from_df(reg_importance.round(4), index=False)}

![]({rf_reg_imp_plot})

### 6.2 Classification task: predict `salary_band`

Features used: `years_experience`, `training_hours`, `team_size`, `projects_completed`, `satisfaction_score`, `commute_minutes`, `remote_pct`.

Five-fold cross-validation results:

{markdown_table_from_df(classification_cv.round(4), index=False)}

Held-out test performance for multinomial logistic regression:

- Accuracy: **{clf_accuracy:.3f}**
- Balanced accuracy: **{clf_bal_accuracy:.3f}**

Class-level test metrics:

{markdown_table_from_df(clf_report_df)}

Confusion matrix:

![]({cm_plot})

Permutation importance from random forest classification:

{markdown_table_from_df(clf_importance.round(4), index=False)}

![]({rf_clf_imp_plot})

Interpretation:

- Accuracy is close to chance for a 5-class problem.
- Balanced accuracy remains low, so the result is not being masked by class imbalance.
- Feature importance is weak and diffuse, consistent with an essentially uninformative feature set for `salary_band`.

## 7. Regression assumption checks

An OLS model for `performance_rating` was fit on the full sample to inspect assumptions and coefficient stability.

### Diagnostics

- R-squared: **{ols_model.rsquared:.4f}**
- Adjusted R-squared: **{ols_model.rsquared_adj:.4f}**
- Overall F-test p-value: **{format_p(ols_model.f_pvalue)}**
- Breusch-Pagan p-value for heteroskedasticity: **{format_p(bp_lm_p)}**
- Jarque-Bera p-value for residual normality: **{format_p(jb_p)}**
- Ramsey RESET p-value for functional form: **{format_p(reset_res.pvalue)}**

Residual diagnostics:

- Residuals vs fitted: ![]({resid_plot})
- Q-Q plot: ![]({qq_plot})

Variance inflation factors:

{markdown_table_from_df(vif_df.round(3), index=False)}

Interpretation:

- The very low R-squared confirms the model explains almost none of the variance.
- Multicollinearity is not a concern; VIF values are low aside from the intercept, which is not substantively important.
- Residual plots do not reveal a strong recoverable structure.
- Even if linear-model assumptions are not severely violated, the model remains practically uninformative because signal is absent.

## 8. Main findings

1. The dataset is mechanically clean but statistically weak.
2. There are no strong pairwise correlations, no meaningful ANOVA group differences by `salary_band`, and no categorical association between `salary_band` and `remote_pct`.
3. `commute_minutes` shows the clearest distributional anomaly through right-skew and outliers, but it still does not relate strongly to the other fields.
4. Predictive models for both `performance_rating` and `salary_band` perform at or near baseline, including nonlinear tree-based models.
5. The most defensible conclusion is that this dataset contains little actionable structure for inference or prediction.

## 9. Limitations and recommended next steps

- The analysis is rigorous for the observed columns, but no model can recover relationships that are not present in the data.
- If this dataset is synthetic, it appears to have been generated with weak or no dependency structure.
- If a meaningful business question is intended, additional variables are likely required. For example:
  - role or job family,
  - manager/team identifiers,
  - tenure at company distinct from total experience,
  - compensation amount instead of only `salary_band`,
  - performance history over time,
  - location and commute modality.
- Before operational use, clarify the true analytical objective and whether these variables are expected to be causally or predictively related at all.
"""

REPORT_PATH.write_text(report)
print(f"Wrote report to {REPORT_PATH}")
print(f"Saved plots to {PLOTS_DIR}")
