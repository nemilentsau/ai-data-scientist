# Analysis Report

## What this dataset is about

This appears to be a student-level dataset with 600 observations and 7 columns:

- `student_id`: unique identifier
- `weekly_study_hours`
- `gpa`
- `extracurriculars`
- `commute_minutes`
- `part_time_job_hours`
- `absences`

The values are internally plausible for a student dataset. There are no explicit missing values, all substantive columns are numeric, and the ranges are reasonable: study hours range from 0.0 to 26.0, GPA from 1.55 to 4.00, extracurricular count from 0 to 5, commute from 0 to 80 minutes, part-time work from 0.0 to 27.2 hours, and absences from 0 to 9. Raw row inspection did not reveal coding errors, date fields stored as strings, or hidden categorical codes.

The main caveat from orientation is that `student_id` is only an identifier and should not be treated as a predictor.

## Key findings

### 1. GPA shows a visible ceiling effect at 4.0

The GPA distribution is concentrated in the low-to-mid 3s, with a strong pile-up at the maximum possible value. Exactly 66 of 600 students have a perfect `4.0`, or 11.0% of the sample. This is visible in [plots/01_gpa_distribution.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/01_gpa_distribution.png).

This matters analytically because GPA is partly censored at the top end: students above 4.0 cannot be distinguished from one another. Any model using GPA as a continuous outcome will therefore understate variation among top performers.

### 2. The recorded workload and time-allocation variables have near-zero association with GPA

I tested the hypothesis that GPA would rise with study time and fall with work burden, commute, or absences. The data did not support that.

Pearson correlations with GPA were all near zero:

- `weekly_study_hours`: `r = -0.003`, `p = 0.942`
- `extracurriculars`: `r = -0.008`, `p = 0.854`
- `commute_minutes`: `r = 0.058`, `p = 0.154`
- `part_time_job_hours`: `r = 0.003`, `p = 0.947`
- `absences`: `r = -0.018`, `p = 0.667`

Spearman correlations told the same story, so the null result is not just a linearity issue.

The clearest example is study time: [plots/02_study_vs_gpa.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/02_study_vs_gpa.png) shows a broad cloud with no meaningful slope. The small wiggle in the LOWESS line is not supported by formal tests and is likely smoothing noise rather than a real effect.

### 3. After adjustment, effect sizes remain tiny and statistically indistinguishable from zero

I fit an OLS model:

`gpa ~ weekly_study_hours + extracurriculars + commute_minutes + part_time_job_hours + absences`

The model explained essentially none of the variance in GPA:

- `R^2 = 0.0037`
- adjusted `R^2 = -0.0047`
- overall model `p = 0.820`

Estimated effects were all extremely small, with confidence intervals crossing zero:

- `weekly_study_hours`: `-0.0005` GPA points per additional hour, 95% CI `[-0.0120, 0.0110]`
- `extracurriculars`: `-0.0019`, 95% CI `[-0.0292, 0.0253]`
- `commute_minutes`: `0.0023`, 95% CI `[-0.0009, 0.0055]`
- `part_time_job_hours`: `0.0001`, 95% CI `[-0.0085, 0.0087]`
- `absences`: `-0.0056`, 95% CI `[-0.0333, 0.0222]`

These estimates are visualized in [plots/03_ols_coefficients.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/03_ols_coefficients.png).

Substantively, this means that even if the point estimates were taken at face value, the implied changes in GPA are negligible.

### 4. The features are not just weak for linear models; they are weak for prediction in general

To test whether a more flexible model could recover non-linear structure, I compared out-of-fold predictions from:

- linear regression
- random forest regression

Using 5-fold cross-validation, both models failed to predict GPA usefully:

- linear regression out-of-fold `R^2 = -0.015`
- random forest out-of-fold `R^2 = -0.162`

Negative out-of-fold `R^2` means the models performed worse than simply predicting the sample mean GPA for everyone. This is shown in [plots/04_cv_predictions.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/04_cv_predictions.png), where predictions collapse toward the mean instead of tracking actual GPA.

I also tested whether the same features could at least identify students with a perfect `4.0`. They could not: a cross-validated logistic regression achieved mean ROC AUC `0.398`, which is worse than random ranking (`0.5`). The majority-class baseline accuracy is already `0.89` because only 11% of students have a perfect GPA.

## What the findings mean

Within this dataset, GPA is effectively independent of the measured student-burden variables. The most defensible interpretation is not that study time, work hours, commuting, and absences never matter in real life; it is that this dataset does not contain enough information about the true drivers of GPA to recover those relationships.

Possible explanations include:

- important omitted variables, such as prior achievement, course difficulty, socioeconomic context, school quality, or major
- measurement error in self-reported behaviors such as study hours and absences
- synthetic or partially randomized data generation, where plausible marginal distributions were created without preserving real dependence structure
- top-coding at `4.0`, which compresses differences among high-performing students

Practically, this means the dataset is not suitable for building a credible GPA prediction model from the available features alone. It is more useful as an example of why plausible-looking columns do not guarantee informative signal.

## Limitations and self-assessment

### Alternative explanations considered

I checked several alternatives before concluding that the signal is absent:

- nonlinearity: quadratic terms and interaction terms did not improve the GPA model materially
- monotonic but non-linear structure: Spearman correlations remained near zero
- model misspecification: random forest regression also failed out of sample
- threshold behavior at perfect GPA: logistic modeling for `gpa == 4.0` also failed

These checks reduce, but do not eliminate, the chance that a simple modeling choice hid a true relationship.

### Assumptions and caveats

- I treated each row as an independent student observation.
- I assumed the columns are measured consistently and on the scales implied by their names.
- I used standard regression on GPA despite the visible cap at `4.0`; this is acceptable for diagnosing weak signal, but a censored-outcome model would be more appropriate if the goal were fine-grained inference near the top end.
- I did not investigate subgroup effects such as whether study time matters only for students with long commutes or high job hours beyond a small number of interaction tests.

### What I did not investigate

- heterogeneity by latent student segments or clusters
- robust regression or censored models such as Tobit
- permutation tests for the random forest results
- whether the exact decimal structure of GPA and work-hour values suggests synthetic generation

### Bottom line

The strongest evidence in this dataset is negative evidence: the observed student workload variables do not explain GPA in any meaningful way. The report’s conclusions are therefore cautious by design. They are supported by both statistical tests and out-of-sample validation, but they should not be generalized beyond this dataset without richer covariates.
