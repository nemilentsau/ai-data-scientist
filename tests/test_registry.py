"""Tests for dataset registry — metadata completeness and consistency."""

import pytest

from datasets.registry import DATASET_REGISTRY, DatasetMeta, get_dataset, list_datasets
from datasets.generator import GENERATORS


def test_registry_has_20_entries():
    assert len(DATASET_REGISTRY) == 20


def test_all_generator_keys_have_registry_entries():
    for name in GENERATORS:
        assert name in DATASET_REGISTRY, f"Generator '{name}' missing from registry"


def test_all_registry_keys_have_generators():
    for name in DATASET_REGISTRY:
        assert name in GENERATORS, f"Registry '{name}' has no generator"


def test_every_entry_has_required_fields():
    for name, meta in DATASET_REGISTRY.items():
        assert meta.name == name, f"name field mismatch for {name}"
        assert meta.category, f"Missing category for {name}"
        assert meta.difficulty in ("easy", "medium", "hard"), f"Invalid difficulty for {name}"
        assert meta.expected_findings, f"No expected_findings for {name}"
        assert meta.key_pattern, f"No key_pattern for {name}"
        assert meta.traps, f"No traps for {name}"
        assert meta.generator_fn, f"No generator_fn for {name}"


def test_generator_fn_references_exist():
    import datasets.generator as gen_module

    for name, meta in DATASET_REGISTRY.items():
        assert hasattr(gen_module, meta.generator_fn), (
            f"Registry '{name}' references {meta.generator_fn} but it doesn't exist"
        )


def test_get_dataset_returns_correct_entry():
    meta = get_dataset("pure_noise")
    assert meta.name == "pure_noise"
    assert meta.category == "Null/Baseline"


def test_get_dataset_raises_on_unknown_name():
    with pytest.raises(KeyError, match="Unknown dataset"):
        get_dataset("nonexistent_dataset")


def test_list_datasets_returns_sorted_names():
    names = list_datasets()
    assert names == sorted(names)
    assert len(names) == 20
