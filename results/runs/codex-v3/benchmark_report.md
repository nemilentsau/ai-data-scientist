# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| heteroscedasticity | - | partial (50%) | - |
| interaction_effects | - | partial (33%) | - |
| multimodal | - | wrong (0%) | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Run Error Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|----------------|--------------|----------------|-----------|
| Codex | 0% | 33% | 0% | 28% | 56% | 38% |

## Detailed Results

### heteroscedasticity

#### Codex (partial)

**Summary:** The agent conducted a thorough and technically competent marketing analysis but largely missed the forest for the trees. While residual diagnostics were properly executed and the heteroscedasticity pattern was observed in the residual plot, the agent treated the variance fan-out as a minor caveat rather than the dataset's defining feature. The entire report is oriented around channel/region/season comparisons and the strength of the linear spend-revenue relationship, with the non-constant variance mentioned only in a single sentence in the Limitations section. Critically, no remedy (weighted regression, robust standard errors, or variance-stabilizing transform) was suggested. The agent demonstrated good analytical mechanics but failed to recognise which signal was the important one for this dataset.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 50%
**Supporting Coverage:** 83%
**Efficiency:** report_chars=8565, trace_events=64, transcript_chars=93932

**Must Have**
- `heteroscedasticity_residual_diagnostics_run`: hit. The agent computed studentized residuals, Cook's distance via statsmodels get_influence().summary_frame(), and produced a residual plot (revenue_model_residuals.png). Residual diagnostics were clearly executed beyond just fitting a mean trend. Evidence: Session: 'resid = models["rev_linear"].get_influence().summary_frame()' computing student_resid and cooks_d. Report references 'plots/revenue_model_residuals.png' and discusses outliers by studentized residual.
- `heteroscedasticity_non_constant_variance_identified`: partial. The agent noticed the variance fan-out pattern but buried it as a minor caveat in the Limitations section rather than treating it as a key finding. The identification is present but significantly underweighted — it should have been the central discovery, not a footnote. Evidence: Limitations section: 'The residual plot also shows wider variance at higher fitted revenue, so exact standard-error-based inference should be interpreted cautiously even though the high-level signal is clear.'
- `heteroscedasticity_remedy_suggested`: miss. The agent never recommended weighted regression, robust standard errors, or a variance-stabilizing transform. They noted inference should be 'interpreted cautiously' but offered no concrete remedy for the heteroscedasticity they observed. Evidence: No mention of WLS, HC standard errors, log-transform, or any other variance-stabilizing technique anywhere in the report or session.

**Supporting**
- `heteroscedasticity_residual_plot_used`: hit. A residual plot was created and referenced in the report, and the agent used it to observe the variance pattern. Evidence: Report: 'These are visible in plots/revenue_model_residuals.png' and 'The residual plot also shows wider variance at higher fitted revenue.'
- `heteroscedasticity_inference_risk_noted`: partial. The agent mentioned that inference should be cautious but did not explicitly explain the mechanism — that standard OLS standard errors, p-values, and confidence intervals are biased/inconsistent under heteroscedasticity. Evidence: 'exact standard-error-based inference should be interpreted cautiously even though the high-level signal is clear'
- `heteroscedasticity_linear_mean_trend_preserved`: hit. The agent clearly distinguished the strong linear mean relationship (R²=0.945) from the variance problem, explicitly noting 'the high-level signal is clear' while flagging the variance issue separately. Evidence: Key Finding 1 emphasises 'revenue_usd ~ ad_spend_usd: R² = 0.945' as valid. Limitations section separately notes the variance issue without dismissing the mean trend.

**Forbidden**
- `heteroscedasticity_assumes_constant_variance`: miss. The agent did not assume constant variance — they explicitly noted increasing variance at higher fitted values in the limitations section. Evidence: 'The residual plot also shows wider variance at higher fitted revenue'
- `heteroscedasticity_uses_ols_uncritically`: miss. While the main findings sections present OLS p-values without inline caveats, the agent does add a caveat in the limitations section about OLS inference reliability. The caveat is weak and misplaced, but it exists, so OLS was not used entirely without caveats. Evidence: Limitations: 'exact standard-error-based inference should be interpreted cautiously even though the high-level signal is clear'

### interaction_effects

#### Codex (partial)

**Summary:** The agent correctly identified time_of_day_hour and channel_score as the two dominant features, created a useful interaction heatmap showing their joint effect (13.3% to 72.9% conversion), and appropriately downplayed secondary features. However, the analysis fundamentally fails to formally test the channel_score × time_of_day_hour interaction term, never builds an interaction-aware predictive model, and consequently never demonstrates that a main-effects-only model underperforms. The agent descriptively noticed the interaction pattern ('compound') but stopped short of the key analytical step: fitting an interaction term or tree-based model and showing its superiority. This results in a partial verdict — the right pattern was observed but not rigorously established.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 33%
**Supporting Coverage:** 83%
**Oracle Attainment (roc_auc):** 38%
**Efficiency:** report_chars=6563, trace_events=71, transcript_chars=63573

**Must Have**
- `interaction_effects_interaction_tested`: partial. The agent tested a page_load_time_sec * device interaction term in logistic regression (AIC comparison shown), and created a descriptive heatmap of channel_score × time_of_day_hour conversion rates. However, the agent never formally tested the key channel_score × time_of_day_hour interaction term in any model, nor used a tree-based or other inherently non-additive model. Evidence: m2 = smf.logit('converted ~ ad_budget_usd_z + time_of_day_hour_z + channel_score_z + page_load_time_sec_z * C(device) + previous_visits_z', data=df).fit() ... AIC base/inter 1669.49 1670.61
- `interaction_effects_main_effects_only_underperforms`: miss. The agent never built an interaction-aware model (with the key channel×time interaction) and compared its performance to the main-effects model. The only AIC comparison was between the base model and a page_load*device interaction model, which showed no improvement. No ROC-AUC comparison between main-effects-only and interaction-aware models is provided. Evidence: ROC AUC 0.69 ± 0.03 reported only for the main-effects logistic regression. No interaction-aware model performance is reported.
- `interaction_effects_channel_time_interaction_identified`: partial. The agent descriptively identified that time_of_day_hour and channel_score 'compound' and created a heatmap showing rates from 13.3% to 72.9%. However, the agent treats these primarily as two strong independent main effects that happen to align, rather than formally identifying their interaction as THE key driver of the classification boundary. No formal interaction term was tested. Evidence: Finding 3: 'Time of day and channel score compound' ... 'the strongest practical signal is to align delivery toward sessions that are both late-day and high-channel-score' ... heatmap shows 13.3% (0-6, low channel) to 72.9% (18-24, high channel)

**Supporting**
- `interaction_effects_interaction_visualized`: hit. The agent created a time_channel_interaction_heatmap.png showing conversion rates across time-of-day bands and channel-score quartiles, clearly illustrating how conversion varies across combinations. Evidence: time_channel_interaction_heatmap.png shows lowest-converting segment at 13.3% (0-6 plus bottom channel-score quartile) and highest at 72.9% (18-24 plus top channel-score quartile)
- `interaction_effects_secondary_features_not_overstated`: hit. The agent correctly identifies device, page_load_time_sec, ad_budget_usd, and previous_visits as weak/non-significant, with confidence intervals crossing 1.0 in the adjusted model, and explicitly cautions against overstating them. Evidence: 'ad_budget_usd, page_load_time_sec, previous_visits, and device indicators all have confidence intervals that cross 1.0' ... 'more spend per session, faster pages within the observed range, and device category do not show strong independent effects'
- `interaction_effects_non_additive_language`: partial. The agent uses language like 'compound' and 'both late-day and high-channel-score,' which hints at non-additivity. However, the report never explicitly states that the effect of one variable depends on the value of the other — the core non-additive insight. The framing remains largely as two independently strong effects that happen to combine well. Evidence: 'those factors compound' ... 'the best conversion outcomes occur when high-intent traffic arrives at high-intent times'

**Forbidden**
- `interaction_effects_main_effects_only_conclusion`: miss. While the agent's formal modeling is primarily additive, they did test one interaction term (page_load*device), created a channel×time interaction heatmap, and acknowledged the compounding pattern. This shows awareness of interactions, even though the key interaction was not formally modeled. The agent did not completely ignore interactions. Evidence: Tested page_load*device interaction; created time_channel_interaction_heatmap; mentioned 'compound' effect of time and channel.
- `interaction_effects_misses_interaction_pattern`: miss. The agent explicitly discusses the compounding effect of channel_score and time_of_day_hour and does not explain conversion entirely through separate main effects. Finding 3 specifically addresses their joint pattern. Evidence: Finding 3: 'Time of day and channel score compound, while budget and page speed add little signal' ... heatmap shows clear interaction pattern

### multimodal

#### Codex (wrong)

**Summary:** The agent produced a technically competent regression analysis but completely missed the dataset's defining characteristic: a three-component Gaussian mixture in the rent distribution. By skipping the fundamental step of plotting the target variable's distribution, the agent never discovered the multimodality, never identified the three modes, and never questioned single-Gaussian assumptions. Instead, it summarized rent with aggregate statistics and fit OLS models throughout, triggering both forbidden criteria. The analysis is well-structured and honest about its limitations (heteroskedasticity, non-normal residuals, unmodeled segments), but these observations were treated as minor diagnostics rather than clues pointing to the core pattern. This is a clear failure of exploratory discipline — the agent went directly from summary statistics to regression without the essential distribution inspection step.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 0%
**Supporting Coverage:** 0%
**Fatal Errors:**
- Assume the rent distribution is approximately normal without checking it.
- Summarize the target with mean and variance only while missing the multiple modes.
**Efficiency:** report_chars=9328, trace_events=73, transcript_chars=100690

**Must Have**
- `multimodal_distribution_visualized`: miss. The agent never created a histogram, KDE, or density plot of the monthly_rent_usd distribution. Plots produced were rent_vs_sqft, adjusted_effects, residuals_vs_fitted, and price_per_sqft_vs_sqft — none of which show the univariate shape of the target variable. Evidence: No histogram or KDE of rent appears in the report or session transcript. The agent's plots focus entirely on bivariate relationships and model diagnostics.
- `multimodal_multimodality_identified`: miss. The agent never identified that the rent distribution is multimodal. The closest remark is about 'meaningful outliers or unmodeled segments' in the limitations section, which is a passing diagnostic comment about OLS residuals, not a finding about the target distribution's shape. Evidence: "Residuals are not perfectly normal, and the largest absolute residuals exceed $1,000, so there are meaningful outliers or unmodeled segments."
- `multimodal_three_modes_noted`: miss. The agent never mentioned three modes, three peaks, or three clusters in the rent distribution. No mixture analysis, mode-finding, or segmentation of the target variable was attempted.
- `multimodal_single_gaussian_rejected`: miss. The agent never explicitly rejected a single-Gaussian assumption for the rent distribution. The entire analysis proceeds with OLS regression, implicitly treating rent as unimodal. While heteroskedasticity and non-normal residuals are noted, these are treated as diagnostic caveats rather than evidence against the distributional assumption. Evidence: "A Breusch-Pagan test strongly rejects constant variance... Coefficient signs and relative magnitudes are still informative, but classical OLS standard errors should be interpreted with caution."

**Supporting**
- `multimodal_segment_interpretation`: miss. No market segments or subpopulations were identified in the rent distribution. The agent analyzed rent purely as a function of predictors without recognizing distinct subpopulations.
- `multimodal_mode_locations_approximated`: miss. No modes were identified, so no mode locations were approximated.
- `multimodal_mixture_or_segmentation_suggested`: miss. The agent never suggested mixture models or segmentation for the rent distribution. The limitations section mentions not clustering listings into submarkets, but frames this as unnecessary rather than as a missed opportunity, and the rationale given is about geography, not about the target distribution's shape. Evidence: "I did not cluster listings into latent neighborhoods or submarkets because the dataset has no explicit geography beyond distance to center."

**Forbidden**
- `multimodal_assumes_normality`: hit. The agent never inspected the rent distribution's shape and proceeded to fit OLS models throughout, implicitly treating rent as unimodal. While residual diagnostics are mentioned as caveats, the agent never actually checked whether the target itself is normally distributed or multimodal. The entire modeling framework assumes a single continuous relationship. Evidence: The agent summarized rent with mean ($1,737), median ($1,515.50), and std ($997), then immediately moved to OLS regression without ever plotting or testing the distribution of the target variable.
- `multimodal_summary_only_distribution`: hit. The agent summarized monthly_rent_usd exclusively with aggregate statistics (mean, median, range, percentiles, standard deviation) and completely missed the three-mode structure. No distributional shape analysis was performed on the target. Evidence: "Rent ranges from $347 to $4,769 per month, with mean $1,737 and median $1,515.50."
