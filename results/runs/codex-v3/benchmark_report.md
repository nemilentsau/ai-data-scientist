# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| heteroscedasticity | - | solved (100%) | - |
| interaction_effects | - | solved (100%) | - |
| multimodal | - | wrong (0%) | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Run Error Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|----------------|--------------|----------------|-----------|
| Codex | 67% | 33% | 0% | 67% | 67% | 38% |

## Detailed Results

### heteroscedasticity

#### Codex (solved)

**Summary:** The agent delivered a thorough and methodologically sound analysis. It correctly identified heteroscedasticity as the key dataset pattern — residual spread increasing with fitted values — supported by both a residual plot and the Breusch-Pagan test (p < 1e-36). It applied HC3 robust standard errors as a remedy and clearly distinguished the strong linear mean trend (R²=0.945) from the variance problem. No forbidden behaviors were exhibited: the agent never assumed constant variance and never reported OLS inference uncritically. The heteroscedasticity finding was framed as a diagnostic note rather than the headline discovery, which slightly underweights its importance relative to the evaluation contract, but the technical substance fully satisfies all must-have and supporting criteria.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Efficiency:** report_chars=8947, trace_events=50, transcript_chars=83489

**Must Have**
- `heteroscedasticity_residual_diagnostics_run`: hit. The agent fit an OLS model (revenue ~ ad_spend), produced residual diagnostic plots, and ran a formal Breusch-Pagan test on the residuals. Evidence: "The residual plot in plots/revenue_model_diagnostics.png shows clear heteroskedasticity, confirmed by the Breusch-Pagan test (p < 1e-36)."
- `heteroscedasticity_non_constant_variance_identified`: hit. The agent explicitly identifies that residual spread increases with spend/fitted values — the core pattern in the dataset. Evidence: "the residual spread widens at higher spend levels" and "Higher-spend campaigns have wider residual spread, so prediction intervals for large campaigns should be wider."
- `heteroscedasticity_remedy_suggested`: hit. The agent applied HC3 robust standard errors as a direct remedy for heteroscedasticity, which is one of the accepted remedies (robust standard errors). Evidence: "I therefore relied on HC3 robust confidence intervals for the slope. This affects uncertainty estimates, not the basic conclusion that spend is the dominant driver."

**Supporting**
- `heteroscedasticity_residual_plot_used`: hit. Both a residual plot and a formal heteroscedasticity test were produced and referenced to support the diagnosis. Evidence: "The residual plot in plots/revenue_model_diagnostics.png shows clear heteroskedasticity, confirmed by the Breusch-Pagan test (p < 1e-36)."
- `heteroscedasticity_inference_risk_noted`: hit. The agent explains that heteroscedasticity affects uncertainty estimates and switches to robust SEs, implicitly but clearly communicating that standard OLS inference would be unreliable. Evidence: "This affects uncertainty estimates" and the deliberate switch to HC3 robust CIs rather than standard OLS intervals.
- `heteroscedasticity_linear_mean_trend_preserved`: hit. The agent clearly distinguishes the mean relationship (strong, R²=0.945) from the variance problem, explicitly stating the heteroscedasticity does not invalidate the mean trend. Evidence: "This affects uncertainty estimates, not the basic conclusion that spend is the dominant driver" and "the average linear relationship is strong."

**Forbidden**
- `heteroscedasticity_assumes_constant_variance`: miss. The agent explicitly tests for and identifies non-constant variance using residual plots and the Breusch-Pagan test. No assumption of constant variance is made. Evidence: Breusch-Pagan test (p < 1e-36) and residual diagnostics were run proactively.
- `heteroscedasticity_uses_ols_uncritically`: miss. The agent explicitly caveat OLS results and switches to HC3 robust standard errors. OLS significance is never reported as trustworthy without qualification. Evidence: "95% CI for slope with HC3 robust standard errors: [2.454, 2.535]" — robust inference was used instead of naive OLS CIs.

### interaction_effects

#### Codex (solved)

**Summary:** The agent delivered an excellent analysis that squarely hits every must-have criterion. It tested the channel_score × time_of_day_hour interaction explicitly via likelihood-ratio test, demonstrated the main-effects model underperforms, and identified the interaction as the key driver. All supporting criteria are also met: the interaction is visualized with a heatmap and tabulated rates, secondary features are appropriately downweighted, and the language clearly conveys non-additive effects. No forbidden criteria are triggered. The only minor gap is that the reported ROC-AUC (0.692) comes from the main-effects logistic regression rather than from a cross-validated interaction-aware model, so the oracle metric may understate the interaction model's true predictive performance.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** pass
**Required Coverage:** 100%
**Supporting Coverage:** 100%
**Oracle Attainment (roc_auc):** 38%
**Efficiency:** report_chars=6680, trace_events=56, transcript_chars=66392

**Must Have**
- `interaction_effects_interaction_tested`: hit. Agent explicitly fitted a logistic model with the channel_score:time_of_day_hour interaction term and performed a likelihood-ratio test against the main-effects-only base model. Evidence: Adding the interaction channel_score:time_of_day_hour improved logistic model fit with a likelihood-ratio statistic of 18.81 on 1 degree of freedom (p = 1.44e-05).
- `interaction_effects_main_effects_only_underperforms`: hit. The agent compared the base (additive) model to the interaction model using a likelihood-ratio test, demonstrating a statistically significant improvement (p = 1.44e-05). AIC also improved from 1669.49 for the base model. Evidence: LR tests vs base ... with_interaction lr 18.81 df 1 p 1.44e-05; base AIC 1669.49
- `interaction_effects_channel_time_interaction_identified`: hit. The report's primary finding is explicitly titled 'Conversion is driven mainly by a time-by-channel-quality interaction' and names channel_score and time_of_day_hour as the interacting variables. Evidence: The strongest pattern is not a simple main effect. Conversion rises later in the day, but the increase is much steeper for high-channel_score traffic than for low-score traffic.

**Supporting**
- `interaction_effects_interaction_visualized`: hit. Agent produced a heatmap and fitted probability curves plot (conversion_by_time_and_score.png) and tabulated conversion rates across channel_score terciles and time-of-day bins. Evidence: In the lowest channel_score tercile during 00-06, the conversion rate is 10.9%. In the highest channel_score tercile during 18-24, it reaches 75.0%. The plot shows both the observed heatmap and the fitted probability curves.
- `interaction_effects_secondary_features_not_overstated`: hit. The report explicitly downweights device (p=0.929), page load time (p=0.784), and ad budget (p=0.629 and flat quintile rates), clearly positioning the interaction as the dominant pattern. Evidence: Device type is also uninformative after adjustment (p = 0.929), and page load time is not distinguishable from noise here (p = 0.784)... ad_budget_usd looks important by name, but not by evidence.
- `interaction_effects_non_additive_language`: hit. The report explicitly describes how the effect of one variable depends on the value of the other, using clear non-additive framing throughout. Evidence: The same hour of day is not equally valuable for all traffic sources. High-quality channels become much more productive late in the day, while low-quality channels stay relatively weak throughout.

**Forbidden**
- `interaction_effects_main_effects_only_conclusion`: miss. The agent did not conclude from a purely additive model. The interaction was tested, found significant, and made the central finding. Evidence: The strongest pattern is not a simple main effect.
- `interaction_effects_misses_interaction_pattern`: miss. The interaction between channel_score and time_of_day_hour is the headline finding; conversion is not explained via separate main effects. Evidence: Conversion is driven mainly by a time-by-channel-quality interaction (Finding #1).

### multimodal

#### Codex (wrong)

**Summary:** The agent produced a competent regression analysis but entirely missed the dataset's defining feature: a three-component Gaussian mixture in the target variable. By jumping directly to correlation and OLS modeling without ever plotting a histogram or KDE of monthly_rent_usd, the agent failed every must-have criterion and triggered both forbidden criteria. The OLS diagnostics flagged severe non-normality (Omnibus p=0.000, excess kurtosis) which should have prompted distributional investigation, but the agent dismissed this as a minor limitation. This is a textbook case of skipping exploratory distribution analysis and paying the price — the strongest signal in the data was invisible to an approach that never looked at the shape of the outcome.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 0%
**Supporting Coverage:** 0%
**Fatal Errors:**
- Assume the rent distribution is approximately normal without checking it.
- Summarize the target with mean and variance only while missing the multiple modes.
**Efficiency:** report_chars=7648, trace_events=55, transcript_chars=67460

**Must Have**
- `multimodal_distribution_visualized`: miss. The agent never plotted a histogram, KDE, or any direct visualization of the monthly_rent_usd distribution. All four plots focus on scatter plots (rent vs sqft), grouped bar charts (parking by size quartile), rent_per_sqft vs distance, and standardized coefficients. No distributional inspection of the target was performed. Evidence: Plots referenced: plot_01_rent_vs_sqft.png, plot_02_parking_by_size_quartile.png, plot_03_rent_per_sqft_vs_distance.png, plot_04_standardized_coefficients.png — none are histograms or KDEs of rent.
- `multimodal_multimodality_identified`: miss. The report never mentions multimodality, multiple modes, or a non-unimodal distribution. The word 'mode' does not appear in the analysis. The agent treats rent as a single continuous outcome modeled by one linear relationship. Evidence: The entire analysis assumes a single-population linear model: 'Size explains most of the rent variation… a simple linear model using sq_ft, bedrooms, and bathrooms would likely capture most available signal.'
- `multimodal_three_modes_noted`: miss. No mention of three modes, clusters, segments, or subpopulations in the rent distribution anywhere in the report. Evidence: N/A — the concept is entirely absent from the report.
- `multimodal_single_gaussian_rejected`: miss. The agent never tests or rejects a single-Gaussian assumption for the target. The OLS output shows Omnibus=129.23 (p=0.000) indicating severe non-normality of residuals, but the agent only mentions this as a caveat ('OLS residuals are somewhat non-normal') without investigating the cause or connecting it to target distribution shape. Evidence: 'The OLS residuals are somewhat non-normal, so p-values should be read as rough inferential guides rather than exact truth.'

**Supporting**
- `multimodal_segment_interpretation`: miss. No interpretation of modes as market segments or subpopulations. The agent groups by bedroom/bathroom counts but never identifies distinct rent segments in the target distribution. Evidence: N/A — concept absent.
- `multimodal_mode_locations_approximated`: miss. No mode locations identified or approximated. The agent reports quantiles and means but never identifies where modes (peaks) occur in the rent distribution. Evidence: N/A — concept absent.
- `multimodal_mixture_or_segmentation_suggested`: miss. No mixture model, clustering, or segmentation approach is suggested. The agent explicitly states it stayed with linear methods and did not test more flexible models. Evidence: 'I did not test more flexible models such as gradient boosting because the core inferential finding was already clear: the signal is dominated by a small set of linear predictors.'

**Forbidden**
- `multimodal_assumes_normality`: hit. The agent never checked the target distribution shape and proceeded to fit a single-population OLS regression, implicitly assuming a unimodal/Gaussian-like target. The Omnibus test in the OLS output screams non-normality (p=0.000) but the agent dismisses residual non-normality as a minor caveat rather than investigating the cause. Evidence: 'The OLS residuals are somewhat non-normal, so p-values should be read as rough inferential guides rather than exact truth.' — dismissed without investigation.
- `multimodal_summary_only_distribution`: hit. The agent characterizes monthly_rent_usd entirely through mean ($1,737.47), SD ($997.09), range ($347–$4,769), and quantiles. The three-mode structure is completely missed because no distributional plot or shape analysis was ever performed. Evidence: 'monthly_rent_usd ranges from $347 to $4,769' and describe output showing mean/std/quantiles. No histogram, no mode count, no shape characterization.
