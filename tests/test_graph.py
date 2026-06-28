import json

from eda_artifacts.codex import (
    ArtifactBuilderOutput,
    EdaFramerOutput,
    FakeCodexAdapter,
    VisualReviewerOutput,
)
from eda_artifacts.graph import run_multimodal_trial


def _framer_output():
    return EdaFramerOutput(
        primary_question="What does the monthly rent target distribution look like?",
        required_checks=["Inspect monthly_rent_usd distribution"],
        chart_requests=["Create a rent distribution chart"],
        stop_conditions=["Do not make regression claims before visual review"],
    )


def _builder_output():
    return ArtifactBuilderOutput(
        sql="""
        SELECT
          floor(monthly_rent_usd / 250) * 250 AS rent_bin,
          count(*) AS listing_count
        FROM dataset
        GROUP BY 1
        ORDER BY 1
        """,
        chart_spec={
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {
                "x": {"field": "rent_bin", "type": "ordinal"},
                "y": {"field": "listing_count", "type": "quantitative"},
            },
        },
    )


def _reviewer_output(
    *,
    verdict="pass",
    visual_findings=None,
    required_revision="",
    report_markdown="# Report\nThe rendered chart shows a multi-peaked rent distribution.",
):
    return VisualReviewerOutput(
        verdict=verdict,
        visual_findings=visual_findings or ["The chart is visibly multi-peaked."],
        required_revision=required_revision,
        report_markdown=report_markdown,
    )


def test_pass_review_run_produces_artifacts_and_lineage(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [_builder_output()],
            "visual_reviewer": [_reviewer_output()],
        }
    )

    state = run_multimodal_trial(run_root=tmp_path, run_id="pass-run", adapter=adapter)

    run_dir = tmp_path / "multimodal" / "pass-run"
    assert state["status"] == "passed_visual_gate"
    assert (run_dir / "00-dataset" / "dataset.csv").exists()
    assert (run_dir / "00-dataset" / "profile.json").exists()
    assert (run_dir / "01-eda-framer" / "prompt.md").exists()
    assert (run_dir / "01-eda-framer" / "output.schema.json").exists()
    assert (run_dir / "01-eda-framer" / "output.json").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "prompt.md").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "output.schema.json").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "output.json").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "query.sql").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "chart.vegalite.json").exists()
    assert not (run_dir / "02-artifact-builder" / "attempt-1" / "report.md").exists()
    assert (run_dir / "03-execution" / "attempt-1" / "result.parquet").exists()
    assert (run_dir / "03-execution" / "attempt-1" / "result.summary.json").exists()
    assert (run_dir / "04-render" / "attempt-1" / "chart.png").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "prompt.md").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "image-inputs.json").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "output.schema.json").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "output.json").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "report.md").read_text().startswith(
        "# Report"
    )
    for old_name in [
        "dataset",
        "framing",
        "queries",
        "results",
        "charts",
        "renders",
        "reviews",
        "reports",
        "role_outputs",
        "schemas",
    ]:
        assert not (run_dir / old_name).exists()
    lineage = json.loads((run_dir / "lineage.json").read_text())
    assert lineage["status"] == "passed_visual_gate"
    assert "04-render/attempt-1/chart.png" in lineage["artifacts"]
    assert lineage["dependencies"]["04-render/attempt-1/chart.png"] == [
        "02-artifact-builder/attempt-1/chart.vegalite.json",
        "03-execution/attempt-1/result.parquet",
    ]
    assert "renders/target_distribution.png" not in lineage["dependencies"]
    assert adapter.requests[-1].images == [run_dir / "04-render" / "attempt-1" / "chart.png"]
    image_inputs = json.loads(
        (run_dir / "05-visual-reviewer" / "attempt-1" / "image-inputs.json").read_text()
    )
    assert image_inputs == {"images": ["04-render/attempt-1/chart.png"]}
    for request in adapter.requests:
        assert request.output_path is not None
        assert request.output_schema_path is not None
        assert request.output_schema_path.exists()


def test_revise_review_runs_one_builder_revision_and_second_review(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output(),
                _builder_output(),
            ],
            "visual_reviewer": [
                _reviewer_output(
                    verdict="revise",
                    visual_findings=["The report ignores the multi-peaked target."],
                    required_revision="State that the rent target is multimodal.",
                    report_markdown="# Report\nThe chart needs a clearer render before final claims.",
                ),
                _reviewer_output(
                    verdict="pass",
                    visual_findings=["The revised report matches the chart."],
                    required_revision="",
                    report_markdown="# Report\nThe target distribution is multimodal.",
                ),
            ],
        }
    )

    state = run_multimodal_trial(run_root=tmp_path, run_id="revise-run", adapter=adapter)

    run_dir = tmp_path / "multimodal" / "revise-run"
    assert state["status"] == "passed_visual_gate"
    assert state["revision_count"] == 1
    assert (
        run_dir / "05-visual-reviewer" / "attempt-2" / "report.md"
    ).read_text().endswith("multimodal.")
    assert not (run_dir / "02-artifact-builder" / "attempt-1" / "report.md").exists()
    assert (run_dir / "03-execution" / "attempt-1" / "result.parquet").exists()
    assert (run_dir / "03-execution" / "attempt-2" / "result.parquet").exists()
    assert (run_dir / "04-render" / "attempt-1" / "chart.png").exists()
    assert (run_dir / "04-render" / "attempt-2" / "chart.png").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "output.json").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-2" / "output.json").exists()
    builder_requests = [
        request for request in adapter.requests if request.role == "artifact_builder"
    ]
    review_requests = [request for request in adapter.requests if request.role == "visual_reviewer"]
    assert len(builder_requests) == 2
    assert len(review_requests) == 2


def test_artifact_builder_chart_spec_json_string_is_written_as_chart_object(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                {
                    "sql": _builder_output().sql,
                    "chart_spec": json.dumps(_builder_output().chart_spec),
                }
            ],
            "visual_reviewer": [_reviewer_output()],
        }
    )

    run_multimodal_trial(run_root=tmp_path, run_id="string-chart-run", adapter=adapter)

    chart_spec = json.loads(
        (
            tmp_path
            / "multimodal"
            / "string-chart-run"
            / "02-artifact-builder"
            / "attempt-1"
            / "chart.vegalite.json"
        ).read_text()
    )
    assert chart_spec["mark"] == "bar"


def test_second_revise_review_exhausts_revision_budget(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output(),
                _builder_output(),
            ],
            "visual_reviewer": [
                _reviewer_output(
                    verdict="revise",
                    visual_findings=["Missing multimodal interpretation."],
                    required_revision="Discuss modes.",
                    report_markdown="# Report\nThe chart requires revision.",
                ),
                _reviewer_output(
                    verdict="revise",
                    visual_findings=["Still missing multimodal interpretation."],
                    required_revision="Discuss modes.",
                    report_markdown="# Report\nThe revised chart still requires revision.",
                ),
            ],
        }
    )

    state = run_multimodal_trial(run_root=tmp_path, run_id="fail-run", adapter=adapter)

    assert state["status"] == "revision_budget_exhausted"
    assert state["revision_count"] == 1
