import json

import pytest
from eda_artifacts.codex import (
    ArtifactBuilderOutput,
    EdaFramerOutput,
    FakeCodexAdapter,
    VisualReviewerOutput,
)
from eda_artifacts.graph import run_multimodal_trial


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
        statistical_findings=statistical_findings
        or ["The chart supports an initial distribution-shape assessment."],
        limitations=limitations or ["The chart is one view of the distribution."],
        carry_forward_notes=carry_forward_notes or [],
        required_revision=required_revision,
        report_markdown=report_markdown
        or f"# {artifact_id}\nThe rendered chart supports the requested check.",
    )


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
    assert (run_dir / "00-dataset" / "dataset.csv").exists()
    assert (run_dir / "00-dataset" / "profile.json").exists()
    assert (run_dir / "01-eda-framer" / "prompt.md").exists()
    assert (run_dir / "01-eda-framer" / "user-question.txt").read_text() == (
        "Assess whether monthly_rent_usd has a simple distribution.\n"
    )
    framing = json.loads((run_dir / "01-eda-framer" / "output.json").read_text())
    assert [artifact["id"] for artifact in framing["artifact_plan"]] == [
        "distribution_histogram",
        "bin_sensitivity",
    ]
    for artifact_id in ["distribution_histogram", "bin_sensitivity"]:
        assert (
            run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "build-context.json"
        ).exists()
        assert (
            run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "prompt.md"
        ).exists()
        assert (
            run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "output.json"
        ).exists()
        assert (
            run_dir / "02-artifact-builder" / artifact_id / "attempt-1" / "query.sql"
        ).exists()
        assert (
            run_dir
            / "02-artifact-builder"
            / artifact_id
            / "attempt-1"
            / "chart.vegalite.json"
        ).exists()
        assert (
            run_dir / "03-execution" / artifact_id / "attempt-1" / "result.parquet"
        ).exists()
        assert (
            run_dir / "03-execution" / artifact_id / "attempt-1" / "result.summary.json"
        ).exists()
        assert (run_dir / "04-render" / artifact_id / "attempt-1" / "chart.png").exists()
        assert (
            run_dir / "05-visual-reviewer" / artifact_id / "attempt-1" / "review-context.json"
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
    review_requests = [request for request in adapter.requests if request.role == "visual_reviewer"]
    assert len(builder_requests) == 2
    assert len(review_requests) == 2
    assert review_requests[0].images == [
        run_dir / "04-render" / "distribution_histogram" / "attempt-1" / "chart.png"
    ]
    assert review_requests[1].images == [
        run_dir / "04-render" / "bin_sensitivity" / "attempt-1" / "chart.png"
    ]
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
    for request in adapter.requests:
        assert request.output_path is not None
        assert request.output_schema_path is not None
        assert request.output_schema_path.exists()


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
    assert first_context["revision_request"] == ""

    assert second_context["current_artifact"]["id"] == "bin_sensitivity"
    assert second_context["previous_reviews"][0]["artifact_id"] == "distribution_histogram"
    assert second_context["remaining_artifacts"] == []


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
    assert not (run_dir / "02-artifact-builder" / "bin_sensitivity" / "attempt-2").exists()


def test_artifact_builder_chart_spec_json_string_is_written_as_chart_object(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                {
                    "artifact_id": "distribution_histogram",
                    "sql": _builder_output("distribution_histogram").sql,
                    "chart_spec": json.dumps(
                        _builder_output("distribution_histogram").chart_spec
                    ),
                },
                _builder_output("bin_sensitivity"),
            ],
            "visual_reviewer": [
                _reviewer_output(artifact_id="distribution_histogram"),
                _reviewer_output(artifact_id="bin_sensitivity"),
            ],
        }
    )

    run_multimodal_trial(
        run_root=tmp_path,
        run_id="string-chart-run",
        adapter=adapter,
        user_question="Assess whether monthly_rent_usd has a simple distribution.",
    )

    chart_spec = json.loads(
        (
            tmp_path
            / "multimodal"
            / "string-chart-run"
            / "02-artifact-builder"
            / "distribution_histogram"
            / "attempt-1"
            / "chart.vegalite.json"
        ).read_text()
    )
    assert chart_spec["mark"] == "bar"


def test_second_revise_for_same_artifact_exhausts_budget_and_skips_later_artifacts(
    tmp_path,
):
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
    assert state["artifact_statuses"]["distribution_histogram"] == (
        "revision_budget_exhausted"
    )
    assert not (run_dir / "02-artifact-builder" / "bin_sensitivity").exists()


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
