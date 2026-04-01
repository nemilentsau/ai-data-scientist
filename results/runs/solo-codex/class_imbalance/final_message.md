I analyzed the dataset, generated the plots, and wrote the report to [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.qkrHZ9mEcI/analysis_report.md). The full workflow is reproducible in [analyze_dataset.py](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.qkrHZ9mEcI/analyze_dataset.py), and all PNGs are in [plots](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.qkrHZ9mEcI/plots).

Main findings: the data are clean on missingness and duplicates, but `amount_usd` and `distance_from_home_km` are heavily right-skewed with meaningful outliers. Fraud is concentrated in far-from-home, higher-amount, and late-night transactions; `card_age_months`, `merchant_category`, and `is_international` add much less signal.

I compared a transformed logistic regression against a random forest. The random forest performed better and matched the data structure better:
- Cross-validated ROC AUC: logistic `0.877`, random forest `0.890`
- Cross-validated PR AUC: logistic `0.488`, random forest `0.548`
- Test ROC AUC: logistic `0.876`, random forest `0.892`
- Test PR AUC: logistic `0.500`, random forest `0.561`

I also checked assumptions rigorously. Multicollinearity was acceptable, but the logistic model still showed residual nonlinearity for transaction amount and poor calibration on the holdout split, so it is best treated as an interpretable baseline rather than the final model.