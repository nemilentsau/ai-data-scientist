import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("dataset.csv").drop(columns="listing_id")
sns.set_theme(style="whitegrid")

# --- Plot 1: Distribution of target ---
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].hist(df["monthly_rent_usd"], bins=40, edgecolor="black", alpha=0.7)
axes[0].set_title("Distribution of Monthly Rent")
axes[0].set_xlabel("Monthly Rent (USD)")
axes[0].set_ylabel("Frequency")

axes[1].hist(df["sq_ft"], bins=40, edgecolor="black", alpha=0.7, color="orange")
axes[1].set_title("Distribution of Square Footage")
axes[1].set_xlabel("Square Feet")
axes[1].set_ylabel("Frequency")
plt.tight_layout()
plt.savefig("plots/01_distributions.png", dpi=150)
plt.close()

# --- Plot 2: Correlation heatmap ---
fig, ax = plt.subplots(figsize=(10, 8))
corr = df.corr()
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax,
            square=True, linewidths=0.5)
ax.set_title("Correlation Matrix")
plt.tight_layout()
plt.savefig("plots/02_correlation_heatmap.png", dpi=150)
plt.close()

# --- Plot 3: Scatter matrix of key variables ---
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# sq_ft vs rent
axes[0,0].scatter(df["sq_ft"], df["monthly_rent_usd"], alpha=0.3, s=10)
axes[0,0].set_xlabel("Square Feet")
axes[0,0].set_ylabel("Monthly Rent (USD)")
axes[0,0].set_title("Rent vs Square Footage")

# bedrooms vs rent (boxplot)
df.boxplot(column="monthly_rent_usd", by="bedrooms", ax=axes[0,1])
axes[0,1].set_title("Rent by Bedrooms")
axes[0,1].set_xlabel("Bedrooms")
axes[0,1].set_ylabel("Monthly Rent (USD)")
plt.sca(axes[0,1])
plt.title("Rent by Bedrooms")

# bathrooms vs rent (boxplot)
df.boxplot(column="monthly_rent_usd", by="bathrooms", ax=axes[0,2])
axes[0,2].set_title("Rent by Bathrooms")
axes[0,2].set_xlabel("Bathrooms")
axes[0,2].set_ylabel("Monthly Rent (USD)")
plt.sca(axes[0,2])
plt.title("Rent by Bathrooms")

# distance vs rent
axes[1,0].scatter(df["distance_to_center_km"], df["monthly_rent_usd"], alpha=0.3, s=10)
axes[1,0].set_xlabel("Distance to Center (km)")
axes[1,0].set_ylabel("Monthly Rent (USD)")
axes[1,0].set_title("Rent vs Distance to Center")

# year_built vs rent
axes[1,1].scatter(df["year_built"], df["monthly_rent_usd"], alpha=0.3, s=10)
axes[1,1].set_xlabel("Year Built")
axes[1,1].set_ylabel("Monthly Rent (USD)")
axes[1,1].set_title("Rent vs Year Built")

# has_parking and pet_friendly vs rent
cats = df.groupby(["has_parking", "pet_friendly"])["monthly_rent_usd"].mean().unstack()
cats.plot(kind="bar", ax=axes[1,2])
axes[1,2].set_title("Mean Rent by Parking & Pet-Friendly")
axes[1,2].set_xlabel("Has Parking")
axes[1,2].set_ylabel("Mean Monthly Rent (USD)")
axes[1,2].legend(title="Pet Friendly")

plt.suptitle("")
plt.tight_layout()
plt.savefig("plots/03_scatter_relationships.png", dpi=150)
plt.close()

# --- Plot 4: Distributions of all continuous features ---
continuous = ["sq_ft", "bedrooms", "bathrooms", "distance_to_center_km", "year_built", "monthly_rent_usd"]
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for i, col in enumerate(continuous):
    ax = axes[i//3, i%3]
    ax.hist(df[col], bins=35, edgecolor="black", alpha=0.7)
    ax.set_title(f"Distribution of {col}")
    ax.axvline(df[col].mean(), color="red", linestyle="--", label=f"mean={df[col].mean():.1f}")
    ax.axvline(df[col].median(), color="green", linestyle="--", label=f"median={df[col].median():.1f}")
    ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig("plots/04_all_distributions.png", dpi=150)
plt.close()

# --- Plot 5: Price per sq_ft analysis ---
df["price_per_sqft"] = df["monthly_rent_usd"] / df["sq_ft"]
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].hist(df["price_per_sqft"], bins=40, edgecolor="black", alpha=0.7, color="green")
axes[0].set_title("Distribution of Price per Sq Ft")
axes[0].set_xlabel("Rent / Sq Ft (USD)")
axes[0].set_ylabel("Frequency")

axes[1].scatter(df["distance_to_center_km"], df["price_per_sqft"], alpha=0.3, s=10)
axes[1].set_xlabel("Distance to Center (km)")
axes[1].set_ylabel("Rent / Sq Ft (USD)")
axes[1].set_title("Price per SqFt vs Distance")
plt.tight_layout()
plt.savefig("plots/05_price_per_sqft.png", dpi=150)
plt.close()

print("EDA plots saved successfully.")
print(f"\nPrice per sqft stats:\n{df['price_per_sqft'].describe()}")
