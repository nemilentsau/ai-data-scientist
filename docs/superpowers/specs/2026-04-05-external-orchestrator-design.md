# External Orchestrator Architecture Proposal

## Purpose

This document defines the v1 architecture for replacing the current shared-session CLI workflow with an external orchestrator that runs independent agent invocations with explicit artifact handoffs.

The main goal is to stop using hidden CLI session memory as the workflow substrate. Each agent invocation must have its own CLI instance, its own private working directory, and its own publish contract. Shared context must move through artifacts that the orchestrator can inspect, validate, and preserve.

## Status

Proposed and ready for review.

## Decisions Locked For V1

These decisions are in scope for the first implementation and should be treated as fixed unless this spec is revised.

1. Every agent invocation uses its own CLI instance.
2. Every agent invocation runs in its own private working directory.
3. Agents do not pass hidden CLI conversation context to each other.
4. Shared context flows through declared artifacts only.
5. The canonical run tree receives only declared published outputs.
6. Full agent traces, logs, and scratch outputs remain available from the private invocation workspace.
7. Prompts are role-first and backend-agnostic in v1.
8. The main workflow is a loop, not a fixed linear pipeline.
9. The analysis stage is split into `analysis_planner` and `analysis_executor`.
10. `final_editor` is not in the main loop and is excluded from v1.
11. Reframing escalation is controlled by the verifier in v1.

## Decisions Explicitly Deferred

These questions should not block the v1 architecture work.

1. Exact directory layout for archived prompt history.
2. Whether specialist probes ship in v1 or land in a later phase.
3. Whether a terminal editorial pass should exist after verification in a later version.
4. Whether critics may directly trigger reframing in a later version.
5. Whether role prompts need backend-specific variants after initial benchmarking.

## Problem Statement

The current runner still models multi-step work as a continued backend session. That creates three structural problems:

1. Context growth becomes the architecture. Every handoff grows prompt state and hidden session state instead of shrinking to the evidence that actually matters.
2. Backend session semantics leak into workflow semantics. Resume behavior, attachment behavior, and thread persistence shape the workflow more than the intended agent roles do.
3. Provenance becomes blurry. It is harder to explain which agent created which artifact, which files were scratch outputs, and which conclusions were actually carried forward.

The replacement architecture must keep the benefits of CLI agents while moving coordination and handoffs into deterministic code.

## Design Principles

### 1. Separate analytical judgment from workflow policy

Agents make analytical judgments. The orchestrator applies workflow policy.

- agents decide framing, critique, and verification verdicts
- the orchestrator decides which step runs next based on structured outputs

### 2. Keep private work private

An agent may generate scratch scripts, exploratory plots, partial drafts, and noisy intermediate files. Those are useful for debugging and auditing, but they should not automatically pollute the canonical run artifact tree.

### 3. Publish explicitly

Each invocation publishes only a declared set of outputs after the orchestrator validates them.

### 4. Roles own responsibilities, not prompt flavors

The system should have a small number of durable roles with clear boundaries. A new prompt is justified only when it introduces a distinct decision boundary.

### 5. Prompt history is preserved, but active runtime stays clean

Committed prompt history remains in the repository. Active runtime prompts must be separable from historical prompt assets. The exact archive layout is deferred.

## Deterministic Preprocessing

V1 should start with a deterministic dataset profiling step before any agent runs.

### `profile_dataset`

Purpose:

- create a compact structural summary of the dataset
- remove repetitive orientation work from every agent invocation

Inputs:

- raw dataset

Outputs:

- schema summary
- column summaries
- null summary
- lightweight univariate metrics
- sample rows

This step is not an LLM role. It is ordinary code that prepares the initial artifact set for `task_framer`.

## Target V1 Workflow

The default v1 loop is:

1. `profile_dataset`
2. `task_framer`
3. `analysis_planner`
4. `analysis_executor`
5. `method_critic` and `visual_critic` in parallel
6. `verifier`
7. loop decision

Possible loop outcomes:

- `pass`: stop successfully
- `revise`: run another `analysis_planner -> analysis_executor` round using critique and verification outputs
- `reframe`: run `task_framer` again, then continue with a new `analysis_planner -> analysis_executor` round
- `fail_terminal`: stop unsuccessfully

This is a state machine, not a sequential step list.

## Role Definitions

### `task_framer`

Purpose:

- define the initial analytical goal
- widen the hypothesis space
- name required checks the analyst may not skip

Inputs:

- dataset
- profile artifacts
- prior verification or critique outputs when reframe is required

Outputs:

- framing memo
- framing JSON
- required checks JSON
- optional next-step guidance

Non-goals:

- does not write the main report
- does not own loop control

### `analysis_planner`

Purpose:

- turn framing into a concrete analysis plan for the current round
- define the exact hypotheses, evidence requirements, plots, and statistical checks the executor must produce
- respond to critique and verification artifacts in later rounds by revising the plan

Inputs:

- dataset
- profile artifacts
- framing artifacts
- prior critique artifacts when revising
- prior verification artifacts when revising or reframing

Outputs:

- `analysis_plan.md`
- `hypotheses.json`
- `experiment_plan.json`
- revision planning memo when applicable

Non-goals:

- does not write the main report
- does not execute the statistical work itself

### `analysis_executor`

Purpose:

- execute the current analysis plan
- write code, generate plots, run statistical tests, and produce the report and evidence artifacts

Inputs:

- dataset
- profile artifacts
- framing artifacts
- planning artifacts from `analysis_planner`
- prior critique artifacts when revising
- prior verification artifacts when revising or reframing

Outputs:

- `analysis_report.md`
- plots
- structured findings
- claim-to-evidence map
- stats artifacts
- revision execution memo when applicable

Non-goals:

- does not decide the analytical goal for the round
- does not decide whether the run is complete

### `method_critic`

Purpose:

- challenge framing adherence, inferential rigor, missing analyses, and unsupported claims

Inputs:

- framing artifacts
- planning artifacts
- report artifacts
- plots and plot manifest
- structured findings and claim-to-evidence map

Outputs:

- structured critique with concrete blocking and non-blocking actions

### `visual_critic`

Purpose:

- inspect plot evidence directly
- identify contradictions, missing plot classes, or visually obvious structure not reflected in the report

Inputs:

- framing artifacts
- planning artifacts
- report artifacts
- plots and plot manifest
- structured findings and claim-to-evidence map

Outputs:

- structured visual critique
- requested visuals when the current evidence is insufficient

### `verifier`

Purpose:

- decide whether the current round is complete enough to stop
- distinguish repairable failures from framing failures and terminal failures

Outputs:

- `verdict`
- concise reasoning
- required repairs when revision is possible
- reframing reasons when the framing must change

The verifier is the acceptance gate for v1. Critics identify problems; verifier determines whether the system should stop, revise, or reframe.

## Orchestrator Responsibilities

The external orchestrator is plain code. It does not interpret free-form markdown to infer workflow state. It reads machine-readable outputs from agents and applies fixed routing policy.

The orchestrator is responsible for:

1. creating run state
2. running deterministic preprocessing steps such as dataset profiling
3. creating invocation workspaces
4. selecting the backend for each role
5. rendering prompts with the declared input artifact set
6. launching CLI invocations
7. collecting logs and traces
8. validating declared outputs
9. publishing declared outputs into the canonical run tree
10. recording provenance and state transitions
11. deciding the next step from structured verdicts

The orchestrator is not responsible for:

- inventing analytical conclusions
- silently repairing agent outputs
- acting like another critic

## Invocation Model

Each invocation has a private workdir, for example:

```text
results/runs/<config>/<dataset>/invocations/<invocation_id>/
```

Suggested contents:

```text
invocations/<invocation_id>/
  input/
  workspace/
  output/
  logs/
  trace/
  manifest.json
```

Meaning:

- `input/`: materialized input artifacts for this invocation
- `workspace/`: the directory where the CLI actually runs
- `output/`: declared outputs collected from the workspace before publish
- `logs/`: CLI stderr, session logs, command metadata
- `trace/`: raw trace streams or backend-native session metadata
- `manifest.json`: invocation metadata, role, backend, prompt ref, input refs, declared output refs, status

### Private Workspace Rules

1. Agents may write freely inside their private invocation workspace.
2. Agents may not write directly to canonical run artifacts during execution.
3. The orchestrator may discard unpublished scratch files without losing the audit trail because the invocation directory is preserved.

## Canonical Run Artifact Model

The canonical run tree is the shared state for the workflow.

Suggested structure:

```text
results/runs/<config>/<dataset>/
  artifacts/
    profile/
    framing/
    analysis/
    critiques/
    verification/
  invocations/
  orchestration/
    run_state.json
    transitions.jsonl
    artifact_index.json
```

The canonical tree should contain only artifacts that later steps are allowed to rely on.

## Publish Contract

Each role has a declared publish contract. Example shape:

```json
{
  "role": "analysis_executor",
  "declared_outputs": [
    "artifacts/analysis/analysis_report.md",
    "artifacts/analysis/findings.json",
    "artifacts/analysis/claim_evidence_map.json",
    "artifacts/analysis/plots/*.png",
    "artifacts/analysis/stats/*.json",
    "artifacts/analysis/revision_execution.md"
  ]
}
```

Publish flow:

1. run the invocation in a private workdir
2. collect declared outputs from the private workspace
3. validate existence and basic shape
4. publish only those outputs into the canonical run tree
5. update artifact index and transition log

Anything not declared stays private to the invocation.

## Prompt Model

V1 uses role-first, backend-agnostic prompts.

Active runtime roles:

1. `task_framer`
2. `analysis_planner`
3. `analysis_executor`
4. `method_critic`
5. `visual_critic`
6. `verifier`

Prompt guidance:

- prompts define role behavior and output contracts
- prompts do not define workflow transitions
- prompts should assume isolated invocation state and explicit artifact inputs
- backend-specific wrappers may exist later, but are out of scope for v1

## Structured Output Contracts

The loop depends on structured outputs, not markdown inference.

Minimum verifier contract:

```json
{
  "verdict": "pass|revise|reframe|fail_terminal",
  "reasoning": "",
  "required_repairs": [],
  "reframing_reasons": []
}
```

Minimum critic contract:

```json
{
  "requires_revision": true,
  "blocking_issues": [],
  "non_blocking_issues": []
}
```

Minimum framer contract:

```json
{
  "primary_frame": "",
  "alternative_frames": [],
  "required_checks": [],
  "framing_risks": []
}
```

The orchestrator should validate these files before using them for routing.

## Loop Policy

The orchestrator uses fixed routing policy:

1. run `profile_dataset`
2. start with `task_framer`
3. run `analysis_planner`
4. run `analysis_executor`
5. run critics in parallel
6. run verifier
7. route by verifier verdict

Routing:

- `pass` -> mark run complete
- `revise` -> run `analysis_planner` again, then `analysis_executor`, with critique and verification artifacts included
- `reframe` -> run `task_framer` again with verifier reasoning included, then restart with `analysis_planner`
- `fail_terminal` -> mark run failed

### Retry Policy

V1 should be bounded.

Recommended bounds:

- one initial framing round
- up to two planning/execution rounds before terminal failure unless a reframe occurs
- at most one reframe cycle in v1
- explicit failure if retry budget is exhausted

The exact numeric limits may be configured, but the runtime must keep the loop bounded and visible.

## Backend Routing

Role and backend are separate dimensions.

Examples:

- `task_framer` may run on Claude
- `analysis_planner` may run on Claude
- `analysis_executor` may run on Codex
- critics may run on either backend

This mapping should be config-driven. The orchestrator owns backend selection for each invocation.

## Provenance And Observability

The system must make it easy to answer:

1. which role created this artifact
2. which invocation created it
3. which prompt and backend were used
4. which canonical inputs were provided
5. what private logs and scratch outputs exist for that invocation

Required metadata:

- invocation manifest
- artifact index with producer invocation id
- transition log with state changes and routing reasons

This keeps the workflow explainable without forcing all artifacts into the shared tree.

## Migration Guidance

### Remove From Active Runtime

The new runtime should stop depending on:

- resumed shared CLI sessions across roles
- legacy linear step lists as the only execution model
- prompts that combine analysis and corrective review into one role
- harness assumptions that every backend step shares one mutable workspace

### Preserve

The repo should preserve:

- committed prompt history from prior experiments
- historical run outputs under `results/runs/`
- benchmark result comparability where feasible

### Introduce

The new runtime needs:

- external orchestrator state machine
- invocation-private workdirs
- publish contracts
- structured role outputs
- clearer prompt separation between active runtime and historical prompts

## Implementation Approach

This should not be built as one large refactor. V1 should be delivered in vertical slices with runnable checkpoints.

### Phase 1: Runtime Skeleton

Build the new orchestration substrate without the full loop:

- invocation-private workdirs
- canonical artifact tree
- invocation manifests
- transition log
- publish contract validation
- backend-per-role config shape

Success checkpoint:

- one role can run in an isolated invocation and publish declared outputs into the canonical tree

### Phase 2: Preprocessing And Planning/Execution Path

Add the first complete analytical path:

- `profile_dataset`
- `task_framer`
- `analysis_planner`
- `analysis_executor`

Success checkpoint:

- one dataset run can produce framing artifacts, planning artifacts, report artifacts, plot artifacts, and stats artifacts without any shared CLI session state

### Phase 3: Critique And Verification

Add:

- `method_critic`
- `visual_critic`
- `verifier`

Success checkpoint:

- a complete single-round run produces critique artifacts and a verifier verdict using the published planning and execution artifacts

### Phase 4: Loop Control

Add the bounded loop:

- `pass`
- `revise`
- `reframe`
- `fail_terminal`

Success checkpoint:

- the orchestrator can route deterministically through at least one revision cycle and one reframe cycle according to verifier output

### Phase 5: Architecture Experiments

Use experiments to resolve uncertain role-boundary questions instead of locking them in prematurely.

Suggested experiments:

1. `analysis_planner + analysis_executor` versus a single combined analyst role
2. critics with full artifact access versus reduced artifact access
3. parallel critics versus serial critics

These experiments should evaluate:

- benchmark quality
- artifact completeness
- tendency to skip required checks
- cost and latency

## Out Of Scope For V1

1. specialist probe library in the default path
2. backend-specific prompt variants
3. final editorial pass
4. autonomous LLM loop coordinator
5. unbounded critique and repair loops

## Success Criteria

V1 is successful when:

1. each role invocation runs in its own CLI session and private workdir
2. canonical shared context flows only through published artifacts
3. the system can show full per-invocation logs without polluting canonical artifacts
4. the orchestrator loop is driven by structured outputs, not hidden thread state
5. the analysis stage produces separate planning artifacts and execution artifacts
6. both critics operate on the full published artifact set, including plots
7. the active prompt set is materially smaller and cleaner than the current draft direction
