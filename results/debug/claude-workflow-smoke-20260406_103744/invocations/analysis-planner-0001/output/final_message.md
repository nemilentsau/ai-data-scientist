All three artifacts are written:

- **`analysis_plan.md`** — 5 phases (distribution checks, bivariate analysis, multicollinearity, predictive modelling, multiple-testing robustness) with 16 concrete checks, each tied to specific plots or validation outputs.

- **`hypotheses.json`** — 6 hypotheses (H-01 through H-06) designed around the core expectation that this is pure noise data: no significant correlations after correction, no predictive power in OLS or random-forest, normal target distribution, and no multicollinearity.

- **`experiment_plan.json`** — 7 experiments (EXP-01 through EXP-07) with stable IDs, explicit input/output artifact paths, priority ordering, and cross-references to the hypotheses and checks they address.

The plan is deliberately structured to first confirm the noise nature of the dataset (the "null result is the finding") and to guard against false positives via Bonferroni/BH corrections and bootstrap confidence intervals.