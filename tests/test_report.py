"""Tests for report generation — markdown output structure."""

import tempfile
from pathlib import Path

from reviewer.scorer import ScoreResult
from reviewer.report import generate_report


def _make_result(dataset: str, agent: str, total: int) -> ScoreResult:
    return ScoreResult(
        dataset_name=dataset,
        agent=agent,
        scores={
            "data_loading_inspection": 4,
            "eda_quality": 3,
            "pattern_identification": 4,
            "method_selection": 3,
            "assumption_checking": 3,
            "code_quality": 4,
            "conclusions": 3,
        },
        modifiers=[],
        total=total,
        summary=f"{agent} did well on {dataset}",
        raw_response="{}",
    )


def test_report_contains_summary_table():
    results = [
        _make_result("pure_noise", "claude", 28),
        _make_result("pure_noise", "codex", 22),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "| pure_noise |" in report
    assert "Claude" in report  # winner


def test_report_handles_single_agent():
    results = [_make_result("pure_noise", "claude", 28)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "pure_noise" in report
    assert "28" in report


def test_report_writes_file():
    results = [_make_result("pure_noise", "claude", 28)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        generate_report(results, path)
        assert path.exists()
        assert path.read_text().startswith("# AI Data Scientist")


def test_report_tie_when_equal_scores():
    results = [
        _make_result("pure_noise", "claude", 25),
        _make_result("pure_noise", "codex", 25),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.md"
        report = generate_report(results, path)

    assert "Tie" in report
