from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import shapiro
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import OLSInfluence
from statsmodels.stats.stattools import durbin_watson, jarque_bera


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "dataset.csv"
REPORT_PATH = ROOT / "analysis_report.md"
PLOTS_DIR = ROOT / "plots"


def code_block(text: str) -> str:
    return f"```\n{text.rstrip()}\n```\n"


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def metric_summary(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "R2": r2_score(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAE": mean_absolute_error(y_true, y_pred),
    }


def main() -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    df = pd.read_csv(DATASET_PATH)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    feature_cols = [
        "engine_rpm",
        "ambient_temp_c",
        "humidity_pct",
        "octane_rating",
        "vehicle_age_years",
    ]
    target_col = "fuel_consumption_lph"

    null_counts = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ids = int(df["test_id"].duplicated().sum())
    describe = df.describe().round(3)
    skewness = df[feature_cols + [target_col]].skew().round(3)
    corr = df[feature_cols + [target_col]].corr().round(3)

    q1 = df[numeric_cols].quantile(0.25)
    q3 = df[numeric_cols].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_counts = (
        ((df[numeric_cols] < lower) | (df[numeric_cols] > upper)).sum().sort_values(ascending=False)
    )

    shapiro_rows = []
    for col in feature_cols + [target_col]:
        sample = df[col].sample(min(len(df), 500), random_state=42)
        stat, pvalue = shapiro(sample)
        shapiro_rows.append({"variable": col, "W": round(stat, 4), "p_value": pvalue})
    shapiro_df = pd.DataFrame(shapiro_rows)

    df_centered = df.copy()
    df_centered["engine_rpm_kc"] = (df_centered["engine_rpm"] - df_centered["engine_rpm"].mean()) / 1000.0

    linear_model = smf.ols(
        "fuel_consumption_lph ~ engine_rpm + ambient_temp_c + humidity_pct + octane_rating + vehicle_age_years",
        data=df,
    ).fit()
    quadratic_model = smf.ols(
        "fuel_consumption_lph ~ engine_rpm_kc + I(engine_rpm_kc**2)",
        data=df_centered,
    ).fit()
    quadratic_controls_model = smf.ols(
        "fuel_consumption_lph ~ engine_rpm_kc + I(engine_rpm_kc**2) + ambient_temp_c + humidity_pct + octane_rating + vehicle_age_years",
        data=df_centered,
    ).fit()

    X = df[feature_cols]
    y = df[target_col]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    candidate_models = {
        "Linear regression (all features)": LinearRegression(),
        "Quadratic RPM regression": Pipeline(
            [("poly", PolynomialFeatures(degree=2, include_bias=False)), ("lr", LinearRegression())]
        ),
        "Random forest benchmark": RandomForestRegressor(
            n_estimators=400, min_samples_leaf=3, random_state=42
        ),
    }

    model_rows = []
    cv = KFold(n_splits=10, shuffle=True, random_state=42)
    for name, model in candidate_models.items():
        if name == "Quadratic RPM regression":
            X_train_fit = X_train[["engine_rpm"]]
            X_test_fit = X_test[["engine_rpm"]]
            X_full_fit = X[["engine_rpm"]]
        else:
            X_train_fit = X_train
            X_test_fit = X_test
            X_full_fit = X

        model.fit(X_train_fit, y_train)
        preds = model.predict(X_test_fit)
        metrics = metric_summary(y_test, preds)
        cv_r2 = cross_val_score(model, X_full_fit, y, cv=cv, scoring="r2")
        cv_rmse = -cross_val_score(
            model,
            X_full_fit,
            y,
            cv=cv,
            scoring="neg_root_mean_squared_error",
        )
        model_rows.append(
            {
                "model": name,
                "test_r2": round(metrics["R2"], 4),
                "test_rmse": round(metrics["RMSE"], 4),
                "test_mae": round(metrics["MAE"], 4),
                "cv_r2_mean": round(cv_r2.mean(), 4),
                "cv_r2_sd": round(cv_r2.std(), 4),
                "cv_rmse_mean": round(cv_rmse.mean(), 4),
                "cv_rmse_sd": round(cv_rmse.std(), 4),
            }
        )
    model_df = pd.DataFrame(model_rows).sort_values("cv_rmse_mean")

    final_pred = quadratic_model.predict(df_centered)
    final_metrics = metric_summary(y, final_pred)

    bp_stat, bp_pvalue, _, _ = het_breuschpagan(quadratic_model.resid, quadratic_model.model.exog)
    jb_stat, jb_pvalue, skew, kurt = jarque_bera(quadratic_model.resid)
    dw = durbin_watson(quadratic_model.resid)
    influence = OLSInfluence(quadratic_model)
    cooks_d = influence.cooks_distance[0]
    leverage = influence.hat_matrix_diag

    linear_bp = het_breuschpagan(linear_model.resid, linear_model.model.exog)
    linear_reset_test = linear_reset(linear_model, power=2, use_f=True)
    linear_jb = jarque_bera(linear_model.resid)

    final_coef = pd.DataFrame(
        {
            "coef": quadratic_model.params.round(6),
            "std_err": quadratic_model.bse.round(6),
            "p_value": quadratic_model.pvalues,
            "ci_low": quadratic_model.conf_int()[0].round(6),
            "ci_high": quadratic_model.conf_int()[1].round(6),
        }
    )

    coef_full = pd.DataFrame(
        {
            "coef": quadratic_controls_model.params.round(6),
            "p_value": quadratic_controls_model.pvalues.round(6),
        }
    )

    plt.figure(figsize=(14, 10))
    df[feature_cols + [target_col]].hist(bins=24, figsize=(14, 10), edgecolor="black")
    plt.suptitle("Distribution of Predictors and Target", y=1.02)
    savefig(PLOTS_DIR / "distributions.png")

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f")
    plt.title("Correlation Heatmap")
    savefig(PLOTS_DIR / "correlation_heatmap.png")

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()
    for ax, col in zip(axes, feature_cols):
        sns.scatterplot(data=df, x=col, y=target_col, alpha=0.7, s=40, ax=ax)
        if col == "octane_rating":
            ax.set_xticks(sorted(df[col].unique()))
        else:
            sns.regplot(
                data=df,
                x=col,
                y=target_col,
                scatter=False,
                ci=None,
                lowess=True,
                line_kws={"color": "crimson", "linewidth": 2},
                ax=ax,
            )
        ax.set_title(f"{target_col} vs {col}")
    axes[-1].axis("off")
    savefig(PLOTS_DIR / "predictor_relationships.png")

    rpm_grid = np.linspace(df["engine_rpm"].min(), df["engine_rpm"].max(), 300)
    rpm_centered = rpm_grid - df["engine_rpm"].mean()
    quad_curve = (
        quadratic_model.params["Intercept"]
        + quadratic_model.params["engine_rpm_kc"] * (rpm_centered / 1000.0)
        + quadratic_model.params["I(engine_rpm_kc ** 2)"] * (rpm_centered / 1000.0) ** 2
    )
    linear_curve = linear_model.params["Intercept"] + linear_model.params["engine_rpm"] * rpm_grid

    plt.figure(figsize=(10, 7))
    sns.scatterplot(data=df, x="engine_rpm", y=target_col, alpha=0.55, s=40)
    plt.plot(rpm_grid, linear_curve, color="gray", linewidth=2, label="Linear fit")
    plt.plot(rpm_grid, quad_curve, color="crimson", linewidth=3, label="Quadratic RPM fit")
    plt.title("Fuel Consumption vs Engine RPM")
    plt.legend()
    savefig(PLOTS_DIR / "rpm_quadratic_fit.png")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.scatterplot(x=quadratic_model.fittedvalues, y=quadratic_model.resid, alpha=0.7, s=40, ax=axes[0])
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Residuals vs Fitted")
    axes[0].set_xlabel("Fitted values")
    axes[0].set_ylabel("Residuals")
    sm.qqplot(quadratic_model.resid, line="45", fit=True, ax=axes[1])
    axes[1].set_title("Residual Q-Q Plot")
    savefig(PLOTS_DIR / "final_model_diagnostics.png")

    plt.figure(figsize=(8, 7))
    sns.scatterplot(x=y, y=final_pred, alpha=0.7, s=40)
    lims = [min(y.min(), final_pred.min()), max(y.max(), final_pred.max())]
    plt.plot(lims, lims, linestyle="--", color="black", linewidth=1.5)
    plt.xlabel("Observed fuel consumption (lph)")
    plt.ylabel("Predicted fuel consumption (lph)")
    plt.title("Observed vs Predicted: Final Model")
    savefig(PLOTS_DIR / "observed_vs_predicted.png")

    plt.figure(figsize=(9, 6))
    sns.boxplot(data=df, x="octane_rating", y=target_col)
    plt.title("Fuel Consumption by Octane Rating")
    savefig(PLOTS_DIR / "fuel_by_octane.png")

    top_influential = (
        pd.DataFrame(
            {
                "test_id": df["test_id"],
                "engine_rpm": df["engine_rpm"],
                target_col: df[target_col],
                "fitted": quadratic_model.fittedvalues.round(3),
                "residual": quadratic_model.resid.round(3),
                "cooks_d": cooks_d.round(5),
                "leverage": leverage.round(5),
            }
        )
        .sort_values("cooks_d", ascending=False)
        .head(10)
    )

    findings = [
        f"The dataset contains {df.shape[0]} rows and {df.shape[1]} columns with no missing values, no duplicate rows, and no duplicated `test_id` values.",
        "The response variable is strongly associated with `engine_rpm` (Pearson r = "
        f"{corr.loc['engine_rpm', target_col]:.3f}), while the other predictors have near-zero marginal correlation with fuel consumption.",
        "A naive linear model is mis-specified: Ramsey RESET rejects linear functional form "
        f"(F = {float(linear_reset_test.fvalue):.1f}, p = {float(linear_reset_test.pvalue):.2e}), and its residuals fail normality.",
        "Adding only a quadratic term in centered RPM materially improves fit and remains parsimonious: "
        f"R^2 = {quadratic_model.rsquared:.4f}, RMSE = {final_metrics['RMSE']:.3f}, "
        f"10-fold CV RMSE = {model_df.loc[model_df['model'] == 'Quadratic RPM regression', 'cv_rmse_mean'].iloc[0]:.3f}.",
        "The quadratic RPM model satisfies the main regression checks more cleanly: "
        f"Breusch-Pagan p = {bp_pvalue:.3f}, Jarque-Bera p = {jb_pvalue:.3f}, Durbin-Watson = {dw:.3f}.",
        "Extending the quadratic model with temperature, humidity, octane, and vehicle age does not add meaningful explanatory power; their coefficients remain statistically weak after controlling for RPM curvature.",
        "A random forest benchmark performs similarly to the quadratic RPM model out of sample, suggesting the remaining signal is limited and mostly captured by simple curvature rather than complex interactions.",
        "IQR-based univariate outliers appear only in ambient temperature (6 points) and humidity (1 point); they do not translate into highly influential observations in the final model.",
    ]

    report = f"""# Dataset Analysis Report

## Scope
This report analyzes `dataset.csv` as a supervised tabular problem, with `fuel_consumption_lph` treated as the outcome of interest. The workflow covered data inspection, exploratory analysis, anomaly checks, model building, diagnostic testing, and validation.

## Data Inspection
- Shape: `{df.shape[0]} rows x {df.shape[1]} columns`
- Numeric columns: `{", ".join(numeric_cols)}`
- Missing values: `{int(null_counts.sum())}`
- Duplicate rows: `{duplicate_rows}`
- Duplicate `test_id` values: `{duplicate_ids}`

### Dtypes
{code_block(df.dtypes.to_string())}

### Basic Statistics
{code_block(describe.to_string())}

### Missing Values by Column
{code_block(null_counts.to_string())}

### Distribution Shape
Skewness values:
{code_block(skewness.to_string())}

Shapiro-Wilk tests were run on random samples of up to 500 observations per variable. These tests reject normality for several variables, but that is not a modeling requirement for predictors; regression assumptions concern the residuals.
{code_block(shapiro_df.to_string(index=False))}

### Outlier Screening
IQR-rule outlier counts:
{code_block(outlier_counts.to_string())}

Interpretation:
- No obvious data quality failures were detected.
- `ambient_temp_c` contains a small number of tail observations, and `humidity_pct` contains one IQR outlier.
- `fuel_consumption_lph` shows no IQR outliers despite a right-skewed distribution.

## Exploratory Data Analysis
Saved plots:
- `plots/distributions.png`
- `plots/correlation_heatmap.png`
- `plots/predictor_relationships.png`
- `plots/rpm_quadratic_fit.png`
- `plots/final_model_diagnostics.png`
- `plots/observed_vs_predicted.png`
- `plots/fuel_by_octane.png`

### Correlation Matrix
{code_block(corr.to_string())}

### EDA Findings
"""
    for finding in findings:
        report += f"- {finding}\n"

    report += f"""

## Modeling Strategy
I treated this as a regression problem and compared three model classes:
1. Linear regression using all measured predictors.
2. A parsimonious quadratic regression using only engine RPM and its squared term.
3. A random forest benchmark to test whether materially nonlinear structure remained after the quadratic specification.

The quadratic model used centered RPM:

{code_block("fuel_consumption_lph ~ engine_rpm_kc + I(engine_rpm_kc**2)  # centered RPM in thousands")}

Centering improves numerical stability and makes the intercept interpretable as expected fuel consumption at mean RPM.

### Model Comparison
{code_block(model_df.to_string(index=False))}

### In-Sample OLS Summaries
Baseline linear model:
{code_block(linear_model.summary().as_text())}

Final quadratic RPM model:
{code_block(quadratic_model.summary().as_text())}

Quadratic RPM model with all additional controls:
{code_block(coef_full.to_string())}

## Assumption Checks and Validation
### Baseline Linear Model Diagnostics
- Breusch-Pagan test: statistic = {linear_bp[0]:.3f}, p = {linear_bp[1]:.3f}
- Jarque-Bera test: statistic = {linear_jb[0]:.3f}, p = {linear_jb[1]:.3e}
- Ramsey RESET test: F = {float(linear_reset_test.fvalue):.3f}, p = {float(linear_reset_test.pvalue):.3e}

Interpretation:
- Homoskedasticity is not the main issue.
- Functional form is the issue: the RESET test strongly rejects the linear specification.
- Residual normality is also poor under the purely linear model.

### Final Quadratic RPM Model Diagnostics
- In-sample R^2 = {quadratic_model.rsquared:.4f}
- In-sample RMSE = {final_metrics['RMSE']:.4f}
- Breusch-Pagan test: statistic = {bp_stat:.3f}, p = {bp_pvalue:.3f}
- Jarque-Bera test: statistic = {jb_stat:.3f}, p = {jb_pvalue:.3f}
- Residual skew = {skew:.4f}
- Residual kurtosis = {kurt:.4f}
- Durbin-Watson = {dw:.3f}
- Maximum Cook's distance = {cooks_d.max():.5f}
- Observations with Cook's distance > 4/n: {int((cooks_d > 4 / len(df)).sum())}

Interpretation:
- Residual variance is consistent with homoskedasticity at conventional thresholds.
- Residual normality is acceptable after adding the quadratic term.
- Independence looks reasonable in the observed row order, though this is still a cross-sectional dataset rather than a true time series.
- Some observations are moderately influential by the 4/n rule, but Cook's distances remain small in absolute terms.

### Final Model Coefficients
{code_block(final_coef.to_string())}

### Most Influential Observations
{code_block(top_influential.to_string(index=False))}

## Conclusions
- `engine_rpm` is the dominant driver of fuel consumption in this dataset.
- The relationship is clearly nonlinear and convex; fuel consumption rises faster at higher RPM.
- Once RPM curvature is modeled, ambient temperature, humidity, octane rating, and vehicle age add little incremental predictive value.
- A simple quadratic RPM model is both accurate and easier to justify than a black-box alternative here.
- The final model passes the main residual diagnostics well enough to support inference and prediction on this dataset.

## Recommended Next Steps
- If this dataset is operational, collect additional covariates tied to engine load or driving conditions; the current non-RPM variables appear weak.
- If the downstream use case requires uncertainty quantification, keep the quadratic OLS model because it is interpretable and diagnostically defensible.
- If the use case is pure prediction and future data may drift, monitor the RPM range closely; extrapolating the quadratic fit beyond the observed `826` to `5999` RPM range would be risky.
"""

    REPORT_PATH.write_text(report)


if __name__ == "__main__":
    main()
