All three artifacts are written:

- **`analysis_plan.md`** — 7-step plan covering distribution checks, correlations, non-linear scans (MI), ANOVA on salary bands, VIF multicollinearity, RF model fit, and a permutation noise test. Each step maps to a framing `required_check`.
- **`hypotheses.json`** — 5 null hypotheses (H-CORR-NONE, H-NONLIN-NONE, H-SALARY-NODIFF, H-MODEL-NOSIGNAL, H-NOISE) with explicit thresholds and linked experiment IDs.
- **`experiment_plan.json`** — 7 experiments (EXP-DIST through EXP-NOISE) specifying inputs, outputs (plot/table paths), methods, and validation criteria.

The plan is designed to rigorously detect the absence of signal — the framing warns this may be pure noise, so the final permutation test (EXP-NOISE) serves as the definitive confirmation. Every required check from `framing.json` is covered by at least one experiment.