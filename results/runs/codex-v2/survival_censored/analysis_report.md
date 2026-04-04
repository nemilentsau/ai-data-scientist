# Survival Analysis Report

## What this dataset appears to contain

`dataset.csv` contains 800 patient records with 8 columns: a unique patient identifier, demographic covariates (`age`, `sex`), disease/tumor descriptors (`stage`, `biomarker_level`), treatment assignment (`Drug_A` or `Drug_B`), follow-up time in months (`months_on_study`), and an event indicator (`event_occurred`).

The structure is unusually clean for operational clinical data: there are no missing values, no duplicate patient IDs, and all variables have plausible ranges. Ages run from 30 to 90 years (mean 62.0), biomarker values are right-skewed (median 4.46, max 53.94), and 66.3% of patients experienced the event during follow-up. The dataset looks most like a trial-style or curated observational survival dataset, so the main question is time to event rather than simple event classification.

## Key findings

### 1. Treatment arm is the strongest signal in the dataset

The clearest finding is a large separation between treatment groups in event-free survival. In the Kaplan-Meier curves in `plots/km_treatment.png`, `Drug_B` stays above `Drug_A` throughout follow-up. The median event-free survival is 13.5 months for `Drug_B` versus 7.6 months for `Drug_A`. Estimated survival at 12 months is 54.2% for `Drug_B` and 33.5% for `Drug_A`, a gap of 20.7 percentage points; at 24 months the gap is still 21.1 points (31.5% vs 10.4%).

This difference is highly unlikely to be noise. The log-rank test gives p = 1.23e-14. In an adjusted Cox proportional-hazards model controlling for age, sex, stage, and log biomarker, `Drug_B` has a hazard ratio of 0.51 (95% CI 0.43 to 0.61, p = 3.71e-14). Interpreted practically, patients on `Drug_B` have about a 49% lower instantaneous event risk than comparable patients on `Drug_A`.

### 2. There is some baseline imbalance, but it does not explain the treatment result

Before interpreting the survival difference, I checked whether the treatment groups looked systematically different at baseline. Age (Welch t-test p = 0.0750), sex (chi-square p = 0.8581), and biomarker level (Mann-Whitney p = 0.2240) are all fairly similar across arms. Stage is the one variable that does differ: chi-square p = 0.0400.

The imbalance is visible in `plots/stage_by_treatment.png`. Stage I patients make up 15.3% of `Drug_A` but 23.2% of `Drug_B`, so `Drug_B` does have a somewhat easier baseline case mix. However, this is not enough to explain the outcome gap. Once stage is included in the adjusted Cox model, the treatment hazard ratio remains essentially unchanged at 0.51. If the raw treatment difference were mostly stage confounding, that estimate should have moved substantially toward 1.0 after adjustment.

### 3. The usual prognostic variables are surprisingly weak here

The adjusted Cox model in `plots/cox_forest.png` shows that age, sex, stage, and biomarker carry much less signal than treatment. None of the stage indicators are statistically distinguishable from the Stage I reference group, and a stage-only log-rank comparison is also null (p = 0.7021). The biomarker effect is small and imprecise: hazard ratio 0.93 per one-unit increase in log biomarker (95% CI 0.83 to 1.04, p = 0.1916).

This is not just a question of underpowered interactions. When I added treatment-biomarker and treatment-stage interaction terms, there was no convincing heterogeneity of treatment effect. The treatment-biomarker interaction had p = 0.2881, and the treatment-stage interaction p-values were Stage II: 0.9409, Stage III: 0.7111, Stage IV: 0.4954. Model discrimination only improved from a concordance index of 0.587 with treatment alone to 0.605 with all baseline covariates, which reinforces the same point: most of the predictive signal is in the treatment arm itself.

## What the findings mean

If this dataset reflects a real study, the practical conclusion is straightforward: `Drug_B` is associated with materially longer event-free survival, and that association is robust to the observed baseline covariates. The clinical implication would be strong preference for `Drug_B` over `Drug_A`, assuming no countervailing toxicity or cost information outside this table.

The more surprising implication is what the dataset does **not** show. Variables that are usually prognostic in oncology-style data, especially stage and biomarker burden, have little explanatory value here. That could mean the event process in this dataset is genuinely treatment-driven, or it could mean the available covariates are too coarse to capture true baseline severity.

## Limitations and self-critique

The biggest limitation is causal interpretation. I can show a strong association between treatment and survival, but I cannot prove treatment caused the difference from this table alone. Treatment assignment is not known to be randomized, and the stage imbalance shows that the arms are not perfectly exchangeable. Unmeasured confounders such as comorbidities, performance status, prior therapy, or site effects could still account for part of the benefit.

Another caution is the unusual weakness of stage and biomarker. That result could be real, but it could also reflect noisy or simplified variable definitions. `stage` may be too coarse, biomarker timing is unknown, and there is no information about measurement error or how the event was defined. Because the dataset is perfectly complete and highly structured, it may also be synthetic or heavily curated; if so, inference should focus on the simulated relationships actually present rather than on external clinical realism.

Model assumptions were checked to the extent possible within this analysis. The Cox model did not show obvious proportional-hazards violations for the included covariates, but I did not fit alternative survival families or conduct sensitivity analyses for unmeasured confounding. I also programmatically reloaded each saved PNG to verify that the files were non-empty and had visual contrast, but direct manual image inspection was limited by the terminal-only environment.
