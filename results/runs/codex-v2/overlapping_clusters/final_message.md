Wrote the report to [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/analysis_report.md) and saved four reviewed plots in `/plots`.

Main conclusion: this student dataset looks structurally plausible, but GPA is almost completely decoupled from the recorded predictors. The strongest findings are an 11.0% pile-up at perfect `4.0` GPA, near-zero correlations between GPA and all measured workload variables, an OLS model with `R^2 = 0.0037`, and negative out-of-fold `R^2` for both linear regression (`-0.015`) and random forest (`-0.162`), which means those features do not support useful GPA prediction.

Plots created:
- [01_gpa_distribution.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/01_gpa_distribution.png)
- [02_study_vs_gpa.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/02_study_vs_gpa.png)
- [03_ols_coefficients.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/03_ols_coefficients.png)
- [04_cv_predictions.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.eS14rwJ5c5/plots/04_cv_predictions.png)