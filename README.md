# eda-artifacts

Notebookless, LLM-assisted EDA with versioned query, chart, and report artifacts.

Exploratory data analysis usually lives in notebooks, where code, plots, prose,
and hidden state collapse into one mutable document. `eda-artifacts` experiments
with a different unit of work: durable analytical artifacts.

This branch is intentionally narrow:

- one dataset: `multimodal`
- one agent surface: Codex headless execution
- one harness: a small LangGraph loop
- one visual review path: Vega-Lite specs rendered to temporary PNG review
  artifacts so Codex can inspect the plotted chart

The durable source of truth is the artifact set: dataset profile, SQL query,
Parquet result, Vega-Lite chart spec, report, visual review, and lineage. PNGs
are generated from those artifacts for visual inspection; they are not the
canonical chart representation.

The current trial is not an open-ended data-analysis benchmark. The user supplies
the analysis question, and the EDA framer turns that question plus the dataset
profile into an ordered chart artifact plan. The run tests whether Codex can turn
each planned artifact into executable SQL, rendered charts, contextual visual
reviews, and final lineage. See
[`docs/goals.md`](docs/goals.md) for the exact goal and success criteria.

## Setup

```bash
uv sync
```

## Smoke Run

Use the deterministic fake Codex adapter for local verification:

```bash
uv run python -m eda_artifacts.cli run \
  --adapter fake \
  --run-id smoke \
  --question "Assess whether monthly_rent_usd has a simple distribution."
```

This writes a run under:

```text
runs/eda-artifacts/multimodal/smoke/
```

Expected artifacts:

```text
00-dataset/dataset.csv
00-dataset/profile.json
01-eda-framer/user-question.txt
01-eda-framer/prompt.md
01-eda-framer/output.schema.json
01-eda-framer/output.json
02-artifact-builder/<artifact_id>/attempt-1/build-context.json
02-artifact-builder/<artifact_id>/attempt-1/prompt.md
02-artifact-builder/<artifact_id>/attempt-1/output.schema.json
02-artifact-builder/<artifact_id>/attempt-1/output.json
02-artifact-builder/<artifact_id>/attempt-1/query.sql
02-artifact-builder/<artifact_id>/attempt-1/chart.vegalite.json
03-execution/<artifact_id>/attempt-1/result.parquet
03-execution/<artifact_id>/attempt-1/result.summary.json
04-render/<artifact_id>/attempt-1/chart.png
05-visual-reviewer/<artifact_id>/attempt-1/review-context.json
05-visual-reviewer/<artifact_id>/attempt-1/prompt.md
05-visual-reviewer/<artifact_id>/attempt-1/image-inputs.json
05-visual-reviewer/<artifact_id>/attempt-1/output.schema.json
05-visual-reviewer/<artifact_id>/attempt-1/output.json
05-visual-reviewer/<artifact_id>/attempt-1/report.md
06-synthesis/report.md
lineage.json
```

The numbered directories are the execution order. Agent roles are named in their
folder names. Artifact IDs are subdirectories under the builder, execution,
render, and reviewer stages. Revision loops create `attempt-2` under the same
artifact ID, so a failed chart is revised without consuming the review budget for
later planned artifacts.

The visual reviewer reviews one rendered image at a time. Its
`review-context.json` includes the current artifact request, the full artifact
plan, previous review decisions, remaining planned artifacts, and the current
revision request. This prevents the reviewer from asking for a chart that is
already planned as a later artifact.

## Codex Run

After authenticating the Codex CLI, run the same harness with headless Codex:

```bash
uv run python -m eda_artifacts.cli run \
  --adapter codex-exec \
  --run-id codex-smoke \
  --question "Assess whether monthly_rent_usd has a simple distribution."
```

The real adapter uses `codex exec` with `gpt-5.5`, JSON output, structured
schemas, and image input for the visual reviewer role.

## Run Inspector

Start the browser UI:

```bash
cd frontend
npm install
npm run dev
```

The app runs at:

```text
http://localhost:5180/
```

The inspector lists repo-local runs automatically from:

```text
runs/eda-artifacts/
```

Select a run in the UI. The browser folder picker is only a fallback for
external runs.

The inspector shows the run as execution stages, selected artifact content,
rendered chart image, and lineage links.

The frontend is intentionally scoped to `frontend/` and uses Vite, React,
Tailwind CSS, and strict TypeScript. Repo-owned frontend source and config are
TypeScript or declarative assets only; JavaScript and JSX files are not part of
the frontend codebase.

Validate it with:

```bash
cd frontend
npm run check
```

## Development

```bash
uv run pytest tests/ -v
uv run ruff check
uv run pyright
```

Core modules:

- `eda_artifacts/datasets.py` generates the deterministic `multimodal` dataset.
- `eda_artifacts/profile.py` writes the dataset profile artifact.
- `eda_artifacts/sql.py` validates read-only SQL and writes query results.
- `eda_artifacts/charts.py` validates Vega-Lite specs and renders PNG reviews.
- `eda_artifacts/codex.py` contains the Codex adapter boundary.
- `eda_artifacts/graph.py` runs the LangGraph harness.
- `eda_artifacts/lineage.py` writes the final artifact dependency index.
