Analysis complete. Here's a summary of the key findings:

**Primary finding**: Square footage alone explains 90% of rent variance (r = 0.95). The best model uses just 3 features — sqft, bedrooms, bathrooms — achieving R² = 0.91 with MAE of $226.

**Three key insights**:

1. **Bedroom premium is real**: Each additional bedroom adds ~$114/month (7.3%) at the same size, highly significant (p < 0.001). More bedrooms = more functional layout = higher rent.

2. **Distance to center is irrelevant**: This was the most surprising finding. No model specification (linear, log, inverse, LOWESS, Random Forest) found any meaningful distance effect. Rent per sqft is uniform across all distance bins.

3. **Diminishing returns to size**: Elasticity of 0.80 — small units are ~17% more expensive per sqft than large ones.

**Non-factors**: Year built, parking, and pet-friendliness have zero measurable impact on rent.

The report is at `./analysis_report.md` with 8 supporting plots in `./plots/`.