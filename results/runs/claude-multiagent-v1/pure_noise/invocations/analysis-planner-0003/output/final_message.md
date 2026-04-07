All three artifacts are written:

- **`analysis_plan.md`** -- Structured plan with 3 phases, a decision gate (skip modelling if no signal), and a traceability table mapping every framing required-check to specific experiments.
- **`hypotheses.json`** -- 7 hypotheses (H-NOISE-01 through H-STRUCT-01), each with a null hypothesis, test strategy, linked experiments, and a concrete verdict rule.
- **`experiment_plan.json`** -- 12 experiments with stable IDs (EXP-CORR-01 through EXP-FEATIMP-01), specifying method, columns, expected outputs, and linked hypotheses.

Key design decisions:
- **Signal-first approach**: Phase 1 is entirely about detecting whether any signal exists at all, since the framing warns this may be pure noise. A permutation test (EXP-PERM-01) is the linchpin — it compares the observed R-squared against a null distribution of 1000 shuffled targets.
- **Decision gate**: Phase 2 (deeper modelling) only runs if Phase 1 finds signal. This avoids wasting compute on spurious analysis.
- **Phase 3 always runs**: Distribution checks and PCA characterise the data regardless of signal, providing evidence for the noise hypothesis if that's the conclusion.
- **Bonferroni correction** is applied wherever multiple comparisons occur to guard against false positives in an 800-row dataset.