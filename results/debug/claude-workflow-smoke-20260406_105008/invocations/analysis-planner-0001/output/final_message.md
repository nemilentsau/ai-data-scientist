All three artifacts are written:

- **`analysis_plan.md`** — 4 experiments covering all 5 required checks, with an experiment-to-check mapping table and framing risk mitigations.
- **`hypotheses.json`** — 5 null hypotheses (H-01 through H-05), each linked to specific required checks and experiments.
- **`experiment_plan.json`** — 4 experiment specifications (EXP-01 through EXP-04) with steps, inputs, outputs, and expected results.

**Design rationale:**
- **EXP-01** handles two checks (correlations + distribution) in a single pass over the data.
- **EXP-02** isolates the salary band ordinal-proxy question.
- **EXP-03** computes VIF and predictor correlation heatmap for multicollinearity.
- **EXP-04** uses a 200-iteration permutation test (minimal but sufficient; explicitly required by the framing).
- All experiments use deterministic, fast, library-based methods. No model-based experiment is needed since OLS in EXP-04 serves only as a baseline statistic for the permutation test.