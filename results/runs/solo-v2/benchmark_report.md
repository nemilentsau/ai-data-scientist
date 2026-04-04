# AI Data Scientist Benchmark Results

## Summary

| Dataset | Claude | Codex | Winner |
|---------|--------|-------|--------|
| outlier_dominated | partial (83%) | - | - |

## Agent Metrics

| Agent | Solve Rate | Wrong Rate | Run Error Rate | Avg Required | Avg Supporting | Avg Oracle |
|-------|------------|------------|----------------|--------------|----------------|-----------|
| Claude | 0% | 0% | 0% | 83% | 100% | 0% |

## Detailed Results

### outlier_dominated

#### Claude (partial)

**Summary:** The agent delivers a thorough and well-structured analysis that successfully detects the 60 extreme outliers (5%), reconstructs expected totals from component variables, quantifies the outlier fraction, justifies their handling with multiple statistical tests, and correctly avoids confusing segments with the outlier problem. No forbidden criteria are triggered. However, the analysis falls short on a key must-have: while it implicitly shows that outliers distort the data (R²=0.99999 on clean data vs R²=0.984 on full data), the agent frames this as a 'discount pricing bug' rather than explicitly discussing how extreme values dominate OLS regression. The agent never compares robust vs non-robust estimators or explicitly demonstrates how the small fraction of extreme values distorts the main relationship — the central analytical pattern this dataset was designed to test. This results in a partial verdict: strong detection and handling, but incomplete framing of the core statistical insight.
**Run Status:** completed
**Rerun Recommended:** no
**Core Insight:** fail
**Required Coverage:** 83%
**Supporting Coverage:** 100%
**Efficiency:** report_chars=9916, trace_events=62, transcript_chars=227862

**Must Have**
- `outlier_dominated_outliers_detected`: hit. The agent clearly identifies 60 anomalous orders (5%) with extreme totals ranging from -$19,241 to $21,439, noting 28 negative and 32 extreme positive totals with no relationship to order features. Evidence: Finding 4: 'Sixty orders have totals that don't follow any pricing formula — 28 have negative totals (down to -$19,241) and 32 have extreme positive totals (up to $21,439) with no relationship to the order's items, prices, or discounts.'
- `outlier_dominated_influence_on_fit_explained`: partial. The agent implicitly shows that outliers distort the relationship: clean data fits R²=0.99999 while full-data fit is R²=0.984. However, the agent never explicitly frames this as 'outliers dominate OLS' or 'extreme values distort the regression.' Instead the framing is about a 'discount pricing bug.' The connection between outliers and regression distortion is left for the reader to infer rather than stated directly. Evidence: R²=0.99999 on clean data vs R²=0.984 on all data is presented, but attributed to discount formula differences rather than outlier influence. No explicit OLS-vs-outlier comparison is made.
- `outlier_dominated_robust_or_justified_handling`: hit. While the agent does not compare robust estimators against naive OLS, it does justify a careful outlier handling strategy: outliers are identified via formula deviation (negative totals or ratio outside [0.5, 3.0]), characterized statistically (no feature correlations, random across segments), interpreted as system errors, and separated from clean analysis. This constitutes a justified handling strategy per the 'or' in the criterion. Evidence: Finding 4: 'No distinguishing features — item quantity, unit price, discount, and shipping are statistically identical to normal orders (all Mann-Whitney p > 0.18).' Limitations section: 'Orders were classified as anomalous if order_total < 0 or the ratio of actual to expected total was outside [0.5, 3.0].'

**Supporting**
- `outlier_dominated_reconstructs_expected_total`: hit. The agent computes expected totals from component variables (qty × price + shipping) and shows extreme totals are completely inconsistent with normal pricing, with detailed residual analysis and plots. Evidence: Finding 1: 'order_total = items_qty × unit_price_usd + shipping_usd (R² = 0.99999)' for clean orders; Finding 4 shows anomalous orders 'have no relationship to the order's items, prices, or discounts.'
- `outlier_dominated_outlier_fraction_quantified`: hit. The agent precisely quantifies: 60 anomalous orders representing 5% of the dataset, broken down into 28 negative and 32 extreme positive. Evidence: Finding 4 title: '60 Anomalous Orders (5%) with Wildly Incorrect Totals'
- `outlier_dominated_segment_not_confused`: hit. The agent explicitly separates segment analysis from the outlier problem. Section 3 analyzes segments on clean orders only, and Finding 4 confirms outliers are randomly distributed across segments with no distinguishing features. Evidence: Finding 4: 'Randomly distributed across customer segments, discount levels, shipping tiers.' Section 3 header: 'While segments don't differ in return behavior, they show some differences in ordering patterns (clean orders only).'

**Forbidden**
- `outlier_dominated_trusts_ols_without_diagnostics`: miss. The agent performs extensive outlier diagnostics before interpreting any regression results. Outliers are identified, characterized, and separated before drawing conclusions about the data relationships. Evidence: Session transcript shows systematic investigation of order total discrepancies, formula checking, and anomaly identification before any regression interpretation.
- `outlier_dominated_drops_rows_without_justification`: miss. The agent provides clear justification for separating anomalous rows: formula-based identification criteria, statistical characterization showing no feature correlations, and interpretation as system-level errors. The threshold is even disclosed in the limitations section. Evidence: Limitations: 'Orders were classified as anomalous if order_total < 0 or the ratio of actual to expected total was outside [0.5, 3.0]. This threshold is somewhat arbitrary; a different cutoff would reclassify a small number of borderline cases.'
