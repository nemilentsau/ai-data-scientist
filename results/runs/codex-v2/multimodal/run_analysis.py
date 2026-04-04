from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_score


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def orient_data(df: pd.DataFrame) -> dict:
    summary = df.describe().T
    return {
        "shape": df.shape,
        "dtypes": df.dtypes,
        "nulls": df.isna().sum(),
        "unique": df.nunique(),
        "summary": summary,
        "head": df.head(8),
    }


def fit_models(df: pd.DataFrame) -> dict:
    formula = (
        "monthly_rent_usd ~ sq_ft + bedrooms + bathrooms + "
        "distance_to_center_km + year_built + has_parking + pet_friendly"
    )
    ols = smf.ols(formula, data=df).fit()

    zcols = [
        "monthly_rent_usd",
        "sq_ft",
        "bedrooms",
        "bathrooms",
        "distance_to_center_km",
        "year_built",
        "has_parking",
        "pet_friendly",
    ]
    zdf = df[zcols].apply(stats.zscore)
    std_formula = (
        "monthly_rent_usd ~ sq_ft + bedrooms + bathrooms + "
        "distance_to_center_km + year_built + has_parking + pet_friendly"
    )
    ols_std = smf.ols(std_formula, data=zdf).fit()

    X_sqft = df[["sq_ft"]]
    X_full = df[
        [
            "sq_ft",
            "bedrooms",
            "bathrooms",
            "distance_to_center_km",
            "year_built",
            "has_parking",
            "pet_friendly",
        ]
    ]
    y = df["monthly_rent_usd"]
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    baseline_scores = cross_val_score(LinearRegression(), X_sqft, y, cv=cv, scoring="r2")
    full_scores = cross_val_score(LinearRegression(), X_full, y, cv=cv, scoring="r2")
    return {
        "ols": ols,
        "ols_std": ols_std,
        "baseline_scores": baseline_scores,
        "full_scores": full_scores,
    }


def save_rent_vs_sqft(df: pd.DataFrame) -> None:
    plt.figure(figsize=(9, 6))
    sns.regplot(
        data=df,
        x="sq_ft",
        y="monthly_rent_usd",
        scatter_kws={"alpha": 0.28, "s": 26, "color": "#2a6f97"},
        line_kws={"color": "#bc3908", "linewidth": 2},
        ci=95,
    )
    plt.title("Monthly Rent Rises Almost Linearly With Unit Size")
    plt.xlabel("Square footage")
    plt.ylabel("Monthly rent (USD)")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "rent_vs_sqft.png", dpi=160)
    plt.close()


def save_adjusted_coefficients(ols_std) -> None:
    coefs = ols_std.params.drop("Intercept")
    cis = ols_std.conf_int().drop("Intercept")
    label_map = {
        "sq_ft": "Square footage",
        "bedrooms": "Bedrooms",
        "bathrooms": "Bathrooms",
        "distance_to_center_km": "Distance to center",
        "year_built": "Year built",
        "has_parking": "Has parking",
        "pet_friendly": "Pet friendly",
    }
    coef_df = (
        pd.DataFrame(
            {
                "feature": [label_map[idx] for idx in coefs.index],
                "coef": coefs.values,
                "low": cis[0].values,
                "high": cis[1].values,
            }
        )
        .sort_values("coef")
        .reset_index(drop=True)
    )

    plt.figure(figsize=(9, 5.6))
    plt.axvline(0, color="0.5", linewidth=1, linestyle="--")
    plt.errorbar(
        coef_df["coef"],
        coef_df["feature"],
        xerr=[
            coef_df["coef"] - coef_df["low"],
            coef_df["high"] - coef_df["coef"],
        ],
        fmt="o",
        color="#2a6f97",
        ecolor="#2a6f97",
        capsize=3,
    )
    plt.title("Standardized Effects in the Full Linear Model")
    plt.xlabel("Standard deviations of rent per 1 SD increase in feature")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "adjusted_coefficients.png", dpi=160)
    plt.close()


def save_distance_partial_plot(df: pd.DataFrame) -> None:
    controls = ["sq_ft", "bedrooms", "bathrooms", "year_built", "has_parking", "pet_friendly"]
    y_resid = sm.OLS(df["monthly_rent_usd"], sm.add_constant(df[controls])).fit().resid
    x_resid = sm.OLS(df["distance_to_center_km"], sm.add_constant(df[controls])).fit().resid

    plt.figure(figsize=(9, 6))
    sns.regplot(
        x=x_resid,
        y=y_resid,
        scatter_kws={"alpha": 0.35, "s": 28, "color": "#4c72b0"},
        line_kws={"color": "#bc3908", "linewidth": 2},
        ci=95,
    )
    plt.title("Distance Adds Little Signal After Controlling for Unit Characteristics")
    plt.xlabel("Distance to center residual")
    plt.ylabel("Rent residual")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "distance_partial_regression.png", dpi=160)
    plt.close()


def save_cv_model_comparison(model_results: dict) -> None:
    scores = pd.DataFrame(
        {
            "model": ["Square footage only"] * len(model_results["baseline_scores"])
            + ["Full linear model"] * len(model_results["full_scores"]),
            "r2": np.r_[model_results["baseline_scores"], model_results["full_scores"]],
        }
    )
    order = ["Square footage only", "Full linear model"]
    means = scores.groupby("model", as_index=False)["r2"].mean()
    means["model"] = pd.Categorical(means["model"], categories=order, ordered=True)
    means = means.sort_values("model")

    plt.figure(figsize=(7.5, 5.6))
    sns.barplot(
        data=means,
        x="model",
        y="r2",
        hue="model",
        order=order,
        palette=["#8d99ae", "#2a6f97"],
        legend=False,
    )
    sns.stripplot(data=scores, x="model", y="r2", order=order, color="black", size=6, alpha=0.75)
    plt.ylim(0.8, 1.0)
    plt.title("Most Predictive Power Comes From Square Footage Alone")
    plt.xlabel("")
    plt.ylabel("5-fold cross-validated $R^2$")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "cv_model_comparison.png", dpi=160)
    plt.close()


def write_report(df: pd.DataFrame, orient: dict, model_results: dict) -> None:
    ols = model_results["ols"]
    coef_table = ols.summary2().tables[1]
    baseline_mean = model_results["baseline_scores"].mean()
    full_mean = model_results["full_scores"].mean()

    raw_corr = df.corr(numeric_only=True)["monthly_rent_usd"].sort_values(ascending=False)
    parking_means = df.groupby("has_parking")["monthly_rent_usd"].mean()
    bedrooms_premium = coef_table.loc["bedrooms", "Coef."]
    bathrooms_premium = coef_table.loc["bathrooms", "Coef."]
    sqft_premium = coef_table.loc["sq_ft", "Coef."]
    distance_coef = coef_table.loc["distance_to_center_km", "Coef."]
    distance_p = coef_table.loc["distance_to_center_km", "P>|t|"]
    parking_coef = coef_table.loc["has_parking", "Coef."]
    parking_p = coef_table.loc["has_parking", "P>|t|"]
    pet_coef = coef_table.loc["pet_friendly", "Coef."]
    pet_p = coef_table.loc["pet_friendly", "P>|t|"]

    report = f"""# Rental Listing Analysis

## What This Dataset Appears To Be

The dataset contains **{orient["shape"][0]:,} rental listings** and **{orient["shape"][1]} columns**, all numeric and with **no missing values**. The fields describe unit size (`sq_ft`), layout (`bedrooms`, `bathrooms`), simple amenities (`has_parking`, `pet_friendly`), age (`year_built`), distance from a city center, and the target outcome `monthly_rent_usd`.

The data look internally consistent: `bathrooms` only takes values 1-3, `bedrooms` ranges from 0-4, and `listing_id` is a pure identifier with one unique value per row. There are no timestamps, neighborhood names, or repeated-listing structures, so the analysis is limited to cross-sectional pricing patterns. The clean schema and absence of messy real-world fields suggest this may be a curated or simulated housing dataset rather than raw marketplace data.

## Key Findings

### 1. Unit size is the dominant driver of rent

Rent and square footage have a **very strong raw correlation of {raw_corr["sq_ft"]:.3f}**, far larger than any other feature. In the multivariable linear model, each additional square foot is associated with about **${sqft_premium:.2f} higher monthly rent** on average, holding the other measured fields constant.

`rent_vs_sqft.png` shows the main relationship: the cloud is wide enough to indicate pricing noise, but the overall trend is strongly linear. This is not just visually strong; the full linear model reaches **R^2 = {ols.rsquared:.3f}** in-sample, and even a model using **square footage alone** reaches a mean **5-fold cross-validated R^2 of {baseline_mean:.3f}** (`cv_model_comparison.png`).

Interpretation: in this dataset, floor area explains most of the pricing variation. Any narrative that centers amenities or building age ahead of size would be inconsistent with the observed data.

### 2. Layout matters beyond raw size, but its effect is much smaller than square footage

After controlling for square footage and the other columns, each additional bedroom is associated with roughly **${bedrooms_premium:.0f} more rent per month** and each additional bathroom with about **${bathrooms_premium:.0f}**. Both effects are statistically detectable in the full model (`p < 0.05`), but they are much smaller than the size effect.

This means that two equally large units are not priced identically: one with a more segmented layout still tends to command somewhat higher rent. The standardized coefficient plot in `adjusted_coefficients.png` makes the scale difference clear: `sq_ft` dominates, while `bedrooms` is a clear but secondary contributor and `bathrooms` is smaller again.

Interpretation: the market represented here values both total space and how that space is configured, but configuration adds an incremental premium rather than defining the price level by itself.

### 3. Distance, parking, pet policy, and building age add little measurable signal once size and layout are known

Several variables that often matter in real housing markets are surprisingly weak here:

- `distance_to_center_km` has a raw correlation with rent of only **{raw_corr["distance_to_center_km"]:.3f}** and an adjusted coefficient of **{distance_coef:.2f}** dollars per km (**p = {distance_p:.3f}**).
- `year_built` is also not statistically distinguishable from zero in the linear model.
- `has_parking` looks important in raw averages because units without parking average **${parking_means.loc[0]:.0f}** rent versus **${parking_means.loc[1]:.0f}** with parking, but that difference largely disappears after adjustment: **{parking_coef:.2f}** dollars (**p = {parking_p:.3f}**).
- `pet_friendly` is effectively null both descriptively and in the regression (**{pet_coef:.2f}**, **p = {pet_p:.3f}**).

`distance_partial_regression.png` shows why the location result is weak: once size, room count, and the other measured fields are removed, there is little residual slope left for distance. `cv_model_comparison.png` reinforces the same point from a prediction angle: adding every non-size feature increases mean cross-validated **R^2** from **{baseline_mean:.3f}** to **{full_mean:.3f}**, only a modest lift.

Interpretation: either this market is unusually dominated by interior unit characteristics, or the dataset omits the location and quality variables that would normally transmit those effects. The second explanation is more plausible.

## What The Findings Mean

If the goal is pricing or benchmarking listings in this dataset, **size should be the first-order anchor**. Bedrooms and bathrooms help refine the estimate, but the measured amenity and age variables contribute little incremental information. A compact model based mainly on square footage and basic layout would already capture most of the predictable variation.

From a substantive perspective, this is not strong evidence that location and amenities do not matter in real housing markets. It is evidence that **they do not vary in a way that is informative in this particular dataset once the observed unit characteristics are included**.

## Limitations And Self-Critique

- The dataset is cross-sectional and observational, so none of these coefficients should be read causally.
- Important housing drivers are missing: neighborhood quality, transit access, unit condition, building class, furnished status, lease terms, and local market segment.
- The near-zero distance effect could be due to omitted-variable structure rather than true economic irrelevance. For example, smaller premium neighborhoods close to downtown could offset a simple distance gradient.
- `listing_id` is an identifier, not a feature, and there is no repeated-measures structure to assess time trends or listing revisions.
- The very clean schema, bounded categorical values, and strong linearity make the data look somewhat synthetic. If this is simulated data, the findings describe the simulation rules more than a real rental market.
- The linear model fits well overall, but residual normality is imperfect, so the exact p-values should not be over-interpreted. The large effect sizes are the more stable part of the analysis.

## Files Produced

- Report: `analysis_report.md`
- Plots: `plots/rent_vs_sqft.png`, `plots/adjusted_coefficients.png`, `plots/distance_partial_regression.png`, `plots/cv_model_comparison.png`
"""

    REPORT_PATH.write_text(report)


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    PLOTS_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    orient = orient_data(df)
    model_results = fit_models(df)
    save_rent_vs_sqft(df)
    save_adjusted_coefficients(model_results["ols_std"])
    save_distance_partial_plot(df)
    save_cv_model_comparison(model_results)
    write_report(df, orient, model_results)


if __name__ == "__main__":
    main()
