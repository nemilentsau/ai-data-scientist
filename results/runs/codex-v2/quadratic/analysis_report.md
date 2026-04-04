# Analysis Report

## What this dataset is about

This dataset contains 600 engine test runs with 7 columns: a row identifier (`test_id`), operating conditions (`engine_rpm`, `ambient_temp_c`, `humidity_pct`), fuel specification (`octane_rating`), asset condition (`vehicle_age_years`), and the measured outcome (`fuel_consumption_lph`).

Orientation checks before modeling:

- Shape: 600 rows x 7 columns.
- Missing data: none in any column.
- Types: all columns were numeric on load; `octane_rating` behaves like a categorical factor with 4 levels (87, 89, 91, 93).
- Ranges:
  - `engine_rpm`: 826 to 5,999
  - `ambient_temp_c`: 3.4 to 49.6
  - `humidity_pct`: 10.0 to 95.0
  - `vehicle_age_years`: 0 to 14
  - `fuel_consumption_lph`: 0.50 to 74.22
- Raw-row sanity check: the first several rows were internally consistent with the column names. Higher RPM tests generally showed higher fuel consumption, which is mechanically plausible.
- Surprises: the data are unusually clean for operational data. There are no nulls, no obvious coding artifacts, no date/time fields, and only minor tail values in temperature and humidity. The dominant feature on first pass was an extremely strong correlation between `engine_rpm` and fuel consumption (`r = 0.979`), which suggested the main analytical risk was underfitting a nonlinear mechanical curve.

## Key findings

### 1. Fuel consumption is driven primarily by a nonlinear RPM curve

**Hypothesis:** Fuel consumption rises with RPM, but not at a constant rate. The increase should accelerate at higher RPM.

**Test:** I compared a linear OLS model against a quadratic OLS model:

- Linear: `fuel_consumption_lph ~ engine_rpm + ambient_temp_c + humidity_pct + C(octane_rating) + vehicle_age_years`
- Quadratic: same model plus `engine_rpm^2`

**Result:** The quadratic term was overwhelmingly supported.

- Nested-model comparison: `F = 4882.5`, `p = 7.7e-288`
- Linear model AIC: `3497.7`
- Quadratic model AIC: `2164.2`
- Quadratic model `R^2 = 0.9955`, adjusted `R^2 = 0.9954`
- 5-fold CV performance:
  - Linear: mean `R^2 = 0.9557`, mean MAE = `3.87 L/h`
  - Quadratic: mean `R^2 = 0.9952`, mean MAE = `1.18 L/h`

The fitted curve in `plots/rpm_vs_fuel_quadratic.png` shows a clear upward bend rather than a straight line. Interpreting the fitted derivative, the expected increase in fuel consumption per additional 1,000 RPM grows substantially across the operating range:

- At 1,000 RPM: about `3.95 L/h` per +1,000 RPM
- At 3,000 RPM: about `11.99 L/h` per +1,000 RPM
- At 6,000 RPM: about `24.05 L/h` per +1,000 RPM

**Interpretation:** This dataset appears to reflect a strongly engineered mechanical relationship in which fuel use accelerates at higher engine speeds. For prediction or control, modeling RPM as linear would leave substantial and avoidable error.

### 2. Octane rating does not materially change fuel consumption after controlling for RPM and conditions

**Hypothesis:** Higher-octane fuel may reduce consumption, but any crude difference could be confounded by RPM or testing conditions.

**Test:** I examined octane effects after residualizing fuel consumption on RPM, temperature, humidity, and vehicle age, and also estimated octane coefficients inside the multivariable OLS models.

**Result:** There is no convincing octane effect in this dataset.

- Raw mean fuel consumption by octane:
  - 87: `29.03 L/h`
  - 89: `28.16 L/h`
  - 91: `28.09 L/h`
  - 93: `27.32 L/h`
- After controlling for the other variables, residual mean differences were all close to zero:
  - 87: `-0.07 L/h`
  - 89: `+0.09 L/h`
  - 91: `+0.31 L/h`
  - 93: `-0.32 L/h`
- ANOVA on residualized values across octane groups: `p = 0.656`
- In the quadratic OLS model, all octane coefficients had 95% confidence intervals spanning zero:
  - 89 vs 87: `0.14 L/h` (`95% CI -0.19 to 0.47`)
  - 91 vs 87: `-0.03 L/h` (`95% CI -0.36 to 0.29`)
  - 93 vs 87: `0.16 L/h` (`95% CI -0.17 to 0.48`)

The visual in `plots/octane_residual_boxplot.png` matches the statistics: the four octane groups overlap heavily, with no meaningful location shift.

**Interpretation:** Within this dataset, octane rating is not an important predictor of hourly fuel consumption once operating conditions are accounted for. Any practical effect, if present, is smaller than the residual variation left in the model.

### 3. Vehicle age does not meaningfully alter the RPM-consumption relationship

**Hypothesis:** Older vehicles might consume more fuel at the same RPM, or they might become less efficient specifically at high RPM.

**Test:** I fit an interaction model with `engine_rpm * vehicle_age_years` and checked age-stratified RPM curves.

**Result:** The age interaction was not supported.

- Interaction coefficient: `0.000011` with `p = 0.678`
- Main effect of vehicle age in the interaction model: `-0.040 L/h per year`, `p = 0.691`
- Adding the interaction slightly worsened AIC:
  - No interaction: `3497.7`
  - With interaction: `3499.6`

The age-binned curves in `plots/age_group_rpm_curves.png` are nearly indistinguishable across three age ranges:

- 0 to 5 years: 226 tests
- 6 to 10 years: 197 tests
- 11 to 14 years: 177 tests

**Interpretation:** In this sample, vehicle age contributes little independent information. Fuel consumption appears to be driven by current operating state far more than by broad asset age.

## Model diagnostics and quality checks

The main inferential model was the quadratic OLS specification. Diagnostics were favorable:

- Residual RMSE: `1.45 L/h`
- Breusch-Pagan test for heteroskedasticity: `p = 0.612`
- Jarque-Bera test for normality: `p = 0.534`

`plots/quadratic_model_diagnostics.png` shows residuals centered around zero with no strong funneling pattern, and the Q-Q plot is close to linear aside from mild tail deviation. That supports the main conclusion that a simple quadratic term captures most of the systematic structure in the data.

## What the findings mean

The practical message is narrow but strong:

- If the goal is to explain or predict fuel consumption, engine RPM dominates the problem.
- The relationship is nonlinear, so a straight-line approximation is materially worse than a quadratic specification.
- In this dataset, fuel octane, ambient temperature, humidity, and vehicle age add little once RPM is known.

This suggests the dataset was likely generated in a regime where the dominant mechanism is engine operating speed itself, with only modest noise around that curve. From an engineering or operational perspective, RPM management would matter far more than fuel grade choice or broad vehicle age category for reducing hourly fuel use in comparable tests.

## Limitations and self-assessment

This analysis is statistically strong for description, but it has clear limits:

- Correlation is not causation. The RPM relationship is mechanically plausible, but this dataset alone does not prove an intervention effect because the test design is unknown.
- I assumed rows are independent test runs. If repeated tests came from the same vehicles or engines, standard errors could be understated because there is no vehicle identifier for clustered modeling.
- The data are extremely clean and unusually well-behaved. That can happen in controlled experiments, but it also means the dataset may not reflect real operational messiness.
- I tested broad linear or quadratic effects for age, temperature, humidity, and octane. I did not exhaustively search for higher-order interactions among all variables, because the evidence already shows that RPM explains nearly all structure.
- The report is limited to the variables present. Important omitted drivers such as engine load, throttle position, displacement, route, or vehicle model could matter in real-world fuel use.

Alternative explanations considered:

- The apparent octane effect in raw means could have been due to confounding by operating conditions; residualization and multivariable modeling did not support a real independent octane effect.
- A simple linear RPM trend could have looked strong because RPM dominates the scale; explicit model comparison showed that the missing curvature was real and large, not cosmetic.
- Vehicle age could have mattered only at high RPM; the interaction test did not support that explanation.

Overall, the conclusions are well supported for this dataset: hourly fuel consumption follows a highly regular nonlinear RPM curve, while octane rating and vehicle age contribute little additional explanatory power.
