# Analysis Planner — Round 1 Summary

## What worked

- **Decision gate design was the standout success.** The pre-registered gate ("if R² does not exceed null 95th percentile AND no correlation survives Bonferroni → declare no signal") was the right architecture for a suspected-noise dataset. It correctly fired: observed R² = 0.014, null 95th percentile = 0.023, p = 0.46.
- **Phased plan structure was sound.** Phase 1 (signal detection) → decision gate → Phase 2 (deeper analysis, conditional) → Phase 3 (distribution checks, always) was praised by the verifier.
- **Permutation test was the strongest single experiment.** EXP-PERM-01 produced the clearest evidence and the best visualization (permutation_r2_hist.png was praised by both critics).
- **Experiment coverage was complete.** All 12 experiments ran. All 6 framing required_checks were addressed. 9 findings produced, 5 claims mapped.

## Issues flagged by critics — fix in next round

### High severity
1. **No power analysis.** The plan never quantifies what "no signal" means in terms of minimum detectable effect. With n=800 and Bonferroni for 7 target correlations, the minimum detectable |r| ≈ 0.12 at 80% power. Add a power calculation to Phase 1 so the null conclusion is properly bounded.

### Medium severity
2. **Decision gate was bypassed.** The plan said "proceed to Phase 3 only" if no signal, but Phase 2 ran anyway "for completeness." This inflates the effective number of comparisons. Next round: either honour the gate strictly, or pre-register the deviation with additional multiple-comparison correction.
3. **Bonferroni factor mismatch.** Hypothesis H-CORR-01 specified 7 tests (each predictor vs target), but execution applied correction for 28 tests (all pairwise). Conservative here, but the plan-vs-execution inconsistency is a methodological error. Pick one and be consistent.
4. **team_size p=0.020 silently dismissed.** This was the only nominally significant OLS coefficient and the largest |r| = 0.086. The report dismissed it without discussion. Next round: explicitly flag the most plausible weak-signal candidate and explain why it's dismissed (expected false positives at α=0.05 with 7 predictors ≈ 0.35).
5. **PCA included the target variable.** H-STRUCT-01 specified "7 numeric features" but execution used 8 (including performance_rating), changing the uniform baseline from 1/7 to 1/8. Exclude the target from PCA in future plans.
6. **RF importance plot is misleading.** Permutation importances were computed on training data of an overfit model (CV R² = -0.086). The plot shows positive bars suggesting signal. Next round: either skip the RF importance plot when CV R² is negative, or annotate it with "CV R² = -0.086; importances reflect noise memorisation."

### Low severity
7. **Single chi-squared test overclaimed for mutual independence.** Only salary_band vs remote_pct tested. Insufficient to support claim C-02 ("all columns mutually independent").
8. **commute_minutes skewness elevated to finding status.** Distributional shape of an independent column has no inferential consequence. Keep it as a data-quality note, not a hypothesis-level finding.
9. **OLS residual diagnostics absent.** No residual-vs-fitted or Q-Q plot. Add these whenever OLS is reported.
10. **Provenance claim overreaches.** "Data appears entirely synthetic" is an interpretation, not a statistical conclusion.

## Visual improvements needed

| Priority | Issue | Fix |
|----------|-------|-----|
| CRITICAL | feature_importance.png implies signal | Add CV R² annotation or skip plot when model fails |
| MAJOR | scatter_lowess.png illegible | Larger figure, lower alpha, jitter for discrete vars |
| MAJOR | distributions.png too small | Larger figure (16x10), bigger font, highlight commute_minutes |
| MAJOR | No OLS residual plot | Add residuals-vs-fitted scatter |
| MAJOR | Correlation matrix uninformative | Tighten colour scale to [-0.15, 0.15] or annotate max |r| |
| MINOR | PCA biplot labels overlap, not colourblind-safe | Use Okabe-Ito palette, adjust label positions |
| MINOR | Scree plot y-axis compression | Dual-axis or inset for individual variance bars |
| MINOR | Salary boxplot missing group sizes | Add n= labels |

## Ledger state

All three ledgers (experiment, hypothesis, issue) are empty (`{"items":[]}`). If ledgers are meant to track status across rounds, populate them from the findings and critiques above.

## Key numbers

| Metric | Value |
|--------|-------|
| Observed R² | 0.014 |
| Null 95th pct R² | 0.023 |
| Permutation p | 0.46 |
| Max |r| with target | 0.086 (team_size, uncorrected p=0.015) |
| RF CV R² | -0.086 |
| OLS F p-value | 0.456 |
| VIF range | 1.002 – 1.013 |
| Chi² p (salary vs remote) | 0.978 |
| Verification | pass, confidence 0.93 |
| Findings | 9 (2 SUPPORTED, 7 NOT SUPPORTED) |
| Claims | 5 (4 strong, 1 moderate) |

## Conclusion carried forward

Dataset is confirmed pure noise. No revision cycle needed for the core conclusion. If a next round occurs on a different dataset, carry forward the methodological fixes above (especially: power analysis, honour the decision gate, exclude target from PCA, annotate or suppress misleading RF plots).
