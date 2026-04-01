Created the full analysis deliverables and validated them by running `python analyze_dataset.py`.

The main outputs are [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.KmnJ9PlP3p/analysis_report.md), the reproducible script [analyze_dataset.py](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.KmnJ9PlP3p/analyze_dataset.py), and the PNG figures in [plots](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.KmnJ9PlP3p/plots).

The strongest findings are:
- The raw file has no missing values, but `order_total_usd` fails a basic accounting consistency check badly, including 28 negative totals and discrepancies up to about `$19,867.89`.
- `returned` is rare at `8.75%`, and neither segment comparisons nor univariate tests show meaningful separation.
- Cross-validated models stayed near chance: logistic regression ROC AUC about `0.478`, random forest about `0.509`, so the dataset does not support a useful return-prediction model in its current form.

Verification: `python analyze_dataset.py` completed successfully and regenerated the report and all plots.