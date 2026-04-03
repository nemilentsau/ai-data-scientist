# Docs

This directory is the durable home for current architecture docs and synthesis artifacts.
Historical refactor planning and postmortem docs are intentionally not kept here anymore.

## Contents

- [`architecture.md`](/Users/andreinemilentsau/Projects/ai-data-scientist/docs/architecture.md): current source of truth for storage, import flow, frontend contract, implemented state, and open work.
- [`artifacts/general-overview-20260401-081508.md`](/Users/andreinemilentsau/Projects/ai-data-scientist/docs/artifacts/general-overview-20260401-081508.md): failure-mode synthesis across the current benchmark run.
- [`artifacts/experiment-redesign-schema-20260401-081508.md`](/Users/andreinemilentsau/Projects/ai-data-scientist/docs/artifacts/experiment-redesign-schema-20260401-081508.md): current schema summary for the SQLite catalog and exported experiment manifests.

## Current Runtime Model

The current benchmark metadata flow is:

- raw harness artifacts stay in `results/runs/...`
- imported metadata is stored in `results/experiments/catalog.sqlite`
- the frontend consumes:
  - `results/experiments/index.json`
  - `results/experiments/<experiment_id>/manifest.json`

There is no per-entry JSON metadata tree anymore and no flat `/api/manifest` compatibility layer.

## Conventions

- Put durable analysis artifacts under `docs/artifacts/`.
- Put current architecture docs directly under `docs/`.
- Tie future artifacts to an `experiment_id` in both filename and content when they refer to a specific imported experiment.
- To surface a markdown note in the frontend, add YAML front matter with
  `experiment_ids` under `docs/artifacts/`.
- Optional `datasets` and `config_names` front-matter fields narrow a note to
  matching cases inside that experiment.
