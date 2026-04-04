# Analysis Report

## Dataset overview
This dataset contains 800 companies and 8 columns describing startup characteristics and funding outcomes. Each row appears to represent one company-round snapshot with a unique `company_id`, categorical descriptors for `sector` and `round_type`, and numeric measures of company scale (`employees`), maturity (`years_since_founding`), traction (`revenue_growth_pct`), investor count (`num_investors`), and outcome (`funding_amount_usd`).

The table is unusually clean: there are no explicit missing values, category levels are balanced enough for comparison (`sector` ranges from 124 to 143 rows; `round_type` ranges from 102 to 324), and numeric columns have plausible ranges. A few structural features matter for interpretation:

- `funding_amount_usd` is highly right-skewed (median $118,934, mean $168,083, max $1,633,984; see `plots/01_funding_distribution.png`).
- The other numeric predictors are close to symmetric, which makes the skew in funding the main modeling issue.
- `sector` has 6 labels and `round_type` has 4 labels with `Seed` the largest group (324 rows).

Because of the skew, most inferential work below uses `log(funding_amount_usd)` rather than raw dollars.

## Key findings

### 1. Funding is driven much more by company maturity and traction than by sector label
**Hypothesis.** Older, larger, faster-growing companies raise more capital, regardless of sector.

**Test.** I fit an OLS model on `log(funding_amount_usd)` with `round_type`, `sector`, `employees`, `years_since_founding`, `revenue_growth_pct`, and `num_investors`. I also checked 5-fold cross-validated predictive performance and residual diagnostics.

**Result.** The hypothesis is strongly supported.

- The full model explains about half the variance in log funding: R^2 = 0.513, adjusted R^2 = 0.505; 5-fold CV R^2 = 0.488.
- Holding other variables constant, each additional year since founding is associated with about **10.4%** more funding.
- Every additional 100 employees is associated with about **32.0%** more funding.
- Every extra 10 percentage points of revenue growth is associated with about **4.9%** more funding.
- Diagnostics are acceptable for a simple linear model after log-transforming the target: residuals show no major structure and the Q-Q plot is reasonably straight (`plots/05_model_diagnostics.png`).

**Interpretation.** In this dataset, capital raised looks primarily like a function of company maturity and operating momentum rather than sector branding. The smooth relationships in `plots/03_numeric_relationships.png` reinforce that the signal is monotonic rather than being driven by a few outliers.

### 2. Round stage matters, but the effect is smaller than the raw boxplots suggest once maturity is controlled for
**Hypothesis.** Later rounds raise more money than earlier rounds.

**Test.** I compared raw funding distributions by `round_type` and then estimated adjusted round effects in the multivariable log-funding model.

**Result.** The hypothesis is supported, but mostly for the latest stage.

- Median funding rises from **$110,934** in Seed to **$150,396** in Series C (`plots/02_funding_by_round.png`).
- Raw means also increase: Seed $154,566, Series A $161,239, Series B $181,262, Series C $205,690.
- After adjusting for size, age, growth, investor count, and sector, only `Series_C` remains clearly above Seed: coefficient 0.167 log points (95% CI 0.031 to 0.304), which is about **18.2%** higher funding than a comparable Seed company.
- `Series_A` and `Series_B` are not clearly different from Seed after adjustment at conventional levels.

**Interpretation.** Later rounds do raise more in raw dollars, but much of that difference appears to be explained by the fact that later-stage firms are also older, larger, and further along operationally. Stage is therefore partly a summary label for maturity rather than an independent funding driver.

### 3. Sector is largely noise here, and more investors is not a sign of larger rounds
**Hypothesis.** Sector differences will disappear after controlling for company fundamentals; investor count may even proxy for fragmented financing rather than round size.

**Test.** I compared a base log-funding model without sector to a full model with sector, and examined the coefficient plot for adjusted effects.

**Result.** The hypothesis is supported.

- Adding sector to the model barely changes fit: base R^2 = 0.512 vs full R^2 = 0.513.
- A nested-model ANOVA finds no evidence that sector improves explanation once the other variables are included (p = 0.981).
- The sector block contributes only about **0.09%** partial R^2 on top of the base model, effectively negligible in this sample.
- Every sector coefficient confidence interval crosses zero in `plots/04_adjusted_effects.png`.
- `num_investors` is slightly negative in the adjusted model: coefficient -0.017 log points per investor (95% CI -0.031 to -0.004), about **-1.7%** less funding per additional investor holding the other variables fixed.

**Interpretation.** Sector-level narratives are not doing much work in this dataset. The negative investor-count coefficient is small, but it suggests that for otherwise similar companies, needing more investors may reflect smaller average check sizes or less concentrated conviction. This is an associational result, not a causal one.

## What these findings mean
Taken together, the dataset describes a funding environment where investors respond mostly to evidence of maturity and traction. A practical implication is that benchmarking funding expectations by sector alone would be weakly informative here. A better benchmark would condition on company age, headcount, growth, and stage simultaneously.

The results also warn against reading raw round-stage differences too literally. Stage and company maturity move together, so unadjusted comparisons overstate how much stage alone matters.

## Limitations and self-critique
- This appears to be a clean, possibly simulated dataset. Real startup data usually has missingness, reporting lag, censoring, and noisier categorical labels. That means effect sizes may look more stable here than they would in production data.
- The analysis is observational. None of the coefficients should be read causally. For example, high revenue growth may attract capital, but capital can also help create growth.
- I assumed one row per independent company-round observation. If the data actually contains repeated measurements from the same firms over time, standard errors would be understated.
- I did not test nonlinear models beyond LOWESS visual checks. The monotonic patterns look approximately linear on the log scale, but there could still be thresholds or interactions that this model misses.
- The small negative investor-count effect is statistically detectable but modest. Alternative explanations include omitted variables such as geography, lead-investor quality, or round structure.
- The model leaves roughly half the variance unexplained, so there are clearly funding drivers not captured in the available columns.

## Files referenced
- `plots/01_funding_distribution.png`
- `plots/02_funding_by_round.png`
- `plots/03_numeric_relationships.png`
- `plots/04_adjusted_effects.png`
- `plots/05_model_diagnostics.png`
