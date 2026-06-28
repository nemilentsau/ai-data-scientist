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
                        analysis_plan=(
                            "Evaluate the target distribution before modeling claims."
                        ),
                        hypotheses=[
                            {
                                "id": "h1",
                                "statement": (
                                    "monthly_rent_usd may be multi-peaked rather than unimodal."
                                ),
                                "rationale": (
                                    "The profile shows a wide numeric range and mean above median."
                                ),
                                "variables": ["monthly_rent_usd"],
                            }
                        ],
                        artifact_requests=[
                            {
                                "id": "a1",
                                "hypothesis_id": "h1",
                                "artifact_type": "chart",
                                "description": "Render a distribution view of monthly_rent_usd.",
                                "statistical_purpose": "Check visible modality and skew.",
                                "expected_fields": ["rent_bin", "listing_count"],
                            }
                        ],
                        stop_conditions=[
                            "Do not make regression claims before visual target review"
                        ],
                    )
                ],
                "artifact_builder": [
                    ArtifactBuilderOutput(
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
                    )
                ],
                "visual_reviewer": [
                    VisualReviewerOutput(
                        verdict="pass",
                        visual_findings=["The target distribution chart is multi-peaked."],
                        required_revision="",
                        report_markdown=(
                            "# Multimodal Rent EDA\n\n"
                            "The rendered distribution is mixture-like, so regression framing "
                            "should come after segmentation-oriented EDA."
                        ),
                    )
                ],
            }
        )
    return CodexExecAdapter(model="gpt-5.5")


if __name__ == "__main__":
    raise SystemExit(main())
