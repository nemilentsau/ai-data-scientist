# Methodological Critique

## Overall Assessment

The analysis reaches the correct top-level conclusion — the dataset contains no predictive signal — and supports it with multiple convergent tests. The decision-gate design (permutation test + Bonferroni-corrected correlations) is appropriate for the pure-noise scenario. However, several methodological weaknesses undermine the rigour of the evidence chain and could mislead readers in less clear-cut cases.

---

## 1. Absence of Evidence vs Evidence of Absence

**Severity: High**

The report repeatedly states that relationships "do not exist" (e.g., "performance_rating is statistically independent of all predictor columns"). Strictly, the tests show a failure to reject the null, not confirmation of independence. The analysis never quantifies **statistical power**: with n = 800, what is the minimum detectable correlation at 80% power? For a two-tailed test at alpha = 0.05/7 (Bonferroni for 7 target correlations), the minimum detectable |r| is approximately 0.12. This means the analysis is adequately powered to detect moderate effects but not weak ones (|r| ~ 0.05–0.10). The claim "no signal" should be bounded: "no effect larger than |r| ~ 0.12 is detectable at 80% power given this sample size and correction."

Without this bound, the strength labels ("strong") on claims C-01 and C-02 are overconfident.

---

## 2. Decision Gate Was Bypassed Without Justification

**Severity: Medium**

The analysis plan explicitly states: "If the observed R-squared does not exceed the 95th percentile... declare no signal and proceed to Phase 3 only." The decision gate correctly fired as "no signal," yet all Phase 2 experiments were run anyway "for completeness."

Running additional tests after a pre-registered stopping rule increases the effective number of comparisons and invites post-hoc interpretation. The report should have either (a) honoured the gate and skipped Phase 2, or (b) acknowledged the deviation and applied a more stringent correction to account for the additional tests. As it stands, Phase 2 results are presented alongside Phase 1 with equal weight, which blurs the pre-registration boundary.

---

## 3. Bonferroni Correction Factor Mismatch

**Severity: Medium**

The report applies Bonferroni correction for 28 pairwise tests (all 8-choose-2 pairs) when assessing correlations with the target. But only 7 tests are relevant for the target-prediction question (each predictor vs performance_rating). Using 28 is more conservative and does not change the conclusion here, but it conflates two different testing families: (a) whether any predictor correlates with the target (7 tests), and (b) whether any pair of columns is correlated (28 tests). Hypothesis H-CORR-01 correctly specifies 7 tests, yet the execution used 28. This inconsistency between the hypothesis specification and the actual correction factor is a methodological error, even if it errs on the conservative side.

---

## 4. Nominally Significant OLS Coefficient Insufficiently Discussed

**Severity: Medium**

The team_size coefficient has p = 0.020 in the OLS model — nominally significant at alpha = 0.05. The report dismisses it with "no individual coefficient is statistically significant" without further discussion. While this p-value does not survive Bonferroni correction for 11 coefficients (corrected p ~ 0.22), it is the only coefficient below 0.05 and its Pearson r = -0.086 (uncorrected p = 0.015) is the largest magnitude in the matrix.

A careful analysis should flag this as the most plausible candidate for a weak signal and explain why it is dismissed: expected number of false positives at alpha = 0.05 with 7 independent predictors is 0.35, so one marginal result is entirely consistent with chance. The current treatment — silent dismissal — would be a problem in a dataset where a weak true signal exists.

---

## 5. PCA Includes the Target Variable

**Severity: Medium**

PCA was run on all 8 numeric features including performance_rating. Standard practice for exploratory feature analysis excludes the target to avoid circular reasoning: if the goal is to discover predictor structure that might relate to the outcome, including the outcome inflates the apparent dimensionality test. The hypothesis H-STRUCT-01 specifies "7 numeric features" and a baseline of 1/7 per component, but the execution used 8 features with a baseline of 1/8. This inconsistency between plan and execution is evident in the report, which cites the 1/8 baseline. While the conclusion (no latent structure) is unaffected, the mismatch between planned and executed methodology should be flagged.

---

## 6. Random Forest Feature Importance Plot Is Misleading

**Severity: Medium**

The feature importance bar chart (feature_importance.png) displays positive permutation importances for all features, with team_size appearing most "important." The report correctly notes that CV R-squared is deeply negative, but the plot itself — presented without that context — would lead a reader to conclude that team_size, training_hours, and years_experience are meaningful predictors.

The issue: permutation importance was computed on the training set of an overfitting model. Shuffling a feature that the model has memorized degrades training-set performance, producing a large positive importance that reflects the degree of memorization, not predictive value. The plot should either (a) not be produced for a model with negative CV R-squared, or (b) include a prominent annotation stating the importances are artefacts of overfitting. As presented, it contradicts the report's own conclusions.

---

## 7. Chi-Squared Independence Test Covers Only One Pair

**Severity: Low-Medium**

Claim C-02 ("all columns are mutually independent") partially relies on F-INDEP-01 (chi-squared test of salary_band vs binned remote_pct). But this tests only 1 of the 7 possible salary_band-vs-numeric-predictor pairs and none of the other categorical discretisations. A single pair cannot support a claim about universal independence. The Kruskal-Wallis tests in EXP-SAL-01 partially compensate (testing salary_band against all 8 numeric features), but the chi-squared test adds little incremental evidence given its narrow scope. The evidence map overstates its contribution.

---

## 8. Commute Minutes Finding Is Inferentially Irrelevant

**Severity: Low**

Finding F-COMM-01 (commute_minutes is right-skewed with outliers) is awarded "moderate" strength and treated as a supported hypothesis on equal footing with the noise conclusion. However, distributional shape of an independent column has no inferential consequence: it does not affect any model, violate any assumption in use, or inform any decision. It is a characterization of the data-generating process, not a finding about relationships. Elevating it to hypothesis status and tracking it through the evidence chain inflates the apparent productivity of the analysis without adding substantive value.

---

## 9. OLS Residual Diagnostics Absent

**Severity: Low**

The OLS summary shows Omnibus p = 0.033 and skewness = -0.226, indicating mild residual non-normality. The permutation test is robust to this, but the report does not acknowledge or discuss it. More importantly, no residual-vs-fitted or Q-Q plot is produced. For completeness, residual diagnostics should appear whenever OLS results are reported, even when the model is null — they confirm that the permutation test's exchangeability assumption holds.

---

## 10. Synthetic-Data Provenance Claim Is Unsupported Inference

**Severity: Low**

The report concludes: "The data appears entirely synthetic, generated from independent random distributions." Statistical independence and simple marginal distributions are consistent with synthetic generation, but they do not prove it. Real-world data can also exhibit independence among poorly chosen features. This is a claim about data provenance — how the data was created — which cannot be established from distributional properties alone. The report should state this as a plausible interpretation rather than a conclusion.

---

## Summary of Issues

| # | Issue | Severity | Affects Conclusion? |
|---|-------|----------|---------------------|
| 1 | No power analysis; overconfident null claims | High | Could miss weak signal |
| 2 | Decision gate bypassed without correction | Medium | Inflates test count |
| 3 | Bonferroni factor mismatch (28 vs 7) | Medium | No (conservative) |
| 4 | team_size p=0.020 silently dismissed | Medium | Not here, but risky pattern |
| 5 | PCA includes target variable | Medium | No, but plan/execution mismatch |
| 6 | RF importance plot misleading without context | Medium | Could mislead readers |
| 7 | Single chi-squared test overclaimed | Low-Medium | Weakens C-02 support |
| 8 | Commute skewness elevated to finding | Low | No |
| 9 | OLS residual diagnostics missing | Low | No |
| 10 | Synthetic-provenance claim overreaches | Low | No |

**Bottom line:** The central conclusion (no predictive signal) is well-supported and almost certainly correct. The main methodological gap is the lack of a power analysis to bound what "no signal" means quantitatively. Secondary issues — bypassing the decision gate, the misleading RF importance plot, and silent dismissal of the team_size coefficient — represent patterns that would cause real damage on a dataset with subtle true effects.
