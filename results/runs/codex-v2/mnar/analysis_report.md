# Dataset Analysis Report

## What this dataset appears to be

This is a 1,000-row respondent-level survey dataset with demographic variables (`age`, `gender`, `region`, `education_years`, `num_children`) plus two self-reported outcomes: `reported_annual_income` and `satisfaction_score`. The structure is simple: one row per respondent, no repeated measures, and mostly clean typing.

The main data quality issue is missing income. `reported_annual_income` is missing for 495 of 1,000 respondents (49.5%). All other columns are complete. Raw rows are internally consistent with the column names, and the values look survey-like rather than transactional: ages run from 18 to 80, education from 8 to 21 years, satisfaction is bounded from 1 to 10, and the number of children ranges from 0 to 4. Reported incomes are rounded and concentrated in plausible survey-style increments.

## Key findings

### 1. Reported income rises materially with education and age

**Hypothesis.** Higher education and older age should be associated with higher reported income.

**Evidence.**

- Among respondents who reported income (`n=505`), education and income had a moderate positive Spearman correlation: `rho = 0.361`, `p = 6.0e-17`.
- The plot `plots/income_vs_education.png` shows a clear upward trend in mean income as education rises. Mean income increases from about `$39.1k-$44.2k` at 9-10 years of education to about `$60.1k-$67.6k` at 18-21 years, though the extreme education levels have very small sample sizes.
- In a multivariable OLS model controlling for gender, region, and number of children, both age and education remained strong predictors (`R^2 = 0.210`):
  - Each additional year of education was associated with `+$1,473` in annual income (95% CI: `$985` to `$1,960`, `p < 0.001`).
  - Each additional year of age was associated with `+$272` in annual income (95% CI: `$174` to `$370`, `p < 0.001`).
  - Each additional child was associated with `-$948` in annual income (95% CI: `-$1,798` to `-$99`, `p = 0.029`).
- The coefficient plot `plots/income_model_coefficients.png` shows that education and age are the most stable positive effects in the model; most gender and region contrasts overlap zero.

**Interpretation.** In this sample, income differences are driven more by human-capital and lifecycle variables than by geography or binary gender contrasts. A practical effect size: four additional years of education corresponds to about `+$5.9k` in annual income, and ten additional years of age corresponds to about `+$2.7k`, holding the other modeled variables fixed.

### 2. Income nonresponse is not random enough to ignore

**Hypothesis.** Missing income might be systematic rather than random, which would make complete-case analyses potentially biased.

**Evidence.**

- Nearly half the sample did not report income (`49.5%` missing).
- Missingness differed by gender (`chi-square p = 0.033`), although the effect size was small (`Cramer's V = 0.083`).
- `plots/income_missing_by_gender.png` shows the pattern clearly:
  - `F`: `52.4%` missing
  - `M`: `47.8%` missing
  - `Other`: `32.5%` missing, with a wide uncertainty interval because `n=40`
- A logistic regression for income missingness found that higher age, more education, and higher satisfaction all predicted higher odds of missing income:
  - Age odds ratio `1.016` per year (95% CI: `1.003` to `1.028`, `p = 0.017`)
  - Education odds ratio `1.084` per year (95% CI: `1.017` to `1.156`, `p = 0.013`)
  - Satisfaction odds ratio `1.106` per point (95% CI: `1.035` to `1.181`, `p = 0.003`)
- Respondents with missing income were also more satisfied on average than those with observed income (`7.161` vs `6.794`, mean gap `0.367`, Welch t-test `p = 0.0028`).

**Interpretation.** The observed-income subset is unlikely to be a random half of the sample. Any conclusion involving income, especially the income-satisfaction relationship, should be read as “among respondents willing to report income” rather than as a clean statement about the full dataset.

### 3. Satisfaction is only weakly explained by the observed covariates

**Hypothesis.** Satisfaction might vary meaningfully by region, family size, or income.

**Evidence.**

- Satisfaction barely differed across regions: one-way ANOVA `p = 0.936`, with a tiny effect size (`Cohen's f = 0.029`).
- Satisfaction also barely differed across number of children: one-way ANOVA `p = 0.543`, `Cohen's f = 0.056`.
- In a multivariable OLS model on complete cases, the predictors explained only `4.2%` of the variance in satisfaction (`R^2 = 0.042`).
- Income had a positive coefficient, but the effect was modest: `2.585e-05` satisfaction points per dollar (`p = 0.001`), which is about `+0.259` satisfaction points per `$10,000`.
- Education had a small negative conditional association with satisfaction after controlling for income (`-0.094` points per education year, `p = 0.039`).
- `plots/satisfaction_vs_income.png` shows the pattern visually: a slight upward LOWESS trend, but with very large vertical spread at nearly all income levels.

**Interpretation.** Income is associated with somewhat higher satisfaction, but the relationship is weak in practical terms and dwarfed by unexplained variation. Region and family size add little. This dataset does not support a strong demographic story for satisfaction.

## What the findings mean

The strongest pattern in the data is socioeconomic rather than attitudinal: age and education track reported income in an expected way, while satisfaction is comparatively flat and noisy. If this were a real survey, the clearest business or policy implication would be that demographic variables are much more useful for segmenting income than for segmenting satisfaction.

The second important takeaway is methodological: the income field is not just sparse, it is selectively sparse. Because respondents with higher satisfaction, higher education, and higher age are somewhat more likely to omit income, any complete-case model using income is exposed to response bias. That does not invalidate the observed relationships, but it does lower confidence in their generalizability.

## Limitations and self-critique

- The dataset has no codebook, so the analysis assumes the obvious meanings of the columns and treats satisfaction as approximately interval-scaled.
- The income models only use the 505 observed incomes. I tested whether missingness was systematic and found that it was, but I did not attempt multiple imputation or explicit missing-data correction. That means the income-related results may be biased.
- The satisfaction model is statistically significant overall but has very low explanatory power. It would be a mistake to over-interpret the small coefficients as strong drivers of wellbeing.
- The education-satisfaction negative coefficient may reflect suppression or omitted variables rather than a genuine negative effect of education. I did not test richer causal structures.
- The highest education levels have very small sample counts (`n=2` at 21 years, `n=3` at 20 years), so the top end of `plots/income_vs_education.png` should be read as suggestive, not precise.
- I checked standard regression outputs and basic plot diagnostics, but I did not build nonlinear or interaction-heavy models. There may be subgroup patterns that a simple additive model misses.

## Files produced

- Report: `analysis_report.md`
- Plots:
  - `plots/income_missing_by_gender.png`
  - `plots/income_vs_education.png`
  - `plots/income_model_coefficients.png`
  - `plots/satisfaction_vs_income.png`
