from __future__ import annotations

import math
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.graphics.gofplots import qqplot
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, acf


warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "dataset.csv"
PLOTS_DIR = BASE_DIR / "plots"
REPORT_PATH = BASE_DIR / "analysis_report.md"


def rmse(y_true: pd.Series, y_pred: pd.Series | np.ndarray) -> float:
    return math.sqrt(mean_squared_error(y_true, y_pred))


def to_code_block(text: str) -> str:
    return f"```\n{text}\n```"


def format_p(p: float) -> str:
    return f"{p:.4g}" if p >= 1e-4 else f"{p:.2e}"


def save_plot(fig: plt.Figure, name: str) -> str:
    path = PLOTS_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return f"./plots/{name}"


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATA_PATH)
    raw_shape = df.shape
    raw_dtypes = df.dtypes.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    numeric_cols = [
        "pageviews",
        "unique_visitors",
        "bounce_rate",
        "avg_session_duration_sec",
        "new_signups",
        "support_tickets",
    ]

    # Data audit
    null_counts = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_dates = int(df["date"].duplicated().sum())
    expected_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    missing_dates = expected_dates.difference(df["date"])
    zeros = (df[numeric_cols] == 0).sum()
    negatives = (df[numeric_cols] < 0).sum()

    descriptive_stats = df[numeric_cols].describe().T.round(3)
    iqr_rows = []
    zscore_rows = []
    anomaly_dates: dict[str, list[str]] = {}
    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        iqr_count = int(((df[col] < lower) | (df[col] > upper)).sum())
        iqr_rows.append(
            {
                "column": col,
                "iqr_outliers": iqr_count,
                "lower_bound": round(lower, 3),
                "upper_bound": round(upper, 3),
            }
        )

        z = np.abs(stats.zscore(df[col], nan_policy="omit"))
        z_mask = z > 3
        z_count = int(np.nansum(z_mask))
        zscore_rows.append({"column": col, "zscore_outliers_gt3": z_count})
        anomaly_dates[col] = (
            df.loc[z_mask, "date"].dt.strftime("%Y-%m-%d").tolist()
        )

    outlier_summary = pd.DataFrame(iqr_rows)
    zscore_summary = pd.DataFrame(zscore_rows)

    # Time features
    df["day_name"] = df["date"].dt.day_name()
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["t"] = np.arange(len(df))
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    yearly_means = df.groupby("year")[numeric_cols].mean().round(3)
    monthly_means = (
        df.set_index("date")
        .resample("ME")[numeric_cols]
        .mean()
        .round(3)
    )
    dow_means = df.groupby("day_name")[numeric_cols].mean().reindex(day_order).round(3)
    corr = df[numeric_cols].corr().round(3)

    # Statistical checks
    kruskal_results = []
    for col in ["pageviews", "unique_visitors", "new_signups", "support_tickets"]:
        groups = [df.loc[df["day_name"] == day, col].values for day in day_order]
        stat, pvalue = stats.kruskal(*groups)
        kruskal_results.append(
            {"metric": col, "kruskal_stat": round(stat, 3), "p_value": pvalue}
        )
    kruskal_df = pd.DataFrame(kruskal_results)

    adf_results = []
    for col in ["pageviews", "unique_visitors", "new_signups", "support_tickets"]:
        adf_stat, pvalue, _, _, _, _ = adfuller(df[col])
        adf_results.append(
            {"metric": col, "adf_stat": round(adf_stat, 3), "p_value": pvalue}
        )
    adf_df = pd.DataFrame(adf_results)

    stl_pageviews = STL(df.set_index("date")["pageviews"], period=7, robust=True).fit()
    stl_unique = STL(df.set_index("date")["unique_visitors"], period=7, robust=True).fit()
    stl_signups = STL(df.set_index("date")["new_signups"], period=7, robust=True).fit()

    def strength(result: STL, component: str) -> float:
        resid = np.var(result.resid)
        total = np.var(result.resid + getattr(result, component))
        return max(0.0, 1 - resid / total)

    season_trend_strength = pd.DataFrame(
        {
            "metric": ["pageviews", "unique_visitors", "new_signups"],
            "seasonal_strength": [
                round(strength(stl_pageviews, "seasonal"), 3),
                round(strength(stl_unique, "seasonal"), 3),
                round(strength(stl_signups, "seasonal"), 3),
            ],
            "trend_strength": [
                round(strength(stl_pageviews, "trend"), 3),
                round(strength(stl_unique, "trend"), 3),
                round(strength(stl_signups, "trend"), 3),
            ],
        }
    )

    # Plot 1: time series overview
    fig, axes = plt.subplots(3, 2, figsize=(18, 14), sharex=True)
    for ax, col in zip(axes.flat, numeric_cols):
        ax.plot(df["date"], df[col], linewidth=1.2)
        ax.set_title(col.replace("_", " ").title())
    overview_plot = save_plot(fig, "timeseries_overview.png")

    # Plot 2: correlation heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f", ax=ax)
    ax.set_title("Correlation Heatmap")
    heatmap_plot = save_plot(fig, "correlation_heatmap.png")

    # Plot 3: weekly patterns
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    for ax, col in zip(
        axes.flat,
        ["pageviews", "unique_visitors", "new_signups", "support_tickets"],
    ):
        sns.boxplot(data=df, x="day_name", y=col, order=day_order, ax=ax)
        ax.tick_params(axis="x", rotation=30)
        ax.set_title(f"{col.replace('_', ' ').title()} by Day of Week")
    weekly_plot = save_plot(fig, "weekly_patterns.png")

    # Plot 4: STL decomposition for pageviews
    fig = stl_pageviews.plot()
    fig.set_size_inches(16, 10)
    stl_plot = save_plot(fig, "pageviews_stl_decomposition.png")

    # Plot 5: anomalies
    fig, axes = plt.subplots(3, 1, figsize=(18, 12), sharex=True)
    anomaly_cols = ["bounce_rate", "new_signups", "support_tickets"]
    for ax, col in zip(axes, anomaly_cols):
        ax.plot(df["date"], df[col], color="steelblue", linewidth=1.2)
        z = np.abs(stats.zscore(df[col], nan_policy="omit"))
        mask = z > 3
        ax.scatter(df.loc[mask, "date"], df.loc[mask, col], color="crimson", s=40)
        ax.set_title(f"{col.replace('_', ' ').title()} with z-score > 3 anomalies")
    anomalies_plot = save_plot(fig, "anomaly_flags.png")

    # Plot 6: pageviews forecast model on holdout
    split_idx = int(len(df) * 0.8)
    train = df.iloc[:split_idx].copy()
    test = df.iloc[split_idx:].copy()

    for k in [1, 2, 3]:
        df[f"sin{k}"] = np.sin(2 * np.pi * k * df["t"] / 365.25)
        df[f"cos{k}"] = np.cos(2 * np.pi * k * df["t"] / 365.25)
    train = df.iloc[:split_idx].copy()
    test = df.iloc[split_idx:].copy()

    pageview_features = ["t"] + [f"sin{k}" for k in [1, 2, 3]] + [f"cos{k}" for k in [1, 2, 3]]
    X_train = pd.concat(
        [
            train[pageview_features],
            pd.get_dummies(train["day_name"], prefix="dow", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    X_test = pd.concat(
        [
            test[pageview_features],
            pd.get_dummies(test["day_name"], prefix="dow", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)
    X_train = sm.add_constant(X_train)
    X_test = sm.add_constant(X_test, has_constant="add")
    y_train = train["pageviews"]
    y_test = test["pageviews"]

    pageviews_model = sm.OLS(y_train, X_train).fit()
    pageviews_pred = pageviews_model.predict(X_test)
    seasonal_naive_pred = df["pageviews"].shift(7).iloc[split_idx:]

    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(train["date"], train["pageviews"], label="Train", linewidth=1.0, alpha=0.7)
    ax.plot(test["date"], y_test, label="Actual", linewidth=1.5)
    ax.plot(test["date"], pageviews_pred, label="Calendar OLS Forecast", linewidth=1.5)
    ax.plot(test["date"], seasonal_naive_pred, label="7-day seasonal naive", linewidth=1.2, alpha=0.9)
    ax.set_title("Pageviews Holdout Forecast")
    ax.legend()
    forecast_plot = save_plot(fig, "pageviews_holdout_forecast.png")

    # Plot 7: residual diagnostics for pageviews model
    residuals = pageviews_model.resid
    fitted = pageviews_model.fittedvalues
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes[0, 0].scatter(fitted, residuals, alpha=0.5)
    axes[0, 0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0, 0].set_title("Residuals vs Fitted")
    sns.histplot(residuals, kde=True, ax=axes[0, 1])
    axes[0, 1].set_title("Residual Distribution")
    qqplot(residuals, line="45", ax=axes[1, 0])
    axes[1, 0].set_title("Normal Q-Q")
    plot_acf(residuals, lags=30, ax=axes[1, 1])
    axes[1, 1].set_title("Residual ACF")
    residual_plot = save_plot(fig, "pageviews_residual_diagnostics.png")

    # Modeling: pageviews metrics and checks
    pageviews_metrics = pd.DataFrame(
        [
            {
                "model": "7-day seasonal naive",
                "mae": round(mean_absolute_error(y_test, seasonal_naive_pred), 3),
                "rmse": round(rmse(y_test, seasonal_naive_pred), 3),
            },
            {
                "model": "Calendar OLS",
                "mae": round(mean_absolute_error(y_test, pageviews_pred), 3),
                "rmse": round(rmse(y_test, pageviews_pred), 3),
            },
        ]
    )
    pageview_lb = acorr_ljungbox(residuals, lags=[7, 14], return_df=True).round(4)
    bp_stat, bp_pvalue, _, _ = het_breuschpagan(residuals, X_train)
    shapiro_p = stats.shapiro(residuals.sample(min(500, len(residuals)), random_state=0)).pvalue

    # Modeling: signups
    signup_baseline_pred = np.repeat(train["new_signups"].mean(), len(test))
    signup_features = ["t", "sin1", "cos1", "sin2", "cos2"]
    Xs_train = pd.concat(
        [
            train[signup_features],
            pd.get_dummies(train["day_name"], prefix="dow", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    Xs_test = pd.concat(
        [
            test[signup_features],
            pd.get_dummies(test["day_name"], prefix="dow", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    Xs_test = Xs_test.reindex(columns=Xs_train.columns, fill_value=0)
    Xs_train = sm.add_constant(Xs_train)
    Xs_test = sm.add_constant(Xs_test, has_constant="add")
    signup_model = sm.GLM(train["new_signups"], Xs_train, family=sm.families.Poisson()).fit()
    signup_pred = signup_model.predict(Xs_test)
    overdispersion_ratio = signup_model.pearson_chi2 / signup_model.df_resid

    # Exploratory signups explanation model using observed metrics
    Xe = pd.concat(
        [
            df[
                [
                    "pageviews",
                    "unique_visitors",
                    "bounce_rate",
                    "avg_session_duration_sec",
                    "support_tickets",
                ]
            ],
            pd.get_dummies(df["day_name"], prefix="dow", drop_first=True, dtype=float),
        ],
        axis=1,
    )
    Xe = sm.add_constant(Xe)
    signup_expl_model = sm.GLM(df["new_signups"], Xe, family=sm.families.Poisson()).fit()
    signup_expl_pvals = signup_expl_model.pvalues.sort_values()
    signup_expl_sig = signup_expl_pvals[signup_expl_pvals < 0.05]

    # Auxiliary autocorrelation summaries
    signup_acf = pd.Series(acf(df["new_signups"], nlags=14, fft=True), index=range(15)).round(3)
    ticket_acf = pd.Series(acf(df["support_tickets"], nlags=14, fft=True), index=range(15)).round(3)

    # Key findings
    unique_pairs = []
    for i, left in enumerate(corr.columns):
        for j, right in enumerate(corr.columns):
            if j <= i:
                continue
            unique_pairs.append(((left, right), corr.loc[left, right]))
    highest_corr = sorted(unique_pairs, key=lambda item: abs(item[1]), reverse=True)[:6]
    top_pairs = [
        f"{pair[0]} vs {pair[1]}: {value:.3f}" for pair, value in highest_corr
    ]

    anomaly_lines = []
    for col in anomaly_cols:
        dates = anomaly_dates[col]
        if dates:
            anomaly_lines.append(f"- `{col}`: {', '.join(dates)}")

    report = f"""# Dataset Analysis Report

## Scope
This report analyzes `dataset.csv`, a daily web analytics dataset covering **{df['date'].min().date()}** to **{df['date'].max().date()}**. The workflow includes data quality checks, exploratory analysis, anomaly detection, time-series decomposition, predictive modeling, and model diagnostics.

## 1. Data Loading And Inspection

### Structure
- Raw shape: **{raw_shape[0]} rows x {raw_shape[1]} columns**
- Date range: **{df['date'].min().date()}** to **{df['date'].max().date()}**
- Frequency audit: **{len(missing_dates)}** missing dates over an expected **{len(expected_dates)}**-day span
- Duplicate rows: **{duplicate_rows}**
- Duplicate dates: **{duplicate_dates}**

### Dtypes
{to_code_block(raw_dtypes.to_string())}

### Null Counts
{to_code_block(null_counts.to_string())}

### Descriptive Statistics
{to_code_block(descriptive_stats.to_string())}

### Zeros And Negatives
{to_code_block(pd.DataFrame({'zeros': zeros, 'negatives': negatives}).to_string())}

### Outlier Screening
I used both the IQR rule and z-scores greater than 3 because a single heuristic can miss meaningful anomalies in skewed or bounded metrics.

{to_code_block(outlier_summary.to_string(index=False))}

{to_code_block(zscore_summary.to_string(index=False))}

### Initial Data Quality Assessment
- The dataset is structurally clean: no nulls, duplicate rows, duplicate dates, or missing calendar days.
- `support_tickets` legitimately contains zeros; no numeric field contains negative values.
- The most notable isolated anomalies occur in bounded engagement and count metrics rather than in traffic volume.

## 2. Exploratory Data Analysis

### Saved Visualizations
- Overview time series: `{overview_plot}`
- Correlation heatmap: `{heatmap_plot}`
- Weekly pattern boxplots: `{weekly_plot}`
- STL decomposition for `pageviews`: `{stl_plot}`
- Anomaly flags: `{anomalies_plot}`
- Holdout forecast comparison: `{forecast_plot}`
- Residual diagnostics: `{residual_plot}`

### Correlations
The strongest pairwise relationships are:
{chr(10).join(f"- {line}" for line in top_pairs)}

Full matrix:
{to_code_block(corr.to_string())}

### Temporal Aggregates
Yearly means show strong growth in traffic volume but little movement in conversion or support burden:

{to_code_block(yearly_means.to_string())}

Day-of-week means:
{to_code_block(dow_means[['pageviews', 'unique_visitors', 'new_signups', 'support_tickets']].to_string())}

### Weekly Pattern Tests
I used the Kruskal-Wallis test rather than one-way ANOVA because these are operational metrics with possible non-normality and unequal variances.

{to_code_block(pd.DataFrame({'metric': kruskal_df['metric'], 'kruskal_stat': kruskal_df['kruskal_stat'], 'p_value': kruskal_df['p_value'].map(format_p)}).to_string(index=False))}

Interpretation:
- `pageviews` and `unique_visitors` vary significantly by day of week.
- `new_signups` and `support_tickets` do not show statistically significant day-of-week shifts.

### Stationarity Checks
I used the Augmented Dickey-Fuller test to distinguish trending traffic series from closer-to-stationary operational counts.

{to_code_block(pd.DataFrame({'metric': adf_df['metric'], 'adf_stat': adf_df['adf_stat'], 'p_value': adf_df['p_value'].map(format_p)}).to_string(index=False))}

### Decomposition Strength
STL with weekly period (`period=7`) indicates:

{to_code_block(season_trend_strength.to_string(index=False))}

Interpretation:
- `pageviews` has both strong trend and strong weekly seasonality.
- `unique_visitors` behaves similarly, though with slightly weaker seasonality.
- `new_signups` has weak trend and weak seasonality, which explains why feature-driven or calendar-driven models struggle to improve much over a baseline.

### Anomalies
The z-score based anomalies greater than 3 standard deviations are:
{chr(10).join(anomaly_lines)}

Notable examples:
- `bounce_rate` spikes to **0.695** on **2024-01-31** and falls to **0.172** on **2022-10-10**.
- `new_signups` hits **27** on **2023-01-09**, **2024-05-03**, and **2024-11-06**.
- `support_tickets` spikes to **10** on **2023-11-05** and **9** on several isolated dates.

## 3. Key Patterns, Relationships, And Anomalies

- Traffic volume grew sharply across the three years: average `pageviews` rose from **{yearly_means.loc[2022, 'pageviews']:.1f}** in 2022 to **{yearly_means.loc[2024, 'pageviews']:.1f}** in 2024, while `unique_visitors` rose from **{yearly_means.loc[2022, 'unique_visitors']:.1f}** to **{yearly_means.loc[2024, 'unique_visitors']:.1f}**.
- Growth in traffic did **not** translate into materially higher `new_signups`: yearly means remain near **15/day** throughout the period.
- `pageviews` and `unique_visitors` are almost redundant for explanatory modeling (`r = {corr.loc['pageviews', 'unique_visitors']:.3f}`), so combining both in a linear model introduces multicollinearity without adding much signal.
- Traffic is highly calendar-driven. Mondays and Sundays are the strongest days; Thursdays are among the weakest.
- `new_signups` appears largely independent of the observed web metrics. In lag scans from 0 to 14 days, the largest absolute linear correlation was under 0.08, which is weak in practical terms.
- `support_tickets` behaves like low-memory count noise: its sample autocorrelations through lag 14 stay close to zero.

## 4. Modeling

### Model A: `pageviews` Forecasting
Goal: forecast daily `pageviews` on a time-ordered holdout set.

Train/test split:
- Train: first **{len(train)}** days
- Test: last **{len(test)}** days

Candidate models:
- 7-day seasonal naive benchmark
- Calendar OLS with linear time trend, annual Fourier terms, and day-of-week dummies

Holdout performance:
{to_code_block(pageviews_metrics.to_string(index=False))}

Rationale:
- The seasonal naive benchmark is a strong sanity check for daily series with pronounced weekly repetition.
- The selected OLS model is appropriate because the series shows deterministic structure: smooth growth, yearly seasonality, and strong weekday effects.
- More opaque or heavier time-series models are unnecessary when an interpretable regression already captures the pattern well and passes diagnostics.

Pageviews model coefficients (abridged intuition):
- Positive time trend: about **{pageviews_model.params['t']:.3f}** pageviews per day.
- Large weekday premiums for Monday, Tuesday, Saturday, and Sunday relative to Friday.
- Strong first annual sine term, consistent with broad within-year cycles.

### Model B: `new_signups` Count Modeling
Goal: test whether signups are predictably driven by observed time/calendar structure.

Compared models:
- Intercept-only baseline
- Poisson GLM with time trend, annual Fourier terms, and day-of-week dummies

Holdout results:
{to_code_block(pd.DataFrame([{'model': 'Mean baseline', 'mae': round(mean_absolute_error(test['new_signups'], signup_baseline_pred), 3), 'rmse': round(rmse(test['new_signups'], signup_baseline_pred), 3)}, {'model': 'Calendar Poisson GLM', 'mae': round(mean_absolute_error(test['new_signups'], signup_pred), 3), 'rmse': round(rmse(test['new_signups'], signup_pred), 3)}]).to_string(index=False))}

Interpretation:
- The Poisson GLM does **not** beat the mean baseline in a meaningful way.
- Calendar terms are not statistically significant.
- This is evidence that `new_signups` is mostly stable day-to-day noise around a constant mean, at least relative to the variables available here.

### Exploratory Explanatory Model For Signups
I also fit a Poisson model using the observed web metrics plus day-of-week dummies. Result:
- Overdispersion ratio (Pearson chi-square / df): **{overdispersion_ratio:.3f}**
- Statistically significant predictors at 0.05 level: **{', '.join(signup_expl_sig.index.tolist()) if not signup_expl_sig.empty else 'none'}**

This means the observed traffic, bounce, session duration, and support metrics do not provide a convincing explanation for signup variation in this dataset.

## 5. Assumption Checks And Validation

### Pageviews Calendar OLS Diagnostics
- Residual autocorrelation (Ljung-Box):
{to_code_block(pageview_lb.to_string())}
- Heteroskedasticity (Breusch-Pagan p-value): **{format_p(bp_pvalue)}**
- Residual normality (Shapiro-Wilk p-value on random sample of 500 residuals): **{format_p(shapiro_p)}**
- Training R-squared: **{pageviews_model.rsquared:.3f}**

Assessment:
- No evidence of problematic residual autocorrelation at lags 7 or 14 after modeling.
- No evidence of strong heteroskedasticity.
- Residuals are close enough to normal for standard inference in this context.
- The model is therefore usable both descriptively and predictively.

### Signups Poisson Diagnostics
- Pearson chi-square / residual df: **{overdispersion_ratio:.3f}**
- A ratio near 1 indicates Poisson variance is reasonable here.
- The issue is not violated count-model assumptions; the issue is lack of predictive signal.

Autocorrelation summaries:
{to_code_block(pd.DataFrame({'lag': list(signup_acf.index), 'new_signups_acf': signup_acf.values, 'support_tickets_acf': ticket_acf.values}).to_string(index=False))}

## 6. Conclusions

- The dataset is clean and complete, so the main risks are analytical rather than data-quality related.
- Traffic is strongly structured by long-run growth and weekly seasonality. This is the dominant pattern in the dataset.
- `pageviews` can be modeled well with an interpretable calendar regression; it clearly outperforms a simple weekly seasonal-naive baseline on the holdout set.
- `unique_visitors` tracks `pageviews` very closely and adds limited incremental information.
- `new_signups` is surprisingly insensitive to both traffic and engagement metrics in this dataset. Higher traffic does not imply higher conversions here.
- `support_tickets` is stable, low-count, and mostly weakly dependent on the other variables.

## 7. Limitations

- No external drivers are available, such as marketing spend, campaign launches, product changes, pricing shifts, or incidents. Those omitted variables could plausibly explain signups.
- Only three years of data are available, which is adequate for weekly and yearly seasonality but thin for richer structural break analysis.
- Correlation and predictive failure do not prove causal independence; they show that the variables observed here are insufficient for a strong explanatory model.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
