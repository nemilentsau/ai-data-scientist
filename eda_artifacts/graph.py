import json
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from eda_artifacts.charts import render_chart_png, validate_vegalite_spec
from eda_artifacts.codex import (
    ArtifactBuilderOutput,
    CodexAdapter,
    CodexRoleRequest,
    EdaFramerOutput,
    VisualReviewerOutput,
    write_output_json,
    write_role_output_schema,
)
from eda_artifacts.datasets import generate_multimodal_dataset
from eda_artifacts.lineage import write_lineage
from eda_artifacts.profile import profile_dataset
from eda_artifacts.prompts import (
    build_artifact_builder_prompt,
    build_framer_prompt,
    build_visual_reviewer_prompt,
)
from eda_artifacts.sql import execute_query_artifact


class TrialState(TypedDict, total=False):
    run_dir: Path
    dataset_path: Path
    profile_path: Path
    framing_path: Path
    query_path: Path
    result_path: Path
    result_summary_path: Path
    chart_spec_path: Path
    render_path: Path
    report_path: Path
    review_path: Path
    latest_revision_request: str
    revision_count: int
    status: str


def run_multimodal_trial(
    *,
    run_root: Path | str,
    run_id: str,
    adapter: CodexAdapter,
) -> TrialState:
    run_dir = Path(run_root) / "multimodal" / run_id
    state: TrialState = {
        "run_dir": run_dir,
        "dataset_path": run_dir / "00-dataset" / "dataset.csv",
        "profile_path": run_dir / "00-dataset" / "profile.json",
        "framing_path": run_dir / "01-eda-framer" / "output.json",
        "latest_revision_request": "",
        "revision_count": 0,
        "status": "running",
    }
    _set_attempt_paths(state, 1)
    return _build_graph(adapter).invoke(state)


def _build_graph(adapter: CodexAdapter):
    graph = StateGraph(TrialState)
    graph.add_node("prepare_dataset", _prepare_dataset)
    graph.add_node("run_eda_framer", lambda state: _run_eda_framer(state, adapter))
    graph.add_node("build_artifacts", lambda state: _build_artifacts(state, adapter))
    graph.add_node("execute_queries", _execute_queries)
    graph.add_node("validate_and_render", _validate_and_render)
    graph.add_node("run_visual_reviewer", lambda state: _run_visual_reviewer(state, adapter))
    graph.add_node("finalize_run", _finalize_run)

    graph.set_entry_point("prepare_dataset")
    graph.add_edge("prepare_dataset", "run_eda_framer")
    graph.add_edge("run_eda_framer", "build_artifacts")
    graph.add_edge("build_artifacts", "execute_queries")
    graph.add_edge("execute_queries", "validate_and_render")
    graph.add_edge("validate_and_render", "run_visual_reviewer")
    graph.add_conditional_edges(
        "run_visual_reviewer",
        _route_after_review,
        {
            "build_artifacts": "build_artifacts",
            "finalize_run": "finalize_run",
        },
    )
    graph.add_edge("finalize_run", END)
    return graph.compile()


def _prepare_dataset(state: TrialState) -> TrialState:
    generate_multimodal_dataset(state["dataset_path"])
    profile_dataset(state["dataset_path"], state["profile_path"])
    return state


def _run_eda_framer(state: TrialState, adapter: CodexAdapter) -> TrialState:
    prompt = build_framer_prompt(
        dataset_path=state["dataset_path"],
        profile_path=state["profile_path"],
    )
    role_dir = state["run_dir"] / "01-eda-framer"
    _write_text(role_dir / "prompt.md", prompt)
    output = _coerce_framer(
        adapter.invoke(
            _build_role_request(
                state,
                role="eda_framer",
                prompt=prompt,
                output_path=state["framing_path"],
                schema_path=role_dir / "output.schema.json",
            )
        )
    )
    write_output_json(state["framing_path"], output)
    return state


def _build_artifacts(state: TrialState, adapter: CodexAdapter) -> TrialState:
    attempt = _current_attempt(state)
    _set_attempt_paths(state, attempt)
    role_dir = _builder_dir(state, attempt)
    prompt = build_artifact_builder_prompt(
        framing_path=state["framing_path"],
        result_summary_path=state["profile_path"],
        revision_request=state.get("latest_revision_request", ""),
    )
    _write_text(role_dir / "prompt.md", prompt)
    output = _coerce_builder(
        adapter.invoke(
            _build_role_request(
                state,
                role="artifact_builder",
                prompt=prompt,
                output_path=role_dir / "output.json",
                schema_path=role_dir / "output.schema.json",
            )
        )
    )
    write_output_json(role_dir / "output.json", output)
    _write_text(state["query_path"], output.sql.strip() + "\n")
    _write_json(state["chart_spec_path"], output.chart_spec)
    return state


def _execute_queries(state: TrialState) -> TrialState:
    execute_query_artifact(
        dataset_path=state["dataset_path"],
        sql=state["query_path"].read_text(),
        result_path=state["result_path"],
        summary_path=state["result_summary_path"],
    )
    return state


def _validate_and_render(state: TrialState) -> TrialState:
    spec = json.loads(state["chart_spec_path"].read_text())
    validate_vegalite_spec(spec)
    render_chart_png(
        spec=spec,
        result_path=state["result_path"],
        render_path=state["render_path"],
    )
    return state


def _run_visual_reviewer(state: TrialState, adapter: CodexAdapter) -> TrialState:
    attempt = _current_attempt(state)
    role_dir = _reviewer_dir(state, attempt)
    prompt = build_visual_reviewer_prompt(
        chart_spec_path=state["chart_spec_path"],
        result_summary_path=state["result_summary_path"],
    )
    _write_text(role_dir / "prompt.md", prompt)
    _write_json(
        role_dir / "image-inputs.json",
        {"images": [str(state["render_path"].relative_to(state["run_dir"]))]},
    )
    output = _coerce_reviewer(
        adapter.invoke(
            CodexRoleRequest(
                role="visual_reviewer",
                prompt=prompt,
                work_dir=state["run_dir"],
                images=[state["render_path"]],
                output_schema_path=_write_role_schema(
                    role_dir / "output.schema.json", "visual_reviewer"
                ),
                output_path=state["review_path"],
            )
        )
    )
    write_output_json(state["review_path"], output)
    _write_text(state["report_path"], output.report_markdown)
    if output.verdict == "pass":
        state["status"] = "passed_visual_gate"
        state["latest_revision_request"] = ""
    elif state["revision_count"] >= 1:
        state["status"] = "revision_budget_exhausted"
        state["latest_revision_request"] = output.required_revision
    else:
        state["revision_count"] += 1
        state["status"] = "revision_requested"
        state["latest_revision_request"] = output.required_revision
    return state


def _route_after_review(state: TrialState) -> str:
    if state["status"] == "revision_requested":
        return "build_artifacts"
    return "finalize_run"


def _finalize_run(state: TrialState) -> TrialState:
    write_lineage(
        state["run_dir"],
        status=state["status"],
        revision_count=state["revision_count"],
    )
    return state


def _build_role_request(
    state: TrialState,
    *,
    role: str,
    prompt: str,
    output_path: Path,
    schema_path: Path,
    images: list[Path] | None = None,
) -> CodexRoleRequest:
    return CodexRoleRequest(
        role=role,
        prompt=prompt,
        work_dir=state["run_dir"],
        images=images,
        output_schema_path=_write_role_schema(schema_path, role),
        output_path=output_path,
    )


def _write_role_schema(schema_path: Path, role: str) -> Path:
    write_role_output_schema(schema_path, role)
    return schema_path


def _current_attempt(state: TrialState) -> int:
    return state["revision_count"] + 1


def _set_attempt_paths(state: TrialState, attempt: int) -> None:
    state["query_path"] = _builder_dir(state, attempt) / "query.sql"
    state["chart_spec_path"] = _builder_dir(state, attempt) / "chart.vegalite.json"
    state["result_path"] = _execution_dir(state, attempt) / "result.parquet"
    state["result_summary_path"] = _execution_dir(state, attempt) / "result.summary.json"
    state["render_path"] = _render_dir(state, attempt) / "chart.png"
    state["report_path"] = _reviewer_dir(state, attempt) / "report.md"
    state["review_path"] = _reviewer_dir(state, attempt) / "output.json"


def _builder_dir(state: TrialState, attempt: int) -> Path:
    return state["run_dir"] / "02-artifact-builder" / f"attempt-{attempt}"


def _execution_dir(state: TrialState, attempt: int) -> Path:
    return state["run_dir"] / "03-execution" / f"attempt-{attempt}"


def _render_dir(state: TrialState, attempt: int) -> Path:
    return state["run_dir"] / "04-render" / f"attempt-{attempt}"


def _reviewer_dir(state: TrialState, attempt: int) -> Path:
    return state["run_dir"] / "05-visual-reviewer" / f"attempt-{attempt}"


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True))


def _coerce_framer(output: Any) -> EdaFramerOutput:
    if isinstance(output, EdaFramerOutput):
        return output
    if isinstance(output, dict):
        return EdaFramerOutput(**output)
    raise TypeError(f"Unexpected eda_framer output: {type(output)!r}")


def _coerce_builder(output: Any) -> ArtifactBuilderOutput:
    if isinstance(output, ArtifactBuilderOutput):
        return ArtifactBuilderOutput(
            sql=output.sql,
            chart_spec=_coerce_chart_spec(output.chart_spec),
        )
    if isinstance(output, dict):
        payload = dict(output)
        payload["chart_spec"] = _coerce_chart_spec(payload["chart_spec"])
        return ArtifactBuilderOutput(**payload)
    raise TypeError(f"Unexpected artifact_builder output: {type(output)!r}")


def _coerce_reviewer(output: Any) -> VisualReviewerOutput:
    if isinstance(output, VisualReviewerOutput):
        return output
    if isinstance(output, dict):
        return VisualReviewerOutput(**output)
    raise TypeError(f"Unexpected visual_reviewer output: {type(output)!r}")


def _coerce_chart_spec(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise TypeError("artifact_builder chart_spec must be a JSON object or JSON object string.")
