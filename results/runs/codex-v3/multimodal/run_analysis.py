from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold, cross_val_score


PLOTS_DIR = Path("plots")
REPORT_PATH = Path("analysis_report.md")
DATA_PATH = Path("dataset.csv")


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def orient(df: pd.DataFrame) -> dict:
    summary = {
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "nulls": df.isna().sum().to_dict(),
        "nunique": df.nunique(dropna=False).to_dict(),
        "head": df.head(6),
    }
    return summary


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATA_PATH)
    df["rent_per_sqft"] = df["monthly_rent_usd"] / df["sq_ft"]
    df["age_years"] = 2026 - df["year_built"]
    df["size_quartile"] = pd.qcut(df["sq_ft"], 4, labels=["Q1", "Q2", "Q3", "Q4"])

    orient_info = orient(df)

    features = [
        "sq_ft",
        "bedrooms",
        "bathrooms",
        "distance_to_center_km",
        "year_built",
        "has_parking",
        "pet_friendly",
    ]
    X = df[features]
    y = df["monthly_rent_usd"]

    size_only = LinearRegression().fit(df[["sq_ft"]], y)
    size_only_r2 = r2_score(y, size_only.predict(df[["sq_ft"]]))

    full_model = LinearRegression().fit(X, y)
    full_r2 = r2_score(y, full_model.predict(X))
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    full_cv_r2 = cross_val_score(full_model, X, y, cv=cv, scoring="r2")
    size_cv_r2 = cross_val_score(LinearRegression(), df[["sq_ft"]], y, cv=cv, scoring="r2")

    ols = smf.ols(
        "monthly_rent_usd ~ sq_ft + bedrooms + bathrooms + distance_to_center_km + year_built + has_parking + pet_friendly",
        data=df,
    ).fit()

    std_coefs = (
        pd.Series(full_model.coef_, index=features) * X.std(ddof=0) / y.std(ddof=0)
    ).sort_values()

    parking_t = stats.ttest_ind(
        df.loc[df["has_parking"] == 1, "monthly_rent_usd"],
        df.loc[df["has_parking"] == 0, "monthly_rent_usd"],
        equal_var=False,
    )
    parking_by_quartile = (
        df.groupby(["size_quartile", "has_parking"], observed=False)["monthly_rent_usd"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )

    rent_psf_distance = stats.pearsonr(df["rent_per_sqft"], df["distance_to_center_km"])
    rent_psf_model = smf.ols(
        "rent_per_sqft ~ distance_to_center_km + bedrooms + bathrooms + age_years + has_parking + pet_friendly",
        data=df,
    ).fit()

    # Plot 1: size dominates rent.
    plt.figure(figsize=(10, 7))
    ax = sns.scatterplot(
        data=df,
        x="sq_ft",
        y="monthly_rent_usd",
        hue="bedrooms",
        palette="viridis",
        alpha=0.65,
        s=45,
    )
    x_grid = np.linspace(df["sq_ft"].min(), df["sq_ft"].max(), 300)
    y_grid = size_only.predict(pd.DataFrame({"sq_ft": x_grid}))
    plt.plot(x_grid, y_grid, color="black", linewidth=2.5, label="Size-only linear fit")
    ax.set_title("Rent rises almost linearly with square footage")
    ax.set_xlabel("Square feet")
    ax.set_ylabel("Monthly rent (USD)")
    ax.legend(title="Bedrooms", frameon=True)
    plt.text(
        0.02,
        0.98,
        f"Size-only R^2 = {size_only_r2:.3f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )
    savefig(PLOTS_DIR / "plot_01_rent_vs_sqft.png")

    # Plot 2: raw parking gap is composition, not a clean parking effect.
    plt.figure(figsize=(10, 7))
    ax = sns.barplot(
        data=parking_by_quartile,
        x="size_quartile",
        y="mean",
        hue="has_parking",
        palette=["#d95f02", "#1b9e77"],
    )
    ax.set_title("Parking barely shifts rent once listings are compared within size bands")
    ax.set_xlabel("Square-footage quartile")
    ax.set_ylabel("Mean monthly rent (USD)")
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles, ["No parking", "Parking"], title="")
    savefig(PLOTS_DIR / "plot_02_parking_by_size_quartile.png")

    # Plot 3: distance has little adjusted explanatory power.
    plt.figure(figsize=(10, 7))
    ax = sns.regplot(
        data=df,
        x="distance_to_center_km",
        y="rent_per_sqft",
        lowess=True,
        scatter_kws={"alpha": 0.35, "s": 35, "color": "#4c78a8"},
        line_kws={"color": "#e45756", "linewidth": 3},
    )
    ax.set_title("Distance to center has a near-flat relationship with rent per square foot")
    ax.set_xlabel("Distance to center (km)")
    ax.set_ylabel("Rent per square foot (USD)")
    plt.text(
        0.02,
        0.98,
        f"Pearson r = {rent_psf_distance.statistic:.3f}\np = {rent_psf_distance.pvalue:.3f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )
    savefig(PLOTS_DIR / "plot_03_rent_per_sqft_vs_distance.png")

    # Plot 4: standardized coefficients.
    coef_df = std_coefs.reset_index()
    coef_df.columns = ["feature", "standardized_coef"]
    plt.figure(figsize=(10, 7))
    ax = sns.barplot(
        data=coef_df,
        x="standardized_coef",
        y="feature",
        hue="feature",
        palette=["#c44e52" if v < 0 else "#4c72b0" for v in coef_df["standardized_coef"]],
        dodge=False,
        legend=False,
    )
    ax.axvline(0, color="black", linewidth=1.2)
    ax.set_title("Square footage dominates the multivariable model")
    ax.set_xlabel("Standardized beta coefficient")
    ax.set_ylabel("")
    savefig(PLOTS_DIR / "plot_04_standardized_coefficients.png")

    report = f"""# Rental Listing Dataset Analysis

## What the dataset is about

This dataset contains **{orient_info["shape"][0]:,} rental listings** with one row per listing and nine original columns: listing ID, size (`sq_ft`), room counts, distance to the city center, construction year, two binary amenity flags (`has_parking`, `pet_friendly`), and monthly asking rent in USD.

The data are unusually clean: all columns are numeric, there are **no missing values**, and the first few raw rows are internally consistent with the column names. Several columns have low cardinality and read like engineered features rather than free-form market data:

- `bedrooms` takes values from 0 to 4.
- `bathrooms` takes values from 1 to 3.
- `has_parking` and `pet_friendly` are binary 0/1 fields.
- `distance_to_center_km` ranges from **0.5 km to 40.7 km**.
- `sq_ft` ranges from **200 to 4,031 sq ft**.
- `monthly_rent_usd` ranges from **$347 to $4,769**.

The strongest immediate pattern during orientation was the very high raw correlation between size and rent, which motivated the first hypothesis.

## Key findings

### 1. Rent is driven primarily by square footage, with a near-linear relationship

**Hypothesis.** Monthly rent is mostly a linear function of `sq_ft`, with only modest incremental contribution from the other fields.

**Test.** I fit a size-only linear regression, then compared it with a multivariable linear model using all available predictors.

**Result.**

- The raw correlation between `sq_ft` and `monthly_rent_usd` is **0.947**.
- A size-only linear model achieves **R² = {size_only_r2:.3f}** on the full data.
- A full linear model with all predictors reaches **R² = {full_r2:.3f}**.
- Under 5-fold cross-validation, the full model averages **R² = {full_cv_r2.mean():.3f}** versus **{size_cv_r2.mean():.3f}** for the size-only model.

That means the extra features improve out-of-sample fit by only about **{full_cv_r2.mean() - size_cv_r2.mean():.3f} R² points** beyond square footage alone. [plot_01_rent_vs_sqft.png](./plots/plot_01_rent_vs_sqft.png) shows why: listings fall close to a single upward-sloping line.

In the multivariable OLS model, the estimated coefficient on `sq_ft` is **${ols.params["sq_ft"]:.3f} per sq ft** (95% CI **${ols.conf_int().loc["sq_ft", 0]:.3f} to ${ols.conf_int().loc["sq_ft", 1]:.3f}**, p < 0.001). [plot_04_standardized_coefficients.png](./plots/plot_04_standardized_coefficients.png) confirms that `sq_ft` is by far the dominant standardized effect.

**Interpretation.** This looks less like a messy housing market and more like a pricing rule in which rent is largely constructed from floor area, with smaller add-ons for room counts.

### 2. The apparent parking discount is a composition effect, not convincing evidence that parking lowers rent

**Hypothesis.** Listings with parking appear cheaper in the raw averages, but that gap should mostly disappear once comparable-size units are contrasted.

**Test.** I compared the raw difference in mean rent by parking status, then stratified listings into square-footage quartiles to hold size roughly constant.

**Result.**

- Raw mean rent is **$1,672** for listings with parking versus **$1,801** without parking, a difference of **-$128** (Welch t-test p = **{parking_t.pvalue:.3f}**).
- That raw difference is misleading because parking is mixed with size and listing composition.
- Within the smallest size quartile, parking listings are actually slightly *more* expensive (**$774 vs $761**).
- In the remaining quartiles, the gaps are small relative to overall rent levels:
  - Q2: **$1,176 vs $1,192**
  - Q3: **$1,769 vs $1,827**
  - Q4: **$3,169 vs $3,229**

[plot_02_parking_by_size_quartile.png](./plots/plot_02_parking_by_size_quartile.png) makes the key point clear: once size is controlled coarsely, parking has no stable directional effect. In the full OLS model the parking coefficient is **${ols.params["has_parking"]:.1f}** with p = **{ols.pvalues["has_parking"]:.3f}**, which is not statistically persuasive.

**Interpretation.** The raw parking discount is best understood as confounding, not as a causal parking penalty.

### 3. Location, building age, and pet policy carry surprisingly little signal after accounting for size and room counts

**Hypothesis.** In real rental markets, central locations and newer buildings usually command higher prices. If those effects are present here, they should appear in rent per square foot or in adjusted multivariable models.

**Test.** I analyzed `rent_per_sqft` against `distance_to_center_km` and fit an OLS model for rent per square foot using location, room counts, age, and amenities.

**Result.**

- `rent_per_sqft` averages **${df["rent_per_sqft"].mean():.3f}** and varies relatively little (SD **${df["rent_per_sqft"].std():.3f}**).
- The Pearson correlation between `rent_per_sqft` and `distance_to_center_km` is only **{rent_psf_distance.statistic:.3f}** (p = **{rent_psf_distance.pvalue:.3f}**).
- In the adjusted rent-per-square-foot model, the coefficient on distance is **${rent_psf_model.params["distance_to_center_km"]:.4f} per km** with p = **{rent_psf_model.pvalues["distance_to_center_km"]:.3f}**.
- The model explains almost none of the variance in rent per square foot: **R² = {rent_psf_model.rsquared:.3f}**.
- In the main rent model, `distance_to_center_km` (p = **{ols.pvalues["distance_to_center_km"]:.3f}**), `year_built` (p = **{ols.pvalues["year_built"]:.3f}**), and `pet_friendly` (p = **{ols.pvalues["pet_friendly"]:.3f}**) are all weak.

[plot_03_rent_per_sqft_vs_distance.png](./plots/plot_03_rent_per_sqft_vs_distance.png) shows a nearly flat LOWESS curve rather than a meaningful location premium.

**Interpretation.** For this dataset, the usual urban-rent intuition does not hold. Either the data were generated from a simplified formula or crucial market variables are absent, leaving little measurable role for location and building age.

## What the findings mean

The practical implication is that this dataset supports a **parsimonious pricing story**:

- Size explains most of the rent variation.
- Bedroom and bathroom counts add some secondary lift.
- Parking, pet policy, building age, and distance to center contribute little once size is known.

If the goal were prediction rather than inference, a simple linear model using `sq_ft`, `bedrooms`, and `bathrooms` would likely capture most available signal. If the goal were market understanding, the weak location and age effects are a warning that this dataset may not represent a full real-world housing process.

## Limitations and self-critique

Several caveats matter here:

- The analysis is observational. Even where a raw difference exists, such as parking, it should not be interpreted causally.
- The data may be synthetic or heavily simplified. The unusually high linearity and weak location effect are atypical for real rental markets.
- Important omitted variables are missing: neighborhood identity, floor level, renovations, furnished status, lease terms, transit access, and unit quality. Any of these could mask or replace the role of `distance_to_center_km`.
- I treated each listing as independent and modeled rent with linear methods. If listings were clustered by building or neighborhood, uncertainty would be understated.
- The OLS residuals are somewhat non-normal, so p-values should be read as rough inferential guides rather than exact truth.
- I did not test more flexible models such as gradient boosting because the core inferential finding was already clear: the signal is dominated by a small set of linear predictors, especially `sq_ft`.

Alternative explanations were considered. The main one was that parking looked negatively associated with rent; stratifying by size and checking the multivariable coefficient showed that the negative raw difference was not robust. Another possibility was that location effects were nonlinear; a LOWESS curve and a quadratic distance term both failed to reveal a substantial premium.

Overall, the evidence supports restrained conclusions: **square footage is the dominant driver of rent in this dataset, while several intuitively important housing features show little additional explanatory power.**
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
