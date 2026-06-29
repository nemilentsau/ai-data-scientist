import argparse
from collections.abc import Sequence
from pathlib import Path

from eda_artifacts.codex import (
    ArtifactBuilderOutput,
    CodexExecAdapter,
    EdaFramerOutput,
    FakeCodexAdapter,
    VisualReviewerOutput,
)
from eda_artifacts.graph import run_multimodal_trial


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    if args.command != "run":
        parser.print_help()
        return 2
    if args.dataset != "multimodal":
        return 2
    question = args.question.strip()
    if not question:
        return 2

    adapter = _build_adapter(args.adapter)
    state = run_multimodal_trial(
        run_root=Path(args.run_root),
        run_id=args.run_id,
        adapter=adapter,
        user_question=question,
    )
    print(f"status={state['status']}")
    print(f"run_dir={state['run_dir']}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eda-artifacts")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--dataset", default="multimodal")
    run_parser.add_argument("--adapter", choices=["fake", "codex-exec"], default="codex-exec")
    run_parser.add_argument("--run-id", default="smoke")
    run_parser.add_argument("--run-root", default="runs/eda-artifacts")
    run_parser.add_argument("--question", required=True)
    return parser


def _build_adapter(name: str):
    if name == "fake":
        return FakeCodexAdapter(
            {
                "eda_framer": [
                    EdaFramerOutput(
                        user_question=(
                            "Assess whether monthly_rent_usd has a simple distribution."
                        ),
                        analysis_goal=(
                            "Evaluate whether the target distribution is simple enough "
                            "for later modeling claims."
                        ),
                        artifact_plan=[
                            {
                                "id": "distribution_histogram",
                                "purpose": "Inspect gross distribution shape and modality.",
                                "statistical_check": (
                                    "Does monthly_rent_usd appear unimodal, multimodal, "
                                    "skewed, or inconclusive?"
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
                                "purpose": (
                                    "Check whether apparent shape is stable under bin changes."
                                ),
                                "statistical_check": (
                                    "Does apparent modality depend on bin width?"
                                ),
                                "artifact_type": "chart",
                                "expected_chart_family": "small_multiple_histograms",
                                "required_fields": [
                                    "bin_width",
                                    "rent_bin",
                                    "listing_count",
                                ],
                                "interpretation_limits": [
                                    "This checks visual stability, not formal mixture-model fit."
                                ],
                            },
                        ],
                        stop_conditions=[
                            "Do not make regression claims before visual target review"
                        ],
                    )
                ],
                "artifact_builder": [
                    ArtifactBuilderOutput(
                        artifact_id="distribution_histogram",
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
                                "x": {
                                    "field": "rent_bin",
                                    "type": "ordinal",
                                    "title": "Monthly rent bin",
                                },
                                "y": {
                                    "field": "listing_count",
                                    "type": "quantitative",
                                    "title": "Listings",
                                },
                            },
                        },
                    ),
                    ArtifactBuilderOutput(
                        artifact_id="bin_sensitivity",
                        sql="""
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
                        """,
                        chart_spec={
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "mark": "bar",
                            "encoding": {
                                "x": {
                                    "field": "rent_bin",
                                    "type": "ordinal",
                                    "title": "Monthly rent bin",
                                },
                                "y": {
                                    "field": "listing_count",
                                    "type": "quantitative",
                                    "title": "Listings",
                                },
                                "column": {
                                    "field": "bin_width",
                                    "type": "nominal",
                                    "title": "Bin width",
                                },
                            },
                        },
                    ),
                ],
                "visual_reviewer": [
                    VisualReviewerOutput(
                        artifact_id="distribution_histogram",
                        verdict="pass",
                        visual_adequacy=["The histogram is readable."],
                        statistical_findings=[
                            "The target distribution chart is multi-peaked."
                        ],
                        limitations=[
                            "A single bin width can leave modality sensitive to binning."
                        ],
                        carry_forward_notes=[
                            "Use the planned bin_sensitivity artifact to check bin stability."
                        ],
                        required_revision="",
                        report_markdown=(
                            "# distribution_histogram\n\n"
                            "The rendered distribution is mixture-like, so regression framing "
                            "should come after segmentation-oriented EDA."
                        ),
                    ),
                    VisualReviewerOutput(
                        artifact_id="bin_sensitivity",
                        verdict="pass",
                        visual_adequacy=["The bin sensitivity chart is readable."],
                        statistical_findings=[
                            "The alternate bin-width view still supports a non-simple shape."
                        ],
                        limitations=[
                            "This visual check is not a formal mixture-model test."
                        ],
                        carry_forward_notes=[],
                        required_revision="",
                        report_markdown=(
                            "# bin_sensitivity\n\n"
                            "The bin sensitivity view preserves the concern that the "
                            "distribution is not a simple single-population shape."
                        ),
                    ),
                ],
            }
        )
    return CodexExecAdapter(model="gpt-5.5")


if __name__ == "__main__":
    raise SystemExit(main())
