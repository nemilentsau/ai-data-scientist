# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| outlier_dominated | - | partial (83%) | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Run Error Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|----------------|--------------|----------------|-----------|
| Codex | 0% | 0% | 0% | 83% | 100% | 0% |

## Detailed Results

### outlier_dominated

#### Codex (partial)

**Summary:** The agent delivers a thorough and well-structured data quality investigation. It correctly identifies extreme order-total outliers via residual analysis against a reconstructed basket formula, quantifies their fraction and revenue impact at multiple thresholds, and cleanly separates the outlier problem from the segment/return analysis. The main shortcoming is the lack of an explicit robust-vs-OLS estimator comparison: the agent never fits a regression model to demonstrate how outliers dominate OLS, nor does it show a robust alternative performing better. This keeps the third must-have at partial. No forbidden criteria are violated. Verdict: partial.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** pass
**Required Coverage:** 83%
**Supporting Coverage:** 100%
**Efficiency:** report_chars=7168, trace_events=53, transcript_chars=76066

**Must Have**
- `outlier_dominated_outliers_detected`: hit. The agent thoroughly detects extreme order-total outliers using multiple approaches: negative totals, residual analysis against computed basket totals, and threshold-based quantification. Evidence: 28 of 1,200 orders (2.33%) have negative recorded totals; 60 orders (5.0%) differ by more than $5,000 from computed basket total; 39 orders (3.25%) by more than $10,000. Range from -$19,240.64 to $21,438.55 flagged as implausible.
- `outlier_dominated_influence_on_fit_explained`: hit. The agent clearly explains that outliers distort the main relationship. The correlation between computed basket total and recorded order_total_usd is shown to be only r=0.279 (should be ~1.0), and the impact on means and revenue totals is explicitly quantified. Evidence: "The correlation between computed basket total and recorded order_total_usd is only r = 0.279, far weaker than expected for a true total." Mean shifts from $1,093 to $1,370 excluding negatives. "The anomalies are large enough to materially bias revenue totals and averages, not just a cosmetic edge case."
- `outlier_dominated_robust_or_justified_handling`: partial. The agent justifies a careful outlier handling strategy (identify via residual analysis, quantify impact, recommend rebuilding from components) but never actually fits or compares robust vs. non-robust estimators. The analysis stays at the data-quality investigation level without demonstrating a robust regression or showing OLS vs. robust side by side. Evidence: Agent recommends: "rebuild a trustworthy revenue metric from items_qty, unit_price_usd, discount_pct, and shipping_usd, then reconcile it against the recorded total." Shows with/without statistics but no OLS or robust model is ever fit.

**Supporting**
- `outlier_dominated_reconstructs_expected_total`: hit. The agent computes the basket formula and systematically shows that extreme totals are inconsistent with what the component variables predict. Evidence: "items_qty * unit_price_usd * (1 - discount_pct/100) + shipping_usd does not reproduce order_total_usd except in 4 rows." 79.2% within ±$200 but 60 orders off by >$5,000. 28 negative totals despite all components being nonnegative. Scatter plot vs 45-degree line produced.
- `outlier_dominated_outlier_fraction_quantified`: hit. The agent precisely quantifies the outlier fraction at multiple thresholds and their revenue impact. Evidence: 28 orders (2.33%) negative totals; 60 orders (5.0%) >$5,000 residual; 39 orders (3.25%) >$10,000 residual. Revenue impact: $1,312,114 → $1,605,912 excluding negatives (~$293K difference).
- `outlier_dominated_segment_not_confused`: hit. The agent cleanly separates the outlier problem (Finding #1-2) from segment analysis (Finding #3) and explicitly shows segments are not the main issue. Evidence: Chi-square test p=0.595 for segment vs returns. AUC=0.492 for logistic regression. "The available transactional fields do not contain meaningful predictive signal for returns." Main conclusion is data quality, not segment behavior.

**Forbidden**
- `outlier_dominated_trusts_ols_without_diagnostics`: miss. The agent never fits or interprets OLS without diagnostics. All statistical analysis is preceded by thorough outlier investigation. The only model fit (logistic regression for returns) comes after extensive diagnostics. Evidence: The entire analysis is structured as outlier diagnostics first, modeling second. The agent explicitly warns against using order_total_usd without auditing.
- `outlier_dominated_drops_rows_without_justification`: miss. The agent never silently removes rows. When showing statistics excluding negatives, it is done as a comparison to quantify impact, not as unexplained data removal. The recommendation is to audit and rebuild, not to drop. Evidence: "order_total_usd should not be used as a revenue metric without auditing upstream logic first." Statistics shown both with and without negative rows as explicit comparison.
