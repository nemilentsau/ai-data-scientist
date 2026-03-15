# Plan: Replace Arbitrary Scores with Decision-First Evaluation

## Context

The current `0-35` rubric is not meaningful. The planned `0-100` checkpoint rewrite is better structured, but it still has the same core problem: it collapses different kinds of performance into one made-up number.

For this benchmark, the first question is not "did the model get 45 or 42?" It is:

1. Did it solve the dataset correctly?
2. If yes, how complete and well-supported was the solution?
3. If modeling quality matters, how close did it get to the best achievable answer?
4. How much time / cost did it take?
5. Only after correctness is fixed: was the solution elegant?

That means the benchmark should return a **scorecard**, not a single scalar.

## Design Principles

1. **Primary metric must be binary or near-binary.**
   The benchmark exists to tell whether the agent solved the statistical problem, not whether it looked polished.

2. **Only use interpretable scales.**
   Use solve rate, evidence coverage, oracle attainment, time, cost, false-positive rate. Avoid arbitrary totals.

3. **Do not force one metric across all dataset types.**
   Some datasets are about detecting a paradox. Some are about fitting the right model. Some are about avoiding a false conclusion. These should not all be reduced to the same point scale.

4. **Keep subjective judgment out of the primary leaderboard.**
   Aesthetics can matter, but only as a separate tiebreaker or side metric.

5. **Use the LLM reviewer only for structured extraction, not free-form scoring.**
   The model can judge whether a criterion was satisfied and cite evidence. Deterministic code should map that into the final result.

## Proposed Output Per Dataset

Each dataset should produce this structured result:

```python
@dataclass(frozen=True)
class DatasetOutcome:
    dataset_name: str
    agent: str
    verdict: str                  # "solved" | "partial" | "failed" | "wrong"
    core_insight_pass: bool
    required_coverage: float      # 0.0 - 1.0
    supporting_coverage: float    # 0.0 - 1.0
    oracle_attainment: float | None   # 0.0 - 1.0 when a quantitative optimum exists
    fatal_errors: list[str]
    efficiency: dict[str, float]      # wall_time_s, tokens, tool_calls, etc.
    summary: str
    raw_response: str
```

These fields are interpretable:

- `verdict`: was the problem solved?
- `required_coverage`: how much of the necessary work was done?
- `supporting_coverage`: how complete / well-supported was the solution?
- `oracle_attainment`: how close the result was to the best possible answer
- `efficiency`: how expensive the solve was

## Dataset Spec: Replace "Checkpoints with Weights" with "Evaluation Contract"

Each dataset should define an explicit contract:

```python
@dataclass(frozen=True)
class Criterion:
    id: str
    description: str
    verification_hint: str = ""

@dataclass(frozen=True)
class OracleMetric:
    name: str                     # "r2", "f1", "ari", "changepoint_error"
    direction: str                # "higher_is_better" | "lower_is_better"
    baseline_value: float
    oracle_value: float
    tolerance: float | None = None

@dataclass(frozen=True)
class EvaluationSpec:
    task_family: str              # "discovery" | "predictive" | "clustering" | "specialized"
    must_have: list[Criterion]    # all needed for SOLVED
    supporting: list[Criterion]   # quality / completeness only
    forbidden: list[Criterion]    # if triggered, result becomes WRONG or FAILED
    oracle_metric: OracleMetric | None = None
```

This keeps the useful part of the checkpoint idea, but removes the fake precision of point totals.

## Verdict Logic

Scoring should be rule-based:

1. If the agent makes a confident forbidden claim, the verdict is `wrong`.
2. If all `must_have` criteria are satisfied and no fatal error is present, the verdict is `solved`.
3. If some but not all `must_have` criteria are satisfied, the verdict is `partial`.
4. Otherwise, the verdict is `failed`.

Important distinction:

- `failed`: did not reach the answer
- `wrong`: reached a materially incorrect conclusion or fell into the trap the dataset was built to expose

That distinction matters more than a `26/100` versus `34/100`.

## Family-Specific Metrics

Do not use the same secondary metric for every dataset family.

### 1. Discovery / Diagnostic tasks

Examples: `simpsons_paradox`, `pure_noise`, `mnar`, `heteroscedasticity`, `spurious_correlation`, `concept_drift`

Use:

- `verdict`
- `required_coverage`
- `supporting_coverage`
- `false_positive` / `fatal_errors`

Do **not** invent an oracle model metric when the real question is pattern recognition.

### 2. Predictive / Modeling tasks

Examples: `deterministic_linear`, `quadratic`, `high_dim_sparse`, `interaction_effects`, `lognormal_skew`

Use:

- `verdict`
- `required_coverage`
- `oracle_attainment`

`oracle_attainment` should be normalized against a baseline:

- For higher-is-better metrics:
  - `(agent_metric - baseline) / (oracle - baseline)`
- For lower-is-better metrics:
  - `(baseline - agent_metric) / (baseline - oracle)`

Clip to `[0, 1]`.

This makes the scale interpretable:

- `0.0`: no better than baseline
- `1.0`: matched oracle
- `0.8`: achieved 80% of the possible gain over baseline

### 3. Clustering / Segmentation tasks

Examples: `well_separated_clusters`, `overlapping_clusters`, `concept_drift`

Use ground-truth-aware metrics:

- ARI / NMI for clustering
- change-point localization error for drift
- cluster-count correctness if that is the central target

Again, report these as separate interpretable metrics, not folded into a universal point score.

### 4. Specialized Method tasks

Examples: `survival_censored`, `time_series_seasonality`

These need:

- correct method choice as a `must_have`
- method-specific quantitative quality only if it is truly meaningful

Example: using Kaplan-Meier or Cox is a correctness requirement; a c-index or decomposition quality metric can be secondary.

## Example Contracts

### Simpson's Paradox

Must-have:

- compare aggregate treatment effect
- compare within-group treatment effect
- explicitly state that direction reverses
- identify the grouping variable as confounder
- give the correct practical conclusion

Supporting:

- quantify effect sizes
- visualize the reversal
- explain mechanism cleanly

Forbidden:

- final conclusion based only on aggregate trend
- claim no confounding

Result:

- `solved` if all must-haves are present
- `wrong` if the agent confidently recommends the aggregate-only conclusion

### Pure Noise

Must-have:

- conclude there is no meaningful signal
- show evidence for weak predictive power / non-significance
- avoid reporting a specific relationship as real

Supporting:

- test multiple candidate relationships
- use a visualization that shows lack of structure

Forbidden:

- claim a strong relationship from noise

### Deterministic Linear

Must-have:

- identify the relationship as linear
- recover slope within tolerance
- recover intercept within tolerance
- report near-perfect fit

Supporting:

- write the equation explicitly
- identify irrelevant noise columns
- avoid overcomplicated models

Oracle metric:

- `r2` or parameter error against the known generating process

## Comparison Between Models

The leaderboard should not be a single "total score".

Use this order:

1. **Primary**: solve rate
2. **Guardrail**: wrong-answer rate
3. **Secondary**: mean required coverage on solved or partial tasks
4. **Secondary**: mean oracle attainment on tasks where it exists
5. **Efficiency**: median wall time / tokens / tool calls per solved dataset
6. **Style**: pairwise preference win rate, reported separately

If a single ordering is needed, use a lexicographic tuple:

```python
(
    solve_rate,
    -wrong_rate,
    mean_oracle_attainment,
    mean_supporting_coverage,
    -median_cost_per_solve,
)
```

That is still much more meaningful than a weighted point total because every component has a clear interpretation.

## Aesthetics / Elegance

This should be explicitly separated from correctness.

Recommended approach:

- only compare aesthetics on outputs that already count as `solved`
- use pairwise preference judgments instead of absolute `1-5` ratings
- ask a narrow question such as:
  - "Which solved analysis is clearer, more concise, and more methodologically elegant?"

Report this as:

- style win rate
- or percentage of pairwise preferences

Do not mix it into the primary benchmark score.

## Statistical Rigor for Benchmark Comparisons

If this benchmark will guide prompt and agent design, do not compare models on one run per dataset and eyeball totals.

Use a paired evaluation design:

1. Same dataset instance for all agents in a comparison
2. Multiple generated seeds per dataset family where useful
3. Multiple agent runs if agent behavior is stochastic
4. Paired bootstrap or sign-test style reporting for solve-rate differences

Minimum useful reporting:

- solve rate with confidence interval
- wrong-answer rate with confidence interval
- paired win / loss / tie counts by dataset

Without this, differences from prompt tweaks can easily be noise.

## Reviewer Role

The LLM reviewer should return structured judgments plus evidence, for example:

```json
{
  "must_have": {
    "reversal_stated": {
      "status": "hit",
      "evidence": "The analysis states that treatment A appears worse overall but better in every subgroup."
    }
  },
  "supporting": {
    "visualized_reversal": {
      "status": "miss",
      "evidence": ""
    }
  },
  "forbidden": {
    "aggregate_only_conclusion": {
      "status": "miss",
      "evidence": ""
    }
  },
  "summary": "Correctly identifies Simpson's paradox, but the evidence presentation is incomplete."
}
```

Then deterministic Python code computes:

- `verdict`
- coverage metrics
- oracle attainment
- final report fields

This sharply reduces judge variance.

## Files to Modify

1. `datasets/registry.py`
   Add `Criterion`, `OracleMetric`, `EvaluationSpec`, and one evaluation contract per dataset.

2. `reviewer/scorer.py`
   Replace total-score logic with verdict + coverage + oracle-attainment computation.

3. `reviewer/rubric.py`
   Replace generic rubric formatting with dataset-contract prompt formatting.

4. `reviewer/report.py`
   Report solve rate, wrong-answer rate, coverage, oracle attainment, and efficiency.

5. `run_benchmark.py`
   Update `score.json` serialization to store structured outcomes instead of a point total.

6. `tests/test_registry.py`
   Validate every dataset has must-have criteria, unique IDs, and coherent oracle specs where present.

7. `tests/test_scorer.py`
   Test verdict computation, forbidden-claim handling, coverage calculation, and oracle normalization.

8. `tests/test_report.py`
   Update report expectations for the new scorecard format.

## Implementation Order

1. Define the new evaluation data model in `datasets/registry.py`.
2. Write evaluation contracts for 3 representative datasets first:
   `simpsons_paradox`, `pure_noise`, `deterministic_linear`.
3. Rewrite scorer logic around `verdict`, coverage, and oracle attainment.
4. Update the report to show scorecards instead of totals.
5. Extend the contract format to the remaining datasets.
6. Add paired-comparison summary metrics and confidence intervals later, after the core scorer is stable.

## Verification

1. For Simpson's paradox, an analysis that misses the reversal must never be `solved`, no matter how polished it is.
2. For pure noise, confidently claiming a strong pattern must produce `wrong`.
3. For deterministic linear, recovering the true equation should yield `solved` and near-1.0 oracle attainment.
4. `uv run pytest tests/ -v`

## Bottom Line

Keep per-dataset evaluation contracts. Drop arbitrary totals. Make the benchmark answer:

- Did the agent solve it?
- How complete was the solution?
- How close was the model to the best achievable answer?
- How expensive was the solve?
- Which solved output was more elegant?

Those are metrics you can actually reason about when comparing prompts, models, and agent designs.
