from pathlib import Path

import pytest

from eda_artifacts.codex import (
    ArtifactBuilderOutput,
    CodexExecAdapter,
    CodexRoleRequest,
    EdaFramerOutput,
    FakeCodexAdapter,
    VisualReviewerOutput,
)
from eda_artifacts.prompts import build_artifact_builder_prompt, build_framer_prompt


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
                    stop_conditions=["Do not make regression claims before target distribution review"],
                )
            ],
            "visual_reviewer": [
                VisualReviewerOutput(
                    verdict="pass",
                    visual_findings=["The rendered chart is visibly multi-peaked."],
                    required_revision="",
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


def test_prompt_builders_include_artifact_paths_not_old_benchmark_language(tmp_path):
    prompt = build_framer_prompt(
        dataset_path=tmp_path / "dataset.csv",
        profile_path=tmp_path / "profile.json",
    )
    builder_prompt = build_artifact_builder_prompt(
        framing_path=tmp_path / "framing.json",
        result_summary_path=tmp_path / "summary.json",
    )

    assert "multimodal" in prompt
    assert "target distribution" in prompt
    assert "benchmark score" not in prompt.lower()
    assert "Vega-Lite" in builder_prompt
    assert "PNG gallery" not in builder_prompt


def test_artifact_builder_output_accepts_chart_spec_and_report_text():
    output = ArtifactBuilderOutput(
        sql="SELECT 1 AS rent_bin, 2 AS listing_count",
        chart_spec={"mark": "bar", "encoding": {"x": {"field": "rent_bin"}}},
        report_markdown="# Report\nThe target is mixture-like.",
    )

    assert output.sql.startswith("SELECT")
    assert output.chart_spec["mark"] == "bar"
