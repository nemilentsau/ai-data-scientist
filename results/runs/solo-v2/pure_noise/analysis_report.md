# Employee Performance Analysis Report

## Dataset Overview

This dataset contains 800 employee records with 10 variables: `employee_id`, `years_experience`, `training_hours`, `team_size`, `projects_completed`, `satisfaction_score`, `commute_minutes`, `performance_rating`, `salary_band`, and `remote_pct`. There are no missing values. The target variable of interest is `performance_rating` (range: 9.5–75.3, mean: 50.0, SD: 10.0).

Key characteristics of the features:
- **years_experience**: 0.2–30.0 years (mean 14.9), roughly uniform
- **training_hours**: 0–79.5 hours (mean 41.1), roughly normal
- **team_size**: 3–24 members (mean 13.7), roughly uniform
- **salary_band**: Five levels (L1–L5) with approximately equal counts (~150–170 each)
- **remote_pct**: Five levels (0%, 25%, 50%, 75%, 100%) with approximately equal counts (~138–194 each)
- **commute_minutes**: 5–120 minutes (mean 24.5), heavily right-skewed (skewness = 1.77)

See: `plots/08_feature_distributions.png`

## Key Finding: Performance Is Largely Unpredictable from Available Features

**The central result of this analysis is that the available features explain almost none of the variance in performance ratings.** This is the most important finding and should inform how the remaining results are interpreted.

Evidence:
- All pairwise Pearson correlations with `performance_rating` are negligible: the strongest is `team_size` at r = -0.086 (see `plots/02_correlation_heatmap.png`, `plots/09_effect_sizes_summary.png`)
- A full OLS regression using all features yields R² = 0.013 — the model explains only **1.3% of variance**
- Random Forest (5-fold CV): R² = -0.034 (worse than predicting the mean)
- Gradient Boosting (5-fold CV): R² = -0.127 (worse than predicting the mean)

Machine learning models with negative R² indicate that the features contain no useful signal beyond noise. The data is consistent with performance ratings being essentially independent of the measured employee and workplace attributes.

See: `plots/05_all_features_vs_performance.png`

## Three Weak Signals

Despite the overall lack of predictability, three statistically weak signals were detected. These are reported with appropriate caveats — effect sizes are small and practical significance is questionable.

See summary: `plots/10_key_findings_summary.png`

### 1. Team Size: Small Negative Association with Performance

Employees on smaller teams have slightly higher performance ratings.

| Metric | Value |
|--------|-------|
| Pearson r | -0.086 |
| Spearman rho | -0.083 |
| OLS coefficient | -0.13 per team member (p = 0.019) |
| Permutation test p-value | 0.016 |
| Variance explained | 0.74% |
| Effect across full range (3→24) | -2.7 points (~0.27 SD) |

The effect survives a permutation test (p = 0.016) and is the only individually significant predictor in OLS regression. However, after Bonferroni correction across 7 tests, the OLS and Spearman p-values become non-significant (corrected p = 0.133). The comparison of top-25% vs bottom-25% performers on team size remains significant after correction (raw p = 0.003, corrected p = 0.021, Cohen's d = -0.28).

The LOWESS curve in `plots/03_team_size_vs_performance.png` shows the relationship is approximately linear with no obvious threshold effect.

**Interpretation**: While statistically detectable, team size explains less than 1% of performance variance. This is too small to be actionable. It could reflect genuine coordination overhead in larger teams, or it could be a type I error.

### 2. Remote Work at 50%: Slightly Lower Performance

Employees working 50% remotely have slightly lower mean performance (47.9) compared to all other remote work levels (50.4).

| Metric | Value |
|--------|-------|
| Mean difference | -2.56 points |
| t-test p-value | 0.006 |
| 95% Bootstrap CI | [-4.41, -0.73] |
| Bonferroni-corrected p | 0.042 |

The Tukey HSD pairwise comparisons across all five remote groups are not individually significant after family-wise correction, though 50% vs 100% is borderline (adjusted p = 0.056).

See: `plots/04_remote_pct_vs_performance.png`, `plots/07_remote_work_deep_dive.png`

**Interpretation**: The 50% remote group shows a real but small deficit (~0.25 SD). This is an isolated dip rather than a monotonic trend — fully remote (100%) and fully in-office (0%) employees perform similarly. One speculative explanation is that hybrid schedules at 50% create coordination friction. However, the effect is small enough that it could also reflect sampling variation in a dataset of this size.

### 3. Training Hours x Team Size Interaction (Marginal)

A two-way ANOVA reveals a marginally significant interaction between training hours and team size (p = 0.047):

| Group | High Training | Low Training |
|-------|--------------|-------------|
| Small team (≤12) | 50.1 | 51.4 |
| Large team (>12) | 50.2 | 48.7 |

In small teams, more training does not help (and may slightly hurt). In large teams, more training is associated with slightly better performance. However, after Bonferroni correction this interaction is not significant (corrected p = 0.329).

See: `plots/06_interaction_training_teamsize.png`

**Interpretation**: This interaction is too fragile to draw conclusions from. The differences are within noise range (1–2 points on a 10-SD scale), and the result does not survive multiple testing correction.

## Non-Findings (Features with No Detectable Effect)

The following features show **no meaningful relationship** with performance:

- **Years of experience** (r = -0.015, p = 0.784): Employees with 1 year perform indistinguishably from those with 30 years.
- **Satisfaction score** (r = 0.001, p = 0.954): Employee satisfaction is completely uncorrelated with performance.
- **Projects completed** (r = 0.016, p = 0.707): Quantity of projects does not predict performance ratings.
- **Commute minutes** (r = -0.006, p = 0.998): No threshold or linear effect at any commute distance.
- **Salary band** (ANOVA F = 0.718, p = 0.579): Performance is identical across all five salary levels. Notably, salary band is also unrelated to years of experience or training hours.

These non-findings are themselves informative. If this data reflects a real organization, either:
1. Performance ratings capture something orthogonal to these measurable attributes (e.g., soft skills, motivation, role fit)
2. Performance ratings have substantial measurement noise or subjective bias
3. The features are too coarsely measured to capture real relationships

## Limitations and Self-Critique

### What alternative explanations exist?
- The "signals" found (team size, remote 50%) could be type I errors. With ~7 independent hypotheses tested at alpha = 0.05, we expect ~0.35 false positives by chance. After Bonferroni correction, most findings become non-significant.
- The dataset may be synthetic or simulated. The uniformity of salary band distributions, the discrete remote_pct values, and the near-complete independence of all features are consistent with randomly generated data.

### What assumptions could be wrong?
- I assumed linear and monotonic relationships as a starting point. I checked for quadratic effects and interactions, finding nothing substantial.
- I assumed features are measured without error. If `performance_rating` has high measurement noise, true relationships would be attenuated.

### What wasn't investigated?
- Temporal patterns: if `employee_id` encodes hire order, there could be cohort effects (not tested because the interpretation is ambiguous).
- Three-way or higher-order interactions: with 8 features, combinatorial search is impractical and would inflate false discovery risk.
- Causal structure: all analysis is correlational. Even the team size finding cannot establish whether smaller teams cause better performance or if better performers are assigned to smaller teams.

### Are conclusions supported by evidence?
The primary conclusion — that these features do not meaningfully predict performance — is robustly supported by multiple methods (correlation, regression, random forest, gradient boosting, ANOVA). The three weak signals are reported honestly with effect sizes, confidence intervals, and multiple testing corrections. None are strong enough to be actionable.

## Summary

| Finding | Effect Size | Statistical Significance | Practical Significance |
|---------|------------|-------------------------|----------------------|
| Features don't predict performance | R² = 0.013 (OLS), R² < 0 (ML) | N/A | **High** — the absence of signal is the key finding |
| Team size negatively associated | r = -0.086, 0.74% variance | p = 0.016 (permutation) | Negligible |
| 50% remote slightly lower | -2.56 points | p = 0.006 (t-test) | Marginal at best |
| Training x team size interaction | ~2 point difference | p = 0.047 (uncorrected) | Not significant after correction |

**Bottom line**: The available employee attributes — experience, training, team size, satisfaction, commute, salary band, and remote work percentage — collectively explain only 1.3% of the variance in performance ratings. For practical purposes, performance in this dataset is independent of these features. Any organizational decisions based on these variables would be indistinguishable from noise.
