# Issue: `method_critic` over-reads the artifact set and becomes the new smoke-test bottleneck

## Status

Open

## Context

- Run: `uv run python - <<'PY' ... run_workflow(...) ... PY`
- Run directory: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_105008`
- Invocation: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/claude-workflow-smoke-20260406_105008/invocations/method-critic-0001`

## Observed Behavior

The workflow now clears `task_framer`, `analysis_planner`, and `analysis_executor`. The next timeout happens while `method_critic` is still gathering context.

`method_critic` reads many high-volume artifacts, including plot images, before writing any critique output.

## Evidence

The trace shows `method_critic` reading:

- `framing.json`
- `analysis_plan.md`
- `experiment_plan.json`
- `hypotheses.json`
- `findings.json`
- `analysis_report.md`
- multiple stats JSON artifacts
- multiple plot PNG files

No `critique.md` write appears before the wrapper timeout.

## Root Cause Hypothesis

The critic prompt is too open-ended.

- It says to read the full published artifact set.
- It does not define an order of operations.
- It does not tell the role to prioritize the highest-signal artifacts.
- It does not tell the role to inspect plots only when needed for a methodological point.

As a result, the critic is thorough but too expensive for a first-pass smoke run.

## Proposed Solution

Tighten the critic contract so it:

1. Starts with `analysis_report.md`, `findings.json`, stats JSON artifacts, and planning/framing context.
2. Opens plot images only when a methodological concern actually requires them.
3. Writes a short blocking-issues critique instead of exhaustively reviewing every artifact.

Also tighten `visual_critic` in the complementary direction:

1. Start with plot images plus `analysis_report.md`.
2. Use stats JSON only when needed for context.

## Validation Plan

1. Update `prompts/active/method-critic.md`.
2. Update `prompts/active/visual-critic.md`.
3. Rerun the isolated `pure_noise` smoke.
4. Confirm `method_critic` writes `critique.md` without exhaustively opening every plot first.
