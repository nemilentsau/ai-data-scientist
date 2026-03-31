"""Step 2: EDA visualizations."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('dataset.csv')
gene_cols = [c for c in df.columns if c.startswith('gene_')]

# --- Plot 1: Outcome distribution and demographics ---
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Outcome bar
df['outcome'].value_counts().plot(kind='bar', ax=axes[0, 0], color=['#2196F3', '#FF5722'])
axes[0, 0].set_title('Outcome Distribution')
axes[0, 0].set_xticklabels(['Positive (1)', 'Negative (0)'], rotation=0)
axes[0, 0].set_ylabel('Count')

# Age distribution by outcome
for outcome in [0, 1]:
    subset = df[df['outcome'] == outcome]['age']
    axes[0, 1].hist(subset, bins=20, alpha=0.6, label=f'Outcome {outcome}', density=True)
axes[0, 1].set_title('Age Distribution by Outcome')
axes[0, 1].set_xlabel('Age')
axes[0, 1].legend()

# Sex vs outcome
ct = pd.crosstab(df['sex'], df['outcome'])
ct.plot(kind='bar', ax=axes[1, 0], color=['#2196F3', '#FF5722'])
axes[1, 0].set_title('Sex vs Outcome')
axes[1, 0].set_xticklabels(['Female', 'Male'], rotation=0)
axes[1, 0].legend(['Outcome 0', 'Outcome 1'])

# Age boxplot by outcome
df.boxplot(column='age', by='outcome', ax=axes[1, 1])
axes[1, 1].set_title('Age by Outcome')
axes[1, 1].set_xlabel('Outcome')
plt.suptitle('')

plt.tight_layout()
plt.savefig('plots/01_demographics.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 01_demographics.png")

# --- Plot 2: Gene expression overview ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Distribution of gene means
gene_means = df[gene_cols].mean()
gene_stds = df[gene_cols].std()
axes[0].hist(gene_means, bins=30, color='steelblue', edgecolor='white')
axes[0].set_title('Distribution of Gene Means')
axes[0].set_xlabel('Mean Expression')
axes[0].axvline(0, color='red', linestyle='--')

axes[1].hist(gene_stds, bins=30, color='coral', edgecolor='white')
axes[1].set_title('Distribution of Gene Std Devs')
axes[1].set_xlabel('Std Dev')
axes[1].axvline(1, color='red', linestyle='--')

plt.tight_layout()
plt.savefig('plots/02_gene_overview.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 02_gene_overview.png")

# --- Plot 3: Univariate tests - which genes differ by outcome? ---
# Two-sample t-test for each gene
t_stats = []
p_vals = []
effect_sizes = []  # Cohen's d

for g in gene_cols:
    g0 = df[df['outcome'] == 0][g]
    g1 = df[df['outcome'] == 1][g]
    t, p = stats.ttest_ind(g0, g1)
    # Cohen's d
    pooled_std = np.sqrt(((len(g0) - 1) * g0.std()**2 + (len(g1) - 1) * g1.std()**2) / (len(g0) + len(g1) - 2))
    d = (g1.mean() - g0.mean()) / pooled_std
    t_stats.append(t)
    p_vals.append(p)
    effect_sizes.append(d)

test_df = pd.DataFrame({
    'gene': gene_cols,
    't_stat': t_stats,
    'p_value': p_vals,
    'effect_size': effect_sizes
})
test_df['p_adj'] = test_df['p_value'] * len(gene_cols)  # Bonferroni
test_df['p_adj'] = test_df['p_adj'].clip(upper=1.0)
test_df['significant_bonf'] = test_df['p_adj'] < 0.05
test_df = test_df.sort_values('p_value')

print(f"\n=== UNIVARIATE TESTS ===")
print(f"Significant genes (Bonferroni p < 0.05): {test_df['significant_bonf'].sum()}")
print(f"\nTop 20 genes by p-value:")
print(test_df.head(20)[['gene', 'p_value', 'p_adj', 'effect_size', 'significant_bonf']].to_string())

# Volcano plot
fig, ax = plt.subplots(figsize=(10, 7))
colors = ['red' if sig else 'gray' for sig in test_df['significant_bonf']]
ax.scatter(test_df['effect_size'], -np.log10(test_df['p_value']), c=colors, alpha=0.6, s=40)
ax.axhline(-np.log10(0.05 / len(gene_cols)), color='blue', linestyle='--', label='Bonferroni threshold')
ax.set_xlabel("Effect Size (Cohen's d)")
ax.set_ylabel('-log10(p-value)')
ax.set_title('Volcano Plot: Gene Expression vs Outcome')
# Label top genes
for _, row in test_df.head(10).iterrows():
    ax.annotate(row['gene'], (row['effect_size'], -np.log10(row['p_value'])),
                fontsize=7, alpha=0.8)
ax.legend()
plt.tight_layout()
plt.savefig('plots/03_volcano_plot.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 03_volcano_plot.png")

# --- Plot 4: Top genes boxplots ---
top_genes = test_df.head(12)['gene'].tolist()
fig, axes = plt.subplots(3, 4, figsize=(16, 12))
for i, gene in enumerate(top_genes):
    ax = axes[i // 4, i % 4]
    df.boxplot(column=gene, by='outcome', ax=ax)
    p = test_df[test_df['gene'] == gene]['p_value'].values[0]
    d = test_df[test_df['gene'] == gene]['effect_size'].values[0]
    ax.set_title(f'{gene}\np={p:.2e}, d={d:.2f}')
    ax.set_xlabel('Outcome')
plt.suptitle('Top 12 Genes by Significance', fontsize=14)
plt.tight_layout()
plt.savefig('plots/04_top_genes_boxplots.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 04_top_genes_boxplots.png")

# --- Plot 5: Correlation heatmap of top genes ---
top20 = test_df.head(20)['gene'].tolist()
corr = df[top20].corr()
fig, ax = plt.subplots(figsize=(12, 10))
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=ax,
            xticklabels=True, yticklabels=True, annot_kws={'size': 7})
ax.set_title('Correlation Among Top 20 Genes')
plt.tight_layout()
plt.savefig('plots/05_top_genes_correlation.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 05_top_genes_correlation.png")

# --- Plot 6: PCA visualization ---
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

X_genes = df[gene_cols].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_genes)

pca = PCA(n_components=10)
X_pca = pca.fit_transform(X_scaled)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# PC1 vs PC2
for outcome in [0, 1]:
    mask = df['outcome'] == outcome
    axes[0].scatter(X_pca[mask, 0], X_pca[mask, 1], alpha=0.5, s=20, label=f'Outcome {outcome}')
axes[0].set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
axes[0].set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
axes[0].set_title('PCA: PC1 vs PC2')
axes[0].legend()

# Scree plot
axes[1].bar(range(1, 11), pca.explained_variance_ratio_ * 100)
axes[1].plot(range(1, 11), np.cumsum(pca.explained_variance_ratio_) * 100, 'ro-')
axes[1].set_xlabel('Principal Component')
axes[1].set_ylabel('Variance Explained (%)')
axes[1].set_title('PCA Scree Plot')

# Full PCA for cumulative variance
pca_full = PCA().fit(X_scaled)
cum_var = np.cumsum(pca_full.explained_variance_ratio_) * 100
n_90 = np.argmax(cum_var >= 90) + 1
axes[2].plot(range(1, len(cum_var) + 1), cum_var)
axes[2].axhline(90, color='red', linestyle='--', label=f'90% at {n_90} PCs')
axes[2].set_xlabel('Number of Components')
axes[2].set_ylabel('Cumulative Variance Explained (%)')
axes[2].set_title('Cumulative Variance Explained')
axes[2].legend()

plt.tight_layout()
plt.savefig('plots/06_pca.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved 06_pca.png")
print(f"PCs needed for 90% variance: {n_90}")

# Save test results for later use
test_df.to_csv('gene_test_results.csv', index=False)
print("\nSaved gene_test_results.csv")
