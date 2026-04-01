"""
Comprehensive EDA and modeling for hospital patient dataset.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", palette="muted")

# ── 1. Load & Inspect ──────────────────────────────────────────────
df = pd.read_csv("dataset.csv")
print("=" * 60)
print("SHAPE:", df.shape)
print("\nDTYPES:")
print(df.dtypes)
print("\nFIRST 5 ROWS:")
print(df.head())
print("\nBASIC STATS:")
print(df.describe(include='all').to_string())
print("\nNULL COUNTS:")
print(df.isnull().sum())
print("\nDUPLICATES:", df.duplicated().sum())
print("\nDuplicate patient_ids:", df['patient_id'].duplicated().sum())

# Value counts for categoricals
for col in ['department', 'treatment', 'readmitted']:
    print(f"\n{col} value counts:")
    print(df[col].value_counts())

# ── 2. Distributions ───────────────────────────────────────────────
numeric_cols = ['age', 'severity_index', 'length_of_stay_days', 'recovery_score']

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
for ax, col in zip(axes.ravel(), numeric_cols):
    ax.hist(df[col], bins=30, edgecolor='black', alpha=0.7)
    ax.axvline(df[col].mean(), color='red', linestyle='--', label=f'Mean={df[col].mean():.1f}')
    ax.axvline(df[col].median(), color='green', linestyle='--', label=f'Median={df[col].median():.1f}')
    ax.set_title(f'Distribution of {col}')
    ax.legend()
fig.tight_layout()
fig.savefig('plots/01_distributions.png', dpi=150)
plt.close()

# Normality tests
print("\n\n── NORMALITY TESTS (Shapiro-Wilk on sample of 500) ──")
for col in numeric_cols:
    sample = df[col].dropna().sample(min(500, len(df)), random_state=42)
    stat, p = stats.shapiro(sample)
    print(f"  {col}: W={stat:.4f}, p={p:.4e} {'(normal)' if p > 0.05 else '(non-normal)'}")

# ── 3. Outlier detection ──────────────────────────────────────────
print("\n── OUTLIER DETECTION (IQR method) ──")
for col in numeric_cols:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = df[(df[col] < lower) | (df[col] > upper)]
    print(f"  {col}: {len(outliers)} outliers (range: [{lower:.2f}, {upper:.2f}])")

fig, axes = plt.subplots(1, 4, figsize=(16, 5))
for ax, col in zip(axes, numeric_cols):
    ax.boxplot(df[col].dropna(), vert=True)
    ax.set_title(col)
fig.suptitle('Boxplots for Outlier Detection', fontsize=14)
fig.tight_layout()
fig.savefig('plots/02_boxplots.png', dpi=150)
plt.close()

# ── 4. Relationships / Correlations ───────────────────────────────
print("\n── CORRELATION MATRIX ──")
corr = df[numeric_cols + ['readmitted']].corr()
print(corr.to_string())

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, fmt='.2f', ax=ax)
ax.set_title('Correlation Matrix')
fig.tight_layout()
fig.savefig('plots/03_correlation_heatmap.png', dpi=150)
plt.close()

# ── 5. Treatment Analysis ─────────────────────────────────────────
print("\n── TREATMENT vs DEPARTMENT ──")
ct = pd.crosstab(df['department'], df['treatment'])
print(ct)

# Is treatment assignment related to department?
chi2, p, dof, expected = stats.chi2_contingency(ct)
print(f"Chi-squared test: chi2={chi2:.2f}, p={p:.4e}, dof={dof}")

# Treatment vs outcomes
print("\n── TREATMENT vs OUTCOMES ──")
for outcome in ['recovery_score', 'length_of_stay_days', 'readmitted']:
    groupA = df[df['treatment'] == 'A'][outcome]
    groupB = df[df['treatment'] == 'B'][outcome]
    if outcome == 'readmitted':
        # Proportion test
        nA, nB = len(groupA), len(groupB)
        pA, pB = groupA.mean(), groupB.mean()
        print(f"  {outcome}: A={pA:.3f} ({int(groupA.sum())}/{nA}), B={pB:.3f} ({int(groupB.sum())}/{nB})")
        # Chi-squared for readmission
        ct2 = pd.crosstab(df['treatment'], df['readmitted'])
        chi2r, pr, _, _ = stats.chi2_contingency(ct2)
        print(f"    Chi-squared: chi2={chi2r:.2f}, p={pr:.4e}")
    else:
        t_stat, p_val = stats.ttest_ind(groupA, groupB, equal_var=False)
        mw_stat, mw_p = stats.mannwhitneyu(groupA, groupB, alternative='two-sided')
        print(f"  {outcome}: A mean={groupA.mean():.2f}, B mean={groupB.mean():.2f}")
        print(f"    Welch's t-test: t={t_stat:.2f}, p={p_val:.4e}")
        print(f"    Mann-Whitney U: U={mw_stat:.0f}, p={mw_p:.4e}")

# Treatment comparison plots
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
sns.boxplot(data=df, x='treatment', y='recovery_score', ax=axes[0])
axes[0].set_title('Recovery Score by Treatment')
sns.boxplot(data=df, x='treatment', y='length_of_stay_days', ax=axes[1])
axes[1].set_title('Length of Stay by Treatment')
ct_readmit = df.groupby('treatment')['readmitted'].mean()
axes[2].bar(ct_readmit.index, ct_readmit.values, color=['steelblue', 'coral'], edgecolor='black')
axes[2].set_title('Readmission Rate by Treatment')
axes[2].set_ylabel('Proportion Readmitted')
fig.tight_layout()
fig.savefig('plots/04_treatment_outcomes.png', dpi=150)
plt.close()

# ── 6. Department Analysis ────────────────────────────────────────
print("\n── DEPARTMENT vs OUTCOMES ──")
for outcome in ['recovery_score', 'length_of_stay_days', 'severity_index']:
    groups = [g[outcome].values for _, g in df.groupby('department')]
    f_stat, p_val = stats.f_oneway(*groups)
    kw_stat, kw_p = stats.kruskal(*groups)
    print(f"  {outcome}:")
    print(f"    ANOVA: F={f_stat:.2f}, p={p_val:.4e}")
    print(f"    Kruskal-Wallis: H={kw_stat:.2f}, p={kw_p:.4e}")
    for dept in df['department'].unique():
        m = df[df['department'] == dept][outcome].mean()
        print(f"      {dept}: mean={m:.2f}")

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
sns.boxplot(data=df, x='department', y='recovery_score', ax=axes[0])
axes[0].set_title('Recovery Score by Department')
sns.boxplot(data=df, x='department', y='length_of_stay_days', ax=axes[1])
axes[1].set_title('Length of Stay by Department')
sns.boxplot(data=df, x='department', y='severity_index', ax=axes[2])
axes[2].set_title('Severity Index by Department')
fig.tight_layout()
fig.savefig('plots/05_department_outcomes.png', dpi=150)
plt.close()

# ── 7. Severity deep-dive ────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Severity vs Recovery
axes[0].scatter(df['severity_index'], df['recovery_score'], alpha=0.3, s=10)
z = np.polyfit(df['severity_index'], df['recovery_score'], 1)
p_line = np.poly1d(z)
x_range = np.linspace(df['severity_index'].min(), df['severity_index'].max(), 100)
axes[0].plot(x_range, p_line(x_range), 'r-', linewidth=2)
r, p = stats.pearsonr(df['severity_index'], df['recovery_score'])
axes[0].set_title(f'Severity vs Recovery (r={r:.3f}, p={p:.2e})')
axes[0].set_xlabel('Severity Index')
axes[0].set_ylabel('Recovery Score')

# Severity vs LOS
axes[1].scatter(df['severity_index'], df['length_of_stay_days'], alpha=0.3, s=10)
z2 = np.polyfit(df['severity_index'], df['length_of_stay_days'], 1)
p_line2 = np.poly1d(z2)
axes[1].plot(x_range, p_line2(x_range), 'r-', linewidth=2)
r2, p2 = stats.pearsonr(df['severity_index'], df['length_of_stay_days'])
axes[1].set_title(f'Severity vs LOS (r={r2:.3f}, p={p2:.2e})')
axes[1].set_xlabel('Severity Index')
axes[1].set_ylabel('Length of Stay (days)')

# Severity by treatment
sns.kdeplot(data=df, x='severity_index', hue='treatment', ax=axes[2], fill=True, alpha=0.4)
axes[2].set_title('Severity Distribution by Treatment')

fig.tight_layout()
fig.savefig('plots/06_severity_analysis.png', dpi=150)
plt.close()

print(f"\n  Severity vs Recovery: r={r:.3f}, p={p:.2e}")
print(f"  Severity vs LOS: r={r2:.3f}, p={p2:.2e}")

# ── 8. Confounding: Is treatment assignment random? ───────────────
print("\n── CONFOUNDING CHECK ──")
for var in ['age', 'severity_index']:
    tA = df[df['treatment'] == 'A'][var]
    tB = df[df['treatment'] == 'B'][var]
    t_s, t_p = stats.ttest_ind(tA, tB, equal_var=False)
    print(f"  {var} by treatment: A={tA.mean():.2f}, B={tB.mean():.2f}, t={t_s:.2f}, p={t_p:.4e}")

# Department × treatment interaction
print("\n  Severity by department × treatment:")
for dept in df['department'].unique():
    sub = df[df['department'] == dept]
    for trt in ['A', 'B']:
        vals = sub[sub['treatment'] == trt]['severity_index']
        if len(vals) > 0:
            print(f"    {dept} × {trt}: n={len(vals)}, mean_severity={vals.mean():.2f}")

# ── 9. Age analysis ──────────────────────────────────────────────
df['age_group'] = pd.cut(df['age'], bins=[0, 35, 45, 55, 65, 100], labels=['<35', '35-45', '45-55', '55-65', '65+'])
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
age_recovery = df.groupby('age_group')['recovery_score'].mean()
age_recovery.plot(kind='bar', ax=axes[0], color='steelblue', edgecolor='black')
axes[0].set_title('Mean Recovery Score by Age Group')
axes[0].set_ylabel('Recovery Score')
axes[0].tick_params(axis='x', rotation=0)

age_readmit = df.groupby('age_group')['readmitted'].mean()
age_readmit.plot(kind='bar', ax=axes[1], color='coral', edgecolor='black')
axes[1].set_title('Readmission Rate by Age Group')
axes[1].set_ylabel('Proportion Readmitted')
axes[1].tick_params(axis='x', rotation=0)
fig.tight_layout()
fig.savefig('plots/07_age_analysis.png', dpi=150)
plt.close()

# ── 10. Pairplot ──────────────────────────────────────────────────
fig = sns.pairplot(df[numeric_cols + ['treatment']], hue='treatment',
                   plot_kws={'alpha': 0.3, 's': 15}, diag_kind='kde')
fig.savefig('plots/08_pairplot.png', dpi=100)
plt.close()

print("\n\nPlots saved. Proceeding to modeling...")
