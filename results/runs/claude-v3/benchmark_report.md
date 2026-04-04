# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| heteroscedasticity | solved (100%) | - | - |
| interaction_effects | solved (100%) | - | - |
| multimodal | partial (12%) | - | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Run Error Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|----------------|--------------|----------------|-----------|
| Claude | 67% | 0% | 0% | 71% | 67% | 41% |

## Detailed Results

### heteroscedasticity

#### Claude (solved)

**Summary:** The agent delivered a thorough and well-structured analysis that squarely addresses the heteroscedasticity discovery task. It ran full residual diagnostics (residual plots, scale-location plot, Breusch-Pagan test), clearly identified non-constant variance increasing with spend/fitted values, suggested all three standard remedies (WLS, robust SEs, log transform), preserved the linear mean trend while distinguishing it from the variance problem, and explicitly warned about the unreliability of standard OLS inference. No forbidden behaviors were observed — the agent neither assumed constant variance nor reported OLS results uncritically. The analysis goes beyond the minimum requirements by quantifying the variance pattern across spend deciles and providing heteroscedasticity-aware prediction intervals. The only mild criticism is organizational: heteroscedasticity is the dataset's signature feature but is introduced as a subordinate observation within a broader spend-revenue finding rather than being elevated to headline status.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Efficiency:** report_chars=15654, trace_events=59, transcript_chars=195826

**Must Have**
- `heteroscedasticity_residual_diagnostics_run`: hit. The agent ran comprehensive residual diagnostics including residuals-vs-fitted plot, scale-location plot, Q-Q plot, residual histogram, Breusch-Pagan test, and Shapiro-Wilk test. This goes well beyond fitting only a mean trend. Evidence: "The model's residuals exhibit heteroscedasticity (Breusch-Pagan LM = 160.3, p < 0.001): absolute residual magnitude grows with predicted revenue, visible as a clear fan shape in the residuals-vs-fitted plot and a rising LOWESS trend in the scale-location plot. Residuals are also leptokurtic (excess kurtosis = 2.13, Shapiro-Wilk p < 0.001)"
- `heteroscedasticity_non_constant_variance_identified`: hit. The agent explicitly identifies that residual variance increases with fitted values / ad spend, supported by both visual diagnostics and a formal test. Finding 6 further quantifies the variance-spend relationship by decile. Evidence: "absolute residual magnitude grows with predicted revenue, visible as a clear fan shape in the residuals-vs-fitted plot and a rising LOWESS trend in the scale-location plot" and "The smallest decile has 2× the coefficient of variation of the largest."
- `heteroscedasticity_remedy_suggested`: hit. The agent recommends all three major remedy families: weighted least squares (actually fitted with weights = 1/spend²), heteroscedasticity-robust standard errors, and a variance-stabilizing log transform (though noting the log-log model has its own issues). Evidence: "a weighted least squares model (weights = 1/spend²) confirms the slope is robust (ROAS ≈ 2.48)" and "The linear OLS model with heteroscedasticity-robust standard errors is the most practical choice."

**Supporting**
- `heteroscedasticity_residual_plot_used`: hit. The agent produced a full regression diagnostics figure with four panels (residuals vs fitted with rolling ±1.96σ bands, Q-Q plot, residual histogram, scale-location plot with LOWESS) and ran the formal Breusch-Pagan test (LM = 160.3, p < 0.001). Evidence: "(Top-left) Residuals vs fitted with rolling ±1.96σ bands showing the fan-shaped heteroscedasticity. ... (Bottom-right) Scale-location plot with LOWESS smoother confirms rising residual spread."
- `heteroscedasticity_inference_risk_noted`: hit. The agent explicitly warns that OLS standard errors are biased under the detected heteroscedasticity, noting they are underestimated for high-spend campaigns and that the blended residual SD misrepresents uncertainty at both ends of the spend range. Evidence: "While the OLS coefficient estimates are unbiased, standard errors are underestimated for high-spend campaigns. The constant residual standard deviation of ~$8,666 overstates precision for large campaigns and understates it for small ones."
- `heteroscedasticity_linear_mean_trend_preserved`: hit. The agent carefully distinguishes the unbiased mean trend (Revenue ≈ 2.49 × Spend, R² = 0.945) from the variance problem, confirming the slope via WLS rather than discarding the model. Evidence: "The OLS coefficient estimates remain unbiased under heteroscedasticity, and a weighted least squares model (weights = 1/spend²) confirms the slope is robust (ROAS ≈ 2.48)."

**Forbidden**
- `heteroscedasticity_assumes_constant_variance`: miss. The agent explicitly tested for and rejected constant variance using both visual diagnostics and a formal Breusch-Pagan test. No assumption of constant variance was made. Evidence: "Breusch-Pagan LM = 160.3, p < 0.001" — non-constant variance is a central finding of the report.
- `heteroscedasticity_uses_ols_uncritically`: miss. The agent consistently caveats OLS inference, noting biased standard errors, recommending robust alternatives, and providing heteroscedasticity-aware prediction intervals rather than reporting OLS confidence as trustworthy. Evidence: "standard errors are underestimated for high-spend campaigns" and the explicit recommendation for "heteroscedasticity-robust standard errors" as the practical choice.

### interaction_effects

#### Claude (solved)

**Summary:** This is an exemplary analysis that fully satisfies all evaluation criteria. The agent correctly identified the channel_score × time_of_day_hour crossing interaction as the dominant driver of conversion, rigorously demonstrated that main-effects-only models underperform (AUC 0.692 vs 0.704, AIC 1662 vs 1645), and provided extensive visualization and tabulation of the interaction pattern. Secondary features were appropriately dismissed with statistical evidence, including a sophisticated debunking of misleading impurity-based feature importance for ad_budget via permutation importance. The non-additive nature of the relationship was explained in clear, precise language. No forbidden criteria were triggered. Verdict: solved.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Oracle Attainment (roc_auc):** 41%
**Efficiency:** report_chars=18262, trace_events=52, transcript_chars=195000

**Must Have**
- `interaction_effects_interaction_tested`: hit. The agent explicitly tested a logistic regression interaction term (channel_score × time_of_day_hour) and compared it to a main-effects-only model via likelihood ratio test and AIC. Also used tree-based models (Random Forest, Gradient Boosting) capable of capturing non-additive effects. Evidence: A logistic regression with main effects only (channel_score + time_of_day_hour) yields AIC = 1662.1. Adding the interaction term drops AIC to 1645.1 (likelihood ratio test: chi-squared = 19.0, p < 0.001).
- `interaction_effects_main_effects_only_underperforms`: hit. The agent directly compared main-effects-only vs interaction-aware models on both AIC and cross-validated AUC-ROC, clearly showing the main-effects-only model underperforms. Evidence: Logistic regression (no interaction): AUC 0.692 ± 0.026 vs Logistic regression (with interaction): AUC 0.700 ± 0.026. Parsimonious 3-term interaction model achieved AUC = 0.704. AIC drops from 1662.1 to 1645.1 with interaction term (LRT p < 0.001).
- `interaction_effects_channel_time_interaction_identified`: hit. The agent's primary finding explicitly identifies the channel_score × time_of_day_hour interaction as the key driver. The standardized coefficient analysis confirms it is an order of magnitude larger than any other feature. Evidence: The single most important finding is that channel score and time of day interact synergistically to drive conversion... the interaction term is highly significant (p = 1.6 x 10^-5)... The interaction term's standardized coefficient (0.71) is an order of magnitude larger than any other feature.

**Supporting**
- `interaction_effects_interaction_visualized`: hit. The agent produced multiple visualizations: a 5×5 heatmap of conversion rates across channel-score and time-of-day quintiles, a summary dashboard, detailed interaction plots, and corrective diagnostics with residual and super-additive effect maps. Also provided tabulated conversion rates for key scenario combinations. Evidence: Summary dashboard showing the interaction effect. The heatmap (top-left) shows conversion rates from 12% (low CS + late evening) to 75% (high CS + late evening). The synergy plot (top-center) shows observed rates systematically exceeding additive predictions at the high end.
- `interaction_effects_secondary_features_not_overstated`: hit. The agent explicitly identifies ad_budget, page_load_time, device, and previous_visits as non-predictive, backed by statistical tests. Also warns that Gradient Boosting's impurity-based importance misleadingly ranks ad_budget second, and demonstrates this is an artifact via permutation importance. Evidence: Ad budget is entirely uncorrelated with conversion... Page load time, device, and previous visits are non-predictive... removing ad_budget_usd from the Gradient Boosting model actually improves cross-validated AUC from 0.679 to 0.686.
- `interaction_effects_non_additive_language`: hit. The agent uses clear non-additive language explaining that the effect of one variable depends on the value of the other, explicitly calling it a crossing interaction and noting the time-of-day effect reverses direction depending on channel score level. Evidence: the evening conversion boost only materializes when channel quality is high. At low channel quality, time of day does not matter... This is stronger than simple synergy: the time-of-day effect reverses direction at low channel scores (flat or slightly negative) versus high channel scores (strongly positive).

**Forbidden**
- `interaction_effects_main_effects_only_conclusion`: miss. The agent did not conclude from a purely additive model. The entire analysis is structured around testing and confirming the interaction, with main-effects-only analysis presented only as a baseline to show its inadequacy. Evidence: Four models were evaluated... the interaction model outperforms main-effects-only in both AIC and AUC.
- `interaction_effects_misses_interaction_pattern`: miss. The agent's primary finding IS the interaction pattern. They explicitly warn that marginal main effects are misleading in isolation and that the time-of-day effect is entirely driven by high-channel-score sessions. Evidence: Critically, this marginal effect is misleading in isolation. As shown in Finding 1, the time-of-day effect is entirely driven by high-channel-score sessions. At low channel scores (CS 0–0.2), there is no time-of-day effect at all.

### multimodal

#### Claude (partial)

**Summary:** The agent delivered a technically competent regression analysis — identifying sq_ft dominance, bedroom premiums, distance irrelevance, and heteroscedasticity — but entirely missed the dataset's defining feature: a three-component Gaussian mixture in the target variable. The rent distribution was cursorily described as 'right-skewed' and tucked into a small dashboard panel, with no histogram/KDE analysis, no multimodality detection, no recognition of three modes, and no rejection of a single-Gaussian assumption. All modeling proceeds under a single-population framework. This is a textbook case of thorough regression work that skips the foundational step of carefully examining the target distribution's shape, leading to a fundamentally incomplete understanding of the data-generating process.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 12%
**Supporting Coverage:** 0%
**Efficiency:** report_chars=14087, trace_events=49, transcript_chars=172854

**Must Have**
- `multimodal_distribution_visualized`: partial. A rent distribution panel appears in the summary dashboard (Figure 6, 'Bottom-center: rent distribution'), and the agent describes the target as 'right-skewed.' However, there is no dedicated histogram or KDE with focused analysis of the distribution's shape — the visualization is a small panel in a multi-figure dashboard that was never discussed for its modal structure. Evidence: Figure 6: Summary dashboard. ... Bottom-center: rent distribution.
- `multimodal_multimodality_identified`: miss. The agent never identifies the target distribution as multimodal. It is characterized solely as 'right-skewed,' and all modeling assumes a single unimodal population. Evidence: The target variable (monthly rent) has a right-skewed distribution with a median of $1,516 and mean of $1,737.
- `multimodal_three_modes_noted`: miss. No mention of three modes, peaks, clusters, or segments in the target distribution anywhere in the report. Evidence: None
- `multimodal_single_gaussian_rejected`: miss. The agent discusses non-normal residuals (kurtosis, skew) and heteroscedasticity, but never questions or rejects a single-Gaussian assumption for the target distribution itself. The log-linear model is preferred only for heteroscedasticity, not because the target is multimodal. Evidence: Non-normal residuals: Residuals exhibit both leptokurtosis (excess kurtosis = 1.28) and mild positive skew (0.77).

**Supporting**
- `multimodal_segment_interpretation`: miss. No interpretation of distribution modes as market segments or subpopulations. The '1,500–2,000 sqft sweet spot' discussion is about rent efficiency by size, not about modes in the rent distribution. Evidence: None
- `multimodal_mode_locations_approximated`: miss. No mode locations in the target distribution are identified or approximated. Evidence: None
- `multimodal_mixture_or_segmentation_suggested`: miss. The agent never suggests a mixture model, segmentation, or clustering approach for the target variable. All modeling is standard OLS/log-linear regression treating rent as a single population. Evidence: None

**Forbidden**
- `multimodal_assumes_normality`: miss. The agent did inspect the distribution shape — noting it is 'right-skewed' and that residuals are non-normal. They did not assume normality outright, though they failed to detect the multimodal structure. Evidence: The target variable (monthly rent) has a right-skewed distribution... Non-normal residuals: Residuals exhibit both leptokurtosis and mild positive skew.
- `multimodal_summary_only_distribution`: miss. The agent did create a distribution visualization (Figure 6 panel) and noted skewness, going beyond pure mean/variance summary. The failure was in interpretation (not recognizing multimodality), not in the approach of only using summary statistics. Evidence: The target variable (monthly rent) has a right-skewed distribution with a median of $1,516 and mean of $1,737... Bottom-center: rent distribution.
