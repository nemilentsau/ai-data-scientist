# Data Analysis Report

## 1. Dataset Overview

| Property | Value |
|---|---|
| Rows | 1,000 |
| Columns | 8 |
| Duplicate rows | 0 |

**Variables:**

| Column | Type | Nulls | Description |
|---|---|---|---|
| `respondent_id` | int | 0 | Unique identifier (1-1000) |
| `age` | int | 0 | Range 18-80, mean 41.8, SD 11.6 |
| `gender` | str | 0 | F (496), M (464), Other (40) |
| `region` | str | 0 | 5 US regions (Southeast most frequent at 230) |
| `education_years` | int | 0 | Range 8-21, mean 14.3, mode 14 |
| `reported_annual_income` | float | **495 (49.5%)** | Range $15,000-$102,800, mean $48,994 |
| `satisfaction_score` | float | 0 | Scale 1.0-10.0, mean 6.98, SD 1.94 |
| `num_children` | int | 0 | Range 0-4, mean 1.46 |

---

## 2. Data Quality Assessment

### 2.1 Missing Data

The most critical data quality issue is **49.5% missing values in `reported_annual_income`**. All other columns are complete.

**The income data is Missing At Random (MAR), not Missing Completely At Random (MCAR).** Respondents with missing income are systematically different:

| Variable | Income Present (mean) | Income Missing (mean) | t-statistic | p-value |
|---|---|---|---|---|
| Age | 40.4 | 43.3 | -3.97 | 0.0001 |
| Education years | 14.0 | 14.6 | -4.13 | <0.0001 |
| Satisfaction score | 6.79 | 7.16 | -3.00 | 0.003 |
| Num children | 1.46 | 1.46 | -0.12 | 0.90 |

Older, more educated, and more satisfied respondents are more likely to have missing income. This is an important caveat: analyses using income on complete cases only will be biased toward younger, less educated respondents with lower satisfaction.

### 2.2 Outliers (IQR Method)

| Variable | Outliers | Bounds |
|---|---|---|
| Age | 7 | [11.5, 71.5] |
| Education years | 14 | [8.5, 20.5] |
| Income | 1 | [$12,200, $85,800] |
| Satisfaction | 2 | [1.4, 12.6] |
| Num children | 58 | [-0.5, 3.5] |

Outliers are minimal and plausible (e.g., age 72-80 is unusual but valid; 4 children is flagged as an outlier by IQR but is perfectly realistic). No data cleaning was warranted.

### 2.3 Distributions

- **Age:** Roughly bell-shaped, slight right skew. Shapiro-Wilk p=0.013 (marginal normality departure).
- **Income:** Approximately normal. Shapiro-Wilk p=0.086 (fails to reject normality at alpha=0.05). Skewness=0.18.
- **Satisfaction:** **Not normal** (Shapiro-Wilk p<0.001). Platykurtic (kurtosis=2.45) with slight left skew (-0.26). Covers the full 1-10 scale fairly broadly.
- **Education:** Discrete, roughly bell-shaped, centered around 13-15 years.
- **Num children:** Right-skewed discrete distribution (mode=1, range 0-4).

---

## 3. Exploratory Data Analysis

### 3.1 Correlation Structure

**Pearson correlations among numeric variables:**

| | Age | Education | Income | Satisfaction | Children |
|---|---|---|---|---|---|
| Age | 1.00 | 0.47 | 0.36 | 0.04 | 0.01 |
| Education | 0.47 | 1.00 | 0.37 | 0.01 | 0.00 |
| Income | 0.36 | 0.37 | 1.00 | 0.12 | -0.09 |
| Satisfaction | 0.04 | 0.01 | 0.12 | 1.00 | -0.04 |
| Children | 0.01 | 0.00 | -0.09 | -0.04 | 1.00 |

**Key findings:**
- **Age and education** are moderately correlated (r=0.47), suggesting a cohort or life-stage effect.
- **Income has meaningful relationships** with age (r=0.36) and education (r=0.37) — both highly significant (p<0.001).
- **Satisfaction score is essentially uncorrelated** with all demographic variables. The only marginally notable association is with income (Spearman rho=0.12, p=0.006), which is statistically significant but practically negligible.

### 3.2 Group Comparisons

**Satisfaction by region** (One-way ANOVA F=0.205, p=0.936; Kruskal-Wallis H=0.578, p=0.966):
- No significant differences across regions. Satisfaction is remarkably uniform geographically.

**Satisfaction by gender** (ANOVA F=0.633, p=0.531; Kruskal-Wallis H=0.853, p=0.653):
- No significant gender differences in satisfaction.

**Income by gender** (among observed values):
- F: mean $48,109; M: mean $49,425; Other: mean $52,874.
- No statistically significant gender gap in this dataset.

**Income by region** (among observed values):
- Ranges from $46,456 (West) to $50,081 (Southeast). Differences are small and not statistically significant.

---

## 4. Modeling

### 4.1 Model 1: Income Prediction

**Objective:** Predict `reported_annual_income` from demographic features.

**Method:** OLS regression with age, education_years, num_children, gender, and region. Also evaluated Ridge, Random Forest, and Gradient Boosting via 5-fold cross-validation.

**OLS Results (n=505):**

| Predictor | Coefficient | Std Error | p-value | Interpretation |
|---|---|---|---|---|
| Age | 271.7 | 49.9 | <0.001 | +$272 per year of age |
| Education years | 1,472.8 | 248.1 | <0.001 | +$1,473 per year of education |
| Num children | -948.5 | 432.4 | 0.029 | -$948 per child |
| Gender (M vs F) | -42.2 | 1,043.7 | 0.968 | Not significant |
| Gender (Other vs F) | 4,277.5 | 2,293.2 | 0.063 | Marginally significant |
| Region dummies | — | — | >0.05 | None significant |

**R-squared: 0.210** (Adjusted R-squared: 0.196)

**Cross-validated performance:**

| Model | R² (CV) | RMSE |
|---|---|---|
| Linear Regression | 0.157 ± 0.054 | $11,386 ± $665 |
| Ridge | 0.158 ± 0.053 | $11,379 ± $662 |
| Random Forest | 0.126 ± 0.049 | $11,597 ± $678 |
| Gradient Boosting | 0.063 ± 0.054 | $12,007 ± $661 |

Linear/Ridge regression outperforms tree-based methods, consistent with the relationships being primarily linear. The model captures ~16% of income variance out-of-sample — age and education are real but modest predictors.

**Assumption checks (OLS):**
- **Homoscedasticity:** Breusch-Pagan test p=0.854 — no heteroscedasticity detected.
- **Normality of residuals:** Q-Q plot shows very slight tail deviation; residuals are approximately normal.
- **Independence:** Durbin-Watson = 2.037 — no autocorrelation.
- **Multicollinearity:** All VIF values < 1.75 — no problematic collinearity.

**Conclusion:** The linear model assumptions are well satisfied. Age and education are statistically significant predictors of income, but the model explains only ~20% of variance, indicating substantial unexplained individual variation.

### 4.2 Model 2: Satisfaction Score Prediction

**Objective:** Predict `satisfaction_score` from all available features.

**Method:** Same model pipeline. Missing income handled by median imputation with a missingness indicator flag.

**OLS Results (n=1000):**

| Predictor | Coefficient | p-value |
|---|---|---|
| Income | 2.06e-05 | 0.005 |
| Income available flag | -0.396 | 0.002 |
| All other variables | — | >0.05 |

**R-squared: 0.023** (Adjusted: 0.012)

**Cross-validated R²: -0.008 to -0.084** (all models worse than predicting the mean).

**Conclusion:** The available demographic and income features have **no practical predictive power** for satisfaction. Cross-validated R² is consistently negative, meaning the models overfit to noise even with just a handful of features. Satisfaction score in this dataset is essentially **independent of the measured covariates**.

---

## 5. Key Findings

1. **Satisfaction is not driven by demographics or income.** Despite common assumptions, satisfaction scores in this dataset show no meaningful relationship with age, gender, region, education, income, or number of children. This is the most important finding: either satisfaction is driven by unmeasured factors (personality, health, job conditions, social connections), or it was measured on too coarse a scale to capture subtle effects.

2. **Income is moderately predictable from age and education.** Each additional year of age is associated with ~$272 higher income, and each year of education with ~$1,473. Together, these explain ~20% of income variation. Gender and region do not significantly predict income.

3. **Income data is Missing At Random (MAR).** Older, more educated, and more satisfied respondents are disproportionately likely to have missing income. Any analysis using only complete cases should acknowledge this potential selection bias. Analyses relying on income should consider multiple imputation rather than complete-case analysis.

4. **The data is generally clean and well-behaved.** No duplicates, minimal outliers, plausible value ranges, and (for the income model) well-satisfied regression assumptions. The only data quality concern is the 49.5% income missingness rate.

5. **No significant regional or gender disparities** were detected in satisfaction, and income differences across these groups are small and non-significant.

---

## 6. Limitations and Recommendations

- **Missing income data:** At 49.5% missingness with MAR mechanism, analyses conditional on income should use multiple imputation (e.g., MICE) for unbiased estimates. Complete-case analysis underrepresents older, more educated respondents.
- **Low "Other" gender count (n=40):** Estimates for this group have wide confidence intervals and should be interpreted cautiously.
- **Unmeasured confounders:** The near-zero R² for satisfaction strongly suggests that critical determinants of satisfaction are not captured in this dataset. Future data collection should include job-related variables, health status, social factors, or psychological measures.
- **Cross-sectional design:** These data are a single snapshot. Causal claims (e.g., "education causes higher income") cannot be made from this observational data.
- **Self-reported income:** The variable name `reported_annual_income` suggests self-report, which may contain measurement error or social desirability bias — potentially contributing to the high missingness rate.

---

## 7. Plots Index

| File | Description |
|---|---|
| `plots/01_distributions.png` | Histograms of all numeric variables |
| `plots/02_categorical_distributions.png` | Bar charts of gender and region |
| `plots/03_correlation_heatmap.png` | Pearson correlation matrix |
| `plots/04_satisfaction_relationships.png` | Satisfaction vs age, education, income, children |
| `plots/05_satisfaction_by_category.png` | Satisfaction by gender and region |
| `plots/06_missingness_patterns.png` | Distribution shifts between income-missing and income-present groups |
| `plots/07_income_relationships.png` | Income vs age and education with trend lines |
| `plots/08_pairplot.png` | Pairwise scatterplots colored by gender |
| `plots/09_income_model_diagnostics.png` | OLS residual diagnostics (residuals vs fitted, Q-Q, histogram, scale-location) |
| `plots/10_feature_importance_income.png` | Random Forest feature importance for income |
| `plots/11_satisfaction_distribution.png` | Detailed satisfaction score distribution |
