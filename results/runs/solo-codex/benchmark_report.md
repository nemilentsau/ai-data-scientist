# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| deterministic_linear | - | solved (100%) | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|--------------|----------------|-----------|
| Codex | 100% | 0% | 100% | 100% | 100% |

## Detailed Results

### deterministic_linear

#### Codex (solved)

**Summary:** This is an exemplary analysis. The agent quickly identified the core pattern — voltage_mv = 2 * temperature_c + 3 as an exact deterministic relationship — verified it to floating-point precision, recovered the exact slope (2) and intercept (3), reported R² = 1.0 on held-out data, explicitly wrote the equation, demonstrated that all other features are irrelevant noise, and avoided any unnecessary model complexity. The agent also went further by checking the formula per-sensor and flagging the leakage/derived-variable implication. All must-have and supporting criteria are hit; no forbidden criteria are triggered. Verdict: solved.
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Oracle Attainment (r2):** 100%
**Efficiency:** report_chars=8842, trace_events=55, transcript_chars=46336

**Must Have**
- `deterministic_linear_linear_relationship_identified`: hit. The analysis explicitly and repeatedly identifies the relationship as exact and deterministic linear. Evidence: voltage_mv is an exact deterministic linear transformation of temperature_c: voltage_mv = 2 * temperature_c + 3 within floating-point tolerance. Maximum absolute deviation from that formula: 1.776e-15.
- `deterministic_linear_slope_recovered`: hit. Slope of exactly 2 is reported in multiple places including the fitted model and per-sensor checks. Evidence: Estimated slope: 2.000000000000; Per-sensor formula check shows slope=2.0 for all four sensors.
- `deterministic_linear_intercept_recovered`: hit. Intercept of exactly 3 is reported in multiple places. Evidence: Estimated intercept: 3.000000000000; Per-sensor formula check shows intercept=3.0 for all four sensors.
- `deterministic_linear_fit_near_perfect`: hit. R² = 1.0 is reported for both training and test sets of the temperature-only model. Evidence: temperature_only train 0.000000 0.000000 1.000000 / temperature_only test 0.000000 0.000000 1.000000 (rmse, mae, r2 columns)

**Supporting**
- `deterministic_linear_equation_written`: hit. The exact equation is written out explicitly in both the patterns section and conclusions. Evidence: voltage_mv = 2 * temperature_c + 3
- `deterministic_linear_ignores_noise_columns`: hit. The analysis identifies humidity, pressure, timestamp features, and sensor identity as irrelevant and demonstrates their coefficients collapse to zero. Evidence: once temperature is included, every other coefficient collapses to numerical noise around zero. The additional features do not improve predictive performance because voltage is already fully determined by temperature.
- `deterministic_linear_avoids_overcomplication`: hit. Only linear regression models and a baseline mean were used. No nonlinear models were attempted. The temperature-only linear model is presented as the correct and sufficient solution. Evidence: Models compared: baseline_mean, non_temperature_features, temperature_only, full_feature_set — all linear. Conclusion: treat voltage_mv as a transformed version of temperature, not as an independent signal.

**Forbidden**
- `deterministic_linear_claims_nonlinear_structure`: miss. The analysis never claims or suggests a nonlinear relationship. It consistently describes the relationship as exact linear. Evidence: Linearity: satisfied exactly for the temperature-voltage relationship.
- `deterministic_linear_unnecessary_model_complexity`: miss. The main recommended model is a simple single-variable linear regression. The full_feature_set model was included only as a comparison to demonstrate that additional features add nothing. Evidence: The temperature_only model is presented as the definitive model; the full model is shown only to prove other features are noise.
