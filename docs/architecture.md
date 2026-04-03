# Architecture

## Purpose

This document is the current source of truth for the benchmark metadata and frontend architecture.

## Runtime Model

The system now uses a hybrid storage model:

- raw harness artifacts stay in `results/runs/...`
- imported metadata lives in `results/experiments/catalog.sqlite`
- the frontend reads exported JSON views:
  - `results/experiments/index.json`
  - `results/experiments/<experiment_id>/manifest.json`

There is no per-entry JSON metadata tree and no flat `/api/manifest` compatibility layer.

## Artifact Storage

The benchmark preserves all harness outputs in `results/runs/...`, including:

- `analysis_report.md`
- `score.json`
- `trace.jsonl`
- `session.json`
- `session.log`
- `final_message.md`
- generated Python files such as `analysis.py`, `analyze_dataset.py`, `run_analysis.py`, `modeling.py`
- plot images
- config-level `benchmark_report.md`

These files are the source of truth for artifact contents.

Experiment-scoped synthesis notes can also live in:

- `docs/artifacts/*.md`

Those notes are imported only when they opt in via YAML front matter with an
`experiment_ids` list.

Optional front-matter fields:

- `datasets`: attach the note to matching dataset cases in the experiment
- `config_names`: narrow the note to specific configs within those cases

## Metadata Storage

Imported benchmark metadata is stored in:

- `results/experiments/catalog.sqlite`

The SQLite catalog currently stores normalized metadata for:

- `experiments`
- `config_snapshots`
- `cases`
- `workflow_runs`
- `agent_runs`
- `artifacts`
- `evaluations`

The current harness is still effectively single-agent per case, but `workflow_runs` and `agent_runs` are already present so the model can expand without another storage redesign.

## Import Flow

Legacy run folders can be imported with:

```bash
uv run python experiment_import.py --title "Imported benchmark"
```

This import:

- catalogs existing `results/runs/...` artifacts
- writes metadata into `catalog.sqlite`
- exports:
  - `results/experiments/index.json`
  - `results/experiments/<experiment_id>/manifest.json`

It does not move, rewrite, or prune raw harness artifacts.

If a markdown file under `docs/artifacts/` includes matching `experiment_ids`
front matter, it is imported as an experiment-scoped synthesis artifact and
exported in the manifest alongside harness artifacts.

If it also includes `datasets` and/or `config_names`, the importer records
`related_case_ids` so those notes can be surfaced from matching case details.

Re-importing the same `experiment_id` replaces the metadata rows for that experiment and rewrites its exported manifest.

Fresh benchmark runs now refresh experiment metadata automatically through
`run_benchmark.py` unless `--skip-import` is passed. Reusing the same
`--experiment-id` across benchmark invocations merges the requested config into
the existing experiment instead of dropping earlier cases.

## Frontend Contract

The frontend is experiment-only and reads:

- `/api/experiments.json`
- `/api/experiments/<experiment_id>.json`
- `/api/artifacts/<experiment_id>/<artifact_id>/content.<ext>`

Artifact contents are loaded lazily from the original files referenced by artifact paths.

The current app:

1. fetches the experiment list
2. selects one experiment (restored from URL hash on refresh)
3. fetches that experiment manifest
4. defaults to a results overview with experiment notes and the comparison matrix
5. exposes three purpose-built artifact views: Plot Gallery, Case Compare, Code Inspector
6. hydrates case detail and artifact detail views from artifact URLs
7. preserves navigation state in `location.hash` so refresh and back/forward work

### URL Routing

The app uses hash-based routing (`router.js`). Routes:

- `#/{experimentId}` — overview with comparison matrix
- `#/{experimentId}/artifacts/{gallery|compare|code}` — artifact explorer sub-view
- `#/{experimentId}/run/{config}/{dataset}` — case detail
- `#/{experimentId}/artifact/{artifactId}` — artifact detail

State changes push browser history entries; back/forward triggers `popstate` and re-applies the route.

### Frontend Stack

- **Svelte 5** with runes (`$state`, `$derived`, `$effect`, `$props`)
- **Vite 6** with `@tailwindcss/vite` plugin and a custom manifest plugin for API middleware
- **Tailwind CSS v4** with a `@theme` block defining the full design system (colors, fonts, shadows, animations)
- Shared utilities: `parse.js` (trace/tool/verdict), `experiments.js` (manifest hydration), `router.js` (URL routing)
- Shared components: `Lightbox.svelte` (reusable image modal with keyboard nav)

## Why This Shape

This model solves the earlier storage problem cleanly:

- files remain the artifact store
- SQLite handles indexing and relationships
- the frontend gets a simple exported JSON view
- the repo avoids hundreds of tiny metadata files

## Current State

Implemented:

- SQLite-backed experiment catalog
- import CLI for legacy runs
- fresh-run experiment refresh from `run_benchmark.py`
- experiment manifest export (index + per-experiment JSON)
- experiment-aware frontend API (Vite dev middleware)
- experiment-aware frontend UI (Svelte 5 + Tailwind CSS v4)
- hash-based URL routing with browser history support
- experiment-scoped synthesis notes
- dataset/config-scoped notes linked to matching cases
- case-detail note navigation
- comparison matrix with verdict coloring, coverage bars, and aggregate stats
- plot gallery with search, dataset/config filters, and lightbox navigation
- case comparison view (side-by-side configs with plots, reports, code)
- code inspector with lazy-loading inline preview
- generic artifact detail for markdown, images, JSON, traces, logs, and code
- centralized verdict colors and display logic (`parse.js`)
- shared Lightbox component with keyboard navigation

Not implemented yet:

- real multi-agent workflow ingestion from the harness
- cross-experiment comparison

## Remaining Work

### 1. Experiment-linked synthesis artifacts

The catalog supports experiment-level and scoped markdown notes. The authoring
model is lightweight (YAML front-matter in `docs/artifacts/`).

Still needed:

- a cleaner convention for deep-dives and comparison notes
- richer scopes such as cross-dataset or cross-experiment comparisons

### 2. Richer multi-agent support

The schema is ready for more than one agent run, but the harness does not yet emit a true multi-agent workflow.

Still needed:

- real multi-agent orchestration
- richer provenance between agent runs and artifacts
- optional stage-level structure only if the harness truly emits it

### 3. Cross-experiment comparison

The frontend is single-experiment. Cross-experiment comparison would require:

- multi-experiment selection UI
- a comparison view showing the same datasets across experiments
- performance trend tracking across runs

## Non-Negotiable Constraints

These remain in force:

1. Generated Python files are benchmark artifacts, not disposable scratch files.
2. Raw harness artifacts should remain in `results/runs/...` unless there is a clear operational reason to move them.
3. Do not reintroduce one-file-per-row metadata without a real consumer.
4. Keep the frontend aligned to the actual metadata model, not a compatibility model.
5. Avoid speculative stage abstractions until the harness really emits them.
