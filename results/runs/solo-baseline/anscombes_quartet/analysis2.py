import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv("dataset.csv")
batches = sorted(df['batch'].unique())

print("="*70)
print("STATISTICAL DIAGNOSTICS PER BATCH")
print("="*70)

for batch in batches:
    sub = df[df['batch'] == batch].reset_index(drop=True)
    X = sm.add_constant(sub['dosage_mg'].values)
    y = sub['response'].values
    model = sm.OLS(y, X).fit()
    residuals = model.resid

    print(f"\n--- {batch} ---")
    print(f"  R²: {model.rsquared:.4f}, Adj R²: {model.rsquared_adj:.4f}")
    print(f"  F-stat: {model.fvalue:.2f}, p={model.f_pvalue:.4f}")
    print(f"  Coefficients: intercept={model.params[0]:.3f}, slope={model.params[1]:.3f}")

    # Shapiro-Wilk
    sw_stat, sw_p = stats.shapiro(residuals)
    print(f"  Shapiro-Wilk (residual normality): W={sw_stat:.4f}, p={sw_p:.4f} {'*** NON-NORMAL' if sw_p < 0.05 else '(normal)'}")

    # Breusch-Pagan
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, X)
    print(f"  Breusch-Pagan (heteroscedasticity): stat={bp_stat:.4f}, p={bp_p:.4f} {'*** HETEROSCEDASTIC' if bp_p < 0.05 else '(homoscedastic)'}")

    # Durbin-Watson
    dw = durbin_watson(residuals)
    print(f"  Durbin-Watson: {dw:.4f}")

    # Nonlinearity test
    x_vals = sub['dosage_mg'].values
    X_quad = sm.add_constant(np.column_stack([x_vals, x_vals**2]))
    model_quad = sm.OLS(y, X_quad).fit()
    f_num = (model.ssr - model_quad.ssr) / 1
    f_den = model_quad.ssr / model_quad.df_resid if model_quad.df_resid > 0 else 1e-10
    f_val = f_num / f_den
    f_p = 1 - stats.f.cdf(f_val, 1, model_quad.df_resid)
    print(f"  Quadratic term F-test: F={f_val:.2f}, p={f_p:.4f} {'*** NONLINEAR' if f_p < 0.05 else '(linear adequate)'}")
    print(f"  Quadratic R²: {model_quad.rsquared:.4f}")

    # Cook's distance
    influence = model.get_influence()
    cooks_d = influence.cooks_distance[0]
    threshold = 4 / len(sub)
    for j in range(len(sub)):
        if cooks_d[j] > threshold:
            print(f"  *** Influential point: obs_id={int(sub.loc[j, 'observation_id'])}, "
                  f"dosage={sub.loc[j, 'dosage_mg']}, response={sub.loc[j, 'response']:.2f}, "
                  f"Cook's D={cooks_d[j]:.4f}")

# Nuisance variable analysis
print("\n" + "="*70)
print("NUISANCE VARIABLE ANALYSIS")
print("="*70)

X_full = sm.add_constant(df[['dosage_mg', 'lab_temp_c', 'weight_kg']].values)
model_full = sm.OLS(df['response'].values, X_full).fit()
print("\nFull model (pooled, dosage + lab_temp + weight):")
print(f"  R²={model_full.rsquared:.4f}")
print(f"  Intercept: {model_full.params[0]:.3f} (p={model_full.pvalues[0]:.4f})")
print(f"  dosage_mg: {model_full.params[1]:.3f} (p={model_full.pvalues[1]:.4f})")
print(f"  lab_temp_c: {model_full.params[2]:.3f} (p={model_full.pvalues[2]:.4f})")
print(f"  weight_kg: {model_full.params[3]:.3f} (p={model_full.pvalues[3]:.4f})")

# Technician ANOVA
X_dose = sm.add_constant(df['dosage_mg'].values)
resid_dose = sm.OLS(df['response'].values, X_dose).fit().resid
groups = [resid_dose[df['technician'] == t] for t in df['technician'].unique()]
f_tech, p_tech = stats.f_oneway(*groups)
print(f"\nTechnician effect ANOVA on dosage-residuals: F={f_tech:.3f}, p={p_tech:.4f}")

r_temp, p_temp = stats.pearsonr(df['lab_temp_c'], df['response'])
print(f"Correlation lab_temp vs response: r={r_temp:.4f}, p={p_temp:.4f}")
r_wt, p_wt = stats.pearsonr(df['weight_kg'], df['response'])
print(f"Correlation weight vs response: r={r_wt:.4f}, p={p_wt:.4f}")

# Leverage/Cook's D plot
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()
for i, batch in enumerate(batches):
    ax = axes[i]
    sub = df[df['batch'] == batch].reset_index(drop=True)
    X = sm.add_constant(sub['dosage_mg'].values)
    model = sm.OLS(sub['response'].values, X).fit()
    influence = model.get_influence()
    leverage = influence.hat_matrix_diag
    cooks_d = influence.cooks_distance[0]
    sizes = 100 + 1500 * (cooks_d / max(cooks_d.max(), 0.001))
    scatter = ax.scatter(leverage, model.resid, s=sizes, alpha=0.6, edgecolors='k',
                        linewidth=0.5, c=cooks_d, cmap='Reds')
    ax.axhline(0, color='grey', linestyle='--', linewidth=1)
    ax.set_title(f'{batch}', fontweight='bold')
    ax.set_xlabel('Leverage')
    ax.set_ylabel('Residual')
    plt.colorbar(scatter, ax=ax, label="Cook's D")
    ax.grid(True, alpha=0.3)
    threshold = 4 / len(sub)
    for j in range(len(sub)):
        if cooks_d[j] > threshold:
            ax.annotate(f'obs {int(sub.loc[j, "observation_id"])}',
                       (leverage[j], model.resid[j]), fontsize=8, fontweight='bold', color='red')
fig.suptitle("Leverage vs Residuals (point size = Cook's D)", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('plots/06_leverage_cooks_distance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nPlot 6 done")

# Robust regression for Q3
print("\n" + "="*70)
print("ROBUST REGRESSION FOR BATCH_Q3")
print("="*70)
sub3 = df[df['batch'] == 'batch_Q3'].reset_index(drop=True)
X3 = sm.add_constant(sub3['dosage_mg'].values)
y3 = sub3['response'].values
ols_3 = sm.OLS(y3, X3).fit()
rlm_3 = sm.RLM(y3, X3, M=sm.robust.norms.HuberT()).fit()
print(f"  OLS: intercept={ols_3.params[0]:.3f}, slope={ols_3.params[1]:.3f}, R²={ols_3.rsquared:.4f}")
print(f"  RLM (Huber): intercept={rlm_3.params[0]:.3f}, slope={rlm_3.params[1]:.3f}")

# Without outlier
mask = sub3['response'] != sub3['response'].max()
sub3_clean = sub3[mask].reset_index(drop=True)
X3c = sm.add_constant(sub3_clean['dosage_mg'].values)
ols_3c = sm.OLS(sub3_clean['response'].values, X3c).fit()
print(f"  OLS (outlier removed): intercept={ols_3c.params[0]:.3f}, slope={ols_3c.params[1]:.3f}, R²={ols_3c.rsquared:.4f}")

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(sub3['dosage_mg'], sub3['response'], s=80, alpha=0.8, edgecolors='k', linewidth=0.5, zorder=5)
x_fit = np.linspace(3, 15, 100)
ax.plot(x_fit, ols_3.params[1]*x_fit + ols_3.params[0], 'r--', linewidth=2, label=f'OLS (slope={ols_3.params[1]:.3f})')
ax.plot(x_fit, rlm_3.params[1]*x_fit + rlm_3.params[0], 'b-', linewidth=2, label=f'Robust Huber (slope={rlm_3.params[1]:.3f})')
ax.plot(x_fit, ols_3c.params[1]*x_fit + ols_3c.params[0], 'g:', linewidth=2, label=f'OLS sans outlier (slope={ols_3c.params[1]:.3f})')
outlier_row = sub3[sub3['response'] == sub3['response'].max()]
ax.scatter(outlier_row['dosage_mg'], outlier_row['response'], s=150, facecolors='none',
          edgecolors='red', linewidth=2, zorder=6, label='Influential outlier')
ax.set_title('batch_Q3: OLS vs Robust Regression', fontweight='bold')
ax.set_xlabel('Dosage (mg)')
ax.set_ylabel('Response')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('plots/07_robust_vs_ols_Q3.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 7 done")

# ==============================================================
# PLOT 8: Boxplots per batch
# ==============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
df.boxplot(column='response', by='batch', ax=axes[0])
axes[0].set_title('Response by Batch', fontweight='bold')
axes[0].set_xlabel('Batch')
axes[0].set_ylabel('Response')
plt.sca(axes[0])
plt.title('Response by Batch')

df.boxplot(column='dosage_mg', by='batch', ax=axes[1])
axes[1].set_title('Dosage by Batch', fontweight='bold')
axes[1].set_xlabel('Batch')
axes[1].set_ylabel('Dosage (mg)')
plt.sca(axes[1])
plt.title('Dosage by Batch')
fig.suptitle('')
plt.tight_layout()
plt.savefig('plots/08_boxplots.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 8 done")

print("\nAll analysis complete.")
