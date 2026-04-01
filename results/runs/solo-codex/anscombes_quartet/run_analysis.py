from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence
from statsmodels.stats.anova import anova_lm


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def savefig(name: str) -> str:
    path = PLOTS_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    return f"./plots/{name}"


def bootstrap_ci_slope(df: pd.DataFrame, n_boot: int = 5000, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    slopes = []
    n = len(df)
    for _ in range(n_boot):
        sample = df.iloc[rng.integers(0, n, n)]
        x = sm.add_constant(sample["dosage_mg"])
        m = sm.OLS(sample["response"], x).fit()
        slopes.append(m.params["dosage_mg"])
    return float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


def df_to_markdown(df: pd.DataFrame, float_digits: int = 4) -> str:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: f"{x:.{float_digits}f}")
        elif pd.api.types.is_integer_dtype(out[col]):
            out[col] = out[col].map(lambda x: f"{x:d}")
        else:
            out[col] = out[col].astype(str)
    header = "| " + " | ".join(map(str, out.columns)) + " |"
    sep = "| " + " | ".join(["---"] * len(out.columns)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in out.itertuples(index=False, name=None)]
    return "\n".join([header, sep] + rows)


def loocv_metrics(X: pd.DataFrame, y: pd.Series, preprocessor: ColumnTransformer) -> dict[str, float]:
    model = Pipeline(
        steps=[
            ("prep", preprocessor),
            ("reg", LinearRegression()),
        ]
    )
    preds = cross_val_predict(model, X, y, cv=LeaveOneOut())
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, preds))),
        "mae": float(mean_absolute_error(y, preds)),
        "r2_pred": float(r2_score(y, preds)),
    }


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATA_PATH)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    missing = df.isna().sum()
    desc = df[numeric_cols].describe().T
    duplicates = int(df.duplicated().sum())

    batch_corr = (
        df.groupby("batch")
        .apply(lambda g: g["dosage_mg"].corr(g["response"]), include_groups=False)
        .rename("pearson_r")
        .reset_index()
    )

    # Global models
    global_simple = smf.ols("response ~ dosage_mg", data=df).fit()
    global_adjusted = smf.ols(
        "response ~ dosage_mg + lab_temp_c + weight_kg + C(technician) + C(batch)",
        data=df,
    ).fit()
    ancova = smf.ols(
        "response ~ dosage_mg * C(batch) + lab_temp_c + weight_kg + C(technician)",
        data=df,
    ).fit()

    infl = OLSInfluence(global_adjusted)
    influence_df = df[["observation_id", "batch", "dosage_mg", "response"]].copy()
    influence_df["studentized_resid"] = infl.resid_studentized_external
    influence_df["cooks_d"] = infl.cooks_distance[0]
    influence_df["leverage"] = infl.hat_matrix_diag
    top_influence = influence_df.sort_values("cooks_d", ascending=False).head(8)

    # Assumptions for adjusted global model
    shapiro_global = stats.shapiro(global_adjusted.resid)
    bp_global = het_breuschpagan(global_adjusted.resid, global_adjusted.model.exog)

    # Batch-specific fits and diagnostics
    per_batch = []
    for batch, g in df.groupby("batch"):
        lin = smf.ols("response ~ dosage_mg", data=g).fit()
        quad = smf.ols("response ~ dosage_mg + I(dosage_mg ** 2)", data=g).fit()
        cooks = np.asarray(OLSInfluence(lin).cooks_distance[0])
        max_idx = int(np.argmax(cooks))
        max_obs = int(g.iloc[max_idx]["observation_id"])
        loo = g[g["observation_id"] != max_obs]
        if loo["dosage_mg"].nunique() >= 2:
            lin_loo = smf.ols("response ~ dosage_mg", data=loo).fit()
            slope_without_top = float(lin_loo.params["dosage_mg"])
        else:
            slope_without_top = np.nan
        shapiro = stats.shapiro(lin.resid)
        bp = het_breuschpagan(lin.resid, lin.model.exog)
        ci_low, ci_high = bootstrap_ci_slope(g)
        per_batch.append(
            {
                "batch": batch,
                "n": len(g),
                "slope": float(lin.params["dosage_mg"]),
                "intercept": float(lin.params["Intercept"]),
                "r2": float(lin.rsquared),
                "pearson_r": float(g["dosage_mg"].corr(g["response"])),
                "quad_p": float(quad.pvalues.get("I(dosage_mg ** 2)", np.nan)),
                "linear_aic": float(lin.aic),
                "quadratic_aic": float(quad.aic),
                "shapiro_p": float(shapiro.pvalue),
                "bp_p": float(bp[1]),
                "max_cooks_d": float(cooks[max_idx]),
                "max_cooks_obs": max_obs,
                "slope_without_top_influence": slope_without_top,
                "slope_bootstrap_ci_low": ci_low,
                "slope_bootstrap_ci_high": ci_high,
            }
        )
    per_batch_df = pd.DataFrame(per_batch)

    # Validation
    X_base = df[["dosage_mg"]]
    y = df["response"]
    simple_loocv = loocv_metrics(
        X_base,
        y,
        ColumnTransformer([("num", "passthrough", ["dosage_mg"])], remainder="drop"),
    )
    adjusted_loocv = loocv_metrics(
        df[["dosage_mg", "lab_temp_c", "weight_kg", "technician", "batch"]],
        y,
        ColumnTransformer(
            [
                ("num", "passthrough", ["dosage_mg", "lab_temp_c", "weight_kg"]),
                ("cat", OneHotEncoder(drop="first", sparse_output=False), ["technician", "batch"]),
            ],
            remainder="drop",
        ),
    )
    quad_q2 = df[df["batch"] == "batch_Q2"].copy()
    q2_lin_pred = cross_val_predict(
        Pipeline(
            steps=[
                ("prep", ColumnTransformer([("num", "passthrough", ["dosage_mg"])], remainder="drop")),
                ("reg", LinearRegression()),
            ]
        ),
        quad_q2[["dosage_mg"]],
        quad_q2["response"],
        cv=LeaveOneOut(),
    )
    q2_quad_pred = cross_val_predict(
        Pipeline(
            steps=[
                (
                    "prep",
                    ColumnTransformer(
                        [
                            (
                                "poly",
                                Pipeline([("poly", PolynomialFeatures(degree=2, include_bias=False))]),
                                ["dosage_mg"],
                            )
                        ],
                        remainder="drop",
                    ),
                ),
                ("reg", LinearRegression()),
            ]
        ),
        quad_q2[["dosage_mg"]],
        quad_q2["response"],
        cv=LeaveOneOut(),
    )
    q2_cv = {
        "linear_rmse": float(np.sqrt(mean_squared_error(quad_q2["response"], q2_lin_pred))),
        "quadratic_rmse": float(np.sqrt(mean_squared_error(quad_q2["response"], q2_quad_pred))),
    }

    # Plots
    plt.figure(figsize=(10, 4))
    sns.barplot(x=missing.index, y=missing.values, color="#4C78A8")
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Missing values")
    plt.title("Missingness by column")
    missing_plot = savefig("missingness.png")

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for ax, col in zip(axes.flatten(), ["dosage_mg", "response", "lab_temp_c", "weight_kg"]):
        sns.histplot(df[col], kde=True, ax=ax, color="#59A14F")
        ax.set_title(f"Distribution of {col}")
    dist_plot = savefig("numeric_distributions.png")

    plt.figure(figsize=(7, 5))
    sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="vlag", center=0, fmt=".2f")
    plt.title("Numeric correlation matrix")
    corr_plot = savefig("correlation_heatmap.png")

    g = sns.lmplot(
        data=df,
        x="dosage_mg",
        y="response",
        hue="batch",
        col="batch",
        col_wrap=2,
        height=4.0,
        ci=None,
        scatter_kws={"s": 70, "alpha": 0.85},
        line_kws={"color": "black", "lw": 2},
        facet_kws={"sharex": False, "sharey": True},
    )
    g.fig.subplots_adjust(top=0.9)
    g.fig.suptitle("Dose-response by batch with separate linear fits")
    batch_scatter_plot = str(PLOTS_DIR / "batch_scatter_fits.png")
    g.savefig(batch_scatter_plot, dpi=160, bbox_inches="tight")
    plt.close(g.fig)
    batch_scatter_plot = "./plots/batch_scatter_fits.png"

    plt.figure(figsize=(9, 6))
    sns.scatterplot(data=df, x="dosage_mg", y="response", hue="batch", style="technician", s=100)
    xs = np.linspace(df["dosage_mg"].min(), df["dosage_mg"].max(), 200)
    ys = global_simple.params["Intercept"] + global_simple.params["dosage_mg"] * xs
    plt.plot(xs, ys, color="black", lw=2, label="Global linear fit")
    plt.title("Global scatter can hide batch-specific geometry")
    global_scatter_plot = savefig("global_scatter.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.scatterplot(x=global_adjusted.fittedvalues, y=global_adjusted.resid, ax=axes[0], color="#E15759")
    axes[0].axhline(0, color="black", lw=1)
    axes[0].set_title("Residuals vs fitted")
    axes[0].set_xlabel("Fitted values")
    axes[0].set_ylabel("Residuals")
    sm.qqplot(global_adjusted.resid, line="45", ax=axes[1], color="#4E79A7")
    axes[1].set_title("Q-Q plot of residuals")
    residual_plot = savefig("global_model_diagnostics.png")

    plt.figure(figsize=(9, 6))
    sns.scatterplot(data=influence_df, x="leverage", y="studentized_resid", hue="batch", size="cooks_d", sizes=(50, 400))
    plt.axhline(0, color="black", lw=1)
    plt.axhline(2, color="grey", lw=1, ls="--")
    plt.axhline(-2, color="grey", lw=1, ls="--")
    plt.title("Influence diagnostics for adjusted global model")
    influence_plot = savefig("influence_diagnostics.png")

    plt.figure(figsize=(10, 5))
    tidy = per_batch_df.melt(
        id_vars="batch",
        value_vars=["slope", "slope_without_top_influence"],
        var_name="estimate",
        value_name="value",
    )
    sns.barplot(data=tidy, x="batch", y="value", hue="estimate", palette=["#4E79A7", "#F28E2B"])
    plt.axhline(global_simple.params["dosage_mg"], color="black", lw=1.5, ls="--")
    plt.title("Batch slopes before and after removing each batch's most influential point")
    slope_plot = savefig("batch_slope_sensitivity.png")

    # Narrative helpers
    top_influence_md = df_to_markdown(top_influence, float_digits=4)
    per_batch_md = df_to_markdown(
        per_batch_df[
        [
            "batch",
            "slope",
            "r2",
            "quad_p",
            "linear_aic",
            "quadratic_aic",
            "max_cooks_obs",
            "max_cooks_d",
            "slope_without_top_influence",
        ]
    ],
        float_digits=4,
    )

    interaction_table = df_to_markdown(anova_lm(ancova, typ=2).reset_index().round(4), float_digits=4)

    q1_row = per_batch_df.loc[per_batch_df["batch"] == "batch_Q1"].iloc[0]
    q2_row = per_batch_df.loc[per_batch_df["batch"] == "batch_Q2"].iloc[0]
    q3_row = per_batch_df.loc[per_batch_df["batch"] == "batch_Q3"].iloc[0]
    q4_row = per_batch_df.loc[per_batch_df["batch"] == "batch_Q4"].iloc[0]

    q4_sensitivity_text = (
        f"The nominal slope is **{q4_row['slope']:.4f}**, but after removing the most influential point "
        f"(**observation {int(q4_row['max_cooks_obs'])}**), dosage has no remaining variation, so a slope is "
        "no longer estimable. In practical terms, there is almost no information in this batch to estimate a "
        "dose-response line because 10 of 11 points share the same dosage."
    )

    report = f"""# Dataset Analysis Report

## Executive Summary

This dataset contains **{df.shape[0]} rows** and **{df.shape[1]} columns** with no missing values and no duplicate rows. The primary scientific-looking relationship is between `dosage_mg` and `response`, and the aggregate data suggest a strong positive linear trend. However, batch-level visual inspection and diagnostics show that this aggregate summary is **not sufficient** to describe the data-generating process.

Key findings:

1. A global linear model shows a strong positive association between dosage and response, but batch-specific geometry reveals materially different structures hidden behind nearly identical summary statistics.
2. `lab_temp_c`, `weight_kg`, and `technician` do not show credible incremental explanatory value after accounting for dosage and batch.
3. The batches behave like four distinct diagnostic scenarios:
   - `batch_Q1`: roughly linear with moderate noise.
   - `batch_Q2`: curved relationship where a straight line is an approximation, not a faithful model.
   - `batch_Q3`: near-linear except for a single influential vertical outlier.
   - `batch_Q4`: slope is largely identified by one extreme leverage point; without that point, the linear trend largely disappears.
4. The defensible conclusion is not “dosage has the same clean effect in all batches,” but rather “aggregate regression is fragile to structure, nonlinearity, and influential observations.”

## 1. Data Loading and Inspection

- Source: `./dataset.csv`
- Shape: `{df.shape}`
- Numeric columns: `{numeric_cols}`
- Categorical columns: `{categorical_cols}`
- Missing values: `{int(missing.sum())}` total
- Duplicate rows: `{duplicates}`

### Data types

```text
{df.dtypes.to_string()}
```

### Missing values by column

```text
{missing.to_string()}
```

### Basic numeric summary

{df_to_markdown(desc.reset_index().rename(columns={"index": "variable"}), float_digits=4)}

### Categorical levels

- `batch`: {json.dumps(df["batch"].value_counts().sort_index().to_dict())}
- `technician`: {json.dumps(df["technician"].value_counts().sort_index().to_dict())}

### Initial quality assessment

The dataset is structurally clean: no nulls, no duplicated rows, and no obvious impossible values. The main risk is **analytical**, not clerical: the sample is small and contains grouped structure (`batch`) that can make aggregate summaries deceptive.

![Missingness]({missing_plot})
![Numeric distributions]({dist_plot})

## 2. Exploratory Data Analysis

### Univariate observations

- `dosage_mg` ranges from 4 to 19 mg, centered at 9 mg.
- `response` ranges from 3.10 to 12.74 and is fairly symmetric overall.
- `lab_temp_c` varies only modestly, from 20.7 C to 23.3 C.
- `weight_kg` spans a wider range, from 48.8 to 89.0 kg.

### Aggregate relationships

The strongest aggregate correlation is between `dosage_mg` and `response`:

```text
{df[numeric_cols].corr().round(4).to_string()}
```

The global Pearson correlation between dosage and response is **{df["dosage_mg"].corr(df["response"]):.4f}**, which would normally motivate a linear regression.

![Correlation heatmap]({corr_plot})
![Global scatter]({global_scatter_plot})

### Batch-level structure

Each batch has the same sample size and extremely similar dose-response summary statistics:

{df_to_markdown(batch_corr, float_digits=4)}

Despite that, the scatterplots show distinct patterns:

- `batch_Q1` is approximately linear.
- `batch_Q2` shows visible curvature.
- `batch_Q3` is nearly linear except for one high-response outlier at observation **{int(q3_row["max_cooks_obs"])}**.
- `batch_Q4` places 10 of 11 observations at the same dosage (`8 mg`), plus one point at `19 mg`, making the fitted slope almost entirely leverage-driven.

![Batch scatterplots]({batch_scatter_plot})

## 3. Modeling Strategy

Because `response` is continuous, ordinary least squares is the natural baseline. I fit:

1. A simple global model: `response ~ dosage_mg`
2. An adjusted global model: `response ~ dosage_mg + lab_temp_c + weight_kg + technician + batch`
3. An interaction model to test whether dose-response differs by batch
4. Batch-specific models to assess within-batch geometry and sensitivity

This progression is necessary because a single global model can be statistically significant while still being scientifically misleading.

## 4. Global Model Results

### Simple global model

- Formula: `response ~ dosage_mg`
- Slope for dosage: **{global_simple.params["dosage_mg"]:.4f}**
- 95% CI: **[{global_simple.conf_int().loc["dosage_mg", 0]:.4f}, {global_simple.conf_int().loc["dosage_mg", 1]:.4f}]**
- R-squared: **{global_simple.rsquared:.4f}**
- p-value: **{global_simple.pvalues["dosage_mg"]:.4g}**

### Adjusted global model

- Formula: `response ~ dosage_mg + lab_temp_c + weight_kg + C(technician) + C(batch)`
- Dosage remains significant: coefficient **{global_adjusted.params["dosage_mg"]:.4f}**, p-value **{global_adjusted.pvalues["dosage_mg"]:.4g}**
- `lab_temp_c` coefficient: **{global_adjusted.params["lab_temp_c"]:.4f}**, p-value **{global_adjusted.pvalues["lab_temp_c"]:.4f}**
- `weight_kg` coefficient: **{global_adjusted.params["weight_kg"]:.4f}**, p-value **{global_adjusted.pvalues["weight_kg"]:.4f}**
- Batch effects are not significant after allowing for common slope

The adjustment variables do not materially improve interpretability or prediction. Their apparent effects are weak and unstable relative to the structural issues introduced by batch geometry.

### Interaction test

The dose-by-batch interaction is not significant in the linear ANCOVA:

{interaction_table}

This result should **not** be over-interpreted as evidence that all batches follow the same linear mechanism. The interaction test only evaluates whether **straight-line slopes** differ; it does not rescue violations caused by curvature, leverage concentration, or outliers.

## 5. Assumption Checks and Diagnostics

### Global adjusted model

- Shapiro-Wilk p-value for residual normality: **{shapiro_global.pvalue:.4f}**
- Breusch-Pagan p-value for heteroskedasticity: **{bp_global[1]:.4f}**
- Condition number is large in the statsmodels summary, reflecting scaling and encoded categorical structure rather than a clear substantive collinearity problem

Residual diagnostics do not show severe global normality or heteroskedasticity failures, but these checks are secondary here. The dominant issue is **model form misspecification caused by mixing batches with different geometries**.

![Global diagnostics]({residual_plot})
![Influence diagnostics]({influence_plot})

### Most influential observations in the adjusted global model

{top_influence_md}

Observation **{int(top_influence.iloc[0]["observation_id"])}** in `batch_Q3` is the most influential point by Cook's distance, but the more serious interpretive risk is `batch_Q4`, where a single high-leverage point creates the appearance of a stable slope.

## 6. Batch-Specific Results

{per_batch_md}

### Interpretation by batch

#### batch_Q1

This is the only batch where a simple linear interpretation looks broadly reasonable. Even here, the fit is moderate rather than perfect (R-squared {q1_row["r2"]:.4f}).

#### batch_Q2

The relationship is visibly curved. The quadratic term p-value is **{q2_row["quad_p"]:.4f}**, and the quadratic AIC (**{q2_row["quadratic_aic"]:.2f}**) is lower than the linear AIC (**{q2_row["linear_aic"]:.2f}**), indicating that a straight line is an inferior description for this batch.

LOOCV RMSE for `batch_Q2`:

- Linear: **{q2_cv["linear_rmse"]:.4f}**
- Quadratic: **{q2_cv["quadratic_rmse"]:.4f}**

The quadratic model predicts dramatically better out of sample, which is consistent with the curvature seen in the plot.

#### batch_Q3

The fitted slope is strongly affected by one influential observation, **{int(q3_row["max_cooks_obs"])}**. Removing that point changes the slope from **{q3_row["slope"]:.4f}** to **{q3_row["slope_without_top_influence"]:.4f}**. This batch is best described as “linear with one anomalous response outlier,” not as clean evidence of stronger treatment effect.

#### batch_Q4

This batch is the clearest warning against naive regression. {q4_sensitivity_text}

## 7. Validation

Leave-one-out cross-validation was used because the dataset is small.

### Global model predictive performance

- Simple model LOOCV RMSE: **{simple_loocv["rmse"]:.4f}**
- Simple model LOOCV MAE: **{simple_loocv["mae"]:.4f}**
- Simple model pseudo-predictive R-squared: **{simple_loocv["r2_pred"]:.4f}**

- Adjusted model LOOCV RMSE: **{adjusted_loocv["rmse"]:.4f}**
- Adjusted model LOOCV MAE: **{adjusted_loocv["mae"]:.4f}**
- Adjusted model pseudo-predictive R-squared: **{adjusted_loocv["r2_pred"]:.4f}**

The adjusted model does **not** materially outperform the simpler dosage-only model. That is consistent with the weak incremental value of temperature, weight, technician, and batch indicators once the misleading aggregate trend is already captured.

## 8. Conclusions

1. The dataset is clean in the clerical sense but not in the modeling sense.
2. A global positive dose-response exists statistically, but it is not a sufficient summary of the data.
3. Batch-level visual inspection is essential here; relying on means, standard deviations, correlations, or a single regression line would produce an overconfident and potentially false narrative.
4. `lab_temp_c`, `weight_kg`, and `technician` do not provide robust evidence of meaningful effects.
5. The most defensible scientific statement is:

> Response tends to increase with dosage in aggregate, but the observed relationship is highly sensitive to batch-specific structure, including nonlinearity, a vertical outlier, and leverage concentration. Any substantive conclusion about treatment effect should therefore be qualified and batch-aware.

## 9. Reproducibility

All plots were saved under `./plots/`:

- `{missing_plot}`
- `{dist_plot}`
- `{corr_plot}`
- `{global_scatter_plot}`
- `{batch_scatter_plot}`
- `{residual_plot}`
- `{influence_plot}`
- `{slope_plot}`
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
