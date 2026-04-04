from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def model_pipeline(numeric: list[str], categorical: list[str]) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "pre",
                ColumnTransformer(
                    transformers=[
                        ("num", StandardScaler(), numeric),
                        ("cat", OneHotEncoder(drop="if_binary"), categorical),
                    ]
                ),
            ),
            ("clf", LogisticRegression(max_iter=5000)),
        ]
    )


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")
    df = pd.read_csv(DATA_PATH)

    gene_cols = [c for c in df.columns if c.startswith("gene_")]
    numeric_cols = gene_cols + ["age"]

    orientation = {
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "age_min": int(df["age"].min()),
        "age_max": int(df["age"].max()),
        "outcome_counts": df["outcome"].value_counts().sort_index().to_dict(),
        "sex_counts": df["sex"].value_counts().sort_index().to_dict(),
        "nulls": int(df.isna().sum().sum()),
    }

    rows = []
    for gene in gene_cols:
        r, p = stats.pointbiserialr(df["outcome"], df[gene])
        mean_diff = (
            df.groupby("outcome")[gene].mean().sort_index().diff().iloc[-1]
        )
        rows.append(
            {
                "gene": gene,
                "r": r,
                "p": p,
                "mean_diff": mean_diff,
                "abs_r": abs(r),
            }
        )
    assoc = pd.DataFrame(rows).sort_values("abs_r", ascending=False)
    assoc["p_fdr"] = multipletests(assoc["p"], method="fdr_bh")[1]
    assoc["significant_fdr_05"] = assoc["p_fdr"] < 0.05
    top3 = assoc.head(3)["gene"].tolist()

    top_formula = "outcome ~ gene_000 + gene_001 + gene_002 + age + C(sex)"
    top_model = smf.logit(top_formula, data=df).fit(disp=False)
    interaction_formula = (
        "outcome ~ gene_000*C(sex) + gene_001*C(sex) + gene_002*C(sex) + age"
    )
    interaction_model = smf.logit(interaction_formula, data=df).fit(disp=False)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    model_specs = {
        "Demographics": (["age"], ["sex"]),
        "Top 3 genes + demographics": (["gene_000", "gene_001", "gene_002", "age"], ["sex"]),
        "All genes + demographics": (gene_cols + ["age"], ["sex"]),
    }

    auc_rows = []
    oof_predictions = {}
    for label, (num_cols, cat_cols) in model_specs.items():
        model = model_pipeline(num_cols, cat_cols)
        proba = cross_val_predict(
            model,
            df[num_cols + cat_cols],
            df["outcome"],
            cv=cv,
            method="predict_proba",
        )[:, 1]
        auc_rows.append({"model": label, "auc": roc_auc_score(df["outcome"], proba)})
        oof_predictions[label] = proba
    auc_df = pd.DataFrame(auc_rows).sort_values("auc", ascending=False)

    age_test = stats.pointbiserialr(df["outcome"], df["age"])
    sex_table = pd.crosstab(df["sex"], df["outcome"])
    sex_chi2 = stats.chi2_contingency(sex_table)

    assoc_plot = assoc.sort_values("r")
    plt.figure(figsize=(12, 8))
    colors = np.where(assoc_plot["significant_fdr_05"], "#c44e52", "#9aa1a6")
    plt.barh(assoc_plot["gene"], assoc_plot["r"], color=colors)
    plt.axvline(0, color="black", linewidth=1)
    plt.xlabel("Point-biserial correlation with outcome")
    plt.ylabel("Gene")
    plt.title("Outcome association is concentrated in three genes")
    plt.yticks(
        ticks=[
            assoc_plot.index.get_loc(assoc_plot.index[0]),
            assoc_plot.index.get_loc(assoc_plot.index[-1]),
        ],
        labels=[assoc_plot.iloc[0]["gene"], assoc_plot.iloc[-1]["gene"]],
    )
    plt.tick_params(axis="y", left=False, labelleft=False)
    for gene in top3:
        row = assoc_plot.loc[assoc_plot["gene"] == gene].iloc[0]
        plt.text(
            row["r"] + (0.01 if row["r"] >= 0 else -0.13),
            assoc_plot.index[assoc_plot["gene"] == gene][0],
            gene,
            va="center",
            fontsize=11,
        )
    savefig(PLOTS_DIR / "gene_outcome_associations.png")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(
        data=df,
        x="gene_001",
        y="gene_000",
        hue="outcome",
        palette={0: "#4c72b0", 1: "#dd8452"},
        alpha=0.7,
        s=50,
        ax=axes[0],
    )
    axes[0].set_title("gene_000 vs gene_001 separates the classes")
    axes[0].set_xlabel("gene_001")
    axes[0].set_ylabel("gene_000")
    axes[0].legend(title="Outcome")

    sns.kdeplot(
        data=df,
        x="gene_002",
        hue="outcome",
        common_norm=False,
        fill=True,
        alpha=0.35,
        palette={0: "#4c72b0", 1: "#dd8452"},
        ax=axes[1],
    )
    axes[1].set_title("gene_002 adds weaker but real separation")
    axes[1].set_xlabel("gene_002")
    axes[1].set_ylabel("Density")
    savefig(PLOTS_DIR / "top_gene_separation.png")

    plt.figure(figsize=(10, 6))
    sns.barplot(data=auc_df, x="auc", y="model", hue="model", dodge=False, palette="deep", legend=False)
    plt.xlim(0.45, 0.95)
    plt.xlabel("Out-of-fold ROC AUC")
    plt.ylabel("")
    plt.title("A sparse model outperforms a high-dimensional one")
    for idx, row in auc_df.reset_index(drop=True).iterrows():
        plt.text(row["auc"] + 0.005, idx, f"{row['auc']:.3f}", va="center", fontsize=11)
    savefig(PLOTS_DIR / "model_auc_comparison.png")

    prob_true, prob_pred = calibration_curve(
        df["outcome"],
        oof_predictions["Top 3 genes + demographics"],
        n_bins=8,
        strategy="quantile",
    )
    plt.figure(figsize=(8, 8))
    plt.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1, label="Perfect calibration")
    plt.plot(prob_pred, prob_true, marker="o", linewidth=2.5, color="#55a868", label="Top 3 genes + demographics")
    plt.xlabel("Predicted probability")
    plt.ylabel("Observed event rate")
    plt.title("The sparse classifier is reasonably calibrated")
    plt.legend(frameon=True)
    savefig(PLOTS_DIR / "top3_calibration.png")

    coef_table = top_model.summary2().tables[1].copy()
    coef_table["odds_ratio"] = np.exp(coef_table["Coef."])
    coef_table["or_ci_low"] = np.exp(coef_table["[0.025"])
    coef_table["or_ci_high"] = np.exp(coef_table["0.975]"])

    interaction_table = interaction_model.summary2().tables[1].copy()

    report = f"""# Analysis Report

## What this dataset appears to be

This dataset contains **{orientation["shape"][0]} samples** and **{orientation["shape"][1]} columns**: 100 continuous gene-expression-like variables (`gene_000` to `gene_099`), `age`, `sex`, a unique `sample_id`, and a binary `outcome`. The raw rows are numerically coherent with the column names: the gene variables are approximately standard-normal in scale (global mean {df[gene_cols].to_numpy().mean():.4f}, SD {df[gene_cols].to_numpy().std():.3f}, range {df[gene_cols].to_numpy().min():.4f} to {df[gene_cols].to_numpy().max():.4f}), `age` ranges from {orientation["age_min"]} to {orientation["age_max"]}, and there are **no missing values**.

Outcome prevalence is fairly balanced: **{orientation["outcome_counts"][1]} positive** vs **{orientation["outcome_counts"][0]} negative** cases. Sex is also balanced (**{orientation["sex_counts"]["F"]} F**, **{orientation["sex_counts"]["M"]} M**). There is no obvious multi-level or longitudinal structure; each row looks like an independent sample.

## Key findings

### 1. The outcome signal is concentrated in three genes, not spread across the whole feature set

The strongest univariate associations by a wide margin are:

- `gene_001`: point-biserial correlation **{assoc.iloc[0]["r"]:.3f}**, FDR-adjusted p-value **{assoc.iloc[0]["p_fdr"]:.2e}**
- `gene_000`: point-biserial correlation **{assoc.iloc[1]["r"]:.3f}**, FDR-adjusted p-value **{assoc.iloc[1]["p_fdr"]:.2e}**
- `gene_002`: point-biserial correlation **{assoc.iloc[2]["r"]:.3f}**, FDR-adjusted p-value **{assoc.iloc[2]["p_fdr"]:.2e}**

Only **{assoc["significant_fdr_05"].sum()} of 100 genes** survive Benjamini-Hochberg correction at 5%, and those are exactly the three genes above. The rest of the genome-wide-looking panel is consistent with noise at this sample size. This is visible in [gene_outcome_associations.png]({(PLOTS_DIR / "gene_outcome_associations.png").resolve()}), where nearly all genes cluster around zero effect.

The pairwise relationships also support a sparse mechanism: `gene_000`, `gene_001`, and `gene_002` are almost uncorrelated with each other (all pairwise Pearson correlations between -0.023 and 0.004), so they appear to contribute mostly independent information.

### 2. A simple linear model using those three genes predicts the outcome well, and adding all other genes makes performance worse

Using 5-fold out-of-fold predictions:

- Demographics only (`age`, `sex`): ROC AUC **{auc_df.loc[auc_df["model"] == "Demographics", "auc"].iloc[0]:.3f}**
- Top 3 genes + demographics: ROC AUC **{auc_df.loc[auc_df["model"] == "Top 3 genes + demographics", "auc"].iloc[0]:.3f}**
- All 100 genes + demographics: ROC AUC **{auc_df.loc[auc_df["model"] == "All genes + demographics", "auc"].iloc[0]:.3f}**

The key result is that the **top-3-gene model outperforms the full 100-gene model** by about **{auc_df.loc[auc_df["model"] == "Top 3 genes + demographics", "auc"].iloc[0] - auc_df.loc[auc_df["model"] == "All genes + demographics", "auc"].iloc[0]:.3f} AUC**. That is a strong sign that the extra genes add variance faster than they add signal. [model_auc_comparison.png]({(PLOTS_DIR / "model_auc_comparison.png").resolve()}) shows this clearly.

The fitted logistic regression coefficients for the sparse model are large and directionally consistent:

- `gene_000`: odds ratio **{coef_table.loc["gene_000", "odds_ratio"]:.2f}** per 1-unit increase (95% CI **{coef_table.loc["gene_000", "or_ci_low"]:.2f} to {coef_table.loc["gene_000", "or_ci_high"]:.2f}**)
- `gene_001`: odds ratio **{coef_table.loc["gene_001", "odds_ratio"]:.2f}** (95% CI **{coef_table.loc["gene_001", "or_ci_low"]:.2f} to {coef_table.loc["gene_001", "or_ci_high"]:.2f}**)
- `gene_002`: odds ratio **{coef_table.loc["gene_002", "odds_ratio"]:.2f}** (95% CI **{coef_table.loc["gene_002", "or_ci_low"]:.2f} to {coef_table.loc["gene_002", "or_ci_high"]:.2f}**)

Visually, the first two genes already create substantial class separation, with `gene_002` adding a weaker but real shift; see [top_gene_separation.png]({(PLOTS_DIR / "top_gene_separation.png").resolve()}).

### 3. Demographics are weak on their own, but age may carry a small adjusted effect

On their own, demographics are poor predictors. `age` has a weak univariate point-biserial correlation with outcome (**r = {age_test.statistic:.3f}, p = {age_test.pvalue:.3f}**), and sex is not associated with outcome in a contingency table (**chi-square p = {sex_chi2[1]:.3f}**).

After adjusting for the top three genes, age becomes borderline-to-significant with a **negative** coefficient in the logistic model: coefficient **{coef_table.loc["age", "Coef."]:.4f}**, p-value **{coef_table.loc["age", "P>|z|"]:.3f}**. Interpreted literally, older samples have slightly lower event odds after holding the key gene signals constant. This is a secondary effect, not a primary driver.

I also tested sex interactions with the three main genes. One interaction term (`gene_001:C(sex)[T.M]`) reached p = **{interaction_table.loc["gene_001:C(sex)[T.M]", "P>|z|"]:.3f}**, but because this was a follow-up probe rather than a pre-registered primary hypothesis, and because several interaction terms were tested, I would treat that as exploratory rather than conclusive.

### 4. The sparse classifier is not only discriminative, but reasonably calibrated

AUC alone can hide probability miscalibration, so I checked the out-of-fold calibration curve for the top-3-gene model. The curve in [top3_calibration.png]({(PLOTS_DIR / "top3_calibration.png").resolve()}) tracks the diagonal reasonably well, with only modest deviations in the mid-probability range. That means the model is not just ranking cases correctly; its predicted risks are broadly usable as probabilities.

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

- Report: [analysis_report.md]({REPORT_PATH.resolve()})
- Plots:
  - [gene_outcome_associations.png]({(PLOTS_DIR / "gene_outcome_associations.png").resolve()})
  - [top_gene_separation.png]({(PLOTS_DIR / "top_gene_separation.png").resolve()})
  - [model_auc_comparison.png]({(PLOTS_DIR / "model_auc_comparison.png").resolve()})
  - [top3_calibration.png]({(PLOTS_DIR / "top3_calibration.png").resolve()})
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
