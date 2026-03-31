import pandas as pd
import numpy as np

df = pd.read_csv("dataset.csv")

print("=== SHAPE ===")
print(df.shape)

print("\n=== DTYPES ===")
print(df.dtypes)

print("\n=== NULL COUNTS ===")
print(df.isnull().sum())

print("\n=== BASIC STATS ===")
print(df.describe().to_string())

print("\n=== VALUE COUNTS FOR BINARY/CATEGORICAL ===")
for col in ["has_parking", "pet_friendly", "bedrooms", "bathrooms"]:
    print(f"\n{col}:")
    print(df[col].value_counts().sort_index())

print("\n=== FIRST FEW DUPLICATES CHECK ===")
print(f"Duplicate rows: {df.duplicated().sum()}")
print(f"Duplicate listing_id: {df['listing_id'].duplicated().sum()}")

print("\n=== CORRELATION MATRIX ===")
print(df.drop(columns="listing_id").corr().round(3).to_string())

print("\n=== SKEWNESS ===")
print(df.drop(columns="listing_id").skew().round(3))

print("\n=== POTENTIAL OUTLIERS (IQR method) ===")
for col in ["sq_ft", "bedrooms", "bathrooms", "distance_to_center_km", "year_built", "monthly_rent_usd"]:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = df[(df[col] < lower) | (df[col] > upper)]
    print(f"{col}: {len(outliers)} outliers (range [{lower:.1f}, {upper:.1f}])")
