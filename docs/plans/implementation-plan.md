# Implementation Plan: Decision-First Scoring

## Goal

Replace the current generic point-based scorer with the decision-first evaluation model described in [scoring_plan.md](./scoring_plan.md), without breaking the benchmark harness during the transition.

The end state is:

- dataset-specific evaluation contracts
- deterministic verdict computation
- no arbitrary total score as the primary metric
- reporting based on solve rate, wrong-answer rate, coverage, oracle attainment, and efficiency

## Rollout Strategy

Do this in phases. Do not rewrite all 20 datasets and the entire reporting stack in one shot.

Each phase should have:

- a narrow code surface
- clear validation criteria
- backward-compatible behavior where practical

## Phase 1: Define the New Evaluation Model

### Objective

Lock the data model and scoring semantics before touching the full scorer.

### Scope

- Add new evaluation dataclasses
- Define verdict semantics
- Decide where oracle metrics live
- Keep the old scorer operational during this phase

### Deliverables

- `Criterion`
- `OracleMetric`
- `EvaluationSpec`
- `DatasetOutcome`
- deterministic verdict rules:
  - `solved`
  - `partial`
  - `failed`
  - `wrong`

### Files

- `datasets/registry.py`
- `reviewer/scorer.py`
- `tests/test_registry.py`
- `tests/test_scorer.py`

### Implementation Notes

- Prefer adding new structures alongside the existing ones first.
- Do not remove the old `ScoreResult` until the new path is proven.
- Add small helper functions for:
  - required coverage
  - supporting coverage
  - forbidden-claim handling
  - oracle normalization

### Exit Criteria

- New dataclasses exist and are tested
- Verdict computation is deterministic
- Old benchmark path still runs

## Phase 2: Build the New Reviewer Contract

### Objective

Change the reviewer from free-form scoring to structured criterion extraction.

### Scope

- Replace the generic rubric prompt with a dataset-specific contract prompt
- Require evidence for each criterion judgment
- Parse structured reviewer output

### Deliverables

- new prompt builder
- new response schema
- robust parser for reviewer JSON

### Files

- `reviewer/rubric.py`
- `reviewer/scorer.py`
- `tests/test_rubric.py`
- `tests/test_scorer.py`

### Implementation Notes

- The LLM should judge only:
  - `must_have`
  - `supporting`
  - `forbidden`
- Deterministic Python should compute the final outcome.
- Keep prompt format strict and machine-friendly.

### Exit Criteria

- Reviewer output is parseable
- Missing core insight can no longer score as a high-quality result
- Parser failures are handled cleanly

## Phase 3: Pilot on 3 Representative Datasets

### Objective

Prove the new scoring model on a small, diverse subset before full migration.

### Pilot Datasets

- `simpsons_paradox`
- `pure_noise`
- `deterministic_linear`

### Why These Three

- `simpsons_paradox` tests discovery and trap handling
- `pure_noise` tests false-positive prevention
- `deterministic_linear` tests oracle-relative quantitative scoring

### Deliverables

- full evaluation contracts for the 3 pilot datasets
- scorer logic validated against those contracts
- updated tests with realistic pass/fail examples

### Files

- `datasets/registry.py`
- `reviewer/scorer.py`
- `tests/test_registry.py`
- `tests/test_scorer.py`

### Validation

- Simpson's paradox result that misses reversal must be `failed` or `wrong`, never `solved`
- Pure noise result that claims strong signal must be `wrong`
- Deterministic linear result that recovers the equation must be `solved` with near-1.0 oracle attainment

### Exit Criteria

- Pilot datasets work end-to-end
- The new scorer is clearly better than the old one on these cases

## Phase 4: Integrate Reporting and Serialization

### Objective

Make benchmark outputs usable with the new scorecard format.

### Scope

- update `score.json`
- update benchmark report generation
- expose the new metrics in a readable layout

### Deliverables

- structured `score.json` schema
- report sections for:
  - verdict
  - required/supporting coverage
  - oracle attainment
  - fatal errors
  - efficiency

### Files

- `run_benchmark.py`
- `reviewer/report.py`
- `tests/test_report.py`

### Implementation Notes

- During migration, prefer dual-writing if it reduces breakage:
  - old fields for compatibility
  - new structured fields as source of truth
- Do not invent a new total score just for the report.

### Exit Criteria

- benchmark report renders cleanly
- report comparison is readable without a single scalar total
- existing benchmark workflow still completes

## Phase 5: Migrate the Remaining Datasets in Batches

### Objective

Scale the contract system across the full registry without losing consistency.

### Suggested Batch Order

1. Discovery / diagnostic:
   - `anscombes_quartet`
   - `heteroscedasticity`
   - `mnar`
   - `spurious_correlation`
   - `multimodal`
   - `concept_drift`
2. Predictive / modeling:
   - `quadratic`
   - `high_dim_sparse`
   - `interaction_effects`
   - `lognormal_skew`
   - `multicollinearity`
   - `outlier_dominated`
3. Classification / imbalance:
   - `class_imbalance`
4. Clustering:
   - `well_separated_clusters`
   - `overlapping_clusters`
5. Specialized / temporal:
   - `time_series_seasonality`
   - `survival_censored`

### Deliverables

- evaluation contract for every dataset
- registry tests that enforce contract completeness
- family-specific oracle logic where applicable

### Files

- `datasets/registry.py`
- `tests/test_registry.py`
- `tests/test_scorer.py`

### Implementation Notes

- Keep contract authoring consistent within each dataset family.
- Do not force oracle metrics onto datasets where they are not meaningful.
- Every dataset should have:
  - at least one `must_have`
  - at least one trap or forbidden criterion where appropriate
  - supporting criteria only if they add information

### Exit Criteria

- All registry entries have evaluation contracts
- No dataset still depends on the old generic rubric

## Phase 6: Add Efficiency Metrics

### Objective

Measure how expensive it was to arrive at the answer without polluting correctness scoring.

### Scope

- wall time
- token usage where available
- tool call counts
- optional time to first correct hypothesis later

### Deliverables

- efficiency field in `DatasetOutcome`
- report summaries for cost per solved dataset

### Files

- `run_benchmark.py`
- `reviewer/scorer.py`
- `reviewer/report.py`
- tests as needed

### Implementation Notes

- Efficiency should be reported separately, not blended into correctness.
- Start with metrics already available from logs and traces.
- Do not block earlier phases on perfect token accounting.

### Exit Criteria

- efficiency numbers are present and stable
- report can compare models on cost per solve

## Phase 7: Add Paired Comparison Statistics

### Objective

Make prompt and agent comparisons statistically defensible.

### Scope

- paired win/loss/tie counts
- confidence intervals for solve rate and wrong-answer rate
- repeated seeds if needed

### Deliverables

- comparison summary in the report
- clear benchmark protocol for repeated runs

### Files

- `run_benchmark.py`
- `reviewer/report.py`
- possibly new helper module for statistics

### Implementation Notes

- Compare agents on the same dataset instances.
- Add repeated dataset seeds only after the scorer itself is stable.
- Keep this phase downstream from core scorer migration.

### Exit Criteria

- small prompt changes can be compared without relying on eyeballed totals
- report shows uncertainty, not just point estimates

## Phase 8: Optional Style / Elegance Evaluation

### Objective

Capture subjective quality without contaminating the primary benchmark.

### Scope

- pairwise preference on solved outputs only
- narrow prompt for clarity and elegance

### Deliverables

- optional style comparison module
- style win-rate reporting

### Implementation Notes

- This is explicitly optional.
- Do not mix style into solve rate or oracle attainment.
- Only compare analyses that already count as correct.

### Exit Criteria

- style is reported as a side metric only

## Dependency Order

The phases depend on each other in this order:

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7
8. Phase 8

Do not start Phase 5 before the Phase 3 pilot works. Do not start Phase 7 before the core scorer and report format are stable.

## Testing Strategy by Phase

### Early phases

- unit tests for verdict logic
- unit tests for oracle normalization
- prompt/response parser tests

### Middle phases

- registry integrity tests
- report rendering tests
- score serialization tests

### Later phases

- integration run on pilot datasets
- re-score known historical outputs and verify expected verdicts

## Definition of Done

This implementation is done when:

- all datasets use evaluation contracts
- the generic 7-dimension rubric is removed from the scoring path
- reports lead with solve rate and wrong-answer rate
- modeling tasks expose oracle-relative quality where meaningful
- efficiency is reported separately
- benchmark comparisons no longer depend on arbitrary point totals
