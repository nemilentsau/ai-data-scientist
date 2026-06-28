import subprocess
from pathlib import Path

import pytest
from eda_artifacts.codex import (
    ROLE_OUTPUT_SCHEMAS,
    ArtifactBuilderOutput,
    CodexExecAdapter,
    CodexRoleRequest,
    EdaFramerOutput,
    FakeCodexAdapter,
    VisualReviewerOutput,
)


def test_fake_codex_adapter_returns_queued_outputs_and_records_images(tmp_path):
    render_path = tmp_path / "chart.png"
    render_path.write_bytes(b"png")
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [
                EdaFramerOutput(
                    primary_question="What does the rent target distribution look like?",
                    required_checks=["Inspect monthly_rent_usd distribution"],
                    chart_requests=["Create target distribution chart"],
                    stop_conditions=[
                        "Do not make regression claims before target distribution review"
                    ],
                )
            ],
            "visual_reviewer": [
                VisualReviewerOutput(
                    verdict="pass",
                    visual_findings=["The rendered chart is visibly multi-peaked."],
                    required_revision="",
                    report_markdown="# Report\nThe rendered chart is visibly multi-peaked.",
                )
            ],
        }
    )

    framer_output = adapter.invoke(
        CodexRoleRequest(role="eda_framer", prompt="frame this", work_dir=tmp_path)
    )
    review_output = adapter.invoke(
        CodexRoleRequest(
            role="visual_reviewer",
            prompt="review this",
            work_dir=tmp_path,
            images=[render_path],
        )
    )

    assert isinstance(framer_output, EdaFramerOutput)
    assert isinstance(review_output, VisualReviewerOutput)
    assert framer_output.primary_question.startswith("What does")
    assert review_output.verdict == "pass"
    assert adapter.requests[1].images == [render_path]


def test_fake_codex_adapter_rejects_unqueued_role(tmp_path):
    adapter = FakeCodexAdapter({})

    with pytest.raises(IndexError, match="No queued Codex output"):
        adapter.invoke(CodexRoleRequest(role="eda_framer", prompt="frame", work_dir=tmp_path))


def test_codex_exec_command_includes_model_schema_json_and_images(tmp_path):
    image_path = tmp_path / "render.png"
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "output.json"
    image_path.write_bytes(b"png")
    adapter = CodexExecAdapter(model="gpt-5.5")
    request = CodexRoleRequest(
        role="visual_reviewer",
        prompt="Review the chart.",
        work_dir=tmp_path,
        images=[image_path],
        output_schema_path=schema_path,
        output_path=output_path,
    )

    command = adapter.build_command(request)

    assert command[:4] == ["codex", "exec", "--model", "gpt-5.5"]
    assert "--json" in command
    assert "--ephemeral" in command
    assert "--output-schema" in command
    assert str(schema_path) in command
    assert "--image" in command
    assert str(image_path) in command
    assert "-o" in command
    assert str(output_path) in command
    assert "--cd" in command
    assert str(tmp_path) in command


def test_artifact_builder_schema_is_strict_structured_output_compatible():
    object_schemas = _collect_object_schemas(ROLE_OUTPUT_SCHEMAS["artifact_builder"])

    assert object_schemas
    for schema in object_schemas:
        assert schema["additionalProperties"] is False
    assert ROLE_OUTPUT_SCHEMAS["artifact_builder"]["properties"]["chart_spec"]["type"] == "string"
    assert ROLE_OUTPUT_SCHEMAS["artifact_builder"]["required"] == ["sql", "chart_spec"]


def test_visual_reviewer_schema_requires_chart_grounded_report():
    schema = ROLE_OUTPUT_SCHEMAS["visual_reviewer"]

    assert "report_markdown" in schema["required"]
    assert schema["properties"]["report_markdown"]["type"] == "string"


def test_codex_exec_command_uses_current_cli_flags_and_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = Path("runs") / "trial"
    schema_path = run_dir / "schema.json"
    output_path = run_dir / "output.json"
    image_path = run_dir / "render.png"
    adapter = CodexExecAdapter(model="gpt-5.5")
    request = CodexRoleRequest(
        role="visual_reviewer",
        prompt="Review the chart.",
        work_dir=run_dir,
        images=[image_path],
        output_schema_path=schema_path,
        output_path=output_path,
    )

    command = adapter.build_command(request)

    assert "--ask-for-approval" not in command
    for flag in ["--cd", "--output-schema", "-o", "--image"]:
        value = command[command.index(flag) + 1]
        assert Path(value).is_absolute()


def test_codex_exec_invoke_creates_output_parent_before_running(tmp_path, monkeypatch):
    output_path = tmp_path / "missing" / "output.json"
    adapter = CodexExecAdapter(model="gpt-5.5")
    request = CodexRoleRequest(
        role="eda_framer",
        prompt="Frame the dataset.",
        work_dir=tmp_path,
        output_path=output_path,
    )

    def fake_run(*args, **kwargs):
        assert output_path.parent.exists()
        output_path.write_text('{"primary_question": "q"}')

    monkeypatch.setattr("eda_artifacts.codex.subprocess.run", fake_run)

    output = adapter.invoke(request)

    assert output == {"primary_question": "q"}


def test_codex_exec_invoke_applies_timeout(tmp_path, monkeypatch):
    output_path = tmp_path / "output.json"
    adapter = CodexExecAdapter(model="gpt-5.5", timeout_seconds=12)
    request = CodexRoleRequest(
        role="eda_framer",
        prompt="Frame the dataset.",
        work_dir=tmp_path,
        output_path=output_path,
    )

    def fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 12
        output_path.write_text('{"primary_question": "q"}')

    monkeypatch.setattr("eda_artifacts.codex.subprocess.run", fake_run)

    adapter.invoke(request)


def test_codex_exec_invoke_surfaces_stderr_on_failed_command(tmp_path, monkeypatch):
    adapter = CodexExecAdapter(model="gpt-5.5")
    request = CodexRoleRequest(
        role="eda_framer",
        prompt="Frame the dataset.",
        work_dir=tmp_path,
        output_path=tmp_path / "output.json",
    )

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0],
            output='{"event": "failed"}',
            stderr="schema rejected",
        )

    monkeypatch.setattr("eda_artifacts.codex.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="schema rejected"):
        adapter.invoke(request)


def test_artifact_builder_output_accepts_chart_spec_without_report_text():
    output = ArtifactBuilderOutput(
        sql="SELECT 1 AS rent_bin, 2 AS listing_count",
        chart_spec={"mark": "bar", "encoding": {"x": {"field": "rent_bin"}}},
    )

    assert output.sql.startswith("SELECT")
    assert output.chart_spec["mark"] == "bar"


def _collect_object_schemas(schema):
    found = []
    if schema.get("type") == "object":
        found.append(schema)
    for child in schema.get("properties", {}).values():
        found.extend(_collect_object_schemas(child))
    return found
