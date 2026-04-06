# Issue: Claude `task_framer` never writes `framing.json`

## Status

Open

## Context

- Run: `uv run python run_benchmark.py --config codex-multiagent-v1 --datasets pure_noise --skip-generate --skip-import`
- Invocation: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/runs/codex-multiagent-v1/pure_noise/invocations/task-framer-0001`
- Trace: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/runs/codex-multiagent-v1/pure_noise/invocations/task-framer-0001/trace/trace.jsonl`

## Observed Behavior

The Claude-backed `task_framer` read the published profile artifacts, then switched into repo-wide contract discovery and never wrote `framing.json`.

## Evidence

- Reads the intended inputs first:
  - `schema.json`, `column_summary.csv`, `null_summary.csv`, `sample_rows.csv` in trace lines 1-4.
- Then starts repo investigation instead of writing output:
  - repo-wide `**/*.json` glob in trace line 5
  - grep for `framing` in trace line 6
  - search for existing `framing.json` in trace line 7
- Continues reading runtime code, tests, specs, and planning notes to infer contract:
  - tests in trace line 12
  - design spec in trace lines 23-24
  - `refactor.md` in trace lines 28-29
- Confirms the file does not exist, but still never writes it:
  - workspace and output checks in trace lines 31-34
- Escalates to subagent search at trace line 36.
- No `Write` or `Edit` event appears anywhere in the trace.

## Root Cause Hypothesis

The role contract is underspecified for live execution.

- The prompt only says to write `framing.json`, but does not define the schema or exact write semantics:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/prompts/active/task-framer.md`
- The rendered prompt provides artifact paths, but not an authoritative output contract:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/ai_data_scientist/orchestration/prompts.py`
- The runtime expects `framing.json` to be published, but does not give the agent a self-contained schema:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/ai_data_scientist/orchestration/runner.py`

Given broad tool freedom, the model uses the repository as a substitute contract source.

## Proposed Solution

1. Make the `task_framer` prompt self-contained.
2. Include the exact minimum JSON schema in the prompt.
3. State the exact write location: write `framing.json` in the current working directory.
4. Forbid repo exploration outside declared inputs:
   - do not read tests
   - do not read specs
   - do not read prior runs
   - do not search for example outputs
5. If feasible in the adapter, restrict `task_framer` tool scope to local invocation inputs and local workspace.

## Validation Plan

1. Rerun the same `pure_noise` smoke test with Claude.
2. Confirm trace contains:
   - reads of published inputs only
   - one write of `framing.json`
   - no repo-wide `Glob` or `Grep`
3. Confirm the published artifact exists under:
   - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/runs/.../artifacts/framing/framing.json`

