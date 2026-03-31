import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import statsmodels.api as sm
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv("dataset.csv").drop(columns="listing_id")
sns.set_theme(style="whitegrid")

features = ["sq_ft", "bedrooms", "bathrooms", "distance_to_center_km", "year_built", "has_parking", "pet_friendly"]
X = df[features]
y = df["monthly_rent_usd"]

# ============ OLS with statsmodels for diagnostics ============
X_sm = sm.add_constant(X)
ols_model = sm.OLS(y, X_sm).fit()
print("=" * 60)
print("OLS REGRESSION SUMMARY")
print("=" * 60)
print(ols_model.summary())

# Residual diagnostics
residuals = ols_model.resid
fitted = ols_model.fittedvalues

# VIF
from statsmodels.stats.outliers_influence import variance_inflation_factor
print("\n=== VIF (Variance Inflation Factors) ===")
for i, col in enumerate(features):
    vif = variance_inflation_factor(X_sm.values, i + 1)  # +1 because of const
    print(f"{col}: {vif:.2f}")

# Normality of residuals
stat_sw, p_sw = stats.shapiro(residuals[:500])  # Shapiro limited to 5000
stat_jb, p_jb = stats.jarque_bera(residuals)[:2]
print(f"\n=== Normality Tests on Residuals ===")
print(f"Shapiro-Wilk (first 500): stat={stat_sw:.4f}, p={p_sw:.6f}")
print(f"Jarque-Bera: stat={stat_jb:.4f}, p={p_jb:.6f}")

# Breusch-Pagan heteroscedasticity test
from statsmodels.stats.diagnostic import het_breuschpagan
bp_stat, bp_p, bp_f, bp_fp = het_breuschpagan(residuals, X_sm)
print(f"\n=== Breusch-Pagan Heteroscedasticity Test ===")
print(f"LM stat={bp_stat:.4f}, p={bp_p:.6f}")
print(f"F stat={bp_f:.4f}, p={bp_fp:.6f}")

# Durbin-Watson
from statsmodels.stats.stattools import durbin_watson
dw = durbin_watson(residuals)
print(f"\n=== Durbin-Watson: {dw:.4f} ===")

# ============ Residual Plots ============
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Residuals vs Fitted
axes[0,0].scatter(fitted, residuals, alpha=0.3, s=10)
axes[0,0].axhline(0, color="red", linestyle="--")
axes[0,0].set_xlabel("Fitted Values")
axes[0,0].set_ylabel("Residuals")
axes[0,0].set_title("Residuals vs Fitted")

# QQ plot
sm.qqplot(residuals, line="45", ax=axes[0,1], alpha=0.3, markersize=3)
axes[0,1].set_title("Q-Q Plot of Residuals")

# Histogram of residuals
axes[1,0].hist(residuals, bins=40, edgecolor="black", alpha=0.7)
axes[1,0].set_title("Residual Distribution")
axes[1,0].set_xlabel("Residual")

# Scale-Location plot
axes[1,1].scatter(fitted, np.sqrt(np.abs(residuals)), alpha=0.3, s=10)
axes[1,1].set_xlabel("Fitted Values")
axes[1,1].set_ylabel("√|Residuals|")
axes[1,1].set_title("Scale-Location Plot")

plt.tight_layout()
plt.savefig("plots/06_ols_diagnostics.png", dpi=150)
plt.close()

# ============ Model Comparison with Cross-Validation ============
print("\n" + "=" * 60)
print("MODEL COMPARISON (5-Fold Cross-Validation)")
print("=" * 60)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

models = {
    "Linear Regression": LinearRegression(),
    "Ridge (alpha=1)": Ridge(alpha=1),
    "Lasso (alpha=1)": Lasso(alpha=1),
    "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42),
}

kf = KFold(n_splits=5, shuffle=True, random_state=42)
results = {}

for name, model in models.items():
    if "Linear" in name or "Ridge" in name or "Lasso" in name:
        X_use = X_scaled
    else:
        X_use = X.values  # tree models don't need scaling
    
    r2_scores = cross_val_score(model, X_use, y, cv=kf, scoring="r2")
    rmse_scores = -cross_val_score(model, X_use, y, cv=kf, scoring="neg_root_mean_squared_error")
    mae_scores = -cross_val_score(model, X_use, y, cv=kf, scoring="neg_mean_absolute_error")
    
    results[name] = {
        "R2_mean": r2_scores.mean(), "R2_std": r2_scores.std(),
        "RMSE_mean": rmse_scores.mean(), "RMSE_std": rmse_scores.std(),
        "MAE_mean": mae_scores.mean(), "MAE_std": mae_scores.std(),
    }
    print(f"\n{name}:")
    print(f"  R² = {r2_scores.mean():.4f} ± {r2_scores.std():.4f}")
    print(f"  RMSE = {rmse_scores.mean():.1f} ± {rmse_scores.std():.1f}")
    print(f"  MAE = {mae_scores.mean():.1f} ± {mae_scores.std():.1f}")

# ============ Train/Test Split for best model ============
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Fit gradient boosting (likely best)
gb = GradientBoostingRegressor(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
gb.fit(X_train, y_train)
y_pred_gb = gb.predict(X_test)

print(f"\n=== Gradient Boosting on Test Set ===")
print(f"R²:   {r2_score(y_test, y_pred_gb):.4f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred_gb)):.1f}")
print(f"MAE:  {mean_absolute_error(y_test, y_pred_gb):.1f}")

# Feature importance
importances = gb.feature_importances_
sorted_idx = np.argsort(importances)[::-1]
print("\n=== Feature Importance (Gradient Boosting) ===")
for i in sorted_idx:
    print(f"  {features[i]:25s}: {importances[i]:.4f}")

# Also fit OLS on train for comparison
lr = LinearRegression()
lr.fit(X_train, y_train)
y_pred_lr = lr.predict(X_test)
print(f"\n=== Linear Regression on Test Set ===")
print(f"R²:   {r2_score(y_test, y_pred_lr):.4f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred_lr)):.1f}")
print(f"MAE:  {mean_absolute_error(y_test, y_pred_lr):.1f}")

print("\n=== OLS Coefficients ===")
for feat, coef in zip(features, lr.coef_):
    print(f"  {feat:25s}: {coef:.4f}")
print(f"  {'intercept':25s}: {lr.intercept_:.4f}")

# ============ Model comparison plot ============
fig, ax = plt.subplots(figsize=(10, 5))
model_names = list(results.keys())
r2_means = [results[m]["R2_mean"] for m in model_names]
r2_stds = [results[m]["R2_std"] for m in model_names]
bars = ax.barh(model_names, r2_means, xerr=r2_stds, alpha=0.7, edgecolor="black")
ax.set_xlabel("R² Score (5-Fold CV)")
ax.set_title("Model Comparison: Cross-Validated R²")
ax.set_xlim(0.85, 1.0)
for bar, val in zip(bars, r2_means):
    ax.text(val + 0.002, bar.get_y() + bar.get_height()/2, f"{val:.4f}", va="center", fontsize=10)
plt.tight_layout()
plt.savefig("plots/07_model_comparison.png", dpi=150)
plt.close()

# ============ Feature importance plot ============
fig, ax = plt.subplots(figsize=(8, 5))
sorted_features = [features[i] for i in sorted_idx]
sorted_importances = importances[sorted_idx]
ax.barh(sorted_features[::-1], sorted_importances[::-1], alpha=0.7, edgecolor="black", color="teal")
ax.set_xlabel("Feature Importance")
ax.set_title("Gradient Boosting Feature Importance")
plt.tight_layout()
plt.savefig("plots/08_feature_importance.png", dpi=150)
plt.close()

# ============ Predicted vs Actual ============
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, y_pred, name in zip(axes, [y_pred_lr, y_pred_gb], ["Linear Regression", "Gradient Boosting"]):
    ax.scatter(y_test, y_pred, alpha=0.4, s=15)
    lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
    ax.plot(lims, lims, "r--", linewidth=1)
    ax.set_xlabel("Actual Rent (USD)")
    ax.set_ylabel("Predicted Rent (USD)")
    ax.set_title(f"{name}: Predicted vs Actual")
    ax.set_aspect("equal")
plt.tight_layout()
plt.savefig("plots/09_predicted_vs_actual.png", dpi=150)
plt.close()

print("\nAll model analysis plots saved.")
