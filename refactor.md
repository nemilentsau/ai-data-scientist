# Multi-Agent Data Scientist Refactor

## Purpose

This document replaces the current shared-session workflow direction with a clean multi-agent architecture that matches the actual benchmark goal:

- independent agents
- explicit artifact handoffs
- backend choice per agent within the same dataset run
- mandatory critique and revision loops
- no hidden dependence on one backend's session mechanics

This is a design reset, not an incremental repair.

We are not preserving runtime backward compatibility with the current workflow runner or config schema. Old runs, old prompts, and old configs remain in the repo and in the viewer as historical artifacts. The new runtime gets a new schema, new contracts, and a new execution model.

## What The Three Experiments Actually Taught Us

### Experiment 1: baseline single-agent failure was mostly framing failure

From [general-overview-20260401-081508.md](/Users/andreinemilentsau/Projects/ai-data-scientist/docs/artifacts/general-overview-20260401-081508.md):

- `overlapping_clusters` failed because the agent locked into a supervised GPA-prediction frame instead of testing latent grouping.
- `concept_drift` failed because the agent checked marginal stability instead of relationship stability.
- both Claude and Codex followed the same bad policy: identify the most target-like column, run generic predictive analysis, interpret weak pooled fit as weak signal.

Implication:

- the system needs a dedicated framing function before the main analyst starts.
- the system needs specialized probes for task families that generic EDA misses.

### Experiment 2: prompt upgrades helped, but did not create real self-correction

From [v2-prompt-overview-20260404.md](/Users/andreinemilentsau/Projects/ai-data-scientist/docs/artifacts/v2-prompt-overview-20260404.md):

- hypothesis-driven instructions helped when the agent already had the right frame in mind.
- visual review helped Claude because Claude actually read images.
- self-critique sections were mostly decorative. Agents named missing analyses and still did not run them.
- the hardest datasets still failed because the correct frame never entered the hypothesis set.

Implication:

- "tell one agent to critique itself" is not equivalent to a separate critic.
- visual review is valuable but insufficient.
- the architecture must force revision after critique, not just invite it.

### Experiment 3: visual review helps only after the right evidence exists

From [experiment-3-visual-pilot-synthesis-20260404.md](/Users/andreinemilentsau/Projects/ai-data-scientist/docs/artifacts/experiment-3-visual-pilot-synthesis-20260404.md):

- Claude solved `heteroscedasticity` and `interaction_effects` because the right signal was already present in the analysis and plots.
- Claude still failed `multimodal` because the workflow never forced a target-distribution reframing.
- Codex became competitive on `heteroscedasticity` and `interaction_effects`, which shows the analyst can be strong.
- Codex still failed `multimodal`, which shows visual review does not repair a wrong frame by itself.
- the current Codex implementation also exposed an architectural mistake: the runner modeled multi-step work as one continuing session instead of independent agents with explicit handoffs.

Implication:

- the system needs a critic that can reject the analyst's framing.
- the system needs explicit artifact requirements, especially for distributional checks.
- the system must orchestrate fresh invocations, not backend-specific resumed threads.

## Hard Requirements For The New System

These are non-negotiable:

1. Every agent invocation is independent by default.
2. Every agent can use a different backend within the same dataset run.
3. Shared context flows through files and structured manifests, not hidden session memory.
4. Critique must trigger a revision step.
5. Visual review must be a real agent role, not a sentence inside another prompt.
6. A deterministic coordinator must control the workflow graph; no backend session model or agent may define workflow semantics implicitly.
7. The runtime may break config compatibility with old benchmark configs.
8. Old results remain viewable in the dashboard without being re-run.

## Design Principles

### 1. Separate agent roles by responsibility, not by prompt flavor

Each agent must own a distinct decision boundary. If two agents can both "do general analysis," the boundary is wrong.

### 2. Make evidence handoffs explicit

Agents must consume named artifacts:

- `dataset_profile.json`
- `framing.json`
- `probe_findings/*.md`
- `analysis_report.md`
- `plots/*.png`
- `critiques/*.md`
- `verification.json`

No step should rely on "what the previous agent probably remembers."

### 3. Keep backend routing orthogonal to agent roles

Agent role and backend are separate dimensions.

Bad model:

- `visual_reviewer == Claude`

Correct model:

- `visual_reviewer` is a role
- `claude_cli`, `codex_cli`, `openai_api`, `anthropic_api`, `ollama` are execution backends
- configs map roles to backends

### 4. Use deterministic helpers where LLM judgment is not needed

Not everything should be an agent. Repetitive, objective preprocessing should be done by local code.

### 5. Force explicit revision loops with bounded retries

One critique pass is mandatory.
One revision pass is mandatory.
One verification pass is mandatory.
At most one additional repair cycle is allowed in the first implementation.

## Target Workflow

The default workflow for one dataset run should be a bounded loop controlled by a deterministic coordinator:

1. `profile_dataset` (deterministic)
2. `task_framer`
3. `specialist_probes` (0-3 agents in parallel, selected by the framer)
4. `analyst` round 1
5. `method_critic` and `visual_critic` in parallel
6. `workflow_coordinator` decides:
   - if blocking critique items exist, run `analyst` revision round N and then re-run the relevant critics
   - if critique passes, run `claim_verifier`
7. `claim_verifier`
8. `workflow_coordinator` decides:
   - if verification fails with repairable gaps and repair budget remains, run `analyst` repair round and verify again
   - if verification passes, run `final_editor`
9. `final_editor`

The first implementation should allow:

- exactly one mandatory critique/revision loop
- exactly one verification pass
- at most one additional repair loop after verification

This is not a linear pipeline. It is a coordinator-driven loop with bounded retries.

## Clean Separation Of Concerns

## Deterministic Runtime Services

These are not agents.

### `profile_dataset`

Purpose:

- create a compact, objective first-pass dossier on the dataset

Inputs:

- `dataset.csv`

Outputs:

- `workspace/profile/dataset_profile.json`
- `workspace/profile/column_summary.csv`
- `workspace/profile/sample_rows.csv`
- `workspace/profile/null_summary.csv`
- `workspace/profile/basic_univariate_metrics.json`

Must do:

- schema inference
- numeric/categorical/date detection
- cardinality summaries
- missingness summaries
- target-like column candidates
- simple distribution summaries for all numeric columns
- time-column detection candidates

Must not do:

- narrative interpretation
- benchmark conclusions
- model fitting beyond trivial summaries

Why it exists:

- removes repetitive orientation work from every agent
- gives the task framer structured input instead of raw CSV only

### `artifact_indexer`

Purpose:

- maintain a machine-readable inventory of every artifact created during the run

Outputs:

- `workspace/meta/artifact_index.json`

Why it exists:

- makes handoffs explicit
- lets agents reference exact artifacts
- simplifies importer/exporter logic

### `workflow_coordinator`

Purpose:

- decide which step runs next based on explicit machine-readable outputs from framers, critics, and verifiers

Inputs:

- `workspace/framing/framing.json`
- `workspace/framing/specialist_requests.json`
- `workspace/critiques/*.json`
- `workspace/verification/verification.json`
- workflow policy from config

Outputs:

- `workspace/meta/coordination_decisions.json`
- updated `workspace/meta/run_manifest.json`

Must do:

- expand requested specialist probes
- route execution through the critique loop
- stop the run only when pass/fail criteria are explicit
- enforce retry ceilings and branch conditions

Must not do:

- invent analysis conclusions
- act as another critic or analyst
- hide branching in opaque prompt text

Why it exists:

- coordination is runtime logic, not an LLM role
- the system needs explicit loop control, not a pipeline with a few extra stages

### `write_scope_checker`

Purpose:

- record file diffs before and after each agent step
- verify the step only wrote allowed paths

Outputs:

- `workspace/meta/step_diffs/<step_id>.json`

Why it exists:

- enforces role separation in practice
- makes step provenance inspectable

## Core Agents

These are required in the first real multi-agent implementation.

### 1. `task_framer`

Purpose:

- decide what kind of problem this dataset might be
- prevent premature regression framing

Inputs:

- `dataset.csv`
- `workspace/profile/dataset_profile.json`
- `workspace/profile/*`

Outputs:

- `workspace/framing/framing.md`
- `workspace/framing/framing.json`
- `workspace/framing/required_checks.json`
- `workspace/framing/specialist_requests.json`

Must do:

- propose 3-5 candidate task families
- rank them
- specify what evidence would falsify each
- list mandatory checks the analyst is not allowed to skip
- request specialist probes when the framing is ambiguous

Must not do:

- write `analysis_report.md`
- build the main analysis
- declare final conclusions

Failures addressed:

- `overlapping_clusters`
- `concept_drift`
- `multimodal`

Recommended default backend:

- Claude first, because Experiment 2 showed stronger framing when multimodal cues were visible and stronger critique behavior overall

### 2. `analyst`

Purpose:

- perform the main analysis and all subsequent revisions under the current framing and critique state

Inputs:

- `dataset.csv`
- `workspace/profile/*`
- `workspace/framing/*`
- `workspace/probes/*`
- optionally `workspace/critiques/*`
- optionally `workspace/verification/*`

Outputs:

- `analysis_report.md`
- `plots/*.png`
- `workspace/analysis/findings.json`
- `workspace/analysis/claim_evidence_map.json`
- `workspace/analysis/analysis_notes.md`

Must do:

- run tests and models aligned to the framing
- generate the initial report
- on later rounds, respond explicitly to critique and verification findings
- produce an explicit claim-to-evidence map

Must not do:

- dismiss mandatory checks from the framer without recording why
- mark the run complete

Failures addressed:

- all datasets where first-pass analysis matters

Recommended default backend:

- Codex or Claude, configurable per experiment
- Experiment 3 suggests Codex is a strong lead analyst on structured statistical work

### 3. `method_critic`

Purpose:

- challenge the analysis framing, omitted tests, and weak inferential logic

Inputs:

- `dataset.csv`
- `workspace/profile/*`
- `workspace/framing/*`
- `analysis_report.md`
- `workspace/analysis/findings.json`
- `workspace/analysis/claim_evidence_map.json`
- plot manifest from `workspace/meta/artifact_index.json`

Outputs:

- `workspace/critiques/method_critique.md`
- `workspace/critiques/method_critique.json`

Must do:

- identify missing task families not seriously tested
- identify unsupported claims
- identify missing statistics and missing plots
- issue concrete action items

Must not do:

- edit `analysis_report.md`
- quietly fix analysis itself

Failures addressed:

- decorative self-critique in Experiment 2
- missing reframing in `multimodal`
- missing regime comparison in `concept_drift`
- missing clustering argument in `overlapping_clusters`

Recommended default backend:

- Claude first

### 4. `visual_critic`

Purpose:

- inspect actual plots and find patterns the text understates or misses

Inputs:

- `analysis_report.md`
- `plots/*.png`
- `workspace/meta/artifact_index.json`
- optionally `workspace/framing/required_checks.json`

Outputs:

- `workspace/critiques/visual_critique.md`
- `workspace/critiques/visual_critique.json`
- optionally `workspace/critiques/requested_visuals.json`

Must do:

- inspect all required plots
- request additional plots if key evidence is absent
- identify visual contradictions

Must not do:

- serve as the only critic
- silently accept missing plot classes

Failures addressed:

- Experiment 3 showed visual review helps only when the right plots exist
- the visual critic must therefore be allowed to say "the required plot is missing"

Recommended default backend:

- Claude first
- Codex may be used later when fresh image-attached invocations are reliable

### 6. `claim_verifier`

Purpose:

- verify that the final report actually proves the benchmark-relevant claims

Inputs:

- `analysis_report.md`
- `workspace/analysis/claim_evidence_map.json`
- all critique artifacts
- artifact index

Outputs:

- `workspace/verification/verification.json`
- `workspace/verification/verification.md`

Must do:

- check whether key claims are supported by actual evidence
- check whether required benchmark dimensions were addressed
- distinguish "claim is correct" from "claim is proven"

Must not do:

- perform large new analyses
- directly edit the report

Failures addressed:

- Experiment 2 partials where the agent stopped one step short
- unsupported caveat handling

Recommended default backend:

- Claude first

### 7. `final_editor`

Purpose:

- prepare the final scored artifact after verification passes

Inputs:

- final `analysis_report.md`
- verification outputs

Outputs:

- final `analysis_report.md`
- `final_message.md`

Must do:

- ensure the report is coherent and final
- avoid introducing new analytical claims

Must not do:

- reopen analysis except for minor wording cleanups that preserve meaning

Why it exists:

- keeps presentation cleanup separate from analysis and critique

## Specialist Probe Library

These agents are conditionally invoked when requested by `task_framer`.

The first implementation should support at least these five specialist types because the benchmark already exposed them.

### `distribution_mixture_probe`

Purpose:

- inspect target and feature distributions for multimodality, mixture structure, and subgroup evidence

Addresses:

- `multimodal`
- `lognormal_skew`
- parts of `outlier_dominated`

Required outputs:

- `workspace/probes/distribution_mixture.md`
- explicit plots of target distribution

### `segmentation_cluster_probe`

Purpose:

- test latent grouping, cluster ambiguity, and segmentation uncertainty

Addresses:

- `overlapping_clusters`
- `well_separated_clusters`

Required outputs:

- clustering diagnostics
- uncertainty-aware interpretation

### `temporal_regime_probe`

Purpose:

- test whether relationships change over time, not just marginal means

Addresses:

- `concept_drift`
- parts of `time_series_seasonality`

Required outputs:

- pre/post comparison
- rolling correlation or rolling slope diagnostics
- regime-aware model comparison

### `assumption_diagnostics_probe`

Purpose:

- test residual structure, heteroscedasticity, leverage, calibration, and specification risk

Addresses:

- `heteroscedasticity`
- `outlier_dominated`
- false confidence under strong mean signal

Required outputs:

- formal tests where applicable
- residual visuals

### `interaction_nonlinearity_probe`

Purpose:

- screen for interactions and non-additive structure

Addresses:

- `interaction_effects`
- `quadratic`
- hidden non-additivity in other datasets

Required outputs:

- candidate interaction terms
- partial dependence or grouped visual evidence as appropriate

## Workflow Semantics

### Default execution policy

- every agent invocation is fresh
- every agent receives a constructed prompt packet plus explicit artifact references
- no step resumes a prior backend session
- the coordinator, not the backend, determines whether a role is being invoked as an initial analysis, critique response, or repair round

### Optional continuation policy

If we ever add session continuation later, it must be opt-in and backend-local:

- `continuation_policy: isolated` is the default and recommended mode
- `continuation_policy: resume_previous` may exist later for debugging or cost optimization
- workflow semantics must not depend on continuation

### Review loop policy

First implementation:

- exactly one mandatory critique round
- exactly one mandatory analyst revision round if either critic returns blocking issues
- one optional repair round if verification fails with repairable gaps

No open-ended loops in v1. The loop is explicit, bounded, and driven by coordinator decisions.

## Backend Model

Backend selection must happen per agent instance.

### Required backend abstraction

Each backend adapter must support one operation:

- `invoke(packet, workspace) -> invocation_result`

Not:

- `start`
- `continue`
- `resume`

`resume` may exist internally for a backend, but the orchestrator must never require it.

### Packet contents

Each invocation packet should include:

- agent role
- backend key
- model
- prompt text
- workspace path
- input artifact list
- image attachments
- allowed write paths
- expected output paths
- timeout / budget / reasoning settings

### Invocation result

Each result should include:

- exit status
- trace path
- session log path
- final message path
- declared outputs
- detected writes
- detected reads if available

### Backends to support in the new design

Phase 1:

- `claude_cli`
- `codex_cli`

Phase 2:

- `openai_api`
- `anthropic_api`
- `ollama`

Important:

- different agents in the same workflow must be able to use different backends
- example: `lead_analyst=codex_cli`, `visual_critic=claude_cli`, `claim_verifier=claude_cli`

## New Config Schema

The new runner gets a new schema. Do not try to normalize the old one.

### Example

```yaml
name: mixed-team-v1
description: Multi-agent workflow with explicit critique and revision

backends:
  codex_main:
    provider: codex_cli
    model: gpt-5.4
    reasoning_effort: high

  claude_review:
    provider: claude_cli
    model: claude-opus-4-6

agents:
  task_framer:
    role: task_framer
    backend: claude_review
    prompt: prompts/agents/task-framer.md
    writes:
      - workspace/framing/**

  analyst:
    role: analyst
    backend: codex_main
    prompt: prompts/agents/analyst.md
    writes:
      - analysis_report.md
      - plots/**
      - workspace/revision/**
      - workspace/analysis/**

  method_critic:
    role: method_critic
    backend: claude_review
    prompt: prompts/agents/method-critic.md
    writes:
      - workspace/critiques/method_critique.*

  visual_critic:
    role: visual_critic
    backend: claude_review
    prompt: prompts/agents/visual-critic.md
    image_inputs:
      - plots/*.png
    writes:
      - workspace/critiques/visual_critique.*

  claim_verifier:
    role: claim_verifier
    backend: claude_review
    prompt: prompts/agents/claim-verifier.md
    writes:
      - workspace/verification/**

workflow:
  steps:
    - id: profile
      builtin: profile_dataset

    - id: coordinate_framing
      builtin: workflow_coordinator
      needs: [profile]

    - id: framing
      agent: task_framer
      needs: [profile, coordinate_framing]

    - id: selected_probes
      dynamic_from: workspace/framing/specialist_requests.json
      needs: [framing]

    - id: analysis_round_1
      agent: analyst
      needs: [framing, selected_probes]
      mode: initial_analysis

    - id: method_review_round_1
      agent: method_critic
      needs: [analysis_round_1]

    - id: visual_review_round_1
      agent: visual_critic
      needs: [analysis_round_1]

    - id: critique_gate_round_1
      builtin: workflow_coordinator
      needs: [method_review_round_1, visual_review_round_1]

    - id: analysis_round_2
      agent: analyst
      needs: [critique_gate_round_1]
      mode: critique_revision
      run_if: critique_gate_round_1.requires_revision == true

    - id: verification
      agent: claim_verifier
      needs: [analysis_round_2]
      run_if: critique_gate_round_1.requires_revision == true

    - id: verification_no_revision
      agent: claim_verifier
      needs: [analysis_round_1]
      run_if: critique_gate_round_1.requires_revision == false

    - id: verification_gate
      builtin: workflow_coordinator
      needs: [verification, verification_no_revision]

policy:
  max_repair_rounds: 1
  fail_on_write_scope_violation: true
```

## Workspace Contract

The new runtime should standardize the per-dataset workspace like this:

```text
<work_dir>/
  dataset.csv
  analysis_report.md
  plots/
  workspace/
    profile/
    framing/
    probes/
    analysis/
    critiques/
    revision/
    verification/
    meta/
      artifact_index.json
      run_manifest.json
      step_diffs/
      prompts/
      packets/
      agent_runs/
```

Each step also gets a mirrored results record:

```text
results/runs/<config>/<dataset>/
  analysis_report.md
  plots/
  score.json
  benchmark_notes.md
  workflow_manifest.json
  agent_runs/
    <step_id>/
      packet.json
      prompt.md
      trace.jsonl
      session.log
      final_message.md
      writes.json
      outputs.json
```

## What Must Change In The Python Package

Do not keep extending the current `orchestration` package. It encodes the wrong mental model.

Create a new package subtree focused on independent invocations and workflow graphs.

## Target package structure

```text
ai_data_scientist/
  runtime/
    run_context.py
    workspace.py
    artifact_index.py
    write_scope.py
    manifests.py
  backends/
    base.py
    claude_cli.py
    codex_cli.py
    openai_api.py
    anthropic_api.py
    ollama.py
  agents/
    registry.py
    packets.py
    prompts.py
    builtin_steps.py
  workflows/
    graph.py
    planner.py
    executor.py
    policies.py
  experiments/
    importer.py
    exporter.py
    store.py
```

## Module responsibilities

### `runtime/*`

- workspace preparation
- artifact indexing
- write-scope tracking
- run manifest generation

### `backends/*`

- build and execute one fresh invocation packet
- collect traces and logs
- attach images or file lists as backend supports

### `agents/*`

- agent registry
- prompt resolution
- packet construction from role plus artifacts
- built-in deterministic steps

### `workflows/*`

- workflow graph validation
- dynamic probe expansion
- step execution ordering
- critique / repair loop policy

### `experiments/*`

- import new workflow manifests into SQLite
- keep legacy import path only for old historical runs
- export dashboard JSON

## Prompts

Do not overwrite the current prompt files. Keep them as historical artifacts.

Create a new structure:

```text
prompts/
  legacy/
    analyst-generic.md
    analyst-v2.md
    visual-review.md
  agents/
    task-framer.md
    analyst.md
    method-critic.md
    visual-critic.md
    claim-verifier.md
  specialists/
    distribution-mixture-probe.md
    segmentation-cluster-probe.md
    temporal-regime-probe.md
    assumption-diagnostics-probe.md
    interaction-nonlinearity-probe.md
```

Prompt rules:

- each prompt should define only that role's boundary
- critics do not revise
- revisers must answer critique items explicitly
- verifier checks proof completeness, not prose quality

## Importer And Viewer Strategy

We are not preserving runtime backward compatibility, but we are preserving historical visibility.

That means:

- old runs stay in `results/runs/...`
- old experiments remain in SQLite and exported manifests
- new runs emit richer manifests
- importer supports two source kinds:
  - `legacy_import`
  - `team_runtime_v1`

### New metadata fields that matter

Add to workflow or agent records:

- `backend_key`
- `backend_provider`
- `model`
- `agent_role`
- `step_kind`
- `input_artifact_ids`
- `output_artifact_ids`
- `allowed_write_globs`
- `detected_write_paths`
- `review_round`
- `parent_step_ids`

### Viewer upgrades needed

The viewer should eventually show:

- workflow graph per case
- which backend ran each agent
- which critique items were raised
- which revision addressed which critique
- artifact grouping by agent role

This is phase 2 for the UI. The first runtime refactor should still emit enough metadata for this later.

## What To Delete Or Freeze

### Freeze as legacy

- current `ai_data_scientist/orchestration/*`
- current workflow config normalization for old schema
- shared-session semantics
- `start_step` / `continue_step` interface
- workflow definitions that hard-code a single forward-only stage order

### Do not use in the new runtime

- `codex exec resume` as workflow semantics
- single-session carry-over as the mechanism for agent handoff

### Keep for history only

- old configs in `results/configs/*.yaml`
- old prompts
- old imported experiments

## Detailed Implementation Plan

## Phase 0: freeze the wrong abstraction

Goal:

- stop adding features to the current runner

Tasks:

- mark current `ai_data_scientist/orchestration` as legacy in docs
- stop routing new work through `resume`-based semantics
- create `refactor.md` as the execution plan

Exit criteria:

- team agrees the old runner is maintenance-only

## Phase 1: define contracts before code

Goal:

- make the new system explicit before implementation

Tasks:

- define dataclasses or pydantic models for:
  - `BackendSpec`
  - `AgentSpec`
  - `BuiltinStepSpec`
  - `WorkflowStepSpec`
  - `CoordinatorDecision`
  - `InvocationPacket`
  - `InvocationResult`
  - `ArtifactRef`
  - `WorkflowManifest`
- define `framing.json` schema
- define `specialist_requests.json` schema
- define `claim_evidence_map.json` schema
- define `verification.json` schema
- define step write-scope rules

Exit criteria:

- all inter-step files have written schemas
- no prompt depends on ambiguous free-form handoff only

## Phase 2: build a fresh-invocation backend layer

Goal:

- make every agent invocation independent

Tasks:

- create `ai_data_scientist/backends/base.py`
- implement `invoke(packet, workspace)` contract
- implement new `claude_cli` backend with fresh process per step
- implement new `codex_cli` backend with fresh process per step
- make image attachment support explicit per packet
- remove any session carry-over assumptions from backend interfaces

Exit criteria:

- two backends can run the same agent packet shape
- no runner code branches on `start` vs `continue`

## Phase 3: build runtime services

Goal:

- provide deterministic infrastructure for agent handoff and provenance

Tasks:

- implement workspace builder
- implement dataset profiler
- implement artifact indexer
- implement prompt packet writer
- implement write-scope checker
- implement workflow manifest writer

Exit criteria:

- every step has reproducible inputs and outputs on disk
- every write is attributable to one step

## Phase 4: implement core agents

Goal:

- get the mandatory critique loop working

Tasks:

- write prompts for:
  - `task_framer`
  - `analyst`
  - `method_critic`
  - `visual_critic`
  - `claim_verifier`
  - `final_editor`
- implement packet builders for each role
- implement required artifact dependencies for each role

Exit criteria:

- one dataset run can execute the full core loop with no specialists

## Phase 5: implement specialist probes

Goal:

- address the known benchmark blind spots directly

Tasks:

- implement specialist prompts and packet builders for:
  - `distribution_mixture_probe`
  - `segmentation_cluster_probe`
  - `temporal_regime_probe`
  - `assumption_diagnostics_probe`
  - `interaction_nonlinearity_probe`
- implement dynamic step expansion from `specialist_requests.json`
- cap probe fan-out to avoid runaway cost

Exit criteria:

- framer can request probes
- probes run in parallel where safe
- analyst receives probe outputs explicitly

## Phase 6: replace config model

Goal:

- make backend-per-agent routing first-class

Tasks:

- define new YAML schema under a new config namespace
- add schema validation
- support backend registry plus agent registry plus workflow graph
- stop trying to normalize legacy config shapes for execution

Exit criteria:

- one config can route different roles to different backends

## Phase 7: replace benchmark entrypoint

Goal:

- switch `run_benchmark.py` to the new runner

Tasks:

- implement new CLI path that loads the new config schema
- keep experiment title / dataset / import flags compatible where reasonable
- emit the new workflow manifest into run outputs

Exit criteria:

- `run_benchmark.py` uses the new runtime for new configs
- old configs are no longer executable unless explicitly run through a legacy path

## Phase 8: importer and dashboard integration

Goal:

- make new runs visible without losing old experiment history

Tasks:

- extend importer to read `workflow_manifest.json`
- preserve legacy import path for old experiments already on disk
- add agent/backend fields to manifest payloads
- export enriched JSON for the frontend

Exit criteria:

- old experiments still load
- new experiments show multi-agent structure

## Phase 9: evaluation and regression tests

Goal:

- make the new architecture reliable before more experiments

Tasks:

- unit tests for config and schema validation
- unit tests for packet construction
- unit tests for write-scope enforcement
- unit tests for dynamic specialist expansion
- unit tests for backend routing per agent
- importer tests for both legacy and new manifests
- fixture-backed integration tests for a mixed-backend workflow

Exit criteria:

- tests pass without live model calls
- one fixture-based mixed workflow proves the architecture shape

## Phase 10: first real benchmark program

Goal:

- validate the architecture on the known hard cases

Run this order:

1. `multimodal`
2. `concept_drift`
3. `overlapping_clusters`
4. `heteroscedasticity`
5. `interaction_effects`

Why this order:

- the first three test reframing
- the last two test whether critics and specialists add value on cases already near-solvable

Success criteria:

- `multimodal` produces an explicit target-distribution plot and mixture framing
- `concept_drift` compares relationship stability across time, not just marginals
- `overlapping_clusters` tests segmentation seriously, not as a throwaway side note
- critique artifacts are specific and revision responses address them explicitly
- at least one mixed-backend configuration works end to end
- the workflow manifest shows explicit coordinator decisions for every branch and loop transition

## Recommended First Mixed-Backend Team

Do this first, because it is grounded in the experiments:

- `task_framer`: Claude
- `distribution_mixture_probe`: Claude
- `temporal_regime_probe`: Claude
- `segmentation_cluster_probe`: Claude
- `analyst`: Codex
- `method_critic`: Claude
- `visual_critic`: Claude
- `claim_verifier`: Claude
- `final_editor`: Codex

Reason:

- Claude currently looks stronger at critique and visual interpretation
- Codex currently looks strong enough to be a serious analyst and reviser
- this mixed setup directly tests the user requirement that different agents in one run can use different backends

## Explicit Non-Goals For The First Refactor

Do not do these in the first cut:

- open-ended agent chat between peers
- nested agent teams
- autonomous agent spawning without orchestrator approval
- unbounded revision loops
- cross-dataset memory
- trying to make the new runtime run the old YAML configs

## Final Direction

The new system is not:

- one clever agent with a longer prompt
- one backend session that keeps talking to itself
- one runner with provider-specific hacks around `resume`
- one forward-only pipeline pretending to be a loop

The new system is:

- a workflow graph of independent agents
- a deterministic coordinator that decides the next step explicitly
- explicit artifact contracts
- explicit critique and revision
- backend routing per agent
- deterministic orchestration around LLM judgment, not orchestration hidden inside one LLM session

That is the architecture the benchmark actually needs, and it is the only direction that matches the lessons from Experiments 1, 2, and 3.
