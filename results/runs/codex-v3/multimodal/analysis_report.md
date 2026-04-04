# Rental Listing Analysis

## What this dataset is about

The dataset contains 1,200 rental listings and 9 original columns:

- `listing_id`
- `sq_ft`
- `bedrooms`
- `bathrooms`
- `distance_to_center_km`
- `year_built`
- `has_parking`
- `pet_friendly`
- `monthly_rent_usd`

The records appear to describe apartment listings. The schema is unusually clean: there are no missing values in any column, `listing_id` is unique for every row, and the binary features are encoded consistently as `0/1`. The raw rows are internally coherent with the column names: for example, studios (`bedrooms = 0`) tend to have smaller floor area and lower rent, while larger 3-4 bedroom units tend to be more expensive.

Key ranges and composition:

- Rent ranges from $347 to $4,769 per month, with mean $1,737 and median $1,515.50.
- Floor area ranges from 200 to 4,031 square feet, with median 998.
- Distance to center ranges from 0.5 km to 40.7 km, with median 3.7 km.
- Year built ranges from 1920 to 2023.
- Bedroom counts are moderately imbalanced but still broad: 237 studios, 372 one-bedroom, 248 two-bedroom, 250 three-bedroom, and 93 four-bedroom listings.
- Bathrooms are concentrated at 1 bath: 855 one-bath, 300 two-bath, and 45 three-bath listings.
- 49.3% of listings have parking and 40.0% are pet friendly.

Nothing in the orientation step suggested implicit missingness, bad type inference, or a hidden time-series / panel structure. This behaves like a cross-sectional housing dataset.

## Key findings

### 1. Rent is dominated by floor area

**Hypothesis:** Monthly rent is driven primarily by size, and a simple size-based relationship should explain most of the variation in rent.

**Test:** I examined the rent-vs-size relationship visually and fit linear models using `sq_ft` alone and then all available predictors.

**Result:** The hypothesis is strongly supported.

- The raw correlation between `sq_ft` and `monthly_rent_usd` is **0.947**.
- A univariate linear model using only `sq_ft` achieves **R^2 = 0.897**.
- The fitted univariate slope is about **$1.30 per square foot**.
- In the full linear model, the effect is still **$114.3 per additional 100 square feet** with 95% CI **[$111.0, $117.6]** and **p < 0.001**.

The visual evidence is in `plots/rent_vs_sqft.png`, which shows an almost linear upward relationship across the full size range.

**Interpretation:** Size is the first-order pricing variable in this dataset. Even before controlling for anything else, floor area alone explains nearly 90% of rent variation. This is unusually strong for real housing markets, where neighborhood and building quality usually matter more, so the dataset likely has a simplified or synthetic pricing structure.

### 2. After controlling for size, layout matters a bit, but location and amenities barely matter

**Hypothesis:** Once size is held constant, bedrooms and bathrooms may still carry some premium, but distance to center, building age, parking, and pet policy should have limited additional explanatory power.

**Test:** I fit a multivariable OLS model with `sq_ft`, `bedrooms`, `bathrooms`, `distance_to_center_km`, `year_built`, `has_parking`, and `pet_friendly`, then inspected coefficients and confidence intervals.

**Result:** The hypothesis is mostly supported.

- Full-model fit: **R^2 = 0.910**, adjusted **R^2 = 0.910**.
- `bedrooms`: **+$114.9** per additional bedroom, 95% CI **[$92.8, $136.9]**, **p < 0.001**.
- `bathrooms`: **+$51.3** per additional bathroom, 95% CI **[$9.2, $93.4]**, **p = 0.017**.
- `distance_to_center_km`: **+$0.21** per km, 95% CI **[-$3.03, $3.45]**, **p = 0.900**.
- `year_built`: **+$3.56** per 10 years, 95% CI **[-$2.10, $9.23]**, **p = 0.218**.
- `has_parking`: **-$26.9**, 95% CI **[-$60.9, $7.2]**, **p = 0.122**.
- `pet_friendly`: **-$4.8**, 95% CI **[-$39.5, $29.8]**, **p = 0.784**.

The adjusted coefficient plot in `plots/adjusted_effects.png` makes the practical ranking clear: square footage and room count matter; the other variables are near zero relative to the overall rent scale.

This result is not just a linear-model artifact. In 5-fold cross-validation:

- `sq_ft` only linear model: **R^2 = 0.896**, RMSE **$320.3**
- Full linear model: **R^2 = 0.908**, RMSE **$300.2**
- Random forest with all predictors: **R^2 = 0.917**, RMSE **$284.3**

The random forest improves performance only modestly over the full linear model, which suggests there is not much hidden nonlinear structure in the non-size variables. Permutation importance from the random forest also ranked `sq_ft` far above every other feature.

**Interpretation:** Layout carries a measurable premium beyond raw square footage, but the dataset does not show a meaningful downtown premium, vintage premium, parking premium, or pet-policy premium. In a real rental market, that would be surprising. Here it likely means those factors were either weakly simulated or intentionally excluded from the rent-generating process.

### 3. Larger units are slightly cheaper on a per-square-foot basis

**Hypothesis:** Although larger units have higher total rent, smaller units may command higher rent per square foot.

**Test:** I created `price_per_sqft = monthly_rent_usd / sq_ft` and regressed it on `sq_ft`, then checked whether the pattern was simply a bedroom-mix artifact.

**Result:** The hypothesis is supported, but the effect is modest.

- Average rent per square foot is **$1.48**.
- The slope of `price_per_sqft ~ sq_ft` is **-0.097 USD/sq ft per additional 1,000 square feet**, with **p < 1e-18**.
- The relationship is statistically strong but explains only **6.3%** of the variance in price per square foot.
- An ANOVA across bedroom groups was not significant for `price_per_sqft` (**p = 0.411**), so this pattern is not mainly a bedroom-count effect.

The plot `plots/price_per_sqft_vs_sqft.png` shows the downward trend clearly without overstating it.

**Interpretation:** This is a standard housing market pattern: smaller units are cheaper in total but less efficient on a per-area basis. The effect exists here, but it is much weaker than the total-rent effect of size.

## What the findings mean

The dataset behaves like a size-driven rental market with a small layout premium and very little evidence that location, age, or amenities affect price. If the goal is prediction, a simple linear model is already strong and interpretable. If the goal is market insight, the absence of a distance-to-center premium is the main substantive surprise.

Practically:

- For forecasting rent in this dataset, square footage is the essential variable.
- Bedrooms and bathrooms add useful but secondary information.
- Adding parking, pet rules, distance to center, or year built yields little marginal improvement.
- Analysts should be careful not to infer real-world urban economics from this dataset, because some variables that matter strongly in real rental markets appear nearly irrelevant here.

## Limitations and self-critique

### Assumptions and diagnostic issues

- The analysis treats listings as independent observations. If multiple rows came from the same building or landlord, that dependency is unmodeled.
- The OLS residuals are heteroskedastic. A Breusch-Pagan test strongly rejects constant variance (**p < 1e-43**), and `plots/residuals_vs_fitted.png` shows larger error spread for higher-rent units. Coefficient signs and relative magnitudes are still informative, but classical OLS standard errors should be interpreted with caution.
- Residuals are not perfectly normal, and the largest absolute residuals exceed **$1,000**, so there are meaningful outliers or unmodeled segments.

### Alternative explanations considered

- One alternative explanation for weak location effects is multicollinearity with size or room count. I checked predictor correlations and variance inflation factors; outside of the expected overlap between `sq_ft`, `bedrooms`, and `bathrooms`, multicollinearity was not severe. That makes it more likely that the location effect is genuinely weak in this dataset.
- Another alternative explanation is that the linear model is missing nonlinear market structure. Cross-validated random forests improved performance only slightly over the linear model, which argues against large hidden nonlinear effects.

### What I did not investigate

- I did not cluster listings into latent neighborhoods or submarkets because the dataset has no explicit geography beyond distance to center.
- I did not fit robust or quantile regressions, which could be useful given the heteroskedastic residuals.
- I did not test interaction terms such as `sq_ft x distance_to_center_km` or `bedrooms x bathrooms`. Those may explain a small part of the remaining error.
- I cannot make causal claims. These are observational associations, and the dataset contains no experimental variation.

## Bottom line

This dataset is best described as a clean, cross-sectional rental listing table where **rent is overwhelmingly explained by square footage**, **layout adds a smaller premium**, and **location / amenity variables contribute surprisingly little**. The strongest evidence is in `plots/rent_vs_sqft.png` and `plots/adjusted_effects.png`; the main caveat is in `plots/residuals_vs_fitted.png`, which shows that prediction error grows for expensive units.
