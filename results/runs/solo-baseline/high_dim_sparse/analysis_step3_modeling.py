"""Step 3: Modeling and validation."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.model_selection import StratifiedKFold, cross_val_score, learning_curve
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (roc_auc_score, classification_report, confusion_matrix,
                             roc_curve, precision_recall_curve, average_precision_score)
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_classif
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('dataset.csv')
gene_cols = [c for c in df.columns if c.startswith('gene_')]

# Prepare features
X_genes = df[gene_cols].values
X_age = df['age'].values.reshape(-1, 1)
X_sex = (df['sex'] == 'M').astype(int).values.reshape(-1, 1)
X_all = np.hstack([X_genes, X_age, X_sex])
y = df['outcome'].values

feature_names_all = gene_cols + ['age', 'sex_M']

# Key genes identified in EDA
key_genes = ['gene_000', 'gene_001', 'gene_002']
X_key = df[key_genes].values

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

print("=" * 60)
print("MODEL COMPARISON (10-fold Stratified CV)")
print("=" * 60)

# --- Model 1: Logistic Regression on key 3 genes only ---
pipe_lr_key = Pipeline([
    ('scaler', StandardScaler()),
    ('lr', LogisticRegression(max_iter=1000, random_state=42))
])
scores_lr_key = cross_val_score(pipe_lr_key, X_key, y, cv=cv, scoring='roc_auc')
print(f"\n1. Logistic Regression (3 key genes):")
print(f"   AUC: {scores_lr_key.mean():.4f} ± {scores_lr_key.std():.4f}")

# --- Model 2: Logistic Regression on all features ---
pipe_lr_all = Pipeline([
    ('scaler', StandardScaler()),
    ('lr', LogisticRegression(max_iter=1000, random_state=42))
])
scores_lr_all = cross_val_score(pipe_lr_all, X_all, y, cv=cv, scoring='roc_auc')
print(f"\n2. Logistic Regression (all 102 features):")
print(f"   AUC: {scores_lr_all.mean():.4f} ± {scores_lr_all.std():.4f}")

# --- Model 3: L1-regularized Logistic Regression (feature selection) ---
pipe_l1 = Pipeline([
    ('scaler', StandardScaler()),
    ('lr', LogisticRegressionCV(penalty='l1', solver='saga', cv=5, max_iter=5000,
                                 random_state=42, Cs=20))
])
scores_l1 = cross_val_score(pipe_l1, X_all, y, cv=cv, scoring='roc_auc')
print(f"\n3. L1-Regularized Logistic Regression (all features):")
print(f"   AUC: {scores_l1.mean():.4f} ± {scores_l1.std():.4f}")

# Fit L1 to see selected features
pipe_l1.fit(X_all, y)
l1_coefs = pipe_l1.named_steps['lr'].coef_[0]
selected = np.where(np.abs(l1_coefs) > 1e-6)[0]
print(f"   Selected features ({len(selected)}):")
for idx in selected:
    print(f"     {feature_names_all[idx]}: coef={l1_coefs[idx]:.4f}")

# --- Model 4: Random Forest on all features ---
pipe_rf = Pipeline([
    ('rf', RandomForestClassifier(n_estimators=500, max_depth=10, random_state=42, n_jobs=-1))
])
scores_rf = cross_val_score(pipe_rf, X_all, y, cv=cv, scoring='roc_auc')
print(f"\n4. Random Forest (all 102 features):")
print(f"   AUC: {scores_rf.mean():.4f} ± {scores_rf.std():.4f}")

# --- Model 5: 3 key genes + age + sex ---
X_clinical = np.hstack([X_key, X_age, X_sex])
pipe_clin = Pipeline([
    ('scaler', StandardScaler()),
    ('lr', LogisticRegression(max_iter=1000, random_state=42))
])
scores_clin = cross_val_score(pipe_clin, X_clinical, y, cv=cv, scoring='roc_auc')
print(f"\n5. Logistic Regression (3 key genes + age + sex):")
print(f"   AUC: {scores_clin.mean():.4f} ± {scores_clin.std():.4f}")

# --- Model 6: Gradient Boosting ---
pipe_gb = Pipeline([
    ('gb', GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.1,
                                       random_state=42))
])
scores_gb = cross_val_score(pipe_gb, X_all, y, cv=cv, scoring='roc_auc')
print(f"\n6. Gradient Boosting (all features):")
print(f"   AUC: {scores_gb.mean():.4f} ± {scores_gb.std():.4f}")

# Cross-val accuracy for best model
scores_acc_key = cross_val_score(pipe_lr_key, X_key, y, cv=cv, scoring='accuracy')
print(f"\n--- Best parsimonious model (LR, 3 key genes) ---")
print(f"Accuracy: {scores_acc_key.mean():.4f} ± {scores_acc_key.std():.4f}")

# --- Plot 7: Model comparison ---
fig, ax = plt.subplots(figsize=(10, 6))
model_names = [
    'LR (3 genes)',
    'LR (all)',
    'L1-LR (all)',
    'RF (all)',
    'LR (3 genes+demo)',
    'GB (all)'
]
all_scores = [scores_lr_key, scores_lr_all, scores_l1, scores_rf, scores_clin, scores_gb]
bp = ax.boxplot([s for s in all_scores], labels=model_names, patch_artist=True)
colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#00BCD4', '#F44336']
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax.set_ylabel('ROC AUC')
ax.set_title('Model Comparison (10-fold CV)')
ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='Random')
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig('plots/07_model_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved 07_model_comparison.png")

# --- Plot 8: ROC Curve (best model, full data fit for illustration) ---
pipe_lr_key.fit(X_key, y)
y_prob = pipe_lr_key.predict_proba(X_key)[:, 1]
fpr, tpr, _ = roc_curve(y, y_prob)
roc_auc = roc_auc_score(y, y_prob)

# Also cross-validated ROC
from sklearn.model_selection import cross_val_predict
y_prob_cv = cross_val_predict(
    Pipeline([('scaler', StandardScaler()),
              ('lr', LogisticRegression(max_iter=1000, random_state=42))]),
    X_key, y, cv=cv, method='predict_proba')[:, 1]
fpr_cv, tpr_cv, _ = roc_curve(y, y_prob_cv)
roc_auc_cv = roc_auc_score(y, y_prob_cv)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

axes[0].plot(fpr, tpr, label=f'Train AUC = {roc_auc:.3f}')
axes[0].plot(fpr_cv, tpr_cv, label=f'CV AUC = {roc_auc_cv:.3f}', linestyle='--')
axes[0].plot([0, 1], [0, 1], 'k--', alpha=0.5)
axes[0].set_xlabel('False Positive Rate')
axes[0].set_ylabel('True Positive Rate')
axes[0].set_title('ROC Curve - LR (3 Key Genes)')
axes[0].legend()

# Precision-Recall curve
precision, recall, _ = precision_recall_curve(y, y_prob_cv)
ap = average_precision_score(y, y_prob_cv)
axes[1].plot(recall, precision, label=f'CV AP = {ap:.3f}')
axes[1].set_xlabel('Recall')
axes[1].set_ylabel('Precision')
axes[1].set_title('Precision-Recall Curve - LR (3 Key Genes)')
axes[1].axhline(y.mean(), color='gray', linestyle='--', label=f'Baseline = {y.mean():.3f}')
axes[1].legend()

plt.tight_layout()
plt.savefig('plots/08_roc_pr_curves.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 08_roc_pr_curves.png")

# --- Plot 9: Confusion matrix ---
y_pred_cv = (y_prob_cv >= 0.5).astype(int)
cm = confusion_matrix(y, y_pred_cv)
fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
            xticklabels=['Predicted 0', 'Predicted 1'],
            yticklabels=['Actual 0', 'Actual 1'])
ax.set_title('Confusion Matrix (Cross-Validated)')
plt.tight_layout()
plt.savefig('plots/09_confusion_matrix.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 09_confusion_matrix.png")
print(f"\nClassification Report (CV predictions):\n{classification_report(y, y_pred_cv)}")

# --- Plot 10: Learning curve ---
train_sizes, train_scores, val_scores = learning_curve(
    Pipeline([('scaler', StandardScaler()),
              ('lr', LogisticRegression(max_iter=1000, random_state=42))]),
    X_key, y, cv=cv, scoring='roc_auc',
    train_sizes=np.linspace(0.1, 1.0, 10), n_jobs=-1
)
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(train_sizes, train_scores.mean(axis=1), 'o-', label='Train AUC')
ax.fill_between(train_sizes, train_scores.mean(axis=1) - train_scores.std(axis=1),
                train_scores.mean(axis=1) + train_scores.std(axis=1), alpha=0.1)
ax.plot(train_sizes, val_scores.mean(axis=1), 'o-', label='Validation AUC')
ax.fill_between(train_sizes, val_scores.mean(axis=1) - val_scores.std(axis=1),
                val_scores.mean(axis=1) + val_scores.std(axis=1), alpha=0.1)
ax.set_xlabel('Training Set Size')
ax.set_ylabel('ROC AUC')
ax.set_title('Learning Curve - LR (3 Key Genes)')
ax.legend()
plt.tight_layout()
plt.savefig('plots/10_learning_curve.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved 10_learning_curve.png")

# --- Fitted model coefficients for report ---
print("\n=== FINAL MODEL DETAILS (LR on 3 key genes) ===")
pipe_lr_key.fit(X_key, y)
lr = pipe_lr_key.named_steps['lr']
scaler = pipe_lr_key.named_steps['scaler']
print(f"Intercept: {lr.intercept_[0]:.4f}")
for name, coef in zip(key_genes, lr.coef_[0]):
    print(f"  {name}: coef={coef:.4f}")

# --- Random Forest feature importance ---
pipe_rf.fit(X_all, y)
importances = pipe_rf.named_steps['rf'].feature_importances_
imp_df = pd.DataFrame({'feature': feature_names_all, 'importance': importances})
imp_df = imp_df.sort_values('importance', ascending=False)

fig, ax = plt.subplots(figsize=(10, 6))
top_imp = imp_df.head(15)
ax.barh(range(len(top_imp)), top_imp['importance'].values, color='steelblue')
ax.set_yticks(range(len(top_imp)))
ax.set_yticklabels(top_imp['feature'].values)
ax.invert_yaxis()
ax.set_xlabel('Feature Importance (Gini)')
ax.set_title('Random Forest - Top 15 Feature Importances')
plt.tight_layout()
plt.savefig('plots/11_rf_feature_importance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved 11_rf_feature_importance.png")
print(f"\nTop 10 RF features:\n{imp_df.head(10).to_string()}")
