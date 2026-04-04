# Real Estate Price Analysis Report

## 1. Dataset Overview

The dataset contains **800 residential property listings** with 8 features and a target variable (price). All records are complete with no missing values.

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| sq_ft | int | 600 – 3,341 | Interior square footage |
| num_rooms | int | 2 – 11 | Number of rooms |
| lot_size_acres | float | 0.316 – 1.715 | Lot size in acres |
| garage_spaces | int | 1 – 4 | Garage capacity |
| year_built | int | 1950 – 2023 | Year of construction |
| neighborhood | str | 5 categories | Eastwood, Suburbs, Hillcrest, Downtown, Lakeside |
| has_pool | int | 0/1 | Whether the home has a pool |
| **price_usd** | **int** | **$83,600 – $496,700** | **Sale price (target)** |

Mean price is $287,148 (SD $61,285). Neighborhoods are fairly balanced (132–185 listings each). About 30% of homes have pools.

## 2. Key Findings

### Finding 1: Price is overwhelmingly determined by just two factors — square footage and year built

A linear model using only `sq_ft` and `year_built` explains **94.4% of all price variance** (R² = 0.944). The formula is:

```
Price = $149 × sq_ft + $522 × year_built − $1,017,000
```

- Each additional square foot adds **$149** to price (95% CI: $146–$152)
- Each year newer adds **$522** to price (95% CI: $473–$570)
- Cross-validated RMSE: **$14,510** (MAE: $11,520)

Adding all remaining features (lot size, rooms, garage, neighborhood, pool) to the model provides **zero improvement** — R² stays at 0.944. See `plots/06_summary.png` for the actual-vs-predicted scatter and the price formula.

### Finding 2: Size features are almost perfectly collinear

The four size-related features are proxies for the same underlying dimension:

| Feature Pair | Correlation |
|---|---|
| sq_ft ↔ lot_size_acres | 0.970 |
| sq_ft ↔ num_rooms | 0.957 |
| num_rooms ↔ lot_size_acres | 0.929 |
| sq_ft ↔ garage_spaces | 0.788 |

Once sq_ft is in the model, lot_size (p=0.81), num_rooms (p=0.21), and garage_spaces (p=0.99) contribute nothing. This extreme collinearity is visible in the correlation heatmap (`plots/01_correlations_and_sqft_price.png`).

### Finding 3: Pools have absolutely no effect on price

This is the most counter-intuitive finding. Pool and non-pool homes are virtually identical:

| Metric | No Pool (n=557) | Pool (n=243) |
|--------|-----------------|--------------|
| Mean price | $287,681 | $285,927 |
| Mean sq_ft | 1,797 | 1,797 |
| Pool rate by size quartile | ~30% in each | — |

- Raw t-test: p = 0.71 (no significant difference)
- After controlling for size: coefficient = −$1,796, p = 0.20 (not significant)
- Pools are uniformly distributed across all home sizes and neighborhoods (27–34% in each)

Pools appear to be a purely random amenity in this market — they neither increase nor decrease home value. See `plots/02_pool_paradox.png`.

### Finding 4: Neighborhood has no effect on price

Despite five distinct neighborhoods, there is no statistically significant price difference between them after controlling for size:

- F-test for neighborhood effect (added to sq_ft model): **p = 0.44**
- ANOVA on price-per-sqft across neighborhoods: **p = 0.51**
- Price per sqft ranges from $159/sqft (Suburbs) to $161/sqft (Lakeside) — a trivial $2 spread

All neighborhoods follow the same price-per-sqft rate. See `plots/04_nonlinearity_neighborhoods_outliers.png` (top-right panel).

### Finding 5: Year built has a strong, linear age premium

Controlling for size, newer homes command a clear, monotonic premium (`plots/03_parsimonious_model_diagnostics.png`, bottom-right):

| Decade Built | Price Premium (vs. mean) |
|---|---|
| 1950s | −$17,926 |
| 1960s | −$11,017 |
| 1970s | −$5,943 |
| 1980s | +$862 |
| 1990s | +$3,843 |
| 2000s | +$10,484 |
| 2010s | +$13,215 |
| 2020s | +$18,949 |

The relationship is linear — a quadratic term is not significant (p = 0.41). There is no "vintage premium" for older homes. Each decade adds approximately $5,000 in value.

### Finding 6: Linear models outperform machine learning on this data

Cross-validated comparison (10-fold CV):

| Model | RMSE | R² |
|---|---|---|
| Linear Reg (sq_ft + year_built) | $14,510 | 0.942 |
| Linear Reg (all features) | $14,538 | 0.942 |
| Lasso (all features) | $14,509 | 0.942 |
| Ridge (all features) | $14,541 | 0.942 |
| Random Forest (all features) | $16,398 | 0.926 |
| Gradient Boosting (all features) | $16,434 | 0.926 |

Tree-based models perform **worse** than linear regression, confirming the relationship is genuinely linear with no hidden non-linear patterns or interactions. The interaction between sq_ft and year_built was also tested and found non-significant (p = 0.23). See `plots/05_model_comparison.png`.

## 3. Interpretation and Practical Implications

**For buyers and sellers**: Price is almost entirely a function of square footage and building age. In this market, you should expect to pay approximately $149 per square foot, with a premium of about $522 for each year newer the home is. Neighborhood, pools, lot size, and garage spaces do not independently affect price.

**For appraisers**: A two-variable model (sq_ft + year_built) is sufficient. Adding more features introduces multicollinearity without improving accuracy. The model's typical error is about $14,500, or roughly 5% of the average home price.

**The pool finding** suggests that in this market, pools are neither an investment nor a liability. Homeowners should make pool decisions based on personal utility, not expected resale value.

**The neighborhood finding** is notable — it implies that location premiums, if they exist, are already capitalized into the physical characteristics of the homes (larger homes in more expensive areas), rather than existing as a separate location premium.

## 4. Limitations and Caveats

**Data generation concerns**: The extreme cleanliness of this data (R² = 0.944 with two variables, perfectly normal residuals, zero neighborhood effect, exactly random pool distribution) is unusual for real-world housing data. Real markets typically show stronger location effects, heteroscedasticity, and non-linear interactions. This dataset may be synthetically generated.

**Omitted variables**: The dataset lacks important real-world pricing factors — condition/renovation status, school district quality, proximity to amenities, lot shape, views, and market timing (sale date). The $14,500 residual error likely captures these unmeasured factors.

**Causal interpretation**: The year_built coefficient ($522/year) should not be interpreted as purely an age/depreciation effect. It may confound with building code improvements, energy efficiency, and modern design preferences.

**Multicollinearity**: The extreme correlation among size features (r > 0.93) means individual coefficient estimates for lot_size, num_rooms, and garage_spaces are unreliable. Only the combined "size" effect is well-estimated.

**Outliers**: Four observations have studentized residuals exceeding |3|, all below predicted values. These represent homes priced lower than expected given their size and age, but none exert undue leverage on the model (no high Cook's distance values). See `plots/04_nonlinearity_neighborhoods_outliers.png` (bottom-right).

## 5. Plots Reference

| File | Description |
|---|---|
| `plots/01_correlations_and_sqft_price.png` | Correlation heatmap and price vs sqft scatter by neighborhood |
| `plots/02_pool_paradox.png` | Pool effect analysis — distributions and residuals |
| `plots/03_parsimonious_model_diagnostics.png` | Model diagnostics: residuals, QQ plot, year-built premium |
| `plots/04_nonlinearity_neighborhoods_outliers.png` | Non-linearity checks, neighborhood comparison, outliers |
| `plots/05_model_comparison.png` | Cross-validated model comparison and feature importance |
| `plots/06_summary.png` | Comprehensive summary of all key findings |
