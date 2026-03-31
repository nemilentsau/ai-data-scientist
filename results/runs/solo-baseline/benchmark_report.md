# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| anscombes_quartet | solved (100%) | - | - |
| class_imbalance | solved (100%) | - | - |
| concept_drift | wrong (12%) | - | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|--------------|----------------|-----------|
| Claude | 67% | 33% | 71% | 61% | 74% |

## Detailed Results

### anscombes_quartet

#### Claude (solved)

**Summary:** The agent delivered an outstanding analysis that fully satisfies every criterion in the evaluation contract. It correctly identified the dataset as a disguised Anscombe's Quartet, computed and displayed per-batch summary statistics showing their near-identity, created comprehensive per-batch visualizations, and identified all four distinct data patterns (linear, quadratic, outlier-driven, leverage-point-driven). The report goes beyond minimum requirements by including diagnostic tests, robust regression comparisons, nuisance variable analysis, and clear model recommendations per batch. No forbidden criteria were triggered — the agent never concluded the batches are the same nor treated them identically.
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Efficiency:** report_chars=8825, trace_events=9, transcript_chars=47081

**Must Have**
- `anscombes_quartet_visualized_all_batches`: hit. All four batches are visualized separately in multiple plots (scatter with OLS lines, residual diagnostics, linear vs quadratic fits, leverage plots) and analyzed individually in Section 3. Evidence: Plot 01_anscombe_quartet_scatter.png shows 2x2 scatter panels; Section 3 has dedicated subsections for batch_Q1 through batch_Q4.
- `anscombes_quartet_identical_summaries_noted`: hit. The report explicitly presents a table of per-batch statistics showing identical means, variances, correlations, and OLS coefficients, and directly states they are the same. Evidence: "All four batches share nearly identical means, variances, correlations (r ~ 0.816), and OLS regression lines (response = 0.500 * dosage + 3.00)" and the full comparison table in Section 2.
- `anscombes_quartet_different_shapes_identified`: hit. The report explicitly identifies four materially different shapes: linear (Q1), quadratic/curvilinear (Q2), linear with outlier (Q3), and leverage-point-driven/vertical structure (Q4). Evidence: "yet each exhibits a fundamentally different data-generating process"; Section 3 headings: 'Well-Behaved Linear Relationship', 'Curvilinear (Quadratic) Relationship', 'Linear With One Outlier', 'Regression Driven by a Single Leverage Point'.

**Supporting**
- `anscombes_quartet_distinct_patterns_described`: hit. All four batch patterns are described in detail with specific anomalies, influential points, and model fit diagnostics — far exceeding the 'at least two batches' threshold. Evidence: Q2: 'The relationship between dosage and response is a perfect parabola'; Q3: 'Observation 25 (dosage=13, response=12.74) has Cook's D = 1.39'; Q4: 'All 10 of 11 observations have dosage = 8, and one observation has dosage = 19.'
- `anscombes_quartet_summary_only_is_inadequate`: hit. The report explicitly and repeatedly explains why summary statistics alone are inadequate. Evidence: "Summary statistics lie by omission"; "Always visualize before modeling. A single scatter plot per batch would have immediately revealed that a unified linear model is inappropriate."
- `anscombes_quartet_named_anscombe`: hit. The dataset is explicitly identified by name in the executive summary. Evidence: "This dataset is a disguised variant of **Anscombe's Quartet** — a classic statistical demonstration that summary statistics alone are insufficient for understanding data."

**Forbidden**
- `anscombes_quartet_summary_only_conclusion`: miss. The report does the opposite — it warns that summary statistics are misleading and that the batches represent fundamentally different phenomena. Evidence: "A naive pooled analysis would entirely miss these critical differences."
- `anscombes_quartet_pooled_identically`: miss. Each batch is analyzed separately with distinct model recommendations. The report explicitly argues against treating them identically. Evidence: Section 5 'Model Recommendation Summary' prescribes a different model for each batch: simple linear, polynomial, robust regression, and no regression respectively.

### class_imbalance

#### Claude (solved)

**Summary:** The agent delivers a thorough and well-structured fraud detection analysis that fully addresses the class imbalance challenge. It correctly identifies the 95/5 split, applies class-weight balancing and stratified cross-validation, reports a comprehensive suite of minority-sensitive metrics (ROC-AUC, Average Precision, F1, per-class precision/recall), and provides confusion matrices and PR curves. The only minor gap is the absence of an explicit explanation of why raw accuracy would be misleading under this imbalance — the agent avoids accuracy entirely but doesn't articulate the baseline accuracy trap for the reader. No forbidden criteria are triggered. Verdict: solved.
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 83%
**Oracle Attainment (roc_auc):** 74%
**Efficiency:** report_chars=10010, trace_events=10, transcript_chars=47809

**Must Have**
- `class_imbalance_imbalance_identified`: hit. The agent clearly identifies the 95/5 class imbalance in the dataset overview and dedicates Section 4.2 to discussing it. Evidence: "Fraud rate | 5.0% (150 fraud / 2,850 legitimate)" and "The 19:1 imbalance ratio is moderate."
- `class_imbalance_balanced_metrics_reported`: hit. The agent reports ROC-AUC, Average Precision, F1, and Brier Score for all three models, plus per-class precision and recall from confusion matrices. Evidence: Results table: ROC-AUC (0.842–0.872), Avg Precision (0.505–0.517), F1 (0.331–0.498), Brier Score. Section 3.3 reports per-class Recall and Precision.
- `class_imbalance_minority_class_evaluated`: hit. The entire modeling section focuses on fraud detection quality with per-class metrics, confusion matrices, and a discussion of precision-recall trade-offs for the minority fraud class. Evidence: "The precision-recall trade-off is stark: LR catches more fraud but with massive false alarm volume. The tree models are conservative but more precise."
- `class_imbalance_imbalance_strategy_used`: hit. The agent applies class_weight='balanced' for LR and RF, uses Average Precision as a primary metric, and employs stratified 5-fold cross-validation. Evidence: Section 4.2: "class_weight='balanced' for LR and RF (upweights minority class in the loss function)", "Stratified cross-validation (preserves class ratios in each fold)"

**Supporting**
- `class_imbalance_baseline_accuracy_trap_noted`: partial. The agent avoids using accuracy entirely and selects imbalance-aware metrics, implicitly recognizing the accuracy trap. However, it never explicitly explains why a naive 95% accuracy baseline makes accuracy misleading. Evidence: Section 3.1: "Metrics: ROC-AUC (discrimination), Average Precision (ranking under imbalance), F1 score (threshold-dependent), Brier score (calibration)" — accuracy is conspicuously absent but its weakness is not discussed.
- `class_imbalance_confusion_matrix_or_pr_curve`: hit. Full confusion matrices are provided for all three models in Section 3.3, and both ROC and PR curves are referenced as generated plots. Evidence: Section 3.3 table with TP/FP/FN/TN for all models; "plots/06_model_curves.png | ROC and Precision-Recall curves for all models"; "plots/08_confusion_matrices.png"
- `class_imbalance_stratified_validation`: hit. Stratified 5-fold cross-validation is explicitly used and its purpose (preserving class proportions) is stated. Evidence: "Evaluation: Stratified 5-fold cross-validation with predictions aggregated across all folds" and Section 4.2: "Stratified cross-validation (preserves class ratios in each fold)"

**Forbidden**
- `class_imbalance_accuracy_only_reporting`: miss. Accuracy is never reported. The agent uses ROC-AUC, Average Precision, F1, and Brier Score as primary evaluation metrics. Evidence: Results table columns: ROC-AUC, Avg Precision, F1, Brier Score — no accuracy column present.
- `class_imbalance_ignores_minority_class`: miss. The minority fraud class is central to the entire analysis, with dedicated per-class metrics, confusion matrices, and operational recommendations for fraud detection. Evidence: Section 3.3 reports fraud-class Recall (37–71%) and Precision (22–69%); Section 6 recommends threshold tuning based on "cost ratio of missed fraud to false alarms."

### concept_drift

#### Claude (wrong)

**Summary:** The agent produced a thorough but fundamentally flawed analysis. It fell directly into the primary trap identified in the ground truth: fitting pooled global models without checking for concept drift. The abrupt distribution shift at the midpoint was completely missed, leading the agent to incorrectly conclude that all features are independent of the defect rate. The agent did examine temporal patterns superficially (time trends, autocorrelation) but never performed any drift-specific diagnostic — no data splitting at the midpoint, no changepoint detection, no rolling model evaluation. Because the forbidden criterion 'single_model_without_drift_check' is hit, the verdict is **wrong**. All four must-have criteria were missed, and no supporting criteria were met.
**Core Insight:** fail
**Required Coverage:** 12%
**Supporting Coverage:** 0%
**Fatal Errors:**
- Fit a single pooled model without checking for drift.
**Efficiency:** report_chars=9323, trace_events=14, transcript_chars=68943

**Must Have**
- `concept_drift_temporal_order_respected`: partial. The agent created time series plots with 24h rolling means and checked for autocorrelation, linear time trends, day-of-week, and hour-of-day effects. However, the core modeling used '5-fold, shuffled, random_state=42' cross-validation, destroying temporal order for the primary analysis. Evidence: Cross-validation: 5-fold, shuffled, random_state=42; Time Series Overview with 24h Rolling Mean plot; Ljung-Box test
- `concept_drift_drift_detected`: miss. The agent explicitly concluded there is no temporal structure and no distribution shift. The abrupt concept drift at the midpoint was completely missed. Evidence: Finding 3: 'No temporal structure in defect_rate' — 'No time trend: Linear trend slope ≈ 0 (p = 0.85)' — 'No autocorrelation'
- `concept_drift_pre_post_segments_compared`: miss. The agent never split the data into pre- and post-midpoint segments. No comparison of first half vs second half was performed. Evidence: No mention of splitting data at any point. All analysis pools the full 1,500 rows.
- `concept_drift_single_global_model_problem_noted`: miss. The agent noted that global models fail (negative R²) but attributed this entirely to features being uninformative, not to concept drift degrading a single global model. The drift-related explanation was never considered. Evidence: Finding 1: 'defect_rate is independent of all measured process variables' — 'Negative R² indicates models are fitting noise'

**Supporting**
- `concept_drift_relationship_flip_described`: miss. The agent never identified that the temperature-defect relationship changes sign across regimes. All correlations were reported as global aggregates. Evidence: Pearson correlations reported globally: 'All |r| < 0.07'
- `concept_drift_changepoint_or_rolling_diagnostic`: miss. While 24h rolling means were plotted, they were purely decorative and not used as diagnostic tools. No changepoint detection algorithm or rolling model performance metric was applied. Evidence: Time series plots show rolling means but no analysis of shifts in those rolling statistics. No changepoint methods mentioned.
- `concept_drift_adaptation_strategy_suggested`: miss. Recommendations focused on unmeasured confounders and measurement review, not on drift-aware strategies like retraining, segmentation, or monitoring. Evidence: Recommended next steps: 'Investigate unmeasured variables', 'Review the defect_rate measurement', 'Process capability study', 'Root cause analysis'

**Forbidden**
- `concept_drift_single_model_without_drift_check`: hit. The agent fit OLS, Ridge, Random Forest, Gradient Boosting, and Logistic Regression all as single pooled models on the full dataset. While temporal patterns were examined superficially (linear trend, autocorrelation), no actual drift check was performed — no distributional shift test, no changepoint detection, no comparison of model performance across time windows. Evidence: Models trained on all 1,500 rows with shuffled 5-fold CV. 'CV R²' reported for pooled models only. No split-sample or rolling-window model evaluation.
- `concept_drift_ignores_time_order`: miss. The agent did examine temporal structure: time series plots with rolling means, autocorrelation tests, day-of-week and hour-of-day analyses. While the core modeling used shuffled CV, time order was not entirely ignored in the analysis. Evidence: Plot 3: Time Series Overview; Plot 8: Daily aggregated trends; Ljung-Box test; hourly/daily groupby analyses
