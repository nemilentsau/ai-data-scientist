The analysis is complete in [analysis_report.md](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/analysis_report.md), with plots saved in `/plots`.

The main result is that the dataset’s signal is highly sparse: `gene_000`, `gene_001`, and `gene_002` are the only genes that survive FDR correction, and a logistic model using just those three genes plus demographics achieves out-of-fold ROC AUC `0.900`, outperforming the full 100-gene model at `0.853`. `Age` and `sex` are weak overall; age shows only a small adjusted effect, and a possible sex interaction for `gene_001` is reported as exploratory rather than conclusive.

I generated and reviewed these plots:
- [gene_outcome_associations.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/gene_outcome_associations.png)
- [top_gene_separation.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/top_gene_separation.png)
- [model_auc_comparison.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/model_auc_comparison.png)
- [top3_calibration.png](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/top3_calibration.png)

The workflow is reproducible via [run_analysis.py](/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/run_analysis.py).