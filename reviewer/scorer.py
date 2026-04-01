"""LLM-assisted reviewer that produces structured benchmark outcomes."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from datasets.registry import (
    Criterion,
    DatasetMeta,
    EvaluationSpec,
    OracleMetric,
    get_evaluation_spec,
)

from .rubric import TRANSCRIPT_CHAR_LIMIT, format_rubric_for_prompt

CriterionStatus = Literal["hit", "partial", "miss"]
RunStatus = Literal["completed", "run_error"]
Verdict = Literal["solved", "partial", "failed", "wrong", "run_error"]


@dataclass(frozen=True)
class CriterionResult:
    """Structured judgment for a single criterion."""

    criterion_id: str
    group: Literal["must_have", "supporting", "forbidden"]
    status: CriterionStatus
    justification: str
    evidence: str = ""


@dataclass
class ScoreResult:
    """Structured outcome for one dataset/agent pair."""

    dataset_name: str
    agent: str
    verdict: Verdict
    core_insight_pass: bool
    required_coverage: float
    supporting_coverage: float
    oracle_attainment: float | None
    oracle_metric_name: str | None
    oracle_agent_value: float | None
    run_status: RunStatus = "completed"
    rerun_recommended: bool = False
    run_error_reasons: list[str] = field(default_factory=list)
    fatal_errors: list[str] = field(default_factory=list)
    efficiency: dict[str, float] = field(default_factory=dict)
    criterion_results: list[CriterionResult] = field(default_factory=list)
    summary: str = ""
    raw_response: str = ""


def _grouped(criteria_results: list[CriterionResult], group: str) -> list[CriterionResult]:
    return [result for result in criteria_results if result.group == group]


def compute_coverage(results: list[CriterionResult]) -> float:
    """Compute normalized coverage from criterion statuses."""
    if not results:
        return 1.0

    score_map: dict[CriterionStatus, float] = {
        "hit": 1.0,
        "partial": 0.5,
        "miss": 0.0,
    }
    return sum(score_map[result.status] for result in results) / len(results)


def determine_verdict(
    required_results: list[CriterionResult],
    forbidden_results: list[CriterionResult],
) -> Verdict:
    """Determine the final dataset verdict."""
    if any(result.status == "hit" for result in forbidden_results):
        return "wrong"
    if required_results and all(result.status == "hit" for result in required_results):
        return "solved"
    if any(result.status in {"hit", "partial"} for result in required_results):
        return "partial"
    return "failed"


def normalize_oracle_attainment(
    oracle_metric: OracleMetric | None,
    agent_value: float | None,
) -> float | None:
    """Normalize a reported metric against a baseline and oracle."""
    if oracle_metric is None or agent_value is None:
        return None

    baseline = oracle_metric.baseline_value
    oracle = oracle_metric.oracle_value

    if oracle == baseline:
        return 1.0 if agent_value == oracle else 0.0

    if oracle_metric.direction == "higher_is_better":
        normalized = (agent_value - baseline) / (oracle - baseline)
    else:
        normalized = (baseline - agent_value) / (baseline - oracle)

    return max(0.0, min(1.0, normalized))


def assess_run_state(results_dir: Path) -> tuple[RunStatus, list[str]]:
    """Determine whether a run completed enough to score analytically."""
    missing_artifacts: list[str] = []

    report_path = results_dir / "analysis_report.md"
    if not report_path.exists():
        missing_artifacts.append("missing analysis report (analysis_report.md)")

    if missing_artifacts:
        return "run_error", missing_artifacts
    return "completed", []


def build_reviewer_prompt(
    dataset_metadata: DatasetMeta,
    analysis_report: str,
    session_transcript: str,
) -> str:
    """Build the dataset-specific review prompt."""
    rubric_text = format_rubric_for_prompt(dataset_metadata)
    spec = get_evaluation_spec(dataset_metadata)
    transcript_excerpt = session_transcript[:TRANSCRIPT_CHAR_LIMIT]
    expected_findings = "\n".join(
        f"- {finding}" for finding in dataset_metadata.expected_findings
    )
    common_traps = "\n".join(f"- {trap}" for trap in dataset_metadata.traps)

    oracle_instructions = ""
    if spec.oracle_metric is not None:
        oracle_instructions = f"""
Also extract the agent's reported value for the oracle metric if possible:
- name: {spec.oracle_metric.name}
- description: {spec.oracle_metric.description}
- if the value is not reported or cannot be inferred reliably, return null
"""

    prompt_lines = [
        (
            "You are a senior data scientist reviewing an analysis against a "
            "dataset-specific evaluation contract."
        ),
        "",
        "## Ground Truth for This Dataset",
        f"**Key Pattern:** {dataset_metadata.key_pattern}",
        "",
        "**Expected Findings:**",
        expected_findings,
        "",
        "**Common Traps:**",
        common_traps,
        "",
        rubric_text,
        "",
        "---",
        "",
        "## Agent's Analysis Report",
        analysis_report,
        "",
        "---",
        "",
        "## Agent's Session Transcript (abbreviated)",
        transcript_excerpt,
        "",
        "---",
        "",
        "## Instructions",
        "Judge each listed criterion ID exactly once.",
        "",
        "- For `must_have` and `supporting`, use one of: `hit`, `partial`, `miss`",
        "- For `forbidden`, use only: `hit` or `miss`",
        (
            "- Always include a brief justification and a short evidence snippet "
            "when available"
        ),
        (
            "- Be strict about the core insight; technical polish does not "
            "compensate for missing the key pattern"
        ),
    ]

    if oracle_instructions:
        prompt_lines.extend([oracle_instructions.strip(), ""])

    prompt_lines.extend(
        [
            "Return ONLY valid JSON in this exact structure:",
            "{",
            '  "must_have": {',
            '    "<criterion_id>": {',
            '      "status": "hit|partial|miss",',
            '      "justification": "...",',
            '      "evidence": "..."',
            "    }",
            "  },",
            '  "supporting": {',
            '    "<criterion_id>": {',
            '      "status": "hit|partial|miss",',
            '      "justification": "...",',
            '      "evidence": "..."',
            "    }",
            "  },",
            '  "forbidden": {',
            '    "<criterion_id>": {',
            '      "status": "hit|miss",',
            '      "justification": "...",',
            '      "evidence": "..."',
            "    }",
            "  },",
            '  "oracle_metric": {',
            '    "agent_value": 0.0,',
            '    "justification": "..."',
            "  },",
            '  "summary": "One paragraph overall assessment"',
            "}",
            "",
            (
                "The `must_have`, `supporting`, and `forbidden` objects must "
                "contain every criterion ID listed in the evaluation contract above."
            ),
        ]
    )

    return "\n".join(prompt_lines)


def _extract_json_payload(raw: str) -> dict[str, Any]:
    json_str = raw
    if "```json" in raw:
        json_str = raw.split("```json", maxsplit=1)[1].split("```", maxsplit=1)[0]
    elif "```" in raw:
        json_str = raw.split("```", maxsplit=1)[1].split("```", maxsplit=1)[0]
    return json.loads(json_str.strip())


def _normalize_status(
    status: str | None,
    *,
    allow_partial: bool,
) -> CriterionStatus:
    normalized = (status or "miss").strip().lower()
    if normalized == "hit":
        return "hit"
    if normalized == "partial" and allow_partial:
        return "partial"
    if normalized == "partial":
        return "hit"
    return "miss"


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _build_group_results(
    group_name: Literal["must_have", "supporting", "forbidden"],
    criteria: list[Criterion],
    payload: dict[str, Any],
) -> list[CriterionResult]:
    results: list[CriterionResult] = []
    allow_partial = group_name != "forbidden"

    for criterion in criteria:
        criterion_payload = payload.get(criterion.id, {})
        status = _normalize_status(
            criterion_payload.get("status"),
            allow_partial=allow_partial,
        )
        results.append(
            CriterionResult(
                criterion_id=criterion.id,
                group=group_name,
                status=status,
                justification=str(criterion_payload.get("justification", "")),
                evidence=str(criterion_payload.get("evidence", "")),
            )
        )

    return results


def _parse_reviewer_response(
    raw_response: str,
    evaluation_spec: EvaluationSpec,
) -> tuple[list[CriterionResult], float | None, str]:
    data = _extract_json_payload(raw_response)

    must_have = _build_group_results(
        "must_have",
        evaluation_spec.must_have,
        data.get("must_have", {}),
    )
    supporting = _build_group_results(
        "supporting",
        evaluation_spec.supporting,
        data.get("supporting", {}),
    )
    forbidden = _build_group_results(
        "forbidden",
        evaluation_spec.forbidden,
        data.get("forbidden", {}),
    )

    oracle_payload = data.get("oracle_metric")
    agent_value = None
    if isinstance(oracle_payload, dict):
        agent_value = _coerce_optional_float(oracle_payload.get("agent_value"))

    summary = str(data.get("summary", "")).strip()
    return must_have + supporting + forbidden, agent_value, summary


def _collect_efficiency_metrics(results_dir: Path, session_transcript: str) -> dict[str, float]:
    metrics: dict[str, float] = {
        "transcript_chars": float(len(session_transcript)),
    }

    trace_path = results_dir / "trace.jsonl"
    if trace_path.exists():
        with trace_path.open() as trace_file:
            metrics["trace_events"] = float(sum(1 for _ in trace_file))

    report_path = results_dir / "analysis_report.md"
    if report_path.exists():
        metrics["report_chars"] = float(len(report_path.read_text()))

    return metrics


def score_analysis(
    dataset_name: str,
    agent: str,
    dataset_metadata: DatasetMeta,
    results_dir: Path,
) -> ScoreResult:
    """Score an agent's analysis using Claude CLI as the structured reviewer."""
    evaluation_spec = get_evaluation_spec(dataset_metadata)
    report_path = results_dir / "analysis_report.md"
    analysis_report = (
        report_path.read_text() if report_path.exists() else "[No analysis report found]"
    )

    trace_path = results_dir / "trace.jsonl"
    if trace_path.exists():
        session_transcript = trace_path.read_text()
    elif agent == "claude":
        transcript_path = results_dir / "session.json"
        session_transcript = (
            transcript_path.read_text()
            if transcript_path.exists()
            else "[No session transcript found]"
        )
    else:
        transcript_path = results_dir / "session.log"
        session_transcript = (
            transcript_path.read_text()
            if transcript_path.exists()
            else "[No session transcript found]"
        )

    run_status, run_error_reasons = assess_run_state(results_dir)
    if run_status == "run_error":
        reason_text = "; ".join(run_error_reasons)
        summary = (
            "Run did not complete successfully. "
            f"Missing required output artifacts: {reason_text}. "
            "This result should be rerun and should not be interpreted as an "
            "analytical miss."
        )
        return ScoreResult(
            dataset_name=dataset_name,
            agent=agent,
            verdict="run_error",
            run_status=run_status,
            rerun_recommended=True,
            run_error_reasons=run_error_reasons,
            core_insight_pass=False,
            required_coverage=0.0,
            supporting_coverage=0.0,
            oracle_attainment=None,
            oracle_metric_name=(
                evaluation_spec.oracle_metric.name
                if evaluation_spec.oracle_metric is not None
                else None
            ),
            oracle_agent_value=None,
            fatal_errors=[],
            efficiency=_collect_efficiency_metrics(results_dir, session_transcript),
            criterion_results=[],
            summary=summary,
            raw_response="",
        )

    prompt = build_reviewer_prompt(dataset_metadata, analysis_report, session_transcript)

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "1"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr}")

    cli_output = json.loads(result.stdout)
    raw_response = cli_output.get("result", result.stdout)

    criterion_results, oracle_agent_value, summary = _parse_reviewer_response(
        raw_response,
        evaluation_spec,
    )

    required_results = _grouped(criterion_results, "must_have")
    supporting_results = _grouped(criterion_results, "supporting")
    forbidden_results = _grouped(criterion_results, "forbidden")

    core_insight_ids = {
        criterion.id for criterion in evaluation_spec.must_have if criterion.is_core_insight
    }
    core_insight_pass = all(
        result.status == "hit"
        for result in required_results
        if result.criterion_id in core_insight_ids
    )
    if not core_insight_ids:
        core_insight_pass = False

    fatal_errors = [
        criterion.description
        for criterion in evaluation_spec.forbidden
        if any(
            result.criterion_id == criterion.id and result.status == "hit"
            for result in forbidden_results
        )
    ]

    verdict = determine_verdict(required_results, forbidden_results)
    required_coverage = compute_coverage(required_results)
    supporting_coverage = compute_coverage(supporting_results)
    oracle_attainment = normalize_oracle_attainment(
        evaluation_spec.oracle_metric,
        oracle_agent_value,
    )

    return ScoreResult(
        dataset_name=dataset_name,
        agent=agent,
        verdict=verdict,
        run_status=run_status,
        rerun_recommended=False,
        run_error_reasons=[],
        core_insight_pass=core_insight_pass,
        required_coverage=required_coverage,
        supporting_coverage=supporting_coverage,
        oracle_attainment=oracle_attainment,
        oracle_metric_name=(
            evaluation_spec.oracle_metric.name
            if evaluation_spec.oracle_metric is not None
            else None
        ),
        oracle_agent_value=oracle_agent_value,
        fatal_errors=fatal_errors,
        efficiency=_collect_efficiency_metrics(results_dir, session_transcript),
        criterion_results=criterion_results,
        summary=summary,
        raw_response=raw_response,
    )
