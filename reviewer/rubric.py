"""Formatting helpers for dataset-specific evaluation contracts."""

from __future__ import annotations

from datasets.registry import Criterion, DatasetMeta, get_evaluation_spec

TRANSCRIPT_CHAR_LIMIT = 20_000


def _format_criteria(title: str, criteria: list[Criterion]) -> list[str]:
    lines = [f"### {title}"]
    if not criteria:
        lines.append("- None")
        lines.append("")
        return lines

    for criterion in criteria:
        detail = criterion.description
        if criterion.verification_hint:
            detail = f"{detail} Hint: {criterion.verification_hint}"
        prefix = f"- `{criterion.id}`:"
        lines.append(f"{prefix} {detail}")
    lines.append("")
    return lines


def format_rubric_for_prompt(dataset_metadata: DatasetMeta) -> str:
    """Format the dataset-specific evaluation contract for the reviewer prompt."""
    spec = get_evaluation_spec(dataset_metadata)

    lines = [
        "## Evaluation Contract",
        f"Task family: {spec.task_family}",
        "",
    ]
    lines.extend(_format_criteria("Must Have Criteria", spec.must_have))
    lines.extend(_format_criteria("Supporting Criteria", spec.supporting))
    lines.extend(_format_criteria("Forbidden Criteria", spec.forbidden))

    if spec.oracle_metric is not None:
        lines.extend(
            [
                "### Oracle Metric",
                f"- Name: `{spec.oracle_metric.name}`",
                f"- Description: {spec.oracle_metric.description}",
                (
                    f"- Baseline: {spec.oracle_metric.baseline_value}, "
                    f"Oracle: {spec.oracle_metric.oracle_value}, "
                    f"Direction: {spec.oracle_metric.direction}"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Verdict Rules",
            "- `wrong`: any forbidden criterion is HIT.",
            "- `solved`: every must-have criterion is HIT and no forbidden criterion is HIT.",
            "- `partial`: at least one must-have criterion is HIT or PARTIAL, but not all are HIT.",
            "- `failed`: no must-have criterion is HIT or PARTIAL.",
        ]
    )

    return "\n".join(lines)
