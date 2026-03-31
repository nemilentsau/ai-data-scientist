import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import cross_val_score, KFold
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
import statsmodels.api as sm
from scipy import stats

df = pd.read_csv("dataset.csv").drop(columns="listing_id")
sns.set_theme(style="whitegrid")

# ============ Check for non-linear relationships ============
# The Breusch-Pagan test was significant, suggesting heteroscedasticity.
# The residual skew (0.76) and kurtosis (4.29) suggest heavier tails.
# Let's check if there's a non-linear sqft relationship.

# Fit with sq_ft^2 term
df["sq_ft_sq"] = df["sq_ft"] ** 2
features_poly = ["sq_ft", "sq_ft_sq", "bedrooms", "bathrooms", "distance_to_center_km", "year_built", "has_parking", "pet_friendly"]
X_poly = sm.add_constant(df[features_poly])
ols_poly = sm.OLS(df["monthly_rent_usd"], X_poly).fit()
print("=== OLS with sq_ft² ===")
print(f"R² = {ols_poly.rsquared:.4f}, Adj-R² = {ols_poly.rsquared_adj:.4f}")
print(f"sq_ft coef = {ols_poly.params['sq_ft']:.4f}, p = {ols_poly.pvalues['sq_ft']:.4f}")
print(f"sq_ft² coef = {ols_poly.params['sq_ft_sq']:.6f}, p = {ols_poly.pvalues['sq_ft_sq']:.4f}")

# ============ Interaction: sq_ft x bedrooms ============
df["sqft_x_bed"] = df["sq_ft"] * df["bedrooms"]
features_inter = ["sq_ft", "bedrooms", "bathrooms", "distance_to_center_km", "year_built", 
                  "has_parking", "pet_friendly", "sqft_x_bed"]
X_inter = sm.add_constant(df[features_inter])
ols_inter = sm.OLS(df["monthly_rent_usd"], X_inter).fit()
print(f"\n=== OLS with sq_ft × bedrooms interaction ===")
print(f"R² = {ols_inter.rsquared:.4f}, Adj-R² = {ols_inter.rsquared_adj:.4f}")
print(f"sqft_x_bed coef = {ols_inter.params['sqft_x_bed']:.6f}, p = {ols_inter.pvalues['sqft_x_bed']:.4f}")

# ============ Log transform approach ============
df["log_rent"] = np.log(df["monthly_rent_usd"])
df["log_sqft"] = np.log(df["sq_ft"])

X_log = sm.add_constant(df[["log_sqft", "bedrooms", "bathrooms", "distance_to_center_km", 
                             "year_built", "has_parking", "pet_friendly"]])
ols_log = sm.OLS(df["log_rent"], X_log).fit()
print(f"\n=== Log-Log Model (log rent ~ log sqft + ...) ===")
print(ols_log.summary())

# Check heteroscedasticity after log transform
from statsmodels.stats.diagnostic import het_breuschpagan
bp_stat, bp_p, _, _ = het_breuschpagan(ols_log.resid, X_log)
print(f"\nBreusch-Pagan on log model: stat={bp_stat:.4f}, p={bp_p:.6f}")

# Normality after log
stat_jb, p_jb = stats.jarque_bera(ols_log.resid)[:2]
print(f"Jarque-Bera on log model: stat={stat_jb:.4f}, p={p_jb:.6f}")

# ============ Residual analysis by segment ============
features_base = ["sq_ft", "bedrooms", "bathrooms", "distance_to_center_km", "year_built", "has_parking", "pet_friendly"]
X_base = sm.add_constant(df[features_base])
ols_base = sm.OLS(df["monthly_rent_usd"], X_base).fit()
df["residual"] = ols_base.resid

# Residual by bedrooms
print("\n=== Mean Residual by Bedrooms ===")
print(df.groupby("bedrooms")["residual"].agg(["mean", "std", "count"]).round(1))

# Residual by bathrooms
print("\n=== Mean Residual by Bathrooms ===")
print(df.groupby("bathrooms")["residual"].agg(["mean", "std", "count"]).round(1))

# Check if there's a rent premium for combinations
print("\n=== Mean Rent and SqFt by Bedrooms ===")
grouped = df.groupby("bedrooms").agg(
    mean_rent=("monthly_rent_usd", "mean"),
    mean_sqft=("sq_ft", "mean"),
    mean_price_per_sqft=("monthly_rent_usd", lambda x: (x / df.loc[x.index, "sq_ft"]).mean()),
    count=("monthly_rent_usd", "count")
).round(1)
print(grouped)

# ============ Random Forest - partial dependence ============
from sklearn.inspection import partial_dependence

rf = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
rf.fit(df[features_base], df["monthly_rent_usd"])

fig, axes = plt.subplots(2, 4, figsize=(18, 8))
for i, feat in enumerate(features_base):
    ax = axes[i//4, i%4]
    pdp = partial_dependence(rf, df[features_base], [i], kind="average")
    ax.plot(pdp["grid_values"][0], pdp["average"][0], linewidth=2)
    ax.set_xlabel(feat)
    ax.set_ylabel("Partial Dependence")
    ax.set_title(f"PDP: {feat}")

# Remove empty subplot
axes[1, 3].axis("off")
plt.suptitle("Partial Dependence Plots (Random Forest)", fontsize=14)
plt.tight_layout()
plt.savefig("plots/10_partial_dependence.png", dpi=150)
plt.close()

# ============ Residuals by predicted range ============
fig, ax = plt.subplots(figsize=(8, 5))
df["fitted"] = ols_base.fittedvalues
df["abs_resid"] = np.abs(df["residual"])
bins = pd.cut(df["fitted"], bins=10)
grouped_resid = df.groupby(bins)["abs_resid"].mean()
grouped_resid.plot(kind="bar", ax=ax, alpha=0.7, edgecolor="black")
ax.set_xlabel("Fitted Value Range")
ax.set_ylabel("Mean Absolute Residual")
ax.set_title("Mean |Residual| by Fitted Value Range (Heteroscedasticity Check)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig("plots/11_residual_by_range.png", dpi=150)
plt.close()

print("\nDeep analysis complete. All plots saved.")
