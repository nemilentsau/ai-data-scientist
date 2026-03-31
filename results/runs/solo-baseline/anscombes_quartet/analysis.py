import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, normal_ad
from statsmodels.stats.stattools import durbin_watson
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv("dataset.csv")
batches = sorted(df['batch'].unique())

# ==============================================================
# PLOT 1: The core Anscombe scatter — 4 panels with OLS lines
# ==============================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for i, batch in enumerate(batches):
    ax = axes[i]
    sub = df[df['batch'] == batch]
    ax.scatter(sub['dosage_mg'], sub['response'], s=60, alpha=0.8, edgecolors='k', linewidth=0.5)
    # OLS fit line
    x_fit = np.linspace(2, 20, 100)
    m, b = np.polyfit(sub['dosage_mg'], sub['response'], 1)
    ax.plot(x_fit, m * x_fit + b, 'r--', linewidth=1.5, label=f'y={m:.2f}x+{b:.2f}')
    ax.set_title(f'{batch}\nr={sub["dosage_mg"].corr(sub["response"]):.4f}', fontsize=12, fontweight='bold')
    ax.set_xlabel('Dosage (mg)')
    ax.set_ylabel('Response')
    ax.set_xlim(2, 20)
    ax.set_ylim(1, 14)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle("Anscombe's Quartet: Identical Statistics, Different Patterns", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('plots/01_anscombe_quartet_scatter.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 1 done")

# ==============================================================
# PLOT 2: Residual diagnostics per batch (residuals vs fitted + QQ)
# ==============================================================
fig, axes = plt.subplots(4, 2, figsize=(14, 18))

for i, batch in enumerate(batches):
    sub = df[df['batch'] == batch]
    X = sm.add_constant(sub['dosage_mg'])
    model = sm.OLS(sub['response'], X).fit()
    residuals = model.resid
    fitted = model.fittedvalues

    # Residuals vs fitted
    ax1 = axes[i, 0]
    ax1.scatter(fitted, residuals, s=60, alpha=0.8, edgecolors='k', linewidth=0.5)
    ax1.axhline(0, color='red', linestyle='--', linewidth=1)
    # LOWESS smoother
    try:
        lowess = sm.nonparametric.lowess(residuals, fitted, frac=0.6)
        ax1.plot(lowess[:, 0], lowess[:, 1], 'g-', linewidth=2, label='LOWESS')
    except:
        pass
    ax1.set_title(f'{batch}: Residuals vs Fitted', fontweight='bold')
    ax1.set_xlabel('Fitted values')
    ax1.set_ylabel('Residuals')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # QQ plot
    ax2 = axes[i, 1]
    sm.qqplot(residuals, line='s', ax=ax2, markerfacecolor='steelblue', markeredgecolor='k',
              markersize=6, alpha=0.8)
    ax2.set_title(f'{batch}: Q-Q Plot', fontweight='bold')
    ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('plots/02_residual_diagnostics.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 2 done")

# ==============================================================
# PLOT 3: Distributions of nuisance variables
# ==============================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# lab_temp_c histogram
axes[0].hist(df['lab_temp_c'], bins=12, edgecolor='black', alpha=0.7, color='steelblue')
axes[0].set_title('Distribution of Lab Temperature', fontweight='bold')
axes[0].set_xlabel('Lab Temp (°C)')
axes[0].set_ylabel('Count')

# weight_kg histogram
axes[1].hist(df['weight_kg'], bins=12, edgecolor='black', alpha=0.7, color='coral')
axes[1].set_title('Distribution of Weight', fontweight='bold')
axes[1].set_xlabel('Weight (kg)')
axes[1].set_ylabel('Count')

# technician counts per batch
tech_batch = df.groupby(['batch', 'technician']).size().unstack(fill_value=0)
tech_batch.plot(kind='bar', ax=axes[2], edgecolor='black')
axes[2].set_title('Technician Assignment by Batch', fontweight='bold')
axes[2].set_xlabel('Batch')
axes[2].set_ylabel('Count')
axes[2].legend(title='Technician')
axes[2].tick_params(axis='x', rotation=0)

plt.tight_layout()
plt.savefig('plots/03_nuisance_variables.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 3 done")

# ==============================================================
# PLOT 4: Correlation heatmap
# ==============================================================
fig, ax = plt.subplots(figsize=(8, 6))
corr_matrix = df[['dosage_mg', 'response', 'lab_temp_c', 'weight_kg']].corr()
sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdBu_r', center=0, ax=ax,
            vmin=-1, vmax=1, linewidths=0.5)
ax.set_title('Correlation Matrix (All Data Pooled)', fontweight='bold')
plt.tight_layout()
plt.savefig('plots/04_correlation_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 4 done")

# ==============================================================
# PLOT 5: Batch-specific non-linear fits
# ==============================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for i, batch in enumerate(batches):
    ax = axes[i]
    sub = df[df['batch'] == batch].sort_values('dosage_mg')
    x, y = sub['dosage_mg'].values, sub['response'].values
    ax.scatter(x, y, s=60, alpha=0.8, edgecolors='k', linewidth=0.5, zorder=5)

    x_fit = np.linspace(min(x) - 0.5, max(x) + 0.5, 200)

    # Linear
    m1, b1 = np.polyfit(x, y, 1)
    ax.plot(x_fit, m1 * x_fit + b1, 'r--', linewidth=1.5, label=f'Linear (R²={np.corrcoef(x,y)[0,1]**2:.3f})')

    # Quadratic
    c2 = np.polyfit(x, y, 2)
    y_quad = np.polyval(c2, x_fit)
    ss_res = np.sum((y - np.polyval(c2, x))**2)
    ss_tot = np.sum((y - y.mean())**2)
    r2_quad = 1 - ss_res / ss_tot
    ax.plot(x_fit, y_quad, 'g-', linewidth=1.5, label=f'Quadratic (R²={r2_quad:.3f})')

    ax.set_title(f'{batch}', fontsize=12, fontweight='bold')
    ax.set_xlabel('Dosage (mg)')
    ax.set_ylabel('Response')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(2, 20)
    ax.set_ylim(1, 14)

fig.suptitle('Linear vs Quadratic Fits by Batch', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('plots/05_linear_vs_quadratic.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 5 done")

# ==============================================================
# STATISTICAL TESTS per batch
# ==============================================================
print("\n" + "="*70)
print("STATISTICAL DIAGNOSTICS PER BATCH")
print("="*70)

for batch in batches:
    sub = df[df['batch'] == batch]
    X = sm.add_constant(sub['dosage_mg'])
    model = sm.OLS(sub['response'], X).fit()
    residuals = model.resid

    print(f"\n--- {batch} ---")
    print(f"  R²: {model.rsquared:.4f}, Adj R²: {model.rsquared_adj:.4f}")
    print(f"  F-stat: {model.fvalue:.2f}, p={model.f_pvalue:.4f}")
    print(f"  Coefficients: intercept={model.params[0]:.3f}, slope={model.params[1]:.3f}")

    # Shapiro-Wilk normality test on residuals
    sw_stat, sw_p = stats.shapiro(residuals)
    print(f"  Shapiro-Wilk (residual normality): W={sw_stat:.4f}, p={sw_p:.4f} {'*** NON-NORMAL' if sw_p < 0.05 else '(normal)'}")

    # Breusch-Pagan heteroscedasticity test
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, X)
    print(f"  Breusch-Pagan (heteroscedasticity): stat={bp_stat:.4f}, p={bp_p:.4f} {'*** HETEROSCEDASTIC' if bp_p < 0.05 else '(homoscedastic)'}")

    # Durbin-Watson
    dw = durbin_watson(residuals)
    print(f"  Durbin-Watson: {dw:.4f}")

    # Nonlinearity: compare linear vs quadratic with F-test
    X_quad = sm.add_constant(np.column_stack([sub['dosage_mg'], sub['dosage_mg']**2]))
    try:
        model_quad = sm.OLS(sub['response'], X_quad).fit()
        # Partial F-test for quadratic term
        f_num = (model.ssr - model_quad.ssr) / 1
        f_den = model_quad.ssr / model_quad.df_resid
        f_val = f_num / f_den if f_den > 0 else 0
        f_p = 1 - stats.f.cdf(f_val, 1, model_quad.df_resid)
        print(f"  Quadratic term F-test: F={f_val:.2f}, p={f_p:.4f} {'*** NONLINEAR' if f_p < 0.05 else '(linear adequate)'}")
        print(f"  Quadratic R²: {model_quad.rsquared:.4f}")
    except:
        print("  Quadratic fit failed (singular)")

    # Influential points (Cook's distance)
    influence = model.get_influence()
    cooks_d = influence.cooks_distance[0]
    threshold = 4 / len(sub)
    influential = np.where(cooks_d > threshold)[0]
    if len(influential) > 0:
        for idx in influential:
            obs_id = sub.iloc[idx]['observation_id']
            print(f"  *** Influential point: obs_id={int(obs_id)}, "
                  f"dosage={sub.iloc[idx]['dosage_mg']}, response={sub.iloc[idx]['response']:.2f}, "
                  f"Cook's D={cooks_d[idx]:.4f}")

# ==============================================================
# NUISANCE VARIABLE ANALYSIS
# ==============================================================
print("\n" + "="*70)
print("NUISANCE VARIABLE ANALYSIS")
print("="*70)

# Does lab_temp_c or weight_kg correlate with response after controlling for dosage?
X_full = sm.add_constant(df[['dosage_mg', 'lab_temp_c', 'weight_kg']])
model_full = sm.OLS(df['response'], X_full).fit()
print("\nFull model (all data pooled, dosage + lab_temp + weight):")
print(model_full.summary().tables[1])

# Technician effect
print("\nOne-way ANOVA for technician effect on residuals (after dosage):")
X_dose = sm.add_constant(df['dosage_mg'])
resid_dose = sm.OLS(df['response'], X_dose).fit().resid
groups = [resid_dose[df['technician'] == t].values for t in df['technician'].unique()]
f_tech, p_tech = stats.f_oneway(*groups)
print(f"  F={f_tech:.3f}, p={p_tech:.4f}")

# Lab temp correlation with response
r_temp, p_temp = stats.pearsonr(df['lab_temp_c'], df['response'])
print(f"\nCorrelation lab_temp vs response: r={r_temp:.4f}, p={p_temp:.4f}")
r_wt, p_wt = stats.pearsonr(df['weight_kg'], df['response'])
print(f"Correlation weight vs response: r={r_wt:.4f}, p={p_wt:.4f}")

# ==============================================================
# PLOT 6: Leverage and Cook's distance
# ==============================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for i, batch in enumerate(batches):
    ax = axes[i]
    sub = df[df['batch'] == batch]
    X = sm.add_constant(sub['dosage_mg'])
    model = sm.OLS(sub['response'], X).fit()
    influence = model.get_influence()
    leverage = influence.hat_matrix_diag
    cooks_d = influence.cooks_distance[0]

    # Size by Cook's D
    sizes = 100 + 1500 * (cooks_d / max(cooks_d.max(), 0.001))
    scatter = ax.scatter(leverage, model.resid, s=sizes, alpha=0.6, edgecolors='k', linewidth=0.5, c=cooks_d, cmap='Reds')
    ax.axhline(0, color='grey', linestyle='--', linewidth=1)
    ax.set_title(f'{batch}', fontweight='bold')
    ax.set_xlabel('Leverage')
    ax.set_ylabel('Residual')
    plt.colorbar(scatter, ax=ax, label="Cook's D")
    ax.grid(True, alpha=0.3)

    # Label influential points
    threshold = 4 / len(sub)
    for j in range(len(sub)):
        if cooks_d[j] > threshold:
            ax.annotate(f'obs {int(sub.iloc[j]["observation_id"])}',
                       (leverage[j], model.resid.iloc[j]),
                       fontsize=8, fontweight='bold', color='red')

fig.suptitle("Leverage vs Residuals (point size = Cook's D)", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('plots/06_leverage_cooks_distance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nPlot 6 done")

# ==============================================================
# ROBUST REGRESSION for batch_Q3 (outlier-affected)
# ==============================================================
print("\n" + "="*70)
print("ROBUST REGRESSION FOR BATCH_Q3 (outlier present)")
print("="*70)
sub3 = df[df['batch'] == 'batch_Q3']
X3 = sm.add_constant(sub3['dosage_mg'])
ols_3 = sm.OLS(sub3['response'], X3).fit()
rlm_3 = sm.RLM(sub3['response'], X3, M=sm.robust.norms.HuberT()).fit()
print(f"  OLS: intercept={ols_3.params[0]:.3f}, slope={ols_3.params[1]:.3f}, R²={ols_3.rsquared:.4f}")
print(f"  RLM: intercept={rlm_3.params[0]:.3f}, slope={rlm_3.params[1]:.3f}")

# PLOT 7: Robust vs OLS for Q3
fig, ax = plt.subplots(figsize=(8, 6))
x = sub3['dosage_mg'].values
y = sub3['response'].values
ax.scatter(x, y, s=80, alpha=0.8, edgecolors='k', linewidth=0.5, zorder=5)
x_fit = np.linspace(3, 15, 100)
ax.plot(x_fit, ols_3.params[1] * x_fit + ols_3.params[0], 'r--', linewidth=2, label='OLS')
ax.plot(x_fit, rlm_3.params[1] * x_fit + rlm_3.params[0], 'b-', linewidth=2, label='Robust (Huber)')
# Highlight outlier
outlier_mask = sub3['response'] == sub3['response'].max()
outlier = sub3[outlier_mask]
ax.scatter(outlier['dosage_mg'], outlier['response'], s=150, facecolors='none', edgecolors='red', linewidth=2, zorder=6, label='Influential outlier')
ax.set_title('batch_Q3: OLS vs Robust Regression', fontweight='bold')
ax.set_xlabel('Dosage (mg)')
ax.set_ylabel('Response')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('plots/07_robust_vs_ols_Q3.png', dpi=150, bbox_inches='tight')
plt.close()
print("Plot 7 done")

print("\nAll analysis complete.")
