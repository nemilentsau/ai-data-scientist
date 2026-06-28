# EDA Artifacts MVP Design

## Purpose

Build a narrow Codex-only trial that tests whether artifact-first EDA can produce
durable, inspectable analysis artifacts for the `multimodal` dataset.

The MVP is not a general AI data scientist benchmark. It is a single-dataset,
single-harness experiment for this constrained claim:

> EDA should produce durable query, result, chart, report, and lineage artifacts,
> while rendered chart images are generated only as review views.

This trial is not testing whether Codex can independently discover the right
analysis question. The current prompts intentionally tell Codex to inspect the
`monthly_rent_usd` target distribution first. The trial tests whether Codex can
turn that known analysis target into valid SQL, chart, render, review, report,
and lineage artifacts.

See `docs/goals.md` for the current trial goal, success criteria, and how these
findings should drive the next run.

## Status

Approved direction for implementation planning.

## Name

Working project/package name:

```text
eda-artifacts
```

Python package/module name:

```text
eda_artifacts
```

Tagline:

```text
Notebookless, LLM-assisted EDA with versioned query, chart, and report artifacts.
```

## Current Codex Assumptions

Checked on 2026-06-28.

- Local CLI version: `codex-cli 0.130.0`.
- Current Codex model guidance recommends `gpt-5.5` for demanding Codex tasks.
- `codex exec` supports non-interactive execution, JSONL event output, explicit
  model selection, image attachments, output schemas, ephemeral runs, and isolated
  sandbox settings.
- The Codex SDK exists for programmatic thread control. Python SDK usage is a
  plausible primary adapter for LangGraph. `codex exec` remains a fallback adapter
  if the SDK adds too much setup friction.

The MVP should default to `gpt-5.5`.

## Dataset Scope

Use exactly one dataset:

```text
multimodal
```

Reason:

- It was one of the clearest failures in prior experiments.
- The failure is a framing failure: the agent treated rent as an ordinary
  regression target before inspecting its distribution.
- It directly tests the artifact idea because the critical evidence is a target
  distribution chart, not a static benchmark score.

Simpson's paradox is deferred. It is important, but it can be solved from grouped
tables and does not stress the rendered-chart review loop as directly.

## MVP Non-Goals

The first implementation will not include:

- multiple datasets
- benchmark scoring across agents
- Claude support
- old experiment import/dashboard catalog support
- persistent PNG plot galleries
- arbitrary Python transforms
- Plotly support
- subagent fan-out
- seven-role orchestration
- memory curator or cross-run memory
- generic user upload UI

## Architecture Choice

Use Option B: a minimal LangGraph harness with three Codex role invocations and
deterministic execution/rendering nodes between them.

```text
dataset profile
  -> eda_framer
  -> execute/render required first chart
  -> artifact_builder
  -> validate/render artifact bundle
  -> visual_reviewer
  -> optional one revision
  -> final report artifact
```

This keeps the part that mattered from the old multi-agent work, separate role
judgment, while removing the pieces that slowed iteration.

## Agent Roles

### `eda_framer`

Purpose:

- Choose the initial EDA frame.
- Declare required checks before any modeling work.
- For `multimodal`, require direct target-distribution inspection before any
  regression or feature-importance story.

Outputs:

- `framing.json`

Minimum fields:

```json
{
  "primary_question": "",
  "required_checks": [],
  "chart_requests": [],
  "stop_conditions": []
}
```

### `artifact_builder`

Purpose:

- Convert the frame into durable artifacts.
- Write SQL query artifacts.
- Produce result artifact metadata.
- Write Vega-Lite chart specs.

Outputs:

- SQL query files
- chart spec files
- artifact metadata updates

The builder does not directly execute arbitrary Python in the MVP.

### `visual_reviewer`

Purpose:

- Inspect rendered chart images generated from the durable chart specs.
- Write the report from plotted evidence after seeing the rendered chart.
- Decide whether one focused revision is required.

Inputs:

- rendered chart image
- chart spec
- compact result sample or summary

Outputs:

- `visual_review.json`

Minimum fields:

```json
{
  "verdict": "pass|revise",
  "visual_findings": [],
  "required_revision": ""
}
```

## Hard Visual Gate

No final report can be accepted until a separate Codex visual-review invocation
has inspected at least one rendered chart image.

The agent may inspect chart specs and data snapshots, but that is not sufficient.
The visual reviewer must receive an actual rendered view of the plotted chart.

## Artifact Model

Durable source-of-truth artifacts:

```text
runs/eda-artifacts/multimodal/<run_id>/
  00-dataset/
    dataset.csv
    profile.json
  01-eda-framer/
    prompt.md
    output.schema.json
    output.json
  02-artifact-builder/
    attempt-1/
      prompt.md
      output.schema.json
      output.json
      query.sql
      chart.vegalite.json
      report.md
  03-execution/
    attempt-1/
      result.parquet
      result.summary.json
  04-render/
    attempt-1/
      chart.png
  05-visual-reviewer/
    attempt-1/
      prompt.md
      image-inputs.json
      output.schema.json
      output.json
  lineage.json
```

The numbered directories are the execution order. Agent roles are named in their
folder names, and revision loops create `attempt-2`, `attempt-3`, and so on
under the affected stages.

`04-render/attempt-*/chart.png` is not the durable chart source of truth. It is a
reproducible review output created from `02-artifact-builder/attempt-*/chart.vegalite.json`
and `03-execution/attempt-*/result.parquet`.

## Chart Strategy

Use Vega-Lite JSON as the MVP chart grammar.

Reason:

- It is declarative.
- It is easier for an agent to inspect and edit than arbitrary plotting code.
- It can render interactively in a frontend later.
- It can also be rendered to PNG for Codex visual review.

Store chart specs and data/result references. Do not store PNGs as primary
chart artifacts.

## Query Strategy

Use DuckDB as the deterministic query engine.

The LLM writes SQL. The harness executes SQL and materializes the result.

Initial required query family for `multimodal`:

- distribution of `monthly_rent_usd`
- appropriate bins or density proxy
- optional grouped breakdown only after the target distribution is inspected

The first pass must answer:

```text
What does the target distribution look like?
```

before:

```text
What predicts the target?
```

## LangGraph Nodes

Planned graph nodes:

1. `prepare_dataset`
   - Generate or copy the `multimodal` CSV into the run directory.
   - Produce deterministic `profile.json`.

2. `run_eda_framer`
   - Invoke Codex with `gpt-5.5`.
   - Request structured JSON output.

3. `execute_queries`
   - Validate SQL is read-only.
   - Execute with DuckDB.
   - Store result data and result summaries.

4. `build_artifacts`
   - Invoke Codex with query/result context.
   - Create or revise query and chart spec artifacts.

5. `validate_and_render`
   - Validate Vega-Lite JSON shape.
   - Render chart image into `04-render/attempt-*`.
   - Validate required artifacts exist.

6. `run_visual_reviewer`
   - Invoke Codex with rendered chart image attached.
   - Produce `visual_review.json`.

7. `maybe_revise_once`
   - If reviewer verdict is `revise`, run one focused builder revision.
   - Re-render and re-review once.
   - Stop after one revision even if the review still fails.

8. `finalize_run`
   - Write final `lineage.json`.
   - Mark the run `passed_visual_gate`, `failed_visual_gate`, or
     `revision_budget_exhausted`.

## Codex Invocation Adapter

Preferred implementation:

- a Python Codex SDK adapter, if it works cleanly with LangGraph and image inputs

Fallback implementation:

- a `codex exec` adapter using:
  - `--model gpt-5.5`
  - `--json`
  - `--output-schema`
  - `--image` for visual-review inputs
  - `--ephemeral` when persistent Codex session files are not needed
  - explicit sandbox settings

The adapter boundary should hide this choice from the graph nodes.

## Repository Cleanup Direction

This branch should move away from the old benchmark surface.

Delete or archive old code only after the design and implementation plan are
approved. Useful prior artifacts remain available in existing branches and git
history.

Expected cleanup target:

- keep dataset generation code needed for `multimodal`
- keep only tests needed for the new `eda_artifacts` package
- remove old multi-agent benchmark runner, reviewer scoring, import catalog,
  and PNG dashboard paths from this branch

Do not merge `pipeline-refactor-for-multiagent` into this branch.

## Testing Strategy

Tests should focus on deterministic behavior, not LLM prose.

Required test areas:

- `prepare_dataset` writes the expected dataset/profile artifacts.
- SQL validation rejects mutation statements.
- DuckDB execution writes result artifacts.
- Vega-Lite validation accepts the MVP chart spec and rejects malformed specs.
- Renderer creates a review image from the chart spec and result artifact.
- LangGraph routing enforces the visual gate.
- A `revise` verdict triggers exactly one revision loop.
- The final lineage graph records query, result, chart, render, review, and report
  dependencies.

No tests should assert exact Codex wording.

## Success Criteria

The MVP is successful if one local command can run the constrained `multimodal`
artifact-generation trial and produce:

- a SQL query artifact for target distribution
- a materialized result artifact
- a Vega-Lite chart spec
- a rendered chart image
- a visual-review artifact proving the image was reviewed
- a report that identifies the target as multimodal or mixture-like before
  making any regression-style claim
- a lineage file that connects all produced artifacts
- an inspectable run directory where numbered folders show execution order and
  role folders contain their own prompt, schema, output, and derived artifacts

The MVP is unsuccessful if it produces a polished report but skips visual target
distribution inspection.

This success does not mean the prompts are useful for practical open-ended EDA.
The prompts currently leak the target-analysis direction. A passing run only
proves that Codex can operationalize a known EDA target into durable artifacts.

## Deferred Decisions

These are intentionally out of scope for the first implementation:

- whether the project becomes a new standalone repo
- whether the package is renamed at the distribution level
- whether dynamic frontend rendering ships in the first branch
- whether to support Plotly
- whether to support arbitrary Python transforms
- whether to restore multiple datasets
- whether to compare against historical benchmark scores
