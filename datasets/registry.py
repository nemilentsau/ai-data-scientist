"""Registry of all 20 benchmark datasets with metadata for evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetMeta:
    """Metadata describing a benchmark dataset."""

    name: str
    category: str
    difficulty: str  # easy / medium / hard
    description: str
    expected_findings: list[str] = field(default_factory=list)
    key_pattern: str = ""
    traps: list[str] = field(default_factory=list)
    generator_fn: str = ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DATASET_REGISTRY: dict[str, DatasetMeta] = {
    # 1
    "simpsons_paradox": DatasetMeta(
        name="simpsons_paradox",
        category="Causal/Confounding",
        difficulty="hard",
        description="Trend reversal when grouped by a confounding variable.",
        expected_findings=[
            "Segment data by group variable",
            "Report trend reversal between aggregate and per-group analysis",
            "Identify the confounding group variable",
        ],
        key_pattern="Aggregate trend reverses direction within every sub-group",
        traps=[
            "Reporting only the aggregate trend",
            "Ignoring the grouping variable",
        ],
        generator_fn="generate_simpsons_paradox",
    ),
    # 2
    "pure_noise": DatasetMeta(
        name="pure_noise",
        category="Null/Baseline",
        difficulty="medium",
        description="Dataset with no real signal — pure random noise.",
        expected_findings=[
            "Conclude no statistically significant relationships",
            "Report low R² or equivalent metric",
            "Resist finding spurious patterns",
        ],
        key_pattern="No true relationship between any variables",
        traps=[
            "Overfitting noise",
            "Finding and reporting spurious patterns as real",
            "Not performing significance tests",
        ],
        generator_fn="generate_pure_noise",
    ),
    # 3
    "deterministic_linear": DatasetMeta(
        name="deterministic_linear",
        category="Regression",
        difficulty="easy",
        description="Perfect deterministic relationship y = 2x + 3.",
        expected_findings=[
            "Identify exact linear relationship",
            "Report R² ≈ 1.0",
            "Report correct slope (2) and intercept (3)",
        ],
        key_pattern="Perfect linear relationship y = 2x + 3",
        traps=[
            "Overcomplicating the model",
            "Trying nonlinear fits on perfectly linear data",
        ],
        generator_fn="generate_deterministic_linear",
    ),
    # 4
    "anscombes_quartet": DatasetMeta(
        name="anscombes_quartet",
        category="Visualization",
        difficulty="medium",
        description="Four datasets with identical summary statistics but very different distributions.",
        expected_findings=[
            "Visualize all four datasets",
            "Note that summary statistics are identical",
            "Identify distinct shapes (linear, quadratic, outlier, vertical)",
        ],
        key_pattern="Identical means, variances, correlations and regression lines but different shapes",
        traps=[
            "Only computing summary statistics without plotting",
            "Treating all four subsets identically",
        ],
        generator_fn="generate_anscombes_quartet",
    ),
    # 5
    "multicollinearity": DatasetMeta(
        name="multicollinearity",
        category="Regression",
        difficulty="medium",
        description="Multiple features that are highly correlated with each other.",
        expected_findings=[
            "Detect multicollinearity via VIF or correlation matrix",
            "Note unstable individual coefficient estimates",
            "Suggest remediation (drop features, PCA, regularisation)",
        ],
        key_pattern="Features are strongly inter-correlated, inflating coefficient variance",
        traps=[
            "Trusting individual coefficient p-values at face value",
            "Ignoring correlation between predictors",
        ],
        generator_fn="generate_multicollinearity",
    ),
    # 6
    "heteroscedasticity": DatasetMeta(
        name="heteroscedasticity",
        category="Regression",
        difficulty="medium",
        description="Variance of residuals grows with the predictor.",
        expected_findings=[
            "Produce residual plots",
            "Identify heteroscedasticity (non-constant variance)",
            "Suggest weighted regression or variance-stabilising transform",
        ],
        key_pattern="Residual spread increases with fitted values",
        traps=[
            "Assuming constant variance without checking",
            "Omitting residual diagnostics",
        ],
        generator_fn="generate_heteroscedasticity",
    ),
    # 7
    "outlier_dominated": DatasetMeta(
        name="outlier_dominated",
        category="Robustness",
        difficulty="medium",
        description="Dataset with ~5 % extreme outliers that dominate OLS fit.",
        expected_findings=[
            "Detect outliers via IQR, z-scores or visual inspection",
            "Compare robust vs. non-robust estimators",
            "Report influence of outliers on results",
        ],
        key_pattern="Small fraction of extreme values distorts ordinary least-squares",
        traps=[
            "Using OLS without outlier diagnostics",
            "Silently removing data without justification",
        ],
        generator_fn="generate_outlier_dominated",
    ),
    # 8
    "time_series_seasonality": DatasetMeta(
        name="time_series_seasonality",
        category="Time Series",
        difficulty="medium",
        description="Time series with weekly and yearly seasonal components.",
        expected_findings=[
            "Perform seasonal decomposition",
            "Identify weekly and yearly periodicities",
            "Model or account for seasonality",
        ],
        key_pattern="Additive weekly and yearly seasonal cycles",
        traps=[
            "Ignoring temporal structure entirely",
            "Treating rows as i.i.d. observations",
        ],
        generator_fn="generate_time_series_seasonality",
    ),
    # 9
    "mnar": DatasetMeta(
        name="mnar",
        category="Data Quality",
        difficulty="hard",
        description="Missingness is correlated with the unobserved target value (MNAR).",
        expected_findings=[
            "Analyse the missingness pattern",
            "Recognise data is Missing Not At Random",
            "Discuss bias from naive imputation or deletion",
        ],
        key_pattern="Probability of being missing depends on the missing value itself",
        traps=[
            "Dropping missing rows without analysis",
            "Imputing with mean/median blindly",
            "Assuming Missing Completely At Random",
        ],
        generator_fn="generate_mnar",
    ),
    # 10
    "class_imbalance": DatasetMeta(
        name="class_imbalance",
        category="Classification",
        difficulty="medium",
        description="Binary classification with a 95/5 class split.",
        expected_findings=[
            "Report balanced metrics (F1, precision, recall, AUC)",
            "Apply resampling or class-weight adjustment",
            "Evaluate with appropriate strategy (stratified CV)",
        ],
        key_pattern="Extreme class imbalance — 95 % majority, 5 % minority",
        traps=[
            "Reporting accuracy only",
            "Ignoring the minority class entirely",
        ],
        generator_fn="generate_class_imbalance",
    ),
    # 11
    "quadratic": DatasetMeta(
        name="quadratic",
        category="Regression",
        difficulty="medium",
        description="True relationship is y = x² + noise, disguised as a regression task.",
        expected_findings=[
            "Detect non-linearity in residual plots",
            "Fit polynomial or other nonlinear model",
            "Report substantially better R² than linear baseline",
        ],
        key_pattern="Quadratic relationship y = x² + noise",
        traps=[
            "Only trying a linear model",
            "Not inspecting residuals",
        ],
        generator_fn="generate_quadratic",
    ),
    # 12
    "well_separated_clusters": DatasetMeta(
        name="well_separated_clusters",
        category="Clustering",
        difficulty="easy",
        description="Three clearly separated blobs in 2-D space.",
        expected_findings=[
            "Identify k = 3 as optimal cluster count",
            "Achieve high silhouette score",
            "Visualise clusters in scatter plot",
        ],
        key_pattern="Three well-separated Gaussian blobs",
        traps=[
            "Not visualising the data",
            "Choosing an arbitrary k without justification",
        ],
        generator_fn="generate_well_separated_clusters",
    ),
    # 13
    "overlapping_clusters": DatasetMeta(
        name="overlapping_clusters",
        category="Clustering",
        difficulty="hard",
        description="Clusters with significant overlap — ambiguous boundaries.",
        expected_findings=[
            "Note cluster ambiguity",
            "Perform silhouette or gap-statistic analysis",
            "Report uncertainty in cluster assignment",
        ],
        key_pattern="Clusters overlap substantially, making hard assignments unreliable",
        traps=[
            "Forcing k = 3 without validation",
            "Ignoring low silhouette scores",
        ],
        generator_fn="generate_overlapping_clusters",
    ),
    # 14
    "survival_censored": DatasetMeta(
        name="survival_censored",
        category="Specialized",
        difficulty="hard",
        description="Right-censored survival/time-to-event data.",
        expected_findings=[
            "Use Kaplan-Meier estimator or Cox proportional-hazards model",
            "Account for censoring in analysis",
            "Produce survival curves",
        ],
        key_pattern="Right-censored observations require survival-analysis methods",
        traps=[
            "Computing naive mean of observed times",
            "Ignoring the censoring indicator",
        ],
        generator_fn="generate_survival_censored",
    ),
    # 15
    "multimodal": DatasetMeta(
        name="multimodal",
        category="EDA",
        difficulty="medium",
        description="Target variable is a mixture of 3 Gaussians.",
        expected_findings=[
            "Detect multimodality (histogram, KDE)",
            "Identify approximately 3 modes",
            "Avoid single-Gaussian assumptions in modelling",
        ],
        key_pattern="Three-component Gaussian mixture in the target variable",
        traps=[
            "Assuming normality without checking",
            "Not plotting the distribution",
        ],
        generator_fn="generate_multimodal",
    ),
    # 16
    "spurious_correlation": DatasetMeta(
        name="spurious_correlation",
        category="Causal",
        difficulty="hard",
        description="Two variables are correlated only because both trend with time.",
        expected_findings=[
            "Identify time as a confounding variable",
            "Show that partial correlation controlling for time is near zero",
            "Warn against causal interpretation",
        ],
        key_pattern="Spurious correlation driven by a shared time trend",
        traps=[
            "Claiming a causal relationship",
            "Not controlling for the time confounder",
        ],
        generator_fn="generate_spurious_correlation",
    ),
    # 17
    "high_dim_sparse": DatasetMeta(
        name="high_dim_sparse",
        category="Feature Selection",
        difficulty="medium",
        description="100 features but only 3 are truly informative.",
        expected_findings=[
            "Perform feature selection or regularisation",
            "Identify the small set of informative features",
            "Demonstrate improved performance with fewer features",
        ],
        key_pattern="Only 3 out of 100 features carry predictive signal",
        traps=[
            "Using all 100 features without selection",
            "Overfitting on noise features",
        ],
        generator_fn="generate_high_dim_sparse",
    ),
    # 18
    "interaction_effects": DatasetMeta(
        name="interaction_effects",
        category="Classification",
        difficulty="hard",
        description="Label depends on A x B interaction, not main effects alone.",
        expected_findings=[
            "Test for interaction terms or use tree-based models",
            "Show that main-effects-only model underperforms",
            "Identify A x B as the key interaction",
        ],
        key_pattern="Classification boundary is driven by an A x B interaction effect",
        traps=[
            "Only checking main effects",
            "Using a purely additive model",
        ],
        generator_fn="generate_interaction_effects",
    ),
    # 19
    "lognormal_skew": DatasetMeta(
        name="lognormal_skew",
        category="Transformation",
        difficulty="medium",
        description="Target variable follows a log-normal distribution.",
        expected_findings=[
            "Detect right skew in the target",
            "Apply log (or Box-Cox) transform",
            "Show improved model fit after transformation",
        ],
        key_pattern="Target is log-normally distributed — heavy right skew",
        traps=[
            "Assuming normality of the target",
            "Not checking residual distribution",
        ],
        generator_fn="generate_lognormal_skew",
    ),
    # 20
    "concept_drift": DatasetMeta(
        name="concept_drift",
        category="Temporal",
        difficulty="hard",
        description="Underlying distribution shifts abruptly at the midpoint of the series.",
        expected_findings=[
            "Detect distribution shift or concept drift",
            "Split analysis into pre- and post-shift segments",
            "Report degraded performance of a single global model",
        ],
        key_pattern="Abrupt distribution change at the midpoint of the dataset",
        traps=[
            "Fitting a single model to all data without checking for drift",
            "Ignoring temporal ordering",
        ],
        generator_fn="generate_concept_drift",
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_dataset(name: str) -> DatasetMeta:
    """Return metadata for a single dataset by name.

    Raises ``KeyError`` with a helpful message if the name is not found.
    """
    try:
        return DATASET_REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(DATASET_REGISTRY))
        raise KeyError(
            f"Unknown dataset '{name}'. Available datasets: {available}"
        ) from None


def list_datasets() -> list[str]:
    """Return a sorted list of all registered dataset names."""
    return sorted(DATASET_REGISTRY)
