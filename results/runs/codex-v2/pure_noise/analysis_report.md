# Analysis Report

## What this dataset is about

`dataset.csv` contains 800 employee-level records with 10 columns covering experience, training, team context, project output, satisfaction, commute time, salary band, remote-work share, and a `performance_rating` target. The table is unusually clean: there are no missing values, no duplicate employee IDs, and the categorical fields are tightly coded (`salary_band` has 5 levels and `remote_pct` is restricted to 0, 25, 50, 75, and 100).

The values are plausible for HR data, but the structure is atypical. Category counts are almost perfectly balanced, and most pairwise correlations are close to zero. That made the main analytical question less about which variable dominates and more about whether the expected HR relationships exist at all.

## Key findings

### 1. Salary band is not aligned with experience in this sample

If `salary_band` encodes seniority, employees in higher bands should show materially more experience. The data do not support that.

- Mean experience ranges only from 14.33 years in `L4` to 15.44 years in `L3`.
- One-way ANOVA for `years_experience ~ salary_band`: F = 0.486, p = 0.746.
- Kruskal-Wallis test: H = 1.894, p = 0.755.
- Visual evidence in `plots/salary_band_vs_experience.png` shows near-complete overlap between bands.

Interpretation: within this dataset, salary labels do not behave like a pay-grade ladder tied to tenure. Either salary band is driven by omitted variables, or the labels are not ordered in the way the names imply.

### 2. Remote work is not strongly linked to either commute or satisfaction

A natural expectation is that more remote work should clearly reduce commute and possibly improve satisfaction. The commute effect is directionally negative but weak, and satisfaction is essentially flat.

- Average commute falls from 27.96 minutes at 0% remote to 23.17 minutes at 100% remote, but the relationship is not monotonic.
- Spearman correlation between `remote_pct` and `commute_minutes`: rho = -0.049, p = 0.166.
- Mean satisfaction stays in a narrow band from 5.49 to 5.74 across all remote-work groups.
- One-way ANOVA for `satisfaction_score ~ remote_pct`: F = 0.215, p = 0.930.
- `plots/remote_work_outcomes.png` makes both patterns visible: small commute differences, almost no satisfaction separation.

Interpretation: remote-work share does not explain much variation in employee sentiment here. The small commute reduction is real descriptively, but it is too noisy to support a stronger claim.

### 3. Larger teams are associated with slightly lower performance, but the effect is modest

The clearest relationship in the table is a weak negative association between `team_size` and `performance_rating`.

- In a multivariable OLS model controlling for training, projects completed, experience, satisfaction, commute, remote share, and salary band, the `team_size` coefficient is -0.129 rating points per additional teammate.
- 95% confidence interval: [-0.237, -0.020], p = 0.020.
- That implies roughly a 2.7-point lower expected rating when comparing a 24-person team with a 3-person team, holding other modeled variables constant.
- `plots/team_size_vs_performance.png` shows the trend, but also shows how noisy it is at the individual level.

Interpretation: bigger teams may create coordination drag or dilute individual visibility, but the practical effect is small relative to the target's standard deviation of 10.02. This is a weak structural signal, not a dominant driver.

### 4. The available features do not predict performance well

To test whether performance depends on a more complex combination of variables, I fit a regularized regression model and evaluated it with 5-fold cross-validation.

- Ridge regression mean cross-validated R² = -0.019 (SD 0.019).
- Mean cross-validated RMSE = 10.055.
- RMSE is effectively the same scale as the target's own standard deviation (10.017), which means the model performs little better than predicting the overall mean every time.
- `plots/performance_cv_predictions.png` shows predictions compressed toward the center rather than tracking actual scores.

Interpretation: whatever drives `performance_rating` is mostly absent from this table, or the target was generated largely independently of the listed features.

## What the findings mean

This dataset looks like employee data on the surface, but it does not behave like a typical observational HR dataset. Key administrative variables such as salary band, remote share, and performance are largely disconnected from the covariates that would normally explain them. That has two practical implications:

- Strong policy claims would be unsafe. For example, the data do not support saying that remote work improves satisfaction or that salary band reflects tenure.
- Predictive modeling is not warranted for performance with the current feature set. Better predictors would likely need manager effects, job family, role level, promotion history, tenure in role, or prior review history.

## Limitations and self-critique

- This is observational, cross-sectional data, so even the team-size result is associative rather than causal.
- I treated `salary_band` as a meaningful label because the names suggest order, but the analysis itself shows that assumption may be wrong.
- The weak effects could reflect synthetic or deliberately decorrelated data rather than a real workplace process. The unusually balanced categories and near-zero correlation matrix support that possibility.
- I did not test interaction-heavy models beyond a baseline linear predictor because the cross-validated linear model already showed almost no recoverable signal. A more flexible model might squeeze out slightly better fit, but it would not change the main conclusion that signal is sparse.
- The report emphasizes effect sizes as well as p-values because several plausible relationships are not just statistically non-significant; they are substantively tiny.

## Appendix: key summary tables

### Experience by salary band

| index | mean | median | std | count |
| --- | --- | --- | --- | --- |
| L1 | 15.37 | 15.2 | 9.1 | 163.0 |
| L2 | 14.77 | 14.9 | 8.87 | 144.0 |
| L3 | 15.44 | 16.3 | 8.49 | 163.0 |
| L4 | 14.33 | 14.5 | 8.5 | 160.0 |
| L5 | 14.62 | 14.95 | 9.1 | 170.0 |

### Remote-work outcomes by remote share

| index | commute_minutes mean | commute_minutes median | satisfaction_score mean | satisfaction_score median |
| --- | --- | --- | --- | --- |
| 0 | 27.96 | 21.0 | 5.58 | 5.59 |
| 25 | 23.24 | 16.0 | 5.74 | 5.61 |
| 50 | 25.81 | 16.0 | 5.64 | 5.73 |
| 75 | 22.5 | 15.0 | 5.62 | 5.51 |
| 100 | 23.17 | 16.0 | 5.49 | 5.63 |
