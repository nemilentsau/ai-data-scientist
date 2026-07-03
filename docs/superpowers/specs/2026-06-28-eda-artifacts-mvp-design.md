# EDA Artifacts MVP Design

## Purpose

Build a narrow Codex-only trial that tests whether artifact-first EDA can produce
durable, inspectable analysis artifacts for the `multimodal` dataset.

The MVP is not a general AI data scientist benchmark. It is a single-dataset,
single-harness experiment for this constrained claim:

> EDA should produce durable query, result, chart, report, and lineage artifacts,
> while rendered chart images are generated only as review views.

This trial is not testing whether Codex can independently discover the right
analysis question. The user supplies the analysis question, and the EDA framer
uses that question plus the dataset profile to propose an ordered chart artifact
plan. The trial tests whether Codex can turn that framed plan into valid SQL,
chart, render, review, report, and lineage artifacts.

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
dataset profile + user question
  -> eda_framer
  -> for each artifact in artifact_plan:
       artifact_builder
       execute query
       validate/render chart artifact
       visual_reviewer with plan context
       optional one revision of the same artifact
  -> deterministic synthesis report
  -> lineage
```

This keeps the part that mattered from the old multi-agent work, separate role
judgment, while removing the pieces that slowed iteration.

## Agent Roles

### `eda_framer`

Purpose:

- Turn the user question and dataset profile into an initial EDA frame.
- Declare an ordered chart artifact plan before any modeling work.
- Request durable chart artifacts that the builder can implement one at a time.

Outputs:

- `output.json`

Minimum fields:

```json
{
  "user_question": "",
  "analysis_goal": "",
  "artifact_plan": [],
  "stop_conditions": []
}
```

### `artifact_builder`

Purpose:

- Convert the frame into durable artifacts.
- Build exactly the current artifact request provided by the harness.
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
- Review exactly one rendered chart image per invocation.
- Use the full artifact plan, previous review decisions, remaining planned
  artifacts, and current revision request as context.
- Write the report from plotted evidence after seeing the rendered chart.
- Decide whether the current artifact passes or one focused revision of that same
  artifact is required.

Inputs:

- rendered chart image
- `review-context.json`
- review prompt and output schema

Outputs:

- `visual_review.json`

Minimum fields:

```json
{
  "artifact_id": "",
  "verdict": "pass|revise",
  "visual_adequacy": [],
  "statistical_findings": [],
  "limitations": [],
  "carry_forward_notes": [],
  "required_revision": "",
  "report_markdown": ""
}
```

## Hard Visual Gate

No final synthesis report can be accepted until separate Codex visual-review
invocations have inspected every planned rendered chart image.

Chart specs and result tables are upstream durable artifacts, but they are not
visual-review evidence. The visual reviewer must judge the attached rendered
chart image for the current artifact. Because it also receives the full plan and
previous decisions, it should not ask for a future planned artifact as a revision
of the current chart.

## Artifact Model

Durable source-of-truth artifacts:

```text
runs/eda-artifacts/multimodal/<run_id>/
  00-dataset/
    dataset.csv
    profile.json
  01-eda-framer/
    user-question.txt
    prompt.md
    output.schema.json
    output.json
  02-artifact-builder/
    <artifact_id>/
      attempt-1/
        build-context.json
        prompt.md
        output.schema.json
        output.json
        query.sql
        chart.vegalite.json
  03-execution/
    <artifact_id>/
      attempt-1/
        result.parquet
        result.summary.json
  04-render/
    <artifact_id>/
      attempt-1/
        chart.png
  05-visual-reviewer/
    <artifact_id>/
      attempt-1/
        review-context.json
        prompt.md
        image-inputs.json
        output.schema.json
        output.json
        report.md
  06-synthesis/
    report.md
  lineage.json
```

The numbered directories are the execution order. Agent roles are named in their
folder names. Artifact IDs are subdirectories under the affected stages, and
revision loops create `attempt-2` under the same artifact ID.

`04-render/<artifact_id>/attempt-*/chart.png` is not the durable chart source of
truth. It is a reproducible review output created from
`02-artifact-builder/<artifact_id>/attempt-*/chart.vegalite.json` and
`03-execution/<artifact_id>/attempt-*/result.parquet`.

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

The builder must implement exactly the current artifact request provided by the
harness. For the current smoke question, the ordered plan usually starts with a
compact distribution artifact for `monthly_rent_usd` and follows with a
bin-sensitivity artifact, but that is a user-question consequence rather than a
hardcoded builder contract.

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
   - Invoke Codex with `build-context.json`.
   - Build or revise only the current artifact's query and chart spec.

5. `validate_and_render`
   - Validate Vega-Lite JSON shape.
   - Render chart image into `04-render/<artifact_id>/attempt-*`.
   - Validate required artifacts exist.

6. `run_visual_reviewer`
   - Write `review-context.json`.
   - Invoke Codex with the rendered chart image attached.
   - Produce contextual visual review JSON.

7. `select_next_artifact`
   - If reviewer verdict is `pass`, advance to the next artifact in
     `artifact_plan`.
   - If reviewer verdict is `revise`, run one focused builder revision for the
     same artifact.
   - Re-render and re-review once.
   - Stop the run after one revision for that artifact if the review still fails.

8. `finalize_run`
   - Write deterministic `06-synthesis/report.md` only after all planned
     artifacts pass.
   - Write final `lineage.json`.
   - Mark the run `passed_visual_gate` or `revision_budget_exhausted`.

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
- A `revise` verdict triggers exactly one revision loop for the current artifact.
- A passed review advances to the next artifact.
- The final lineage graph records query, result, chart, render, review, synthesis,
  and per-artifact dependencies.

No tests should assert exact Codex wording.

## Success Criteria

The MVP is successful if one local command can run the constrained `multimodal`
artifact-generation trial and produce:

- a preserved user-question artifact
- an EDA framer output with an ordered `artifact_plan`
- a SQL query artifact for each planned chart artifact attempt
- a materialized result artifact for each planned chart artifact attempt
- a Vega-Lite chart spec for each planned chart artifact attempt
- a rendered chart image for each planned chart artifact attempt
- a visual-review artifact proving each rendered image was reviewed with plan
  context
- a deterministic synthesis report after all planned artifacts pass
- a lineage file that connects all produced artifacts
- an inspectable run directory where numbered folders show execution order and
  role folders contain their own prompt, schema, output, and derived artifacts

The MVP is unsuccessful if it produces a polished report but skips the visual
review gate for any planned chart artifact.

This success does not mean the prompts are useful for practical open-ended EDA.
The user question currently supplies the analysis direction. A passing run only
proves that Codex can operationalize a known question into durable artifacts.

## Deferred Decisions

These are intentionally out of scope for the first implementation:

- whether the project becomes a new standalone repo
- whether the package is renamed at the distribution level
- whether dynamic frontend rendering ships in the first branch
- whether to support Plotly
- whether to support arbitrary Python transforms
- whether to restore multiple datasets
- whether to compare against historical benchmark scores
