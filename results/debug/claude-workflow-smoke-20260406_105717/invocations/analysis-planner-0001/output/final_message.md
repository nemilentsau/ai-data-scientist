All three artifacts written:

- **`analysis_plan.md`** — 4 experiments covering all 5 required checks, with an explicit check-to-experiment mapping table.
- **`hypotheses.json`** — 5 hypotheses (H-01 through H-05), each linked to required checks, framing risks, and experiments. Four are null hypotheses (expecting no signal in this pure-noise dataset); H-05 is directional (commute skew is observable from the profile).
- **`experiment_plan.json`** — 4 experiments with stable IDs (EXP-01 through EXP-04). Only EXP-03 is model-based. EXP-03 is reused across checks 2 and 3. Total estimated runtime: ~43 seconds.

**Design rationale**: The dataset name ("pure_noise") and the diffuse distributions strongly suggest no genuine signal. The plan is structured to confirm that conclusion rigorously — correlations should not survive Bonferroni, the RF model should match the mean baseline, and salary_band groups should not separate. The one expected positive finding is commute_minutes right-skew (median 16, mean 24.5, max 120), which is visible directly from the profile stats.