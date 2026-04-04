# Analysis Report

## What this dataset appears to be about
This dataset contains 44 observations from what looks like a small laboratory dose-response study. Each row records an `observation_id`, `batch`, administered `dosage_mg`, measured `response`, `lab_temp_c`, `technician`, and subject `weight_kg`.

Key orientation facts:
- Shape: 44 rows x 7 columns.
- No missing values were present.
- `batch` has 4 levels with exactly 11 rows each; `technician` has 3 levels.
- `dosage_mg` ranges from 4 to 19 mg, `response` from 3.10 to 12.74, `lab_temp_c` from 20.7 to 23.3 C, and `weight_kg` from 48.8 to 89.0 kg.
- Each batch has the same mean dosage (9.0 mg) and nearly identical mean response (about 7.50) and response SD (about 2.03).

That last point turned out to be the central feature of the dataset.

## Key findings

### 1. Batch-level summary statistics are almost identical, but the underlying shapes are not
Hypothesis: if the batches are truly comparable, then not only their means and correlations but also their point patterns should look similar.

Result: the summaries are nearly identical across all four batches, but the raw scatterplots are qualitatively different. In every batch, the dosage-response correlation is about 0.816 and the fitted slope is about 0.500, yet [batch_scatter.png](./plots/batch_scatter.png) shows four distinct geometries:
- `batch_Q1` is roughly linear but moderately noisy.
- `batch_Q2` is curved, so a linear fit is an oversimplification.
- `batch_Q3` is almost perfectly linear except for one large outlier (`observation_id` 25).
- `batch_Q4` has almost no dosage variation for 10 of 11 points; the apparent slope is created largely by one high-dosage leverage point (`observation_id` 41 at 19 mg).

Evidence:
- Overall model: `response ~ dosage_mg` estimated a slope of 0.500 response units per mg (95% CI 0.390 to 0.610, p=1.44e-11).
- Batch means are statistically indistinguishable by ANOVA (p=1.000000), which would wrongly suggest the batches are interchangeable.
- Batch-by-dosage interaction terms are near zero in a linear model, but that is misleading because the problem is geometry, not average slope alone.

Interpretation: a report that only gave means, standard deviations, correlations, or a single pooled regression line would miss the real structure of the data. Visualization changes the conclusion.

### 2. Two batches are heavily shaped by single influential observations
Hypothesis: if the apparent linear relationships are genuine within each batch, then removing the most influential point in each batch should not radically change the fit.

Result: this hypothesis failed for the most suspicious batches. The influence diagnostic in [influence_diagnostic.png](./plots/influence_diagnostic.png) shows that a small number of observations exert disproportionate pull on the fitted models.

Most influential cases by Cook's distance:
- batch_Q1: obs 3 had Cook's distance 0.489; slope changed from 0.500 to 0.592 when removed, and R^2 changed from 0.667 to 0.784.
- batch_Q2: obs 17 had Cook's distance 0.808; slope changed from 0.500 to 0.627 when removed, and R^2 changed from 0.666 to 0.793.
- batch_Q3: obs 25 had Cook's distance 1.393; slope changed from 0.500 to 0.345 when removed, and R^2 changed from 0.666 to 1.000.
- batch_Q4: obs 37 had Cook's distance 0.137; slope changed from 0.500 to 0.518 when removed, and R^2 changed from 0.667 to 0.746.

The strongest example is `batch_Q3`: removing obs 25 changes the story from a noisy linear pattern (R^2=0.666) to a perfect line (R^2=1.000). `batch_Q4` is the opposite problem: the fit looks linear mostly because of one leverage point at 19 mg while the other ten observations are all at 8 mg.

Interpretation: the common slope of about 0.5 is not equally trustworthy across batches. In at least two batches, the fitted relationship is fragile and observation-dependent.

### 3. After accounting for dosage and batch, there is no strong evidence that technician, temperature, or weight matter
Hypothesis: differences in technician handling, lab temperature, or subject weight might explain response variation beyond dosage.

Test: I fit `response ~ dosage_mg + C(batch) + C(technician) + lab_temp_c + weight_kg` and inspected coefficient estimates with confidence intervals.

Result: dosage remains the only clearly supported predictor. The coefficient plot in [adjusted_coefficients.png](./plots/adjusted_coefficients.png) shows:
- Dosage: 0.472 per mg (95% CI 0.352 to 0.592, p=2.08e-09).
- Technician Kim vs Alex: 0.689 (95% CI -0.216 to 1.594, p=0.131).
- Technician Pat vs Alex: 0.392 (95% CI -0.540 to 1.325, p=0.399).
- Lab temperature: -0.470 per C (95% CI -1.221 to 0.281, p=0.212).
- Weight: -0.0045 per kg (95% CI -0.0386 to 0.0296, p=0.792).

Even the raw technician mean differences were not statistically convincing (one-way ANOVA p=0.288); Kim had the highest raw mean response (8.119) but also the widest variability.

Interpretation: there is no strong evidence here that technician, temperature, or weight are driving the outcome. The dominant signal is dosage, but that signal itself must be interpreted batch-by-batch because of the structural issues above.

## Practical meaning
If this were a real experiment, the main operational lesson would be caution rather than optimization. A naive pooled analysis would conclude that increasing dosage raises response by about 0.5 units per mg and that batch does not matter. That conclusion is incomplete. The pooled slope exists, but its credibility varies sharply by batch because some batches reflect curvature, outliers, or leverage rather than stable within-batch linear behavior.

In practice, I would not use this dataset to justify a single global linear dose-response rule without first resolving why the batch geometries differ so much. The next step would be to inspect the experimental process behind batches Q2 through Q4, especially obs 25 and obs 41, and verify whether those are measurement issues, real rare events, or intentionally different regimes.

## Limitations and self-critique
- Small sample: only 44 observations total and 11 per batch, so inference is sensitive to single points.
- Non-random structure: the batches appear intentionally constructed rather than naturally sampled, which limits external validity.
- Model assumptions are shaky within some batches because linearity is visibly violated (`batch_Q2`) or depends on influential points (`batch_Q3`, `batch_Q4`).
- I treated observations as independent and did not model any repeated-measures or hierarchical structure because none was explicit in the data.
- Alternative explanation: apparent batch differences could reflect undocumented protocol changes or data-generation artifacts rather than biological differences.
- I did not attempt nonlinear dose-response models because the dataset is too small for that to be stable, and the stronger issue was first-order data geometry rather than predictive performance.

## Bottom line
The dataset looks like a dose-response study, but its main lesson is methodological: identical summary statistics can conceal radically different underlying patterns. The dose-response effect is real in the pooled data, yet some batch-level relationships are fragile, nonlinear, or driven by single observations. Any substantive conclusion should therefore be based on the raw plots, not on aggregate metrics alone.
