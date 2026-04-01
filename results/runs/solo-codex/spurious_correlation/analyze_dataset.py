from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from matplotlib import pyplot as plt
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.graphics.gofplots import qqplot
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def rmse(y_true: pd.Series, y_pred: pd.Series | np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def poisson_deviance(y_true: np.ndarray, mu: np.ndarray) -> float:
    mu = np.clip(mu, 1e-9, None)
    return float(
        2
        * np.sum(
            np.where(y_true == 0, mu, y_true * np.log(np.clip(y_true / mu, 1e-9, None)) - (y_true - mu))
        )
    )


def series_to_block(series: pd.Series, round_digits: int | None = None) -> str:
    formatted = series.copy()
    if round_digits is not None:
        formatted = formatted.round(round_digits)
    return formatted.to_string()


def df_to_block(df: pd.DataFrame, round_digits: int | None = None) -> str:
    formatted = df.copy()
    if round_digits is not None:
        numeric_cols = formatted.select_dtypes(include=[np.number]).columns
        formatted.loc[:, numeric_cols] = formatted.loc[:, numeric_cols].round(round_digits)
    return formatted.to_string()


def build_plots(df: pd.DataFrame, monthly: pd.DataFrame, corr: pd.DataFrame, sales_model, pool_model, poisson_model) -> None:
    sns.set_theme(style="whitegrid", context="talk")

    fig, axes = plt.subplots(4, 1, figsize=(16, 18), sharex=True)
    line_specs = [
        ("avg_temperature_c", "Avg Temperature (C)", "#1f77b4"),
        ("ice_cream_sales_units", "Ice Cream Sales", "#ff7f0e"),
        ("pool_visits", "Pool Visits", "#2ca02c"),
        ("drowning_incidents", "Drowning Incidents", "#d62728"),
    ]
    for ax, (col, title, color) in zip(axes, line_specs):
        ax.plot(df["date"], df[col], color=color, linewidth=1.5)
        ax.set_title(title)
    axes[-1].set_xlabel("Date")
    fig.suptitle("Daily Time Series", y=0.995)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "time_series_overview.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    cols = [
        "avg_temperature_c",
        "ice_cream_sales_units",
        "pool_visits",
        "drowning_incidents",
        "uv_index",
        "humidity_pct",
    ]
    for ax, col in zip(axes.flat, cols):
        sns.histplot(df[col], kde=True, ax=ax, color="#4c72b0")
        ax.set_title(f"Distribution: {col}")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "distributions.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f", ax=ax)
    ax.set_title("Correlation Heatmap")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    scatter_specs = [
        ("avg_temperature_c", "ice_cream_sales_units", "Temperature vs Ice Cream Sales"),
        ("avg_temperature_c", "pool_visits", "Temperature vs Pool Visits"),
        ("avg_temperature_c", "drowning_incidents", "Temperature vs Drowning Incidents"),
    ]
    for ax, (x, y, title) in zip(axes, scatter_specs):
        sns.regplot(
            data=df,
            x=x,
            y=y,
            lowess=True,
            scatter_kws={"alpha": 0.45, "s": 35},
            line_kws={"color": "#d62728", "linewidth": 2},
            ax=ax,
        )
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "temperature_relationships.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    monthly_plot = monthly.reset_index().melt(id_vars="month", var_name="metric", value_name="value")
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.lineplot(data=monthly_plot, x="month", y="value", hue="metric", marker="o", linewidth=2.2, ax=ax)
    ax.set_title("Monthly Seasonality")
    ax.set_xticks(range(1, 13))
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "monthly_seasonality.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fitted = sales_model.fittedvalues
    resid = sales_model.resid
    sns.scatterplot(x=fitted, y=resid, alpha=0.5, s=35, ax=axes[0, 0], color="#1f77b4")
    axes[0, 0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0, 0].set_title("Sales OLS Residuals vs Fitted")
    qqplot(resid, line="45", fit=True, ax=axes[0, 1])
    axes[0, 1].set_title("Sales OLS QQ Plot")
    plot_acf(resid, lags=30, ax=axes[1, 0])
    axes[1, 0].set_title("Sales OLS Residual ACF")
    sns.histplot(resid, kde=True, ax=axes[1, 1], color="#ff7f0e")
    axes[1, 1].set_title("Sales OLS Residual Distribution")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "sales_model_diagnostics.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    sns.scatterplot(
        x=poisson_model.fittedvalues,
        y=poisson_model.resid_pearson,
        alpha=0.5,
        s=40,
        ax=axes[0],
        color="#2ca02c",
    )
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Poisson Pearson Residuals vs Fitted")
    sns.histplot(poisson_model.resid_pearson, kde=True, ax=axes[1], color="#d62728")
    axes[1].set_title("Poisson Pearson Residual Distribution")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "drowning_poisson_diagnostics.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear

    numeric_cols = [
        "avg_temperature_c",
        "ice_cream_sales_units",
        "pool_visits",
        "drowning_incidents",
        "uv_index",
        "humidity_pct",
    ]

    original_cols = ["date", *numeric_cols]
    basic_summary = df[numeric_cols].describe().T
    null_counts = df[original_cols].isna().sum()
    duplicate_dates = int(df["date"].duplicated().sum())
    date_gaps = df["date"].diff().dropna().dt.days
    irregular_steps = int((date_gaps != 1).sum())
    corr = df[numeric_cols].corr()
    monthly = df.groupby("month")[numeric_cols].mean()

    skew_kurt = pd.DataFrame(
        {
            "skew": [stats.skew(df[c]) for c in numeric_cols],
            "excess_kurtosis": [stats.kurtosis(df[c]) for c in numeric_cols],
            "zero_count": [(df[c] == 0).sum() for c in numeric_cols],
        },
        index=numeric_cols,
    )

    outlier_rows = []
    for c in numeric_cols:
        q1, q3 = df[c].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo = q1 - 1.5 * iqr
        hi = q3 + 1.5 * iqr
        outlier_rows.append(
            {
                "column": c,
                "lower_bound": lo,
                "upper_bound": hi,
                "iqr_outlier_count": int(((df[c] < lo) | (df[c] > hi)).sum()),
            }
        )
    outlier_summary = pd.DataFrame(outlier_rows).set_index("column")

    full_vif_cols = ["avg_temperature_c", "uv_index", "humidity_pct", "pool_visits", "ice_cream_sales_units"]
    vif_X = sm.add_constant(df[full_vif_cols], has_constant="add")
    vif = pd.Series(
        [variance_inflation_factor(vif_X.values, i) for i in range(vif_X.shape[1])],
        index=vif_X.columns,
        name="VIF",
    )

    train = df[df["date"] < "2024-01-01"].copy()
    test = df[df["date"] >= "2024-01-01"].copy()

    weather_features = ["avg_temperature_c", "uv_index", "humidity_pct"]
    X_train = sm.add_constant(train[weather_features], has_constant="add")
    X_test = sm.add_constant(test[weather_features], has_constant="add")
    X_full = sm.add_constant(df[weather_features], has_constant="add")

    sales_model = sm.OLS(train["ice_cream_sales_units"], X_train).fit()
    pool_model = sm.OLS(train["pool_visits"], X_train).fit()
    poisson_model = sm.GLM(train["drowning_incidents"], X_train, family=sm.families.Poisson()).fit()

    sales_pred_test = sales_model.predict(X_test)
    pool_pred_test = pool_model.predict(X_test)
    drown_pred_test = poisson_model.predict(X_test)
    drown_null_pred = np.repeat(train["drowning_incidents"].mean(), len(test))

    sales_model_full = sm.OLS(df["ice_cream_sales_units"], X_full).fit()
    pool_model_full = sm.OLS(df["pool_visits"], X_full).fit()
    poisson_model_full = sm.GLM(df["drowning_incidents"], X_full, family=sm.families.Poisson()).fit()

    sales_influence = sales_model_full.get_influence().summary_frame()
    sales_influential = pd.concat(
        [
            df[["date", "ice_cream_sales_units", "avg_temperature_c", "uv_index", "humidity_pct"]],
            sales_influence[["standard_resid", "cooks_d"]],
        ],
        axis=1,
    ).nlargest(8, "cooks_d")

    sales_bp = het_breuschpagan(sales_model.resid, X_train)
    pool_bp = het_breuschpagan(pool_model.resid, X_train)
    sales_shapiro = stats.shapiro(sales_model.resid.sample(min(500, len(sales_model.resid)), random_state=0))
    pool_shapiro = stats.shapiro(pool_model.resid.sample(min(500, len(pool_model.resid)), random_state=0))

    sales_metrics = {
        "test_mae": mean_absolute_error(test["ice_cream_sales_units"], sales_pred_test),
        "test_rmse": rmse(test["ice_cream_sales_units"], sales_pred_test),
        "test_r2": r2_score(test["ice_cream_sales_units"], sales_pred_test),
        "durbin_watson_train_resid": durbin_watson(sales_model.resid),
        "breusch_pagan_p": sales_bp[1],
        "shapiro_p": sales_shapiro.pvalue,
    }
    pool_metrics = {
        "test_mae": mean_absolute_error(test["pool_visits"], pool_pred_test),
        "test_rmse": rmse(test["pool_visits"], pool_pred_test),
        "test_r2": r2_score(test["pool_visits"], pool_pred_test),
        "durbin_watson_train_resid": durbin_watson(pool_model.resid),
        "breusch_pagan_p": pool_bp[1],
        "shapiro_p": pool_shapiro.pvalue,
    }
    poisson_dispersion = ((train["drowning_incidents"] - poisson_model.mu) ** 2 / poisson_model.mu).sum() / poisson_model.df_resid
    drown_metrics = {
        "test_mae": mean_absolute_error(test["drowning_incidents"], drown_pred_test),
        "test_rmse": rmse(test["drowning_incidents"], drown_pred_test),
        "test_poisson_deviance": poisson_deviance(test["drowning_incidents"].to_numpy(), drown_pred_test.to_numpy()),
        "null_poisson_deviance": poisson_deviance(test["drowning_incidents"].to_numpy(), drown_null_pred),
        "mean_predicted_rate": float(np.mean(drown_pred_test)),
        "mean_actual_rate": float(test["drowning_incidents"].mean()),
        "observed_zero_rate": float((test["drowning_incidents"] == 0).mean()),
        "predicted_zero_rate_mean": float(np.mean(np.exp(-drown_pred_test))),
        "train_dispersion": float(poisson_dispersion),
    }

    build_plots(df, monthly, corr, sales_model_full, pool_model_full, poisson_model_full)

    top_drowning = df.nlargest(
        8,
        "drowning_incidents",
    )[
        [
            "date",
            "drowning_incidents",
            "avg_temperature_c",
            "pool_visits",
            "ice_cream_sales_units",
            "uv_index",
            "humidity_pct",
        ]
    ]

    report = f"""# Dataset Analysis Report

## Executive Summary

This dataset contains **{len(df)} daily observations** from **{df['date'].min().date()} to {df['date'].max().date()}** with no missing values and a complete daily cadence. The dominant structure is strong annual seasonality: temperature, UV index, ice cream sales, pool visits, and drowning incidents all rise together in warmer months, while humidity is comparatively weakly related to the other variables.

The two strongest business-style targets are:

- **Ice cream sales**: a weather-driven continuous outcome that is modeled well with linear regression.
- **Pool visits**: also well explained by weather with linear regression.

For **drowning incidents**, the response is a low-count, zero-heavy series, so a **Poisson generalized linear model** is more appropriate than OLS. The Poisson dispersion estimate is close to 1, which supports the Poisson assumption and does not justify a more complex negative binomial model for this dataset.

One important caution: the weather and behavior variables are **extremely collinear** because they all share the same seasonal pattern. This makes them useful predictors but weakens coefficient-level causal interpretation in multivariable models that include multiple seasonal proxies simultaneously.

## 1. Data Loading and Inspection

- Shape: **{df.shape[0]} rows x {df.shape[1] - 3} original columns**
- Date coverage: **{df['date'].min().date()} to {df['date'].max().date()}**
- Duplicate dates: **{duplicate_dates}**
- Irregular date steps: **{irregular_steps}**

### Dtypes

```text
{series_to_block(df[original_cols].dtypes)}
```

### Null Counts

```text
{series_to_block(null_counts)}
```

### Basic Statistics

```text
{df_to_block(basic_summary, 3)}
```

### Shape Diagnostics

```text
{df_to_block(skew_kurt, 3)}
```

Observations:

- No missing values or duplicate dates were found.
- The dataset is unusually clean for operational data.
- `drowning_incidents` is strongly right-skewed and contains many zeros.
- `ice_cream_sales_units` and `pool_visits` have many zero days, concentrated in cold months.

## 2. Exploratory Data Analysis

Generated plots:

- `plots/time_series_overview.png`
- `plots/distributions.png`
- `plots/correlation_heatmap.png`
- `plots/temperature_relationships.png`
- `plots/monthly_seasonality.png`
- `plots/sales_model_diagnostics.png`
- `plots/drowning_poisson_diagnostics.png`

### Correlation Matrix

```text
{df_to_block(corr, 3)}
```

### Average by Month

```text
{df_to_block(monthly, 2)}
```

### IQR-Based Outlier Summary

```text
{df_to_block(outlier_summary, 3)}
```

Key EDA takeaways:

- `avg_temperature_c`, `uv_index`, `ice_cream_sales_units`, and `pool_visits` move together very tightly.
- `ice_cream_sales_units` and `avg_temperature_c` have an especially strong correlation (**{corr.loc['avg_temperature_c', 'ice_cream_sales_units']:.3f}**).
- `pool_visits` is likewise strongly associated with temperature (**{corr.loc['avg_temperature_c', 'pool_visits']:.3f}**).
- `drowning_incidents` has a moderate positive relationship with warm-weather activity variables, but much weaker than the sales and pool signals.
- `humidity_pct` is almost orthogonal to the main seasonal variables.

## 3. Patterns, Relationships, and Anomalies

### Seasonality

The monthly profiles show a clear annual cycle:

- Winter months have near-zero pool use and very low ice cream demand.
- Late spring through summer has the highest temperature, UV, sales, visits, and incidents.
- Drowning incidents peak in **June and July** on average, aligning with the highest exposure/activity months.

### Multicollinearity

Variance inflation factors for a full seasonal-feature set:

```text
{series_to_block(vif.round(2))}
```

Interpretation:

- Temperature, UV, pool visits, and ice cream sales all have high VIF values.
- This means those variables contain overlapping seasonal information.
- A coefficient sign flip in a saturated model would not be surprising and should not be over-interpreted.

### Potentially Unusual Observations

Largest drowning-incident days:

```text
{df_to_block(top_drowning, 2)}
```

Most influential points for the full-sample ice cream sales model:

```text
{df_to_block(sales_influential, 3)}
```

Interpretation:

- The highest-incident days occur on warm, high-activity days rather than isolated cold-weather anomalies.
- The most influential sales observations are still plausible and generally lie on the same seasonal manifold.
- There is no strong evidence of gross data corruption, but a few days have unusually high positive sales residuals.

## 4. Modeling Strategy

I fit models on **2023 as training data** and evaluated them on **2024 as a forward holdout set**. That is stricter than random splitting because it respects time order.

### Model A: Ice Cream Sales

Model form:

`ice_cream_sales_units ~ avg_temperature_c + uv_index + humidity_pct`

Why this model:

- The target is continuous and high-volume.
- The weather relationship appears approximately linear in the scatterplots.
- A simple weather model is interpretable and performs very well.

Training coefficients:

```text
{sales_model.params.round(4).to_string()}
```

### Model B: Pool Visits

Model form:

`pool_visits ~ avg_temperature_c + uv_index + humidity_pct`

Training coefficients:

```text
{pool_model.params.round(4).to_string()}
```

### Model C: Drowning Incidents

Model form:

`drowning_incidents ~ avg_temperature_c + uv_index + humidity_pct`

Why Poisson:

- The target is a non-negative count.
- It is zero-heavy and right-skewed.
- The estimated train dispersion is **{drown_metrics['train_dispersion']:.3f}**, which is close to 1.

Training coefficients:

```text
{poisson_model.params.round(4).to_string()}
```

## 5. Assumption Checks and Validation

### Ice Cream Sales OLS

Validation:

```text
{pd.Series(sales_metrics).round(4).to_string()}
```

Assumption notes:

- Residuals are close to normal by QQ plot and Shapiro test.
- Breusch-Pagan p-value indicates **some heteroskedasticity**.
- Durbin-Watson indicates **mild positive autocorrelation** in training residuals.
- Despite those imperfections, holdout performance is very strong.

### Pool Visits OLS

Validation:

```text
{pd.Series(pool_metrics).round(4).to_string()}
```

Assumption notes:

- Residual normality looks acceptable.
- There is again mild heteroskedasticity and mild autocorrelation.
- The model generalizes well on the 2024 holdout set.

### Drowning Incidents Poisson GLM

Validation:

```text
{pd.Series(drown_metrics).round(4).to_string()}
```

Assumption notes:

- The Poisson dispersion statistic is close to 1, so overdispersion is not a major concern.
- The predicted zero rate (**{drown_metrics['predicted_zero_rate_mean']:.3f}**) is reasonably close to the observed zero rate (**{drown_metrics['observed_zero_rate']:.3f}**).
- Holdout Poisson deviance is materially lower than the null-model deviance, so the weather model adds predictive signal.
- On the training fit, temperature is the clearest signal; UV and humidity are weaker once temperature is already present.

## 6. Findings

1. **The dataset is dominated by shared seasonality.** Temperature, UV, ice cream sales, and pool visits all rise and fall together over the year.
2. **Ice cream sales are highly weather-sensitive.** A simple linear model using weather alone explains most of the variation and generalizes strongly to the next year.
3. **Pool visits show the same pattern.** Weather is also enough to explain a large majority of variation in visits.
4. **Drowning incidents increase in warmer, more active periods, but the signal is weaker and noisier.** A count model is required; OLS would be a poor choice.
5. **Humidity contributes little.** It has weak marginal correlation with the main outcomes and is not a stable driver in the fitted models.
6. **Multicollinearity limits causal interpretation.** Because many predictors are seasonal proxies, coefficient-level interpretations should be made cautiously.
7. **The data looks unusually smooth and structured.** The tight relationships and clean seasonality are more consistent with a simulated or heavily curated dataset than messy real-world observational data.

## 7. Recommendations

- For **prediction**, the simple weather-driven models are adequate and interpretable.
- For **causal claims**, avoid saying that ice cream sales or pool visits themselves cause drowning; they likely proxy for shared seasonal exposure.
- If this were a production problem, I would next test:
  - day-of-week effects
  - holiday indicators
  - lagged weather effects
  - spline or GAM terms for nonlinearity
  - robust or HAC standard errors for the OLS models

## Reproducibility

The report and plots were generated programmatically from `dataset.csv` by running `analyze_dataset.py`.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
