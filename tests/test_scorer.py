"""Tests for prompt building and deterministic scoring helpers."""

from datasets.registry import OracleMetric, get_dataset
from reviewer.scorer import (
    CriterionResult,
    ScoreResult,
    build_reviewer_prompt,
    compute_coverage,
    determine_verdict,
    normalize_oracle_attainment,
)


def test_prompt_includes_ground_truth_and_contract_details():
    meta = get_dataset("simpsons_paradox")
    prompt = build_reviewer_prompt(meta, "Some analysis", "Some transcript")

    assert meta.key_pattern in prompt
    for finding in meta.expected_findings:
        assert finding in prompt
    for trap in meta.traps:
        assert trap in prompt
    assert "simpsons_paradox_reversal_identified" in prompt


def test_prompt_includes_agent_outputs_and_truncates_long_transcript():
    meta = get_dataset("pure_noise")
    report = "This is the agent's analysis report."
    transcript = "x" * 50_000

    prompt = build_reviewer_prompt(meta, report, transcript)

    assert report in prompt
    assert "x" * 20_000 in prompt
    assert "x" * 20_001 not in prompt


def test_coverage_counts_partial_as_half_credit():
    coverage = compute_coverage(
        [
            CriterionResult("a", "must_have", "hit", "done"),
            CriterionResult("b", "must_have", "partial", "partly done"),
            CriterionResult("c", "must_have", "miss", "missing"),
        ]
    )

    assert coverage == 0.5


def test_verdict_marks_forbidden_hits_as_wrong():
    verdict = determine_verdict(
        [CriterionResult("a", "must_have", "hit", "done")],
        [CriterionResult("trap", "forbidden", "hit", "bad")],
    )

    assert verdict == "wrong"


def test_verdict_marks_all_required_hits_as_solved():
    verdict = determine_verdict(
        [
            CriterionResult("a", "must_have", "hit", "done"),
            CriterionResult("b", "must_have", "hit", "done"),
        ],
        [],
    )

    assert verdict == "solved"


def test_verdict_marks_mixed_required_statuses_as_partial():
    verdict = determine_verdict(
        [
            CriterionResult("a", "must_have", "hit", "done"),
            CriterionResult("b", "must_have", "miss", "missing"),
        ],
        [],
    )

    assert verdict == "partial"


def test_oracle_attainment_normalizes_higher_is_better_metrics():
    oracle = OracleMetric(
        name="r2",
        description="Best reported R^2.",
        direction="higher_is_better",
        baseline_value=0.0,
        oracle_value=1.0,
    )

    assert normalize_oracle_attainment(oracle, 0.8) == 0.8


def test_oracle_attainment_normalizes_lower_is_better_metrics():
    oracle = OracleMetric(
        name="rmse",
        description="Lowest RMSE.",
        direction="lower_is_better",
        baseline_value=10.0,
        oracle_value=2.0,
    )

    assert normalize_oracle_attainment(oracle, 4.0) == 0.75


def test_score_result_dataclass_uses_structured_fields():
    result = ScoreResult(
        dataset_name="test",
        agent="claude",
        verdict="solved",
        core_insight_pass=True,
        required_coverage=1.0,
        supporting_coverage=0.5,
        oracle_attainment=0.9,
        oracle_metric_name="r2",
        oracle_agent_value=0.9,
        fatal_errors=[],
        efficiency={"trace_events": 10.0},
        criterion_results=[],
        summary="Good",
        raw_response="{}",
    )

    assert result.dataset_name == "test"
    assert result.verdict == "solved"
    assert result.oracle_attainment == 0.9
