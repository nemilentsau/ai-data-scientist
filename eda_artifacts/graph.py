import json
import re
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypedDict, cast

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

_ARTIFACT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


class TrialState(TypedDict):
    run_dir: Path
    dataset_path: Path
    profile_path: Path
    user_question: str
    user_question_path: Path
    analysis_goal: str
    framing_path: Path
    artifact_plan: list[dict[str, Any]]
    current_artifact_index: int
    current_artifact: dict[str, Any]
    current_artifact_id: str
    current_attempt: int
    artifact_attempts: dict[str, int]
    artifact_reviews: list[dict[str, Any]]
    review_history: list[dict[str, Any]]
    artifact_statuses: dict[str, str]
    builder_context_path: Path
    query_path: Path
    result_path: Path
    result_summary_path: Path
    chart_spec_path: Path
    render_path: Path
    review_context_path: Path
    report_path: Path
    review_path: Path
    final_report_path: Path
    latest_revision_request: str
    status: str


def run_multimodal_trial(
    *,
    run_root: Path | str,
    run_id: str,
    adapter: CodexAdapter,
    user_question: str,
) -> TrialState:
    run_dir = Path(run_root) / "multimodal" / run_id
    state = _initial_state(run_dir, user_question)
    return cast(TrialState, _build_graph(adapter).invoke(state))


def _build_graph(adapter: CodexAdapter):
    graph = StateGraph(TrialState)
    graph.add_node("prepare_dataset", _prepare_dataset)
    graph.add_node(
        "run_eda_framer",
        lambda state: _run_eda_framer(cast(TrialState, state), adapter),
    )
    graph.add_node("select_next_artifact", _select_next_artifact)
    graph.add_node(
        "build_artifacts",
        lambda state: _build_artifacts(cast(TrialState, state), adapter),
    )
    graph.add_node("execute_queries", _execute_queries)
    graph.add_node("validate_and_render", _validate_and_render)
    graph.add_node(
        "run_visual_reviewer",
        lambda state: _run_visual_reviewer(cast(TrialState, state), adapter),
    )
    graph.add_node("finalize_run", _finalize_run)

    graph.set_entry_point("prepare_dataset")
    graph.add_edge("prepare_dataset", "run_eda_framer")
    graph.add_edge("run_eda_framer", "select_next_artifact")
    graph.add_conditional_edges(
        "select_next_artifact",
        _route_after_select,
        {
            "build_artifacts": "build_artifacts",
            "finalize_run": "finalize_run",
        },
    )
    graph.add_edge("build_artifacts", "execute_queries")
    graph.add_edge("execute_queries", "validate_and_render")
    graph.add_edge("validate_and_render", "run_visual_reviewer")
    graph.add_conditional_edges(
        "run_visual_reviewer",
        _route_after_review,
        {
            "build_artifacts": "build_artifacts",
            "select_next_artifact": "select_next_artifact",
            "finalize_run": "finalize_run",
        },
    )
    graph.add_edge("finalize_run", END)
    return graph.compile()


def _initial_state(run_dir: Path, user_question: str) -> TrialState:
    unset_path = run_dir / ".unset"
    return {
        "run_dir": run_dir,
        "dataset_path": run_dir / "00-dataset" / "dataset.csv",
        "profile_path": run_dir / "00-dataset" / "profile.json",
        "user_question": user_question,
        "user_question_path": run_dir / "01-eda-framer" / "user-question.txt",
        "analysis_goal": "",
        "framing_path": run_dir / "01-eda-framer" / "output.json",
        "artifact_plan": [],
        "current_artifact_index": 0,
        "current_artifact": {},
        "current_artifact_id": "",
        "current_attempt": 1,
        "artifact_attempts": {},
        "artifact_reviews": [],
        "review_history": [],
        "artifact_statuses": {},
        "builder_context_path": unset_path,
        "query_path": unset_path,
        "chart_spec_path": unset_path,
        "result_path": unset_path,
        "result_summary_path": unset_path,
        "render_path": unset_path,
        "review_context_path": unset_path,
        "report_path": unset_path,
        "review_path": unset_path,
        "final_report_path": run_dir / "06-synthesis" / "report.md",
        "latest_revision_request": "",
        "status": "running",
    }


def _prepare_dataset(state: TrialState) -> TrialState:
    generate_multimodal_dataset(state["dataset_path"])
    profile_dataset(state["dataset_path"], state["profile_path"])
    return state


def _run_eda_framer(state: TrialState, adapter: CodexAdapter) -> TrialState:
    prompt = build_framer_prompt(
        user_question=state["user_question"],
        profile_path=_artifact_ref(state, state["profile_path"]),
    )
    role_dir = state["run_dir"] / "01-eda-framer"
    _write_text(state["user_question_path"], state["user_question"].strip() + "\n")
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
    _validate_artifact_plan(output.artifact_plan)
    state["analysis_goal"] = output.analysis_goal
    state["artifact_plan"] = output.artifact_plan
    write_output_json(state["framing_path"], output)
    return state


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
    state["latest_revision_request"] = ""
    state["status"] = "running"
    return state


def _build_artifacts(state: TrialState, adapter: CodexAdapter) -> TrialState:
    _set_artifact_attempt_paths(
        state,
        state["current_artifact_id"],
        state["current_attempt"],
    )
    role_dir = _builder_dir(
        state,
        state["current_artifact_id"],
        state["current_attempt"],
    )
    _write_json(state["builder_context_path"], _artifact_context(state))
    prompt = build_artifact_builder_prompt(
        build_context_path=_artifact_ref(state, state["builder_context_path"]),
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
    if output.artifact_id != state["current_artifact_id"]:
        raise ValueError(
            f"Builder returned artifact_id {output.artifact_id!r}, "
            f"expected {state['current_artifact_id']!r}."
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
    artifact_id = state["current_artifact_id"]
    attempt = state["current_attempt"]
    role_dir = _reviewer_dir(state, artifact_id, attempt)
    _write_json(state["review_context_path"], _artifact_context(state))
    prompt = build_visual_reviewer_prompt(
        review_context_path=_artifact_ref(state, state["review_context_path"]),
    )
    _write_text(role_dir / "prompt.md", prompt)
    _write_json(
        role_dir / "image-inputs.json",
        {
            "images": [str(state["render_path"].relative_to(state["run_dir"]))],
            "review_context": str(
                state["review_context_path"].relative_to(state["run_dir"])
            ),
        },
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
    if output.artifact_id != artifact_id:
        raise ValueError(
            f"Reviewer returned artifact_id {output.artifact_id!r}, "
            f"expected {artifact_id!r}."
        )
    write_output_json(state["review_path"], output)
    _write_text(state["report_path"], output.report_markdown)

    review_payload = asdict(output)
    state["review_history"].append(review_payload)
    if output.verdict == "pass":
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
    return state


def _route_after_select(state: TrialState) -> str:
    if state["status"] == "passed_visual_gate":
        return "finalize_run"
    return "build_artifacts"


def _route_after_review(state: TrialState) -> str:
    if state["status"] == "revision_requested":
        return "build_artifacts"
    if state["status"] == "revision_budget_exhausted":
        return "finalize_run"
    return "select_next_artifact"


def _finalize_run(state: TrialState) -> TrialState:
    if state["status"] == "passed_visual_gate":
        _write_final_report(state)
    write_lineage(
        state["run_dir"],
        status=state["status"],
        artifact_statuses=state["artifact_statuses"],
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


def _artifact_ref(state: TrialState, path: Path) -> Path:
    return path.relative_to(state["run_dir"])


def _set_artifact_attempt_paths(state: TrialState, artifact_id: str, attempt: int) -> None:
    state["builder_context_path"] = (
        _builder_dir(state, artifact_id, attempt) / "build-context.json"
    )
    state["query_path"] = _builder_dir(state, artifact_id, attempt) / "query.sql"
    state["chart_spec_path"] = (
        _builder_dir(state, artifact_id, attempt) / "chart.vegalite.json"
    )
    state["result_path"] = _execution_dir(state, artifact_id, attempt) / "result.parquet"
    state["result_summary_path"] = (
        _execution_dir(state, artifact_id, attempt) / "result.summary.json"
    )
    state["render_path"] = _render_dir(state, artifact_id, attempt) / "chart.png"
    state["review_context_path"] = (
        _reviewer_dir(state, artifact_id, attempt) / "review-context.json"
    )
    state["report_path"] = _reviewer_dir(state, artifact_id, attempt) / "report.md"
    state["review_path"] = _reviewer_dir(state, artifact_id, attempt) / "output.json"


def _builder_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "02-artifact-builder" / artifact_id / f"attempt-{attempt}"


def _execution_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "03-execution" / artifact_id / f"attempt-{attempt}"


def _render_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "04-render" / artifact_id / f"attempt-{attempt}"


def _reviewer_dir(state: TrialState, artifact_id: str, attempt: int) -> Path:
    return state["run_dir"] / "05-visual-reviewer" / artifact_id / f"attempt-{attempt}"


def _remaining_artifacts(state: TrialState) -> list[dict[str, Any]]:
    return state["artifact_plan"][state["current_artifact_index"] + 1 :]


def _artifact_context(state: TrialState) -> dict[str, Any]:
    return {
        "user_question": state["user_question"],
        "analysis_goal": state["analysis_goal"],
        "artifact_plan": state["artifact_plan"],
        "current_artifact": state["current_artifact"],
        "previous_reviews": state["review_history"],
        "remaining_artifacts": _remaining_artifacts(state),
        "revision_request": state["latest_revision_request"],
    }


def _write_final_report(state: TrialState) -> None:
    sections = ["# EDA Artifact Review Summary\n"]
    for review in state["artifact_reviews"]:
        sections.append(f"## {review['artifact_id']}\n")
        sections.append(str(review["report_markdown"]).strip())
        sections.append("\n")
    _write_text(state["final_report_path"], "\n".join(sections).strip() + "\n")


def _validate_artifact_plan(artifact_plan: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    if not artifact_plan:
        raise ValueError("Artifact plan must contain at least one artifact.")
    for artifact_request in artifact_plan:
        artifact_id = _artifact_request_id(artifact_request)
        if artifact_id in seen:
            raise ValueError(f"Duplicate artifact id: {artifact_id!r}")
        seen.add(artifact_id)
        if artifact_request.get("artifact_type") != "chart":
            raise ValueError(
                f"Unsupported artifact_type for {artifact_id!r}: "
                f"{artifact_request.get('artifact_type')!r}"
            )


def _artifact_request_id(artifact_request: Mapping[str, Any]) -> str:
    return _validate_artifact_id(artifact_request.get("id"))


def _validate_artifact_id(value: object) -> str:
    if not isinstance(value, str) or not _ARTIFACT_ID_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid artifact id: {value!r}")
    return value


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
            artifact_id=output.artifact_id,
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
