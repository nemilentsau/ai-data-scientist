# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| multicollinearity | solved (100%) | - | - |
| quadratic | solved (100%) | - | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|--------------|----------------|-----------|
| Claude | 100% | 0% | 100% | 100% | 100% |

## Detailed Results

### multicollinearity

#### Claude (solved)

**Summary:** This is an excellent analysis that correctly identifies multicollinearity as the central challenge in the dataset. The agent computes both pairwise correlations and VIF, names sq_ft, num_rooms, and lot_size_acres as near-redundant size proxies, explains that including all three inflates standard errors and renders individual coefficients uninterpretable, and systematically remediates by comparing full, reduced, and parsimonious models alongside Ridge and Lasso regularization. The predictive-vs-interpretive tradeoff is clearly demonstrated (R² unchanged at 0.944 across models while coefficient significance improves dramatically). No forbidden criteria are triggered — p-values in the collinear full model are correctly treated as symptoms of the problem, not trusted at face value.
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Efficiency:** report_chars=9504, trace_events=11, transcript_chars=41680

**Must Have**
- `multicollinearity_predictor_correlation_detected`: hit. Section 2.3 is entirely dedicated to detecting multicollinearity. Pairwise correlations (0.89–0.95) and VIF values (12.0–29.2) are computed for sq_ft, num_rooms, and lot_size_acres. Evidence: sq_ft vs lot_size_acres: 0.95, sq_ft vs num_rooms: 0.93, lot_size_acres vs num_rooms: 0.89. VIF: sq_ft=29.2, lot_size_acres=17.2, num_rooms=12.0. 'VIF > 10 indicates severe multicollinearity.'
- `multicollinearity_instability_explained`: hit. The report explicitly explains that multicollinearity inflates standard errors and makes coefficients uninterpretable. The full model having only 2/10 significant predictors despite R²=0.944 further demonstrates instability. Evidence: 'Including all three in a regression inflates standard errors and makes individual coefficients uninterpretable.' and 'Including all three provides no predictive benefit and inflates coefficient uncertainty.'
- `multicollinearity_remediation_suggested`: hit. Multiple remediations are suggested and implemented: dropping redundant features (reduced and parsimonious models), Ridge regularization, and Lasso feature selection. The entire modeling strategy is built around addressing the multicollinearity. Evidence: Three models compared: Full (10 features) → Reduced (4, dropping collinear predictors) → Parsimonious (2). Also: 'Lasso feature selection (optimal alpha=155.35) zeroed out garage_spaces and neighborhood_Eastwood entirely.' Ridge regression also tested.

**Supporting**
- `multicollinearity_correlation_matrix_or_vif`: hit. Both a correlation matrix (with heatmap visualization) and VIF analysis are presented as formal diagnostics. Evidence: Correlation heatmap (plots/01_correlation_heatmap.png), pairwise correlation table in Section 2.3, and VIF table with values for all 6 numeric features.
- `multicollinearity_redundant_features_named`: hit. The three redundant predictors are explicitly named and characterized as measuring the same latent construct. Evidence: 'sq_ft, num_rooms, and lot_size_acres are near-redundant (pairwise r > 0.89, VIFs > 12). These three features likely represent the same underlying construct: "house size."'
- `multicollinearity_predictive_vs_interpretive_tradeoff`: hit. The report directly demonstrates that predictive accuracy is unaffected while interpretability suffers. All three models achieve R²≈0.944, but the full model has only 2/10 significant coefficients. Evidence: 'All models achieve virtually identical R² (~0.944). The parsimonious model wins on AIC (lowest), parsimony, and interpretability. Adding 8 more features gains only 0.07 percentage points of R².'

**Forbidden**
- `multicollinearity_trusts_individual_p_values`: miss. The report uses the non-significance of individual coefficients in the full model as evidence of the multicollinearity problem, not as face-value interpretations. P-values in the final parsimonious model are only reported after collinear features have been removed. Evidence: Full model shows num_rooms p=0.205, lot_size_acres p=0.812, garage_spaces p=0.990 — these are cited as symptoms of multicollinearity, not trusted at face value. Only the 2-predictor model's p-values are interpreted.
- `multicollinearity_ignores_predictor_correlation`: miss. Predictor correlation is a central theme of the analysis. An entire section (2.3) is dedicated to it, and the modeling strategy is built around addressing it. Evidence: Section 2.3 'Severe Multicollinearity Among Size Features' with pairwise correlations, VIF analysis, and dedicated visualization (plots/06_multicollinearity.png).

### quadratic

#### Claude (solved)

**Summary:** This is an exemplary analysis that comprehensively addresses every aspect of the evaluation contract. The agent correctly identified the quadratic relationship between engine RPM and fuel consumption, fit a polynomial model with R² = 0.9954, demonstrated massive improvement over the linear baseline (0.958 → 0.995), performed thorough residual diagnostics on both models, wrote out the explicit quadratic equation, and correctly dismissed all noise features with appropriate statistical tests. No forbidden criteria were triggered. The analysis goes above and beyond with cross-validation, multiple statistical tests, and clear physical interpretation of the quadratic relationship.
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Oracle Attainment (r2):** 100%
**Efficiency:** report_chars=8732, trace_events=10, transcript_chars=45851

**Must Have**
- `quadratic_nonlinearity_detected`: hit. The agent explicitly detected nonlinearity through scatter plots, residual analysis from the linear fit, and polynomial degree comparison. Evidence: "The scatter plot shows a clear nonlinear (quadratic/parabolic) relationship between engine RPM and fuel consumption." Also created Plot 6 showing residuals from the linear fit with systematic curvature.
- `quadratic_quadratic_relationship_identified`: hit. The agent unambiguously identified the core relationship as quadratic/second-order. Evidence: "The relationship is quadratic, not linear. Fuel consumption scales approximately as RPM², consistent with engine physics (power ~ RPM² at constant torque)." Simplified equation: "fuel_consumption ~ 2.0e-6 * RPM^2".
- `quadratic_nonlinear_model_fit`: hit. A quadratic polynomial model was fit with full OLS regression, coefficient table, and cross-validation. Evidence: "fuel_consumption = 0.066 - 0.000032 * RPM + 0.000002005 * RPM^2" with t-statistics and p-values for each term. 10-fold CV R² = 0.9952 ± 0.0010.
- `quadratic_improvement_over_linear_shown`: hit. The agent provided a direct side-by-side comparison of linear vs quadratic models with R², MAE, and RMSE metrics. Evidence: "The quadratic term in RPM produces a massive improvement: R² jumps from 0.958 to 0.995 (RMSE drops from 4.41 to 1.46 L/h)." A four-model comparison table was included.

**Supporting**
- `quadratic_residuals_compared`: hit. Extensive residual diagnostics were performed on both the linear and quadratic models, including normality, homoscedasticity, and independence tests. Evidence: Shapiro-Wilk (p=0.70), Breusch-Pagan (p=0.23), Durbin-Watson (2.03) on quadratic residuals. Plot 06 shows linear residuals with clear curvature. Plot 08 is a 4-panel residual diagnostic.
- `quadratic_equation_or_feature_transform`: hit. The agent wrote out the full quadratic equation with coefficients and also provided the simplified approximate form. Evidence: "fuel_consumption = 0.066 - 0.000032 * RPM + 0.000002005 * RPM^2" and simplified "fuel_consumption ~ 2.0e-6 * RPM^2". RPM^2 term had t=69.94, p<0.001.
- `quadratic_noise_columns_not_overinterpreted`: hit. The agent correctly dismissed all non-RPM features as noise, supported by ANOVA, Kruskal-Wallis, partial correlations, and model comparison showing <0.001 R² improvement from adding them. Evidence: "Octane rating has no effect on fuel consumption" (ANOVA p=0.92, Kruskal-Wallis p=0.91). "Adding all other features to either model yields negligible improvement (< 0.001 in R²)."

**Forbidden**
- `quadratic_linear_only_conclusion`: miss. The agent explicitly concluded with a quadratic model and stated the relationship is quadratic, not linear. Evidence: "The simplest adequate model is Quadratic RPM only." Key finding: "The relationship is quadratic, not linear."
- `quadratic_no_residual_checks`: miss. The agent performed comprehensive residual diagnostics on both the linear and quadratic models. Evidence: Residual plots (Plots 06, 08, 10), Shapiro-Wilk, Breusch-Pagan, Durbin-Watson tests, Q-Q plot, residuals-vs-fitted plot, outlier detection via IQR.
