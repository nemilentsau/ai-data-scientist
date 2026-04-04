# Rental Listing Dataset Analysis

## What the dataset is about

This dataset contains **1,200 rental listings** with one row per listing and nine original columns: listing ID, size (`sq_ft`), room counts, distance to the city center, construction year, two binary amenity flags (`has_parking`, `pet_friendly`), and monthly asking rent in USD.

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
- A size-only linear model achieves **R² = 0.897** on the full data.
- A full linear model with all predictors reaches **R² = 0.910**.
- Under 5-fold cross-validation, the full model averages **R² = 0.908** versus **0.896** for the size-only model.

That means the extra features improve out-of-sample fit by only about **0.013 R² points** beyond square footage alone. [plot_01_rent_vs_sqft.png](./plots/plot_01_rent_vs_sqft.png) shows why: listings fall close to a single upward-sloping line.

In the multivariable OLS model, the estimated coefficient on `sq_ft` is **$1.143 per sq ft** (95% CI **$1.110 to $1.176**, p < 0.001). [plot_04_standardized_coefficients.png](./plots/plot_04_standardized_coefficients.png) confirms that `sq_ft` is by far the dominant standardized effect.

**Interpretation.** This looks less like a messy housing market and more like a pricing rule in which rent is largely constructed from floor area, with smaller add-ons for room counts.

### 2. The apparent parking discount is a composition effect, not convincing evidence that parking lowers rent

**Hypothesis.** Listings with parking appear cheaper in the raw averages, but that gap should mostly disappear once comparable-size units are contrasted.

**Test.** I compared the raw difference in mean rent by parking status, then stratified listings into square-footage quartiles to hold size roughly constant.

**Result.**

- Raw mean rent is **$1,672** for listings with parking versus **$1,801** without parking, a difference of **-$128** (Welch t-test p = **0.025**).
- That raw difference is misleading because parking is mixed with size and listing composition.
- Within the smallest size quartile, parking listings are actually slightly *more* expensive (**$774 vs $761**).
- In the remaining quartiles, the gaps are small relative to overall rent levels:
  - Q2: **$1,176 vs $1,192**
  - Q3: **$1,769 vs $1,827**
  - Q4: **$3,169 vs $3,229**

[plot_02_parking_by_size_quartile.png](./plots/plot_02_parking_by_size_quartile.png) makes the key point clear: once size is controlled coarsely, parking has no stable directional effect. In the full OLS model the parking coefficient is **$-26.9** with p = **0.122**, which is not statistically persuasive.

**Interpretation.** The raw parking discount is best understood as confounding, not as a causal parking penalty.

### 3. Location, building age, and pet policy carry surprisingly little signal after accounting for size and room counts

**Hypothesis.** In real rental markets, central locations and newer buildings usually command higher prices. If those effects are present here, they should appear in rent per square foot or in adjusted multivariable models.

**Test.** I analyzed `rent_per_sqft` against `distance_to_center_km` and fit an OLS model for rent per square foot using location, room counts, age, and amenities.

**Result.**

- `rent_per_sqft` averages **$1.479** and varies relatively little (SD **$0.281**).
- The Pearson correlation between `rent_per_sqft` and `distance_to_center_km` is only **0.062** (p = **0.031**).
- In the adjusted rent-per-square-foot model, the coefficient on distance is **$0.0033 per km** with p = **0.031**.
- The model explains almost none of the variance in rent per square foot: **R² = 0.006**.
- In the main rent model, `distance_to_center_km` (p = **0.900**), `year_built` (p = **0.218**), and `pet_friendly` (p = **0.784**) are all weak.

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
