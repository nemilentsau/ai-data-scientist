# Multi-Artifact Review Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current single-chart harness with an explicit ordered chart-artifact loop where the visual reviewer sees the current artifact contract, the full expected artifact plan, and prior review decisions.

**Architecture:** The EDA framer emits an ordered `artifact_plan`. The graph iterates through that plan, building, executing, rendering, and reviewing one chart artifact at a time. Each reviewer invocation receives a saved context JSON containing the current artifact request, all planned artifacts, previous passed reviews, remaining artifacts, and any revision request for the current attempt.

**Tech Stack:** Python 3.14, uv, LangGraph, DuckDB, Vega-Lite rendering, Codex headless adapter, pytest, Ruff, Pyright.

---

## Non-Negotiable Design Decisions

- The framer produces multiple planned chart artifacts. It does not pick one hypothesis.
- The builder never chooses from the plan. The harness passes exactly one current artifact request to the builder.
- The visual reviewer reviews exactly one rendered image at a time, but it also receives the full plan and prior review decisions so it does not request an already-planned future artifact as a revision of the current one.
- Revision budget is per artifact, not global. One failed artifact can get one rebuild without consuming the budget for later artifacts.
- Final run success means every planned artifact passed its visual review gate.
- The first implementation supports `artifact_type = "chart"` only. Table artifacts need a different non-image review path and should not be half-supported in this loop.
- Tests must verify outcomes and saved context artifacts, not exact prompt text.

## File Structure

- Modify `eda_artifacts/codex.py`
  - Update role dataclasses and strict JSON schemas.
  - Add `artifact_id` to builder and reviewer outputs.
  - Replace `hypotheses` / `artifact_requests` schema with ordered `artifact_plan`.

- Modify `eda_artifacts/prompts.py`
  - Update framer prompt to emit an ordered chart artifact plan.
  - Update builder prompt so it builds exactly the current artifact request from a context file.
  - Update visual reviewer prompt so it judges the current image against the current artifact request and uses prior reviews/remaining artifacts to avoid misplaced revision requests.

- Modify `eda_artifacts/graph.py`
  - Replace single-artifact state paths with per-artifact attempt paths.
  - Add loop nodes for selecting the next artifact and retrying the same artifact once.
  - Write builder and reviewer context JSON files.
  - Write deterministic final summary only after all artifact reviews pass.

- Modify `eda_artifacts/lineage.py`
  - Discover artifact IDs and attempts from the run directory.
  - Record dependencies for every per-artifact build, execution, render, review, and final summary.

- Modify `eda_artifacts/cli.py`
  - Update fake adapter output to include two chart artifacts and matching builder/reviewer responses.

- Modify `tests/test_codex_adapter.py`
  - Test strict schemas for the new framer, builder, and reviewer outputs.

- Modify `tests/test_graph.py`
  - Test multi-artifact pass path.
  - Test per-artifact revision then continue.
  - Test per-artifact revision exhaustion stops later artifacts.
  - Test reviewer context includes current artifact, full plan, previous decisions, and remaining artifacts.

- Modify `tests/test_cli.py`
  - Update fake CLI smoke expectations for per-artifact folders.

- Modify `README.md`, `docs/goals.md`, and `docs/superpowers/specs/2026-06-28-eda-artifacts-mvp-design.md`
  - Document artifact loop semantics and per-artifact review context.

---

## Target Artifact Shape

The framer output must become:

```json
{
  "user_question": "Assess whether monthly_rent_usd has a simple distribution.",
  "analysis_goal": "Determine whether the rent target distribution can be treated as a simple single-population distribution before downstream modeling.",
  "artifact_plan": [
    {
      "id": "distribution_histogram",
      "purpose": "Inspect gross distribution shape and modality.",
      "statistical_check": "Does monthly_rent_usd appear unimodal, multimodal, skewed, or inconclusive?",
      "artifact_type": "chart",
      "expected_chart_family": "histogram",
      "required_fields": ["rent_bin", "listing_count"],
      "interpretation_limits": [
        "A single bin width may not establish modality.",
        "Sparse tails may be hard to judge without an alternate view."
      ]
    },
    {
      "id": "bin_sensitivity",
      "purpose": "Check whether apparent shape is stable under alternate bin widths.",
      "statistical_check": "Does the apparent modality depend on bin width?",
      "artifact_type": "chart",
      "expected_chart_family": "small_multiple_histograms",
      "required_fields": ["bin_width", "rent_bin", "listing_count"],
      "interpretation_limits": [
        "This view checks visual stability, not formal mixture-model fit."
      ]
    }
  ],
  "stop_conditions": [
    "Do not make prediction, causality, regression, or price-driver claims."
  ]
}
```

The builder output must become:

```json
{
  "artifact_id": "distribution_histogram",
  "sql": "SELECT ...",
  "chart_spec": "{\"mark\":\"bar\",\"encoding\":{...}}"
}
```

The reviewer output must become:

```json
{
  "artifact_id": "distribution_histogram",
  "verdict": "pass",
  "visual_adequacy": ["Axes and marks are readable."],
  "statistical_findings": ["The rendered histogram shows more than one visible concentration."],
  "limitations": ["A single bin width cannot rule out binning artifacts."],
  "carry_forward_notes": ["The planned bin_sensitivity artifact should address bin-width dependence."],
  "required_revision": "",
  "report_markdown": "# distribution_histogram\n..."
}
```

---

## Target Run Directory Shape

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
    distribution_histogram/
      attempt-1/
        build-context.json
        prompt.md
        output.schema.json
        output.json
        query.sql
        chart.vegalite.json
    bin_sensitivity/
      attempt-1/
        build-context.json
        prompt.md
        output.schema.json
        output.json
        query.sql
        chart.vegalite.json
  03-execution/
    distribution_histogram/
      attempt-1/
        result.parquet
        result.summary.json
    bin_sensitivity/
      attempt-1/
        result.parquet
        result.summary.json
  04-render/
    distribution_histogram/
      attempt-1/
        chart.png
    bin_sensitivity/
      attempt-1/
        chart.png
  05-visual-reviewer/
    distribution_histogram/
      attempt-1/
        review-context.json
        prompt.md
        image-inputs.json
        output.schema.json
        output.json
        report.md
    bin_sensitivity/
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

---

## Task 1: Update Role Output Schemas

**Files:**
- Modify: `eda_artifacts/codex.py`
- Test: `tests/test_codex_adapter.py`

- [ ] **Step 1: Write failing schema tests**

Replace `test_eda_framer_schema_requires_question_hypotheses_and_artifact_requests` with:

```python
def test_eda_framer_schema_requires_ordered_artifact_plan():
    schema = ROLE_OUTPUT_SCHEMAS["eda_framer"]
    object_schemas = _collect_object_schemas(schema)
    artifact_item = schema["properties"]["artifact_plan"]["items"]

    assert schema["required"] == [
        "user_question",
        "analysis_goal",
        "artifact_plan",
        "stop_conditions",
    ]
    assert schema["properties"]["artifact_plan"]["minItems"] == 1
    assert artifact_item["required"] == [
        "id",
        "purpose",
        "statistical_check",
        "artifact_type",
        "expected_chart_family",
        "required_fields",
        "interpretation_limits",
    ]
    assert artifact_item["properties"]["artifact_type"]["enum"] == ["chart"]
    for object_schema in object_schemas:
        assert object_schema["additionalProperties"] is False
```

Add:

```python
def test_artifact_builder_schema_requires_artifact_id_sql_and_chart_spec():
    schema = ROLE_OUTPUT_SCHEMAS["artifact_builder"]
    object_schemas = _collect_object_schemas(schema)

    assert schema["required"] == ["artifact_id", "sql", "chart_spec"]
    assert schema["properties"]["artifact_id"]["type"] == "string"
    assert schema["properties"]["chart_spec"]["type"] == "string"
    for object_schema in object_schemas:
        assert object_schema["additionalProperties"] is False
```

Replace `test_visual_reviewer_schema_requires_chart_grounded_report` with:

```python
def test_visual_reviewer_schema_requires_contextual_chart_review_fields():
    schema = ROLE_OUTPUT_SCHEMAS["visual_reviewer"]
    object_schemas = _collect_object_schemas(schema)

    assert schema["required"] == [
        "artifact_id",
        "verdict",
        "visual_adequacy",
        "statistical_findings",
        "limitations",
        "carry_forward_notes",
        "required_revision",
        "report_markdown",
    ]
    assert schema["properties"]["verdict"]["enum"] == ["pass", "revise"]
    for field in [
        "visual_adequacy",
        "statistical_findings",
        "limitations",
        "carry_forward_notes",
    ]:
        assert schema["properties"][field]["type"] == "array"
    for object_schema in object_schemas:
        assert object_schema["additionalProperties"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_codex_adapter.py::test_eda_framer_schema_requires_ordered_artifact_plan tests/test_codex_adapter.py::test_artifact_builder_schema_requires_artifact_id_sql_and_chart_spec tests/test_codex_adapter.py::test_visual_reviewer_schema_requires_contextual_chart_review_fields -v
```

Expected: fail because schemas and dataclasses still use `hypotheses`, `artifact_requests`, and reviewer fields without context.

- [ ] **Step 3: Update dataclasses and schemas**

In `eda_artifacts/codex.py`, replace role dataclasses with:

```python
@dataclass(frozen=True)
class EdaFramerOutput:
    user_question: str
    analysis_goal: str
    artifact_plan: list[dict[str, Any]]
    stop_conditions: list[str]


@dataclass(frozen=True)
class ArtifactBuilderOutput:
    artifact_id: str
    sql: str
    chart_spec: dict[str, Any]


@dataclass(frozen=True)
class VisualReviewerOutput:
    artifact_id: str
    verdict: str
    visual_adequacy: list[str]
    statistical_findings: list[str]
    limitations: list[str]
    carry_forward_notes: list[str]
    required_revision: str
    report_markdown: str
```

Update `ROLE_OUTPUT_SCHEMAS["eda_framer"]` to require `user_question`, `analysis_goal`, `artifact_plan`, and `stop_conditions`. The `artifact_plan.items` object must be strict and include exactly the fields listed in the failing test.

Update `ROLE_OUTPUT_SCHEMAS["artifact_builder"]` to require `artifact_id`, `sql`, and `chart_spec`.

Update `ROLE_OUTPUT_SCHEMAS["visual_reviewer"]` to require all contextual reviewer fields in the failing test.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_codex_adapter.py -v
```

Expected: adapter tests pass after updating test fixtures for the new dataclass fields.

- [ ] **Step 5: Commit**

```bash
git add eda_artifacts/codex.py tests/test_codex_adapter.py
git commit -m "Define multi-artifact role schemas"
```

---

## Task 2: Add Artifact ID Validation And Per-Artifact Path Helpers

**Files:**
- Modify: `eda_artifacts/graph.py`
- Test: `tests/test_graph.py`

- [ ] **Step 1: Write failing tests for artifact ID validation**

Add to `tests/test_graph.py`:

```python
def test_artifact_ids_cannot_create_nested_paths(tmp_path):
    framer = EdaFramerOutput(
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
        analysis_goal="Check distribution shape.",
        artifact_plan=[
            {
                "id": "../bad",
                "purpose": "Break path containment.",
                "statistical_check": "Invalid artifact id should fail.",
                "artifact_type": "chart",
                "expected_chart_family": "histogram",
                "required_fields": ["rent_bin", "listing_count"],
                "interpretation_limits": [],
            }
        ],
        stop_conditions=[],
    )
    adapter = FakeCodexAdapter({"eda_framer": [framer]})

    with pytest.raises(ValueError, match="Invalid artifact id"):
        run_multimodal_trial(
            run_root=tmp_path,
            run_id="bad-artifact-id",
            adapter=adapter,
            user_question="Assess whether monthly_rent_usd has a simple distribution.",
        )
```

Add `import pytest` to the top of `tests/test_graph.py`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_graph.py::test_artifact_ids_cannot_create_nested_paths -v
```

Expected: fail because graph does not validate artifact IDs yet.

- [ ] **Step 3: Add validation helper**

In `eda_artifacts/graph.py`, add:

```python
import re
from collections.abc import Mapping


_ARTIFACT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def _validate_artifact_id(value: object) -> str:
    if not isinstance(value, str) or not _ARTIFACT_ID_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid artifact id: {value!r}")
    return value


def _artifact_request_id(artifact_request: Mapping[str, Any]) -> str:
    return _validate_artifact_id(artifact_request.get("id"))
```

Call `_artifact_request_id` for every artifact in the framer output immediately after `_coerce_framer`, before writing `01-eda-framer/output.json`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_graph.py::test_artifact_ids_cannot_create_nested_paths -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add eda_artifacts/graph.py tests/test_graph.py
git commit -m "Validate artifact ids"
```

---

## Task 3: Implement Multi-Artifact Pass Loop

**Files:**
- Modify: `eda_artifacts/graph.py`
- Modify: `tests/test_graph.py`

- [ ] **Step 1: Replace graph fixtures with a two-artifact plan**

In `tests/test_graph.py`, replace `_framer_output()` with a two-artifact plan:

```python
def _framer_output():
    return EdaFramerOutput(
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
        analysis_goal=(
            "Evaluate whether the target distribution is simple enough for later "
            "modeling claims."
        ),
        artifact_plan=[
            {
                "id": "distribution_histogram",
                "purpose": "Inspect gross distribution shape and modality.",
                "statistical_check": (
                    "Does monthly_rent_usd appear unimodal, multimodal, skewed, "
                    "or inconclusive?"
                ),
                "artifact_type": "chart",
                "expected_chart_family": "histogram",
                "required_fields": ["rent_bin", "listing_count"],
                "interpretation_limits": [
                    "A single bin width may not establish modality."
                ],
            },
            {
                "id": "bin_sensitivity",
                "purpose": "Check whether apparent shape is stable under bin changes.",
                "statistical_check": "Does apparent modality depend on bin width?",
                "artifact_type": "chart",
                "expected_chart_family": "small_multiple_histograms",
                "required_fields": ["bin_width", "rent_bin", "listing_count"],
                "interpretation_limits": [
                    "This checks visual stability, not formal mixture-model fit."
                ],
            },
        ],
        stop_conditions=["Do not make regression claims before visual review"],
    )
```

Replace `_builder_output()` with:

```python
def _builder_output(artifact_id="distribution_histogram"):
    if artifact_id == "bin_sensitivity":
        sql = """
        SELECT
          250 AS bin_width,
          floor(monthly_rent_usd / 250) * 250 AS rent_bin,
          count(*) AS listing_count
        FROM dataset
        GROUP BY 1, 2
        UNION ALL
        SELECT
          500 AS bin_width,
          floor(monthly_rent_usd / 500) * 500 AS rent_bin,
          count(*) AS listing_count
        FROM dataset
        GROUP BY 1, 2
        ORDER BY bin_width, rent_bin
        """
        chart_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {
                "x": {"field": "rent_bin", "type": "ordinal"},
                "y": {"field": "listing_count", "type": "quantitative"},
                "column": {"field": "bin_width", "type": "nominal"},
            },
        }
    else:
        sql = """
        SELECT
          floor(monthly_rent_usd / 250) * 250 AS rent_bin,
          count(*) AS listing_count
        FROM dataset
        GROUP BY 1
        ORDER BY 1
        """
        chart_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {
                "x": {"field": "rent_bin", "type": "ordinal"},
                "y": {"field": "listing_count", "type": "quantitative"},
            },
        }
    return ArtifactBuilderOutput(
        artifact_id=artifact_id,
        sql=sql,
        chart_spec=chart_spec,
    )
```

Replace `_reviewer_output()` with:

```python
def _reviewer_output(
    *,
    artifact_id="distribution_histogram",
    verdict="pass",
    visual_adequacy=None,
    statistical_findings=None,
    limitations=None,
    carry_forward_notes=None,
    required_revision="",
    report_markdown=None,
):
    return VisualReviewerOutput(
        artifact_id=artifact_id,
        verdict=verdict,
        visual_adequacy=visual_adequacy or ["The chart is readable."],
        statistical_findings=statistical_findings or [
            "The chart supports an initial distribution-shape assessment."
        ],
        limitations=limitations or ["The chart is one view of the distribution."],
        carry_forward_notes=carry_forward_notes or [],
        required_revision=required_revision,
        report_markdown=report_markdown
        or f"# {artifact_id}\nThe rendered chart supports the requested check.",
    )
```

- [ ] **Step 2: Write failing multi-artifact pass test**

Replace `test_pass_review_run_produces_artifacts_and_lineage` expectations with per-artifact paths:

```python
def test_pass_review_run_produces_each_planned_artifact(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output("distribution_histogram"),
                _builder_output("bin_sensitivity"),
            ],
            "visual_reviewer": [
                _reviewer_output(artifact_id="distribution_histogram"),
                _reviewer_output(artifact_id="bin_sensitivity"),
            ],
        }
    )

    state = run_multimodal_trial(
        run_root=tmp_path,
        run_id="pass-run",
        adapter=adapter,
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
    )

    run_dir = tmp_path / "multimodal" / "pass-run"
    assert state["status"] == "passed_visual_gate"
    for artifact_id in ["distribution_histogram", "bin_sensitivity"]:
        assert (
            run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "query.sql"
        ).exists()
        assert (
            run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "chart.vegalite.json"
        ).exists()
        assert (
            run_dir / "03-execution" / artifact_id / "attempt-1" / "result.parquet"
        ).exists()
        assert (
            run_dir / "04-render" / artifact_id / "attempt-1" / "chart.png"
        ).exists()
        assert (
            run_dir / "05-visual-reviewer" / artifact_id / "attempt-1" / "output.json"
        ).exists()
        assert (
            run_dir / "05-visual-reviewer" / artifact_id / "attempt-1" / "report.md"
        ).exists()

    assert (run_dir / "06-synthesis" / "report.md").exists()
    builder_requests = [
        request for request in adapter.requests if request.role == "artifact_builder"
    ]
    review_requests = [
        request for request in adapter.requests if request.role == "visual_reviewer"
    ]
    assert len(builder_requests) == 2
    assert len(review_requests) == 2
    assert review_requests[0].images == [
        run_dir / "04-render" / "distribution_histogram" / "attempt-1" / "chart.png"
    ]
    assert review_requests[1].images == [
        run_dir / "04-render" / "bin_sensitivity" / "attempt-1" / "chart.png"
    ]
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_graph.py::test_pass_review_run_produces_each_planned_artifact -v
```

Expected: fail because graph only builds one artifact and uses `attempt-1` directly under each stage.

- [ ] **Step 4: Update graph state and routing**

In `TrialState`, replace single global attempt fields with:

```python
artifact_plan: list[dict[str, Any]]
current_artifact_index: int
current_artifact: dict[str, Any]
current_artifact_id: str
current_attempt: int
artifact_attempts: dict[str, int]
artifact_reviews: list[dict[str, Any]]
artifact_statuses: dict[str, str]
builder_context_path: Path
review_context_path: Path
final_report_path: Path
```

Keep the existing path fields for current artifact execution:

```python
query_path: Path
result_path: Path
result_summary_path: Path
chart_spec_path: Path
render_path: Path
report_path: Path
review_path: Path
```

Add graph node `select_next_artifact` after `run_eda_framer`. Route:

```text
run_eda_framer -> select_next_artifact
select_next_artifact -> build_artifacts if artifacts remain
select_next_artifact -> finalize_run if all artifacts passed
run_visual_reviewer -> build_artifacts if revise current artifact
run_visual_reviewer -> select_next_artifact if current artifact passed
run_visual_reviewer -> finalize_run if revision budget exhausted
```

Implement `_select_next_artifact`:

```python
def _select_next_artifact(state: TrialState) -> TrialState:
    if state["current_artifact_index"] >= len(state["artifact_plan"]):
        state["status"] = "passed_visual_gate"
        return state
    current_artifact = state["artifact_plan"][state["current_artifact_index"]]
    artifact_id = _artifact_request_id(current_artifact)
    state["current_artifact"] = current_artifact
    state["current_artifact_id"] = artifact_id
    state["current_attempt"] = state["artifact_attempts"].get(artifact_id, 1)
    _set_artifact_attempt_paths(state, artifact_id, state["current_attempt"])
    state["status"] = "running"
    return state
```

Implement `_route_after_select`:

```python
def _route_after_select(state: TrialState) -> str:
    if state["status"] == "passed_visual_gate":
        return "finalize_run"
    return "build_artifacts"
```

Implement `_route_after_review`:

```python
def _route_after_review(state: TrialState) -> str:
    if state["status"] == "revision_requested":
        return "build_artifacts"
    if state["status"] == "revision_budget_exhausted":
        return "finalize_run"
    return "select_next_artifact"
```

Implement per-artifact paths:

```python
def _set_artifact_attempt_paths(state: TrialState, artifact_id: str, attempt: int) -> None:
    state["builder_context_path"] = (
        _builder_dir(state, artifact_id, attempt) / "build-context.json"
    )
    state["query_path"] = _builder_dir(state, artifact_id, attempt) / "query.sql"
    state["chart_spec_path"] = (
        _builder_dir(state, artifact_id, attempt) / "chart.vegalite.json"
    )
    state["result_path"] = (
        _execution_dir(state, artifact_id, attempt) / "result.parquet"
    )
    state["result_summary_path"] = (
        _execution_dir(state, artifact_id, attempt) / "result.summary.json"
    )
    state["render_path"] = _render_dir(state, artifact_id, attempt) / "chart.png"
    state["review_context_path"] = (
        _reviewer_dir(state, artifact_id, attempt) / "review-context.json"
    )
    state["report_path"] = _reviewer_dir(state, artifact_id, attempt) / "report.md"
    state["review_path"] = _reviewer_dir(state, artifact_id, attempt) / "output.json"
```

Change directory helpers to:

```python
def _builder_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "02-artifact-builder" / artifact_id / f"attempt-{attempt}"


def _execution_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "03-execution" / artifact_id / f"attempt-{attempt}"


def _render_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "04-render" / artifact_id / f"attempt-{attempt}"


def _reviewer_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "05-visual-reviewer" / artifact_id / f"attempt-{attempt}"
```

In `_run_eda_framer`, after coercion:

```python
for artifact_request in output.artifact_plan:
    _artifact_request_id(artifact_request)
state["artifact_plan"] = output.artifact_plan
```

In `_run_visual_reviewer`, on pass:

```python
review_payload = asdict(output)
state["artifact_reviews"].append(review_payload)
state["artifact_statuses"][output.artifact_id] = "passed"
state["current_artifact_index"] += 1
state["latest_revision_request"] = ""
state["status"] = "artifact_passed"
```

Add `from dataclasses import asdict`.

- [ ] **Step 5: Write deterministic final summary**

In `_finalize_run`, before `write_lineage`, write `06-synthesis/report.md` only if `state["status"] == "passed_visual_gate"`:

```python
def _write_final_report(state: TrialState) -> None:
    sections = ["# EDA Artifact Review Summary\n"]
    for review in state["artifact_reviews"]:
        sections.append(f"## {review['artifact_id']}\n")
        sections.append(review["report_markdown"].strip())
        sections.append("\n")
    _write_text(state["final_report_path"], "\n".join(sections).strip() + "\n")
```

This is deterministic aggregation, not another LLM role.

- [ ] **Step 6: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_graph.py::test_pass_review_run_produces_each_planned_artifact -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add eda_artifacts/graph.py tests/test_graph.py
git commit -m "Loop over planned artifacts"
```

---

## Task 4: Persist Builder And Reviewer Context Artifacts

**Files:**
- Modify: `eda_artifacts/graph.py`
- Modify: `eda_artifacts/prompts.py`
- Test: `tests/test_graph.py`

- [ ] **Step 1: Write failing context test**

Add:

```python
def test_reviewer_context_includes_plan_previous_reviews_and_remaining_artifacts(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output("distribution_histogram"),
                _builder_output("bin_sensitivity"),
            ],
            "visual_reviewer": [
                _reviewer_output(
                    artifact_id="distribution_histogram",
                    carry_forward_notes=[
                        "The planned bin_sensitivity artifact should address bin-width dependence."
                    ],
                ),
                _reviewer_output(artifact_id="bin_sensitivity"),
            ],
        }
    )

    run_multimodal_trial(
        run_root=tmp_path,
        run_id="context-run",
        adapter=adapter,
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
    )

    run_dir = tmp_path / "multimodal" / "context-run"
    first_context = json.loads(
        (
            run_dir
            / "05-visual-reviewer"
            / "distribution_histogram"
            / "attempt-1"
            / "review-context.json"
        ).read_text()
    )
    second_context = json.loads(
        (
            run_dir
            / "05-visual-reviewer"
            / "bin_sensitivity"
            / "attempt-1"
            / "review-context.json"
        ).read_text()
    )

    assert first_context["current_artifact"]["id"] == "distribution_histogram"
    assert [artifact["id"] for artifact in first_context["artifact_plan"]] == [
        "distribution_histogram",
        "bin_sensitivity",
    ]
    assert first_context["previous_reviews"] == []
    assert [artifact["id"] for artifact in first_context["remaining_artifacts"]] == [
        "bin_sensitivity"
    ]

    assert second_context["current_artifact"]["id"] == "bin_sensitivity"
    assert second_context["previous_reviews"][0]["artifact_id"] == "distribution_histogram"
    assert second_context["remaining_artifacts"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_graph.py::test_reviewer_context_includes_plan_previous_reviews_and_remaining_artifacts -v
```

Expected: fail because context JSON files are not written yet.

- [ ] **Step 3: Write context helpers**

In `eda_artifacts/graph.py`, add:

```python
def _remaining_artifacts(state: TrialState) -> list[dict[str, Any]]:
    return state["artifact_plan"][state["current_artifact_index"] + 1 :]


def _build_context(state: TrialState) -> dict[str, Any]:
    return {
        "user_question": state["user_question"],
        "analysis_goal": _analysis_goal(state),
        "artifact_plan": state["artifact_plan"],
        "current_artifact": state["current_artifact"],
        "previous_reviews": state["artifact_reviews"],
        "remaining_artifacts": _remaining_artifacts(state),
        "revision_request": state["latest_revision_request"],
    }


def _review_context(state: TrialState) -> dict[str, Any]:
    return {
        "user_question": state["user_question"],
        "analysis_goal": _analysis_goal(state),
        "artifact_plan": state["artifact_plan"],
        "current_artifact": state["current_artifact"],
        "previous_reviews": state["artifact_reviews"],
        "remaining_artifacts": _remaining_artifacts(state),
        "revision_request": state["latest_revision_request"],
    }


def _analysis_goal(state: TrialState) -> str:
    framing = json.loads(state["framing_path"].read_text())
    return str(framing["analysis_goal"])
```

Before invoking builder, write:

```python
_write_json(state["builder_context_path"], _build_context(state))
```

Before invoking reviewer, write:

```python
_write_json(state["review_context_path"], _review_context(state))
```

- [ ] **Step 4: Update prompt builders to reference context files**

Change signatures in `eda_artifacts/prompts.py`:

```python
def build_artifact_builder_prompt(
    *,
    build_context_path: Path | str,
) -> str:
```

Prompt content must say:

```text
Build only the current_artifact described in the build context artifact.
Do not choose another artifact from artifact_plan.
If revision_request is non-empty, revise the same current_artifact.
Return artifact_id matching current_artifact.id, sql, and chart_spec.
```

Change visual reviewer signature:

```python
def build_visual_reviewer_prompt(*, review_context_path: Path | str) -> str:
```

Prompt content must say:

```text
Review only current_artifact against the attached rendered chart image.
Use artifact_plan, previous_reviews, and remaining_artifacts to distinguish:
- a defect in this chart that requires revise
- a limitation that is already addressed by a remaining planned artifact
Do not ask for a chart that already appears in remaining_artifacts unless the current chart itself is unreadable or fails its own purpose.
```

Do not add tests that assert exact prompt text. The saved context JSON is the tested contract.

- [ ] **Step 5: Run context test to verify it passes**

Run:

```bash
uv run pytest tests/test_graph.py::test_reviewer_context_includes_plan_previous_reviews_and_remaining_artifacts -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add eda_artifacts/graph.py eda_artifacts/prompts.py tests/test_graph.py
git commit -m "Pass artifact context to reviewer"
```

---

## Task 5: Implement Per-Artifact Revision Budget

**Files:**
- Modify: `eda_artifacts/graph.py`
- Modify: `tests/test_graph.py`

- [ ] **Step 1: Write failing test for revise then continue**

Replace `test_revise_review_runs_one_builder_revision_and_second_review` with:

```python
def test_revise_review_rebuilds_same_artifact_then_continues_to_next(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output("distribution_histogram"),
                _builder_output("distribution_histogram"),
                _builder_output("bin_sensitivity"),
            ],
            "visual_reviewer": [
                _reviewer_output(
                    artifact_id="distribution_histogram",
                    verdict="revise",
                    visual_adequacy=["The chart is readable."],
                    statistical_findings=[],
                    limitations=["The binning hides the shape."],
                    required_revision="Use clearer bins for the same artifact.",
                    report_markdown="# distribution_histogram\nNeeds revision.",
                ),
                _reviewer_output(artifact_id="distribution_histogram"),
                _reviewer_output(artifact_id="bin_sensitivity"),
            ],
        }
    )

    state = run_multimodal_trial(
        run_root=tmp_path,
        run_id="revise-run",
        adapter=adapter,
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
    )

    run_dir = tmp_path / "multimodal" / "revise-run"
    assert state["status"] == "passed_visual_gate"
    assert (
        run_dir / "02-artifact-builder" / "distribution_histogram" / "attempt-2" / "query.sql"
    ).exists()
    assert (
        run_dir / "02-artifact-builder" / "bin_sensitivity" / "attempt-1" / "query.sql"
    ).exists()
    assert not (
        run_dir / "02-artifact-builder" / "bin_sensitivity" / "attempt-2"
    ).exists()
```

- [ ] **Step 2: Write failing test for exhaustion stops later artifacts**

Replace `test_second_revise_review_exhausts_revision_budget` with:

```python
def test_second_revise_for_same_artifact_exhausts_budget_and_skips_later_artifacts(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output("distribution_histogram"),
                _builder_output("distribution_histogram"),
            ],
            "visual_reviewer": [
                _reviewer_output(
                    artifact_id="distribution_histogram",
                    verdict="revise",
                    required_revision="Make shape clearer.",
                    report_markdown="# distribution_histogram\nNeeds revision.",
                ),
                _reviewer_output(
                    artifact_id="distribution_histogram",
                    verdict="revise",
                    required_revision="Still not clear enough.",
                    report_markdown="# distribution_histogram\nStill needs revision.",
                ),
            ],
        }
    )

    state = run_multimodal_trial(
        run_root=tmp_path,
        run_id="fail-run",
        adapter=adapter,
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
    )

    run_dir = tmp_path / "multimodal" / "fail-run"
    assert state["status"] == "revision_budget_exhausted"
    assert state["artifact_statuses"]["distribution_histogram"] == "revision_budget_exhausted"
    assert not (run_dir / "02-artifact-builder" / "bin_sensitivity").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_graph.py::test_revise_review_rebuilds_same_artifact_then_continues_to_next tests/test_graph.py::test_second_revise_for_same_artifact_exhausts_budget_and_skips_later_artifacts -v
```

Expected: fail until per-artifact attempts are tracked.

- [ ] **Step 4: Implement per-artifact revision handling**

In `_run_visual_reviewer`, use:

```python
artifact_id = state["current_artifact_id"]
attempt = state["current_attempt"]
if output.artifact_id != artifact_id:
    raise ValueError(
        f"Reviewer returned artifact_id {output.artifact_id!r}, expected {artifact_id!r}."
    )
if output.verdict == "pass":
    review_payload = asdict(output)
    state["artifact_reviews"].append(review_payload)
    state["artifact_statuses"][artifact_id] = "passed"
    state["current_artifact_index"] += 1
    state["latest_revision_request"] = ""
    state["status"] = "artifact_passed"
elif attempt >= 2:
    state["artifact_statuses"][artifact_id] = "revision_budget_exhausted"
    state["latest_revision_request"] = output.required_revision
    state["status"] = "revision_budget_exhausted"
else:
    state["artifact_attempts"][artifact_id] = attempt + 1
    state["current_attempt"] = attempt + 1
    state["latest_revision_request"] = output.required_revision
    state["status"] = "revision_requested"
```

Add the same artifact ID validation to `_build_artifacts`:

```python
if output.artifact_id != state["current_artifact_id"]:
    raise ValueError(
        f"Builder returned artifact_id {output.artifact_id!r}, "
        f"expected {state['current_artifact_id']!r}."
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_graph.py::test_revise_review_rebuilds_same_artifact_then_continues_to_next tests/test_graph.py::test_second_revise_for_same_artifact_exhausts_budget_and_skips_later_artifacts -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add eda_artifacts/graph.py tests/test_graph.py
git commit -m "Track revisions per artifact"
```

---

## Task 6: Update Lineage For Per-Artifact Artifacts

**Files:**
- Modify: `eda_artifacts/lineage.py`
- Modify: `tests/test_graph.py`

- [ ] **Step 1: Write failing lineage assertions**

In `test_pass_review_run_produces_each_planned_artifact`, after loading lineage:

```python
lineage = json.loads((run_dir / "lineage.json").read_text())
assert lineage["status"] == "passed_visual_gate"
assert lineage["artifact_statuses"] == {
    "bin_sensitivity": "passed",
    "distribution_histogram": "passed",
}
assert lineage["dependencies"][
    "02-artifact-builder/distribution_histogram/attempt-1/output.json"
] == [
    "02-artifact-builder/distribution_histogram/attempt-1/prompt.md",
    "02-artifact-builder/distribution_histogram/attempt-1/build-context.json",
    "02-artifact-builder/distribution_histogram/attempt-1/output.schema.json",
    "01-eda-framer/output.json",
]
assert lineage["dependencies"][
    "05-visual-reviewer/bin_sensitivity/attempt-1/output.json"
] == [
    "05-visual-reviewer/bin_sensitivity/attempt-1/prompt.md",
    "05-visual-reviewer/bin_sensitivity/attempt-1/review-context.json",
    "05-visual-reviewer/bin_sensitivity/attempt-1/image-inputs.json",
    "05-visual-reviewer/bin_sensitivity/attempt-1/output.schema.json",
    "04-render/bin_sensitivity/attempt-1/chart.png",
]
assert lineage["dependencies"]["06-synthesis/report.md"] == [
    "05-visual-reviewer/bin_sensitivity/attempt-1/report.md",
    "05-visual-reviewer/distribution_histogram/attempt-1/report.md",
]
```

- [ ] **Step 2: Run lineage test to verify it fails**

Run:

```bash
uv run pytest tests/test_graph.py::test_pass_review_run_produces_each_planned_artifact -v
```

Expected: fail because lineage still assumes global attempts.

- [ ] **Step 3: Update lineage writer signature**

Change:

```python
def write_lineage(run_dir: Path, *, status: str, revision_count: int) -> dict[str, Any]:
```

to:

```python
def write_lineage(
    run_dir: Path,
    *,
    status: str,
    artifact_statuses: dict[str, str],
) -> dict[str, Any]:
```

Lineage payload should include:

```python
lineage = {
    "status": status,
    "artifact_statuses": dict(sorted(artifact_statuses.items())),
    "artifacts": artifacts,
    "dependencies": _dependencies_for_artifact_attempts(run_dir),
}
```

Implement `_artifact_attempts`:

```python
def _artifact_attempts(run_dir: Path) -> list[tuple[str, int]]:
    attempts: list[tuple[str, int]] = []
    builder_root = run_dir / "02-artifact-builder"
    if not builder_root.exists():
        return attempts
    for artifact_dir in sorted(path for path in builder_root.iterdir() if path.is_dir()):
        for attempt_dir in sorted(path for path in artifact_dir.iterdir() if path.is_dir()):
            prefix = "attempt-"
            if attempt_dir.name.startswith(prefix):
                attempts.append((artifact_dir.name, int(attempt_dir.name.removeprefix(prefix))))
    return attempts
```

Implement dependency generation per `(artifact_id, attempt)`.

- [ ] **Step 4: Update graph finalize call**

In `_finalize_run`, call:

```python
write_lineage(
    state["run_dir"],
    status=state["status"],
    artifact_statuses=state["artifact_statuses"],
)
```

- [ ] **Step 5: Run lineage test to verify it passes**

Run:

```bash
uv run pytest tests/test_graph.py::test_pass_review_run_produces_each_planned_artifact -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add eda_artifacts/lineage.py eda_artifacts/graph.py tests/test_graph.py
git commit -m "Write lineage for artifact loop"
```

---

## Task 7: Update CLI Fake Adapter And Smoke Test

**Files:**
- Modify: `eda_artifacts/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI smoke expectations**

In `test_fake_cli_run_creates_multimodal_artifact_tree`, replace single-attempt path assertions with:

```python
for artifact_id in ["distribution_histogram", "bin_sensitivity"]:
    assert (
        run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "query.sql"
    ).exists()
    assert (
        run_dir / "03-execution" / artifact_id / "attempt-1" / "result.parquet"
    ).exists()
    assert (
        run_dir / "04-render" / artifact_id / "attempt-1" / "chart.png"
    ).exists()
    assert (
        run_dir / "05-visual-reviewer" / artifact_id / "attempt-1" / "report.md"
    ).exists()
assert (run_dir / "06-synthesis" / "report.md").exists()
assert json.loads((run_dir / "lineage.json").read_text())["status"] == "passed_visual_gate"
```

- [ ] **Step 2: Run CLI test to verify it fails**

Run:

```bash
uv run pytest tests/test_cli.py::test_fake_cli_run_creates_multimodal_artifact_tree -v
```

Expected: fail until fake adapter emits two artifact builders and two reviewer outputs.

- [ ] **Step 3: Update fake adapter**

In `eda_artifacts/cli.py`, make fake `EdaFramerOutput` match the two-artifact `_framer_output()` shape from graph tests.

Queue two `ArtifactBuilderOutput` objects:

```python
ArtifactBuilderOutput(
    artifact_id="distribution_histogram",
    sql="...",
    chart_spec={...},
)
ArtifactBuilderOutput(
    artifact_id="bin_sensitivity",
    sql="...",
    chart_spec={...},
)
```

Queue two `VisualReviewerOutput` objects with matching `artifact_id`.

- [ ] **Step 4: Run CLI test to verify it passes**

Run:

```bash
uv run pytest tests/test_cli.py -v
```

Expected: all CLI tests pass.

- [ ] **Step 5: Commit**

```bash
git add eda_artifacts/cli.py tests/test_cli.py
git commit -m "Update fake smoke for artifact loop"
```

---

## Task 8: Update Docs To Match The Loop

**Files:**
- Modify: `README.md`
- Modify: `docs/goals.md`
- Modify: `docs/superpowers/specs/2026-06-28-eda-artifacts-mvp-design.md`
- Modify: `AGENTS.md` only if commands change

- [ ] **Step 1: Update README run shape**

Change expected artifacts from single `attempt-1` folders to per-artifact examples:

```text
02-artifact-builder/<artifact_id>/attempt-1/query.sql
03-execution/<artifact_id>/attempt-1/result.parquet
04-render/<artifact_id>/attempt-1/chart.png
05-visual-reviewer/<artifact_id>/attempt-1/review-context.json
06-synthesis/report.md
```

State that the visual reviewer reviews one image at a time but receives the full artifact plan and prior decisions.

- [ ] **Step 2: Update goals**

In `docs/goals.md`, change success criteria to:

```text
- framer emits ordered artifact_plan
- each artifact request is built exactly once unless revised
- reviewer context includes current artifact, full plan, previous reviews, and remaining artifacts
- final success requires all planned chart artifacts to pass
```

- [ ] **Step 3: Update design spec**

In `docs/superpowers/specs/2026-06-28-eda-artifacts-mvp-design.md`, replace the single-artifact graph with:

```text
dataset profile + user question
  -> eda_framer
  -> for each artifact in artifact_plan:
       artifact_builder
       execute query
       render chart
       visual_reviewer with plan context
       optional one revision of same artifact
  -> deterministic synthesis report
  -> lineage
```

- [ ] **Step 4: Search for stale language**

Run:

```bash
rg -n "highest-priority|choose a primary|primary_question|required_checks|chart_requests|attempt-1/chart.png|single chart|one chart total" README.md AGENTS.md docs eda_artifacts tests
```

Expected: no stale single-artifact or old-schema language remains, except test helper names if they still describe current behavior accurately.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/goals.md docs/superpowers/specs/2026-06-28-eda-artifacts-mvp-design.md AGENTS.md
git commit -m "Document artifact review loop"
```

---

## Task 9: Full Verification And Smoke Run

**Files:**
- No code files unless validation exposes a defect.

- [ ] **Step 1: Run Python validation**

Run:

```bash
uv run ruff check
uv run pyright
uv run pytest tests/ -v
```

Expected:

```text
All checks passed!
0 errors, 0 warnings, 0 informations
all tests passed
```

- [ ] **Step 2: Run fake smoke outside repo**

Run:

```bash
rm -rf /tmp/eda-artifacts-loop-smoke
uv run python -m eda_artifacts.cli run \
  --adapter fake \
  --run-id loop-smoke \
  --run-root /tmp/eda-artifacts-loop-smoke \
  --question "Assess whether monthly_rent_usd has a simple distribution."
```

Expected:

```text
status=passed_visual_gate
run_dir=/tmp/eda-artifacts-loop-smoke/multimodal/loop-smoke
```

- [ ] **Step 3: Inspect smoke artifact tree**

Run:

```bash
find /tmp/eda-artifacts-loop-smoke/multimodal/loop-smoke -maxdepth 4 -type f | sort
```

Expected files include:

```text
01-eda-framer/output.json
02-artifact-builder/distribution_histogram/attempt-1/build-context.json
02-artifact-builder/bin_sensitivity/attempt-1/build-context.json
05-visual-reviewer/distribution_histogram/attempt-1/review-context.json
05-visual-reviewer/bin_sensitivity/attempt-1/review-context.json
06-synthesis/report.md
lineage.json
```

- [ ] **Step 4: Check repo cleanliness and empty directories**

Run:

```bash
git status --short
find . -path ./.git -prune -o -path ./.venv -prune -o -path ./frontend/node_modules -prune -o -type d -empty -print
```

Expected:

```text
git status shows no unstaged source changes after final commit
find prints nothing
```

- [ ] **Step 5: Final commit if validation required fixes**

If any validation fixes were needed:

```bash
git add <changed-files>
git commit -m "Stabilize artifact review loop"
```

---

## Self-Review

- Spec coverage: The plan covers ordered artifact plan, exact current-artifact builder contract, one-image reviewer loop with full plan and previous decisions, per-artifact revision budget, final success after all artifacts pass, lineage, CLI fake smoke, docs, and validation.
- Placeholder scan: No open placeholder tasks are left. Every task has concrete files, test code, implementation shape, commands, and expected results.
- Type consistency: The plan consistently uses `artifact_plan`, `artifact_id`, `analysis_goal`, `build-context.json`, `review-context.json`, `artifact_reviews`, and `artifact_statuses`.
