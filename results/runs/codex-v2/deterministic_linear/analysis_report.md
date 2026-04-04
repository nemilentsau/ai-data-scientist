# Dataset Analysis Report

## What this dataset is about

This dataset contains 500 hourly observations from **2024-01-01 00:00:00** through **2024-01-21 19:00:00** for four sensors (`S-001` to `S-004`). Each row records a timestamp, sensor identifier, temperature in Celsius, humidity percentage, pressure in hPa, and voltage in mV.

The data are structurally clean:

- Shape: 500 rows x 6 columns
- Missing values: none
- Duplicate timestamps: 0
- Duplicate rows: 0
- Sensor counts: S-001=122, S-002=122, S-003=117, S-004=139

Column ranges:

| index  | temperature_c | humidity_pct | pressure_hpa | voltage_mv |
| ------ | ------------- | ------------ | ------------ | ---------- |
| min    | -19.49        | 9.5          | 984.0        | -35.98     |
| mean   | 29.86         | 50.11        | 1013.73      | 62.71      |
| median | 31.32         | 49.5         | 1013.8       | 65.63      |
| max    | 79.3          | 96.2         | 1038.8       | 161.6      |
| std    | 29.87         | 15.11        | 9.95         | 59.74      |

Two orientation notes mattered for the rest of the analysis:

1. `timestamp` arrived as a string and needed parsing before any time-based analysis.
2. `voltage_mv` looked suspiciously tied to `temperature_c` from the raw rows, so I treated that as a data-quality question rather than assuming it was an independent measurement.

## Key findings

### 1. There is no convincing hourly or diurnal pattern in the environmental variables

I tested the hypothesis that temperature, humidity, or pressure follow a systematic hour-of-day cycle. The evidence does **not** support that.

- Temperature by hour: ANOVA F=0.632, p=0.907, eta²=0.030
- Humidity by hour: ANOVA F=0.579, p=0.942, eta²=0.027
- Pressure by hour: ANOVA F=0.933, p=0.553, eta²=0.043

The effect sizes are near zero, and [hourly_profiles.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.OVGosEPYkM/plots/hourly_profiles.png) shows broad confidence bands with no stable morning-to-evening structure. A true physical environment often shows some daily rhythm, especially in temperature, but this series does not.

That impression is reinforced by weak serial dependence:

- Temperature autocorrelation: lag 1=0.039, lag 24=-0.009
- Humidity autocorrelation: lag 1=0.008, lag 24=-0.047
- Pressure autocorrelation: lag 1=-0.032, lag 24=-0.019

Interpretation: across the three environmental variables, the hourly sequence looks closer to weakly structured draws than to a smooth physical time series.

### 2. Temperature differs across sensors, but humidity and pressure do not

I next tested whether the sensors operate in distinct regimes.

- Temperature by sensor: ANOVA F=4.610, p=0.003, eta²=0.027
- Humidity by sensor: ANOVA F=1.938, p=0.123, eta²=0.012
- Pressure by sensor: ANOVA F=0.383, p=0.765, eta²=0.002

Only temperature shows a statistically credible sensor effect, and the effect size is still modest. Mean temperatures were:

- `S-001`: 36.48 C
- `S-002`: 31.40 C
- `S-003`: 22.52 C
- `S-004`: 28.86 C

[sensor_boxplots.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.OVGosEPYkM/plots/sensor_boxplots.png) shows that `S-003` runs coolest and `S-001` warmest. Tukey's HSD indicates these significant temperature differences:

| group1 | group2 | meandiff | p-adj  |
| ------ | ------ | -------- | ------ |
| S-001  | S-003  | -13.9585 | 0.0016 |

I checked whether this could just be an artifact of sensor IDs being unevenly assigned over time. It does not look like that:

- Sensor vs hour chi-square p=0.326
- Sensor vs day chi-square p=0.311

Interpretation: if these are real devices, the dataset suggests sensor-specific calibration or placement differences for temperature, but not for humidity or pressure.

### 3. `voltage_mv` is not an independent feature; it is exactly derived from temperature

The strongest finding in the dataset is a data-quality / feature-engineering issue rather than a natural relationship.

- Fitted model: `voltage_mv = 3.00 + 2.00 * temperature_c`
- R² = 1.000000
- Maximum absolute deviation from `2 * temperature_c + 3` = 1.78e-15

[temperature_voltage_relationship.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.OVGosEPYkM/plots/temperature_voltage_relationship.png) confirms that every point sits exactly on the same line, with no residual noise.

Interpretation: `voltage_mv` should not be treated as a separate predictor, target, or corroborating measurement. Including it in a predictive model would leak temperature almost perfectly and exaggerate model performance.

### 4. The only cross-variable association among the environmental measurements is weak

I tested whether temperature, humidity, and pressure meaningfully move together.

- Temperature vs humidity: Pearson r=0.068, p=0.128
- Temperature vs pressure: Pearson r=0.098, p=0.028
- Humidity vs pressure: Pearson r=0.035, p=0.439

The temperature-pressure slope is only 0.033 hPa per 1 C, with R²=0.010. [temperature_pressure_scatter.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.OVGosEPYkM/plots/temperature_pressure_scatter.png) shows a diffuse cloud rather than a tight physical law.

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
