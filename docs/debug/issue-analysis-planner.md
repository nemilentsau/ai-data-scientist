# Issue: `analysis_planner` over-scopes work and hands the executor an expensive plan

## Status

Open

## Context

- Run: `uv run python - <<'PY' ... run_workflow(...) ... PY`
- Run directory: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_103928`
- Planning artifacts:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_103928/artifacts/planning/analysis_plan.md`
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_103928/artifacts/planning/experiment_plan.json`
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_103928/artifacts/planning/hypotheses.json`

## Observed Behavior

`analysis_planner` successfully writes its required artifacts, but it creates an unnecessarily heavy plan for a first-pass smoke workflow.

The resulting plan includes seven experiments, several of which are redundant or more expensive than needed for the stated framing checks.

## Evidence

`experiment_plan.json` includes:

- `EXP-DIST` for distributions
- `EXP-CORR` for pairwise correlation analysis
- `EXP-NONLIN` for MI plus shuffled-target baseline and LOWESS plots
- `EXP-ANOVA` for salary-band group comparison
- `EXP-VIF` for multicollinearity
- `EXP-MODEL` for Random Forest with 5-fold CV, dummy baseline, and permutation importance
- `EXP-NOISE` for a 200-shuffle permutation null distribution on model R-squared

The framing required checks only call for:

- pairwise correlations
- non-linear relationship check
- salary-band difference check
- overall predictive fit warning
- multicollinearity check

The extra permutation-noise confirmation step is not required by the framing contract and materially increases executor cost.

## Root Cause Hypothesis

The planner prompt is too open-ended.

- It tells the agent to plan evidence and checks, but it does not bound scope.
- It does not tell the planner to optimize for one-invocation executability.
- It does not distinguish required checks from optional confirmations.
- It does not discourage heavy methods when lighter methods would satisfy the same question.

As a result, the planner optimizes for analytical thoroughness rather than bounded execution.

## Proposed Solution

Tighten the planner contract so it:

1. Plans the smallest sufficient experiment set.
2. Maps every experiment to a required framing check or material framing risk.
3. Avoids optional confirmation work by default.
4. Targets 3 to 5 experiments total.
5. Uses at most one model-based experiment.
6. Avoids heavy permutation tests, bootstraps, and simulation-heavy null distributions unless explicitly required.

## Validation Plan

1. Update `prompts/active/analysis-planner.md`.
2. Rerun the same isolated `pure_noise` workflow smoke.
3. Confirm `experiment_plan.json` shrinks to a smaller bounded set.
4. Confirm the executor no longer expands into a large long-running analysis program just to satisfy planning scope.
