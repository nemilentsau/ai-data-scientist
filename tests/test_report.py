"""Tests for structured benchmark report generation."""

import tempfile
from pathlib import Path

from reviewer.report import generate_report
from reviewer.scorer import CriterionResult, ScoreResult


def _make_result(dataset: str, agent: str, verdict: str) -> ScoreResult:
    return ScoreResult(
        dataset_name=dataset,
        agent=agent,
        verdict=verdict,  # type: ignore[arg-type]
        core_insight_pass=verdict == "solved",
        required_coverage=1.0 if verdict == "solved" else 0.5,
        supporting_coverage=0.5,
        oracle_attainment=0.8 if dataset == "deterministic_linear" else None,
        oracle_metric_name="r2" if dataset == "deterministic_linear" else None,
        oracle_agent_value=0.8 if dataset == "deterministic_linear" else None,
        fatal_errors=["Claimed a spurious pattern"] if verdict == "wrong" else [],
        efficiency={"trace_events": 12.0},
        criterion_results=[
            CriterionResult(
                criterion_id=f"{dataset}_core_insight",
                group="must_have",
                status="hit" if verdict == "solved" else "partial",
                justification="Reviewed",
            )
        ],
        summary=f"{agent} produced a {verdict} analysis for {dataset}",
        raw_response="{}",
    )


def test_report_contains_summary_table_and_winner():
    results = [
        _make_result("pure_noise", "claude", "solved"),
        _make_result("pure_noise", "codex", "partial"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "| pure_noise | solved (100%) | partial (50%) | Claude |" in report


def test_report_handles_single_agent_results():
    results = [_make_result("pure_noise", "claude", "solved")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "pure_noise" in report
    assert "Solve Rate" in report
    assert "Claude" in report


def test_report_writes_markdown_file():
    results = [_make_result("pure_noise", "claude", "solved")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        generate_report(results, path)
        assert path.exists()
        assert path.read_text().startswith("# AI Data Scientist")


def test_report_marks_ties_when_results_match():
    results = [
        _make_result("pure_noise", "claude", "partial"),
        _make_result("pure_noise", "codex", "partial"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "Tie" in report


def test_report_includes_fatal_errors_for_wrong_results():
    results = [_make_result("pure_noise", "claude", "wrong")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "Fatal Errors" in report
    assert "Claimed a spurious pattern" in report
