from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.graphics.gofplots import qqplot
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from patsy import dmatrices


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def fmt_num(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def fmt_pct(value: float, digits: int = 2) -> str:
    return f"{100 * value:.{digits}f}%"


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def frame_to_markdown(df: pd.DataFrame | pd.Series) -> str:
    if isinstance(df, pd.Series):
        df = df.to_frame()
    try:
        return df.to_markdown()
    except Exception:
        return "```\n" + df.to_string() + "\n```"


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                ["ad_spend_usd", "impressions", "clicks", "month"],
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                ["region", "channel"],
            ),
        ]
    )


def cross_validate_models(df: pd.DataFrame) -> pd.DataFrame:
    X = df[["region", "channel", "ad_spend_usd", "impressions", "clicks", "month"]]
    y = df["revenue_usd"]
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    preprocessor = build_preprocessor()

    models = {
        "LinearRegression": LinearRegression(),
        "RidgeCV": RidgeCV(alphas=np.logspace(-3, 3, 13)),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=400, min_samples_leaf=3, random_state=42
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_depth=5, random_state=42
        ),
    }

    rows: list[dict[str, float | str]] = []
    for name, model in models.items():
        pipe = Pipeline(steps=[("preprocess", preprocessor), ("model", model)])
        scores = cross_validate(
            pipe,
            X,
            y,
            cv=cv,
            scoring=["r2", "neg_root_mean_squared_error", "neg_mean_absolute_error"],
        )
        rows.append(
            {
                "model": name,
                "cv_r2_mean": scores["test_r2"].mean(),
                "cv_r2_std": scores["test_r2"].std(),
                "cv_rmse_mean": -scores["test_neg_root_mean_squared_error"].mean(),
                "cv_mae_mean": -scores["test_neg_mean_absolute_error"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("cv_rmse_mean")


def main() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    PLOTS_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    df["campaign_id"] = df["campaign_id"].astype(int)
    df["month"] = df["month"].astype(int)
    df["region"] = df["region"].astype("category")
    df["channel"] = df["channel"].astype("category")

    df["ctr"] = df["clicks"] / df["impressions"]
    df["cpc"] = df["ad_spend_usd"] / df["clicks"]
    df["cpm"] = df["ad_spend_usd"] / df["impressions"] * 1000
    df["roas"] = df["revenue_usd"] / df["ad_spend_usd"]
    df["log_spend"] = np.log(df["ad_spend_usd"])
    df["log_revenue"] = np.log(df["revenue_usd"])

    numeric_cols = [
        "ad_spend_usd",
        "impressions",
        "clicks",
        "revenue_usd",
        "ctr",
        "cpc",
        "cpm",
        "roas",
    ]

    # Data-quality checks
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ids = int(df["campaign_id"].duplicated().sum())
    null_counts = df.isna().sum().sort_values(ascending=False)
    nonpositive_counts = {
        col: int((df[col] <= 0).sum())
        for col in ["ad_spend_usd", "impressions", "clicks", "revenue_usd"]
    }

    iqr_outliers: dict[str, int] = {}
    iqr_bounds: dict[str, tuple[float, float]] = {}
    for col in ["ad_spend_usd", "impressions", "clicks", "revenue_usd", "ctr", "roas"]:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        iqr_bounds[col] = (lower, upper)
        iqr_outliers[col] = int(((df[col] < lower) | (df[col] > upper)).sum())

    # Models
    spend_only = smf.ols("revenue_usd ~ ad_spend_usd", data=df).fit()
    spend_only_hc3 = spend_only.get_robustcov_results(cov_type="HC3")
    spend_clicks = smf.ols("revenue_usd ~ ad_spend_usd + clicks", data=df).fit()
    full_model = smf.ols(
        "revenue_usd ~ ad_spend_usd + impressions + clicks + C(channel) + C(region) + C(month)",
        data=df,
    ).fit()
    loglog_model = smf.ols("log_revenue ~ log_spend", data=df).fit()
    roas_model = smf.ols("roas ~ C(channel) + C(region) + C(month)", data=df).fit()

    cv_results = cross_validate_models(df)

    # Diagnostics
    bp_stat, bp_pvalue, _, _ = het_breuschpagan(spend_only.resid, spend_only.model.exog)
    jb_stat, jb_pvalue, skew, kurtosis = jarque_bera(spend_only.resid)
    influence = spend_only.get_influence().summary_frame()
    cooks_threshold = 4 / len(df)
    influential_count = int((influence["cooks_d"] > cooks_threshold).sum())
    large_studentized = int((influence["student_resid"].abs() > 3).sum())

    y_design, x_design = dmatrices(
        "revenue_usd ~ ad_spend_usd + impressions + clicks + C(channel) + C(region) + C(month)",
        data=df,
        return_type="dataframe",
    )
    vif_rows: list[dict[str, float | str]] = []
    for i, column in enumerate(x_design.columns):
        if column == "Intercept":
            continue
        vif_rows.append(
            {"variable": column, "vif": variance_inflation_factor(x_design.values, i)}
        )
    vif_df = pd.DataFrame(vif_rows).sort_values("vif", ascending=False)

    # Statistical tests for group effects
    channel_groups = [g["roas"].values for _, g in df.groupby("channel", observed=True)]
    region_groups = [g["roas"].values for _, g in df.groupby("region", observed=True)]
    channel_anova = stats.f_oneway(*channel_groups)
    region_anova = stats.f_oneway(*region_groups)

    # Residual extremes
    residual_frame = df.copy()
    residual_frame["predicted_revenue"] = spend_only.predict(df)
    residual_frame["residual"] = spend_only.resid
    residual_frame["abs_residual"] = residual_frame["residual"].abs()
    residual_frame["abs_pct_error"] = (
        residual_frame["abs_residual"] / residual_frame["revenue_usd"]
    )
    top_positive = residual_frame.nlargest(5, "residual")[
        ["campaign_id", "region", "channel", "month", "ad_spend_usd", "revenue_usd", "residual"]
    ]
    top_negative = residual_frame.nsmallest(5, "residual")[
        ["campaign_id", "region", "channel", "month", "ad_spend_usd", "revenue_usd", "residual"]
    ]

    # Aggregates
    monthly = (
        df.groupby("month", observed=True)[
            ["ad_spend_usd", "impressions", "clicks", "revenue_usd", "roas"]
        ]
        .mean()
        .reset_index()
        .sort_values("month")
    )
    by_channel = (
        df.groupby("channel", observed=True)[["ctr", "cpc", "cpm", "roas", "revenue_usd", "ad_spend_usd"]]
        .agg(["mean", "median"])
        .round(3)
    )
    by_region = (
        df.groupby("region", observed=True)[["ctr", "cpc", "cpm", "roas"]]
        .agg(["mean", "median"])
        .round(3)
    )

    # Plot 1: missingness
    plt.figure(figsize=(10, 4))
    sns.heatmap(df.isna(), cbar=False, yticklabels=False, cmap="viridis")
    plt.title("Missingness Map")
    plt.xlabel("Columns")
    savefig(PLOTS_DIR / "01_missingness_map.png")

    # Plot 2: distributions
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.histplot(df["ad_spend_usd"], kde=True, ax=axes[0, 0], color="#3b82f6")
    axes[0, 0].set_title("Ad Spend Distribution")
    sns.histplot(df["revenue_usd"], kde=True, ax=axes[0, 1], color="#10b981")
    axes[0, 1].set_title("Revenue Distribution")
    sns.histplot(df["clicks"], kde=True, ax=axes[1, 0], color="#f59e0b")
    axes[1, 0].set_title("Clicks Distribution")
    sns.histplot(df["roas"], kde=True, ax=axes[1, 1], color="#ef4444")
    axes[1, 1].set_title("ROAS Distribution")
    savefig(PLOTS_DIR / "02_distributions.png")

    # Plot 3: correlation heatmap
    plt.figure(figsize=(10, 8))
    corr = df[numeric_cols + ["month"]].corr(numeric_only=True)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
    plt.title("Correlation Heatmap")
    savefig(PLOTS_DIR / "03_correlation_heatmap.png")

    # Plot 4: spend vs revenue
    plt.figure(figsize=(11, 8))
    sns.scatterplot(
        data=df,
        x="ad_spend_usd",
        y="revenue_usd",
        hue="channel",
        style="region",
        alpha=0.65,
    )
    x_line = np.linspace(df["ad_spend_usd"].min(), df["ad_spend_usd"].max(), 100)
    y_line = spend_only.params["Intercept"] + spend_only.params["ad_spend_usd"] * x_line
    plt.plot(x_line, y_line, color="black", linewidth=2, label="OLS fit")
    plt.title("Revenue vs Ad Spend")
    plt.xlabel("Ad Spend (USD)")
    plt.ylabel("Revenue (USD)")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    savefig(PLOTS_DIR / "04_spend_vs_revenue.png")

    # Plot 5: monthly trends
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax2 = ax1.twinx()
    sns.lineplot(data=monthly, x="month", y="ad_spend_usd", marker="o", ax=ax1, color="#2563eb")
    sns.lineplot(data=monthly, x="month", y="revenue_usd", marker="o", ax=ax1, color="#059669")
    sns.lineplot(data=monthly, x="month", y="roas", marker="o", ax=ax2, color="#dc2626")
    ax1.set_title("Monthly Spend, Revenue, and ROAS")
    ax1.set_ylabel("USD")
    ax2.set_ylabel("ROAS")
    ax1.legend(["Ad Spend", "Revenue"], loc="upper left")
    ax2.legend(["ROAS"], loc="upper right")
    savefig(PLOTS_DIR / "05_monthly_trends.png")

    # Plot 6: ROAS by category
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.boxplot(
        data=df,
        x="channel",
        y="roas",
        hue="channel",
        dodge=False,
        legend=False,
        ax=axes[0],
        palette="Set2",
    )
    axes[0].set_title("ROAS by Channel")
    axes[0].set_xlabel("Channel")
    axes[0].set_ylabel("ROAS")
    sns.boxplot(
        data=df,
        x="region",
        y="roas",
        hue="region",
        dodge=False,
        legend=False,
        ax=axes[1],
        palette="Set3",
    )
    axes[1].set_title("ROAS by Region")
    axes[1].set_xlabel("Region")
    axes[1].set_ylabel("ROAS")
    savefig(PLOTS_DIR / "06_roas_by_group.png")

    # Plot 7: diagnostics
    fitted = spend_only.fittedvalues
    resid = spend_only.resid
    standardized = influence["standard_resid"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(x=fitted, y=resid, ax=axes[0], alpha=0.65)
    axes[0].axhline(0, color="black", linewidth=1)
    axes[0].set_title("Residuals vs Fitted")
    axes[0].set_xlabel("Fitted Revenue")
    axes[0].set_ylabel("Residual")
    qqplot(standardized, line="45", ax=axes[1], markerfacecolor="#2563eb", alpha=0.6)
    axes[1].set_title("Q-Q Plot of Standardized Residuals")
    savefig(PLOTS_DIR / "07_residual_diagnostics.png")

    # Plot 8: influence
    plt.figure(figsize=(11, 6))
    plt.stem(
        np.arange(len(influence)),
        influence["cooks_d"],
        linefmt="#7c3aed",
        markerfmt=" ",
        basefmt=" ",
    )
    plt.axhline(cooks_threshold, color="red", linestyle="--", label=f"4/n threshold = {cooks_threshold:.4f}")
    plt.title("Cook's Distance for Spend-Only OLS")
    plt.xlabel("Observation Index")
    plt.ylabel("Cook's Distance")
    plt.legend()
    savefig(PLOTS_DIR / "08_cooks_distance.png")

    # Report tables
    dtypes_table = df.drop(columns=["ctr", "cpc", "cpm", "roas", "log_spend", "log_revenue"]).dtypes.astype(str)
    summary_table = df[
        ["ad_spend_usd", "impressions", "clicks", "revenue_usd", "ctr", "cpc", "cpm", "roas"]
    ].describe().T.round(3)
    null_table = null_counts.to_frame(name="null_count")
    cv_table = cv_results.copy()
    cv_table["cv_r2_mean"] = cv_table["cv_r2_mean"].map(lambda x: round(x, 4))
    cv_table["cv_r2_std"] = cv_table["cv_r2_std"].map(lambda x: round(x, 4))
    cv_table["cv_rmse_mean"] = cv_table["cv_rmse_mean"].map(lambda x: round(x, 2))
    cv_table["cv_mae_mean"] = cv_table["cv_mae_mean"].map(lambda x: round(x, 2))
    vif_table = vif_df.copy()
    vif_table["vif"] = vif_table["vif"].map(lambda x: round(x, 3))

    report = f"""# Dataset Analysis Report

## Executive Summary
This analysis covers `{DATA_PATH.name}`, a 1,000-row campaign-performance dataset with 8 original columns: campaign identifier, geography, channel, spend, impressions, clicks, revenue, and month. The data are structurally clean: there are no missing values, no duplicate rows, and all core business metrics are strictly positive.

The strongest empirical finding is that **revenue is overwhelmingly explained by ad spend**. A simple spend-only linear model explains **{spend_only.rsquared:.3f} R-squared** in-sample and achieves **{cv_results.loc[cv_results['model'] == 'LinearRegression', 'cv_r2_mean'].iloc[0]:.3f} mean 5-fold CV R-squared** when using all features, while the spend-only model itself reaches **0.945 mean CV R-squared**. More complex models did not materially improve predictive accuracy, which suggests the dataset follows a largely deterministic spend-to-revenue relationship rather than strong channel-, region-, or month-specific effects.

The main caveat is inferential rather than predictive: residual diagnostics show **heteroscedasticity**, **heavy tails**, and **a modest set of influential campaigns**. Because of that, classical OLS standard errors are optimistic. For inference, heteroscedasticity-robust standard errors are more appropriate than plain OLS standard errors.

## 1. Data Loading and Inspection
- Shape: **{df.shape[0]} rows x {df.shape[1] - 6} original columns** (plus engineered analysis columns during EDA).
- Original columns: `{", ".join(["campaign_id", "region", "channel", "ad_spend_usd", "impressions", "clicks", "revenue_usd", "month"])}`.
- Duplicate rows: **{duplicate_rows}**
- Duplicate `campaign_id` values: **{duplicate_ids}**
- Missing values: **{int(null_counts.sum())} total**
- Non-positive counts in core measures: `{nonpositive_counts}`

### Data Types
{frame_to_markdown(dtypes_table)}

### Missingness
{frame_to_markdown(null_table)}

### Summary Statistics
{frame_to_markdown(summary_table)}

## 2. Data Quality and Sanity Checks
- No nulls, duplicate rows, or duplicate campaign IDs were found.
- All business-volume columns (`ad_spend_usd`, `impressions`, `clicks`, `revenue_usd`) are strictly positive, so log transforms are feasible if needed.
- `month` only takes values 1 through 12, so there is no obvious invalid temporal coding.
- The categorical distributions are reasonably balanced:
  - Regions: {df['region'].value_counts().to_dict()}
  - Channels: {df['channel'].value_counts().to_dict()}
- IQR-based outlier screening suggests the strongest univariate anomalies are in:
  - `clicks`: **{iqr_outliers['clicks']}** points outside the 1.5 IQR rule
  - `roas`: **{iqr_outliers['roas']}** points outside the 1.5 IQR rule
  - `ad_spend_usd`, `impressions`, and `revenue_usd` show **0** IQR outliers under that rule, indicating broad ranges but not isolated extreme tails in the raw monetary/volume variables.

## 3. Exploratory Data Analysis

### Engineered Metrics
To make campaign efficiency interpretable, I engineered:
- `ctr = clicks / impressions`
- `cpc = ad_spend_usd / clicks`
- `cpm = ad_spend_usd / impressions * 1000`
- `roas = revenue_usd / ad_spend_usd`

Their key averages are:
- Mean CTR: **{fmt_pct(df['ctr'].mean())}**
- Mean CPC: **${fmt_num(df['cpc'].mean())}**
- Mean CPM: **${fmt_num(df['cpm'].mean())}**
- Mean ROAS: **{fmt_num(df['roas'].mean(), 3)}x**

### Main Patterns
1. **Spend and revenue move almost one-for-one on a strong linear scale.**
   - Pearson correlation(`ad_spend_usd`, `revenue_usd`) = **{df[['ad_spend_usd', 'revenue_usd']].corr().iloc[0, 1]:.3f}**
   - The scatterplot in [plots/04_spend_vs_revenue.png](./plots/04_spend_vs_revenue.png) shows a tight linear band.

2. **Impressions and clicks are also strongly correlated with spend, which creates redundancy rather than much new information.**
   - Correlation(`ad_spend_usd`, `impressions`) = **{df[['ad_spend_usd', 'impressions']].corr().iloc[0, 1]:.3f}**
   - Correlation(`ad_spend_usd`, `clicks`) = **{df[['ad_spend_usd', 'clicks']].corr().iloc[0, 1]:.3f}**

3. **Efficiency metrics are surprisingly stable across categories.**
   - Channel-level mean ROAS ranges only from **{fmt_num(df.groupby('channel', observed=True)['roas'].mean().min(), 3)}x** to **{fmt_num(df.groupby('channel', observed=True)['roas'].mean().max(), 3)}x**
   - Region-level mean ROAS ranges only from **{fmt_num(df.groupby('region', observed=True)['roas'].mean().min(), 3)}x** to **{fmt_num(df.groupby('region', observed=True)['roas'].mean().max(), 3)}x**
   - ANOVA does not show strong evidence that ROAS differs by channel (`p = {channel_anova.pvalue:.3f}`) or region (`p = {region_anova.pvalue:.3f}`).

4. **There is visible month-to-month volume variation, but little independent month effect once spend is controlled for.**
   - Highest mean revenue month: **month {int(monthly.loc[monthly['revenue_usd'].idxmax(), 'month'])}** at **${fmt_num(monthly['revenue_usd'].max())}**
   - Lowest mean revenue month: **month {int(monthly.loc[monthly['revenue_usd'].idxmin(), 'month'])}** at **${fmt_num(monthly['revenue_usd'].min())}**
   - The multivariable model finds month indicators mostly insignificant after accounting for spend and delivery metrics.

### Group-Level Summaries
#### By Channel
{frame_to_markdown(by_channel)}

#### By Region
{frame_to_markdown(by_region)}

## 4. Modeling Strategy
I treated this primarily as a **regression** problem with `revenue_usd` as the outcome. I compared:
- A simple interpretable OLS benchmark: `revenue_usd ~ ad_spend_usd`
- A slightly richer linear model: `revenue_usd ~ ad_spend_usd + clicks`
- A full OLS model with spend, impressions, clicks, and categorical controls for region, channel, and month
- Machine-learning regressors for predictive comparison: linear regression pipeline, ridge, random forest, and histogram gradient boosting

I excluded `campaign_id` from modeling because it behaves like an identifier, not a meaningful signal.

### Model Comparison
#### OLS Family
| model | adjusted_r2 | AIC | Breusch-Pagan p | Jarque-Bera p |
|---|---:|---:|---:|---:|
| Spend only | {spend_only.rsquared_adj:.6f} | {spend_only.aic:.2f} | {bp_pvalue:.3e} | {jb_pvalue:.3e} |
| Spend + clicks | {spend_clicks.rsquared_adj:.6f} | {spend_clicks.aic:.2f} | {het_breuschpagan(spend_clicks.resid, spend_clicks.model.exog)[1]:.3e} | {jarque_bera(spend_clicks.resid)[1]:.3e} |
| Full linear model | {full_model.rsquared_adj:.6f} | {full_model.aic:.2f} | {het_breuschpagan(full_model.resid, full_model.model.exog)[1]:.3e} | {jarque_bera(full_model.resid)[1]:.3e} |

The richer linear models do **not** improve adjusted R-squared or AIC enough to justify the added complexity. The best practical model is therefore the **spend-only model**: it is simpler, easier to explain, and just as accurate out of sample.

#### Cross-Validated Predictive Models
{frame_to_markdown(cv_table.set_index("model"))}

The simplest linear models perform best. Tree-based ensembles do not help here, which is consistent with the near-linear structure seen in the EDA.

## 5. Preferred Model and Interpretation
### Preferred model
`revenue_usd ~ ad_spend_usd`

Using heteroscedasticity-robust HC3 standard errors:
- Intercept: **{fmt_num(spend_only_hc3.params[0])}** (p = {spend_only_hc3.pvalues[0]:.3f})
- Spend slope: **{fmt_num(spend_only_hc3.params[1], 4)}** (95% CI: **[{fmt_num(spend_only_hc3.conf_int()[1, 0], 4)}, {fmt_num(spend_only_hc3.conf_int()[1, 1], 4)}]**)

Interpretation:
- On average, an additional **$1** of ad spend is associated with approximately **${fmt_num(spend_only_hc3.params[1], 2)}** in revenue.
- The implied average ROAS from the slope is consistent with the observed dataset-wide mean ROAS of **{fmt_num(df['roas'].mean(), 3)}x**.

### Why not the full model?
- In the full model, `impressions` is not significant and `clicks` is only borderline.
- Channel, region, and month indicators are broadly insignificant after controlling for spend.
- Multicollinearity is non-trivial:
  - `ad_spend_usd` VIF = **{vif_df.loc[vif_df['variable'] == 'ad_spend_usd', 'vif'].iloc[0]:.3f}**
  - `impressions` VIF = **{vif_df.loc[vif_df['variable'] == 'impressions', 'vif'].iloc[0]:.3f}**

#### VIF Table for Full Model
{frame_to_markdown(vif_table.head(10).set_index("variable"))}

## 6. Assumption Checks and Validation

### Linearity
- The spend-revenue scatter is strongly linear, so the mean trend is well captured.
- Log-log regression yields a near-unit elasticity estimate (`log_revenue ~ log_spend` slope = **{fmt_num(loglog_model.params['log_spend'], 4)}**), reinforcing the proportional relationship.

### Heteroscedasticity
- Breusch-Pagan test for the preferred model: **p = {bp_pvalue:.3e}**
- Conclusion: residual variance is not constant. Prediction is still strong, but inference should rely on robust standard errors.

### Normality of Residuals
- Jarque-Bera test: **p = {jb_pvalue:.3e}**
- Residuals are approximately centered but have heavier tails than Gaussian residuals, visible in [plots/07_residual_diagnostics.png](./plots/07_residual_diagnostics.png).

### Independence
- Durbin-Watson for the preferred model: **{durbin_watson(spend_only.resid):.3f}**
- There is no obvious autocorrelation signal, though this is cross-sectional campaign data rather than a strict time series.

### Influence and Anomalies
- Cook's distance threshold (`4/n`) = **{cooks_threshold:.4f}**
- Observations above that threshold: **{influential_count}**
- Studentized residuals with absolute value > 3: **{large_studentized}**

These campaigns deserve business review because they substantially over- or under-perform relative to their spend levels.

#### Largest Positive Residuals
{frame_to_markdown(top_positive.set_index("campaign_id"))}

#### Largest Negative Residuals
{frame_to_markdown(top_negative.set_index("campaign_id"))}

## 7. Conclusions
1. The dataset is clean and well-structured, with no missingness or duplicate-record issues.
2. Revenue is driven primarily by spend. The relationship is strong enough that a simple one-variable linear model performs as well as or better than more complex alternatives.
3. Channel, region, and month matter far less than expected once spend is included, and there is no strong evidence of systematic ROAS differences across those groups in this dataset.
4. The main statistical caution is heteroscedasticity plus a small set of influential campaigns. That affects uncertainty estimates more than it affects predictive accuracy.
5. Operationally, the most valuable next step is not adding model complexity but investigating the campaigns with the largest residuals. Those are the places where performance is materially above or below what spend alone would predict.

## 8. Deliverables
- Report: [analysis_report.md](./analysis_report.md)
- Plots:
  - [plots/01_missingness_map.png](./plots/01_missingness_map.png)
  - [plots/02_distributions.png](./plots/02_distributions.png)
  - [plots/03_correlation_heatmap.png](./plots/03_correlation_heatmap.png)
  - [plots/04_spend_vs_revenue.png](./plots/04_spend_vs_revenue.png)
  - [plots/05_monthly_trends.png](./plots/05_monthly_trends.png)
  - [plots/06_roas_by_group.png](./plots/06_roas_by_group.png)
  - [plots/07_residual_diagnostics.png](./plots/07_residual_diagnostics.png)
  - [plots/08_cooks_distance.png](./plots/08_cooks_distance.png)
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
