Created [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/analysis_report.md) and saved four reviewed plots in [/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/plots](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/plots).

Main result: this rental dataset is overwhelmingly size-driven. `sq_ft` alone explains about 89.7% of rent variance, the full linear model reaches about 91.0% `R^2`, bedrooms and bathrooms add a modest premium, and distance to center, year built, parking, and pet-friendliness are all near-zero after adjustment. A secondary effect is that larger units are slightly cheaper per square foot. The main caveat is heteroskedastic residuals for higher-rent units, documented in `residuals_vs_fitted.png`.

Artifacts produced:
- [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/analysis_report.md)
- [rent_vs_sqft.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/plots/rent_vs_sqft.png)
- [adjusted_effects.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/plots/adjusted_effects.png)
- [price_per_sqft_vs_sqft.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/plots/price_per_sqft_vs_sqft.png)
- [residuals_vs_fitted.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp1i3u3w6l/plots/residuals_vs_fitted.png)

Verification: all files were written successfully and the PNGs were read back for visual review before finalizing.