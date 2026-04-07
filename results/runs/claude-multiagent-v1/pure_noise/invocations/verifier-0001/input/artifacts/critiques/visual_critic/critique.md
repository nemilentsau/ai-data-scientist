# Visual Critique

**Reviewer:** visual_critic
**Artifact reviewed:** analysis report and 9 plots in `plots/`

---

## Overall Assessment

The visualization suite is functional and mostly supports the report's conclusions. However, several charts have readability problems, one plot carries a **high risk of misleading interpretation**, and there are gaps where visual evidence is missing for claims made in prose.

**Severity scale:** CRITICAL = actively misleading; MAJOR = impairs comprehension or omits key evidence; MINOR = cosmetic or readability friction.

---

## CRITICAL Issues

### 1. Feature importance chart implies signal where none exists

**Plot:** `feature_importance.png`

The Random Forest permutation importance bar chart shows team_size, training_hours, and years_experience with large positive bars (0.13 -- 0.39) and tight error bars, visually suggesting these features matter. A reader scanning the report who lands on this chart will conclude there is meaningful signal.

The report text explains this reflects noise memorisation from an overfit model (CV R^2 = -0.086), but **the chart itself carries no visual warning**. There is no annotation, no baseline reference line, and no indication that these importances are artifacts of overfitting. The title "Random Forest Permutation Feature Importances" is neutral and does not cue the reader to distrust the values.

**Recommendation:** Add a subtitle or annotation such as "Model CV R^2 = -0.086 (no signal); importances reflect noise memorisation" directly on the plot. Alternatively, overlay a horizontal reference band showing the expected importance under permuted targets, so the reader can see these values are not distinguishable from the null.

---

## MAJOR Issues

### 2. Correlation matrix colour scale exaggerates near-zero values

**Plot:** `correlation_matrix.png`

The diverging colour ramp spans [-1, +1], which is correct in principle. However, because every off-diagonal value falls in [-0.086, +0.046], the entire heatmap appears uniformly white/near-white. This makes it impossible to visually compare the relative magnitudes of the tiny correlations.

There are two problems here:
- The chart is functionally uninformative beyond "everything is near zero" -- which a single sentence could convey.
- The numeric annotations are small and hard to read against the near-white background.

**Recommendation:** If the goal is to show "everything is near zero," annotate the plot with a note like "max |r| = 0.086" and consider tightening the colour scale to [-0.15, +0.15] so the minor variation is at least visible. If the goal is to show the full [-1, +1] range for context, that is fine but then the plot's purpose is purely confirmatory and should be labelled as such.

### 3. Distribution panel (`distributions.png`) is too small to read

**Plot:** `distributions.png`

The 2x4 grid of histograms with KDE overlays is rendered at a resolution where axis labels, tick marks, and the annotation text (mu, sigma, skew, kurtosis) are barely legible. The subplot titles and statistics text blur together at the rendered size.

Key details lost at this resolution:
- The commute_minutes subplot's skew and long tail -- the most important distributional finding -- is hard to distinguish from a quick glance.
- The difference between the uniform-like shapes (years_experience, team_size, satisfaction_score, remote_pct) and the normal-shaped performance_rating is not visually emphasised.

**Recommendation:** Render this figure at a larger size (e.g., 16x10 inches) or split into two rows of 4. Increase font size for the annotation text. Consider highlighting the commute_minutes panel (e.g., coloured border) since it is the only one with a noteworthy finding.

### 4. Scatter + LOWESS panel (`scatter_lowess.png`) is illegible

**Plot:** `scatter_lowess.png`

This is the worst readability offender. The 2x4 grid of scatter plots is rendered at a size where:
- Axis labels are unreadable.
- Individual data points blur into a solid mass.
- The LOWESS curves (red lines) -- which are the entire point of the chart -- are difficult to trace against the dense point cloud.
- The remote_pct subplot shows severe discrete-value banding (vertical stripes at 0, ~20, ~40, ~60, ~80, 100) that visually dominates and obscures the LOWESS line.

Since the LOWESS flatness is cited as evidence for "no non-linear patterns" (EXP-NONLIN-01), this plot is a key piece of evidence that is currently unreadable.

**Recommendation:** Render at a much larger size. Reduce point alpha to 0.15--0.2 and use smaller marker sizes so the LOWESS curve stands out. For remote_pct, consider jittering the x-axis to reduce overplotting. Add a horizontal reference line at y = mean(performance_rating) so the reader can visually confirm the LOWESS stays flat relative to the mean.

### 5. No visual evidence for the OLS regression (EXP-REG-01)

The report presents detailed OLS results (R^2, adjusted R^2, F-stat, coefficient table), but there is no residual plot, Q-Q plot, or fitted-vs-actual plot. For a "pure noise" conclusion, a residual plot showing no structure would be highly confirmatory visual evidence.

**Recommendation:** Add a residuals-vs-fitted scatter plot. In a noise dataset it should look like a uniform blob, which would visually reinforce the conclusion more effectively than the numeric table alone.

### 6. No visual for the chi-squared independence test (EXP-INDEP-01)

The chi-squared test of salary_band vs binned remote_pct (p = 0.978) has no accompanying visualisation. A mosaic plot or grouped bar chart of observed vs expected counts would let the reader see the independence visually rather than relying solely on a p-value.

---

## MINOR Issues

### 7. PCA biplot loading arrows are hard to distinguish

**Plot:** `pca_biplot.png`

The biplot correctly shows both scores and loadings, and the salary_band colour encoding is a nice touch. However:
- Several loading labels overlap (years_experience, commute_minutes, satisfaction_score cluster near the centre).
- The arrow lengths are similar (as expected for independent features), making it hard to distinguish which direction each arrow points.
- The salary_band colour palette (red, green, orange, olive, grey) includes green and olive tones that are difficult to distinguish for colour-blind readers.

**Recommendation:** Use a colour-blind-safe palette (e.g., ColorBrewer Set2 or Okabe-Ito). Adjust label positions to reduce overlap or use leader lines.

### 8. PCA scree plot bar heights are visually deceptive

**Plot:** `pca_screeplot.png`

The y-axis starts at 0.0 and goes to 1.0 (to accommodate the cumulative line), which compresses the individual-variance bars into a narrow band at the bottom. The visual difference between 11% and 15% is invisible at this scale. The uniform baseline dashed line is a good addition, but the bars look identical to the naked eye.

**Recommendation:** Use a dual-axis or inset plot: one axis scaled to [0, 0.2] for the bars, and a secondary axis for the cumulative line. This would let the reader see whether any component stands out above the baseline.

### 9. Salary band boxplot lacks group sizes

**Plot:** `salary_band_boxplot.png`

The boxplot shows performance_rating by salary_band and visually confirms identical distributions. However, there is no indication of group sizes. If L1 has 120 observations and L3 has 80, the visual spread could be misleading. The report mentions L5 has 170 observations but does not annotate the plot.

**Recommendation:** Add n= labels below each boxplot or use a notched/letter-value plot that encodes sample size.

### 10. Commute boxplot is horizontal without clear justification

**Plot:** `commute_boxplot.png`

The horizontal orientation works, but this is the only horizontal chart in the set. All other plots use standard x-y orientation. The inconsistency is minor but adds a small amount of cognitive friction.

The outlier count and skewness are helpfully noted in the title, which is good practice.

---

## Missing Visual Evidence Summary

| Claim in report | Visual evidence present? | Gap |
|---|---|---|
| No pairwise correlations survive Bonferroni | Correlation matrix (partial) | Matrix shows raw r, not corrected p-values |
| OLS R^2 indistinguishable from null | Permutation histogram (good) | No residual plot |
| LOWESS trends are flat | Scatter+LOWESS panel | Illegible at rendered size |
| No salary_band group differences | Salary boxplot (adequate) | Only shows target; report claims all 8 features are equal |
| salary_band vs remote_pct independent | None | No mosaic/contingency plot |
| VIF all near 1.0 | None | No visual; table-only is acceptable here |

---

## What Works Well

- **Permutation test histogram** (`permutation_r2_hist.png`): Clear, well-labelled, with both the observed value and 95th-percentile threshold annotated. This is the strongest plot in the set and effectively communicates the core "no signal" finding.
- **Commute boxplot** (`commute_boxplot.png`): Clean, with outlier count and skewness in the title. Communicates the one distributional anomaly well.
- **PCA scree plot** (`pca_screeplot.png`): The uniform baseline overlay is a smart design choice that immediately shows the variance ratios are unremarkable. The bar-plus-cumulative-line encoding is standard and readable (even if the scale compression noted above reduces its power).
- **Salary band boxplot** (`salary_band_boxplot.png`): Effectively shows identical distributions. The visual equivalence is the message, and it comes through clearly.

---

## Priority Ranking

1. **CRITICAL:** Annotate or redesign `feature_importance.png` to prevent misinterpretation of noise as signal.
2. **MAJOR:** Increase size and legibility of `scatter_lowess.png` -- it is currently non-functional as evidence.
3. **MAJOR:** Increase size and legibility of `distributions.png`.
4. **MAJOR:** Add a residual plot for OLS to provide visual confirmation of the no-signal conclusion.
5. **MAJOR:** Tighten the correlation matrix colour scale or add a max-|r| annotation.
6. **MINOR:** Fix PCA biplot colour palette for accessibility and reduce label overlap.
7. **MINOR:** Improve scree plot dual-axis scaling.
8. **MINOR:** Add group-size annotations to salary band boxplot.
