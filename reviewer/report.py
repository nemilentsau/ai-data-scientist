"""Markdown reporting for structured benchmark outcomes."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .scorer import CriterionResult, ScoreResult

VERDICT_RANK = {
    "wrong": 0,
    "failed": 1,
    "partial": 2,
    "solved": 3,
}


def _comparison_key(result: ScoreResult) -> tuple[float, ...]:
    oracle = result.oracle_attainment if result.oracle_attainment is not None else -1.0
    return (
        float(VERDICT_RANK[result.verdict]),
        result.required_coverage,
        oracle,
        result.supporting_coverage,
        1.0 if result.core_insight_pass else 0.0,
    )


def _format_result_cell(result: ScoreResult | None) -> str:
    if result is None:
        return "-"
    return f"{result.verdict} ({result.required_coverage:.0%})"


def _winner_label(claude_result: ScoreResult | None, codex_result: ScoreResult | None) -> str:
    if claude_result is None or codex_result is None:
        return "-"
    claude_key = _comparison_key(claude_result)
    codex_key = _comparison_key(codex_result)
    if claude_key > codex_key:
        return "Claude"
    if codex_key > claude_key:
        return "Codex"
    return "Tie"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _group_criteria(results: list[CriterionResult], group: str) -> list[CriterionResult]:
    return [result for result in results if result.group == group]


def _format_criterion_section(
    lines: list[str],
    title: str,
    results: list[CriterionResult],
) -> None:
    lines.append(f"**{title}**")
    if not results:
        lines.append("- None")
        lines.append("")
        return

    for result in results:
        detail = result.justification or "No justification provided."
        if result.evidence:
            detail = f"{detail} Evidence: {result.evidence}"
        lines.append(f"- `{result.criterion_id}`: {result.status}. {detail}")
    lines.append("")


def generate_report(results: list[ScoreResult], output_path: Path) -> str:
    """Generate a markdown comparison report from structured outcomes."""
    by_dataset: dict[str, dict[str, ScoreResult]] = {}
    by_agent: dict[str, list[ScoreResult]] = defaultdict(list)

    for result in results:
        by_dataset.setdefault(result.dataset_name, {})[result.agent] = result
        by_agent[result.agent].append(result)

    lines = ["# AI Data Scientist Benchmark Results\n"]

    lines.append("## Summary\n")
    lines.append("| Dataset | Claude | Codex | Winner |")
    lines.append("|---------|--------|-------|--------|")

    for dataset_name, agents in sorted(by_dataset.items()):
        claude_result = agents.get("claude")
        codex_result = agents.get("codex")
        lines.append(
            "| "
            f"{dataset_name} | "
            f"{_format_result_cell(claude_result)} | "
            f"{_format_result_cell(codex_result)} | "
            f"{_winner_label(claude_result, codex_result)} |"
        )
    lines.append("")

    lines.append("## Agent Metrics\n")
    lines.append(
        "| Agent | Solve Rate | Wrong Rate | Avg Required | Avg Supporting | Avg Oracle |"
    )
    lines.append("|-------|------------|------------|--------------|----------------|-----------|")
    for agent_name in sorted(by_agent):
        agent_results = by_agent[agent_name]
        solve_rate = _mean([1.0 if result.verdict == "solved" else 0.0 for result in agent_results])
        wrong_rate = _mean([1.0 if result.verdict == "wrong" else 0.0 for result in agent_results])
        avg_required = _mean([result.required_coverage for result in agent_results])
        avg_supporting = _mean([result.supporting_coverage for result in agent_results])
        oracle_values = [
            result.oracle_attainment
            for result in agent_results
            if result.oracle_attainment is not None
        ]
        avg_oracle = _mean(oracle_values)
        lines.append(
            f"| {agent_name.title()} | {solve_rate:.0%} | {wrong_rate:.0%} | "
            f"{avg_required:.0%} | {avg_supporting:.0%} | {avg_oracle:.0%} |"
        )
    lines.append("")

    lines.append("## Detailed Results\n")
    for dataset_name, agents in sorted(by_dataset.items()):
        lines.append(f"### {dataset_name}\n")
        for agent_name, result in sorted(agents.items()):
            lines.append(f"#### {agent_name.title()} ({result.verdict})\n")
            lines.append(f"**Summary:** {result.summary or 'No summary provided.'}")
            lines.append(f"**Core Insight:** {'pass' if result.core_insight_pass else 'fail'}")
            lines.append(f"**Required Coverage:** {result.required_coverage:.0%}")
            lines.append(f"**Supporting Coverage:** {result.supporting_coverage:.0%}")
            if result.oracle_metric_name is not None:
                if result.oracle_attainment is None:
                    oracle_text = "not available"
                else:
                    oracle_text = f"{result.oracle_attainment:.0%}"
                lines.append(f"**Oracle Attainment ({result.oracle_metric_name}):** {oracle_text}")
            if result.fatal_errors:
                lines.append("**Fatal Errors:**")
                for error in result.fatal_errors:
                    lines.append(f"- {error}")
            if result.efficiency:
                formatted_efficiency = ", ".join(
                    f"{name}={value:.0f}" for name, value in sorted(result.efficiency.items())
                )
                lines.append(f"**Efficiency:** {formatted_efficiency}")
            lines.append("")

            _format_criterion_section(
                lines,
                "Must Have",
                _group_criteria(result.criterion_results, "must_have"),
            )
            _format_criterion_section(
                lines,
                "Supporting",
                _group_criteria(result.criterion_results, "supporting"),
            )
            _format_criterion_section(
                lines,
                "Forbidden",
                _group_criteria(result.criterion_results, "forbidden"),
            )

    report = "\n".join(lines)
    output_path.write_text(report)
    return report
