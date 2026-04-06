# Issue: Codex `task_framer` succeeds, but only after path and contract discovery detours

## Status

Open

## Context

- Debug run: isolated Codex `task_framer` smoke test on `pure_noise`
- Invocation: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/codex-task-framer-smoke-20260406_101213/invocations/task-framer-0001`
- Trace: `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/codex-task-framer-smoke-20260406_101213/invocations/task-framer-0001/trace/trace.jsonl`
- Output written successfully:
  - `/Users/andreinemilentsau/Projects/ai-data-scientist/results/debug/codex-task-framer-smoke-20260406_101213/invocations/task-framer-0001/workspace/framing.json`

## Observed Behavior

Codex eventually wrote a valid `framing.json`, but it did not execute the role cleanly.

It first failed to resolve the published input paths from inside the invocation workspace, then read tests, specs, and planning notes to reconstruct the minimum schema.

## Evidence

- Early path resolution attempts fail because the role tries repo-relative paths from the invocation workspace:
  - trace lines 9-18
- Codex then explores the local directory structure to rediscover the real input paths under `../input/...`:
  - trace lines 19-25
- After path recovery, it still reads repo sources to infer the minimum contract:
  - design spec in trace line 58
  - active prompt in trace line 59
  - runtime test in trace line 61
  - `refactor.md` in trace line 64
- It does eventually write the expected artifact:
  - file change in trace lines 66-67
  - readback in trace line 70

## Root Cause Hypothesis

Two problems are interacting:

1. The prompt presents artifact locations in a way that is ambiguous from the invocation workspace.
2. The prompt does not define the `framing.json` contract strongly enough, so the model backfills it from repo files.

This is a softer version of the Claude failure. Codex recovers, but only by spending unnecessary context on contract discovery.

## Proposed Solution

1. Render invocation-local artifact paths in the prompt, not repo-root-relative paths.
2. Make the `task_framer` output schema explicit in the prompt.
3. State that only declared inputs may be read.
4. State that tests, specs, and planning docs are not part of the runtime contract.
5. Keep a smoke test that asserts `framing.json` is produced without repo spelunking.

## Validation Plan

1. Rerun the isolated Codex `task_framer` smoke test.
2. Confirm trace shows:
   - correct input reads without path search
   - no reads from tests, specs, or `refactor.md`
   - direct write of `framing.json`
3. Compare total trace length before and after; it should drop materially from the current 72 events.
