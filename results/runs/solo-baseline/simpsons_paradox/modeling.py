"""
Modeling: regression for recovery_score and LOS, logistic for readmission.
Key challenge: treatment is confounded with department — must control for it.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, roc_curve
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", palette="muted")
df = pd.read_csv("dataset.csv")

# ══════════════════════════════════════════════════════════════════
# MODEL 1: Recovery Score (OLS)
# ══════════════════════════════════════════════════════════════════
print("=" * 60)
print("MODEL 1: Recovery Score ~ Severity + Age + Treatment + Department")
print("=" * 60)

# Naive model (no confounders)
m_naive = smf.ols('recovery_score ~ C(treatment)', data=df).fit()
print("\n── Naive model (treatment only) ──")
print(f"  Treatment B effect: {m_naive.params['C(treatment)[T.B]']:.3f} (p={m_naive.pvalues['C(treatment)[T.B]']:.4e})")
print(f"  R²: {m_naive.rsquared:.4f}")

# Full model
m_full = smf.ols('recovery_score ~ severity_index + age + C(treatment) + C(department)', data=df).fit()
print("\n── Full model ──")
print(m_full.summary().tables[1])
print(f"\n  R²: {m_full.rsquared:.4f}, Adj R²: {m_full.rsquared_adj:.4f}")
print(f"  AIC: {m_full.aic:.1f}, BIC: {m_full.bic:.1f}")

# Model with interaction terms
m_interact = smf.ols('recovery_score ~ severity_index * C(treatment) + age + C(department)', data=df).fit()
print("\n── Interaction model ──")
print(m_interact.summary().tables[1])
print(f"\n  R²: {m_interact.rsquared:.4f}, Adj R²: {m_interact.rsquared_adj:.4f}")

# Compare models with F-test
from scipy.stats import f as f_dist
ssr_reduced = m_full.ssr
ssr_full = m_interact.ssr
df_diff = m_interact.df_model - m_full.df_model
f_stat = ((ssr_reduced - ssr_full) / df_diff) / (ssr_full / m_interact.df_resid)
p_val = 1 - f_dist.cdf(f_stat, df_diff, m_interact.df_resid)
print(f"\n  F-test (interaction vs main effects): F={f_stat:.2f}, p={p_val:.4f}")

# Use the better model
best_model = m_full  # (interaction likely not significant)
if p_val < 0.05:
    best_model = m_interact
    print("  → Interaction model preferred")
else:
    print("  → Main effects model preferred (interaction not significant)")

# ── Diagnostics for best OLS model ──
print("\n── OLS Diagnostics ──")
residuals = best_model.resid
fitted = best_model.fittedvalues

# Residual normality
stat_sw, p_sw = stats.shapiro(residuals.sample(min(500, len(residuals)), random_state=42))
print(f"  Shapiro-Wilk on residuals: W={stat_sw:.4f}, p={p_sw:.4f}")

# Durbin-Watson
dw = sm.stats.durbin_watson(residuals)
print(f"  Durbin-Watson: {dw:.4f} (expect ~2 for no autocorrelation)")

# Breusch-Pagan (heteroscedasticity)
bp_test = sm.stats.diagnostic.het_breuschpagan(residuals, best_model.model.exog)
print(f"  Breusch-Pagan: LM={bp_test[0]:.2f}, p={bp_test[1]:.4f}")

# VIF
from statsmodels.stats.outliers_influence import variance_inflation_factor
X_vif = best_model.model.exog
vif_data = pd.DataFrame()
vif_data["Variable"] = best_model.model.exog_names
vif_data["VIF"] = [variance_inflation_factor(X_vif, i) for i in range(X_vif.shape[1])]
print("\n  VIF:")
for _, row in vif_data.iterrows():
    print(f"    {row['Variable']}: {row['VIF']:.2f}")

# Diagnostic plots
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Residuals vs Fitted
axes[0, 0].scatter(fitted, residuals, alpha=0.3, s=10)
axes[0, 0].axhline(y=0, color='r', linestyle='--')
axes[0, 0].set_xlabel('Fitted Values')
axes[0, 0].set_ylabel('Residuals')
axes[0, 0].set_title('Residuals vs Fitted')

# Q-Q plot
sm.qqplot(residuals, line='45', ax=axes[0, 1], alpha=0.3, markersize=3)
axes[0, 1].set_title('Q-Q Plot of Residuals')

# Scale-Location
axes[1, 0].scatter(fitted, np.sqrt(np.abs(residuals)), alpha=0.3, s=10)
axes[1, 0].set_xlabel('Fitted Values')
axes[1, 0].set_ylabel('√|Residuals|')
axes[1, 0].set_title('Scale-Location')

# Residuals distribution
axes[1, 1].hist(residuals, bins=30, edgecolor='black', alpha=0.7, density=True)
x_norm = np.linspace(residuals.min(), residuals.max(), 100)
axes[1, 1].plot(x_norm, stats.norm.pdf(x_norm, residuals.mean(), residuals.std()), 'r-', lw=2)
axes[1, 1].set_title('Residual Distribution')

fig.suptitle('Recovery Score Model - Diagnostics', fontsize=14)
fig.tight_layout()
fig.savefig('plots/09_recovery_diagnostics.png', dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════════════
# MODEL 2: Length of Stay (OLS)
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MODEL 2: LOS ~ Severity + Age + Treatment + Department")
print("=" * 60)

m_los = smf.ols('length_of_stay_days ~ severity_index + age + C(treatment) + C(department)', data=df).fit()
print(m_los.summary().tables[1])
print(f"\n  R²: {m_los.rsquared:.4f}, Adj R²: {m_los.rsquared_adj:.4f}")

# LOS diagnostics
resid_los = m_los.resid
bp_los = sm.stats.diagnostic.het_breuschpagan(resid_los, m_los.model.exog)
print(f"  Breusch-Pagan: LM={bp_los[0]:.2f}, p={bp_los[1]:.4f}")
print(f"  Durbin-Watson: {sm.stats.durbin_watson(resid_los):.4f}")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].scatter(m_los.fittedvalues, resid_los, alpha=0.3, s=10)
axes[0].axhline(y=0, color='r', linestyle='--')
axes[0].set_title('LOS Model: Residuals vs Fitted')
sm.qqplot(resid_los, line='45', ax=axes[1], alpha=0.3, markersize=3)
axes[1].set_title('LOS Model: Q-Q Plot')
fig.tight_layout()
fig.savefig('plots/10_los_diagnostics.png', dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════════════
# MODEL 3: Readmission (Logistic Regression)
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MODEL 3: Readmission ~ Severity + Age + LOS + Recovery + Treatment + Department")
print("=" * 60)

m_logit = smf.logit(
    'readmitted ~ severity_index + age + length_of_stay_days + recovery_score + C(treatment) + C(department)',
    data=df
).fit(disp=0)
print(m_logit.summary().tables[1])
print(f"\n  Pseudo R²: {m_logit.prsquared:.4f}")
print(f"  AIC: {m_logit.aic:.1f}")

# Odds ratios
print("\n  Odds Ratios:")
or_df = pd.DataFrame({
    'OR': np.exp(m_logit.params),
    'CI_lower': np.exp(m_logit.conf_int()[0]),
    'CI_upper': np.exp(m_logit.conf_int()[1]),
    'p-value': m_logit.pvalues
})
print(or_df.to_string())

# ROC curve
y_prob = m_logit.predict(df)
fpr, tpr, thresholds = roc_curve(df['readmitted'], y_prob)
auc = roc_auc_score(df['readmitted'], y_prob)

fig, ax = plt.subplots(figsize=(7, 6))
ax.plot(fpr, tpr, label=f'ROC (AUC = {auc:.3f})')
ax.plot([0, 1], [0, 1], 'k--', alpha=0.5)
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.set_title('ROC Curve - Readmission Model')
ax.legend()
fig.tight_layout()
fig.savefig('plots/11_readmission_roc.png', dpi=150)
plt.close()

print(f"\n  AUC (in-sample): {auc:.3f}")

# Cross-validated AUC
from sklearn.preprocessing import LabelEncoder
X_sk = df[['severity_index', 'age', 'length_of_stay_days', 'recovery_score']].copy()
X_sk['treatment_B'] = (df['treatment'] == 'B').astype(int)
dept_dummies = pd.get_dummies(df['department'], prefix='dept', drop_first=True)
X_sk = pd.concat([X_sk, dept_dummies], axis=1)
y_sk = df['readmitted']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_sk)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(
    LogisticRegression(max_iter=1000, random_state=42),
    X_scaled, y_sk, cv=cv, scoring='roc_auc'
)
print(f"  CV AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# ══════════════════════════════════════════════════════════════════
# MODEL 4: Within-department treatment effect (adjusting for confounding)
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MODEL 4: Treatment effect WITHIN each department")
print("=" * 60)

for dept in df['department'].unique():
    sub = df[df['department'] == dept]
    nA = (sub['treatment'] == 'A').sum()
    nB = (sub['treatment'] == 'B').sum()
    if nA < 10 or nB < 10:
        print(f"\n  {dept}: skipping (A={nA}, B={nB} - too few in one group)")
        continue
    m_dept = smf.ols('recovery_score ~ severity_index + age + C(treatment)', data=sub).fit()
    trt_coef = m_dept.params.get('C(treatment)[T.B]', np.nan)
    trt_p = m_dept.pvalues.get('C(treatment)[T.B]', np.nan)
    print(f"\n  {dept} (n_A={nA}, n_B={nB}):")
    print(f"    Treatment B effect on recovery: {trt_coef:.3f} (p={trt_p:.4f})")
    print(f"    R²: {m_dept.rsquared:.4f}")

# Neurology is the most balanced; let's look at it in detail
print("\n── Detailed: Neurology subgroup ──")
neuro = df[df['department'] == 'Neurology']
m_neuro = smf.ols('recovery_score ~ severity_index + age + C(treatment)', data=neuro).fit()
print(m_neuro.summary().tables[1])

# ══════════════════════════════════════════════════════════════════
# Summary coefficient plot
# ══════════════════════════════════════════════════════════════════
coef_df = pd.DataFrame({
    'Variable': best_model.params.index[1:],  # skip intercept
    'Coefficient': best_model.params.values[1:],
    'CI_lower': best_model.conf_int()[0].values[1:],
    'CI_upper': best_model.conf_int()[1].values[1:]
})

fig, ax = plt.subplots(figsize=(8, 5))
y_pos = range(len(coef_df))
ax.barh(y_pos, coef_df['Coefficient'], xerr=[
    coef_df['Coefficient'] - coef_df['CI_lower'],
    coef_df['CI_upper'] - coef_df['Coefficient']
], alpha=0.7, color='steelblue', capsize=3)
ax.set_yticks(y_pos)
ax.set_yticklabels(coef_df['Variable'])
ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
ax.set_xlabel('Coefficient (95% CI)')
ax.set_title('Recovery Score Model - Coefficients')
fig.tight_layout()
fig.savefig('plots/12_coefficient_plot.png', dpi=150)
plt.close()

# ══════════════════════════════════════════════════════════════════
# Effect size summary
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("EFFECT SIZE SUMMARY")
print("=" * 60)
print(f"""
Recovery Score Model (R²={best_model.rsquared:.3f}):
  - Severity index: {best_model.params['severity_index']:.2f} per unit (strongest predictor)
  - Age: {best_model.params['age']:.2f} per year
  - Treatment B (vs A): {best_model.params['C(treatment)[T.B]']:.2f} (p={best_model.pvalues['C(treatment)[T.B]']:.4f})
  - Dept Neurology (vs Cardiology): {best_model.params['C(department)[T.Neurology]']:.2f}
  - Dept Orthopedics (vs Cardiology): {best_model.params['C(department)[T.Orthopedics]']:.2f}

LOS Model (R²={m_los.rsquared:.3f}):
  - Severity index: {m_los.params['severity_index']:.2f} days per unit
  - Treatment B (vs A): {m_los.params['C(treatment)[T.B]']:.2f} days (p={m_los.pvalues['C(treatment)[T.B]']:.4f})

Readmission Model (Pseudo R²={m_logit.prsquared:.3f}):
  - AUC = {auc:.3f} (in-sample), CV AUC = {cv_scores.mean():.3f}
  - Readmission is weakly predicted by all available features
""")

print("All modeling complete.")
