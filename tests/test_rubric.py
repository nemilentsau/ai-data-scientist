"""Tests for scoring rubric — structure and formatting."""

from reviewer.rubric import (
    RUBRIC_DIMENSIONS,
    BONUS_MODIFIERS,
    PENALTY_MODIFIERS,
    MAX_DIMENSION_SCORE,
    MAX_MODIFIER,
    MIN_MODIFIER,
    CRITICAL_MISS_THRESHOLD,
    CRITICAL_MISS_PENALTY,
    CRITICAL_MISS_ZEROES_BONUSES,
    Dimension,
    Modifier,
    format_rubric_for_prompt,
)


def test_seven_dimensions():
    assert len(RUBRIC_DIMENSIONS) == 7


def test_max_dimension_score_is_35():
    assert MAX_DIMENSION_SCORE == 35


def test_modifier_bounds():
    assert MAX_MODIFIER == 3
    assert MIN_MODIFIER == -8  # room for critical miss penalty (-5) + regular penalties (-3)


def test_critical_miss_constants():
    assert CRITICAL_MISS_THRESHOLD == 3
    assert CRITICAL_MISS_PENALTY == -5
    assert CRITICAL_MISS_ZEROES_BONUSES is True


def test_all_bonus_modifiers_are_positive():
    for m in BONUS_MODIFIERS:
        assert m.value > 0


def test_all_penalty_modifiers_are_negative():
    for m in PENALTY_MODIFIERS:
        assert m.value < 0


def test_dimension_names_are_unique():
    names = [d.name for d in RUBRIC_DIMENSIONS]
    assert len(names) == len(set(names))


def test_format_rubric_for_prompt_contains_all_dimensions():
    text = format_rubric_for_prompt()
    for dim in RUBRIC_DIMENSIONS:
        assert dim.description in text


def test_format_rubric_for_prompt_contains_modifiers():
    text = format_rubric_for_prompt()
    assert "Bonus" in text
    assert "Penalty" in text


def test_format_rubric_for_prompt_contains_critical_miss_rule():
    text = format_rubric_for_prompt()
    assert "Critical Miss" in text
    assert "pattern_identification" in text
