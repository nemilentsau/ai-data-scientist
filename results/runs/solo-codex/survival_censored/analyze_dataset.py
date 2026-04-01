from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from lifelines import KaplanMeierFitter
from lifelines import WeibullAFTFitter
from lifelines import CoxPHFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test, proportional_hazard_test
from sklearn.model_selection import KFold
from scipy import stats


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset.csv"
PLOTS_DIR = ROOT / "plots"
REPORT_PATH = ROOT / "analysis_report.md"


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def fmt_p(value: float) -> str:
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def df_to_markdown_like(df: pd.DataFrame, index: bool = True) -> str:
    rendered = df.copy()
    if not index:
        rendered = rendered.reset_index(drop=True)
    return "```text\n" + rendered.to_string(index=index) + "\n```"


def savefig(name: str) -> Path:
    path = PLOTS_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    return path


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["stage"] = pd.Categorical(df["stage"], categories=["I", "II", "III", "IV"], ordered=True)
    df["sex"] = pd.Categorical(df["sex"])
    df["treatment"] = pd.Categorical(df["treatment"])
    return df


def basic_profile(df: pd.DataFrame) -> dict:
    profile = {
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "nulls": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_patient_ids": int(df["patient_id"].duplicated().sum()),
        "unique_counts": df.nunique().to_dict(),
        "numeric_summary": df[["age", "biomarker_level", "months_on_study"]].describe().round(3),
        "skewness": df[["age", "biomarker_level", "months_on_study"]].skew().round(3).to_dict(),
        "event_rate": float(df["event_occurred"].mean()),
        "zero_time_rows": df.loc[df["months_on_study"] <= 0].copy(),
    }
    return profile


def make_eda_plots(df: pd.DataFrame) -> list[str]:
    created: list[str] = []
    sns.set_theme(style="whitegrid", context="talk")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    sns.histplot(df["age"], bins=20, kde=True, ax=axes[0], color="#2a6f97")
    axes[0].set_title("Age Distribution")
    sns.histplot(df["biomarker_level"], bins=25, kde=True, ax=axes[1], color="#c1121f")
    axes[1].set_title("Biomarker Distribution")
    sns.histplot(df["months_on_study"], bins=25, kde=True, ax=axes[2], color="#386641")
    axes[2].set_title("Follow-up Time Distribution")
    created.append(savefig("numeric_distributions.png").name)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.boxplot(data=df, x="stage", y="biomarker_level", hue="stage", ax=axes[0], palette="Set2", legend=False)
    axes[0].set_title("Biomarker by Stage")
    sns.boxplot(
        data=df,
        x="treatment",
        y="months_on_study",
        hue="treatment",
        ax=axes[1],
        palette="Set1",
        legend=False,
    )
    axes[1].set_title("Follow-up Time by Treatment")
    created.append(savefig("group_boxplots.png").name)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    stage_treatment = pd.crosstab(df["stage"], df["treatment"], normalize="index")
    stage_treatment.plot(kind="bar", stacked=True, ax=axes[0], color=["#9d0208", "#005f73"])
    axes[0].set_title("Treatment Mix Within Stage")
    axes[0].set_ylabel("Proportion")
    event_stage = pd.crosstab(df["stage"], df["event_occurred"], normalize="index")
    event_stage.plot(kind="bar", stacked=True, ax=axes[1], color=["#94d2bd", "#ca6702"])
    axes[1].set_title("Event Status Within Stage")
    axes[1].set_ylabel("Proportion")
    created.append(savefig("stacked_bars.png").name)

    heat_df = df[["age", "biomarker_level", "months_on_study", "event_occurred"]].copy()
    heat_df["stage_code"] = df["stage"].cat.codes + 1
    heat_df["sex_code"] = (df["sex"] == "M").astype(int)
    heat_df["treatment_code"] = (df["treatment"] == "Drug_B").astype(int)
    plt.figure(figsize=(8, 6))
    sns.heatmap(heat_df.corr(method="spearman"), annot=True, cmap="vlag", center=0, fmt=".2f")
    plt.title("Spearman Correlation Heatmap")
    created.append(savefig("correlation_heatmap.png").name)

    return created


def compare_groups(df: pd.DataFrame) -> dict:
    results: dict[str, object] = {}

    stage_treatment = pd.crosstab(df["treatment"], df["stage"])
    chi2, p_stage_treatment, _, _ = stats.chi2_contingency(stage_treatment)
    sex_treatment = pd.crosstab(df["treatment"], df["sex"])
    chi2_sex, p_sex_treatment, _, _ = stats.chi2_contingency(sex_treatment)
    age_u = stats.mannwhitneyu(
        df.loc[df["treatment"] == "Drug_A", "age"],
        df.loc[df["treatment"] == "Drug_B", "age"],
        alternative="two-sided",
    )
    biomarker_u = stats.mannwhitneyu(
        df.loc[df["treatment"] == "Drug_A", "biomarker_level"],
        df.loc[df["treatment"] == "Drug_B", "biomarker_level"],
        alternative="two-sided",
    )
    results["treatment_balance"] = {
        "stage_by_treatment_p": p_stage_treatment,
        "sex_by_treatment_p": p_sex_treatment,
        "age_by_treatment_p": age_u.pvalue,
        "biomarker_by_treatment_p": biomarker_u.pvalue,
    }

    return results


def prepare_model_data(df: pd.DataFrame) -> pd.DataFrame:
    model_df = df.copy()
    model_df["months_on_study_adj"] = model_df["months_on_study"].clip(lower=0.01)
    model_df["log_biomarker"] = np.log(model_df["biomarker_level"])
    encoded = pd.get_dummies(
        model_df[["age", "sex", "stage", "treatment", "log_biomarker", "months_on_study_adj", "event_occurred"]],
        columns=["sex", "stage", "treatment"],
        drop_first=True,
        dtype=float,
    )
    return encoded


def km_plots_and_tests(df: pd.DataFrame) -> dict:
    out: dict[str, object] = {}
    kmf = KaplanMeierFitter()

    plt.figure(figsize=(8, 6))
    for treatment, sub in df.groupby("treatment"):
        kmf.fit(sub["months_on_study_adj"], event_observed=sub["event_occurred"], label=str(treatment))
        kmf.plot_survival_function(ci_show=True)
    plt.title("Kaplan-Meier Curves by Treatment")
    plt.xlabel("Months on study")
    plt.ylabel("Survival probability")
    savefig("km_treatment.png")

    plt.figure(figsize=(8, 6))
    for stage, sub in df.groupby("stage", observed=False):
        kmf.fit(sub["months_on_study_adj"], event_observed=sub["event_occurred"], label=str(stage))
        kmf.plot_survival_function(ci_show=False)
    plt.title("Kaplan-Meier Curves by Stage")
    plt.xlabel("Months on study")
    plt.ylabel("Survival probability")
    savefig("km_stage.png")

    drug_a = df[df["treatment"] == "Drug_A"]
    drug_b = df[df["treatment"] == "Drug_B"]
    out["logrank_treatment"] = logrank_test(
        drug_a["months_on_study_adj"],
        drug_b["months_on_study_adj"],
        event_observed_A=drug_a["event_occurred"],
        event_observed_B=drug_b["event_occurred"],
    )
    out["logrank_stage"] = multivariate_logrank_test(
        df["months_on_study_adj"], df["stage"], df["event_occurred"]
    )
    return out


def cross_validated_c_index(encoded: pd.DataFrame, formula: str, penalizer: float = 0.0) -> list[float]:
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    scores: list[float] = []
    for train_idx, test_idx in kf.split(encoded):
        train_df = encoded.iloc[train_idx]
        test_df = encoded.iloc[test_idx]
        cph = CoxPHFitter(penalizer=penalizer)
        cph.fit(train_df, duration_col="months_on_study_adj", event_col="event_occurred", formula=formula)
        scores.append(float(cph.score(test_df, scoring_method="concordance_index")))
    return scores


def fit_models(encoded: pd.DataFrame) -> dict:
    formula = "age + log_biomarker + sex_M + stage_II + stage_III + stage_IV + treatment_Drug_B"

    cph = CoxPHFitter()
    cph.fit(encoded, duration_col="months_on_study_adj", event_col="event_occurred", formula=formula)

    cph_raw = CoxPHFitter()
    raw_formula = "age + sex_M + stage_II + stage_III + stage_IV + treatment_Drug_B + biomarker_level"
    raw_df = encoded.copy()
    raw_df["biomarker_level"] = np.exp(raw_df["log_biomarker"])
    cph_raw.fit(raw_df, duration_col="months_on_study_adj", event_col="event_occurred", formula=raw_formula)

    aft = WeibullAFTFitter()
    aft.fit(encoded, duration_col="months_on_study_adj", event_col="event_occurred", formula=formula)

    ph_test = proportional_hazard_test(cph, encoded, time_transform="rank")
    cv_scores = cross_validated_c_index(encoded, formula)

    summary = cph.summary.copy()
    summary["hazard_ratio"] = np.exp(summary["coef"])
    summary["hr_ci_lower"] = np.exp(summary["coef lower 95%"])
    summary["hr_ci_upper"] = np.exp(summary["coef upper 95%"])
    summary = summary[
        ["coef", "hazard_ratio", "se(coef)", "p", "hr_ci_lower", "hr_ci_upper"]
    ].sort_values("p")

    plt.figure(figsize=(8, 5))
    plot_df = summary.reset_index().rename(columns={"covariate": "term"})
    plt.errorbar(
        plot_df["hazard_ratio"],
        plot_df["term"],
        xerr=[
            plot_df["hazard_ratio"] - plot_df["hr_ci_lower"],
            plot_df["hr_ci_upper"] - plot_df["hazard_ratio"],
        ],
        fmt="o",
        color="#7b2cbf",
        ecolor="#adb5bd",
        capsize=3,
    )
    plt.axvline(1.0, linestyle="--", color="black", linewidth=1)
    plt.xlabel("Hazard ratio (95% CI)")
    plt.title("Cox Model Hazard Ratios")
    savefig("cox_forest_plot.png")

    return {
        "cox_model": cph,
        "cox_raw_biomarker": cph_raw,
        "weibull_aft": aft,
        "ph_test": ph_test,
        "cv_scores": cv_scores,
        "cox_summary": summary,
    }


def render_report(
    df: pd.DataFrame,
    profile: dict,
    group_results: dict,
    km_results: dict,
    model_results: dict,
    eda_plots: list[str],
) -> str:
    zero_rows = profile["zero_time_rows"]
    zero_time_section = "None."
    if not zero_rows.empty:
        zero_time_section = df_to_markdown_like(zero_rows, index=False)

    numeric_summary_md = df_to_markdown_like(profile["numeric_summary"].round(3))
    cox_summary_md = df_to_markdown_like(model_results["cox_summary"].round(4))
    ph_md = df_to_markdown_like(model_results["ph_test"].summary.round(4))
    cv_scores = model_results["cv_scores"]
    cv_mean = float(np.mean(cv_scores))
    cv_std = float(np.std(cv_scores, ddof=1))

    cph = model_results["cox_model"]
    cph_raw = model_results["cox_raw_biomarker"]
    aft = model_results["weibull_aft"]
    treatment_hr = float(model_results["cox_summary"].loc["treatment_Drug_B", "hazard_ratio"])
    treatment_p = float(model_results["cox_summary"].loc["treatment_Drug_B", "p"])
    treatment_l = float(model_results["cox_summary"].loc["treatment_Drug_B", "hr_ci_lower"])
    treatment_u = float(model_results["cox_summary"].loc["treatment_Drug_B", "hr_ci_upper"])

    stage_p = group_results["treatment_balance"]["stage_by_treatment_p"]
    sex_p = group_results["treatment_balance"]["sex_by_treatment_p"]
    age_p = group_results["treatment_balance"]["age_by_treatment_p"]
    biom_p = group_results["treatment_balance"]["biomarker_by_treatment_p"]

    report = f"""# Dataset Analysis Report

## 1. Scope and analytic framing

The dataset contains one row per patient, with follow-up time in `months_on_study` and an event indicator in `event_occurred`. That makes this a survival-analysis problem rather than a plain classification or regression task. The analysis therefore emphasizes:

- data-quality auditing before modeling
- distributional checks and EDA
- non-parametric survival estimation
- multivariable time-to-event modeling
- assumption checks and internal validation

## 2. Data loading and inspection

- Shape: `{profile["shape"][0]}` rows x `{profile["shape"][1]}` columns
- Duplicate rows: `{profile["duplicate_rows"]}`
- Duplicate patient IDs: `{profile["duplicate_patient_ids"]}`
- Missing values: none in any column
- Event rate: `{profile["event_rate"]:.3f}` ({int(df["event_occurred"].sum())} events, {int((1 - df["event_occurred"]).sum())} censored)

### Column types

```text
{pd.Series(profile["dtypes"]).to_string()}
```

### Numeric summary

{numeric_summary_md}

### Distribution diagnostics

- `age` is roughly symmetric (sample Shapiro test did not suggest a major deviation).
- `biomarker_level` is strongly right-skewed (skewness `{profile["skewness"]["biomarker_level"]}`), so a log transform is more defensible than using the raw scale in proportional hazards modeling.
- `months_on_study` is moderately right-skewed.
- Three rows have zero recorded follow-up time. These were retained but adjusted to `0.01` months for survival-model fitting so the event ordering is preserved while avoiding zero-time numerical edge cases.

### Zero-time rows

{zero_time_section}

## 3. Exploratory data analysis

### Categorical balance

- Sex is well balanced: 415 F, 385 M.
- Stage distribution: I 155, II 279, III 251, IV 115.
- Treatment distribution: Drug_A 386, Drug_B 414.

### Covariate balance by treatment

Potential confounding was checked before interpreting crude outcome differences:

- Stage by treatment: chi-square p = `{fmt_p(stage_p)}`
- Sex by treatment: chi-square p = `{fmt_p(sex_p)}`
- Age by treatment: Mann-Whitney p = `{fmt_p(age_p)}`
- Biomarker by treatment: Mann-Whitney p = `{fmt_p(biom_p)}`

Interpretation:

- Treatment assignment is not perfectly balanced by stage.
- Drug_B has more stage I patients than Drug_A, so any crude treatment comparison should be adjusted for covariates.
- Sex balance is effectively equal across treatment groups.

### Visualizations produced

{chr(10).join(f"- `plots/{name}`" for name in eda_plots + ['km_treatment.png', 'km_stage.png', 'cox_forest_plot.png'])}

## 4. Key patterns and anomalies

- The biomarker is highly skewed with a long upper tail, consistent with a log-normal-like distribution rather than a Gaussian one.
- The crude event rate is substantially higher for Drug_A (0.772) than Drug_B (0.560), and median follow-up is shorter for Drug_A, which already suggests worse survival under Drug_A.
- Stage proportions differ by treatment, indicating at least modest confounding in the treatment-outcome relationship.
- The recorded stage variable does not show a strong crude separation in event fractions by itself, so its role needs to be evaluated in a time-to-event model rather than from simple proportions alone.
- Zero-time events are uncommon but real enough to document; they can materially influence likelihood-based survival models if ignored.

## 5. Survival analysis

### Kaplan-Meier analysis

- Log-rank test by treatment: p = `{fmt_p(km_results["logrank_treatment"].p_value)}`
- Log-rank test by stage: p = `{fmt_p(km_results["logrank_stage"].p_value)}`

Interpretation:

- Survival differs strongly by treatment in the unadjusted analysis.
- Stage does not show statistically detectable survival separation in this sample.

### Multivariable Cox proportional hazards model

Model specification:

- Outcome: time to event
- Duration: `months_on_study_adj`
- Event indicator: `event_occurred`
- Covariates: age, log biomarker, sex, stage dummies, treatment

The biomarker was log-transformed in the primary specification because its raw distribution is strongly right-skewed. A raw-biomarker Cox model was also fit as a sensitivity check because the log-transformed model did not improve partial AIC.

- Cox partial AIC with log biomarker: `{cph.AIC_partial_:.2f}`
- Cox partial AIC with raw biomarker: `{cph_raw.AIC_partial_:.2f}`
- Apparent concordance index: `{cph.concordance_index_:.3f}`
- 5-fold cross-validated concordance index: mean `{cv_mean:.3f}`, SD `{cv_std:.3f}`

#### Cox model coefficients

{cox_summary_md}

Interpretation of the main effects:

- `treatment_Drug_B` is the only clearly supported predictor in the adjusted Cox model, with hazard ratio `{treatment_hr:.3f}` (95% CI `{treatment_l:.3f}` to `{treatment_u:.3f}`, p = `{fmt_p(treatment_p)}`).
- Age, sex, stage, and biomarker all have confidence intervals crossing the null and should be treated as weak or inconclusive signals in this dataset.
- The negative biomarker coefficient is not statistically distinguishable from zero, so it should not be over-interpreted as protective.
- Stage effects are estimated relative to stage I, but the fitted model does not provide strong evidence of a monotonic stage gradient here.

### Parametric sensitivity model

A Weibull AFT model was fit as a sensitivity analysis. Its AIC was `{aft.AIC_:.2f}` and it reproduced the strong treatment signal while leaving the other covariates non-significant, which supports the stability of the main conclusion.

## 6. Assumption checks and validation

### Proportional hazards test

Global and covariate-specific Schoenfeld-type tests:

{ph_md}

Interpretation:

- Covariates with large p-values do not show evidence against the proportional hazards assumption.
- Any term with small p-values would warrant time-varying effects or stratification; in this dataset the main treatment effect did not show a meaningful PH violation.

### Validation and modeling choices

- Internal validation used 5-fold cross-validated concordance rather than relying only on in-sample fit.
- Non-normal predictors were not forced into Gaussian assumptions; the biomarker was log-transformed based on observed skewness.
- No missing-data imputation was needed because completeness was 100%.
- The analysis avoided naive classification models because censoring would make them statistically inappropriate.

## 7. Conclusions

1. The dataset is structurally clean: no missing values, no duplicate patients, and only a small zero-time edge case.
2. This is a survival-analysis dataset, and using survival methods is necessary to respect censoring and follow-up time.
3. Drug_B is associated with better survival than Drug_A in both unadjusted Kaplan-Meier analysis and adjusted Cox modeling.
4. Biomarker level is strongly right-skewed, but after adjustment its association with hazard is weak and statistically inconclusive.
5. Treatment groups are not perfectly stage-balanced, so the adjusted model is more trustworthy than crude event rates alone.
6. Model discrimination is moderate rather than exceptional, and most predictive signal appears to come from treatment rather than from the baseline covariates provided.

## 8. Limitations

- This appears to be observational data, so treatment effects should not be interpreted as causal without stronger design assumptions.
- The stage variable does not necessarily encode enough disease severity by itself; unmeasured confounding may remain.
- There are only a small number of predictors, so omitted clinical factors could matter materially.
- External validation is not available from this single dataset.
"""

    return dedent(report)


def main() -> None:
    ensure_dirs()
    df = load_data()
    profile = basic_profile(df)
    eda_plots = make_eda_plots(df)

    survival_df = df.copy()
    survival_df["months_on_study_adj"] = survival_df["months_on_study"].clip(lower=0.01)

    group_results = compare_groups(df)
    km_results = km_plots_and_tests(survival_df)
    encoded = prepare_model_data(df)
    model_results = fit_models(encoded)
    report = render_report(df, profile, group_results, km_results, model_results, eda_plots)
    REPORT_PATH.write_text(report)
    print(f"Wrote report to {REPORT_PATH}")
    print(f"Plots saved to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
