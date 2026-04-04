# Housing Listings Analysis

## What This Dataset Is About

This dataset contains 800 residential property listings with a unique `listing_id`, structural attributes (`sq_ft`, `num_rooms`, `lot_size_acres`, `garage_spaces`, `year_built`), two location/amenity fields (`neighborhood`, `has_pool`), and the target variable `price_usd`.

The data is unusually clean: there are no missing values, all fields are already typed sensibly, and the raw rows are internally consistent with the column names. The main coding conventions to note are:

- `has_pool` is binary and stored as `0/1`.
- `neighborhood` has 5 levels: Downtown, Eastwood, Hillcrest, Lakeside, and Suburbs.
- `listing_id` is only an identifier and was excluded from modeling.

Selected ranges:

- `sq_ft`: 600 to 3,341
- `year_built`: 1950 to 2023
- `price_usd`: $83,600 to $496,700
- pool rate: 30.4%

## Key Findings

### 1. Square footage is the dominant driver of price

**Hypothesis:** Larger homes should sell for more, and this may explain most of the total price variation.

**Test:** Fit a simple OLS model, `price_usd ~ sq_ft`, and visualize the relationship in `plots/price_vs_sqft.png`.

**Result:** The relationship is very strong and close to linear.

- Estimated slope: **$148.9 per additional square foot**
- Model fit: **R² = 0.912**
- 10-fold cross-validated RMSE for the `sq_ft`-only model: **$18,111**

Interpretation: size alone explains about 91% of observed price variation, which is exceptionally high for real housing data. That makes square footage the main variable to control for before interpreting anything else.

### 2. Newer homes retain a positive price premium even after controlling for size

**Hypothesis:** Newer homes are worth more, but this effect may be hidden in raw correlations because square footage dominates the pricing signal.

**Test:** Extend the model to `price_usd ~ sq_ft + year_built` and inspect the residualized relationship in `plots/year_built_partial_effect.png`.

**Result:** `year_built` adds a clear independent effect.

- Estimated `sq_ft` coefficient in the two-variable model: **$148.9 per sq ft**
- Estimated `year_built` coefficient: **$521.7 per year**
- 95% CI for `year_built`: **$473.3 to $570.2 per year**
- Adjusted R² improves from **0.9118** to **0.9434**
- Nested-model test versus `sq_ft` alone: **F = 446.9, p = 4.23e-79**
- 10-fold CV RMSE improves from **$18,111** to **$14,510**

Interpretation: after controlling for size, a home built 10 years later is worth about **$5.2k more on average**. This is a meaningful effect, not just a statistically significant but trivial one.

### 3. Most other housing features are mostly proxies for size, and neighborhood/pool add little signal

**Hypothesis:** Variables like `num_rooms`, `lot_size_acres`, and `garage_spaces` look important individually, but they may mostly be measuring the same underlying “house size” construct. Likewise, `neighborhood` and `has_pool` may matter less than their names suggest.

**Test:** Examine the correlation structure (`plots/predictor_correlation_heatmap.png`), fit a fuller regression with all predictors plus neighborhood dummies, compare it to the simpler `sq_ft + year_built` model, and inspect neighborhood residuals in `plots/neighborhood_residuals.png`. Model generalization is compared in `plots/cv_model_comparison.png`.

**Result:** The data strongly supports the redundancy hypothesis.

Collinearity among structural variables is extreme:

- `corr(sq_ft, lot_size_acres) = 0.97`
- `corr(sq_ft, num_rooms) = 0.96`
- `corr(price_usd, sq_ft) = 0.95`
- VIFs: `sq_ft = 29.15`, `lot_size_acres = 17.16`, `num_rooms = 12.02`

In the full model, only `sq_ft` and `year_built` remain clearly significant:

- `num_rooms`: **p = 0.205**
- `lot_size_acres`: **p = 0.812**
- `garage_spaces`: **p = 0.990**
- `has_pool`: **p = 0.103**
- all neighborhood indicators: **p >= 0.233**

The extra variables do not materially improve out-of-sample prediction:

- `sq_ft + year_built` 10-fold CV RMSE: **$14,510**
- full model 10-fold CV RMSE: **$14,538**
- nested-model test, `sq_ft + year_built` versus full model: **F = 1.30, p = 0.238**

Raw group comparisons also show weak location/amenity effects:

- neighborhood ANOVA on raw prices: **p = 0.343**
- pool versus no-pool Welch t-test on raw prices: **p = 0.716**

Interpretation: the dataset behaves as if price is driven mainly by a compact structural rule: bigger homes cost more, and newer homes cost somewhat more, while neighborhood and pool contribute little measurable signal once those two variables are known.

## What The Findings Mean

If the goal is explanation, the clearest story is:

- size is the primary pricing mechanism
- newer construction adds a moderate premium beyond size
- many seemingly different listing features mostly duplicate the information already contained in `sq_ft`

If the goal is prediction, a parsimonious model with only `sq_ft` and `year_built` is preferable here. It matches the full specification in cross-validated error while being easier to interpret and less exposed to multicollinearity.

## Limitations And Self-Critique

- This analysis is observational. The coefficients describe association, not causal effects. For example, `year_built` may stand in for unmeasured renovation quality or building standards.
- The dataset is unusually tidy for real estate data: no missingness, no obvious recording errors, and very regular linear structure. That raises the possibility that the data is simulated or highly curated, so real-world housing conclusions should be made cautiously.
- I did not test nonlinear alternatives in depth because the linear fit already explained over 94% of variation with two variables and the residual plots did not suggest a strong pattern. A more irregular real dataset would justify splines or tree-based models.
- I did not investigate geographic detail beyond the provided `neighborhood` labels. If those categories are too coarse, true location effects could be hidden.
- Pool effects could be heterogeneous. For example, a pool might matter only in one neighborhood or only for larger homes. I checked the main effect and found little evidence overall, but I did not run a full interaction search.

Overall, the main conclusions are well supported by both inference and cross-validation: `sq_ft` dominates price, `year_built` adds a real secondary premium, and the remaining variables add little incremental information in this dataset.
