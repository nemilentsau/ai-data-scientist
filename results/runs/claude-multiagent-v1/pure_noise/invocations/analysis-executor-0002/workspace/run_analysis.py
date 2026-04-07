"""
Full analysis execution for the pure_noise dataset.
Phases 1 & 3 run unconditionally; Phase 2 is conditional on signal detection.
"""

import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from itertools import combinations

warnings.filterwarnings("ignore")
np.random.seed(42)

# ── Load data ────────────────────────────────────────────────────────────
import os
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(WORKSPACE, "..", "input", "artifacts", "dataset", "dataset.csv")
os.chdir(WORKSPACE)
df = pd.read_csv(DATA)
print(f"Loaded dataset: {df.shape[0]} rows × {df.shape[1]} cols")

NUMERIC_COLS = [
    "years_experience", "training_hours", "team_size",
    "projects_completed", "satisfaction_score", "commute_minutes",
    "performance_rating", "remote_pct",
]
PREDICTOR_NUM = [c for c in NUMERIC_COLS if c != "performance_rating"]
TARGET = "performance_rating"

# ══════════════════════════════════════════════════════════════════════════
# PHASE 1 — Signal Detection
# ══════════════════════════════════════════════════════════════════════════

# ── EXP-CORR-01: Pairwise correlations ──────────────────────────────────
print("\n=== EXP-CORR-01: Pairwise correlations ===")
pearson_corr = df[NUMERIC_COLS].corr(method="pearson")
spearman_corr = df[NUMERIC_COLS].corr(method="spearman")

# Correlation values vs target
corr_vs_target = {}
for col in PREDICTOR_NUM:
    pr, _ = stats.pearsonr(df[col], df[TARGET])
    sr, _ = stats.spearmanr(df[col], df[TARGET])
    corr_vs_target[col] = {"pearson_r": round(pr, 6), "spearman_r": round(sr, 6)}
    print(f"  {col:25s}  Pearson={pr:+.4f}  Spearman={sr:+.4f}")

with open("stats/correlation_values.json", "w") as f:
    json.dump(corr_vs_target, f, indent=2)

# Heatmap
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(pearson_corr, annot=True, fmt=".3f", cmap="RdBu_r",
            center=0, vmin=-1, vmax=1, ax=ax)
ax.set_title("Pearson Correlation Matrix")
plt.tight_layout()
fig.savefig("plots/correlation_matrix.png", dpi=150)
plt.close(fig)

# ── EXP-CORR-02: P-values with Bonferroni ───────────────────────────────
print("\n=== EXP-CORR-02: Correlation p-values (Bonferroni) ===")
pairs = list(combinations(NUMERIC_COLS, 2))
n_tests = len(pairs)  # 28
pvalue_results = {}
any_significant = False

for c1, c2 in pairs:
    pr, pp = stats.pearsonr(df[c1], df[c2])
    sr, sp = stats.spearmanr(df[c1], df[c2])
    bonf_pp = min(pp * n_tests, 1.0)
    bonf_sp = min(sp * n_tests, 1.0)
    sig = bonf_pp < 0.05 or bonf_sp < 0.05
    if sig:
        any_significant = True
    pvalue_results[f"{c1} vs {c2}"] = {
        "pearson_r": round(float(pr), 6),
        "pearson_p": round(float(pp), 6),
        "spearman_r": round(float(sr), 6),
        "spearman_p": round(float(sp), 6),
        "bonferroni_pearson_p": round(float(bonf_pp), 6),
        "bonferroni_spearman_p": round(float(bonf_sp), 6),
        "significant": bool(sig),
    }

# Focus on correlations with target
target_sig = []
for col in PREDICTOR_NUM:
    key = f"{col} vs {TARGET}" if f"{col} vs {TARGET}" in pvalue_results else f"{TARGET} vs {col}"
    if key in pvalue_results and pvalue_results[key]["significant"]:
        target_sig.append(key)

print(f"  Total pairs tested: {n_tests}")
print(f"  Pairs surviving Bonferroni: {sum(1 for v in pvalue_results.values() if v['significant'])}")
print(f"  Target-related pairs surviving: {len(target_sig)}")

with open("stats/correlation_pvalues.json", "w") as f:
    json.dump(pvalue_results, f, indent=2)

# ── EXP-REG-01: OLS regression ──────────────────────────────────────────
print("\n=== EXP-REG-01: OLS regression ===")
import statsmodels.api as sm

X = pd.get_dummies(df[PREDICTOR_NUM + ["salary_band"]], columns=["salary_band"], drop_first=True, dtype=float)
X = sm.add_constant(X)
y = df[TARGET]

ols_model = sm.OLS(y, X).fit()
print(f"  R-squared:     {ols_model.rsquared:.6f}")
print(f"  Adj R-squared: {ols_model.rsquared_adj:.6f}")
print(f"  F-statistic:   {ols_model.fvalue:.4f}")
print(f"  F p-value:     {ols_model.f_pvalue:.6f}")

ols_summary_text = ols_model.summary().as_text()
with open("stats/ols_summary.txt", "w") as f:
    f.write(ols_summary_text)

ols_metrics = {
    "r_squared": round(ols_model.rsquared, 6),
    "adj_r_squared": round(ols_model.rsquared_adj, 6),
    "f_stat": round(float(ols_model.fvalue), 6),
    "f_pvalue": round(float(ols_model.f_pvalue), 6),
    "coefficients": {},
}
for name, coef, pval in zip(ols_model.params.index, ols_model.params, ols_model.pvalues):
    ols_metrics["coefficients"][name] = {
        "coef": round(float(coef), 6),
        "pvalue": round(float(pval), 6),
    }

with open("stats/ols_metrics.json", "w") as f:
    json.dump(ols_metrics, f, indent=2)

# ── EXP-PERM-01: Permutation test ───────────────────────────────────────
print("\n=== EXP-PERM-01: Permutation test (1000 shuffles) ===")
observed_r2 = ols_model.rsquared
n_perm = 1000
null_r2s = np.empty(n_perm)

for i in range(n_perm):
    y_perm = np.random.permutation(y.values)
    m = sm.OLS(y_perm, X).fit()
    null_r2s[i] = m.rsquared

empirical_p = (np.sum(null_r2s >= observed_r2) + 1) / (n_perm + 1)
null_95 = np.percentile(null_r2s, 95)

print(f"  Observed R²:       {observed_r2:.6f}")
print(f"  Null mean R²:      {null_r2s.mean():.6f}")
print(f"  Null 95th pct R²:  {null_95:.6f}")
print(f"  Empirical p-value: {empirical_p:.4f}")
print(f"  Signal detected:   {observed_r2 > null_95}")

perm_results = {
    "observed_r2": round(observed_r2, 6),
    "null_mean_r2": round(float(null_r2s.mean()), 6),
    "null_95th_pct": round(float(null_95), 6),
    "empirical_pvalue": round(float(empirical_p), 6),
    "signal_detected": bool(observed_r2 > null_95),
}

with open("stats/permutation_results.json", "w") as f:
    json.dump(perm_results, f, indent=2)

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(null_r2s, bins=40, alpha=0.7, color="steelblue", edgecolor="white", label="Null R² distribution")
ax.axvline(observed_r2, color="red", linewidth=2, linestyle="--", label=f"Observed R² = {observed_r2:.4f}")
ax.axvline(null_95, color="orange", linewidth=1.5, linestyle=":", label=f"95th percentile = {null_95:.4f}")
ax.set_xlabel("R²")
ax.set_ylabel("Count")
ax.set_title("Permutation Test: Observed R² vs Null Distribution")
ax.legend()
plt.tight_layout()
fig.savefig("plots/permutation_r2_hist.png", dpi=150)
plt.close(fig)

# ══════════════════════════════════════════════════════════════════════════
# PHASE 3 — Distribution & Data-Quality Checks (always run)
# ══════════════════════════════════════════════════════════════════════════

# ── EXP-DIST-01: Feature distributions ──────────────────────────────────
print("\n=== EXP-DIST-01: Feature distributions ===")
dist_stats = {}
fig, axes = plt.subplots(2, 4, figsize=(18, 9))
for i, col in enumerate(NUMERIC_COLS):
    ax = axes[i // 4, i % 4]
    sns.histplot(df[col], kde=True, ax=ax, color="steelblue", edgecolor="white")
    sk = float(stats.skew(df[col]))
    ku = float(stats.kurtosis(df[col]))
    mn = float(df[col].mean())
    sd = float(df[col].std())
    ax.set_title(f"{col}\nμ={mn:.1f} σ={sd:.1f}\nskew={sk:.2f} kurt={ku:.2f}", fontsize=9)
    dist_stats[col] = {
        "mean": round(mn, 4),
        "std": round(sd, 4),
        "skewness": round(sk, 4),
        "kurtosis": round(ku, 4),
    }
    print(f"  {col:25s}  skew={sk:+.3f}  kurt={ku:+.3f}")

plt.suptitle("Numeric Feature Distributions", fontsize=14, y=1.01)
plt.tight_layout()
fig.savefig("plots/distributions.png", dpi=150, bbox_inches="tight")
plt.close(fig)

with open("stats/distribution_stats.json", "w") as f:
    json.dump(dist_stats, f, indent=2)

# ── EXP-COMM-01: Commute outlier analysis ────────────────────────────────
print("\n=== EXP-COMM-01: Commute minutes outlier analysis ===")
comm = df["commute_minutes"]
q1 = float(comm.quantile(0.25))
q3 = float(comm.quantile(0.75))
iqr = q3 - q1
lower_fence = q1 - 1.5 * iqr
upper_fence = q3 + 1.5 * iqr
outliers = comm[(comm < lower_fence) | (comm > upper_fence)]
n_outliers = len(outliers)
pct_outliers = round(n_outliers / len(comm) * 100, 2)
sk = float(stats.skew(comm))

print(f"  Q1={q1}, Q3={q3}, IQR={iqr}")
print(f"  Upper fence={upper_fence}, Lower fence={lower_fence}")
print(f"  Outliers: {n_outliers} ({pct_outliers}%)")
print(f"  Skewness: {sk:.3f}")

comm_results = {
    "q1": round(q1, 2),
    "q3": round(q3, 2),
    "iqr": round(iqr, 2),
    "lower_fence": round(lower_fence, 2),
    "upper_fence": round(upper_fence, 2),
    "n_outliers": n_outliers,
    "pct_outliers": pct_outliers,
    "skewness": round(sk, 4),
}

with open("stats/commute_outliers.json", "w") as f:
    json.dump(comm_results, f, indent=2)

fig, ax = plt.subplots(figsize=(8, 4))
sns.boxplot(x=comm, ax=ax, color="steelblue")
ax.set_title(f"Commute Minutes Boxplot (outliers: {n_outliers}, skew: {sk:.2f})")
ax.set_xlabel("commute_minutes")
plt.tight_layout()
fig.savefig("plots/commute_boxplot.png", dpi=150)
plt.close(fig)

# ── EXP-INDEP-01: Chi-squared independence ──────────────────────────────
print("\n=== EXP-INDEP-01: Chi-squared independence (salary_band vs remote_pct) ===")
df["remote_pct_bin"] = pd.cut(df["remote_pct"], bins=4, labels=["Q1", "Q2", "Q3", "Q4"])
ct = pd.crosstab(df["salary_band"], df["remote_pct_bin"])
chi2, chi2_p, dof, expected = stats.chi2_contingency(ct)
print(f"  Chi² = {chi2:.4f}, p = {chi2_p:.4f}, dof = {dof}")

chi2_results = {
    "chi2_stat": round(float(chi2), 6),
    "pvalue": round(float(chi2_p), 6),
    "dof": int(dof),
    "significant": bool(chi2_p < 0.05),
    "expected_freq_table": {str(k): {str(k2): round(v2, 2) for k2, v2 in v.items()}
                            for k, v in pd.DataFrame(expected, index=ct.index, columns=ct.columns).to_dict(orient="index").items()},
}

with open("stats/chi2_independence.json", "w") as f:
    json.dump(chi2_results, f, indent=2)

df.drop(columns=["remote_pct_bin"], inplace=True)

# ── EXP-PCA-01: PCA ─────────────────────────────────────────────────────
print("\n=== EXP-PCA-01: PCA ===")
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

X_pca = StandardScaler().fit_transform(df[NUMERIC_COLS])
pca = PCA()
scores = pca.fit_transform(X_pca)
evr = pca.explained_variance_ratio_
cumvar = np.cumsum(evr)
n_features = len(NUMERIC_COLS)
uniform_baseline = 1.0 / n_features

print(f"  Explained variance ratios: {[round(x, 4) for x in evr]}")
print(f"  Cumulative (2 comp): {cumvar[1]:.4f}")
print(f"  Uniform baseline: {uniform_baseline:.4f}")

pca_results = {
    "explained_variance_ratios": [round(float(x), 6) for x in evr],
    "cumulative_variance": [round(float(x), 6) for x in cumvar],
    "uniform_baseline_per_component": round(uniform_baseline, 6),
    "first_2_cumulative": round(float(cumvar[1]), 6),
}

with open("stats/pca_variance.json", "w") as f:
    json.dump(pca_results, f, indent=2)

# Scree plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(range(1, n_features + 1), evr, color="steelblue", edgecolor="white", alpha=0.8, label="Individual")
ax.plot(range(1, n_features + 1), cumvar, "ro-", label="Cumulative")
ax.axhline(y=uniform_baseline, color="orange", linestyle="--", label=f"Uniform baseline (1/{n_features})")
ax.set_xlabel("Principal Component")
ax.set_ylabel("Explained Variance Ratio")
ax.set_title("PCA Scree Plot")
ax.legend()
ax.set_xticks(range(1, n_features + 1))
plt.tight_layout()
fig.savefig("plots/pca_screeplot.png", dpi=150)
plt.close(fig)

# Biplot
fig, ax = plt.subplots(figsize=(10, 8))
salary_map = {s: i for i, s in enumerate(sorted(df["salary_band"].unique()))}
colors = [salary_map[s] for s in df["salary_band"]]
scatter = ax.scatter(scores[:, 0], scores[:, 1], c=colors, cmap="Set1", alpha=0.5, s=15)
loadings = pca.components_[:2].T
for i, col in enumerate(NUMERIC_COLS):
    ax.annotate("", xy=(loadings[i, 0] * 4, loadings[i, 1] * 4),
                xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.5))
    ax.text(loadings[i, 0] * 4.2, loadings[i, 1] * 4.2, col, fontsize=8, fontweight="bold")
handles = [plt.Line2D([0], [0], marker="o", color="w",
           markerfacecolor=plt.cm.Set1(salary_map[s] / max(1, len(salary_map) - 1)),
           markersize=8, label=s) for s in sorted(salary_map)]
ax.legend(handles=handles, title="salary_band")
ax.set_xlabel(f"PC1 ({evr[0]:.1%})")
ax.set_ylabel(f"PC2 ({evr[1]:.1%})")
ax.set_title("PCA Biplot (PC1 vs PC2)")
plt.tight_layout()
fig.savefig("plots/pca_biplot.png", dpi=150)
plt.close(fig)

# ══════════════════════════════════════════════════════════════════════════
# DECISION GATE
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("DECISION GATE")
print("=" * 60)
signal_r2 = observed_r2 > null_95
signal_corr = len(target_sig) > 0
signal_detected = signal_r2 or signal_corr
print(f"  R² exceeds 95th percentile of null: {signal_r2}")
print(f"  Any correlation survives Bonferroni (vs target): {signal_corr}")
print(f"  → Signal detected: {signal_detected}")

# ══════════════════════════════════════════════════════════════════════════
# PHASE 2 — Deeper Analysis (conditional)
# ══════════════════════════════════════════════════════════════════════════
# Run Phase 2 regardless to provide complete artifacts, but note the gate result.

# ── EXP-SAL-01: Salary band tests ───────────────────────────────────────
print("\n=== EXP-SAL-01: Salary band feature profiles ===")
sal_test_results = {}
groups = [group[TARGET].values for _, group in df.groupby("salary_band")]
for col in NUMERIC_COLS:
    col_groups = [group[col].values for _, group in df.groupby("salary_band")]
    h_stat, p_val = stats.kruskal(*col_groups)
    bonf_p = min(p_val * len(NUMERIC_COLS), 1.0)
    sig = bonf_p < 0.05
    sal_test_results[col] = {
        "h_stat": round(float(h_stat), 4),
        "pvalue": round(float(p_val), 6),
        "bonferroni_pvalue": round(float(bonf_p), 6),
        "significant": bool(sig),
    }
    print(f"  {col:25s}  H={h_stat:8.3f}  p={p_val:.4f}  bonf_p={bonf_p:.4f}  sig={sig}")

with open("stats/salary_band_tests.json", "w") as f:
    json.dump(sal_test_results, f, indent=2)

fig, ax = plt.subplots(figsize=(8, 5))
sns.boxplot(data=df, x="salary_band", y=TARGET, order=sorted(df["salary_band"].unique()), ax=ax)
ax.set_title("Performance Rating by Salary Band")
plt.tight_layout()
fig.savefig("plots/salary_band_boxplot.png", dpi=150)
plt.close(fig)

# ── EXP-MULTI-01: VIF ───────────────────────────────────────────────────
print("\n=== EXP-MULTI-01: Variance Inflation Factors ===")
from statsmodels.stats.outliers_influence import variance_inflation_factor

X_vif = df[PREDICTOR_NUM].copy()
X_vif = sm.add_constant(X_vif)
vif_table = {}
for i, col in enumerate(X_vif.columns):
    if col == "const":
        continue
    vif_val = variance_inflation_factor(X_vif.values, i)
    vif_table[col] = round(float(vif_val), 4)
    print(f"  {col:25s}  VIF={vif_val:.4f}")

with open("stats/vif_table.json", "w") as f:
    json.dump(vif_table, f, indent=2)

# ── EXP-NONLIN-01: Scatter plots with LOWESS ────────────────────────────
print("\n=== EXP-NONLIN-01: Scatter + LOWESS ===")
fig, axes = plt.subplots(2, 4, figsize=(18, 9))
for i, col in enumerate(PREDICTOR_NUM + ["(empty)"]):
    ax = axes[i // 4, i % 4]
    if col == "(empty)":
        ax.axis("off")
        continue
    ax.scatter(df[col], df[TARGET], alpha=0.3, s=8, color="steelblue")
    try:
        lowess_result = sm.nonparametric.lowess(df[TARGET], df[col], frac=0.3)
        ax.plot(lowess_result[:, 0], lowess_result[:, 1], color="red", linewidth=2, label="LOWESS")
    except Exception:
        pass
    ax.set_xlabel(col, fontsize=9)
    ax.set_ylabel(TARGET, fontsize=9)
    ax.set_title(f"{col} vs {TARGET}", fontsize=9)

plt.suptitle("Scatter Plots with LOWESS Overlay", fontsize=14, y=1.01)
plt.tight_layout()
fig.savefig("plots/scatter_lowess.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ── EXP-FEATIMP-01: Random Forest ───────────────────────────────────────
print("\n=== EXP-FEATIMP-01: Random Forest feature importance ===")
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.model_selection import cross_val_score

X_rf = pd.get_dummies(df[PREDICTOR_NUM + ["salary_band"]], columns=["salary_band"], drop_first=True, dtype=float)
y_rf = df[TARGET]

rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
cv_scores = cross_val_score(rf, X_rf, y_rf, cv=5, scoring="r2")
print(f"  CV R² mean: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

rf.fit(X_rf, y_rf)
perm_imp = permutation_importance(rf, X_rf, y_rf, n_repeats=10, random_state=42, n_jobs=-1)

rf_results = {
    "cv_r2_mean": round(float(cv_scores.mean()), 6),
    "cv_r2_std": round(float(cv_scores.std()), 6),
    "feature_importances": {},
}
for fname, imp_mean, imp_std in zip(X_rf.columns, perm_imp.importances_mean, perm_imp.importances_std):
    rf_results["feature_importances"][fname] = {
        "importance_mean": round(float(imp_mean), 6),
        "importance_std": round(float(imp_std), 6),
    }
    print(f"  {fname:30s}  imp={imp_mean:+.4f} ± {imp_std:.4f}")

with open("stats/rf_results.json", "w") as f:
    json.dump(rf_results, f, indent=2)

# Feature importance plot
sorted_feats = sorted(rf_results["feature_importances"].items(), key=lambda x: x[1]["importance_mean"])
names = [x[0] for x in sorted_feats]
means = [x[1]["importance_mean"] for x in sorted_feats]
stds = [x[1]["importance_std"] for x in sorted_feats]

fig, ax = plt.subplots(figsize=(8, 6))
ax.barh(names, means, xerr=stds, color="steelblue", edgecolor="white", alpha=0.8)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Permutation Importance")
ax.set_title("Random Forest Permutation Feature Importances")
plt.tight_layout()
fig.savefig("plots/feature_importance.png", dpi=150)
plt.close(fig)

# ══════════════════════════════════════════════════════════════════════════
# Collect results summary
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("ALL EXPERIMENTS COMPLETE")
print("=" * 60)
print(f"Signal detected: {signal_detected}")
print(f"Observed R²: {observed_r2:.6f}")
print(f"Null 95th: {null_95:.6f}")
print(f"Permutation p: {empirical_p:.4f}")
print(f"Corr pairs surviving Bonferroni (all): {sum(1 for v in pvalue_results.values() if v['significant'])}")
print(f"Corr pairs vs target surviving: {len(target_sig)}")
print(f"CV R² (RF): {cv_scores.mean():.4f}")

# Save the decision gate result for artifact generation
gate = {
    "signal_detected": bool(signal_detected),
    "r2_exceeds_null_95th": bool(signal_r2),
    "any_corr_survives_bonferroni_vs_target": bool(signal_corr),
    "observed_r2": round(float(observed_r2), 6),
    "null_95th_pct_r2": round(float(null_95), 6),
    "permutation_pvalue": round(float(empirical_p), 4),
    "rf_cv_r2_mean": round(float(cv_scores.mean()), 6),
}
with open("stats/decision_gate.json", "w") as f:
    json.dump(gate, f, indent=2)

print("\nDone. All stats and plots saved.")
