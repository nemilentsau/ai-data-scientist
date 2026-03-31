"""Step 4: Model assumption checks and additional diagnostics."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.calibration import calibration_curve
from sklearn.model_selection import cross_val_predict, StratifiedKFold, permutation_test_score
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('dataset.csv')
gene_cols = [c for c in df.columns if c.startswith('gene_')]
key_genes = ['gene_000', 'gene_001', 'gene_002']
X_key = df[key_genes].values
y = df['outcome'].values
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

print("=" * 60)
print("LOGISTIC REGRESSION ASSUMPTION CHECKS")
print("=" * 60)

# 1. Linearity of log-odds: check with statsmodels
X_sm = sm.add_constant(X_key)
logit_model = sm.Logit(y, X_sm).fit(disp=0)
print("\n--- Statsmodels Logistic Regression Summary ---")
print(logit_model.summary2())

# 2. Multicollinearity (VIF)
from statsmodels.stats.outliers_influence import variance_inflation_factor
vif_data = pd.DataFrame()
vif_data['feature'] = key_genes
vif_data['VIF'] = [variance_inflation_factor(X_key, i) for i in range(X_key.shape[1])]
print(f"\n--- Variance Inflation Factors ---")
print(vif_data.to_string())
print("(VIF < 5 is acceptable; < 10 is tolerable)")

# 3. Linearity check: Box-Tidwell test approximation
# Add interaction terms (X * log(|X| + offset))
print("\n--- Linearity of Log-Odds (Box-Tidwell approximation) ---")
for i, gene in enumerate(key_genes):
    x = X_key[:, i]
    # Shift to positive for log transform
    x_shifted = x - x.min() + 1
    x_logx = x * np.log(x_shifted)
    # Add interaction to model
    X_bt = np.column_stack([X_key, x_logx])
    X_bt_sm = sm.add_constant(X_bt)
    bt_model = sm.Logit(y, X_bt_sm).fit(disp=0)
    p_interaction = bt_model.pvalues[-1]
    print(f"  {gene}: interaction p-value = {p_interaction:.4f} {'(non-linear!)' if p_interaction < 0.05 else '(linear OK)'}")

# 4. Influential observations (Cook's distance via statsmodels)
influence = logit_model.get_influence()
cooks_d = influence.cooks_distance[0]
print(f"\n--- Influential Observations ---")
print(f"Cook's D > 4/n threshold: {(cooks_d > 4/len(y)).sum()} observations")
print(f"Max Cook's D: {cooks_d.max():.4f}")

# 5. Goodness of fit: Hosmer-Lemeshow test
y_prob = logit_model.predict(X_sm)
# Manual Hosmer-Lemeshow
n_groups = 10
sorted_idx = np.argsort(y_prob)
groups = np.array_split(sorted_idx, n_groups)
hl_stat = 0
for g in groups:
    obs_1 = y[g].sum()
    exp_1 = y_prob[g].sum()
    obs_0 = len(g) - obs_1
    exp_0 = len(g) - exp_1
    if exp_1 > 0:
        hl_stat += (obs_1 - exp_1)**2 / exp_1
    if exp_0 > 0:
        hl_stat += (obs_0 - exp_0)**2 / exp_0
hl_p = 1 - stats.chi2.cdf(hl_stat, n_groups - 2)
print(f"\n--- Hosmer-Lemeshow Goodness of Fit ---")
print(f"  Chi-square statistic: {hl_stat:.4f}")
print(f"  p-value: {hl_p:.4f}")
print(f"  {'Good fit (p > 0.05)' if hl_p > 0.05 else 'Poor fit (p < 0.05)'}")

# 6. Calibration plot
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

y_prob_cv = cross_val_predict(
    Pipeline([('scaler', StandardScaler()),
              ('lr', LogisticRegression(max_iter=1000, random_state=42))]),
    X_key, y, cv=cv, method='predict_proba')[:, 1]

prob_true, prob_pred = calibration_curve(y, y_prob_cv, n_bins=10)
axes[0].plot(prob_pred, prob_true, 'o-', label='LR (3 genes)')
axes[0].plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
axes[0].set_xlabel('Mean Predicted Probability')
axes[0].set_ylabel('Fraction of Positives')
axes[0].set_title('Calibration Plot (Cross-Validated)')
axes[0].legend()

# 7. Residual plot
residuals = y - y_prob
axes[1].scatter(y_prob, residuals, alpha=0.3, s=10)
axes[1].axhline(0, color='red', linestyle='--')
axes[1].set_xlabel('Predicted Probability')
axes[1].set_ylabel('Residual (Observed - Predicted)')
axes[1].set_title('Residual Plot')

plt.tight_layout()
plt.savefig('plots/12_diagnostics.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved 12_diagnostics.png")

# 8. Permutation test to check if model is significantly better than chance
print("\n--- Permutation Test (100 permutations) ---")
score, perm_scores, perm_p = permutation_test_score(
    Pipeline([('scaler', StandardScaler()),
              ('lr', LogisticRegression(max_iter=1000, random_state=42))]),
    X_key, y, cv=cv, scoring='roc_auc', n_permutations=100, random_state=42
)
print(f"  True AUC: {score:.4f}")
print(f"  Permutation AUC mean: {perm_scores.mean():.4f} ± {perm_scores.std():.4f}")
print(f"  Permutation p-value: {perm_p:.4f}")

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(perm_scores, bins=20, color='gray', alpha=0.7, label='Permuted')
ax.axvline(score, color='red', linewidth=2, label=f'True AUC = {score:.3f}')
ax.set_xlabel('ROC AUC')
ax.set_ylabel('Count')
ax.set_title('Permutation Test: Model vs Chance')
ax.legend()
plt.tight_layout()
plt.savefig('plots/13_permutation_test.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 13_permutation_test.png")

# 9. Check for non-linear interactions between key genes
print("\n--- Interaction Effects ---")
X_interact = np.column_stack([
    X_key,
    X_key[:, 0] * X_key[:, 1],  # gene_000 * gene_001
    X_key[:, 0] * X_key[:, 2],  # gene_000 * gene_002
    X_key[:, 1] * X_key[:, 2],  # gene_001 * gene_002
])
X_interact_sm = sm.add_constant(X_interact)
interact_model = sm.Logit(y, X_interact_sm).fit(disp=0)
interact_names = key_genes + ['gene_000*gene_001', 'gene_000*gene_002', 'gene_001*gene_002']
for name, p in zip(interact_names, interact_model.pvalues[1:]):
    sig = '*' if p < 0.05 else ''
    print(f"  {name}: p={p:.4f} {sig}")

# LR test: main effects vs main+interactions
lr_stat = -2 * (logit_model.llf - interact_model.llf)
lr_p = 1 - stats.chi2.cdf(lr_stat, 3)
print(f"  LR test (main vs main+interactions): chi2={lr_stat:.4f}, p={lr_p:.4f}")
print(f"  {'Interactions improve fit' if lr_p < 0.05 else 'No significant interaction effects'}")

# 10. Decision boundary visualization (gene_000 vs gene_001)
fig, ax = plt.subplots(figsize=(8, 7))
scatter = ax.scatter(df['gene_000'], df['gene_001'], c=y, cmap='RdBu', alpha=0.5, s=15)
ax.set_xlabel('gene_000')
ax.set_ylabel('gene_001')
ax.set_title('Outcome by gene_000 and gene_001')
plt.colorbar(scatter, label='Outcome')

# Add decision boundary
scaler = StandardScaler()
X_2d = scaler.fit_transform(df[['gene_000', 'gene_001']].values)
lr_2d = LogisticRegression(max_iter=1000, random_state=42).fit(X_2d, y)
xx, yy = np.meshgrid(np.linspace(df['gene_000'].min()-0.5, df['gene_000'].max()+0.5, 200),
                      np.linspace(df['gene_001'].min()-0.5, df['gene_001'].max()+0.5, 200))
grid = scaler.transform(np.c_[xx.ravel(), yy.ravel()])
Z = lr_2d.predict_proba(grid)[:, 1].reshape(xx.shape)
ax.contour(xx, yy, Z, levels=[0.5], colors='black', linewidths=2, linestyles='--')

plt.tight_layout()
plt.savefig('plots/14_decision_boundary.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 14_decision_boundary.png")

# 11. Effect sizes and odds ratios
print("\n--- Odds Ratios (per 1 SD change) ---")
for name, coef in zip(key_genes, logit_model.params[1:]):
    ci_low, ci_high = logit_model.conf_int()[key_genes.index(name) + 1]
    or_val = np.exp(coef)
    or_low = np.exp(ci_low)
    or_high = np.exp(ci_high)
    print(f"  {name}: OR={or_val:.3f} (95% CI: {or_low:.3f}-{or_high:.3f})")
