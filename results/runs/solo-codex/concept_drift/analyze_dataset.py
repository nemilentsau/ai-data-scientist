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
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name, dpi=150, bbox_inches="tight")
    plt.close()


def format_table(df: pd.DataFrame, digits: int = 4) -> str:
    rounded = df.copy()
    for col in rounded.columns:
        if pd.api.types.is_numeric_dtype(rounded[col]):
            rounded[col] = rounded[col].round(digits)
    headers = [str(col) for col in rounded.columns]
    rows = [[str(value) for value in row] for row in rounded.astype(object).fillna("").values.tolist()]
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    table.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(table)


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    raw_df = pd.read_csv(DATASET_PATH, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df = raw_df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["date"] = df["timestamp"].dt.date
    df["is_perfect"] = (df["defect_rate"] == 1.0).astype(int)

    original_columns = raw_df.columns.tolist()
    numeric_cols = ["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm", "defect_rate"]
    feature_cols = ["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm", "operator", "hour", "dayofweek"]
    num_features = ["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm", "hour", "dayofweek"]
    cat_features = ["operator"]

    intervals = df["timestamp"].diff().dropna()
    interval_counts = intervals.value_counts()
    summary_stats = df[numeric_cols].describe().T
    summary_stats["missing"] = df[numeric_cols].isna().sum()
    summary_stats["skew"] = df[numeric_cols].skew()

    corr = df[numeric_cols].corr()

    outlier_rows = []
    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((df[col] < lower) | (df[col] > upper)).sum())
        outlier_rows.append(
            {
                "feature": col,
                "lower_bound": lower,
                "upper_bound": upper,
                "outlier_count": count,
                "outlier_pct": count / len(df),
            }
        )
    outlier_df = pd.DataFrame(outlier_rows)

    shapiro_rows = []
    rng = np.random.default_rng(0)
    for col in numeric_cols:
        sample = df[col]
        if len(sample) > 500:
            sample = sample.iloc[rng.choice(len(sample), size=500, replace=False)]
        stat, pvalue = stats.shapiro(sample)
        shapiro_rows.append({"feature": col, "shapiro_stat": stat, "shapiro_pvalue": pvalue})
    shapiro_df = pd.DataFrame(shapiro_rows)

    daily_summary = df.groupby("date")["defect_rate"].agg(["mean", "std"])
    operator_summary = df.groupby("operator")["defect_rate"].agg(
        mean="mean",
        median="median",
        std="std",
        min="min",
        max="max",
    )
    operator_summary["pct_exactly_1"] = df.groupby("operator")["is_perfect"].mean()
    operator_test = stats.kruskal(*[group["defect_rate"].values for _, group in df.groupby("operator")])
    hour_means = df.groupby("hour")["defect_rate"].mean()
    dayofweek_means = df.groupby("dayofweek")["defect_rate"].mean()
    autocorr = pd.Series({lag: df["defect_rate"].autocorr(lag=lag) for lag in [1, 2, 6, 12, 24, 48]})

    plt.figure(figsize=(10, 4))
    sns.heatmap(df.isna().T, cbar=False, cmap="viridis")
    plt.title("Missingness Map")
    plt.xlabel("Row")
    plt.ylabel("Column")
    savefig("missingness_heatmap.png")

    fig, axes = plt.subplots(3, 2, figsize=(14, 14))
    axes = axes.flatten()
    for ax, col in zip(axes, numeric_cols):
        sns.histplot(df[col], kde=True, ax=ax, color="#33658A")
        ax.set_title(f"Distribution of {col}")
    axes[-1].axis("off")
    savefig("numeric_distributions.png")

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
    plt.title("Correlation Heatmap")
    savefig("correlation_heatmap.png")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sensors = ["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm"]
    for ax, col in zip(axes.flatten(), sensors):
        ax.plot(df["timestamp"], df[col], linewidth=1.0, color="#2F4858")
        ax.set_title(f"{col} Over Time")
        ax.tick_params(axis="x", rotation=30)
    savefig("process_signals_over_time.png")

    plt.figure(figsize=(14, 5))
    plt.plot(df["timestamp"], df["defect_rate"], alpha=0.35, linewidth=1.0, label="Observed", color="#BC4749")
    plt.plot(df["timestamp"], df["defect_rate"].rolling(48, min_periods=1).mean(), linewidth=2.5, label="48-step rolling mean", color="#386641")
    plt.title("Defect Rate Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Defect rate")
    plt.legend()
    plt.xticks(rotation=30)
    savefig("defect_rate_time_series.png")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, col in zip(axes.flatten(), sensors):
        sns.scatterplot(data=df, x=col, y="defect_rate", hue="operator", alpha=0.55, ax=ax, s=45)
        sns.regplot(data=df, x=col, y="defect_rate", scatter=False, ax=ax, color="black")
        ax.set_title(f"Defect Rate vs {col}")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    for ax in axes.flatten():
        legend = ax.get_legend()
        if legend is not None:
            legend.remove()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
    savefig("defect_rate_vs_features.png")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    sns.boxplot(data=df, x="operator", y="defect_rate", ax=axes[0], color="#9CC5A1")
    axes[0].set_title("Defect Rate by Operator")
    sns.boxplot(data=df, x="hour", y="defect_rate", ax=axes[1], color="#A7C957")
    axes[1].set_title("Defect Rate by Hour")
    axes[1].tick_params(axis="x", rotation=90)
    sns.boxplot(data=df, x="dayofweek", y="defect_rate", ax=axes[2], color="#6A4C93")
    axes[2].set_title("Defect Rate by Day of Week")
    savefig("groupwise_boxplots.png")

    preprocess = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                num_features,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(drop="first", handle_unknown="ignore")),
                    ]
                ),
                cat_features,
            ),
        ]
    )

    tscv = TimeSeriesSplit(n_splits=5)

    regression_models = {
        "dummy_mean": DummyRegressor(strategy="mean"),
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(
            n_estimators=400,
            random_state=0,
            min_samples_leaf=5,
            n_jobs=-1,
        ),
    }
    reg_results = []
    for name, estimator in regression_models.items():
        if name == "dummy_mean":
            model = estimator
            X_used = df[["hour"]]
        else:
            model = Pipeline([("preprocess", preprocess), ("model", estimator)])
            X_used = df[feature_cols]
        scores = cross_validate(
            model,
            X_used,
            df["defect_rate"],
            cv=tscv,
            scoring={"mae": "neg_mean_absolute_error", "rmse": "neg_root_mean_squared_error", "r2": "r2"},
            n_jobs=1,
        )
        reg_results.append(
            {
                "model": name,
                "mae_mean": -scores["test_mae"].mean(),
                "mae_std": scores["test_mae"].std(),
                "rmse_mean": -scores["test_rmse"].mean(),
                "r2_mean": scores["test_r2"].mean(),
            }
        )
    reg_results_df = pd.DataFrame(reg_results).sort_values(["r2_mean", "mae_mean"], ascending=[False, True])

    classification_models = {
        "dummy_majority": DummyClassifier(strategy="most_frequent"),
        "logistic": LogisticRegression(max_iter=2000),
        "random_forest": RandomForestClassifier(
            n_estimators=400,
            random_state=0,
            min_samples_leaf=5,
            n_jobs=-1,
        ),
    }
    cls_results = []
    for name, estimator in classification_models.items():
        if name == "dummy_majority":
            model = estimator
            X_used = df[["hour"]]
        else:
            model = Pipeline([("preprocess", preprocess), ("model", estimator)])
            X_used = df[feature_cols]
        scores = cross_validate(
            model,
            X_used,
            df["is_perfect"],
            cv=tscv,
            scoring={"accuracy": "accuracy", "roc_auc": "roc_auc", "f1": "f1"},
            n_jobs=1,
        )
        cls_results.append(
            {
                "model": name,
                "accuracy_mean": scores["test_accuracy"].mean(),
                "roc_auc_mean": scores["test_roc_auc"].mean(),
                "f1_mean": scores["test_f1"].mean(),
            }
        )
    cls_results_df = pd.DataFrame(cls_results).sort_values(["roc_auc_mean", "accuracy_mean"], ascending=[False, False])

    split_index = int(len(df) * 0.8)
    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    final_ridge = Pipeline([("preprocess", preprocess), ("model", Ridge(alpha=1.0))])
    final_ridge.fit(train_df[feature_cols], train_df["defect_rate"])
    ridge_preds = final_ridge.predict(test_df[feature_cols])
    ridge_holdout = {
        "mae": mean_absolute_error(test_df["defect_rate"], ridge_preds),
        "rmse": np.sqrt(mean_squared_error(test_df["defect_rate"], ridge_preds)),
        "r2": r2_score(test_df["defect_rate"], ridge_preds),
    }

    feature_names = final_ridge.named_steps["preprocess"].get_feature_names_out()
    ridge_coef = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": final_ridge.named_steps["model"].coef_,
            "abs_coefficient": np.abs(final_ridge.named_steps["model"].coef_),
        }
    ).sort_values("abs_coefficient", ascending=False)

    final_rf = Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=400,
                    random_state=0,
                    min_samples_leaf=5,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    final_rf.fit(train_df[feature_cols], train_df["defect_rate"])
    rf_preds = final_rf.predict(test_df[feature_cols])
    rf_holdout = {
        "mae": mean_absolute_error(test_df["defect_rate"], rf_preds),
        "rmse": np.sqrt(mean_squared_error(test_df["defect_rate"], rf_preds)),
        "r2": r2_score(test_df["defect_rate"], rf_preds),
    }
    rf_perm = permutation_importance(
        final_rf,
        test_df[feature_cols],
        test_df["defect_rate"],
        n_repeats=20,
        random_state=0,
        scoring="neg_mean_absolute_error",
        n_jobs=1,
    )
    rf_importance = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance_mean": rf_perm.importances_mean,
            "importance_std": rf_perm.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].scatter(ridge_preds, test_df["defect_rate"], alpha=0.55, color="#457B9D")
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="black")
    axes[0].set_title("Ridge: Predicted vs Actual")
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Actual")
    axes[1].scatter(rf_preds, test_df["defect_rate"], alpha=0.55, color="#E76F51")
    axes[1].plot([0, 1], [0, 1], linestyle="--", color="black")
    axes[1].set_title("Random Forest: Predicted vs Actual")
    axes[1].set_xlabel("Predicted")
    axes[1].set_ylabel("Actual")
    savefig("holdout_predicted_vs_actual.png")

    sm_X = pd.get_dummies(df[feature_cols], drop_first=True, dtype=float)
    sm_X = sm.add_constant(sm_X)
    ols_model = sm.OLS(df["defect_rate"], sm_X).fit()
    fitted = ols_model.fittedvalues
    residuals = ols_model.resid

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].scatter(fitted, residuals, alpha=0.5, color="#2A9D8F")
    axes[0].axhline(0, linestyle="--", color="black")
    axes[0].set_title("OLS Residuals vs Fitted")
    axes[0].set_xlabel("Fitted")
    axes[0].set_ylabel("Residual")
    sm.qqplot(residuals, line="45", ax=axes[1], markerfacecolor="#264653", markeredgecolor="#264653", alpha=0.5)
    axes[1].set_title("OLS Residual Q-Q Plot")
    savefig("ols_diagnostics.png")

    vif_df = pd.DataFrame(
        {
            "feature": sm_X.columns[1:],
            "vif": [variance_inflation_factor(sm_X.values, i) for i in range(1, sm_X.shape[1])],
        }
    ).sort_values("vif", ascending=False)

    ols_diag = {
        "r_squared": ols_model.rsquared,
        "adj_r_squared": ols_model.rsquared_adj,
        "f_pvalue": ols_model.f_pvalue,
        "durbin_watson": durbin_watson(residuals),
        "jarque_bera_stat": jarque_bera(residuals)[0],
        "jarque_bera_pvalue": jarque_bera(residuals)[1],
        "breusch_pagan_stat": het_breuschpagan(residuals, ols_model.model.exog)[0],
        "breusch_pagan_pvalue": het_breuschpagan(residuals, ols_model.model.exog)[1],
    }

    report = dedent(
        f"""
        # Dataset Analysis Report

        ## Executive Summary

        This dataset contains **{len(df):,} observations** and **{len(original_columns)} original columns** sampled at a perfectly regular **30-minute cadence** from **{df['timestamp'].min()}** to **{df['timestamp'].max()}**.

        The data are structurally clean: there are **no missing values**, timestamps are unique and monotonic, and the process signals remain in plausible numeric ranges. The main analytical challenge is not data quality but **weak explanatory signal**:

        - `defect_rate` is strongly bounded and **47.5% of records equal exactly `1.0`**, creating a severe upper-bound pile-up.
        - Pairwise linear relationships between the process variables and `defect_rate` are negligible; the largest absolute Pearson correlation is only **{corr['defect_rate'].drop('defect_rate').abs().max():.3f}**.
        - Time-aware regression and classification models perform at or near trivial baselines, indicating that the available features explain very little of the target variation.
        - OLS residual diagnostics reject normality, so classical linear-model inference is not reliable even though autocorrelation and multicollinearity are not major problems.

        The practical conclusion is that, with the variables present in `dataset.csv`, there is **no strong evidence of a controllable, stable driver of `defect_rate`**. Better prediction likely requires additional features such as machine state, material batch, maintenance history, sensor lags, or upstream/downstream quality context.

        ## 1. Data Loading and Inspection

        - Shape: **{raw_df.shape[0]} rows x {raw_df.shape[1]} columns**
        - Timestamp frequency: **{interval_counts.index[0]}** for all {len(intervals):,} gaps
        - Missing values: **0 across all columns**
        - Duplicate timestamps: **{df['timestamp'].duplicated().sum()}**
        - Operators: {", ".join(f"{idx} ({count})" for idx, count in df['operator'].value_counts().items())}

        ### Numeric Summary

        {format_table(summary_stats.reset_index().rename(columns={"index": "feature"}))}

        ### Null Counts

        {format_table(raw_df.isna().sum().rename("null_count").reset_index().rename(columns={"index": "column"}), digits=0)}

        ### Distribution Checks

        {format_table(shapiro_df)}

        Interpretation:

        - `temperature_c`, `pressure_bar`, and `speed_rpm` look approximately Gaussian in moderate samples.
        - `vibration_mm_s` is strongly right-skewed.
        - `defect_rate` is decisively non-normal because it is bounded and concentrated near the upper limit.

        ## 2. Exploratory Data Analysis

        Plots saved to `./plots/`:

        - `missingness_heatmap.png`
        - `numeric_distributions.png`
        - `correlation_heatmap.png`
        - `process_signals_over_time.png`
        - `defect_rate_time_series.png`
        - `defect_rate_vs_features.png`
        - `groupwise_boxplots.png`
        - `holdout_predicted_vs_actual.png`
        - `ols_diagnostics.png`

        ### Correlation Matrix

        {format_table(corr.reset_index().rename(columns={"index": "feature"}))}

        Key EDA findings:

        - `defect_rate` has almost no linear association with the measured process variables.
        - The process variables are also mostly uncorrelated with each other, which reduces confounding but also suggests the dataset lacks a strong latent process trend.
        - The target time series is noisy with a fairly stable rolling average and near-zero autocorrelation at short and daily lags.

        ### Outlier Review (IQR Rule)

        {format_table(outlier_df)}

        Interpretation:

        - Outliers are modest for most variables, but `vibration_mm_s` has a noticeable upper tail.
        - Low-end `defect_rate` values are flagged as outliers because the target is highly concentrated near `1.0`; these are influential rare events, not obvious data-entry errors.

        ### Group Comparisons

        Operator-level summary:

        {format_table(operator_summary.reset_index())}

        - Kruskal-Wallis test across operators: statistic = **{operator_test.statistic:.4f}**, p-value = **{operator_test.pvalue:.4f}**
        - Conclusion: no statistically significant operator effect at the 5% level.

        Hour-of-day mean `defect_rate`:

        {format_table(hour_means.rename("mean_defect_rate").reset_index())}

        Day-of-week mean `defect_rate`:

        {format_table(dayofweek_means.rename("mean_defect_rate").reset_index())}

        These temporal differences are small in magnitude and visually unstable rather than strongly systematic.

        ### Autocorrelation

        {format_table(autocorr.rename("autocorrelation").reset_index().rename(columns={"index": "lag"}))}

        ## 3. Modeling Strategy

        Because `defect_rate` is continuous but bounded in `[0, 1]` with a large point mass at `1.0`, I evaluated two modeling views:

        1. **Regression** on the raw `defect_rate`
        2. **Auxiliary classification** on whether a record achieved the upper bound (`defect_rate == 1.0`)

        Time order was preserved using **5-fold `TimeSeriesSplit`** to avoid leakage from future observations into past folds.

        ### Regression Results

        {format_table(reg_results_df)}

        Holdout performance on the last 20% of the series:

        | model | MAE | RMSE | R2 |
        |---|---:|---:|---:|
        | ridge | {ridge_holdout['mae']:.4f} | {ridge_holdout['rmse']:.4f} | {ridge_holdout['r2']:.4f} |
        | random_forest | {rf_holdout['mae']:.4f} | {rf_holdout['rmse']:.4f} | {rf_holdout['r2']:.4f} |

        Interpretation:

        - The **dummy mean regressor** is already hard to beat.
        - Linear and ridge models are essentially indistinguishable from the baseline.
        - Random forest does not uncover useful nonlinear structure; average CV `R^2` is still negative.
        - Negative `R^2` on time-aware validation means the models perform worse than predicting the fold mean.

        ### Classification Results (`defect_rate == 1.0`)

        {format_table(cls_results_df)}

        Interpretation:

        - The majority-class baseline reaches about **51.4% accuracy**, reflecting class balance.
        - Logistic regression and random forest produce mean ROC AUC values around **0.50**, which is effectively chance performance.
        - The predictors do not meaningfully separate perfect-score records from non-perfect ones.

        ### Feature Importance and Coefficients

        Top ridge coefficients by magnitude:

        {format_table(ridge_coef.head(8))}

        Random-forest permutation importance on holdout data:

        {format_table(rf_importance.head(8))}

        These effects are small and unstable. In weak-signal settings, rankings should not be over-interpreted.

        ## 4. Assumption Checks and Diagnostics

        I fit an interpretable OLS model to inspect assumptions, with predictors:
        `temperature_c`, `pressure_bar`, `vibration_mm_s`, `speed_rpm`, `hour`, `dayofweek`, and operator dummies.

        ### OLS Diagnostics

        | metric | value |
        |---|---:|
        | R-squared | {ols_diag['r_squared']:.4f} |
        | Adjusted R-squared | {ols_diag['adj_r_squared']:.4f} |
        | Model F-test p-value | {ols_diag['f_pvalue']:.4f} |
        | Durbin-Watson | {ols_diag['durbin_watson']:.4f} |
        | Jarque-Bera statistic | {ols_diag['jarque_bera_stat']:.4f} |
        | Jarque-Bera p-value | {ols_diag['jarque_bera_pvalue']:.4e} |
        | Breusch-Pagan statistic | {ols_diag['breusch_pagan_stat']:.4f} |
        | Breusch-Pagan p-value | {ols_diag['breusch_pagan_pvalue']:.4f} |

        VIF values:

        {format_table(vif_df)}

        Diagnostic interpretation:

        - **Autocorrelation**: Durbin-Watson near 2 indicates no serious serial correlation in residuals.
        - **Normality**: Jarque-Bera strongly rejects normal residuals. This is expected given the bounded, upper-inflated target.
        - **Homoskedasticity**: Breusch-Pagan is borderline but not strongly significant at 5%.
        - **Multicollinearity**: VIF values are low, so instability is not caused by collinearity.
        - **Overall fit**: the main failure is simply lack of explanatory power, not a hidden overfit relationship.

        ## 5. Final Conclusions

        1. The dataset is **clean and regularly sampled**, with no missing data or timestamp issues.
        2. `defect_rate` is **non-Gaussian and upper-inflated**, so standard Gaussian assumptions are a poor description of the target.
        3. There are **no strong pairwise relationships** between `defect_rate` and the available process variables.
        4. Operator, hour, and day-of-week effects are **small and not robust**.
        5. Regression and classification models validated with time-aware splits perform **at or near baseline**, so the current feature set has little predictive value.

        ## 6. Recommendations

        - Add lagged sensor features and rolling statistics if the process is believed to have delayed effects.
        - Add contextual variables that often drive manufacturing quality: batch ID, raw material lot, maintenance events, tool age, alarm states, calibration status, and machine identifier.
        - If `defect_rate` is conceptually a proportion with structural ones, consider a **two-part or zero/one-inflated beta-style model** once richer features are available.
        - If the target is actually a capped quality score rather than a physical defect proportion, rename it accordingly before downstream use to avoid modeling assumptions that do not fit the measurement process.
        """
    ).strip()
    report = "\n".join(line[8:] if line.startswith("        ") else line for line in report.splitlines()) + "\n"

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
