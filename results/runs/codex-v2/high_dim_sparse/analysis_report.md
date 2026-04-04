# Analysis Report

## What this dataset appears to be

This dataset contains **600 samples** and **104 columns**: 100 continuous gene-expression-like variables (`gene_000` to `gene_099`), `age`, `sex`, a unique `sample_id`, and a binary `outcome`. The raw rows are numerically coherent with the column names: the gene variables are approximately standard-normal in scale (global mean -0.0001, SD 1.002, range -4.4656 to 4.4791), `age` ranges from 20 to 85, and there are **no missing values**.

Outcome prevalence is fairly balanced: **315 positive** vs **285 negative** cases. Sex is also balanced (**295 F**, **305 M**). There is no obvious multi-level or longitudinal structure; each row looks like an independent sample.

## Key findings

### 1. The outcome signal is concentrated in three genes, not spread across the whole feature set

The strongest univariate associations by a wide margin are:

- `gene_001`: point-biserial correlation **-0.452**, FDR-adjusted p-value **1.69e-29**
- `gene_000`: point-biserial correlation **0.407**, FDR-adjusted p-value **1.28e-23**
- `gene_002`: point-biserial correlation **0.244**, FDR-adjusted p-value **4.74e-08**

Only **3 of 100 genes** survive Benjamini-Hochberg correction at 5%, and those are exactly the three genes above. The rest of the genome-wide-looking panel is consistent with noise at this sample size. This is visible in [gene_outcome_associations.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/gene_outcome_associations.png), where nearly all genes cluster around zero effect.

The pairwise relationships also support a sparse mechanism: `gene_000`, `gene_001`, and `gene_002` are almost uncorrelated with each other (all pairwise Pearson correlations between -0.023 and 0.004), so they appear to contribute mostly independent information.

### 2. A simple linear model using those three genes predicts the outcome well, and adding all other genes makes performance worse

Using 5-fold out-of-fold predictions:

- Demographics only (`age`, `sex`): ROC AUC **0.529**
- Top 3 genes + demographics: ROC AUC **0.900**
- All 100 genes + demographics: ROC AUC **0.853**

The key result is that the **top-3-gene model outperforms the full 100-gene model** by about **0.048 AUC**. That is a strong sign that the extra genes add variance faster than they add signal. [model_auc_comparison.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/model_auc_comparison.png) shows this clearly.

The fitted logistic regression coefficients for the sparse model are large and directionally consistent:

- `gene_000`: odds ratio **5.92** per 1-unit increase (95% CI **4.20 to 8.35**)
- `gene_001`: odds ratio **0.14** (95% CI **0.09 to 0.20**)
- `gene_002`: odds ratio **2.75** (95% CI **2.13 to 3.56**)

Visually, the first two genes already create substantial class separation, with `gene_002` adding a weaker but real shift; see [top_gene_separation.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/top_gene_separation.png).

### 3. Demographics are weak on their own, but age may carry a small adjusted effect

On their own, demographics are poor predictors. `age` has a weak univariate point-biserial correlation with outcome (**r = -0.068, p = 0.095**), and sex is not associated with outcome in a contingency table (**chi-square p = 0.919**).

After adjusting for the top three genes, age becomes borderline-to-significant with a **negative** coefficient in the logistic model: coefficient **-0.0188**, p-value **0.057**. Interpreted literally, older samples have slightly lower event odds after holding the key gene signals constant. This is a secondary effect, not a primary driver.

I also tested sex interactions with the three main genes. One interaction term (`gene_001:C(sex)[T.M]`) reached p = **0.007**, but because this was a follow-up probe rather than a pre-registered primary hypothesis, and because several interaction terms were tested, I would treat that as exploratory rather than conclusive.

### 4. The sparse classifier is not only discriminative, but reasonably calibrated

AUC alone can hide probability miscalibration, so I checked the out-of-fold calibration curve for the top-3-gene model. The curve in [top3_calibration.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/top3_calibration.png) tracks the diagonal reasonably well, with only modest deviations in the mid-probability range. That means the model is not just ranking cases correctly; its predicted risks are broadly usable as probabilities.

## Interpretation

The dataset behaves like a binary classification problem generated primarily by a **small additive expression signature**, dominated by `gene_000`, `gene_001`, and `gene_002`. The practical implication is that this is **not** a case where high-dimensional modeling or broad feature inclusion helps. If the analytical goal is prediction, a sparse, interpretable model is preferable. If the scientific goal is explanation, these three genes deserve almost all the follow-up attention.

The age effect is weak enough that I would not center the narrative on it. A more defensible interpretation is that age might modulate baseline risk slightly once expression is accounted for, but the evidence is much thinner than for the three-gene signature.

## Limitations and self-critique

- The dataset looks synthetic or heavily simulated. The standardized, near-Gaussian gene distributions, clean IDs, and absence of missingness are unusual for raw biological data. That does not invalidate the analysis, but it limits real-world generalization.
- I assumed each row is independent. If there is hidden batch structure, family structure, or repeated measures not encoded in the file, the p-values would be anti-conservative.
- The superiority of the top-3-gene model over the full model was established with 5-fold cross-validation, which is appropriate, but I did not run nested hyperparameter tuning or repeated resampling. The exact AUC values could move a bit under different splits.
- The apparent sex interaction for `gene_001` could be a false positive from multiple exploratory interaction tests. I tested it because the main signal suggested checking for heterogeneity, not because there was external prior evidence for it.
- Calibration was checked visually, not with a formal score decomposition such as Brier-loss calibration terms. The curve looks acceptable, but that is still a qualitative assessment.
- Correlation is not causation. These findings support association and predictive usefulness, not causal claims about what drives the outcome biologically.

## Files produced

- Report: [analysis_report.md](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/analysis_report.md)
- Plots:
  - [gene_outcome_associations.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/gene_outcome_associations.png)
  - [top_gene_separation.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/top_gene_separation.png)
  - [model_auc_comparison.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/model_auc_comparison.png)
  - [top3_calibration.png](/private/var/folders/j_/dt6mk_nd7tbfpyx2v5z_lv6c0000gn/T/tmp.XsBTO6ktdZ/plots/top3_calibration.png)
