# Analysis Report

## Primary Frame
Identify which employee attributes, if any, are predictive of `performance_rating`.

## Dataset
- 800 rows, 10 columns (1 ID, 7 numeric predictors, 1 target, 1 categorical)
- Zero nulls; synthetic / pre-cleaned data
- Target: `performance_rating` (mean=50.0, std=10.0, range [9.5, 75.3])

---

## EXP-01: Distribution & Pairwise Correlations

**Objective**: Assess normality/outliers in `performance_rating`; compute pairwise correlations.

### Results

**Distribution**:
- Shapiro-Wilk: W=0.9947, p=0.0071 — statistically significant departure from normality, though the effect is small (W close to 1). With n=800, the test is sensitive to minor deviations.
- 2 outliers beyond mean +/- 3 SD.
- Visual inspection (histogram) shows an approximately bell-shaped distribution.

**Correlations**:

| Feature | Pearson r | p-value | Spearman rho | p-value |
|---|---|---|---|---|
| years_experience | -0.0149 | 0.6733 | -0.0041 | 0.9077 |
| training_hours | 0.0455 | 0.1983 | 0.0391 | 0.2688 |
| team_size | -0.0860 | 0.0150 | -0.0832 | 0.0186 |
| projects_completed | 0.0164 | 0.6441 | 0.0153 | 0.6659 |
| satisfaction_score | 0.0014 | 0.9694 | 0.0147 | 0.6788 |
| commute_minutes | -0.0062 | 0.8600 | 0.0084 | 0.8119 |
| remote_pct | 0.0232 | 0.5125 | 0.0291 | 0.4105 |

**No feature exceeds |r| > 0.1 at p < 0.05.** The strongest individual correlation is `team_size` (r=-0.086, p=0.015) which is statistically significant at p<0.05 but fails the practical significance threshold of |r|>0.1. All correlations are negligibly small.

**Plots**: `plots/exp01_performance_dist.png`, `plots/exp01_correlations.png`
**Stats**: `stats/exp01_correlations.json`

---

## EXP-02: Salary Band Investigation

**Objective**: Determine whether `salary_band` acts as an ordinal proxy.

### Results

**Band frequencies**: L1=163, L2=144, L3=163, L4=160, L5=170 — roughly balanced.

**Kruskal-Wallis test**: H=3.9586, p=0.4116 — performance_rating does **not** differ significantly across salary bands.

**Monotonic trend tests** (Spearman rho of band rank vs group mean):

| Feature | rho | p |
|---|---|---|
| years_experience | -0.60 | 0.285 |
| training_hours | 0.00 | 1.000 |
| performance_rating | -0.30 | 0.624 |
| satisfaction_score | -0.80 | 0.104 |

No feature shows a statistically significant monotonic trend across bands. **salary_band is not acting as an ordinal proxy.**

**Plot**: `plots/exp02_salary_band.png`
**Stats**: `stats/exp02_salary_band.json`

---

## EXP-03: Multicollinearity Assessment

**Objective**: Detect multicollinearity among numeric predictors.

### Results

| Feature | VIF |
|---|---|
| years_experience | 1.01 |
| training_hours | 1.01 |
| team_size | 1.01 |
| projects_completed | 1.00 |
| satisfaction_score | 1.00 |
| commute_minutes | 1.01 |
| remote_pct | 1.01 |

All VIFs are near 1.0 — **no multicollinearity detected**. No pairwise |r| exceeds 0.7. Predictors are effectively independent of each other.

**Plot**: `plots/exp03_vif_heatmap.png`
**Stats**: `stats/exp03_multicollinearity.json`

---

## EXP-04: Permutation Baseline Test

**Objective**: Test whether OLS R² exceeds chance via 200 permutations.

### Results

- Observed R² = 0.0098
- Permuted R² mean = 0.0091, max = 0.0243
- Empirical p-value = 0.380

The observed R² falls **well within** the null distribution. **The model does not capture real signal** — the observed fit is indistinguishable from chance.

**Plot**: `plots/exp04_permutation.png`
**Stats**: `stats/exp04_permutation.json`

---

## Overall Conclusions

1. **No predictive signal**: None of the 7 numeric features are meaningfully correlated with `performance_rating`. The strongest individual correlation (team_size, r=-0.086) is negligibly small.
2. **No model signal**: The full OLS model achieves R²=0.0098, which does not exceed chance (permutation p=0.38).
3. **No ordinal structure**: `salary_band` does not act as an ordinal proxy for any feature.
4. **No multicollinearity**: All predictors are independent (VIFs ~1.0).
5. **Data is consistent with pure noise**: The dataset shows no evidence of any relationship between employee attributes and performance rating.

## Framing Risks Addressed

| Risk | Finding |
|---|---|
| Spurious correlations | No feature exceeds combined |r|>0.1 and p<0.05; permutation test confirms no global signal |
| Salary bands may be arbitrary | Confirmed: bands are balanced and show no ordinal structure |
| Commute_minutes right-skewed | Spearman (rank) correlation used alongside Pearson; neither shows signal |
| Synthetic data | Noted; zero nulls, clean distributions consistent with generated data |

## Artifacts Produced

- `analysis_report.md` (this file)
- `findings.json` — 5 findings
- `claim_evidence_map.json` — 5 claims
- `plots/exp01_performance_dist.png`
- `plots/exp01_correlations.png`
- `plots/exp02_salary_band.png`
- `plots/exp03_vif_heatmap.png`
- `plots/exp04_permutation.png`
- `stats/exp01_correlations.json`
- `stats/exp02_salary_band.json`
- `stats/exp03_multicollinearity.json`
- `stats/exp04_permutation.json`
