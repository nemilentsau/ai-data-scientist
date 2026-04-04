Completed the analysis and wrote the report to [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.kcLVEz3BLd/analysis_report.md).

Saved and reviewed these plots in [plots/](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.kcLVEz3BLd/plots):
- [rpm_vs_fuel_quadratic.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.kcLVEz3BLd/plots/rpm_vs_fuel_quadratic.png)
- [octane_residual_boxplot.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.kcLVEz3BLd/plots/octane_residual_boxplot.png)
- [age_group_rpm_curves.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.kcLVEz3BLd/plots/age_group_rpm_curves.png)
- [quadratic_model_diagnostics.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.kcLVEz3BLd/plots/quadratic_model_diagnostics.png)

Headline finding: fuel consumption is almost entirely explained by a nonlinear RPM curve. The quadratic model reached `R^2 = 0.9955` with 5-fold CV MAE `1.18 L/h`, while octane rating and vehicle age showed no meaningful independent effect after controlling for RPM and the other measured conditions.