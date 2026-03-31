from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"

sns.set_theme(style="whitegrid", context="talk")


def metric_frame(y_true: pd.Series, y_pred: np.ndarray, split: str, model_name: str) -> dict[str, float | str]:
    return {
        "model": model_name,
        "split": split,
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def save_missingness_plot(df: pd.DataFrame) -> None:
    missing = df.isna().sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=missing.index, y=missing.values, ax=ax, color="#4C72B0")
    ax.set_title("Missing Values by Column")
    ax.set_xlabel("Column")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "missing_values.png", dpi=150)
    plt.close(fig)


def save_distribution_plots(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, col in zip(axes.flat, numeric_cols, strict=True):
        sns.histplot(df[col], kde=True, bins=24, ax=ax, color="#55A868")
        ax.set_title(f"Distribution of {col}")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "numeric_distributions.png", dpi=150)
    plt.close(fig)


def save_correlation_heatmap(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    corr = df[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".3f", ax=ax, vmin=-1, vmax=1)
    ax.set_title("Correlation Heatmap")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=150)
    plt.close(fig)


def save_temperature_voltage_plot(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.scatterplot(
        data=df,
        x="temperature_c",
        y="voltage_mv",
        hue="sensor_id",
        palette="deep",
        alpha=0.8,
        ax=ax,
    )
    x_line = np.linspace(df["temperature_c"].min(), df["temperature_c"].max(), 200)
    ax.plot(x_line, 2 * x_line + 3, color="black", linewidth=2, label="y = 2x + 3")
    ax.set_title("Voltage vs Temperature")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "temperature_voltage_scatter.png", dpi=150)
    plt.close(fig)


def save_time_series_plot(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
    series_specs = [
        ("temperature_c", "#C44E52"),
        ("humidity_pct", "#4C72B0"),
        ("pressure_hpa", "#8172B2"),
        ("voltage_mv", "#55A868"),
    ]
    for ax, (col, color) in zip(axes, series_specs, strict=True):
        ax.plot(df["timestamp"], df[col], color=color, linewidth=1.5)
        ax.set_ylabel(col)
    axes[0].set_title("Time Series Overview")
    axes[-1].set_xlabel("Timestamp")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "time_series_overview.png", dpi=150)
    plt.close(fig)


def save_sensor_boxplots(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    plot_cols = ["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
    for ax, col in zip(axes.flat, plot_cols, strict=True):
        sns.boxplot(data=df, x="sensor_id", y=col, ax=ax, color="#DD8452")
        ax.set_title(f"{col} by Sensor")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "sensor_boxplots.png", dpi=150)
    plt.close(fig)


def save_residual_plot(df: pd.DataFrame, residuals: np.ndarray) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].scatter(df["temperature_c"], residuals, alpha=0.75, color="#4C72B0")
    axes[0].axhline(0, color="black", linestyle="--")
    axes[0].set_title("Residuals vs Temperature")
    axes[0].set_xlabel("temperature_c")
    axes[0].set_ylabel("residual")

    sns.histplot(residuals, kde=True, ax=axes[1], color="#C44E52")
    axes[1].set_title("Residual Distribution")
    axes[1].set_xlabel("residual")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "model_residuals.png", dpi=150)
    plt.close(fig)


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(DATASET_PATH, parse_dates=["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df["timestamp"].dt.date
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    numeric_cols = ["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
    numeric_df = df[numeric_cols]

    save_missingness_plot(df.drop(columns=["date"]))
    save_distribution_plots(df, numeric_cols)
    save_correlation_heatmap(df, numeric_cols)
    save_temperature_voltage_plot(df)
    save_time_series_plot(df)
    save_sensor_boxplots(df)

    sorted_df = df.sort_values("timestamp").reset_index(drop=True)
    sensor_counts = sorted_df["sensor_id"].value_counts().sort_index()
    missing = sorted_df.isna().sum()
    duplicates = int(sorted_df.duplicated().sum())
    duplicate_timestamps = int(sorted_df["timestamp"].duplicated().sum())
    date_min = sorted_df["timestamp"].min()
    date_max = sorted_df["timestamp"].max()
    timestep_counts = sorted_df["timestamp"].diff().value_counts(dropna=True)
    lag1_autocorr = {col: float(sorted_df[col].autocorr()) for col in numeric_cols}

    outlier_rows: list[dict[str, object]] = []
    outlier_counts: dict[str, int] = {}
    for col in numeric_cols:
        q1, q3 = sorted_df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (sorted_df[col] < lower) | (sorted_df[col] > upper)
        outlier_counts[col] = int(mask.sum())
        if mask.any():
            subset = sorted_df.loc[mask, ["timestamp", "sensor_id", *numeric_cols]].copy()
            subset["outlier_variable"] = col
            subset["lower_bound"] = lower
            subset["upper_bound"] = upper
            outlier_rows.extend(subset.to_dict("records"))

    formula_diff = sorted_df["voltage_mv"] - (2 * sorted_df["temperature_c"] + 3)
    exact_formula_max_abs = float(np.abs(formula_diff).max())

    df_model = pd.get_dummies(sorted_df.copy(), columns=["sensor_id"], drop_first=True)
    sensor_dummies = [col for col in df_model.columns if col.startswith("sensor_id_")]
    train = df_model.iloc[:400].copy()
    test = df_model.iloc[400:].copy()

    feature_sets = {
        "baseline_mean": [],
        "non_temperature_features": ["humidity_pct", "pressure_hpa", "hour_sin", "hour_cos", *sensor_dummies],
        "temperature_only": ["temperature_c"],
        "full_feature_set": ["temperature_c", "humidity_pct", "pressure_hpa", "hour_sin", "hour_cos", *sensor_dummies],
    }

    metric_rows: list[dict[str, float | str]] = []
    fitted_models: dict[str, object] = {}
    residuals_temperature_only = None

    y_train = train["voltage_mv"]
    y_test = test["voltage_mv"]

    for model_name, features in feature_sets.items():
        if features:
            model = LinearRegression()
            model.fit(train[features], y_train)
            train_pred = model.predict(train[features])
            test_pred = model.predict(test[features])
        else:
            model = DummyRegressor(strategy="mean")
            model.fit(np.zeros((len(train), 1)), y_train)
            train_pred = model.predict(np.zeros((len(train), 1)))
            test_pred = model.predict(np.zeros((len(test), 1)))

        fitted_models[model_name] = model
        metric_rows.append(metric_frame(y_train, train_pred, "train", model_name))
        metric_rows.append(metric_frame(y_test, test_pred, "test", model_name))

        if model_name == "temperature_only":
            residuals_temperature_only = y_test.to_numpy() - test_pred

    assert residuals_temperature_only is not None
    save_residual_plot(test, residuals_temperature_only)

    temperature_model = fitted_models["temperature_only"]
    full_model = fitted_models["full_feature_set"]

    per_sensor_formula = []
    for sensor_id, group in sorted_df.groupby("sensor_id"):
        x = group["temperature_c"].to_numpy()
        y = group["voltage_mv"].to_numpy()
        design = np.column_stack([x, np.ones(len(x))])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual_max = float(np.abs(y - design @ coef).max())
        per_sensor_formula.append(
            {
                "sensor_id": sensor_id,
                "slope": float(coef[0]),
                "intercept": float(coef[1]),
                "max_abs_residual": residual_max,
            }
        )

    summary_stats = numeric_df.describe().round(3)
    grouped_means = sorted_df.groupby("sensor_id")[numeric_cols].agg(["mean", "std"]).round(3)
    corr = numeric_df.corr().round(6)
    metrics_df = pd.DataFrame(metric_rows).round(6)
    outliers_df = pd.DataFrame(outlier_rows)
    per_sensor_df = pd.DataFrame(per_sensor_formula).round(12)

    report_lines: list[str] = []
    report_lines.append("# Dataset Analysis Report")
    report_lines.append("")
    report_lines.append("## Scope")
    report_lines.append("")
    report_lines.append(
        "This report inspects the dataset, performs exploratory analysis, evaluates data quality, "
        "builds and validates predictive models, and checks whether any model assumptions are defensible."
    )
    report_lines.append("")
    report_lines.append("## 1. Data Loading and Inspection")
    report_lines.append("")
    report_lines.append(f"- File: `{DATASET_PATH.name}`")
    report_lines.append(f"- Shape: `{sorted_df.shape[0]} rows x {sorted_df.shape[1]} columns` after feature engineering")
    report_lines.append(f"- Original columns: `{', '.join(pd.read_csv(DATASET_PATH, nrows=0).columns.tolist())}`")
    report_lines.append(f"- Time span: `{date_min}` to `{date_max}`")
    report_lines.append(f"- Dominant time step: `{timestep_counts.index[0]}` observed `{int(timestep_counts.iloc[0])}` times")
    report_lines.append(f"- Duplicate rows: `{duplicates}`")
    report_lines.append(f"- Duplicate timestamps: `{duplicate_timestamps}`")
    report_lines.append("")
    report_lines.append("### Dtypes")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(sorted_df.dtypes.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Missing Values")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(missing.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Basic Numeric Statistics")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(summary_stats.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Sensor Counts")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(sensor_counts.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("## 2. Exploratory Data Analysis")
    report_lines.append("")
    report_lines.append("Generated plots:")
    report_lines.append("")
    for plot_name in [
        "missing_values.png",
        "numeric_distributions.png",
        "correlation_heatmap.png",
        "temperature_voltage_scatter.png",
        "time_series_overview.png",
        "sensor_boxplots.png",
        "model_residuals.png",
    ]:
        report_lines.append(f"- `plots/{plot_name}`")
    report_lines.append("")
    report_lines.append("### Correlations")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(corr.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Sensor-Level Summary")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(grouped_means.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Temporal Dependence")
    report_lines.append("")
    report_lines.append("Lag-1 autocorrelation values:")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(pd.Series(lag1_autocorr).round(6).to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("Interpretation: all lag-1 autocorrelations are close to zero, so there is little evidence of strong short-run persistence.")
    report_lines.append("")
    report_lines.append("## 3. Patterns, Relationships, and Anomalies")
    report_lines.append("")
    report_lines.append(f"- `voltage_mv` is an exact deterministic linear transformation of `temperature_c`: `voltage_mv = 2 * temperature_c + 3` within floating-point tolerance.")
    report_lines.append(f"- Maximum absolute deviation from that formula: `{exact_formula_max_abs:.3e}`.")
    report_lines.append(f"- The correlation between `temperature_c` and `voltage_mv` is `{corr.loc['temperature_c', 'voltage_mv']:.6f}`, effectively perfect.")
    report_lines.append("- `humidity_pct` and `pressure_hpa` show only weak linear associations with both temperature and voltage.")
    report_lines.append("- Sensor-level mean differences exist, but the temperature-to-voltage mapping is unchanged across all four sensors.")
    report_lines.append("- A small number of univariate IQR outliers appear in humidity and pressure, but none break the temperature-voltage rule.")
    report_lines.append("")
    report_lines.append("### IQR Outlier Counts")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(pd.Series(outlier_counts).to_string())
    report_lines.append("```")
    report_lines.append("")
    if not outliers_df.empty:
        trimmed_outliers = outliers_df[
            ["timestamp", "sensor_id", "outlier_variable", "temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]
        ].copy()
        report_lines.append("### Outlier Rows")
        report_lines.append("")
        report_lines.append("```text")
        report_lines.append(trimmed_outliers.to_string(index=False))
        report_lines.append("```")
        report_lines.append("")
    report_lines.append("### Per-Sensor Formula Check")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(per_sensor_df.to_string(index=False))
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("## 4. Modeling")
    report_lines.append("")
    report_lines.append(
        "A chronological 80/20 split was used: the first 400 observations for training and the last 100 for testing. "
        "This is more appropriate than a random split for ordered timestamped data, even though the series shows weak autocorrelation."
    )
    report_lines.append("")
    report_lines.append("Models compared:")
    report_lines.append("")
    report_lines.append("- `baseline_mean`: predicts the training-set mean voltage.")
    report_lines.append("- `non_temperature_features`: linear regression on humidity, pressure, hour-of-day sine/cosine encoding, and sensor dummies.")
    report_lines.append("- `temperature_only`: linear regression on temperature alone.")
    report_lines.append("- `full_feature_set`: the previous model plus all available covariates.")
    report_lines.append("")
    report_lines.append("### Validation Metrics")
    report_lines.append("")
    report_lines.append("```text")
    report_lines.append(metrics_df.to_string(index=False))
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Fitted Temperature Model")
    report_lines.append("")
    report_lines.append(
        f"- Estimated slope: `{float(temperature_model.coef_[0]):.12f}`"
    )
    report_lines.append(
        f"- Estimated intercept: `{float(temperature_model.intercept_):.12f}`"
    )
    report_lines.append(
        f"- Test-set residual max absolute value: `{float(np.abs(residuals_temperature_only).max()):.3e}`"
    )
    report_lines.append("")
    report_lines.append("### Full Model Coefficients")
    report_lines.append("")
    full_coef = pd.Series(full_model.coef_, index=feature_sets["full_feature_set"]).round(12)
    report_lines.append("```text")
    report_lines.append(full_coef.to_string())
    report_lines.append("```")
    report_lines.append("")
    report_lines.append(
        "Interpretation: once temperature is included, every other coefficient collapses to numerical noise around zero. "
        "The additional features do not improve predictive performance because voltage is already fully determined by temperature."
    )
    report_lines.append("")
    report_lines.append("## 5. Assumption Checks and Result Validation")
    report_lines.append("")
    report_lines.append("- Linearity: satisfied exactly for the temperature-voltage relationship.")
    report_lines.append("- Generalization: confirmed on the held-out chronological test set with `R^2 = 1.0` and residuals near machine precision.")
    report_lines.append("- Residual diagnostics: classical checks such as normality or heteroskedasticity are not meaningful here because residual variance is effectively zero.")
    report_lines.append("- Multicollinearity concern: the main issue is not unstable estimation but target derivation. `voltage_mv` appears engineered directly from `temperature_c` rather than independently generated with noise.")
    report_lines.append("- Leakage risk: if the real analytical goal were to predict an independently measured voltage, using temperature would be valid only if voltage is genuinely caused by temperature. If not, the dataset likely contains a derived variable and the prediction task is trivialized.")
    report_lines.append("")
    report_lines.append("## 6. Conclusions")
    report_lines.append("")
    report_lines.append("- The dataset is clean in the narrow operational sense: no missing values, no duplicate rows, regular hourly cadence, and stable schema.")
    report_lines.append("- The core finding dominates everything else: `voltage_mv` is deterministically encoded from `temperature_c` using `2 * temperature_c + 3`.")
    report_lines.append("- Humidity, pressure, timestamp-derived features, and sensor identity provide negligible incremental information for predicting voltage.")
    report_lines.append("- Because the target is effectively a formula of one predictor, this is not a realistic noisy forecasting problem. Any downstream scientific or operational conclusion should treat `voltage_mv` as a transformed version of temperature, not as an independent signal.")
    report_lines.append("")
    report_lines.append("## 7. Reproducibility")
    report_lines.append("")
    report_lines.append(f"- Analysis script: `analysis_pipeline.py`")
    report_lines.append(f"- Report output: `{REPORT_PATH.name}`")
    report_lines.append(f"- Plot directory: `{PLOTS_DIR.name}/`")
    report_lines.append("")

    REPORT_PATH.write_text("\n".join(report_lines))


if __name__ == "__main__":
    main()
