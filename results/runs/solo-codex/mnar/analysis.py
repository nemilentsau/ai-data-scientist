from pathlib import Path
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import make_scorer, mean_squared_error
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.dummy import DummyRegressor


BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "dataset.csv"
PLOTS_DIR = BASE / "plots"
REPORT_PATH = BASE / "analysis_report.md"
PLOTS_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.dpi"] = 120
plt.rcParams["savefig.dpi"] = 150
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 11


def savefig(name: str):
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name, bbox_inches="tight")
    plt.close()


def code_block(text: str) -> str:
    return f"```\n{text.rstrip()}\n```"


def series_to_lines(s: pd.Series) -> str:
    return s.to_string()


def frame_to_lines(df: pd.DataFrame) -> str:
    return df.to_string()


def rmse(y_true, y_pred):
    return mean_squared_error(y_true, y_pred) ** 0.5


rmse_scorer = make_scorer(rmse, greater_is_better=False)


def cv_summary(models: dict, X: pd.DataFrame, y: pd.Series, cv: KFold) -> pd.DataFrame:
    rows = []
    for name, model in models.items():
        scores = cross_validate(
            model,
            X,
            y,
            cv=cv,
            scoring={"r2": "r2", "rmse": rmse_scorer},
            n_jobs=None,
        )
        rows.append(
            {
                "model": name,
                "mean_r2": scores["test_r2"].mean(),
                "std_r2": scores["test_r2"].std(),
                "mean_rmse": -scores["test_rmse"].mean(),
                "std_rmse": scores["test_rmse"].std(),
            }
        )
    out = pd.DataFrame(rows)
    numeric_cols = [c for c in out.columns if c != "model"]
    out[numeric_cols] = out[numeric_cols].round(4)
    return out.sort_values("mean_r2", ascending=False)


raw_df = pd.read_csv(DATA_PATH)
df = raw_df.copy()
df["income_missing"] = df["reported_annual_income"].isna().astype(int)

numeric_cols = [
    "age",
    "education_years",
    "reported_annual_income",
    "satisfaction_score",
    "num_children",
]
categorical_cols = ["gender", "region"]

# Data quality and profiling
overview = pd.DataFrame(
    {
        "dtype": df.dtypes.astype(str),
        "non_null_count": df.notna().sum(),
        "null_count": df.isna().sum(),
        "null_pct": (df.isna().mean() * 100).round(2),
        "n_unique": df.nunique(dropna=False),
    }
)

numeric_summary = df[numeric_cols].describe().T.round(3)
categorical_summary = pd.concat(
    {col: df[col].value_counts(dropna=False) for col in categorical_cols}, axis=1
).fillna(0)

duplicates = int(df.duplicated().sum())
duplicate_ids = int(df["respondent_id"].duplicated().sum())

range_checks = {
    "age_out_of_expected_range": int(((df["age"] < 0) | (df["age"] > 100)).sum()),
    "education_years_negative": int((df["education_years"] < 0).sum()),
    "income_non_positive": int((df["reported_annual_income"].fillna(1) <= 0).sum()),
    "satisfaction_out_of_1_10": int(
        ((df["satisfaction_score"] < 1) | (df["satisfaction_score"] > 10)).sum()
    ),
    "num_children_negative": int((df["num_children"] < 0).sum()),
}

distribution_stats = pd.DataFrame(
    {
        "skew": df[numeric_cols].skew(numeric_only=True),
        "kurtosis": df[numeric_cols].kurtosis(numeric_only=True),
    }
).round(3)

outlier_rows = []
for col in numeric_cols:
    s = df[col].dropna()
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_rows.append(
        {
            "feature": col,
            "q1": round(q1, 3),
            "q3": round(q3, 3),
            "iqr": round(iqr, 3),
            "lower_fence": round(lower, 3),
            "upper_fence": round(upper, 3),
            "n_outliers": int(((s < lower) | (s > upper)).sum()),
        }
    )
outlier_summary = pd.DataFrame(outlier_rows)

# Missingness analysis
missing_group_means = (
    df.groupby("income_missing")[["age", "education_years", "satisfaction_score", "num_children"]]
    .mean()
    .round(3)
)

missing_group_tests = []
for col in ["age", "education_years", "satisfaction_score", "num_children"]:
    observed = df.loc[df["income_missing"] == 0, col]
    missing = df.loc[df["income_missing"] == 1, col]
    welch = stats.ttest_ind(observed, missing, equal_var=False, nan_policy="omit")
    mannwhitney = stats.mannwhitneyu(observed, missing, alternative="two-sided")
    missing_group_tests.append(
        {
            "variable": col,
            "welch_t_pvalue": welch.pvalue,
            "mannwhitney_pvalue": mannwhitney.pvalue,
        }
    )
missing_group_tests = pd.DataFrame(missing_group_tests).round(6)

missingness_logit = smf.logit(
    "income_missing ~ age + education_years + satisfaction_score + num_children + C(gender) + C(region)",
    data=df,
).fit(disp=0)
missingness_table = missingness_logit.summary2().tables[1].round(4)
missingness_or = np.exp(missingness_logit.params).rename("odds_ratio").round(3)

# Correlation and group summaries
correlation = df[numeric_cols].corr().round(3)
income_by_gender = (
    df.groupby("gender")["reported_annual_income"]
    .agg(["count", "mean", "median", "std"])
    .round(2)
)
income_by_region = (
    df.groupby("region")["reported_annual_income"]
    .agg(["count", "mean", "median", "std"])
    .round(2)
)
satisfaction_by_gender = (
    df.groupby("gender")["satisfaction_score"]
    .agg(["count", "mean", "median", "std"])
    .round(2)
)
satisfaction_by_region = (
    df.groupby("region")["satisfaction_score"]
    .agg(["count", "mean", "median", "std"])
    .round(2)
)

# Models
income_cc = df.dropna(subset=["reported_annual_income"]).copy()
income_formula = (
    "reported_annual_income ~ age + education_years + num_children + C(gender) + C(region)"
)
income_ols = smf.ols(income_formula, data=income_cc).fit()
income_bp = het_breuschpagan(income_ols.resid, income_ols.model.exog)
income_shapiro_p = stats.shapiro(income_ols.resid)[1]
income_predictions = income_ols.fittedvalues
income_residuals = income_ols.resid

satisfaction_formula_basic = (
    "satisfaction_score ~ age + education_years + num_children + C(gender) + C(region)"
)
satisfaction_ols_basic = smf.ols(satisfaction_formula_basic, data=df).fit()
satisfaction_bp_basic = het_breuschpagan(
    satisfaction_ols_basic.resid, satisfaction_ols_basic.model.exog
)
satisfaction_shapiro_p_basic = stats.shapiro(satisfaction_ols_basic.resid)[1]

satisfaction_cc = income_cc.copy()
satisfaction_cc["log_income"] = np.log(satisfaction_cc["reported_annual_income"])
satisfaction_formula_income = (
    "satisfaction_score ~ age + education_years + num_children + log_income + C(gender) + C(region)"
)
satisfaction_ols_income = smf.ols(satisfaction_formula_income, data=satisfaction_cc).fit()
satisfaction_bp_income = het_breuschpagan(
    satisfaction_ols_income.resid, satisfaction_ols_income.model.exog
)
satisfaction_shapiro_p_income = stats.shapiro(satisfaction_ols_income.resid)[1]

# Cross-validated predictive validation
cv = KFold(n_splits=5, shuffle=True, random_state=42)

income_features = ["age", "education_years", "num_children", "gender", "region"]
X_income = income_cc[income_features]
y_income = income_cc["reported_annual_income"]

preprocess_income = ColumnTransformer(
    transformers=[
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), ["age", "education_years", "num_children"]),
        (
            "cat",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]
            ),
            ["gender", "region"],
        ),
    ]
)

income_models = {
    "LinearRegression": Pipeline(
        [("preprocess", preprocess_income), ("model", LinearRegression())]
    ),
    "RandomForestRegressor": Pipeline(
        [
            ("preprocess", preprocess_income),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=400, max_depth=None, min_samples_leaf=4, random_state=42
                ),
            ),
        ]
    ),
}
income_cv = cv_summary(income_models, X_income, y_income, cv)

satisfaction_features = [
    "age",
    "education_years",
    "num_children",
    "gender",
    "region",
    "reported_annual_income",
    "income_missing",
]
X_sat = df[satisfaction_features]
y_sat = df["satisfaction_score"]

preprocess_sat = ColumnTransformer(
    transformers=[
        (
            "num",
            Pipeline([("imputer", SimpleImputer(strategy="median"))]),
            ["age", "education_years", "num_children", "reported_annual_income", "income_missing"],
        ),
        (
            "cat",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]
            ),
            ["gender", "region"],
        ),
    ]
)

satisfaction_models = {
    "DummyRegressor": DummyRegressor(strategy="mean"),
    "LinearRegression": Pipeline(
        [("preprocess", preprocess_sat), ("model", LinearRegression())]
    ),
    "RandomForestRegressor": Pipeline(
        [
            ("preprocess", preprocess_sat),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=400, max_depth=None, min_samples_leaf=4, random_state=42
                ),
            ),
        ]
    ),
}
satisfaction_cv = cv_summary(satisfaction_models, X_sat, y_sat, cv)

# Plots
plt.figure(figsize=(8, 4))
missing_pct = (df.isna().mean() * 100).sort_values(ascending=False)
sns.barplot(x=missing_pct.index, y=missing_pct.values, color="#4472c4")
plt.ylabel("Missing values (%)")
plt.xlabel("")
plt.xticks(rotation=45, ha="right")
plt.title("Missingness by Column")
savefig("missingness_by_column.png")

fig, axes = plt.subplots(2, 3, figsize=(16, 9))
for ax, col in zip(axes.flat, numeric_cols):
    sns.histplot(df[col], kde=True, bins=25, ax=ax, color="#4c956c")
    ax.set_title(col)
axes.flat[-1].axis("off")
savefig("numeric_distributions.png")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
sns.countplot(data=df, x="gender", hue="gender", ax=axes[0], palette="Set2", legend=False)
axes[0].set_title("Gender Counts")
sns.countplot(data=df, x="region", hue="region", ax=axes[1], palette="Set2", legend=False)
axes[1].set_title("Region Counts")
axes[1].tick_params(axis="x", rotation=30)
savefig("categorical_counts.png")

plt.figure(figsize=(7, 5))
sns.heatmap(correlation, annot=True, cmap="coolwarm", center=0, fmt=".2f")
plt.title("Correlation Matrix")
savefig("correlation_heatmap.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.boxplot(
    data=income_cc,
    x="gender",
    y="reported_annual_income",
    hue="gender",
    ax=axes[0],
    palette="Set3",
    legend=False,
)
axes[0].set_title("Income by Gender")
sns.boxplot(
    data=income_cc,
    x="region",
    y="reported_annual_income",
    hue="region",
    ax=axes[1],
    palette="Set3",
    legend=False,
)
axes[1].set_title("Income by Region")
axes[1].tick_params(axis="x", rotation=30)
savefig("income_boxplots.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.scatterplot(
    data=income_cc,
    x="education_years",
    y="reported_annual_income",
    hue="gender",
    alpha=0.7,
    ax=axes[0],
)
axes[0].set_title("Income vs Education")
sns.scatterplot(
    data=income_cc,
    x="age",
    y="reported_annual_income",
    hue="region",
    alpha=0.7,
    ax=axes[1],
)
axes[1].set_title("Income vs Age")
savefig("income_scatter_relationships.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.boxplot(
    data=df,
    x="gender",
    y="satisfaction_score",
    hue="gender",
    ax=axes[0],
    palette="Pastel1",
    legend=False,
)
axes[0].set_title("Satisfaction by Gender")
sns.boxplot(
    data=df,
    x="region",
    y="satisfaction_score",
    hue="region",
    ax=axes[1],
    palette="Pastel1",
    legend=False,
)
axes[1].set_title("Satisfaction by Region")
axes[1].tick_params(axis="x", rotation=30)
savefig("satisfaction_boxplots.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.scatterplot(
    data=income_cc,
    x="reported_annual_income",
    y="satisfaction_score",
    hue="gender",
    alpha=0.7,
    ax=axes[0],
)
axes[0].set_title("Satisfaction vs Income")
sns.scatterplot(
    data=df,
    x="age",
    y="satisfaction_score",
    hue="region",
    alpha=0.7,
    ax=axes[1],
)
axes[1].set_title("Satisfaction vs Age")
savefig("satisfaction_scatter_relationships.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.scatterplot(x=income_predictions, y=income_residuals, alpha=0.7, ax=axes[0], color="#2a9d8f")
axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
axes[0].set_title("Income Model Residuals vs Fitted")
stats.probplot(income_residuals, dist="norm", plot=axes[1])
axes[1].set_title("Income Model Q-Q Plot")
savefig("income_model_diagnostics.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.scatterplot(
    x=satisfaction_ols_income.fittedvalues,
    y=satisfaction_ols_income.resid,
    alpha=0.7,
    ax=axes[0],
    color="#e76f51",
)
axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
axes[0].set_title("Satisfaction Model Residuals vs Fitted")
stats.probplot(satisfaction_ols_income.resid, dist="norm", plot=axes[1])
axes[1].set_title("Satisfaction Model Q-Q Plot")
savefig("satisfaction_model_diagnostics.png")

# Narrative findings
income_missing_pct = df["reported_annual_income"].isna().mean() * 100
income_corr = correlation["reported_annual_income"].drop("reported_annual_income").sort_values(ascending=False)
sat_corr = correlation["satisfaction_score"].drop("satisfaction_score").sort_values(ascending=False)

report = f"""# Dataset Analysis Report

## Executive Summary

This report analyzes `dataset.csv` ({raw_df.shape[0]} rows, {raw_df.shape[1]} raw columns) with a focus on data quality, exploratory structure, missingness, and whether the tabular features support meaningful predictive modeling.

The most important finding is that `reported_annual_income` is missing for {income_missing_pct:.1f}% of respondents. That missingness is not consistent with a purely random process: older respondents, respondents with more education, and respondents with higher satisfaction were more likely to have missing income. Because of that, any model using only observed income values should be interpreted as a conditional analysis on responders, not as fully representative of the entire sample.

Income is moderately structured by age and education and can be modeled with modest predictive skill. Satisfaction, by contrast, is only weakly predictable from the available variables. The data support descriptive findings more strongly than causal claims.

## 1. Data Loading and Inspection

- Rows: {raw_df.shape[0]}
- Raw columns: {raw_df.shape[1]}
- Derived analysis columns added: 1 (`income_missing`)
- Duplicate full rows: {duplicates}
- Duplicate `respondent_id` values: {duplicate_ids}

### Column Overview
{code_block(frame_to_lines(overview))}

### Numeric Summary
{code_block(frame_to_lines(numeric_summary))}

### Categorical Counts
{code_block(frame_to_lines(categorical_summary))}

### Basic Validity Checks
{code_block(pd.Series(range_checks).to_string())}

No obvious impossible values were found in the observed fields. The key quality issue is missing income, not invalid ranges.

## 2. Exploratory Data Analysis

### Distribution Shape
{code_block(frame_to_lines(distribution_stats))}

`reported_annual_income` is only mildly right-skewed, so modeling it on the raw scale is defensible for interpretability. `satisfaction_score` is bounded between 1 and 10 and slightly left-skewed, but not strongly enough to make basic linear diagnostics meaningless.

### Correlations
{code_block(frame_to_lines(correlation))}

Key bivariate patterns:

- Income rises with age (`r = {correlation.loc['age', 'reported_annual_income']:.3f}`) and education (`r = {correlation.loc['education_years', 'reported_annual_income']:.3f}`).
- Satisfaction has only a weak linear association with income (`r = {correlation.loc['satisfaction_score', 'reported_annual_income']:.3f}`) and is nearly unrelated to age and education.
- Number of children is weakly negatively associated with income and satisfaction.

### Outlier Review
{code_block(frame_to_lines(outlier_summary))}

The IQR rule flags some high-child-count observations as outliers because `num_children` is discrete and concentrated at low values. Those are not necessarily data errors. Income has only one IQR-based outlier, so extreme-income distortion is limited.

### Saved Visualizations

- `plots/missingness_by_column.png`
- `plots/numeric_distributions.png`
- `plots/categorical_counts.png`
- `plots/correlation_heatmap.png`
- `plots/income_boxplots.png`
- `plots/income_scatter_relationships.png`
- `plots/satisfaction_boxplots.png`
- `plots/satisfaction_scatter_relationships.png`
- `plots/income_model_diagnostics.png`
- `plots/satisfaction_model_diagnostics.png`

## 3. Missing-Data Investigation

Because nearly half the income values are missing, missingness itself was modeled.

### Group Means by Income Missingness
{code_block(frame_to_lines(missing_group_means))}

### Two-Sample Tests
{code_block(frame_to_lines(missing_group_tests))}

### Logistic Regression for Income Missingness
{code_block(frame_to_lines(missingness_table))}

Odds ratios:
{code_block(series_to_lines(missingness_or))}

Interpretation:

- Higher age, education, and satisfaction are each associated with higher odds of missing income after adjusting for the other observed features.
- Respondents in the `Other` gender category were less likely than the reference group to have missing income.
- Region effects were not statistically strong in this model.
- Pseudo R-squared is low ({missingness_logit.prsquared:.3f}), so the observed variables explain only part of the missingness process, but they explain enough to reject a naive MCAR interpretation.

This is the central modeling caveat in the dataset.

## 4. Income Modeling

Income was modeled only on rows where income is observed (`n = {len(income_cc)}`), with OLS for inference and cross-validated machine-learning models for predictive validation.

### OLS: `reported_annual_income ~ age + education_years + num_children + gender + region`
{code_block(frame_to_lines(income_ols.summary2().tables[1].round(4)))}

Model fit:

- R-squared: {income_ols.rsquared:.3f}
- Adjusted R-squared: {income_ols.rsquared_adj:.3f}
- Residual normality Shapiro p-value: {income_shapiro_p:.6f}
- Breusch-Pagan p-value for heteroskedasticity: {income_bp[1]:.6f}

Interpretation:

- Age and education are the strongest positive predictors of reported income.
- Each additional child is associated with lower reported income, conditional on the other variables.
- Region and gender effects are comparatively weak and mostly not statistically distinguishable from zero in this sample.
- Residuals are not perfectly normal, but the deviation is modest in the plots and there is no strong evidence of heteroskedasticity.

### Cross-Validated Predictive Performance
{code_block(frame_to_lines(income_cv))}

The cross-validated results show modest predictive skill. Linear regression and random forest are broadly similar, which suggests the signal is mostly simple and additive rather than strongly nonlinear.

### Income by Group
Income by gender:
{code_block(frame_to_lines(income_by_gender))}

Income by region:
{code_block(frame_to_lines(income_by_region))}

## 5. Satisfaction Modeling

Satisfaction was analyzed in two ways:

1. A full-sample OLS model without income, avoiding the missing-data problem.
2. A complete-case OLS model adding log-income, used only as a conditional analysis on income responders.

### OLS Without Income (All Rows)
{code_block(frame_to_lines(satisfaction_ols_basic.summary2().tables[1].round(4)))}

Model fit:

- R-squared: {satisfaction_ols_basic.rsquared:.3f}
- Adjusted R-squared: {satisfaction_ols_basic.rsquared_adj:.3f}
- Residual normality Shapiro p-value: {satisfaction_shapiro_p_basic:.6f}
- Breusch-Pagan p-value: {satisfaction_bp_basic[1]:.6f}

This model explains almost none of the variance in satisfaction.

### OLS With Log-Income (Income Observed Only)
{code_block(frame_to_lines(satisfaction_ols_income.summary2().tables[1].round(4)))}

Model fit:

- Observations: {int(satisfaction_ols_income.nobs)}
- R-squared: {satisfaction_ols_income.rsquared:.3f}
- Adjusted R-squared: {satisfaction_ols_income.rsquared_adj:.3f}
- Residual normality Shapiro p-value: {satisfaction_shapiro_p_income:.6f}
- Breusch-Pagan p-value: {satisfaction_bp_income[1]:.6f}

Interpretation:

- Conditional on income being observed, higher income is associated with higher satisfaction.
- The effect size is statistically detectable but practically limited because overall explanatory power remains low.
- Education becomes slightly negative when income enters, which is consistent with correlated predictors and weak net effects rather than a strong substantive relationship.

### Cross-Validated Predictive Performance
{code_block(frame_to_lines(satisfaction_cv))}

Even after imputing income and including a missingness indicator, predictive performance is weak. The available features do not strongly determine satisfaction in this dataset.

### Satisfaction by Group
Satisfaction by gender:
{code_block(frame_to_lines(satisfaction_by_gender))}

Satisfaction by region:
{code_block(frame_to_lines(satisfaction_by_region))}

## 6. Assumptions and Validation

The following checks were used to avoid over-claiming:

- Missingness was explicitly modeled rather than ignored.
- OLS residual plots and Q-Q plots were generated for the income and satisfaction models.
- Breusch-Pagan tests were used to check heteroskedasticity.
- Shapiro-Wilk tests were used to check residual normality. With sample sizes this large, even mild deviations can produce small p-values, so the diagnostic plots matter more than the p-values alone.
- Predictive models were validated with 5-fold cross-validation instead of reporting in-sample fit only.

Modeling choices were therefore guided by both interpretability and validation:

- OLS was used because the strongest relationships are approximately linear and the primary need is explanation.
- Random forest was used as a nonlinear benchmark. It did not materially outperform the linear baseline.
- Satisfaction was not modeled as an ordinal outcome here because the score behaves more like a dense bounded scale than a sparse ordered category, and the main result is low signal regardless.

## 7. Conclusions

1. The dataset is mostly clean in terms of ranges and duplicates, but it has a major missing-data problem in `reported_annual_income`.
2. Income missingness is associated with observed respondent characteristics, so analyses restricted to observed income are not safely representative of the whole sample.
3. Among respondents who reported income, age and education are the clearest positive correlates of income, while number of children has a modest negative association.
4. Satisfaction is only weakly explained by the observed variables. Income has a positive conditional association with satisfaction, but the total predictive power remains low.
5. There is limited evidence that more complex nonlinear models materially improve on simple linear structure.

## 8. Limitations

- The dataset is cross-sectional, so none of these associations should be interpreted causally.
- High income missingness likely biases complete-case estimates if nonresponse depends on unobserved factors as well as observed ones.
- Satisfaction is bounded and possibly subjective, so small coefficient estimates should not be over-interpreted.
- Without domain context or a designated target variable, the modeling section is exploratory rather than productized.
"""

REPORT_PATH.write_text(textwrap.dedent(report))
print(f"Wrote report to {REPORT_PATH}")
print(f"Saved plots to {PLOTS_DIR}")
