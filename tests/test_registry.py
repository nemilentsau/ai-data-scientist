"""Tests for dataset registry metadata and evaluation contracts."""

import pytest
from datasets.generator import GENERATORS
from datasets.registry import (
    CONTRACTS_DIR,
    DATASET_REGISTRY,
    EvaluationSpec,
    get_dataset,
    get_evaluation_spec,
    list_datasets,
)


def test_registry_contains_all_dataset_entries():
    assert len(DATASET_REGISTRY) == 20


def test_every_generator_has_registered_metadata():
    for name in GENERATORS:
        assert name in DATASET_REGISTRY, f"Generator '{name}' missing from registry"


def test_every_contract_file_is_present_and_named_after_dataset():
    contract_files = sorted(CONTRACTS_DIR.glob("*.yaml"))
    assert len(contract_files) == 20
    assert {path.stem for path in contract_files} == set(DATASET_REGISTRY)


def test_every_registry_entry_has_a_generator():
    for name in DATASET_REGISTRY:
        assert name in GENERATORS, f"Registry '{name}' has no generator"


def test_every_dataset_has_required_metadata_fields():
    for name, meta in DATASET_REGISTRY.items():
        assert meta.name == name, f"name field mismatch for {name}"
        assert meta.category, f"Missing category for {name}"
        assert meta.difficulty in ("easy", "medium", "hard"), f"Invalid difficulty for {name}"
        assert meta.expected_findings, f"No expected_findings for {name}"
        assert meta.key_pattern, f"No key_pattern for {name}"
        assert meta.traps, f"No traps for {name}"
        assert meta.generator_fn, f"No generator_fn for {name}"


def test_every_dataset_resolves_to_an_evaluation_contract():
    for meta in DATASET_REGISTRY.values():
        spec = get_evaluation_spec(meta)
        assert isinstance(spec, EvaluationSpec)
        assert meta.evaluation_spec is not None, f"{meta.name} should have an explicit contract"
        assert spec.must_have, f"{meta.name} has no must-have criteria"

        all_ids = [
            criterion.id
            for group in (spec.must_have, spec.supporting, spec.forbidden)
            for criterion in group
        ]
        assert len(all_ids) == len(set(all_ids)), f"{meta.name} has duplicate criterion ids"
        assert any(
            criterion.is_core_insight for criterion in spec.must_have
        ), f"{meta.name} has no core insight criterion"


def test_anscombes_quartet_has_custom_contract():
    spec = get_evaluation_spec("anscombes_quartet")

    assert len(spec.must_have) == 3
    assert any(
        criterion.id == "anscombes_quartet_different_shapes_identified"
        for criterion in spec.must_have
    )
    assert any(
        criterion.id == "anscombes_quartet_summary_only_conclusion"
        for criterion in spec.forbidden
    )


def test_deterministic_linear_exposes_an_oracle_metric():
    spec = get_evaluation_spec("deterministic_linear")

    assert spec.oracle_metric is not None
    assert spec.oracle_metric.name == "r2"
    assert spec.oracle_metric.oracle_value == 1.0


def test_get_dataset_returns_registered_entry():
    meta = get_dataset("pure_noise")
    assert meta.name == "pure_noise"
    assert meta.category == "Null/Baseline"


def test_unknown_dataset_name_raises_helpful_error():
    with pytest.raises(KeyError, match="Unknown dataset"):
        get_dataset("nonexistent_dataset")


def test_list_datasets_returns_all_names_sorted():
    names = list_datasets()
    assert names == sorted(names)
    assert len(names) == 20
