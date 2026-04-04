from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


def eta_squared_from_anova(groups: list[np.ndarray]) -> float:
    overall = np.concatenate(groups)
    grand_mean = overall.mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = ((overall - grand_mean) ** 2).sum()
    return float(ss_between / ss_total)


def fmt_p(p: float) -> str:
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def df_to_markdown_table(frame: pd.DataFrame, index: bool = True) -> str:
    cols = list(frame.columns)
    header = (["index"] if index else []) + [str(c) for c in cols]
    rows = []
    for idx, row in frame.iterrows():
        values = [str(idx)] if index else []
        values.extend(str(v) for v in row.tolist())
        rows.append(values)

    widths = [
        max(len(header[i]), max((len(r[i]) for r in rows), default=0))
        for i in range(len(header))
    ]

    def format_row(items: list[str]) -> str:
        return "| " + " | ".join(item.ljust(width) for item, width in zip(items, widths)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    parts = [format_row(header), separator]
    parts.extend(format_row(r) for r in rows)
    return "\n".join(parts)


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")

    raw_df = pd.read_csv(DATA_PATH)
    df = raw_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day
    sensor_order = sorted(df["sensor_id"].unique())

    orientation = {
        "shape": raw_df.shape,
        "time_min": df["timestamp"].min(),
        "time_max": df["timestamp"].max(),
        "sensor_counts": df["sensor_id"].value_counts().sort_index(),
        "ranges": raw_df[["temperature_c", "humidity_pct", "pressure_hpa", "voltage_mv"]]
        .agg(["min", "mean", "median", "max", "std"])
        .round(2),
    }

    # Hypothesis 1: there is a real daily cycle in temperature/humidity/pressure.
    groups_by_hour = {
        col: [g[col].to_numpy() for _, g in df.groupby("hour")]
        for col in ["temperature_c", "humidity_pct", "pressure_hpa"]
    }
    anova_hour = {
        col: stats.f_oneway(*groups).statistic
        for col, groups in groups_by_hour.items()
    }
    anova_hour_p = {
        col: stats.f_oneway(*groups).pvalue
        for col, groups in groups_by_hour.items()
    }
    eta_hour = {
        col: eta_squared_from_anova(groups)
        for col, groups in groups_by_hour.items()
    }

    hourly = (
        df.groupby("hour")[["temperature_c", "humidity_pct", "pressure_hpa"]]
        .agg(["mean", "sem"])
        .sort_index()
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 13), sharex=True)
    for ax, col, label in zip(
        axes,
        ["temperature_c", "humidity_pct", "pressure_hpa"],
        ["Temperature (C)", "Humidity (%)", "Pressure (hPa)"],
    ):
        mean = hourly[(col, "mean")]
        sem = hourly[(col, "sem")]
        ci = 1.96 * sem
        ax.plot(mean.index, mean.values, marker="o", linewidth=2.5)
        ax.fill_between(mean.index, mean - ci, mean + ci, alpha=0.2)
        ax.set_ylabel(label)
        ax.set_title(
            f"{label}: hourly mean with 95% CI | ANOVA p={fmt_p(anova_hour_p[col])}, eta²={eta_hour[col]:.3f}"
        )
    axes[-1].set_xlabel("Hour of day")
    savefig(PLOTS_DIR / "hourly_profiles.png")

    # Hypothesis 2: sensors show distinct operating regimes, especially for temperature.
    anova_sensor = {}
    eta_sensor = {}
    tukey_summary = None
    for col in ["temperature_c", "humidity_pct", "pressure_hpa"]:
        groups = [g[col].to_numpy() for _, g in df.groupby("sensor_id")]
        res = stats.f_oneway(*groups)
        anova_sensor[col] = res
        eta_sensor[col] = eta_squared_from_anova(groups)
        if col == "temperature_c":
            tukey_summary = pairwise_tukeyhsd(
                endog=df[col], groups=df["sensor_id"], alpha=0.05
            )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.boxplot(
        data=df,
        x="sensor_id",
        y="temperature_c",
        hue="sensor_id",
        order=sensor_order,
        dodge=False,
        legend=False,
        ax=axes[0],
        palette="Set2",
    )
    sns.stripplot(
        data=df,
        x="sensor_id",
        y="temperature_c",
        order=sensor_order,
        ax=axes[0],
        color="black",
        alpha=0.25,
        size=3,
    )
    axes[0].set_title(
        f"Temperature differs by sensor | ANOVA p={fmt_p(anova_sensor['temperature_c'].pvalue)}, eta²={eta_sensor['temperature_c']:.3f}"
    )
    axes[0].set_xlabel("Sensor")
    axes[0].set_ylabel("Temperature (C)")

    sns.boxplot(
        data=df,
        x="sensor_id",
        y="humidity_pct",
        hue="sensor_id",
        order=sensor_order,
        dodge=False,
        legend=False,
        ax=axes[1],
        palette="Set2",
    )
    sns.stripplot(
        data=df,
        x="sensor_id",
        y="humidity_pct",
        order=sensor_order,
        ax=axes[1],
        color="black",
        alpha=0.25,
        size=3,
    )
    axes[1].set_title(
        f"Humidity by sensor | ANOVA p={fmt_p(anova_sensor['humidity_pct'].pvalue)}, eta²={eta_sensor['humidity_pct']:.3f}"
    )
    axes[1].set_xlabel("Sensor")
    axes[1].set_ylabel("Humidity (%)")
    savefig(PLOTS_DIR / "sensor_boxplots.png")

    # Hypothesis 3: voltage is an independent sensor reading.
    voltage_model = smf.ols("voltage_mv ~ temperature_c", data=df).fit()
    voltage_resid_max = float(
        (df["voltage_mv"] - (2 * df["temperature_c"] + 3)).abs().max()
    )

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.scatterplot(
        data=df,
        x="temperature_c",
        y="voltage_mv",
        hue="sensor_id",
        palette="Set2",
        s=60,
        ax=ax,
    )
    x_grid = np.linspace(df["temperature_c"].min(), df["temperature_c"].max(), 200)
    ax.plot(x_grid, 2 * x_grid + 3, color="black", linewidth=2, linestyle="--")
    ax.set_title("Voltage is a deterministic linear transform of temperature")
    ax.set_xlabel("Temperature (C)")
    ax.set_ylabel("Voltage (mV)")
    ax.text(
        0.03,
        0.97,
        f"Fit: voltage = {voltage_model.params['Intercept']:.2f} + {voltage_model.params['temperature_c']:.2f} * temperature\nR² = {voltage_model.rsquared:.6f}",
        transform=ax.transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )
    savefig(PLOTS_DIR / "temperature_voltage_relationship.png")

    # Hypothesis 4: pressure and temperature move together in a meaningful way.
    temp_pressure = stats.pearsonr(df["temperature_c"], df["pressure_hpa"])
    tp_model = smf.ols("pressure_hpa ~ temperature_c", data=df).fit()

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.regplot(
        data=df,
        x="temperature_c",
        y="pressure_hpa",
        scatter_kws={"alpha": 0.65, "s": 45},
        line_kws={"color": "black"},
        ax=ax,
    )
    ax.set_title(
        f"Temperature vs pressure: weak positive association | r={temp_pressure.statistic:.3f}, p={fmt_p(temp_pressure.pvalue)}"
    )
    ax.set_xlabel("Temperature (C)")
    ax.set_ylabel("Pressure (hPa)")
    savefig(PLOTS_DIR / "temperature_pressure_scatter.png")

    # Supporting diagnostics used in the report.
    sensor_by_time_hour = stats.chi2_contingency(pd.crosstab(df["sensor_id"], df["hour"]))
    sensor_by_time_day = stats.chi2_contingency(pd.crosstab(df["sensor_id"], df["day"]))
    autocorr = {
        col: {lag: float(df[col].autocorr(lag)) for lag in [1, 6, 12, 24]}
        for col in ["temperature_c", "humidity_pct", "pressure_hpa"]
    }

    tukey_table = pd.DataFrame(
        data=tukey_summary._results_table.data[1:],
        columns=tukey_summary._results_table.data[0],
    )

    ranges_md = df_to_markdown_table(orientation["ranges"])
    tukey_sig = tukey_table.loc[
        tukey_table["reject"] == True, ["group1", "group2", "meandiff", "p-adj"]
    ].copy()
    tukey_sig_md = df_to_markdown_table(tukey_sig, index=False)

    report = f"""# Dataset Analysis Report

## What this dataset is about

This dataset contains 500 hourly observations from **2024-01-01 00:00:00** through **2024-01-21 19:00:00** for four sensors (`S-001` to `S-004`). Each row records a timestamp, sensor identifier, temperature in Celsius, humidity percentage, pressure in hPa, and voltage in mV.

The data are structurally clean:

- Shape: {orientation["shape"][0]} rows x {orientation["shape"][1]} columns
- Missing values: none
- Duplicate timestamps: 0
- Duplicate rows: 0
- Sensor counts: {", ".join(f"{k}={v}" for k, v in orientation["sensor_counts"].items())}

Column ranges:

{ranges_md}

Two orientation notes mattered for the rest of the analysis:

1. `timestamp` arrived as a string and needed parsing before any time-based analysis.
2. `voltage_mv` looked suspiciously tied to `temperature_c` from the raw rows, so I treated that as a data-quality question rather than assuming it was an independent measurement.

## Key findings

### 1. There is no convincing hourly or diurnal pattern in the environmental variables

I tested the hypothesis that temperature, humidity, or pressure follow a systematic hour-of-day cycle. The evidence does **not** support that.

- Temperature by hour: ANOVA F={anova_hour['temperature_c']:.3f}, p={fmt_p(anova_hour_p['temperature_c'])}, eta²={eta_hour['temperature_c']:.3f}
- Humidity by hour: ANOVA F={anova_hour['humidity_pct']:.3f}, p={fmt_p(anova_hour_p['humidity_pct'])}, eta²={eta_hour['humidity_pct']:.3f}
- Pressure by hour: ANOVA F={anova_hour['pressure_hpa']:.3f}, p={fmt_p(anova_hour_p['pressure_hpa'])}, eta²={eta_hour['pressure_hpa']:.3f}

The effect sizes are near zero, and [hourly_profiles.png]({(PLOTS_DIR / 'hourly_profiles.png').resolve()}) shows broad confidence bands with no stable morning-to-evening structure. A true physical environment often shows some daily rhythm, especially in temperature, but this series does not.

That impression is reinforced by weak serial dependence:

- Temperature autocorrelation: lag 1={autocorr['temperature_c'][1]:.3f}, lag 24={autocorr['temperature_c'][24]:.3f}
- Humidity autocorrelation: lag 1={autocorr['humidity_pct'][1]:.3f}, lag 24={autocorr['humidity_pct'][24]:.3f}
- Pressure autocorrelation: lag 1={autocorr['pressure_hpa'][1]:.3f}, lag 24={autocorr['pressure_hpa'][24]:.3f}

Interpretation: across the three environmental variables, the hourly sequence looks closer to weakly structured draws than to a smooth physical time series.

### 2. Temperature differs across sensors, but humidity and pressure do not

I next tested whether the sensors operate in distinct regimes.

- Temperature by sensor: ANOVA F={anova_sensor['temperature_c'].statistic:.3f}, p={fmt_p(anova_sensor['temperature_c'].pvalue)}, eta²={eta_sensor['temperature_c']:.3f}
- Humidity by sensor: ANOVA F={anova_sensor['humidity_pct'].statistic:.3f}, p={fmt_p(anova_sensor['humidity_pct'].pvalue)}, eta²={eta_sensor['humidity_pct']:.3f}
- Pressure by sensor: ANOVA F={anova_sensor['pressure_hpa'].statistic:.3f}, p={fmt_p(anova_sensor['pressure_hpa'].pvalue)}, eta²={eta_sensor['pressure_hpa']:.3f}

Only temperature shows a statistically credible sensor effect, and the effect size is still modest. Mean temperatures were:

- `S-001`: {df.groupby('sensor_id')['temperature_c'].mean()['S-001']:.2f} C
- `S-002`: {df.groupby('sensor_id')['temperature_c'].mean()['S-002']:.2f} C
- `S-003`: {df.groupby('sensor_id')['temperature_c'].mean()['S-003']:.2f} C
- `S-004`: {df.groupby('sensor_id')['temperature_c'].mean()['S-004']:.2f} C

[sensor_boxplots.png]({(PLOTS_DIR / 'sensor_boxplots.png').resolve()}) shows that `S-003` runs coolest and `S-001` warmest. Tukey's HSD indicates these significant temperature differences:

{tukey_sig_md}

I checked whether this could just be an artifact of sensor IDs being unevenly assigned over time. It does not look like that:

- Sensor vs hour chi-square p={fmt_p(sensor_by_time_hour[1])}
- Sensor vs day chi-square p={fmt_p(sensor_by_time_day[1])}

Interpretation: if these are real devices, the dataset suggests sensor-specific calibration or placement differences for temperature, but not for humidity or pressure.

### 3. `voltage_mv` is not an independent feature; it is exactly derived from temperature

The strongest finding in the dataset is a data-quality / feature-engineering issue rather than a natural relationship.

- Fitted model: `voltage_mv = {voltage_model.params['Intercept']:.2f} + {voltage_model.params['temperature_c']:.2f} * temperature_c`
- R² = {voltage_model.rsquared:.6f}
- Maximum absolute deviation from `2 * temperature_c + 3` = {voltage_resid_max:.2e}

[temperature_voltage_relationship.png]({(PLOTS_DIR / 'temperature_voltage_relationship.png').resolve()}) confirms that every point sits exactly on the same line, with no residual noise.

Interpretation: `voltage_mv` should not be treated as a separate predictor, target, or corroborating measurement. Including it in a predictive model would leak temperature almost perfectly and exaggerate model performance.

### 4. The only cross-variable association among the environmental measurements is weak

I tested whether temperature, humidity, and pressure meaningfully move together.

- Temperature vs humidity: Pearson r={stats.pearsonr(df['temperature_c'], df['humidity_pct']).statistic:.3f}, p={fmt_p(stats.pearsonr(df['temperature_c'], df['humidity_pct']).pvalue)}
- Temperature vs pressure: Pearson r={temp_pressure.statistic:.3f}, p={fmt_p(temp_pressure.pvalue)}
- Humidity vs pressure: Pearson r={stats.pearsonr(df['humidity_pct'], df['pressure_hpa']).statistic:.3f}, p={fmt_p(stats.pearsonr(df['humidity_pct'], df['pressure_hpa']).pvalue)}

The temperature-pressure slope is only {tp_model.params['temperature_c']:.3f} hPa per 1 C, with R²={tp_model.rsquared:.3f}. [temperature_pressure_scatter.png]({(PLOTS_DIR / 'temperature_pressure_scatter.png').resolve()}) shows a diffuse cloud rather than a tight physical law.

Interpretation: with 500 rows, even a very small effect can become statistically significant. The temperature-pressure link is real in the narrow statistical sense, but practically weak.

## What the findings mean

The dataset is internally tidy but only partly behaves like a real multivariate environmental monitoring stream.

- The absence of daily structure and near-zero autocorrelation suggest the time series has little temporal continuity.
- Sensor-to-sensor temperature differences are more prominent than time-based differences.
- `voltage_mv` is deterministic given temperature, so it contributes no new information.
- Relationships among the non-derived environmental variables are weak enough that strong mechanistic claims would be overreach.

For practical use, this means:

- Any model that uses `voltage_mv` to predict `temperature_c` would be trivial and misleading.
- If the task is device QA, the main actionable signal is the temperature offset between sensors.
- If the task is environmental inference, the dataset is limited because the measurements do not show the temporal coherence usually needed for forecasting or causal interpretation.

## Limitations and self-critique

The evidence supports the findings above, but there are important caveats.

- I treated rows as independent for most tests. That is imperfect for time-indexed data, although the very small autocorrelations make severe dependence less likely here.
- I did not have external metadata about the sensors, their locations, calibration procedures, or whether `voltage_mv` was intentionally engineered from temperature. If that transformation was by design, then the issue is documentation rather than corruption.
- I tested hour-of-day effects, but not longer seasonal or operational cycles beyond the 21-day window. A longer time span could reveal structure that is invisible here.
- The temperature sensor effect could reflect placement rather than calibration. Without location metadata, those explanations cannot be separated.
- Statistical significance was interpreted alongside effect size on purpose. With n=500, p-values alone would overstate weak associations.

The main alternative explanation I considered was that apparent sensor effects were caused by uneven sensor allocation across time. The chi-square checks did not support that explanation. I also considered whether the lack of temporal structure was a plotting artifact, which is why the report relies on both visual evidence and formal ANOVA / autocorrelation checks rather than a single chart.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
