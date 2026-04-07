`critique.md` has been written. Summary of findings:

- **1 CRITICAL issue:** The feature importance chart visually implies signal exists (large bars, tight error bars) when the underlying model has negative CV R^2. No annotation warns the reader -- this is the most dangerous chart in the set.
- **5 MAJOR issues:** The scatter+LOWESS and distributions panels are too small to read; the correlation matrix colour scale makes near-zero values indistinguishable; no residual plot exists for OLS; no visual for the chi-squared independence test.
- **4 MINOR issues:** PCA biplot has overlapping labels and a non-colourblind-safe palette; scree plot y-axis compression hides bar differences; salary boxplot lacks group sizes; inconsistent chart orientation.

The permutation test histogram is the strongest plot -- well-annotated with clear reference lines. The commute boxplot is also effective. The highest-priority fix is preventing the feature importance chart from being misread as evidence of signal.