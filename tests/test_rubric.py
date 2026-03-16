"""Tests for dataset-specific contract formatting."""

from datasets.registry import get_dataset
from reviewer.rubric import TRANSCRIPT_CHAR_LIMIT, format_rubric_for_prompt


def test_contract_prompt_lists_required_sections():
    prompt = format_rubric_for_prompt(get_dataset("simpsons_paradox"))

    assert "Evaluation Contract" in prompt
    assert "Must Have Criteria" in prompt
    assert "Supporting Criteria" in prompt
    assert "Forbidden Criteria" in prompt
    assert "Verdict Rules" in prompt


def test_contract_prompt_includes_named_criteria_for_pilot_dataset():
    prompt = format_rubric_for_prompt(get_dataset("simpsons_paradox"))

    assert "simpsons_paradox_reversal_identified" in prompt
    assert "simpsons_paradox_correct_conclusion" in prompt
    assert "simpsons_paradox_aggregate_only_conclusion" in prompt


def test_contract_prompt_includes_oracle_metric_when_available():
    prompt = format_rubric_for_prompt(get_dataset("deterministic_linear"))

    assert "Oracle Metric" in prompt
    assert "`r2`" in prompt
    assert "higher_is_better" in prompt


def test_contract_prompt_includes_custom_contract_for_anscombes():
    prompt = format_rubric_for_prompt(get_dataset("anscombes_quartet"))

    assert "anscombes_quartet_different_shapes_identified" in prompt
    assert "anscombes_quartet_visualized_all_batches" in prompt
    assert "anscombes_quartet_summary_only_conclusion" in prompt


def test_transcript_character_limit_is_20000():
    assert TRANSCRIPT_CHAR_LIMIT == 20_000
