# Student Academic Performance Analysis Report

## 1. Dataset Overview

The dataset contains **600 student records** with 7 variables:

| Variable | Type | Range | Mean | Std |
|---|---|---|---|---|
| student_id | Identifier | 1 -- 600 | 300.5 | 173.3 |
| weekly_study_hours | Continuous | 0.0 -- 26.0 | 11.5 | 4.1 |
| gpa | Continuous | 1.55 -- 4.00 | 3.14 | 0.58 |
| extracurriculars | Discrete (0--5) | 0 -- 5 | 2.5 | 1.7 |
| commute_minutes | Discrete | 0 -- 80 | 30.2 | 14.6 |
| part_time_job_hours | Continuous | 0.0 -- 27.2 | 8.2 | 5.5 |
| absences | Discrete | 0 -- 9 | 2.9 | 1.7 |

There are **zero missing values** in any column. GPA is left-skewed (skewness = -0.35) with a ceiling effect at 4.0, where 66 students (11.0%) sit at the maximum. Only 25 students (4.2%) fall below 2.0.

## 2. Key Findings

### Finding 1: No measured behavioral feature predicts GPA

The central finding of this analysis is a **null result**: none of the five behavioral variables -- study hours, extracurricular activities, commute time, part-time work, or absences -- have a meaningful relationship with GPA.

**Evidence:**

- All pairwise Pearson correlations between features and GPA are near zero (largest: commute_minutes, r = 0.058, p = 0.154). See `plots/03_correlation_heatmap.png`.
- LOWESS smoothers across all scatter plots are flat, ruling out masked non-linear relationships. See `plots/01_scatter_vs_gpa.png` and `plots/08_comprehensive_null_results.png`.
- Mean GPA is essentially identical across all levels of extracurriculars (range: 3.12 -- 3.18) and absences (range: 3.03 -- 3.22, excluding the single n=1 cell).
- Mutual information analysis confirms zero non-linear dependence for extracurriculars, commute, and absences with GPA.
- A composite "academic engagement" score (standardized study hours + extracurriculars - absences - job hours) also shows zero correlation with GPA (r = 0.002, p = 0.96).
- **Machine learning models fail completely**: Linear regression (CV R^2 = -0.03), Random Forest (CV R^2 = -0.05), and Gradient Boosting (CV R^2 = -0.19) all produce negative cross-validated R^2, meaning they perform worse than simply predicting the mean.
- Two-way ANOVA testing the interaction between study hours and extracurriculars finds no main effects and no interaction (all p > 0.7).
- K-means clustering (k=3) finds subgroups with identical GPA distributions (ANOVA F = 0.06, p = 0.94).

**This is not a power problem.** With n = 600, the study has 80% power to detect correlations as small as r = 0.057 (corresponding to a GPA difference of just 0.067 points). All observed feature-GPA correlations fall well below this threshold. See `plots/09_power_and_distributions.png` (left panel).

### Finding 2: Student ID is the only significant predictor of GPA

Unexpectedly, student_id -- which should be an arbitrary identifier -- shows a statistically significant and practically meaningful negative correlation with GPA (r = -0.201, p < 0.0001).

**The pattern is non-linear**: GPA peaks for students in the ID range 241--360 (mean GPA = 3.35) and drops sharply for IDs above 360, reaching a low around IDs 480--540 (mean GPA ~ 2.84). See `plots/06_student_id_effect.png`.

**Splitting the data at ID = 360:**
- ID 1--360: mean GPA = 3.27, 14.7% at 4.0, 9.7% below 2.5
- ID 361--600: mean GPA = 2.96, 5.0% at 4.0, 19.2% below 2.5
- Difference: **0.31 GPA points** (Cohen's d = 0.55, a medium effect)
- Kruskal-Wallis test across ID quintiles: H = 43.3, p < 0.000001

Post-hoc pairwise Mann-Whitney U tests (Bonferroni-corrected) confirm that the bottom two quintiles (ID 361--600) differ significantly from the middle quintiles (ID 241--360), but the top two quintiles (ID 1--240) do not differ from the middle. See `plots/02_student_id_vs_gpa.png`.

Even with student_id included, the best OLS model explains only R^2 = 0.071 of GPA variance (binary ID split). The ID effect is real but accounts for a small fraction of total variability.

### Finding 3: A suggestive but fragile subgroup effect for extracurriculars

Within the high-ID group (ID > 360), there is a negative correlation between extracurricular participation and GPA (r = -0.156, p = 0.016). Students with 5 extracurriculars average GPA = 2.84, compared to 3.06 for students with 0. In the low-ID group, the trend reverses weakly (r = +0.094, p = 0.076). See `plots/07_extracurriculars_by_group.png`.

**Caveats on this finding:**
- The p = 0.016 does not survive Bonferroni correction for 10 subgroup tests (threshold = 0.005).
- However, the bootstrap 95% CI for the high-ID correlation excludes zero: [-0.27, -0.04], with only 0.5% of 10,000 bootstrap samples showing r > 0.
- This is a post-hoc, data-dredged finding and should be treated as hypothesis-generating, not confirmatory.

### Finding 4: Strong evidence of synthetic data generation

The features display distributional properties characteristic of synthetic/simulated data:

| Variable | Best-fit distribution | Goodness-of-fit p-value |
|---|---|---|
| weekly_study_hours | Normal | 0.91 |
| extracurriculars | Discrete uniform (0--5) | 0.65 |
| absences | Poisson (lambda = 2.9) | 0.98 |
| part_time_job_hours | Right-skewed (exponential-like) | -- |
| commute_minutes | Peaked/normal-like | -- |

See `plots/09_power_and_distributions.png` (right panel) and `plots/05_feature_distributions.png`.

The absences data fits a Poisson(2.9) distribution almost exactly (chi^2 = 1.93, p = 0.98), and extracurriculars is nearly perfectly uniform across 0--5 (chi^2 = 3.30, p = 0.65). Combined with (a) zero missing data, (b) perfect mutual independence between all features, and (c) the complete absence of any feature-GPA relationship, this strongly suggests the data was generated by sampling each feature independently from known distributions, with GPA generated separately (possibly as a function of student_id plus noise).

## 3. Interpretation

### What the data shows

This dataset demonstrates that **common behavioral proxies for academic effort do not predict GPA** -- at least in this sample. A student who studies 26 hours per week has no better GPA, on average, than one who studies 0 hours. A student with 9 absences performs similarly to one with perfect attendance. This is true regardless of how the features are combined, transformed, or modeled.

The only meaningful signal is the student_id effect, which likely encodes an unmeasured grouping variable (e.g., cohort, program, department, or admission wave). This hidden variable explains about 7% of GPA variance, while all measured behavioral features explain 0%.

### Practical implications

If this data represents a real educational setting, it would suggest that:

1. **Study time alone does not determine grades.** Quality of study, prior preparation, course difficulty, and instructor effects may matter far more than raw hours.
2. **An unmeasured factor associated with student ID ordering is the dominant predictor.** Identifying what this represents (e.g., different academic programs, admission cohorts, or grading standards) would be the most productive next step.
3. **Extracurricular activity may have context-dependent effects** -- potentially beneficial in some programs and detrimental in others -- though this finding requires replication.

## 4. Limitations and Self-Critique

### What we tested and can be confident about
- The null result is robust: we tested linear, non-linear (LOWESS, Random Forest, Gradient Boosting), and interaction effects. We checked for ceiling effects, subgroups via clustering, and composite variables. With n = 600, we had adequate power to detect small effects (r > 0.057).

### What we cannot rule out
- **Omitted variable bias**: The most important predictors of GPA (course difficulty, prior academic preparation, instructor, cognitive ability, motivation) are not in this dataset. The behavioral variables may predict GPA only after conditioning on these factors.
- **Measurement issues**: Self-reported study hours are notoriously unreliable. If the measures are noisy, true correlations would be attenuated toward zero.
- **Restricted range**: All students are from a single institution (presumably), and the GPA range is truncated at 4.0. If the sample is relatively homogeneous, real effects could be too small to detect.
- **Synthetic data**: The distributional evidence strongly suggests this dataset was artificially generated with independent features and no feature-GPA relationship built in. The student_id-GPA relationship may have been the only deliberately encoded signal.

### What we did not investigate
- Temporal patterns (if student_id represents enrollment order, trends over time)
- Causal inference methods (propensity score matching, instrumental variables)
- Grade distributions within specific courses vs. overall GPA

## 5. Summary of Plots

| File | Description |
|---|---|
| `plots/01_scatter_vs_gpa.png` | Scatter plots of each feature vs. GPA with LOWESS smoothers |
| `plots/02_student_id_vs_gpa.png` | Detailed analysis of the student ID -- GPA relationship |
| `plots/03_correlation_heatmap.png` | Pearson correlation matrix showing near-zero correlations |
| `plots/04_gpa_distribution.png` | GPA histogram and Q-Q plot |
| `plots/05_feature_distributions.png` | Distributions of all six variables |
| `plots/06_student_id_effect.png` | Four-panel analysis of the student ID effect |
| `plots/07_extracurriculars_by_group.png` | Extracurriculars -- GPA relationship split by ID group |
| `plots/08_comprehensive_null_results.png` | Summary of all feature -- GPA relationships |
| `plots/09_power_and_distributions.png` | Statistical power analysis and distribution fitting |
