All three artifacts are written:

- **`analysis_plan.md`** -- 7-stage plan covering distributions, bivariate associations, multicollinearity, predictive modelling (with permutation test), salary-band classification, clustering, and FDR correction. Includes a decision framework for interpreting results.

- **`hypotheses.json`** -- 9 hypotheses (H-01 through H-09), each with null/alternative statements, test methods, significance levels, and links to specific experiments and framing checks. The final hypothesis (H-09) is a meta-test: whether *any* result survives multiple-comparison correction.

- **`experiment_plan.json`** -- 11 experiments (EXP-01 through EXP-11) with step-by-step methods, required libraries, expected output artifacts (plots + tables), validation checks, and dependency chains. EXP-11 depends on all p-value-producing experiments.

Key design choices given the framing risks:
- **Permutation test** (EXP-08) is the cornerstone -- it directly tests whether model R^2 exceeds what random noise would produce.
- **FDR correction** (EXP-11) aggregates all p-values to guard against spurious findings from multiple testing.
- **Validation checkpoints** are tied to profile statistics (mean ~50, std ~10, 800 rows) so the analysis stage can verify data integrity before drawing conclusions.