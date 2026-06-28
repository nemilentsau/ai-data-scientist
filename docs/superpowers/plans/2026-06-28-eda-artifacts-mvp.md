# EDA Artifacts MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old broad benchmark surface on this branch with a narrow Codex-only EDA artifact harness for the `multimodal` dataset.

**Architecture:** Build a new `eda_artifacts` package around deterministic dataset/profile/query/chart/render/lineage modules plus a LangGraph runner. Codex role invocations are isolated behind an adapter boundary so tests can use a fake adapter and real runs can use `codex exec` with `gpt-5.5`.

**Tech Stack:** Python 3.14, `uv`, DuckDB, Pandas, PyArrow/Parquet, Vega-Lite JSON, `vl-convert-python`, LangGraph, Codex CLI.

---

## File Structure

- Create `eda_artifacts/datasets.py` for the single deterministic `multimodal` dataset generator.
- Create `eda_artifacts/profile.py` for deterministic dataset profiling.
- Create `eda_artifacts/sql.py` for read-only SQL validation and DuckDB execution.
- Create `eda_artifacts/charts.py` for Vega-Lite validation and PNG review rendering.
- Create `eda_artifacts/codex.py` for Codex role adapter interfaces plus fake and `codex exec` adapters.
- Create `eda_artifacts/prompts.py` for role prompt builders.
- Create `eda_artifacts/lineage.py` for final lineage graph writing.
- Create `eda_artifacts/graph.py` for the LangGraph state machine.
- Create `eda_artifacts/cli.py` for `uv run python -m eda_artifacts.cli run`.
- Replace broad old tests with focused tests under `tests/`.
- Update `pyproject.toml`, `README.md`, and `AGENTS.md`.

## Tasks

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] Add runtime dependencies: `duckdb`, `pyarrow`, `langgraph`, `vl-convert-python`.
- [ ] Run `uv sync`.
- [ ] Commit dependency update.

### Task 2: Dataset And Profile

**Files:**
- Create: `tests/test_dataset_profile.py`
- Create: `eda_artifacts/__init__.py`
- Create: `eda_artifacts/datasets.py`
- Create: `eda_artifacts/profile.py`

- [ ] Write failing tests that verify the `multimodal` generator is deterministic and writes `dataset.csv`.
- [ ] Write failing tests that verify `profile_dataset()` writes `profile.json` with row count, columns, dtypes, null counts, and numeric summaries.
- [ ] Run `uv run pytest tests/test_dataset_profile.py -v` and confirm the tests fail because modules do not exist.
- [ ] Implement the minimal generator and profiler.
- [ ] Run `uv run pytest tests/test_dataset_profile.py -v` and confirm pass.
- [ ] Commit dataset/profile implementation.

### Task 3: SQL Execution

**Files:**
- Create: `tests/test_sql_execution.py`
- Create: `eda_artifacts/sql.py`

- [ ] Write failing tests for read-only SQL validation: `SELECT` passes, `DROP TABLE` fails, and `WITH ... SELECT` passes.
- [ ] Write failing tests that execute a distribution query against `dataset.csv` and write both Parquet and summary JSON artifacts.
- [ ] Run `uv run pytest tests/test_sql_execution.py -v` and confirm fail.
- [ ] Implement `validate_read_only_sql()` and `execute_query_artifact()`.
- [ ] Run `uv run pytest tests/test_sql_execution.py -v` and confirm pass.
- [ ] Commit SQL execution implementation.

### Task 4: Chart Spec And Render

**Files:**
- Create: `tests/test_charts.py`
- Create: `eda_artifacts/charts.py`

- [ ] Write failing tests that a minimal Vega-Lite bar chart spec validates.
- [ ] Write failing tests that malformed specs are rejected.
- [ ] Write failing tests that a chart spec plus result Parquet renders a non-empty PNG under `renders/`.
- [ ] Run `uv run pytest tests/test_charts.py -v` and confirm fail.
- [ ] Implement chart validation and rendering with `vl-convert-python`.
- [ ] Run `uv run pytest tests/test_charts.py -v` and confirm pass.
- [ ] Commit chart implementation.

### Task 5: Codex Adapter And Role Schemas

**Files:**
- Create: `tests/test_codex_adapter.py`
- Create: `eda_artifacts/codex.py`
- Create: `eda_artifacts/prompts.py`

- [ ] Write failing tests for `FakeCodexAdapter` returning queued role outputs and recording image inputs.
- [ ] Write failing tests that `CodexExecAdapter` command construction includes `--model gpt-5.5`, `--json`, `--output-schema`, and `--image` for visual review.
- [ ] Run `uv run pytest tests/test_codex_adapter.py -v` and confirm fail.
- [ ] Implement role output dataclasses, fake adapter, command builder, and prompt builders.
- [ ] Run `uv run pytest tests/test_codex_adapter.py -v` and confirm pass.
- [ ] Commit adapter implementation.

### Task 6: LangGraph Harness And Lineage

**Files:**
- Create: `tests/test_graph.py`
- Create: `eda_artifacts/graph.py`
- Create: `eda_artifacts/lineage.py`

- [ ] Write failing tests that a fake pass-review run produces query, result, chart, render, review, report, and lineage artifacts.
- [ ] Write failing tests that a `revise` review triggers exactly one builder revision and second visual review.
- [ ] Write failing tests that final status is `revision_budget_exhausted` when the second review still requests revision.
- [ ] Run `uv run pytest tests/test_graph.py -v` and confirm fail.
- [ ] Implement LangGraph nodes and lineage writing.
- [ ] Run `uv run pytest tests/test_graph.py -v` and confirm pass.
- [ ] Commit graph implementation.

### Task 7: CLI And Branch Cleanup

**Files:**
- Create: `tests/test_cli.py`
- Create: `eda_artifacts/cli.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Delete: old benchmark/frontend/reviewer/import/prompt/result files that are not needed for the MVP.

- [ ] Write failing CLI tests for `uv run python -m eda_artifacts.cli run --adapter fake --run-id test-run`.
- [ ] Implement CLI.
- [ ] Delete old broad benchmark files from this branch after the new CLI path works.
- [ ] Update README and AGENTS with the new command surface.
- [ ] Run `uv run pytest tests/ -v`.
- [ ] Commit cleanup and CLI.

### Task 8: Verification

**Files:**
- No new files unless verification exposes a gap.

- [ ] Run `uv run pytest tests/ -v`.
- [ ] Run `uv run ruff check`.
- [ ] Run `uv run python -m eda_artifacts.cli run --adapter fake --run-id smoke`.
- [ ] Inspect the smoke run artifact tree.
- [ ] Commit any final fixes.
