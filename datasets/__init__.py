"""Benchmark datasets package — generation and registry."""

from datasets.registry import (
    DATASET_REGISTRY,
    DatasetMeta,
    get_dataset,
    list_datasets,
)

__all__ = [
    "DATASET_REGISTRY",
    "DatasetMeta",
    "get_dataset",
    "list_datasets",
]
