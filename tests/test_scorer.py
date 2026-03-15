"""Tests for scorer — prompt building and result parsing (no LLM calls)."""

from datasets.registry import get_dataset
from reviewer.scorer import build_reviewer_prompt, ScoreResult


def test_reviewer_prompt_includes_ground_truth():
    meta = get_dataset("simpsons_paradox")
    prompt = build_reviewer_prompt(meta, "Some analysis", "Some transcript")

    assert meta.key_pattern in prompt
    for finding in meta.expected_findings:
        assert finding in prompt
    for trap in meta.traps:
        assert trap in prompt


def test_reviewer_prompt_includes_critical_miss_rule():
    meta = get_dataset("simpsons_paradox")
    prompt = build_reviewer_prompt(meta, "Some analysis", "Some transcript")
    assert "Key Pattern" in prompt
    assert "critical" in prompt.lower() or "CRITICAL" in prompt


def test_reviewer_prompt_includes_agent_output():
    meta = get_dataset("pure_noise")
    report = "This is the agent's analysis report."
    transcript = "This is the session transcript."

    prompt = build_reviewer_prompt(meta, report, transcript)
    assert report in prompt
    assert transcript in prompt


def test_reviewer_prompt_truncates_long_transcript():
    meta = get_dataset("pure_noise")
    long_transcript = "x" * 50000
    prompt = build_reviewer_prompt(meta, "report", long_transcript)
    # The prompt should contain at most 20000 chars of transcript
    assert "x" * 20000 in prompt
    assert "x" * 20001 not in prompt


def test_score_result_dataclass():
    result = ScoreResult(
        dataset_name="test",
        agent="claude",
        scores={"data_loading_inspection": 4},
        modifiers=[{"description": "bonus", "value": 1}],
        total=25,
        summary="Good",
        raw_response="{}",
    )
    assert result.dataset_name == "test"
    assert result.total == 25
