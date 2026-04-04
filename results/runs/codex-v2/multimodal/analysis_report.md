# Rental Listing Analysis

## What This Dataset Appears To Be

The dataset contains **1,200 rental listings** and **9 columns**, all numeric and with **no missing values**. The fields describe unit size (`sq_ft`), layout (`bedrooms`, `bathrooms`), simple amenities (`has_parking`, `pet_friendly`), age (`year_built`), distance from a city center, and the target outcome `monthly_rent_usd`.

The data look internally consistent: `bathrooms` only takes values 1-3, `bedrooms` ranges from 0-4, and `listing_id` is a pure identifier with one unique value per row. There are no timestamps, neighborhood names, or repeated-listing structures, so the analysis is limited to cross-sectional pricing patterns. The clean schema and absence of messy real-world fields suggest this may be a curated or simulated housing dataset rather than raw marketplace data.

## Key Findings

### 1. Unit size is the dominant driver of rent

Rent and square footage have a **very strong raw correlation of 0.947**, far larger than any other feature. In the multivariable linear model, each additional square foot is associated with about **$1.14 higher monthly rent** on average, holding the other measured fields constant.

`rent_vs_sqft.png` shows the main relationship: the cloud is wide enough to indicate pricing noise, but the overall trend is strongly linear. This is not just visually strong; the full linear model reaches **R^2 = 0.910** in-sample, and even a model using **square footage alone** reaches a mean **5-fold cross-validated R^2 of 0.896** (`cv_model_comparison.png`).

Interpretation: in this dataset, floor area explains most of the pricing variation. Any narrative that centers amenities or building age ahead of size would be inconsistent with the observed data.

### 2. Layout matters beyond raw size, but its effect is much smaller than square footage

After controlling for square footage and the other columns, each additional bedroom is associated with roughly **$115 more rent per month** and each additional bathroom with about **$51**. Both effects are statistically detectable in the full model (`p < 0.05`), but they are much smaller than the size effect.

This means that two equally large units are not priced identically: one with a more segmented layout still tends to command somewhat higher rent. The standardized coefficient plot in `adjusted_coefficients.png` makes the scale difference clear: `sq_ft` dominates, while `bedrooms` is a clear but secondary contributor and `bathrooms` is smaller again.

Interpretation: the market represented here values both total space and how that space is configured, but configuration adds an incremental premium rather than defining the price level by itself.

### 3. Distance, parking, pet policy, and building age add little measurable signal once size and layout are known

Several variables that often matter in real housing markets are surprisingly weak here:

- `distance_to_center_km` has a raw correlation with rent of only **-0.049** and an adjusted coefficient of **0.21** dollars per km (**p = 0.900**).
- `year_built` is also not statistically distinguishable from zero in the linear model.
- `has_parking` looks important in raw averages because units without parking average **$1801** rent versus **$1672** with parking, but that difference largely disappears after adjustment: **-26.89** dollars (**p = 0.122**).
- `pet_friendly` is effectively null both descriptively and in the regression (**-4.84**, **p = 0.784**).

`distance_partial_regression.png` shows why the location result is weak: once size, room count, and the other measured fields are removed, there is little residual slope left for distance. `cv_model_comparison.png` reinforces the same point from a prediction angle: adding every non-size feature increases mean cross-validated **R^2** from **0.896** to **0.908**, only a modest lift.

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
