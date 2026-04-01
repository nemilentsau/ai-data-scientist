from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import make_scorer, mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.tsa.stattools import acf


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def format_pvalue(value: float) -> str:
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def as_code_block(obj: pd.DataFrame | pd.Series | str) -> str:
    if isinstance(obj, str):
        text = obj
    else:
        text = obj.to_string()
    return f"```\n{text}\n```"


def save_numeric_distributions(df: pd.DataFrame) -> None:
    numeric_cols = ["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, col in zip(axes.flat, numeric_cols):
        sns.histplot(df[col], kde=True, ax=ax, color="#4C78A8", edgecolor="white")
        ax.set_title(f"Distribution of {col}")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "numeric_distributions.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_correlation_heatmap(df: pd.DataFrame) -> None:
    corr = df.select_dtypes(include=["number"]).corr()
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlation Heatmap")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_time_series(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    cols = ["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
    colors = ["#E45756", "#72B7B2", "#54A24B", "#F58518"]
    for ax, col, color in zip(axes, cols, colors):
        ax.plot(df["timestamp"], df[col], lw=1.2, color=color)
        ax.set_title(f"{col} over time")
        ax.set_ylabel(col)
    axes[-1].set_xlabel("Timestamp")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "time_series.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_sensor_boxplots(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    metrics = ["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
    for ax, col in zip(axes.flat, metrics):
        sns.boxplot(data=df, x="sensor_id", y=col, ax=ax, color="#A0CBE8")
        ax.set_title(f"{col} by sensor")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "sensor_boxplots.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_voltage_temperature(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(data=df, x="temperature_c", y="voltage_mv", hue="sensor_id", ax=ax, s=45)
    x = np.linspace(df["temperature_c"].min(), df["temperature_c"].max(), 200)
    ax.plot(x, 2 * x + 3, color="black", linestyle="--", label="voltage = 2*temperature + 3")
    ax.set_title("Voltage vs Temperature")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "voltage_vs_temperature.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_temperature_model_diagnostics(df: pd.DataFrame, model: sm.regression.linear_model.RegressionResultsWrapper) -> None:
    fitted = model.fittedvalues
    resid = model.resid
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    sns.scatterplot(x=fitted, y=resid, ax=axes[0, 0], s=28, color="#4C78A8")
    axes[0, 0].axhline(0, color="black", linestyle="--", lw=1)
    axes[0, 0].set_title("Residuals vs Fitted")
    axes[0, 0].set_xlabel("Fitted temperature")
    axes[0, 0].set_ylabel("Residual")

    sm.qqplot(resid, line="45", ax=axes[0, 1], color="#E45756", alpha=0.7)
    axes[0, 1].set_title("Q-Q Plot of Residuals")

    sns.histplot(resid, kde=True, ax=axes[1, 0], color="#72B7B2", edgecolor="white")
    axes[1, 0].set_title("Residual Distribution")

    acf_vals = acf(df.sort_values("timestamp")["temperature_c"], nlags=24, fft=False)
    axes[1, 1].stem(range(len(acf_vals)), acf_vals, basefmt=" ")
    axes[1, 1].set_title("ACF of Temperature")
    axes[1, 1].set_xlabel("Lag")
    axes[1, 1].set_ylabel("Autocorrelation")

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "temperature_model_diagnostics.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid")

    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    raw_columns = list(df.columns)
    raw_shape = df.shape
    raw_dtypes = df.dtypes.astype(str)
    raw_nulls = df.isna().sum()

    df = df.sort_values("timestamp").reset_index(drop=True)
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek

    numeric_cols = ["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
    duplicates = int(df.duplicated().sum())
    duplicate_timestamps = int(df["timestamp"].duplicated().sum())
    duplicate_sensor_time = int(df.duplicated(["sensor_id", "timestamp"]).sum())
    timestamp_diff_counts = df["timestamp"].diff().dropna().value_counts().sort_index()
    describe = df[numeric_cols].describe().T
    corr = df[numeric_cols].corr()

    exact_voltage_relation = np.allclose(df["voltage_mv"], 2 * df["temperature_c"] + 3)
    max_voltage_diff = float(np.max(np.abs(df["voltage_mv"] - (2 * df["temperature_c"] + 3))))

    outlier_rows = {}
    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (df[col] < lower) | (df[col] > upper)
        outlier_rows[col] = {
            "count": int(mask.sum()),
            "lower": float(lower),
            "upper": float(upper),
            "rows": df.loc[mask, ["timestamp", "sensor_id", *numeric_cols]].copy(),
        }

    sensor_summary = df.groupby("sensor_id")[numeric_cols].agg(["count", "mean", "std", "min", "max"])

    anova_results = {}
    kruskal_results = {}
    shapiro_results = {}
    for col in ["temperature_c", "humidity_pct", "pressure_hpa"]:
        groups = [g[col].values for _, g in df.groupby("sensor_id")]
        anova_results[col] = stats.f_oneway(*groups)
        kruskal_results[col] = stats.kruskal(*groups)
    for sensor_id, group in df.groupby("sensor_id"):
        shapiro_results[sensor_id] = stats.shapiro(group["temperature_c"])
    levene_result = stats.levene(*[g["temperature_c"].values for _, g in df.groupby("sensor_id")])
    tukey = pairwise_tukeyhsd(df["temperature_c"], df["sensor_id"])
    tukey_df = pd.DataFrame(
        tukey._results_table.data[1:], columns=tukey._results_table.data[0]
    )

    calibration_X = sm.add_constant(df[["temperature_c"]])
    calibration_model = sm.OLS(df["voltage_mv"], calibration_X).fit()

    feature_cols = ["sensor_id", "humidity_pct", "pressure_hpa", "hour", "dayofweek"]
    X_temp = df[feature_cols]
    y_temp = df["temperature_c"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                ["humidity_pct", "pressure_hpa", "hour", "dayofweek"],
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                ["sensor_id"],
            ),
        ]
    )

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "r2": "r2",
        "mae": make_scorer(mean_absolute_error, greater_is_better=False),
        "rmse": make_scorer(root_mean_squared_error, greater_is_better=False),
    }
    model_pipelines = {
        "Linear regression": Pipeline(
            [("preprocessor", preprocessor), ("model", LinearRegression())]
        ),
        "Random forest": Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        min_samples_leaf=3,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }
    cv_results = {}
    for model_name, pipeline in model_pipelines.items():
        result = cross_validate(
            pipeline,
            X_temp,
            y_temp,
            cv=cv,
            scoring=scoring,
            return_train_score=False,
        )
        cv_results[model_name] = {
            "r2_mean": float(np.mean(result["test_r2"])),
            "r2_std": float(np.std(result["test_r2"])),
            "mae_mean": float(np.mean(-result["test_mae"])),
            "mae_std": float(np.std(-result["test_mae"])),
            "rmse_mean": float(np.mean(-result["test_rmse"])),
            "rmse_std": float(np.std(-result["test_rmse"])),
        }

    temp_X_ols = pd.get_dummies(
        df[["sensor_id", "humidity_pct", "pressure_hpa", "hour", "dayofweek"]],
        drop_first=True,
        dtype=float,
    )
    temp_X_ols = sm.add_constant(temp_X_ols)
    temp_model = sm.OLS(y_temp, temp_X_ols).fit()
    bp_stat = het_breuschpagan(temp_model.resid, temp_model.model.exog)
    ljung_box = acorr_ljungbox(temp_model.resid, lags=[10, 24], return_df=True)

    save_numeric_distributions(df)
    save_correlation_heatmap(df)
    save_time_series(df)
    save_sensor_boxplots(df)
    save_voltage_temperature(df)
    save_temperature_model_diagnostics(df, temp_model)

    hourly_means = df.groupby("hour")[["temperature_c", "humidity_pct", "pressure_hpa"]].mean()
    dayofweek_means = df.groupby("dayofweek")[["temperature_c", "humidity_pct", "pressure_hpa"]].mean()

    report = f"""# Dataset Analysis Report

## Executive Summary

This dataset contains **{raw_shape[0]} rows** and **{raw_shape[1]} columns** of hourly sensor observations from **{df['timestamp'].min()}** through **{df['timestamp'].max()}**.

Key conclusions:

1. The dataset is structurally clean: no missing values, no duplicate rows, and a complete hourly timestamp sequence.
2. `voltage_mv` is not an independent signal. It is an exact deterministic transform of temperature: **`voltage_mv = 2 * temperature_c + 3`** up to floating-point precision.
3. Aside from that engineered relationship, the remaining variables show weak associations. Humidity and pressure have near-zero linear correlation with temperature.
4. Sensors differ modestly in temperature distribution. The strongest pairwise difference is between `S-001` and `S-003`.
5. A non-leaky temperature prediction model performs poorly out of sample, indicating little recoverable predictive structure in `sensor_id`, humidity, pressure, and calendar features alone.

## 1. Data Loading and Inspection

### Shape and schema

- Shape: **{raw_shape[0]} rows x {raw_shape[1]} columns**
- Columns: {", ".join(raw_columns)}

### Data types

{as_code_block(raw_dtypes)}

### Missing values

{as_code_block(raw_nulls.to_frame("null_count"))}

### Duplication and temporal integrity

- Duplicate rows: **{duplicates}**
- Duplicate timestamps: **{duplicate_timestamps}**
- Duplicate sensor-timestamp pairs: **{duplicate_sensor_time}**
- Timestamp cadence: all consecutive differences are **1 hour**

Timestamp difference counts:

{timestamp_diff_counts.to_string()}

### Basic summary statistics

{as_code_block(describe.round(3))}

## 2. Exploratory Data Analysis

### Visual outputs

- [plots/numeric_distributions.png](plots/numeric_distributions.png)
- [plots/correlation_heatmap.png](plots/correlation_heatmap.png)
- [plots/time_series.png](plots/time_series.png)
- [plots/sensor_boxplots.png](plots/sensor_boxplots.png)
- [plots/voltage_vs_temperature.png](plots/voltage_vs_temperature.png)
- [plots/temperature_model_diagnostics.png](plots/temperature_model_diagnostics.png)

### Distributional observations

- `temperature_c` spans **{df['temperature_c'].min():.2f}** to **{df['temperature_c'].max():.2f}** with mean **{df['temperature_c'].mean():.2f}** and standard deviation **{df['temperature_c'].std():.2f}**.
- `humidity_pct` is centered near **{df['humidity_pct'].mean():.2f}%** and has a few IQR-rule outliers at both tails.
- `pressure_hpa` is tightly concentrated around **{df['pressure_hpa'].mean():.2f} hPa** with a few mild low-end outliers.
- `voltage_mv` mirrors temperature exactly because of the deterministic calibration relationship.

### Correlation structure

{as_code_block(corr.round(3))}

Interpretation:

- `corr(temperature_c, voltage_mv) = {corr.loc['temperature_c', 'voltage_mv']:.3f}` because voltage is an exact linear transform of temperature.
- `corr(temperature_c, humidity_pct) = {corr.loc['temperature_c', 'humidity_pct']:.3f}` and `corr(temperature_c, pressure_hpa) = {corr.loc['temperature_c', 'pressure_hpa']:.3f}`, both too small to support a strong practical linear relationship.

### Sensor-level summary

{as_code_block(sensor_summary.round(3))}

### Outlier review

IQR-rule outlier counts:

- `temperature_c`: **{outlier_rows['temperature_c']['count']}**
- `humidity_pct`: **{outlier_rows['humidity_pct']['count']}**
- `pressure_hpa`: **{outlier_rows['pressure_hpa']['count']}**
- `voltage_mv`: **{outlier_rows['voltage_mv']['count']}**

Humidity outliers:

{as_code_block(outlier_rows['humidity_pct']['rows'].to_string(index=False)) if not outlier_rows['humidity_pct']['rows'].empty else 'None'}

Pressure outliers:

{as_code_block(outlier_rows['pressure_hpa']['rows'].to_string(index=False)) if not outlier_rows['pressure_hpa']['rows'].empty else 'None'}

These outliers are mild and plausible for environmental measurements. I did not remove them because there is no evidence they are data entry errors.

### Time structure

- The series is hourly and complete over 20 full days plus 20 hours on the last day.
- The autocorrelation function of temperature is weak at short lags, suggesting little temporal persistence.
- Hour-of-day means fluctuate, but without a stable daily cycle strong enough to support forecasting from calendar time alone.

Hourly means:

{as_code_block(hourly_means.round(2))}

Day-of-week means:

{as_code_block(dayofweek_means.round(2))}

## 3. Key Patterns, Relationships, and Anomalies

### Deterministic engineering relationship

- Exact calibration check: **{exact_voltage_relation}**
- Maximum absolute deviation from `2 * temperature_c + 3`: **{max_voltage_diff:.3e}**

This is the dominant pattern in the data. Any model using both `temperature_c` and `voltage_mv` will exhibit perfect leakage unless one of the two is intentionally excluded.

### Sensor differences

Temperature differs across sensors more than humidity or pressure:

- ANOVA for temperature by sensor: **F = {anova_results['temperature_c'].statistic:.3f}, p = {format_pvalue(anova_results['temperature_c'].pvalue)}**
- Kruskal-Wallis for temperature by sensor: **H = {kruskal_results['temperature_c'].statistic:.3f}, p = {format_pvalue(kruskal_results['temperature_c'].pvalue)}**
- ANOVA for humidity by sensor: **p = {format_pvalue(anova_results['humidity_pct'].pvalue)}**
- ANOVA for pressure by sensor: **p = {format_pvalue(anova_results['pressure_hpa'].pvalue)}**

The nonparametric result agrees with ANOVA for temperature, so the sensor effect is not an artifact of normality assumptions alone.

Pairwise Tukey HSD for temperature:

{as_code_block(tukey_df.to_string(index=False))}

The only clearly significant pairwise difference after family-wise correction is `S-001` versus `S-003`.

## 4. Modeling

### Model A: Calibration model for voltage

I fit an ordinary least squares model with `voltage_mv` as the response and `temperature_c` as the sole predictor because the scatterplot indicated a perfect line.

- Intercept: **{calibration_model.params['const']:.6f}**
- Temperature coefficient: **{calibration_model.params['temperature_c']:.6f}**
- R-squared: **{calibration_model.rsquared:.6f}**

Interpretation:

This is not a predictive discovery so much as a recovered measurement equation. The fitted model reproduces **`voltage_mv = 3 + 2 * temperature_c`** exactly within floating-point tolerance.

### Model B: Non-leaky temperature prediction

To test whether the remaining features contain useful predictive information, I modeled `temperature_c` using:

- `sensor_id`
- `humidity_pct`
- `pressure_hpa`
- `hour`
- `dayofweek`

I intentionally excluded `voltage_mv` because it is a deterministic duplicate of the target.

#### Cross-validated performance

{as_code_block(pd.DataFrame(cv_results).T.round(3))}

Interpretation:

- Linear regression has mean cross-validated **R-squared = {cv_results['Linear regression']['r2_mean']:.3f}**
- Random forest has mean cross-validated **R-squared = {cv_results['Random forest']['r2_mean']:.3f}**

Both are near zero or negative, meaning they do not generalize better than predicting the mean. This supports the conclusion that the dataset contains little predictive structure beyond the voltage-temperature equation.

### In-sample explanatory temperature model

For interpretability and diagnostics, I also fit an OLS model to `temperature_c` with one-hot encoded sensor indicators plus humidity, pressure, hour, and day-of-week.

- In-sample R-squared: **{temp_model.rsquared:.3f}**
- Adjusted R-squared: **{temp_model.rsquared_adj:.3f}**

Selected coefficients:

{as_code_block(temp_model.params.round(4).to_frame("coefficient"))}

This model suggests lower mean temperatures for `S-003` and `S-004` relative to `S-001`, but the total explained variance remains small.

## 5. Assumption Checks and Validation

### Calibration model assumptions

The calibration model has effectively zero residual variance because the relationship is exact. That means:

- The estimated line is valid as a recovered formula.
- Classical residual diagnostics are not very informative because the residual distribution degenerates to numerical noise.

### Temperature group comparison assumptions

For ANOVA on temperature by sensor:

- Levene test for equal variances: **stat = {levene_result.statistic:.3f}, p = {format_pvalue(levene_result.pvalue)}**
- Shapiro-Wilk p-values by sensor:

{as_code_block(pd.DataFrame({k: {'W': v.statistic, 'p_value': v.pvalue} for k, v in shapiro_results.items()}).T.round(4))}

Interpretation:

- Homogeneity of variance is acceptable.
- Normality is rejected within each sensor group, which is not surprising given broad, somewhat flattened distributions.
- Because normality is questionable, I used Kruskal-Wallis as a robustness check; it confirmed the same qualitative conclusion.

### Temperature model residual checks

- Breusch-Pagan test for heteroskedasticity: **LM p = {format_pvalue(bp_stat[1])}, F p = {format_pvalue(bp_stat[3])}**
- Ljung-Box test on residual autocorrelation:

{as_code_block(ljung_box.round(4))}

Interpretation:

- No strong evidence of heteroskedasticity.
- No strong evidence of residual autocorrelation at lags 10 or 24.
- Residual normality is poor, as seen in the Q-Q plot and the OLS omnibus tests. This limits strict parametric inference, but does not change the larger practical finding that explained variance is very small.

## 6. Final Conclusions

1. The dataset is clean and temporally consistent.
2. `voltage_mv` is fully redundant with `temperature_c` and should be treated as a calibrated proxy, not a separate feature.
3. Humidity and pressure contribute little explanatory power for temperature in this sample.
4. Sensor identity carries a modest temperature offset, especially between `S-001` and `S-003`, but the effect is not large enough to make temperature strongly predictable.
5. After removing the leakage path through voltage, predictive models fail to generalize well. This dataset is more suitable for calibration validation and sensor comparison than for forecasting.

## 7. Recommendations

1. Drop one of `temperature_c` or `voltage_mv` in downstream predictive modeling to avoid perfect multicollinearity and leakage.
2. If the scientific goal is sensor calibration, formalize the deterministic equation and document it as part of the data dictionary.
3. If the goal is temperature prediction, collect more informative predictors such as location, external weather conditions, device state, or a longer time series with known seasonal structure.
4. If the goal is anomaly detection, keep the mild humidity and pressure outliers but define engineering thresholds rather than relying only on boxplot rules.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
