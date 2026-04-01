import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. LOAD AND INSPECT
# ============================================================
df = pd.read_csv('dataset.csv')
print("=" * 60)
print("1. DATA INSPECTION")
print("=" * 60)
print(f"Shape: {df.shape}")
print(f"\nColumn types:\n{df.dtypes.value_counts()}")
print(f"\nFirst few columns: {list(df.columns[:5])} ... {list(df.columns[-5:])}")
print(f"\nNull counts:\n{df.isnull().sum().sum()} total nulls")
print(f"\nNull per column (if any):")
nulls = df.isnull().sum()
print(nulls[nulls > 0] if nulls.sum() > 0 else "No nulls found")

print(f"\nDuplicate rows: {df.duplicated().sum()}")
print(f"Duplicate sample_ids: {df['sample_id'].duplicated().sum()}")

gene_cols = [c for c in df.columns if c.startswith('gene_')]
print(f"\nGene columns: {len(gene_cols)}")
print(f"\nOutcome distribution:\n{df['outcome'].value_counts()}")
print(f"Outcome balance: {df['outcome'].mean():.3f}")

print(f"\nSex distribution:\n{df['sex'].value_counts()}")

print(f"\nAge stats:\n{df['age'].describe()}")

print(f"\nGene expression summary (across all gene columns):")
gene_data = df[gene_cols]
print(f"  Overall mean: {gene_data.values.mean():.4f}")
print(f"  Overall std:  {gene_data.values.std():.4f}")
print(f"  Overall min:  {gene_data.values.min():.4f}")
print(f"  Overall max:  {gene_data.values.max():.4f}")

# Check for constant or near-constant columns
gene_stds = gene_data.std()
print(f"\n  Gene std range: [{gene_stds.min():.4f}, {gene_stds.max():.4f}]")
low_var = gene_stds[gene_stds < 0.1]
print(f"  Genes with std < 0.1: {len(low_var)}")

# Check for outlier samples
sample_means = gene_data.mean(axis=1)
sample_stds = gene_data.std(axis=1)
print(f"\n  Per-sample mean range: [{sample_means.min():.4f}, {sample_means.max():.4f}]")
print(f"  Per-sample std range:  [{sample_stds.min():.4f}, {sample_stds.max():.4f}]")

# ============================================================
# 2. EXPLORATORY DATA ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("2. EXPLORATORY DATA ANALYSIS")
print("=" * 60)

# --- Plot 1: Outcome distribution ---
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

df['outcome'].value_counts().plot(kind='bar', ax=axes[0], color=['steelblue', 'coral'])
axes[0].set_title('Outcome Distribution')
axes[0].set_xlabel('Outcome')
axes[0].set_ylabel('Count')
axes[0].set_xticklabels(['0', '1'], rotation=0)

# --- Age distribution by outcome ---
for outcome in [0, 1]:
    subset = df[df['outcome'] == outcome]['age']
    axes[1].hist(subset, bins=20, alpha=0.6, label=f'Outcome {outcome}', edgecolor='black')
axes[1].set_title('Age Distribution by Outcome')
axes[1].set_xlabel('Age')
axes[1].set_ylabel('Count')
axes[1].legend()

# --- Sex vs Outcome ---
ct = pd.crosstab(df['sex'], df['outcome'])
ct.plot(kind='bar', ax=axes[2], color=['steelblue', 'coral'])
axes[2].set_title('Sex vs Outcome')
axes[2].set_xlabel('Sex')
axes[2].set_ylabel('Count')
axes[2].set_xticklabels(['F', 'M'], rotation=0)
axes[2].legend(title='Outcome')

plt.tight_layout()
plt.savefig('plots/01_basic_distributions.png', dpi=150, bbox_inches='tight')
plt.close()

# --- Statistical tests on demographics ---
print("\nAge by outcome:")
for outcome in [0, 1]:
    ages = df[df['outcome'] == outcome]['age']
    print(f"  Outcome {outcome}: mean={ages.mean():.1f}, median={ages.median():.1f}, std={ages.std():.1f}")

t_stat, p_val = stats.ttest_ind(
    df[df['outcome'] == 0]['age'],
    df[df['outcome'] == 1]['age']
)
print(f"  t-test: t={t_stat:.3f}, p={p_val:.4f}")

u_stat, u_p = stats.mannwhitneyu(
    df[df['outcome'] == 0]['age'],
    df[df['outcome'] == 1]['age'],
    alternative='two-sided'
)
print(f"  Mann-Whitney U: U={u_stat:.1f}, p={u_p:.4f}")

print("\nSex vs Outcome (chi-squared):")
chi2, chi_p, dof, expected = stats.chi2_contingency(ct)
print(f"  chi2={chi2:.3f}, p={chi_p:.4f}, dof={dof}")

# --- Plot 2: Gene expression heatmap (correlation among top variable genes) ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Correlation of top-20 most variable genes
top_var_genes = gene_data.std().nlargest(20).index.tolist()
corr_top = df[top_var_genes].corr()
sns.heatmap(corr_top, cmap='RdBu_r', center=0, ax=axes[0],
            xticklabels=True, yticklabels=True, vmin=-1, vmax=1)
axes[0].set_title('Correlation: Top 20 Most Variable Genes')
axes[0].tick_params(labelsize=7)

# Overall gene correlation distribution
all_corr = gene_data.corr()
upper_tri = all_corr.where(np.triu(np.ones(all_corr.shape), k=1).astype(bool))
corr_vals = upper_tri.stack().values
axes[1].hist(corr_vals, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
axes[1].axvline(x=0, color='red', linestyle='--')
axes[1].set_title('Distribution of Pairwise Gene Correlations')
axes[1].set_xlabel('Correlation')
axes[1].set_ylabel('Count')

plt.tight_layout()
plt.savefig('plots/02_gene_correlations.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"\nPairwise gene correlation stats:")
print(f"  Mean: {corr_vals.mean():.4f}")
print(f"  Std:  {corr_vals.std():.4f}")
print(f"  Max:  {corr_vals.max():.4f}")
print(f"  Min:  {corr_vals.min():.4f}")
print(f"  |corr| > 0.3: {(np.abs(corr_vals) > 0.3).sum()} pairs")
print(f"  |corr| > 0.5: {(np.abs(corr_vals) > 0.5).sum()} pairs")

# --- Plot 3: Univariate association of each gene with outcome ---
from scipy.stats import mannwhitneyu

pvals = []
effect_sizes = []
for gene in gene_cols:
    g0 = df[df['outcome'] == 0][gene]
    g1 = df[df['outcome'] == 1][gene]
    _, p = mannwhitneyu(g0, g1, alternative='two-sided')
    # Cohen's d
    pooled_std = np.sqrt((g0.std()**2 + g1.std()**2) / 2)
    d = (g1.mean() - g0.mean()) / pooled_std if pooled_std > 0 else 0
    pvals.append(p)
    effect_sizes.append(d)

univariate_df = pd.DataFrame({
    'gene': gene_cols,
    'p_value': pvals,
    'cohens_d': effect_sizes
})
univariate_df['neg_log10_p'] = -np.log10(univariate_df['p_value'])

# Bonferroni and BH correction
from statsmodels.stats.multitest import multipletests
reject_bonf, pvals_bonf, _, _ = multipletests(univariate_df['p_value'], method='bonferroni')
reject_bh, pvals_bh, _, _ = multipletests(univariate_df['p_value'], method='fdr_bh')
univariate_df['p_bonferroni'] = pvals_bonf
univariate_df['p_bh'] = pvals_bh
univariate_df['sig_bonferroni'] = reject_bonf
univariate_df['sig_bh'] = reject_bh

print(f"\nUnivariate gene-outcome associations:")
print(f"  Genes with raw p < 0.05: {(univariate_df['p_value'] < 0.05).sum()}")
print(f"  Genes significant after Bonferroni: {univariate_df['sig_bonferroni'].sum()}")
print(f"  Genes significant after BH (FDR): {univariate_df['sig_bh'].sum()}")

sig_genes = univariate_df.sort_values('p_value').head(20)
print(f"\nTop 20 genes by association with outcome:")
print(sig_genes[['gene', 'p_value', 'cohens_d', 'p_bh', 'sig_bh']].to_string(index=False))

# Volcano plot
fig, ax = plt.subplots(figsize=(10, 6))
colors = ['red' if sig else 'grey' for sig in univariate_df['sig_bh']]
ax.scatter(univariate_df['cohens_d'], univariate_df['neg_log10_p'], c=colors, alpha=0.6, s=30)
ax.axhline(y=-np.log10(0.05), color='blue', linestyle='--', label='p=0.05')
bonf_line = -np.log10(0.05 / len(gene_cols))
ax.axhline(y=bonf_line, color='red', linestyle='--', label=f'Bonferroni (p={0.05/len(gene_cols):.4f})')
ax.set_xlabel("Cohen's d (Outcome 1 - Outcome 0)")
ax.set_ylabel('-log10(p-value)')
ax.set_title('Volcano Plot: Gene-Outcome Associations')
ax.legend()

# Label top genes
for _, row in univariate_df.nlargest(5, 'neg_log10_p').iterrows():
    ax.annotate(row['gene'], (row['cohens_d'], row['neg_log10_p']),
                fontsize=8, ha='center', va='bottom')

plt.tight_layout()
plt.savefig('plots/03_volcano_plot.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# 3. PCA / DIMENSIONALITY REDUCTION
# ============================================================
print("\n" + "=" * 60)
print("3. DIMENSIONALITY REDUCTION (PCA)")
print("=" * 60)

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

scaler = StandardScaler()
X_genes_scaled = scaler.fit_transform(df[gene_cols])

pca = PCA(n_components=min(50, len(gene_cols)))
X_pca = pca.fit_transform(X_genes_scaled)

print(f"Variance explained by first 10 PCs: {pca.explained_variance_ratio_[:10].cumsum()[-1]:.3f}")
print(f"Variance explained by first 20 PCs: {pca.explained_variance_ratio_[:20].cumsum()[-1]:.3f}")
print(f"Variance explained by first 50 PCs: {pca.explained_variance_ratio_[:50].cumsum()[-1]:.3f}")
print(f"PCs needed for 90% variance: {np.argmax(pca.explained_variance_ratio_.cumsum() >= 0.90) + 1}")
print(f"PCs needed for 95% variance: {np.argmax(pca.explained_variance_ratio_.cumsum() >= 0.95) + 1}")

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Scree plot
axes[0].bar(range(1, 21), pca.explained_variance_ratio_[:20], color='steelblue', alpha=0.7)
axes[0].plot(range(1, 21), pca.explained_variance_ratio_[:20].cumsum(), 'ro-', markersize=4)
axes[0].axhline(y=0.90, color='grey', linestyle='--', alpha=0.5, label='90%')
axes[0].set_xlabel('Principal Component')
axes[0].set_ylabel('Variance Explained')
axes[0].set_title('PCA Scree Plot')
axes[0].legend()

# PC1 vs PC2 colored by outcome
for outcome, color, label in [(0, 'steelblue', 'Outcome 0'), (1, 'coral', 'Outcome 1')]:
    mask = df['outcome'] == outcome
    axes[1].scatter(X_pca[mask, 0], X_pca[mask, 1], c=color, label=label, alpha=0.5, s=20)
axes[1].set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
axes[1].set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
axes[1].set_title('PCA: PC1 vs PC2 by Outcome')
axes[1].legend()

# PC1 vs PC2 colored by age
sc = axes[2].scatter(X_pca[:, 0], X_pca[:, 1], c=df['age'], cmap='viridis', alpha=0.5, s=20)
plt.colorbar(sc, ax=axes[2], label='Age')
axes[2].set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
axes[2].set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
axes[2].set_title('PCA: PC1 vs PC2 by Age')

plt.tight_layout()
plt.savefig('plots/04_pca.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# 4. MODELING
# ============================================================
print("\n" + "=" * 60)
print("4. PREDICTIVE MODELING")
print("=" * 60)

from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (classification_report, roc_auc_score, roc_curve,
                             confusion_matrix, brier_score_loss, log_loss)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

# Prepare features
le = LabelEncoder()
df['sex_encoded'] = le.fit_transform(df['sex'])

feature_cols = gene_cols + ['age', 'sex_encoded']
X = df[feature_cols].values
y = df['outcome'].values

print(f"Feature matrix: {X.shape}")
print(f"Class balance: {y.mean():.3f}")

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

# --- Model 1: L1-regularized logistic regression (sparse, handles high-dim) ---
print("\n--- L1 Logistic Regression (Lasso) ---")
pipe_l1 = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression(penalty='l1', solver='saga', C=0.1, max_iter=5000, random_state=42))
])

scores_l1 = cross_val_score(pipe_l1, X, y, cv=cv, scoring='roc_auc')
print(f"AUC (10-fold CV): {scores_l1.mean():.3f} +/- {scores_l1.std():.3f}")

y_prob_l1 = cross_val_predict(pipe_l1, X, y, cv=cv, method='predict_proba')[:, 1]
y_pred_l1 = (y_prob_l1 >= 0.5).astype(int)
print(f"Overall AUC: {roc_auc_score(y, y_prob_l1):.3f}")
print(f"Brier score: {brier_score_loss(y, y_prob_l1):.4f}")
print(classification_report(y, y_pred_l1, target_names=['Outcome 0', 'Outcome 1']))

# --- Model 2: L2 Logistic Regression (Ridge) ---
print("--- L2 Logistic Regression (Ridge) ---")
pipe_l2 = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression(penalty='l2', C=0.1, max_iter=5000, random_state=42))
])

scores_l2 = cross_val_score(pipe_l2, X, y, cv=cv, scoring='roc_auc')
print(f"AUC (10-fold CV): {scores_l2.mean():.3f} +/- {scores_l2.std():.3f}")

y_prob_l2 = cross_val_predict(pipe_l2, X, y, cv=cv, method='predict_proba')[:, 1]
y_pred_l2 = (y_prob_l2 >= 0.5).astype(int)
print(f"Overall AUC: {roc_auc_score(y, y_prob_l2):.3f}")
print(f"Brier score: {brier_score_loss(y, y_prob_l2):.4f}")

# --- Model 3: Random Forest ---
print("\n--- Random Forest ---")
pipe_rf = Pipeline([
    ('scaler', StandardScaler()),
    ('model', RandomForestClassifier(n_estimators=500, max_depth=5, min_samples_leaf=10,
                                      random_state=42, n_jobs=-1))
])

scores_rf = cross_val_score(pipe_rf, X, y, cv=cv, scoring='roc_auc')
print(f"AUC (10-fold CV): {scores_rf.mean():.3f} +/- {scores_rf.std():.3f}")

y_prob_rf = cross_val_predict(pipe_rf, X, y, cv=cv, method='predict_proba')[:, 1]
y_pred_rf = (y_prob_rf >= 0.5).astype(int)
print(f"Overall AUC: {roc_auc_score(y, y_prob_rf):.3f}")
print(f"Brier score: {brier_score_loss(y, y_prob_rf):.4f}")
print(classification_report(y, y_pred_rf, target_names=['Outcome 0', 'Outcome 1']))

# --- Model 4: Gradient Boosting ---
print("--- Gradient Boosting ---")
pipe_gb = Pipeline([
    ('scaler', StandardScaler()),
    ('model', GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05,
                                          min_samples_leaf=10, subsample=0.8, random_state=42))
])

scores_gb = cross_val_score(pipe_gb, X, y, cv=cv, scoring='roc_auc')
print(f"AUC (10-fold CV): {scores_gb.mean():.3f} +/- {scores_gb.std():.3f}")

y_prob_gb = cross_val_predict(pipe_gb, X, y, cv=cv, method='predict_proba')[:, 1]
y_pred_gb = (y_prob_gb >= 0.5).astype(int)
print(f"Overall AUC: {roc_auc_score(y, y_prob_gb):.3f}")
print(f"Brier score: {brier_score_loss(y, y_prob_gb):.4f}")
print(classification_report(y, y_pred_gb, target_names=['Outcome 0', 'Outcome 1']))

# --- Model comparison plot ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# ROC curves
for name, y_prob, color in [
    ('L1 Logistic', y_prob_l1, 'blue'),
    ('L2 Logistic', y_prob_l2, 'green'),
    ('Random Forest', y_prob_rf, 'orange'),
    ('Gradient Boosting', y_prob_gb, 'red'),
]:
    fpr, tpr, _ = roc_curve(y, y_prob)
    auc = roc_auc_score(y, y_prob)
    axes[0].plot(fpr, tpr, color=color, label=f'{name} (AUC={auc:.3f})')

axes[0].plot([0, 1], [0, 1], 'k--', alpha=0.3)
axes[0].set_xlabel('False Positive Rate')
axes[0].set_ylabel('True Positive Rate')
axes[0].set_title('ROC Curves (10-fold CV)')
axes[0].legend(fontsize=9)

# CV AUC comparison
model_names = ['L1 Logistic', 'L2 Logistic', 'Random Forest', 'Gradient Boost']
all_scores = [scores_l1, scores_l2, scores_rf, scores_gb]
bp = axes[1].boxplot(all_scores, labels=model_names, patch_artist=True)
colors_bp = ['steelblue', 'green', 'orange', 'coral']
for patch, color in zip(bp['boxes'], colors_bp):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
axes[1].set_ylabel('AUC')
axes[1].set_title('Cross-Validation AUC Comparison')
axes[1].tick_params(axis='x', rotation=15)

# Confusion matrix for best model
best_idx = np.argmax([s.mean() for s in all_scores])
best_name = model_names[best_idx]
best_pred = [y_pred_l1, y_pred_l2, y_pred_rf, y_pred_gb][best_idx]
cm = confusion_matrix(y, best_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[2],
            xticklabels=['Pred 0', 'Pred 1'], yticklabels=['True 0', 'True 1'])
axes[2].set_title(f'Confusion Matrix: {best_name}')

plt.tight_layout()
plt.savefig('plots/05_model_comparison.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"\nBest model by mean CV AUC: {best_name} ({all_scores[best_idx].mean():.3f})")

# ============================================================
# 5. FEATURE IMPORTANCE & MODEL INTERPRETATION
# ============================================================
print("\n" + "=" * 60)
print("5. FEATURE IMPORTANCE")
print("=" * 60)

# Fit L1 logistic on full data for coefficient inspection
pipe_l1_full = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression(penalty='l1', solver='saga', C=0.1, max_iter=5000, random_state=42))
])
pipe_l1_full.fit(X, y)
coefs = pipe_l1_full.named_steps['model'].coef_[0]
coef_df = pd.DataFrame({'feature': feature_cols, 'coef': coefs})
coef_df['abs_coef'] = np.abs(coef_df['coef'])
coef_df = coef_df.sort_values('abs_coef', ascending=False)

non_zero = coef_df[coef_df['abs_coef'] > 0]
print(f"L1 Logistic: {len(non_zero)}/{len(feature_cols)} features with non-zero coefficients")
print(f"\nTop 20 features by |coefficient|:")
print(non_zero.head(20)[['feature', 'coef']].to_string(index=False))

# Fit RF on full data for feature importance
pipe_rf_full = Pipeline([
    ('scaler', StandardScaler()),
    ('model', RandomForestClassifier(n_estimators=500, max_depth=5, min_samples_leaf=10,
                                      random_state=42, n_jobs=-1))
])
pipe_rf_full.fit(X, y)
rf_imp = pipe_rf_full.named_steps['model'].feature_importances_
rf_imp_df = pd.DataFrame({'feature': feature_cols, 'importance': rf_imp})
rf_imp_df = rf_imp_df.sort_values('importance', ascending=False)
print(f"\nRandom Forest top 20 features:")
print(rf_imp_df.head(20).to_string(index=False))

# Feature importance plot
fig, axes = plt.subplots(1, 2, figsize=(14, 8))

top20_l1 = coef_df.head(20)
colors = ['coral' if c > 0 else 'steelblue' for c in top20_l1['coef']]
axes[0].barh(range(len(top20_l1)), top20_l1['coef'].values, color=colors)
axes[0].set_yticks(range(len(top20_l1)))
axes[0].set_yticklabels(top20_l1['feature'].values, fontsize=8)
axes[0].set_xlabel('Coefficient')
axes[0].set_title('L1 Logistic Regression: Top 20 Features')
axes[0].invert_yaxis()

top20_rf = rf_imp_df.head(20)
axes[1].barh(range(len(top20_rf)), top20_rf['importance'].values, color='steelblue')
axes[1].set_yticks(range(len(top20_rf)))
axes[1].set_yticklabels(top20_rf['feature'].values, fontsize=8)
axes[1].set_xlabel('Importance')
axes[1].set_title('Random Forest: Top 20 Features')
axes[1].invert_yaxis()

plt.tight_layout()
plt.savefig('plots/06_feature_importance.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# 6. MODEL CALIBRATION & VALIDATION
# ============================================================
print("\n" + "=" * 60)
print("6. MODEL CALIBRATION & VALIDATION")
print("=" * 60)

from sklearn.calibration import calibration_curve

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for name, y_prob, color in [
    ('L1 Logistic', y_prob_l1, 'blue'),
    ('L2 Logistic', y_prob_l2, 'green'),
    ('Random Forest', y_prob_rf, 'orange'),
    ('Gradient Boosting', y_prob_gb, 'red'),
]:
    prob_true, prob_pred = calibration_curve(y, y_prob, n_bins=10, strategy='uniform')
    axes[0].plot(prob_pred, prob_true, 's-', color=color, label=name)

axes[0].plot([0, 1], [0, 1], 'k--', alpha=0.3)
axes[0].set_xlabel('Mean Predicted Probability')
axes[0].set_ylabel('Fraction of Positives')
axes[0].set_title('Calibration Curves')
axes[0].legend(fontsize=9)

# Predicted probability distributions
for name, y_prob, color in [
    ('L1 Logistic', y_prob_l1, 'blue'),
    ('Random Forest', y_prob_rf, 'orange'),
]:
    axes[1].hist(y_prob[y == 0], bins=30, alpha=0.4, color=color, label=f'{name} (Outcome 0)', density=True)
    axes[1].hist(y_prob[y == 1], bins=30, alpha=0.4, color=color, linestyle='--', label=f'{name} (Outcome 1)', density=True, histtype='step', linewidth=2)

axes[1].set_xlabel('Predicted Probability')
axes[1].set_ylabel('Density')
axes[1].set_title('Predicted Probability Distributions')
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig('plots/07_calibration.png', dpi=150, bbox_inches='tight')
plt.close()

# Hosmer-Lemeshow style check for best model
best_probs = [y_prob_l1, y_prob_l2, y_prob_rf, y_prob_gb][best_idx]
print(f"\nCalibration check for {best_name}:")
print(f"  Brier score: {brier_score_loss(y, best_probs):.4f}")
print(f"  Log loss: {log_loss(y, best_probs):.4f}")

# Bin predictions and check calibration
n_bins = 10
bin_edges = np.linspace(0, 1, n_bins + 1)
for i in range(n_bins):
    mask = (best_probs >= bin_edges[i]) & (best_probs < bin_edges[i+1])
    if mask.sum() > 0:
        actual_rate = y[mask].mean()
        pred_rate = best_probs[mask].mean()
        print(f"  Bin [{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}]: n={mask.sum()}, predicted={pred_rate:.3f}, actual={actual_rate:.3f}")

# ============================================================
# 7. ADDITIONAL ANALYSIS: Top gene box plots
# ============================================================

# Box plots of top discriminative genes
top5_genes = univariate_df.nsmallest(6, 'p_value')['gene'].tolist()

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
for idx, gene in enumerate(top5_genes):
    ax = axes[idx // 3][idx % 3]
    data_0 = df[df['outcome'] == 0][gene]
    data_1 = df[df['outcome'] == 1][gene]
    bp = ax.boxplot([data_0, data_1], labels=['Outcome 0', 'Outcome 1'], patch_artist=True)
    bp['boxes'][0].set_facecolor('steelblue')
    bp['boxes'][1].set_facecolor('coral')
    p = univariate_df[univariate_df['gene'] == gene]['p_value'].values[0]
    d = univariate_df[univariate_df['gene'] == gene]['cohens_d'].values[0]
    ax.set_title(f'{gene}\np={p:.2e}, d={d:.2f}', fontsize=10)

plt.suptitle('Top 6 Discriminative Genes by Outcome', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('plots/08_top_genes_boxplots.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# 8. PERMUTATION TEST (sanity check: is signal real?)
# ============================================================
print("\n" + "=" * 60)
print("7. PERMUTATION TEST")
print("=" * 60)

from sklearn.model_selection import permutation_test_score

# Use L1 logistic for permutation test (faster)
pipe_perm = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression(penalty='l1', solver='saga', C=0.1, max_iter=5000, random_state=42))
])

score_real, perm_scores, perm_p = permutation_test_score(
    pipe_perm, X, y, scoring='roc_auc', cv=cv, n_permutations=100, random_state=42, n_jobs=-1
)

print(f"Real score (AUC): {score_real:.3f}")
print(f"Permutation scores: mean={perm_scores.mean():.3f}, std={perm_scores.std():.3f}")
print(f"Permutation p-value: {perm_p:.4f}")

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(perm_scores, bins=30, alpha=0.7, color='grey', label='Permuted')
ax.axvline(score_real, color='red', linewidth=2, label=f'Real AUC={score_real:.3f}')
ax.set_xlabel('AUC')
ax.set_ylabel('Count')
ax.set_title(f'Permutation Test (p={perm_p:.4f})')
ax.legend()
plt.tight_layout()
plt.savefig('plots/09_permutation_test.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# SAVE SUMMARY STATISTICS FOR REPORT
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY FOR REPORT")
print("=" * 60)

print(f"Dataset: {df.shape[0]} samples, {len(gene_cols)} genes, age, sex, binary outcome")
print(f"Outcome balance: {(y==0).sum()} vs {(y==1).sum()} ({y.mean():.1%} positive)")
print(f"Age range: {df['age'].min()}-{df['age'].max()}, mean {df['age'].mean():.1f}")
print(f"Sex: {(df['sex']=='F').sum()} F, {(df['sex']=='M').sum()} M")
print(f"Significant genes (BH FDR<0.05): {univariate_df['sig_bh'].sum()}")
print(f"Best model: {best_name}, CV AUC = {all_scores[best_idx].mean():.3f}")
print(f"Permutation test p-value: {perm_p:.4f}")
print(f"Non-zero L1 features: {len(non_zero)}")

print("\nDONE.")
