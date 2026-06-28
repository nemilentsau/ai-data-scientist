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

## Setup

```bash
uv sync
```

## Smoke Run

Use the deterministic fake Codex adapter for local verification:

```bash
uv run python -m eda_artifacts.cli run --adapter fake --run-id smoke
```

This writes a run under:

```text
runs/eda-artifacts/multimodal/smoke/
```

Expected artifacts:

```text
dataset/dataset.csv
dataset/profile.json
framing/framing.json
queries/target_distribution.sql
results/target_distribution.parquet
results/target_distribution.summary.json
charts/target_distribution.vegalite.json
renders/target_distribution.png
reviews/visual_review.json
reports/report.md
lineage.json
```

## Codex Run

After authenticating the Codex CLI, run the same harness with headless Codex:

```bash
uv run python -m eda_artifacts.cli run --adapter codex-exec --run-id codex-smoke
```

The real adapter uses `codex exec` with `gpt-5.5`, JSON output, structured
schemas, and image input for the visual reviewer role.

## Development

```bash
uv run pytest tests/ -v
uv run ruff check
```

Core modules:

- `eda_artifacts/datasets.py` generates the deterministic `multimodal` dataset.
- `eda_artifacts/profile.py` writes the dataset profile artifact.
- `eda_artifacts/sql.py` validates read-only SQL and writes query results.
- `eda_artifacts/charts.py` validates Vega-Lite specs and renders PNG reviews.
- `eda_artifacts/codex.py` contains the Codex adapter boundary.
- `eda_artifacts/graph.py` runs the LangGraph harness.
- `eda_artifacts/lineage.py` writes the final artifact dependency index.
