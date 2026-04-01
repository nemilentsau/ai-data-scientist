# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| simpsons_paradox | partial (60%) | - | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Run Error Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|----------------|--------------|----------------|-----------|
| Claude | 0% | 0% | 0% | 60% | 17% | 0% |

## Detailed Results

### simpsons_paradox

#### Claude (partial)

**Summary:** The agent conducted a rigorous and methodical analysis with correct within-department treatment comparisons, proper covariate balance checks, well-specified regression models, and appropriate diagnostics. Its practical conclusion — favor Treatment A — is correct and grounded in stratified evidence. However, the agent fundamentally missed the dataset's key pattern: Simpson's Paradox. Despite computing both the aggregate effect (in the session) and the within-group effects (in the report), the agent never juxtaposed them, never identified the attenuation/discrepancy as paradoxical, never named Simpson's Paradox, and never explained how confounded treatment-department assignment makes the aggregate effect misleading. The analysis is technically sound but misses the core discovery insight the dataset was designed to test.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 60%
**Supporting Coverage:** 17%
**Efficiency:** report_chars=9560, trace_events=11, transcript_chars=51693

**Must Have**
- `simpsons_paradox_aggregate_effect`: partial. The agent computed the aggregate treatment effect in the session transcript (A=68.71 vs B=66.66, diff=+2.06, p=6.70e-06) but did NOT present this aggregate comparison in the final report. The report jumps directly to within-department effects in Section 3.1 without first establishing the aggregate baseline, undermining the ability to contrast the two. Evidence: Session: 'Overall Treatment A mean: 68.71 ... Overall Treatment B mean: 66.66 ... Difference: 2.06'. Report Section 3 skips straight to 'Within-Department Treatment Effect'.
- `simpsons_paradox_within_group_effects`: hit. The agent clearly computed and presented treatment effects within each department with means, differences, Cohen's d, and p-values. Evidence: Section 3.1 table: Cardiology +4.5 (d=0.76), Neurology +5.1 (d=0.84), Orthopedics +5.1 (d=0.86), all highly significant.
- `simpsons_paradox_reversal_identified`: miss. The agent never states that the treatment effect direction or magnitude changes misleadingly between aggregate and within-group analysis. The aggregate effect (+2.06) is attenuated compared to within-group effects (+4.5 to +5.1), but the agent never contrasts these or identifies the discrepancy as a reversal or paradox. The report presents only the within-group result without noting the aggregate attenuation. Evidence: No statement anywhere in the report or session output comparing the aggregate +2.06 effect to the within-group ~+5 effects or noting the discrepancy.
- `simpsons_paradox_confounder_identified`: partial. The agent identified that treatment assignment is unbalanced across departments (Section 2.3) and that departments have very different patient profiles (severity, age). However, the agent did not explicitly frame department as a confounder that drives a misleading aggregate effect. The confounding is noted factually but not connected to the paradox mechanism. Evidence: Section 2.3: 'Treatment assignment is not balanced across departments: Cardiology 36%A/64%B, Orthopedics 70%A/30%B'. Section 6: 'apparent differences between departments are fully explained by their differing severity profiles'.
- `simpsons_paradox_correct_conclusion`: hit. The agent's practical recommendation is based on the stratified within-department analysis, not the aggregate trend. The conclusion correctly favors Treatment A based on the consistent ~4.7-5 point within-department advantage. Evidence: Section 7: 'Favor Treatment A for improving recovery outcomes. The evidence for its superiority is strong and consistent.'

**Supporting**
- `simpsons_paradox_named_simpsons_paradox`: miss. The agent never names Simpson's Paradox nor describes the mechanism of an aggregate trend being misleading due to confounded group composition. Evidence: No mention of 'Simpson' or 'paradox' or equivalent language anywhere in the report.
- `simpsons_paradox_effect_sizes_quantified`: partial. Within-group effect sizes are thoroughly quantified (differences, Cohen's d, CIs). The aggregate effect was computed in the session transcript (+2.06) but never presented in the report, so the contrast between aggregate and subgroup sizes is not made explicit. Evidence: Report table: dept-level diffs of +4.5, +5.1, +5.1 with Cohen's d 0.76-0.86. Session: overall diff = 2.06. These are never juxtaposed.
- `simpsons_paradox_visualized_reversal`: miss. No visualization or table contrasts the aggregate treatment effect against the within-group effects to make the attenuation/reversal visible. Plot 06 shows within-department treatment comparisons but has no aggregate reference. Evidence: Plot index lists 'plots/06_treatment_by_department.png' for within-department effects but no plot showing aggregate vs stratified comparison.

**Forbidden**
- `simpsons_paradox_aggregate_only_conclusion`: miss. The agent's final conclusion is based on the stratified within-department analysis, not the aggregate trend. The recommendation to favor Treatment A cites the within-department evidence. Evidence: Section 6: '~4.7-point advantage across all departments (partial eta²=0.169)'. Section 7: 'Favor Treatment A'.
- `simpsons_paradox_ignores_grouping_variable`: miss. The agent extensively analyzes the department grouping variable, including department profiles, treatment-department imbalance, and within-department effects. Evidence: Sections 2.1, 2.3, and 3.1 all analyze department as a key grouping variable with confounding noted.
