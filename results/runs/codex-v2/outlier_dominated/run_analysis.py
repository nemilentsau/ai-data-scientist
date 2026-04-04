from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def save_and_review(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    img = mpimg.imread(path)
    if img.ndim < 2 or min(img.shape[0], img.shape[1]) < 400:
        raise ValueError(f"Plot {path.name} appears too small to be legible: {img.shape}")
    if float(np.nanstd(img)) < 0.01:
        raise ValueError(f"Plot {path.name} appears nearly blank")


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    PLOTS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    clean = df[df["order_total_usd"] >= 0].copy()
    df["is_negative_total"] = (df["order_total_usd"] < 0).astype(int)
    clean["subtotal_after_discount"] = (
        clean["items_qty"] * clean["unit_price_usd"] * (1 - clean["discount_pct"] / 100)
    )
    clean["markup"] = (
        clean["order_total_usd"] - clean["subtotal_after_discount"] - clean["shipping_usd"]
    )
    clean["price_quintile"] = pd.qcut(
        clean["unit_price_usd"], q=5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"]
    )

    neg_count = int(df["is_negative_total"].sum())
    neg_share = neg_count / len(df)
    return_rate = df["returned"].mean()
    segment_counts = df["customer_segment"].value_counts()

    ct_segment = pd.crosstab(df["customer_segment"], df["returned"])
    chi2_segment, p_segment, _, _ = stats.chi2_contingency(ct_segment)

    ct_high_price = pd.crosstab(
        df["unit_price_usd"] >= df["unit_price_usd"].quantile(0.8), df["returned"]
    )
    chi2_hp, p_hp, _, _ = stats.chi2_contingency(ct_high_price)
    top_price_return = df.loc[df["unit_price_usd"] >= df["unit_price_usd"].quantile(0.8), "returned"].mean()
    rest_price_return = df.loc[df["unit_price_usd"] < df["unit_price_usd"].quantile(0.8), "returned"].mean()

    pre = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="median")),
                        ("sc", StandardScaler()),
                    ]
                ),
                [
                    "items_qty",
                    "unit_price_usd",
                    "shipping_usd",
                    "discount_pct",
                    "order_total_usd",
                    "is_negative_total",
                ],
            ),
            ("cat", OneHotEncoder(drop="first"), ["customer_segment"]),
        ]
    )
    clf = Pipeline(
        [("pre", pre), ("lr", LogisticRegression(max_iter=2000, class_weight="balanced"))]
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(
        clf,
        df[
            [
                "customer_segment",
                "items_qty",
                "unit_price_usd",
                "shipping_usd",
                "discount_pct",
                "order_total_usd",
                "is_negative_total",
            ]
        ],
        df["returned"],
        cv=cv,
        scoring="roc_auc",
    )

    samples = [g["order_total_usd"].values for _, g in clean.groupby("customer_segment")]
    kruskal_total = stats.kruskal(*samples)

    X = pd.get_dummies(
        clean[["customer_segment", "items_qty", "unit_price_usd", "shipping_usd", "discount_pct"]],
        drop_first=True,
    )
    X = sm.add_constant(X).astype(float)
    ols = sm.OLS(np.log1p(clean["order_total_usd"]), X).fit()

    subtotal_X = sm.add_constant(clean[["subtotal_after_discount", "shipping_usd"]]).astype(float)
    subtotal_model = sm.OLS(clean["order_total_usd"], subtotal_X).fit()
    clean["subtotal_pred"] = subtotal_model.predict(subtotal_X)
    clean["subtotal_resid"] = clean["order_total_usd"] - clean["subtotal_pred"]
    spearman_subtotal = stats.spearmanr(clean["subtotal_after_discount"], clean["order_total_usd"])

    price_quintile_stats = (
        clean.groupby("price_quintile", observed=False)["returned"]
        .agg(["mean", "count", "sum"])
        .reset_index()
    )
    z = 1.96
    price_quintile_stats["wilson_low"] = (
        (
            price_quintile_stats["mean"]
            + z**2 / (2 * price_quintile_stats["count"])
            - z
            * np.sqrt(
                (
                    price_quintile_stats["mean"] * (1 - price_quintile_stats["mean"])
                    + z**2 / (4 * price_quintile_stats["count"])
                )
                / price_quintile_stats["count"]
            )
        )
        / (1 + z**2 / price_quintile_stats["count"])
    )
    price_quintile_stats["wilson_high"] = (
        (
            price_quintile_stats["mean"]
            + z**2 / (2 * price_quintile_stats["count"])
            + z
            * np.sqrt(
                (
                    price_quintile_stats["mean"] * (1 - price_quintile_stats["mean"])
                    + z**2 / (4 * price_quintile_stats["count"])
                )
                / price_quintile_stats["count"]
            )
        )
        / (1 + z**2 / price_quintile_stats["count"])
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=df,
        x="order_id",
        y="order_total_usd",
        hue="is_negative_total",
        palette={0: "#1f77b4", 1: "#d62728"},
        alpha=0.7,
        s=35,
        ax=ax,
    )
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Order totals include a small set of extreme negative anomalies")
    ax.set_xlabel("Order ID")
    ax.set_ylabel("Order total (USD)")
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles, ["Non-negative total", "Negative total"], title="")
    save_and_review(fig, PLOTS_DIR / "order_total_anomalies.png")

    cap = clean["order_total_usd"].quantile(0.99)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(
        data=clean,
        x="customer_segment",
        y="order_total_usd",
        order=["New", "Returning", "VIP"],
        hue="customer_segment",
        dodge=False,
        palette={"New": "#7aa6c2", "Returning": "#5d8a66", "VIP": "#d28f5a"},
        legend=False,
        showfliers=False,
        ax=ax,
    )
    ax.set_ylim(0, cap)
    ax.set_title("Cleaned order totals overlap strongly across segments")
    ax.set_xlabel("Customer segment")
    ax.set_ylabel("Order total (USD), capped at 99th percentile")
    save_and_review(fig, PLOTS_DIR / "segment_total_clean_boxplot.png")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=price_quintile_stats,
        x="price_quintile",
        y="mean",
        color="#4c78a8",
        ax=ax,
    )
    ax.errorbar(
        x=np.arange(len(price_quintile_stats)),
        y=price_quintile_stats["mean"],
        yerr=[
            price_quintile_stats["mean"] - price_quintile_stats["wilson_low"],
            price_quintile_stats["wilson_high"] - price_quintile_stats["mean"],
        ],
        fmt="none",
        ecolor="black",
        capsize=5,
        linewidth=1.3,
    )
    ax.set_title("Return rate drifts upward in the highest price quintile")
    ax.set_xlabel("Unit price quintile")
    ax.set_ylabel("Return rate")
    ax.set_ylim(0, max(0.16, price_quintile_stats["wilson_high"].max() + 0.01))
    save_and_review(fig, PLOTS_DIR / "return_rate_by_price_quintile.png")

    scatter_cap = clean["order_total_usd"].quantile(0.995)
    fig, ax = plt.subplots(figsize=(10, 6))
    subset = clean[clean["order_total_usd"] <= scatter_cap].copy()
    sns.scatterplot(
        data=subset,
        x="subtotal_after_discount",
        y="order_total_usd",
        alpha=0.45,
        s=32,
        color="#2a9d8f",
        ax=ax,
    )
    max_lim = max(subset["subtotal_after_discount"].quantile(0.995), scatter_cap)
    ax.plot([0, max_lim], [0, max_lim], linestyle="--", color="black", linewidth=1)
    ax.set_xlim(0, max_lim)
    ax.set_ylim(0, scatter_cap)
    ax.set_title("Order totals rise with discounted subtotal, but not one-for-one")
    ax.set_xlabel("Discounted subtotal estimate (USD)")
    ax.set_ylabel("Recorded order total (USD)")
    save_and_review(fig, PLOTS_DIR / "total_vs_subtotal_clean.png")

    report = f"""# Analysis Report

## What the dataset is about

This is an order-level ecommerce-style dataset with 1,200 rows and 8 columns: an order identifier, customer segment, quantity, unit price, shipping charge, discount rate, recorded order total, and a binary return flag.

The basic structure is clean: there are no nulls, `order_id` is unique for every row, `customer_segment` has three levels (`Returning`: {segment_counts['Returning']}, `New`: {segment_counts['New']}, `VIP`: {segment_counts['VIP']}), shipping is coded at four fixed price points (`0`, `4.99`, `9.99`, `14.99`), discounts are coded at five fixed percentages (`0`, `5`, `10`, `15`, `20`), and the overall return rate is {pct(return_rate)} ({int(df['returned'].sum())} of 1,200).

Two features require caution before interpretation:

1. `order_total_usd` contains 28 negative values ({pct(neg_share)} of rows), including extreme values down to -19,240.64. Most of those rows are **not** marked as returned (25 of 28), so they do not behave like standard refunds or cancellations.
2. `order_total_usd` cannot be exactly reconstructed from `items_qty`, `unit_price_usd`, `discount_pct`, and `shipping_usd`. Even after restricting to non-negative totals, the residual spread is large enough to suggest either hidden charges/taxes or synthetic noise. That means spending analyses should be treated as directional rather than accounting-precise.

Raw rows otherwise look plausible for an order table: quantities range from 1 to 19, unit prices from 5.63 to 199.89, and return is encoded as `0` or `1`.

## Key findings

### 1. Negative order totals are a small but material anomaly, not a valid business pattern

**Hypothesis:** The negative totals represent a meaningful business state such as returned orders or refunds.

**Test:** Compare negative-total rows with the `returned` flag and visualize all order totals across the full dataset.

**Result:** The hypothesis is refuted. Only 3 of the 28 negative-total rows are marked as returned. The remaining 25 sit among otherwise ordinary orders and span all three segments. [order_total_anomalies.png]({(PLOTS_DIR / 'order_total_anomalies.png').resolve()}) shows these values as isolated points far below the rest of the data rather than a separate operational regime.

**Interpretation:** These rows are best treated as data anomalies or bookkeeping fields encoded inconsistently with the rest of the table. They are too few to dominate the dataset, but they are large enough to distort any average or model that uses `order_total_usd` naively. For that reason, all spending comparisons below use the 1,172 non-negative rows.

### 2. Customer segment does not explain spending once order composition is known

**Hypothesis:** VIP or returning customers place systematically larger orders than new customers.

**Test:** Compare cleaned order totals across segments, then fit a regression for `log(1 + order_total_usd)` using segment plus quantity, unit price, shipping, and discount.

**Result:** The segment-only story is weak. On the cleaned subset, median order totals are 758.12 for `New`, 813.93 for `Returning`, and 868.62 for `VIP`, but the overall distributional difference is not statistically significant (Kruskal-Wallis p = {kruskal_total.pvalue:.3f}). This overlap is visible in [segment_total_clean_boxplot.png]({(PLOTS_DIR / 'segment_total_clean_boxplot.png').resolve()}).

In the regression, `items_qty` and `unit_price_usd` dominate:

- `items_qty` coefficient: {ols.params['items_qty']:.3f} on log-total, p < 0.001
- `unit_price_usd` coefficient: {ols.params['unit_price_usd']:.3f} on log-total, p < 0.001
- `customer_segment_Returning`: {ols.params['customer_segment_Returning']:.3f}, p = {ols.pvalues['customer_segment_Returning']:.3f}
- `customer_segment_VIP`: {ols.params['customer_segment_VIP']:.3f}, p = {ols.pvalues['customer_segment_VIP']:.3f}

The model explains about {pct(ols.rsquared)} of the variance in log-order-total, and almost all of that explanatory power comes from quantity and unit price rather than segment.

**Interpretation:** Apparent segment differences are mostly compositional. VIP customers do not appear to spend more because they are VIP; they spend more only insofar as they buy slightly more items or higher-priced items on a given order.

### 3. Returns are only weakly related to the observed order attributes

**Hypothesis:** Returns can be meaningfully predicted from segment, price, quantity, discount, shipping, and total.

**Test:** Check segment-level differences, compare return rates across price bands, and fit a cross-validated logistic regression.

**Result:** The evidence for strong return structure is weak.

- Segment is not associated with return at conventional significance levels (chi-square = {chi2_segment:.3f}, p = {p_segment:.3f}).
- The highest unit-price quintile has the highest return rate, but the effect is modest: {pct(top_price_return)} in the top quintile versus {pct(rest_price_return)} in the other four combined, with chi-square p = {p_hp:.3f}. This pattern is shown in [return_rate_by_price_quintile.png]({(PLOTS_DIR / 'return_rate_by_price_quintile.png').resolve()}).
- A logistic regression using all observed fields achieved mean 5-fold ROC AUC of {auc_scores.mean():.3f} (std {auc_scores.std():.3f}), which is effectively no predictive signal.

**Interpretation:** Returns in this dataset are close to irreducible given the available columns. There may be some weak tendency for high-priced items to be returned more often, but the dataset does not support operational targeting based on these variables alone.

### 4. Recorded order totals track discounted subtotal directionally, but not mechanically

**Hypothesis:** `order_total_usd` is a near-deterministic function of quantity, unit price, discount, and shipping.

**Test:** Compare the recorded total against a discounted subtotal estimate and fit a simple regression of `order_total_usd` on discounted subtotal plus shipping.

**Result:** The relationship is monotonic but not tightly accounting-based. The Spearman correlation between discounted subtotal and recorded total is {spearman_subtotal.statistic:.3f}, but the linear model explains only {pct(subtotal_model.rsquared)} of the variance, and the median markup over discounted subtotal plus shipping is 50.90 USD with a long right tail up to 19,867.89 USD. [total_vs_subtotal_clean.png]({(PLOTS_DIR / 'total_vs_subtotal_clean.png').resolve()}) shows that totals generally rise with subtotal, but many points sit far above the one-to-one line.

**Interpretation:** The total field likely includes unobserved components or synthetic perturbation. It is still useful as a rough size metric after excluding negatives, but it should not be treated as a clean accounting target for reconciliation or margin analysis.

## Practical implications

- For spending analysis, exclude the 28 negative-total rows or handle them in a separate anomaly workflow.
- For customer strategy, segment labels alone are not a strong lever in this data. Order composition matters more than whether a customer is `New`, `Returning`, or `VIP`.
- For returns, the observed fields are inadequate for accurate prediction. Better signals would likely come from product category, fulfillment problems, customer history, or time-to-delivery, none of which are present here.

## Limitations and self-critique

- The largest limitation is field semantics. I assumed negative totals are data quality issues because they do not align with the return flag, but without documentation they could reflect an undocumented accounting process.
- I treated the non-negative subset as the best basis for monetary comparisons. If the negative rows are actually legitimate and systematically different, then the cleaned analyses understate that process.
- The weak return findings may reflect missing predictors rather than true randomness. A low-AUC model here means “little signal in these columns,” not “returns are inherently unpredictable.”
- I did not test causal claims, because the dataset is observational and lacks time, product, and customer-history fields. All findings are associative.
- The irregular relationship between `order_total_usd` and the other monetary columns means effect sizes tied to totals should be interpreted cautiously. This is especially important for any downstream forecasting or unit-economics work.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
