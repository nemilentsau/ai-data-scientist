from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
PLOTS = ROOT / "plots"
PLOTS.mkdir(exist_ok=True)


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    sns.set_theme(style="whitegrid", palette="deep")

    df = pd.read_csv(ROOT / "dataset.csv", parse_dates=["timestamp"]).sort_values("timestamp")
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["low_quality"] = (df["defect_rate"] < 0.7).astype(int)
    df["pressure_decile"] = pd.qcut(df["pressure_bar"], 10, duplicates="drop")

    # Core summary metrics
    slope, intercept, r_time, p_time, _ = stats.linregress(np.arange(len(df)), df["defect_rate"])
    daily = df.groupby("date", as_index=False)["defect_rate"].mean()
    pressure_spearman = stats.spearmanr(df["pressure_bar"], df["defect_rate"])

    vals = [g["defect_rate"].values for _, g in df.groupby("operator")]
    kruskal_stat, kruskal_p = stats.kruskal(*vals)

    y_cls = df["low_quality"]
    X_model = df[
        ["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm", "operator", "hour", "dayofweek"]
    ]
    y_reg = df["defect_rate"]
    numeric = ["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm", "hour", "dayofweek"]
    categorical = ["operator"]

    pre = ColumnTransformer(
        [
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), numeric),
            (
                "cat",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="most_frequent")),
                        ("oh", OneHotEncoder(drop="first")),
                    ]
                ),
                categorical,
            ),
        ]
    )

    cv_reg = KFold(n_splits=5, shuffle=True, random_state=0)
    cv_cls = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

    ridge = Pipeline([("pre", pre), ("model", Ridge(alpha=1.0))])
    rf_reg = Pipeline(
        [("pre", pre), ("model", RandomForestRegressor(n_estimators=400, min_samples_leaf=10, random_state=0))]
    )
    logit = Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=2000))])
    rf_cls = Pipeline(
        [("pre", pre), ("model", RandomForestClassifier(n_estimators=400, min_samples_leaf=10, random_state=0))]
    )

    ridge_r2 = cross_val_score(ridge, X_model, y_reg, cv=cv_reg, scoring="r2")
    rf_r2 = cross_val_score(rf_reg, X_model, y_reg, cv=cv_reg, scoring="r2")
    logit_auc = cross_val_score(logit, X_model, y_cls, cv=cv_cls, scoring="roc_auc")
    rf_auc = cross_val_score(rf_cls, X_model, y_cls, cv=cv_cls, scoring="roc_auc")

    X_ols = df[["temperature_c", "pressure_bar", "vibration_mm_s", "speed_rpm"]].copy()
    X_ols = pd.concat([X_ols, pd.get_dummies(df["operator"], drop_first=True, dtype=float)], axis=1)
    X_ols = sm.add_constant(X_ols)
    ols = sm.OLS(df["defect_rate"], X_ols).fit()

    X_logit = X_ols.copy()
    X_logit["const"] = 1.0
    logit_threshold = sm.Logit(y_cls, X_logit).fit(disp=False)

    # Plot 1: distribution
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.histplot(df["defect_rate"], bins=30, kde=False, ax=axes[0], color="#4C72B0")
    axes[0].set_title("Defect Rate Distribution")
    axes[0].set_xlabel("defect_rate")
    axes[0].set_ylabel("Count")
    axes[0].axvline(df["defect_rate"].median(), color="#DD8452", linestyle="--", label="Median")
    axes[0].legend()

    sorted_defect = np.sort(df["defect_rate"])
    ecdf = np.arange(1, len(sorted_defect) + 1) / len(sorted_defect)
    axes[1].step(sorted_defect, ecdf, where="post", color="#55A868")
    axes[1].set_title("Empirical CDF of Defect Rate")
    axes[1].set_xlabel("defect_rate")
    axes[1].set_ylabel("Share of observations")
    axes[1].axvline(1.0, color="#C44E52", linestyle=":", label=f"At 1.0: {(df['defect_rate'] == 1).mean():.1%}")
    axes[1].legend()
    savefig(PLOTS / "defect_rate_distribution.png")

    # Plot 2: time series
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["timestamp"], df["defect_rate"], alpha=0.2, linewidth=0.9, color="#4C72B0", label="Half-hourly")
    ax.plot(
        df["timestamp"],
        df["defect_rate"].rolling(48, min_periods=1).mean(),
        linewidth=2.3,
        color="#C44E52",
        label="24-hour rolling mean",
    )
    ax.set_title("Defect Rate Over Time")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("defect_rate")
    ax.legend()
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
    savefig(PLOTS / "defect_rate_over_time.png")

    # Plot 3: pressure relationship
    pressure_deciles = (
        df.groupby("pressure_decile", observed=False)
        .agg(pressure_mid=("pressure_bar", "median"), defect_mean=("defect_rate", "mean"), low_quality_rate=("low_quality", "mean"))
        .reset_index(drop=True)
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.regplot(
        data=df.sample(n=min(600, len(df)), random_state=0),
        x="pressure_bar",
        y="defect_rate",
        lowess=True,
        scatter_kws={"alpha": 0.25, "s": 25},
        line_kws={"color": "#C44E52", "linewidth": 2},
        ax=axes[0],
    )
    axes[0].set_title("Pressure vs. Defect Rate")
    axes[0].set_xlabel("pressure_bar")
    axes[0].set_ylabel("defect_rate")

    axes[1].plot(pressure_deciles["pressure_mid"], pressure_deciles["low_quality_rate"], marker="o", color="#8172B2")
    axes[1].set_title("Low-quality Event Rate by Pressure Decile")
    axes[1].set_xlabel("Median pressure within decile")
    axes[1].set_ylabel("Share with defect_rate < 0.7")
    savefig(PLOTS / "pressure_vs_quality.png")

    # Plot 4: operator comparison
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.boxplot(data=df, x="operator", y="defect_rate", ax=axes[0], showfliers=False)
    axes[0].set_title("Defect Rate by Operator")
    axes[0].set_xlabel("Operator")
    axes[0].set_ylabel("defect_rate")

    sns.pointplot(
        data=df.groupby("operator", as_index=False)["defect_rate"].mean(),
        x="operator",
        y="defect_rate",
        ax=axes[1],
        color="#55A868",
        markers="o",
        linestyles="",
        errorbar=None,
    )
    axes[1].set_ylim(df["defect_rate"].mean() - 0.03, df["defect_rate"].mean() + 0.03)
    axes[1].set_title("Mean Defect Rate by Operator")
    axes[1].set_xlabel("Operator")
    axes[1].set_ylabel("Mean defect_rate")
    savefig(PLOTS / "operator_comparison.png")

    # Plot 5: cross-validated predictive performance
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), sharey=False)
    reg_perf = pd.DataFrame(
        {"model": ["Ridge", "Random forest"], "mean": [ridge_r2.mean(), rf_r2.mean()], "std": [ridge_r2.std(), rf_r2.std()]}
    )
    cls_perf = pd.DataFrame(
        {
            "model": ["Logistic", "Random forest"],
            "mean": [logit_auc.mean(), rf_auc.mean()],
            "std": [logit_auc.std(), rf_auc.std()],
        }
    )
    axes[0].bar(reg_perf["model"], reg_perf["mean"], color=["#4C72B0", "#4C72B0"])
    axes[0].errorbar(reg_perf["model"], reg_perf["mean"], yerr=reg_perf["std"], fmt="none", color="black", capsize=4)
    axes[0].axhline(0, color="black", linewidth=1, linestyle="--")
    axes[0].set_title("Regression Performance")
    axes[0].set_ylabel("Cross-validated $R^2$")
    axes[0].set_xlabel("Model")

    axes[1].bar(cls_perf["model"], cls_perf["mean"], color=["#DD8452", "#DD8452"])
    axes[1].errorbar(cls_perf["model"], cls_perf["mean"], yerr=cls_perf["std"], fmt="none", color="black", capsize=4)
    axes[1].axhline(0.5, color="gray", linewidth=1, linestyle=":")
    axes[1].set_title("Low-quality Event Classification")
    axes[1].set_ylabel("Cross-validated ROC AUC")
    axes[1].set_xlabel("Model")
    fig.suptitle("Cross-validated Predictive Performance")
    savefig(PLOTS / "model_performance.png")

    summary = {
        "n_rows": len(df),
        "n_cols": df.shape[1],
        "start": str(df["timestamp"].min()),
        "end": str(df["timestamp"].max()),
        "share_perfect": float((df["defect_rate"] == 1).mean()),
        "share_low_quality": float(df["low_quality"].mean()),
        "mean_defect": float(df["defect_rate"].mean()),
        "median_defect": float(df["defect_rate"].median()),
        "time_slope_per_day": float(slope * 48),
        "time_trend_p": float(p_time),
        "daily_min": float(daily["defect_rate"].min()),
        "daily_max": float(daily["defect_rate"].max()),
        "pressure_spearman_rho": float(pressure_spearman.statistic),
        "pressure_spearman_p": float(pressure_spearman.pvalue),
        "pressure_ols_coef": float(ols.params["pressure_bar"]),
        "pressure_ols_p": float(ols.pvalues["pressure_bar"]),
        "pressure_logit_or": float(np.exp(logit_threshold.params["pressure_bar"])),
        "pressure_logit_p": float(logit_threshold.pvalues["pressure_bar"]),
        "kruskal_stat": float(kruskal_stat),
        "kruskal_p": float(kruskal_p),
        "operator_means": df.groupby("operator")["defect_rate"].mean().round(6).to_dict(),
        "ridge_r2_mean": float(ridge_r2.mean()),
        "rf_r2_mean": float(rf_r2.mean()),
        "logit_auc_mean": float(logit_auc.mean()),
        "rf_auc_mean": float(rf_auc.mean()),
    }
    pd.Series(summary).to_json(ROOT / "analysis_metrics.json", indent=2)


if __name__ == "__main__":
    main()
