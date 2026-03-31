"""Step 1: Data inspection and basic EDA."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('dataset.csv')

print("=== SHAPE ===")
print(df.shape)

print("\n=== DTYPES ===")
print(df.dtypes.value_counts())
print("\nNon-numeric columns:")
print(df.select_dtypes(exclude='number').dtypes)

print("\n=== NULLS ===")
print(f"Total nulls: {df.isnull().sum().sum()}")
null_cols = df.isnull().sum()
null_cols = null_cols[null_cols > 0]
if len(null_cols) > 0:
    print(null_cols)
else:
    print("No missing values")

print("\n=== DUPLICATES ===")
print(f"Duplicate rows: {df.duplicated().sum()}")
print(f"Duplicate sample_ids: {df['sample_id'].duplicated().sum()}")

print("\n=== OUTCOME DISTRIBUTION ===")
print(df['outcome'].value_counts())
print(f"Outcome balance: {df['outcome'].mean():.3f}")

print("\n=== SEX DISTRIBUTION ===")
print(df['sex'].value_counts())

print("\n=== AGE STATS ===")
print(df['age'].describe())

print("\n=== GENE EXPRESSION SUMMARY (across all gene columns) ===")
gene_cols = [c for c in df.columns if c.startswith('gene_')]
print(f"Number of gene features: {len(gene_cols)}")
gene_data = df[gene_cols]
print(f"Global mean: {gene_data.values.mean():.4f}")
print(f"Global std: {gene_data.values.std():.4f}")
print(f"Global min: {gene_data.values.min():.4f}")
print(f"Global max: {gene_data.values.max():.4f}")

# Check for constant or near-constant features
stds = gene_data.std()
print(f"\nGene std range: [{stds.min():.4f}, {stds.max():.4f}]")
print(f"Near-constant genes (std < 0.1): {(stds < 0.1).sum()}")

# Check for extreme outliers
z_scores = (gene_data - gene_data.mean()) / gene_data.std()
extreme = (z_scores.abs() > 5).sum().sum()
print(f"\nExtreme outliers (|z| > 5): {extreme} cells out of {gene_data.size}")

print("\n=== PER-GENE STATS (first 10) ===")
print(gene_data.describe().iloc[:, :10])

# Check if data appears standardized per gene
print("\n=== STANDARDIZATION CHECK ===")
means = gene_data.mean()
print(f"Gene means range: [{means.min():.4f}, {means.max():.4f}]")
print(f"Gene stds range: [{stds.min():.4f}, {stds.max():.4f}]")

# Outcome by sex and age
print("\n=== OUTCOME BY SEX ===")
print(pd.crosstab(df['sex'], df['outcome'], margins=True))
print(pd.crosstab(df['sex'], df['outcome'], normalize='index'))

print("\n=== AGE BY OUTCOME ===")
print(df.groupby('outcome')['age'].describe())
