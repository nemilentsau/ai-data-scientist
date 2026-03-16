"""Registry of benchmark datasets loaded from YAML contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast

import yaml

CriterionGroup = Literal["must_have", "supporting", "forbidden"]
TaskFamily = Literal["discovery", "predictive", "clustering", "specialized", "general"]
OracleDirection = Literal["higher_is_better", "lower_is_better"]

CONTRACTS_DIR = Path(__file__).with_name("contracts")


@dataclass(frozen=True)
class Criterion:
    """A single reviewer-checkable criterion."""

    id: str
    description: str
    verification_hint: str = ""
    is_core_insight: bool = False


@dataclass(frozen=True)
class OracleMetric:
    """Normalized quantitative target for a task with a known optimum."""

    name: str
    description: str
    direction: OracleDirection
    baseline_value: float
    oracle_value: float
    tolerance: float | None = None


@dataclass(frozen=True)
class EvaluationSpec:
    """Structured evaluation contract for a dataset."""

    task_family: TaskFamily
    must_have: list[Criterion] = field(default_factory=list)
    supporting: list[Criterion] = field(default_factory=list)
    forbidden: list[Criterion] = field(default_factory=list)
    oracle_metric: OracleMetric | None = None


@dataclass(frozen=True)
class DatasetMeta:
    """Metadata and scoring contract for a benchmark dataset."""

    name: str
    category: str
    difficulty: str
    description: str
    expected_findings: list[str]
    key_pattern: str
    traps: list[str]
    generator_fn: str
    evaluation_spec: EvaluationSpec


def _expect_mapping(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a mapping, got {type(value).__name__}")
    return cast(dict[str, object], value)


def _expect_str(mapping: dict[str, object], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise TypeError(f"{context}.{key} must be a non-empty string")
    return value


def _expect_optional_str(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string when present")
    return value


def _expect_bool(mapping: dict[str, object], key: str) -> bool:
    value = mapping.get(key, False)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a boolean when present")
    return value


def _expect_string_list(mapping: dict[str, object], key: str, *, context: str) -> list[str]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise TypeError(f"{context}.{key} must be a non-empty list")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise TypeError(f"{context}.{key}[{index}] must be a non-empty string")
        items.append(item)
    return items


def _expect_float(mapping: dict[str, object], key: str, *, context: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, int | float):
        raise TypeError(f"{context}.{key} must be numeric")
    return float(value)


def _parse_criterion(
    value: object,
    *,
    dataset_name: str,
    group: CriterionGroup,
) -> Criterion:
    data = _expect_mapping(value, context=f"{dataset_name}.{group}")
    criterion_id = _expect_str(data, "id", context=f"{dataset_name}.{group}")
    if not criterion_id.startswith(f"{dataset_name}_"):
        raise ValueError(
            f"{dataset_name}.{group} criterion id must start with '{dataset_name}_': {criterion_id}"
        )

    criterion = Criterion(
        id=criterion_id,
        description=_expect_str(data, "description", context=f"{dataset_name}.{group}"),
        verification_hint=_expect_optional_str(data, "verification_hint"),
        is_core_insight=_expect_bool(data, "is_core_insight"),
    )

    if group != "must_have" and criterion.is_core_insight:
        raise ValueError(f"{criterion_id} marks core insight outside must_have")

    return criterion


def _parse_criterion_group(
    mapping: dict[str, object],
    key: CriterionGroup,
    *,
    dataset_name: str,
) -> list[Criterion]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise TypeError(f"{dataset_name}.evaluation_spec.{key} must be a non-empty list")
    return [
        _parse_criterion(item, dataset_name=dataset_name, group=key)
        for item in value
    ]


def _parse_oracle_metric(value: object, *, dataset_name: str) -> OracleMetric | None:
    if value is None:
        return None

    data = _expect_mapping(value, context=f"{dataset_name}.evaluation_spec.oracle_metric")
    direction = _expect_str(
        data,
        "direction",
        context=f"{dataset_name}.evaluation_spec.oracle_metric",
    )
    if direction not in {"higher_is_better", "lower_is_better"}:
        raise ValueError(
            f"{dataset_name}.evaluation_spec.oracle_metric.direction must be valid"
        )

    tolerance_raw = data.get("tolerance")
    tolerance = None
    if tolerance_raw is not None:
        if not isinstance(tolerance_raw, int | float):
            raise TypeError(
                f"{dataset_name}.evaluation_spec.oracle_metric.tolerance must be numeric"
            )
        tolerance = float(tolerance_raw)

    return OracleMetric(
        name=_expect_str(data, "name", context=f"{dataset_name}.evaluation_spec.oracle_metric"),
        description=_expect_str(
            data,
            "description",
            context=f"{dataset_name}.evaluation_spec.oracle_metric",
        ),
        direction=cast(OracleDirection, direction),
        baseline_value=_expect_float(
            data,
            "baseline_value",
            context=f"{dataset_name}.evaluation_spec.oracle_metric",
        ),
        oracle_value=_expect_float(
            data,
            "oracle_value",
            context=f"{dataset_name}.evaluation_spec.oracle_metric",
        ),
        tolerance=tolerance,
    )


def _parse_evaluation_spec(value: object, *, dataset_name: str) -> EvaluationSpec:
    data = _expect_mapping(value, context=f"{dataset_name}.evaluation_spec")
    task_family = _expect_str(data, "task_family", context=f"{dataset_name}.evaluation_spec")
    if task_family not in {
        "discovery",
        "predictive",
        "clustering",
        "specialized",
        "general",
    }:
        raise ValueError(f"{dataset_name}.evaluation_spec.task_family is invalid")

    must_have = _parse_criterion_group(data, "must_have", dataset_name=dataset_name)
    supporting = _parse_criterion_group(data, "supporting", dataset_name=dataset_name)
    forbidden = _parse_criterion_group(data, "forbidden", dataset_name=dataset_name)

    all_ids = [criterion.id for criterion in [*must_have, *supporting, *forbidden]]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError(f"{dataset_name} contains duplicate criterion ids")
    if not any(criterion.is_core_insight for criterion in must_have):
        raise ValueError(f"{dataset_name} must define a core insight in must_have")

    return EvaluationSpec(
        task_family=cast(TaskFamily, task_family),
        must_have=must_have,
        supporting=supporting,
        forbidden=forbidden,
        oracle_metric=_parse_oracle_metric(data.get("oracle_metric"), dataset_name=dataset_name),
    )


def _parse_dataset_contract(path: Path) -> DatasetMeta:
    raw = yaml.safe_load(path.read_text())
    data = _expect_mapping(raw, context=str(path))
    dataset_name = _expect_str(data, "name", context=str(path))

    if path.stem != dataset_name:
        raise ValueError(f"{path.name} must match dataset name '{dataset_name}'")

    difficulty = _expect_str(data, "difficulty", context=dataset_name)
    if difficulty not in {"easy", "medium", "hard"}:
        raise ValueError(f"{dataset_name}.difficulty must be one of easy/medium/hard")

    return DatasetMeta(
        name=dataset_name,
        category=_expect_str(data, "category", context=dataset_name),
        difficulty=difficulty,
        description=_expect_str(data, "description", context=dataset_name),
        expected_findings=_expect_string_list(data, "expected_findings", context=dataset_name),
        key_pattern=_expect_str(data, "key_pattern", context=dataset_name),
        traps=_expect_string_list(data, "traps", context=dataset_name),
        generator_fn=_expect_str(data, "generator_fn", context=dataset_name),
        evaluation_spec=_parse_evaluation_spec(
            data.get("evaluation_spec"),
            dataset_name=dataset_name,
        ),
    )


@lru_cache(maxsize=1)
def _load_dataset_registry() -> dict[str, DatasetMeta]:
    if not CONTRACTS_DIR.exists():
        raise FileNotFoundError(f"Contracts directory not found: {CONTRACTS_DIR}")

    registry: dict[str, DatasetMeta] = {}
    for path in sorted(CONTRACTS_DIR.glob("*.yaml")):
        meta = _parse_dataset_contract(path)
        if meta.name in registry:
            raise ValueError(f"Duplicate dataset name in contracts: {meta.name}")
        registry[meta.name] = meta

    if not registry:
        raise ValueError(f"No dataset contracts found in {CONTRACTS_DIR}")

    return registry


DATASET_REGISTRY: dict[str, DatasetMeta] = _load_dataset_registry()


def get_dataset(name: str) -> DatasetMeta:
    """Return metadata for a single dataset by name."""
    try:
        return DATASET_REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(DATASET_REGISTRY))
        raise KeyError(f"Unknown dataset '{name}'. Available datasets: {available}") from None


def get_evaluation_spec(name_or_meta: str | DatasetMeta) -> EvaluationSpec:
    """Return the evaluation contract for a dataset."""
    meta = get_dataset(name_or_meta) if isinstance(name_or_meta, str) else name_or_meta
    return meta.evaluation_spec


def list_datasets() -> list[str]:
    """Return a sorted list of all registered dataset names."""
    return sorted(DATASET_REGISTRY)
