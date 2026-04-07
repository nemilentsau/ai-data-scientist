# Issue: `analysis_executor` expands the plan into a heavy long-running execution pass

## Status

Open

## Context

- Run: `uv run python run_benchmark.py --config claude-multiagent-v1 --datasets pure_noise --skip-generate --skip-score --skip-import`
- Invocation: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/runs/claude-multiagent-v1/pure_noise/invocations/analysis-executor-0001`
- Trace: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/runs/claude-multiagent-v1/pure_noise/invocations/analysis-executor-0001/trace/trace.jsonl`

## Observed Behavior

`analysis_executor` successfully receives the expected published artifacts, starts execution, and writes a large local analysis program plus several intermediate outputs.

The problem is that it takes too long to complete a bounded smoke run, so the workflow times out before the role publishes its required artifacts.

## Evidence

- Fresh isolated run:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_103928`
- Trace:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_103928/invocations/analysis-executor-0001/trace/trace.jsonl`
- Reads the full planning bundle, framing, profile artifacts, and a bounded preview of `dataset.csv`.
- Creates output directories with `mkdir -p plots stats tables`.
- Writes a large `run_analysis.py` into the workspace.
- Intermediate outputs appear in the workspace before timeout, including:
  - `plots/distributions.png`
  - `plots/correlation_heatmap.png`
  - `plots/mi_scores.png`
  - `plots/scatter_lowess_top3.png`
  - `plots/boxplot_salary_band.png`
  - `plots/feature_importances.png`
  - `tables/correlation_matrix.csv`
  - `tables/mi_scores.csv`
  - `tables/anova_results.csv`
  - `tables/vif_scores.csv`
  - `tables/cv_scores.csv`
- The wrapper run still exits with:
  - `RESULT=timeout`
- Required terminal artifacts are still missing:
  - `analysis_report.md`
  - `findings.json`
  - `claim_evidence_map.json`
  - any stats JSON files under `stats/`

## Root Cause Hypothesis

The executor prompt is still too permissive about execution scope.

- It tells the agent what artifacts must exist, but it does not tell it to minimize runtime aggressively.
- It does not tell the agent to simplify an over-expensive plan when a cheaper method would answer the same question.
- It does not bias toward a short script or direct command sequence.

The result is a large monolithic script that starts making progress but cannot reliably finish within a bounded smoke run.

## Proposed Solution

1. Tighten `analysis_executor` into a bounded execution contract.
2. Instruct it to:
   - favor minimal sufficient computation over exhaustive confirmation
   - prefer one short script or direct commands over a large program
   - simplify obviously expensive plan items and record the simplification in `analysis_report.md`
   - start `analysis_report.md` early and finish required outputs before optional work
3. Keep required artifact schemas explicit.
4. Pair this with a tighter planner so the executor is not handed unnecessary heavy experiments.

## Validation Plan

1. Update the planner and executor prompts.
2. Rerun the same `pure_noise` smoke test.
3. Confirm the trace shows:
   - a smaller plan from `analysis_planner`
   - faster execution with fewer heavy experiments
4. Confirm the executor finishes and writes:
   - `analysis_report.md`
   - `findings.json`
   - `claim_evidence_map.json`
   - stats JSON outputs
5. Confirm canonical outputs appear under:
   - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/.../artifacts/analysis/`
