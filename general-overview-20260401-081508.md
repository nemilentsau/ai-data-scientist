# General Overview

Run ID: `20260401-081508`

## Scope

This note summarizes the shared failure modes across the Claude and Codex benchmark runs, with emphasis on:

- `overlapping_clusters`
- `concept_drift`
- all datasets where either harness received a `partial` verdict

Sources reviewed:

- `results/runs/solo-baseline/overlapping_clusters`
- `results/runs/solo-baseline/concept_drift`
- `results/runs/solo-codex/overlapping_clusters`
- `results/runs/solo-codex/concept_drift`
- `datasets/generator.py`
- `harness/prompt_template.txt`

## Benchmark Outcome

Both agents failed in the same broad way:

- `overlapping_clusters`: Claude `failed`, Codex `failed`
- `concept_drift`: Claude `wrong`, Codex `wrong`

This is not just a model-specific miss. It is a systematic harness-level failure mode.

## Executive Diagnosis

The common problem was premature task framing.

Both agents defaulted to a generic supervised workflow:

1. Find the most target-like column.
2. Run regression or classification.
3. If pooled out-of-sample performance is weak, conclude the data has little signal or is missing important features.

That workflow works for many benchmark datasets, but it is exactly wrong for these two:

- `overlapping_clusters` is an unsupervised ambiguity problem, not a GPA prediction problem.
- `concept_drift` is a relationship-stability problem, not a static pooled prediction problem.

The generic harness prompt likely reinforces this behavior because it asks the agent to identify patterns and then "build appropriate model(s)" without forcing an explicit task-family decision first.

## Dataset 1: `overlapping_clusters`

### What the data is actually testing

The generator creates three latent groups in only two variables:

- `weekly_study_hours`
- `gpa`

All other fields are effectively noise:

- `extracurriculars`
- `commute_minutes`
- `part_time_job_hours`
- `absences`

The relevant generator section is in `datasets/generator.py`, where the centers are:

- `(10, 3.2)`
- `(12, 3.4)`
- `(11, 3.0)`

with large within-cluster spread:

- `study_hrs ~ N(center, 4)`
- `gpa ~ N(center, 0.6)` clipped to `[0, 4]`

### Why the agents missed it

Both agents treated `gpa` as an obvious target and switched immediately into regression:

- Codex explicitly set `y = df["gpa"]` in its script.
- Claude's report framed the file as a student GPA prediction problem from the start.

Once that happened, the rest of the analysis became internally coherent but irrelevant. They proved that the noise covariates do not predict GPA, which is true, but they never asked whether the data should be clustered in the first place.

### What the data says when analyzed correctly

The clustering structure is real but weak and ambiguous.

Local checks run directly on the generator output:

- On all six substantive features, KMeans silhouette is only about `0.12` to `0.13`.
- On all six substantive features, adjusted Rand index versus true labels is about `0.006` at `k=3`.
- Even on the signal dimensions only (`weekly_study_hours`, `gpa`), adjusted Rand index is only about `0.046` at `k=3`.

The latent centers are close relative to the spread:

- pairwise standardized distances are only about `0.42` to `0.73`

So the correct conclusion is not "there are no clusters" and not "there are three clean clusters." The correct conclusion is:

- there is weak subgroup structure
- hard assignments are unreliable
- any segmentation should be reported with uncertainty

### Isolated failure mode here

The specific miss was task-family inference.

The agents saw a plausible continuous target column and interpreted the problem as supervised prediction before testing whether unsupervised structure was the real point.

## Dataset 2: `concept_drift`

### What the data is actually testing

The generator keeps the marginal distributions roughly stable but flips the feature-target relationship halfway through the series.

Specifically:

- first half: `defect_rate` increases with `temperature_c`
- second half: `defect_rate` decreases with `temperature_c`

This is a concept-drift problem in the conditional relationship, not necessarily in the raw marginals.

### Why the agents missed it

Both agents did respect time order, which is why each still got one required criterion. But both then performed the wrong temporal checks:

- rolling means
- autocorrelation
- pooled correlations
- pooled models

Those checks are not enough when the drift lives in the slope rather than in the marginal distribution.

As a result, both agents concluded:

- no drift
- weak explanatory signal
- likely missing features

That conclusion is understandable from pooled modeling, but it is wrong for this dataset.

### What the data says when analyzed correctly

The pre/post marginals are intentionally similar:

- pre/post KS tests are nonsignificant for all numeric columns
- `defect_rate` mean changes by only about `0.0067`

So a generic drift check on means or distributions will often say "stable."

But the conditional relationship clearly flips:

- pre half `corr(temperature_c, defect_rate) ~= +0.254`
- post half `corr(temperature_c, defect_rate) ~= -0.193`
- pooled `corr(temperature_c, defect_rate) ~= +0.025`

Linear models show the same pattern:

- pooled temperature-only model `R^2 ~= 0.0006`
- segmented pre/post temperature-only models combined `R^2 ~= 0.0506`
- pre coefficient `~= +0.0098`
- post coefficient `~= -0.0076`

Rolling local slopes also flip sign around the midpoint:

- clearly positive in early windows
- clearly negative in later windows

So the data does contain signal. The signal is just destroyed by pooling across regimes.

### Isolated failure mode here

The specific miss was checking temporal stability of marginals instead of temporal stability of relationships.

The agents preserved time order but never asked:

- does the coefficient change over time?
- does the correlation change over time?
- does a pre/post split materially improve fit?

## Shared Failure Pattern

Across both datasets, the shared failure chain was:

1. Use the generic prompt as a supervised modeling instruction.
2. Lock onto the most semantically target-like column.
3. Run competent pooled modeling.
4. Treat poor pooled performance as evidence of weak signal.
5. Recommend more features instead of questioning the framing.

This is why the results look similar across Claude and Codex. The issue is less about model capability than about the decision policy induced by the benchmark setup.

## Why These Two Datasets Are Especially Hard

These two cases hide the signal in second-order structure.

`overlapping_clusters` hides it in:

- latent geometry
- ambiguity of assignment
- weak separation rather than strong predictive structure

`concept_drift` hides it in:

- sign changes of the feature-target relationship
- stable marginals with unstable conditional behavior

A generic "EDA + predictive model + diagnostics" template tends to miss both unless it explicitly checks alternative task families and nonstationary relationships.

## Suggested Mitigation

Prompt polish still helps, but a better prompt alone is unlikely to fix the benchmark's main failure modes.

The stronger intervention is a small multi-agent team with an explicit review loop.

### Proposed team architecture

1. **Hypothesis Generator**
   - Reads schema, summaries, and a small first-pass EDA.
   - Produces 3 to 5 candidate framings:
     - supervised prediction
     - clustering / segmentation
     - mixture / multimodality
     - temporal regime change
     - confounding / missingness / robustness issue
   - For each framing, lists the minimum tests or plots needed to falsify it.

2. **Analyst / Builder**
   - Runs the main analysis, but only after choosing among the candidate framings.
   - Builds competing models or diagnostics aligned to the top hypotheses.
   - Produces plots and an initial report draft.

3. **Visual Reviewer**
   - Actually inspects the generated plots as images, not just their filenames.
   - Answers a fixed visual checklist:
     - is the target unimodal or multimodal?
     - do any views suggest clusters or overlapping groups?
     - do a small number of points dominate the fit?
     - does the relationship look additive or interaction-driven?
     - does the relationship appear stable over time?
   - If the current plots are insufficient, requests new plots rather than guessing.

4. **Method Critic**
   - Challenges the analyst's framing and asks what alternative explanation has not yet been ruled out.
   - Checks for specific anti-patterns:
     - obvious target selected without justification
     - pooled model used where segmented modeling may be needed
     - additive model accepted without interaction comparison
     - confounder named without controlled collapse shown
     - outliers diagnosed without robust comparison

5. **Claim Verifier**
   - Reviews the final draft for proof completeness.
   - Forces each central claim to be backed by one explicit demonstration.
   - Makes sure the report contains the benchmark-critical label or action:
     - `MNAR`, not just "systematic missingness"
     - explicit controlled-collapse result for spurious correlation
     - explicit remediation for multicollinearity
     - explicit robust-vs-OLS comparison for outlier contamination

6. **Revision Loop**
   - If the critic or verifier finds a gap, the analyst gets one focused revision pass.
   - The loop should be short and targeted, not an open-ended conversation.

### Why actual plot review matters

The current harnesses mostly generate plots as artifacts for the report, but do not reliably use them as first-class reasoning inputs.

That matters because several benchmark failures were visible in plots before they were visible in summary metrics:

- `multimodal`: a true visual read of the rent distribution is more informative than skewness and OLS diagnostics.
- `overlapping_clusters`: scatter geometry matters more than GPA regression metrics.
- `outlier_dominated`: a small number of extreme points can dominate the visual story long before a generic model summary explains it well.
- `interaction_effects`: the joint surface or heatmap can reveal non-additivity that additive coefficients hide.

Plot review would help less on `concept_drift` if the agent only generated generic distributions and autocorrelation charts. For that dataset, the visual reviewer needs the right plots:

- pre/post scatter with fitted lines
- rolling coefficient plots
- segmented model comparison views

So the mitigation is not just "look at plots." It is:

- generate canonical structural plots
- force an agent to review them
- allow that reviewer to request better plots if the current set is not diagnostic

### How each role addresses the observed failure modes

#### Hypothesis Generator

This role primarily addresses **premature task framing**.

It would help on:

- `overlapping_clusters`
  - prevents immediate commitment to "`gpa` is the target"
  - forces clustering / geometry as a competing hypothesis
- `multimodal`
  - forces target-distribution shape to be considered before regression
- `outlier_dominated`
  - forces a robustness / contamination framing instead of only prediction
- `concept_drift`
  - forces temporal regime-change as an explicit hypothesis

#### Analyst / Builder

This role addresses **execution quality once the right hypotheses exist**.

It would help on:

- `interaction_effects`
  - by running additive and interaction-aware models side by side
- `spurious_correlation`
  - by fitting both raw and controlled analyses
- `multicollinearity`
  - by running both baseline and remedial models
- `mnar`
  - by modeling missingness explicitly and testing proxy relationships

The analyst alone is not enough; many of the existing runs already had competent analysis. The issue is that the analyst needs better upstream framing and stronger downstream critique.

#### Visual Reviewer

This role primarily addresses **structural phenomena that are easier to see than to summarize numerically**.

It would help on:

- `multimodal`
  - direct identification of multiple rent modes
- `overlapping_clusters`
  - recognition that the problem is geometric and ambiguous, not predictive GPA modeling
- `outlier_dominated`
  - clear identification that a small fraction of extreme totals visually dominates the main relationship
- `interaction_effects`
  - visual confirmation that the effect of channel depends on time of day

For `concept_drift`, the visual reviewer helps only if given the right plot pack. That is why this role must be allowed to request additional plots rather than passively accept whatever the analyst happened to make.

#### Method Critic

This role primarily addresses **wrong frame** and **failure to test structural alternatives**.

It would help on:

- `concept_drift`
  - by asking why pooled models are being trusted without pre/post comparison
- `interaction_effects`
  - by challenging an additive conclusion after interaction-like EDA
- `outlier_dominated`
  - by insisting on robust-vs-naive comparison rather than stopping at diagnostics
- `multimodal`
  - by asking why a single-regression workflow is being used before target-shape interpretation

This role is especially important because many wrong runs were not careless. They were coherent analyses of the wrong question.

#### Claim Verifier

This role primarily addresses **under-completed inference**.

It would help on:

- `mnar`
  - by forcing the final report to explicitly decide among MCAR / MAR / MNAR
- `spurious_correlation`
  - by requiring an explicit raw-vs-controlled collapse demonstration
- `multicollinearity`
  - by requiring an explicit remediation recommendation
- `interaction_effects`
  - by requiring a clear statement that the additive model underperforms or does not explain the key pattern

Many partial runs already contained most of the right ingredients. What they lacked was a final pass that checked whether the report had actually closed the benchmark's core claim.

### Recommended loop order

The simplest useful workflow is:

1. hypothesis generation
2. main analysis
3. visual review
4. method critique
5. targeted revision
6. claim verification

This is better than one stronger prompt because the roles have different priors:

- the hypothesis generator is rewarded for breadth
- the analyst is rewarded for execution
- the visual reviewer is rewarded for noticing structure
- the critic is rewarded for finding what was not ruled out
- the verifier is rewarded for proof completeness

Those incentives are exactly what the current single-pass workflow lacks.

## Bottom Line

The models did not simply "miss the answer." They followed the wrong meta-strategy:

- assume supervised prediction
- trust pooled modeling
- interpret failure as lack of signal

For these two datasets, the real signal is structural, not marginal. That is the isolated failure mode.

## Partial Runs Review

The remaining non-solved runs do not all fail for the same reason.

They split into three main buckets:

1. structural miss before or during modeling
2. correct analysis but incomplete final inference
3. near-solved analysis with an actionability gap

### Partial-run summary

| dataset | Claude | Codex | dominant failure mode |
| --- | --- | --- | --- |
| `interaction_effects` | partial | wrong | saw important variables but under-proved or missed the interaction |
| `mnar` | partial | partial | strong missingness analysis, but undercalled the MNAR mechanism |
| `multicollinearity` | solved | partial | diagnosis was right, remediation recommendation was missing |
| `multimodal` | partial | partial | wrong framing: regression before understanding target shape |
| `outlier_dominated` | partial | partial | wrong objective: diagnostics without the key robust-vs-OLS comparison |
| `spurious_correlation` | solved | partial | correct concept, incomplete controlled demonstration |

## Failure Mode A: Structural Miss Before Modeling

These are the closest to the failures on `overlapping_clusters` and `concept_drift`.

The agent starts a generic supervised workflow, but the benchmark is actually testing structural understanding first.

### `multimodal`

The generator is explicitly a three-component rent mixture:

- means near `800`, `1600`, and `3200`
- different component scales
- a target distribution that should be understood as a mixture before regression

But both agents treated `monthly_rent_usd` as an ordinary supervised target and proceeded directly to regression model comparison.

This is the same family as `overlapping_clusters`:

- the underlying structure is in the target geometry
- standard regression can still look competent
- the benchmark expects the agent to identify the structure first

### `outlier_dominated`

The generator only corrupts about 5% of `order_total_usd`, but those errors are enormous:

- totals get large positive or negative offsets
- the point is to show how a small fraction of extreme values distorts ordinary least squares

Claude diagnosed bad OLS but stopped before comparing a robust estimator.

Codex drifted even farther by treating the main problem as return prediction rather than robust fitting of order totals.

This is another structural miss:

- the key question is not "what predicts the obvious target best?"
- the key question is "how does a fragile estimator behave under contamination?"

### `interaction_effects`

The generator includes both weak main effects and a strong `channel_score * time_of_day_hour` term.

Claude saw this in EDA and even called it the dominant pattern, but then selected a plain additive logistic model and concluded interactions did not materially improve performance.

Codex similarly identified the two right variables but still concluded that the additive model was sufficient.

This is closest to `concept_drift`:

- the real signal is conditional
- a simpler pooled or additive summary weakens it
- the agent then mistakes "interaction not strongly proven" for "interaction not really there"

## Failure Mode B: Correct Analysis, Incomplete Final Inference

These runs are not primarily wrong-framing failures.

The agent usually did the hard work, but did not close the loop in the exact way the benchmark required.

### `mnar`

The generator makes missingness a direct function of true income:

- higher-income respondents are more likely to have missing reported income

Both harnesses investigated missingness carefully and correctly rejected MCAR-style thinking.

The issue was the final mechanism call:

- Claude explicitly labeled the pattern as `MAR`
- Codex strongly described systematic missingness but did not explicitly and confidently name `MNAR`

So the failure was not weak analysis. The failure was stopping one inferential step short of the benchmark's core label.

### `spurious_correlation` for Codex

Codex identified the shared confounder correctly:

- temperature
- shared seasonality
- no direct causal claim

But it did not explicitly present the key before/after controlled demonstration showing that the ice-cream-sales and drowning relationship largely disappears once temperature is controlled for.

This is a proof gap, not a conceptual misunderstanding.

## Failure Mode C: Actionability Gap

### `multicollinearity` for Codex

Codex correctly diagnosed:

- strong predictor correlation
- unstable coefficient interpretation
- predictive performance can remain good even under collinearity

The only real miss was the remediation recommendation.

Regularized models were tested, but the report framed them as not needed for predictive accuracy instead of recommending them, or another remedy, as a response to multicollinearity itself.

This is essentially a near-solved run that missed the actionable prescription.

## Cross-Dataset Pattern

Taken together, the benchmark's non-solved runs suggest two larger systemic weaknesses.

### 1. The agents are strongest when the benchmark insight aligns with the obvious predictive task

They do well when:

- the target is obvious
- the right model family is conventional
- the benchmark insight is visible in standard validation or diagnostics

They degrade when:

- the real task is discovery rather than prediction
- the key structure is in interactions, mixtures, confounding, or estimator fragility
- the correct conclusion requires questioning the default modeling frame

### 2. Even when the agents see the pattern, they often stop short of the benchmark-critical final step

Typical examples:

- seeing systematic missingness but not naming `MNAR`
- identifying a confounder but not showing the controlled collapse explicitly
- diagnosing multicollinearity but not recommending a remedy
- seeing an interaction in EDA but not proving it in model comparison

So there are really two separate benchmark risks:

- wrong frame
- under-completed inference

## Updated Mitigation

The broader benchmark review reinforces the same conclusion:

- the benchmark should move from a single-pass prompt to a staged multi-agent review loop

### 1. Use a team, not a single analyst

The minimum effective team is:

- hypothesis generator
- analyst
- visual reviewer
- method critic
- claim verifier

This directly addresses the three recurring weaknesses surfaced by the benchmark:

1. premature task framing
2. failure to test structural alternatives
3. failure to complete the last inferential step

### 2. Give the visual reviewer real image access

This is important enough to call out separately.

The benchmark should not treat plots as report decorations. It should treat them as reasoning inputs.

That means:

- pass a canonical plot pack to the visual reviewer
- let the reviewer inspect images directly
- let the reviewer request additional targeted plots

Without that, the team will continue to miss visually obvious structure such as:

- multimodality
- overlap vs clean separation
- dominance of a few outliers
- interaction surfaces

### 3. Add a proof-completion checkpoint before finalization

Before the report is accepted, require a short proof checklist:

- interaction demonstrated against an additive baseline
- confounding demonstrated with a controlled collapse
- missingness mechanism explicitly classified
- multicollinearity remediation explicitly recommended
- robustness shown through naive-vs-robust comparison
- temporal instability shown through segmented or rolling relationships

This checkpoint is what converts a strong but partial run into a solved run.

### 4. Keep lightweight guardrails by dataset family

Even with a team, it helps to encode a few family-specific expectations:

- temporal data: pre/post or rolling relationship checks
- clustering or mixture-like data: geometry or target-distribution review
- missingness problems: explicit MCAR / MAR / MNAR positioning
- confounding problems: at least one controlled analysis
- robustness problems: naive vs robust estimator comparison

## Updated Bottom Line

The benchmark's misses are not all the same, but they are consistent with one architectural problem:

- a single-pass analyst is being asked to do hypothesis generation, analysis, visual interpretation, self-critique, and proof completion all at once

That setup works when the benchmark insight is aligned with the obvious predictive task.

It breaks when success requires:

- questioning the default framing
- seeing structural patterns in plots
- proving the right claim against a plausible alternative

So the right mitigation is not just a better prompt.

It is a small team with distinct roles:

1. hypothesis generator
2. analyst
3. visual reviewer
4. method critic
5. claim verifier

Those roles map directly onto the observed failures and together explain how to prevent nearly all of the non-solved runs.
