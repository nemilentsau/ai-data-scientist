The analysis is complete in [analysis_report.md](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/analysis_report.md).

Main result: `price_usd` is driven primarily by `sq_ft`, with `year_built` adding a meaningful secondary premium. A two-feature linear model (`sq_ft + year_built`) achieved essentially the same 10-fold CV error as the full model, while `num_rooms`, `lot_size_acres`, `garage_spaces`, `has_pool`, and `neighborhood` added little incremental signal once size and age were controlled for.

Saved plots are in [/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots):
[price_vs_sqft.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots/price_vs_sqft.png),
[year_built_partial_effect.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots/year_built_partial_effect.png),
[predictor_correlation_heatmap.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots/predictor_correlation_heatmap.png),
[neighborhood_residuals.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots/neighborhood_residuals.png),
and [cv_model_comparison.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.0xDaUqRyBR/plots/cv_model_comparison.png).