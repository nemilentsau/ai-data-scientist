Done. Three artifacts written to the workspace:

- **`analysis_plan.md`** — 3 experiments with explicit mapping to all 5 required checks and all 4 framing risks
- **`hypotheses.json`** — 3 hypotheses (H-01 correlation, H-02 salary band distributions, H-03 predictive signal), each linked to checks and experiments
- **`experiment_plan.json`** — executable specs for EXP-01 (Pearson+Spearman+Bonferroni), EXP-02 (Kruskal-Wallis by salary band), EXP-03 (Ridge CV with 100-iteration permutation test)

The plan uses exactly 1 model-based experiment (EXP-03) and reuses Bonferroni correction across EXP-01 and EXP-02 to jointly cover the multiple-comparison check. All methods are deterministic or low-cost (100 permutations), fitting within a single local invocation.