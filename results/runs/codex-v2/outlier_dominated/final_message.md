Created [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/analysis_report.md) and four PNG plots in [/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/plots](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/plots).

The main findings are:
- `order_total_usd` has 28 negative rows that behave like anomalies, not normal returns.
- After excluding those anomalies, customer segment has little explanatory power for spend once quantity and unit price are included.
- Returns are weakly structured in the available fields; a 5-fold cross-validated logistic model reached ROC AUC 0.475, and only a modest, non-significant increase appears in the highest price quintile.
- Recorded totals move with discounted subtotal, but not in a clean accounting way, which limits reconciliation-style interpretation.

I also saved the reproducible script at [run_analysis.py](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.Z3Ma1YHn9a/run_analysis.py).