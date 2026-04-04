# Analysis Report

## What this dataset is about

This dataset contains 1,200 hospital patient records with one row per patient. The fields are:

- `patient_id`: unique identifier
- `department`: `Cardiology`, `Neurology`, or `Orthopedics`
- `age`
- `severity_index`: a numeric illness severity measure
- `treatment`: `A` or `B`
- `length_of_stay_days`
- `recovery_score`
- `readmitted`: binary indicator

The data is unusually clean: there are no nulls, no obvious type issues, and all departments have exactly 400 patients. `patient_id` is unique and behaves like a pure identifier rather than an analytic feature. The overall averages are age 54.5 years, severity 5.01, stay length 13.8 days, recovery score 67.5, and readmission rate 10.8%.

## Key findings

### 1. Severity is the dominant clinical signal in the dataset

Severity is strongly associated with both utilization and outcome:

- Severity vs. length of stay: Pearson `r = 0.853` (`p < 1e-300`)
- Severity vs. recovery score: Pearson `r = -0.658` (`p = 9.3e-150`)

This pattern is visible in [plots/severity_relationships.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.dsEFIS56SS/plots/severity_relationships.png). Higher-severity patients stay longer and recover less well.

Department averages line up with the same story:

- Cardiology: severity 3.03, stay 10.48 days, recovery 71.94
- Neurology: severity 5.03, stay 13.74 days, recovery 67.13
- Orthopedics: severity 6.98, stay 17.20 days, recovery 63.32

Interpretation: most of the variation in patient outcomes appears to reflect case mix. Any treatment comparison that ignores severity is likely to be biased.

### 2. The raw treatment comparison is misleading because treatment assignment is heavily confounded

At first glance, treatment `B` appears better:

- Mean recovery under `A`: 66.29
- Mean recovery under `B`: 68.53

But treatment assignment is far from balanced across departments, as shown in [plots/department_treatment_imbalance.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.dsEFIS56SS/plots/department_treatment_imbalance.png):

- Cardiology: 8% `A`, 92% `B`
- Neurology: 46% `A`, 55% `B`
- Orthopedics: 89% `A`, 11% `B`

The department-treatment association is extremely strong (`chi^2 = 523.9`, `p = 1.7e-114`, Cramer's `V = 0.661`). Since departments also differ sharply in severity, the raw treatment average mixes treatment effect with case mix.

Once the comparison is made within department, treatment `A` is better everywhere, shown in [plots/treatment_recovery_reversal.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.dsEFIS56SS/plots/treatment_recovery_reversal.png):

- Cardiology: `A - B = +5.10` recovery points (`p = 2.1e-5`)
- Neurology: `A - B = +4.19` recovery points (`p = 5.4e-12`)
- Orthopedics: `A - B = +3.76` recovery points (`p = 3.7e-5`)

An adjusted linear model confirms the reversal:

`recovery_score ~ treatment + department + severity_index + age + length_of_stay_days`

- Treatment `B` coefficient: `-4.00` points relative to `A`
- 95% CI: `[-4.78, -3.23]`
- Model `R^2 = 0.497`

Severity remains the strongest adjusted predictor in the same model:

- Severity coefficient: `-2.86` recovery points per 1-point severity increase
- 95% CI: `[-3.30, -2.42]`

Interpretation: the naive conclusion that treatment `B` is superior is wrong. The data show a Simpson's paradox pattern driven by non-random treatment allocation across departments and severity levels. On an adjusted basis, treatment `A` is associated with better recovery.

### 3. Readmission has only a weak signal in the measured variables

Readmission is rare enough to be a low-signal target here: 130 of 1,200 patients were readmitted (10.8%). Rates are almost identical by department:

- Cardiology: 11.0%
- Neurology: 10.8%
- Orthopedics: 10.8%

Treatment differences are also small in raw terms:

- `A`: 9.6%
- `B`: 11.9%

The clearest readmission pattern is age. In the adjusted logistic model,

`readmitted ~ treatment + department + severity_index + age + length_of_stay_days + recovery_score`

- Age odds ratio: `1.042` per year
- 95% CI: `[1.006, 1.079]`
- `p = 0.022`

That effect is modest but directionally consistent with [plots/readmission_signal.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.dsEFIS56SS/plots/readmission_signal.png): readmission rises from 8.3% in the youngest age quartile to 13.4% in the oldest.

However, the overall readmission model is weak:

- Logistic likelihood-ratio test: `p = 0.138`
- Cross-validated ROC AUC: `0.556`
- Cross-validated average precision: `0.130` versus a base rate of `0.108`

Interpretation: the observed patient and treatment variables explain recovery reasonably well, but they do not explain readmission well. Important readmission drivers are likely missing from the dataset.

## What the findings mean

This looks like a structured hospital outcomes dataset where case severity is the main driver of both patient trajectory and recovery. The most decision-relevant result is that treatment comparisons are unsafe unless they adjust for case mix. If a stakeholder looked only at the overall treatment averages, they would choose the wrong treatment.

Practically, the data support two conclusions:

- Recovery analysis should always adjust for severity, and probably department as well.
- Readmission should not be treated as well-explained by the current fields; more features would be needed for reliable prediction or operational targeting.

## Limitations and self-critique

- The strongest limitation is confounding by indication. Treatment assignment is clearly non-random, so the adjusted treatment result is still associative, not causal.
- Department and severity are tightly linked, and treatment is also highly imbalanced across departments. That makes the treatment effect direction fairly consistent, but it still reduces how confidently the effect can be interpreted as a true causal advantage.
- I did not have information on comorbidities, discharge disposition, prior admissions, medications, insurance, or follow-up quality. Any of these could materially affect readmission.
- The outcome window for `readmitted` is not defined. A 7-day, 30-day, and 90-day readmission label would imply different mechanisms.
- Length of stay may be partly downstream of severity and treatment rather than a pure baseline covariate, so its coefficient in adjusted models should not be given a causal interpretation.
- The dataset appears synthetic or highly curated: perfect completeness, clean categories, and very regular group sizes are atypical in operational healthcare data. That does not invalidate the relationships, but it limits how much real-world messiness is represented.

## Bottom line

The dataset is primarily about hospital severity, recovery, and treatment allocation. Severity strongly predicts longer stays and worse recovery. The headline treatment comparison reverses after adjustment because treatment assignment is heavily confounded by department and severity; within comparable groups, treatment `A` is associated with about 4 more recovery points than `B`. Readmission is only weakly explained by the available variables, with age providing the only modest adjusted signal.
