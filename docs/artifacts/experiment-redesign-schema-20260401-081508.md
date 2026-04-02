# Experiment Redesign Schema

Run ID: `20260401-081508`

## Status

This document now reflects the current implemented schema, not the earlier file-heavy proposal.

The important correction is:

- raw artifacts stay in `results/runs/...`
- metadata lives in SQLite
- the frontend consumes exported manifests
- there is no one-file-per-entry metadata tree

## Runtime Storage Model

### Artifact storage

- `results/runs/<config>/<dataset>/...`

This remains the source of truth for:

- reports
- scores
- traces
- session logs
- generated Python files
- plots
- config-level benchmark reports

### Metadata storage

- `results/experiments/catalog.sqlite`

### Frontend export files

- `results/experiments/index.json`
- `results/experiments/<experiment_id>/manifest.json`

## Core Entities

The current implementation stores normalized metadata for:

- `Experiment`
- `ConfigSnapshot`
- `Case`
- `WorkflowRun`
- `AgentRun`
- `Artifact`
- `Evaluation`

The current harness is still effectively single-agent per case, but `workflow_runs` and `agent_runs` already exist in the catalog so the model can expand without another storage redesign.

## SQLite Tables

Current catalog tables:

- `experiments`
- `config_snapshots`
- `cases`
- `workflow_runs`
- `agent_runs`
- `artifacts`
- `evaluations`

Each table stores both:

- useful query fields
- the full normalized payload as JSON text

That gives the system two things at once:

- relational filtering and indexing
- stable manifest reconstruction without recomputing domain objects from scratch

## Current ID Conventions

- `experiment_id`: `exp_YYYYMMDD_HHMMSS_<slug>`
- `config_snapshot_id`: `config_<experiment_id>_<config>`
- `case_id`: `case_<experiment_id>_<config>_<dataset>`
- `workflow_run_id`: `workflow_<case_id>_<attempt>`
- `agent_run_id`: `agent_<workflow_run_id>_<seq>`
- `evaluation_id`: `evaluation_<workflow_run_id>`
- `artifact_id`: `artifact_<experiment_id>_<slugified_relative_path>`

## Artifact Typing

Current artifact types include:

- `analysis_report`
- `score`
- `trace`
- `session`
- `final_message`
- `generated_code`
- `plot`
- `benchmark_report`
- generic `artifact` fallback

Generated Python files are explicitly preserved as:

- `type: generated_code`
- `role: harness_output`
- `media_type: text/x-python`

## Exported Experiment Index Shape

`results/experiments/index.json` contains a list of experiment summaries.

Example shape:

```json
[
  {
    "experiment_id": "exp_20260401_181245_legacy-solo-benchmark-import",
    "title": "Legacy Solo Benchmark Import",
    "source_kind": "legacy_import",
    "created_at": "2026-04-01T18:12:45Z",
    "updated_at": "2026-04-01T18:12:45Z",
    "summary": {
      "num_cases": 40,
      "num_workflow_runs": 40,
      "num_agent_runs": 40,
      "num_artifacts": 598,
      "num_evaluations": 40,
      "verdict_counts": {
        "solved": 26,
        "partial": 9,
        "wrong": 3,
        "failed": 2,
        "run_error": 0
      }
    }
  }
]
```

## Exported Experiment Manifest Shape

`results/experiments/<experiment_id>/manifest.json` contains:

- `experiment`
- `config_snapshots`
- `cases`
- `workflow_runs`
- `agent_runs`
- `artifacts`
- `evaluations`

This manifest is the frontend-facing experiment view, not the underlying source of truth.

## Artifact Content URLs

The frontend adds content URLs to manifest artifacts when serving or building the app.

Current URL shape:

```text
/api/artifacts/<experiment_id>/<artifact_id>/content.<ext>
```

Those URLs resolve back to the original artifact files referenced by artifact paths.

## Why This Schema Is Better Than The Earlier Proposal

The earlier redesign draft over-translated normalized entities into filesystem entries.

The current implemented schema is better because it:

- preserves all benchmark artifacts
- avoids hundreds of tiny metadata files
- keeps metadata queryable
- keeps the frontend contract stable
- supports future multi-agent expansion without another storage pivot

## Future Extension

The current schema does not require a `StageRun` table yet.

If the harness later emits real staged multi-agent execution, stage-level structure can be added on top of:

- `workflow_runs`
- `agent_runs`
- `artifacts`

without changing the core storage model again.
