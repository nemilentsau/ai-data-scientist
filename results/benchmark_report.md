# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| simpsons_paradox | partial (70%) | - | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|--------------|----------------|-----------|
| Claude | 0% | 0% | 70% | 33% | 0% |

## Detailed Results

### simpsons_paradox

#### Claude (partial)

**Summary:** The agent conducted a thorough and technically competent analysis including EDA, ANOVA, regression modeling, and diagnostic checks. It correctly computed aggregate and within-group treatment effects and based its final recommendation on stratified evidence. However, it entirely missed the core dataset pattern: Simpson's paradox. The agent never identified that the aggregate effect is suppressed/attenuated by confounding department composition, never named the paradox, and instead characterized the treatment effect as 'consistent' rather than highlighting the discrepancy between aggregate and stratified effect magnitudes. While no forbidden criteria were triggered, the failure to identify the reversal (or at minimum the dramatic attenuation) as the central finding means the analysis misses the key insight the contract demands.
**Core Insight:** fail
**Required Coverage:** 70%
**Supporting Coverage:** 33%
**Efficiency:** report_chars=5821, trace_events=9, transcript_chars=38006

**Must Have**
- `simpsons_paradox_aggregate_effect`: hit. The agent computed and reported the aggregate treatment comparison explicitly. Evidence: MEANS BY TREATMENT: A recovery=68.71, B recovery=66.66; report states Treatment A yields ~4.7 points higher recovery overall.
- `simpsons_paradox_within_group_effects`: hit. The agent computed treatment effects within each department with t-tests and Cohen's d. Evidence: T-tests within each department: Cardiology +4.5, Neurology +5.1, Orthopedics +5.1; Cohen's d = 0.76–0.86.
- `simpsons_paradox_reversal_identified`: miss. The agent never identifies or states a reversal between aggregate and within-group trends. Instead, it reports the effect is consistent in the same direction (Treatment A better everywhere), just attenuated at the aggregate level. The contract requires explicitly stating the trend reverses, which the agent does not do. Evidence: Report says: 'Treatment A Consistently Outperforms Treatment B... Consistent across all departments... No interaction: The treatment effect does not vary by department (interaction p=0.75)'
- `simpsons_paradox_confounder_identified`: partial. The agent identifies that departments serve different severity populations and that raw department comparisons are misleading, recognizing confounding structure. However, it does not frame department as the confounder driving a paradoxical reversal—only as explaining attenuated effects. Evidence: Report: 'Departments differ dramatically in raw outcomes, but this is driven entirely by patient composition... Do not benchmark departments against each other without adjusting for severity.'
- `simpsons_paradox_correct_conclusion`: hit. The final recommendation is based on the stratified (within-group) analysis, not the aggregate trend alone. The agent recommends Treatment A based on per-department evidence. Evidence: Recommendation: 'Adopt Treatment A as the preferred protocol — it yields significantly better recovery scores (+4.7 points, d≈0.8) with no increase in length of stay, consistent across all departments.'

**Supporting**
- `simpsons_paradox_named_simpsons_paradox`: miss. The agent never names Simpson's paradox or describes the mechanism of aggregate trend reversal in equivalent language. Evidence: No mention of 'Simpson's paradox' or equivalent terminology anywhere in the report.
- `simpsons_paradox_effect_sizes_quantified`: hit. The agent quantifies both aggregate and subgroup effect sizes with means, differences, Cohen's d, and confidence intervals. Evidence: Aggregate: A=68.71 vs B=66.66; Per-department: +4.5 (Cardiology), +5.1 (Neurology), +5.1 (Orthopedics); Cohen's d = 0.76–0.86.
- `simpsons_paradox_visualized_reversal`: miss. While the agent produces treatment-by-department bar charts and boxplots, there is no visualization specifically designed to show a reversal between aggregate and subgroup trends. Evidence: Plot 08 shows treatment effects with CI by department, but no side-by-side aggregate vs. stratified comparison that highlights reversal.

**Forbidden**
- `simpsons_paradox_aggregate_only_conclusion`: miss. The agent's conclusion is based on stratified analysis, not on the aggregate trend alone. Evidence: Conclusion explicitly references per-department consistency: 'consistent across all departments.'
- `simpsons_paradox_ignores_grouping_variable`: miss. The agent extensively analyzes the department grouping variable and its confounding role. Evidence: Section 2.1 is dedicated to department-level analysis; Section 2.2 breaks treatment effects by department.
