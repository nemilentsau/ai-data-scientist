All 10 plots are referenced in the report. Here's a summary of the corrections made:

**Issues identified and fixed:**

1. **Plot 04 title bug**: Fixed the code artifact (`n=(~floor_mask).sum()`) to show the actual count (`n=1281`).

2. **"Monotonic" time trend overstated**: Changed Finding 3 title and text to "strong but non-monotonic" and noted the 04-12h plateau (25.2% vs 24.2%). Added the critical caveat that the marginal time effect is misleading because it's entirely driven by high-CS sessions.

3. **GB feature importance artifact unexplained**: Added a new "Feature importance: a cautionary note" section documenting that impurity-based importance ranks budget second (0.20), but held-out permutation importance is -0.003. Removing budget from GB actually improves AUC (0.679 to 0.686).

4. **Crossing interaction understated**: Upgraded the interaction finding from "synergistic" to "crossing interaction" with specific evidence: at low CS, Spearman rho = -0.025 (flat/slightly declining); at high CS, rho = 0.330 (strongly positive). Added model-vs-observed comparison table showing the logistic model underpredicts the extremes by up to 13 percentage points.

5. **New diagnostic plot** (`plots/10_corrective_diagnostics.png`): 6-panel figure showing residual heatmap, crossing curves with CIs, impurity vs permutation importance, low-vs-high CS error bars, cell-level calibration, and super-additive effect map.

6. **Zero-visit finding sharpened**: Updated from "consistent with sampling variability" to noting the marginal chi-squared p = 0.091 and the possibility of a real first-visit disadvantage.