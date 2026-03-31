import pandas as pd
import numpy as np

df = pd.read_csv("dataset.csv")
print("=== SHAPE ===")
print(df.shape)
print("\n=== DTYPES ===")
print(df.dtypes)
print("\n=== NULL COUNTS ===")
print(df.isnull().sum())
print("\n=== BASIC STATS (NUMERIC) ===")
print(df.describe().round(3))
print("\n=== CATEGORICAL VALUE COUNTS ===")
for col in ['batch', 'technician']:
    print(f"\n{col}:")
    print(df[col].value_counts().sort_index())
print("\n=== PER-BATCH SUMMARY OF dosage_mg and response ===")
for batch in sorted(df['batch'].unique()):
    sub = df[df['batch'] == batch]
    print(f"\n--- {batch} (n={len(sub)}) ---")
    print(f"  dosage_mg: mean={sub['dosage_mg'].mean():.2f}, var={sub['dosage_mg'].var():.2f}, "
          f"min={sub['dosage_mg'].min()}, max={sub['dosage_mg'].max()}")
    print(f"  response:  mean={sub['response'].mean():.2f}, var={sub['response'].var():.2f}, "
          f"min={sub['response'].min()}, max={sub['response'].max()}")
    corr = sub['dosage_mg'].corr(sub['response'])
    print(f"  correlation(dosage, response): {corr:.4f}")
    # Linear regression
    from numpy.polynomial.polynomial import polyfit
    b, m = polyfit(sub['dosage_mg'], sub['response'], 1)
    print(f"  OLS: response = {m:.3f} * dosage + {b:.3f}")
