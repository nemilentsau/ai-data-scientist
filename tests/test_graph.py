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


def _builder_output(report_text="# Report\nThe target distribution is multimodal."):
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
        report_markdown=report_text,
    )


def test_pass_review_run_produces_artifacts_and_lineage(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [_builder_output()],
            "visual_reviewer": [
                VisualReviewerOutput(
                    verdict="pass",
                    visual_findings=["The chart is visibly multi-peaked."],
                    required_revision="",
                )
            ],
        }
    )

    state = run_multimodal_trial(run_root=tmp_path, run_id="pass-run", adapter=adapter)

    run_dir = tmp_path / "multimodal" / "pass-run"
    assert state["status"] == "passed_visual_gate"
    assert (run_dir / "dataset" / "dataset.csv").exists()
    assert (run_dir / "dataset" / "profile.json").exists()
    assert (run_dir / "framing" / "framing.json").exists()
    assert (run_dir / "queries" / "target_distribution.sql").exists()
    assert (run_dir / "results" / "target_distribution.parquet").exists()
    assert (run_dir / "charts" / "target_distribution.vegalite.json").exists()
    assert (run_dir / "renders" / "target_distribution.png").exists()
    assert (run_dir / "reviews" / "visual_review.json").exists()
    assert (run_dir / "reports" / "report.md").read_text().startswith("# Report")
    lineage = json.loads((run_dir / "lineage.json").read_text())
    assert lineage["status"] == "passed_visual_gate"
    assert "renders/target_distribution.png" in lineage["artifacts"]
    assert adapter.requests[-1].images == [run_dir / "renders" / "target_distribution.png"]


def test_revise_review_runs_one_builder_revision_and_second_review(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output("# Report\nThis is just a regression setup."),
                _builder_output("# Report\nThe target distribution is multimodal."),
            ],
            "visual_reviewer": [
                VisualReviewerOutput(
                    verdict="revise",
                    visual_findings=["The report ignores the multi-peaked target."],
                    required_revision="State that the rent target is multimodal.",
                ),
                VisualReviewerOutput(
                    verdict="pass",
                    visual_findings=["The revised report matches the chart."],
                    required_revision="",
                ),
            ],
        }
    )

    state = run_multimodal_trial(run_root=tmp_path, run_id="revise-run", adapter=adapter)

    run_dir = tmp_path / "multimodal" / "revise-run"
    assert state["status"] == "passed_visual_gate"
    assert state["revision_count"] == 1
    assert (run_dir / "reports" / "report.md").read_text().endswith("multimodal.")
    builder_requests = [request for request in adapter.requests if request.role == "artifact_builder"]
    review_requests = [request for request in adapter.requests if request.role == "visual_reviewer"]
    assert len(builder_requests) == 2
    assert len(review_requests) == 2


def test_second_revise_review_exhausts_revision_budget(tmp_path):
    adapter = FakeCodexAdapter(
        {
            "eda_framer": [_framer_output()],
            "artifact_builder": [
                _builder_output("# Report\nThis is just a regression setup."),
                _builder_output("# Report\nStill not enough."),
            ],
            "visual_reviewer": [
                VisualReviewerOutput(
                    verdict="revise",
                    visual_findings=["Missing multimodal interpretation."],
                    required_revision="Discuss modes.",
                ),
                VisualReviewerOutput(
                    verdict="revise",
                    visual_findings=["Still missing multimodal interpretation."],
                    required_revision="Discuss modes.",
                ),
            ],
        }
    )

    state = run_multimodal_trial(run_root=tmp_path, run_id="fail-run", adapter=adapter)

    assert state["status"] == "revision_budget_exhausted"
    assert state["revision_count"] == 1
