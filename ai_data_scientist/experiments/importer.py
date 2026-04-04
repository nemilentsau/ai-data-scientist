"""Import legacy benchmark run trees into normalized experiment metadata."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ai_data_scientist.experiments.export import refresh_frontend_dist_api, write_json
from ai_data_scientist.experiments.ids import slugify
from ai_data_scientist.experiments.store import (
    catalog_db_path,
    load_experiment_manifest,
    load_experiments_index,
    persist_experiment,
)
from ai_data_scientist.orchestration.config import primary_agent_metadata

VERDICTS = ("solved", "partial", "wrong", "failed", "run_error")
PLOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}


def import_legacy_experiment(
    *,
    repo_root: Path,
    experiment_id: str,
    title: str,
    description: str | None = None,
    configs: list[str] | None = None,
    datasets: list[str] | None = None,
) -> Path:
    """Build normalized experiment metadata over existing legacy run artifacts."""
    results_dir = repo_root / "results"
    runs_dir = results_dir / "runs"
    configs_dir = results_dir / "configs"
    experiments_dir = results_dir / "experiments"
    experiment_dir = experiments_dir / experiment_id
    db_path = catalog_db_path(experiments_dir)

    selected_configs = _selected_config_names(runs_dir, configs)
    selected_datasets = set(datasets or [])
    existing_manifest = _load_existing_manifest(db_path, experiment_id)
    if existing_manifest is not None:
        selected_configs = sorted(
            {
                *selected_configs,
                *[snapshot["config_name"] for snapshot in existing_manifest["config_snapshots"]],
            }
        )
        if selected_datasets:
            selected_datasets.update(case["dataset"] for case in existing_manifest["cases"])

    config_records: list[dict[str, Any]] = []
    case_records: list[dict[str, Any]] = []
    workflow_records: list[dict[str, Any]] = []
    agent_records: list[dict[str, Any]] = []
    artifact_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []

    for config_name in selected_configs:
        config_record = _build_config_snapshot(
            repo_root=repo_root,
            experiment_id=experiment_id,
            config_name=config_name,
            configs_dir=configs_dir,
        )
        config_records.append(config_record)

        config_run_dir = runs_dir / config_name
        report_path = config_run_dir / "benchmark_report.md"
        if report_path.exists():
            artifact_records.append(
                _build_artifact_record(
                    repo_root=repo_root,
                    experiment_id=experiment_id,
                    config_snapshot_id=config_record["config_snapshot_id"],
                    path=report_path,
                    artifact_type="benchmark_report",
                    role="benchmark_output",
                    case_id=None,
                    workflow_run_id=None,
                    agent_run_id=None,
                )
            )

        for dataset_dir in sorted(config_run_dir.iterdir()):
            if not dataset_dir.is_dir():
                continue
            dataset_name = dataset_dir.name
            if selected_datasets and dataset_name not in selected_datasets:
                continue

            case_id = f"case_{experiment_id}_{config_name}_{dataset_name}"
            workflow_run_id = f"workflow_{case_id}_01"
            agent_run_id = f"agent_{workflow_run_id}_01"

            case_artifacts = _collect_case_artifacts(
                repo_root=repo_root,
                experiment_id=experiment_id,
                config_snapshot_id=config_record["config_snapshot_id"],
                case_id=case_id,
                workflow_run_id=workflow_run_id,
                agent_run_id=agent_run_id,
                run_dir=dataset_dir,
            )
            artifact_records.extend(case_artifacts)
            case_artifact_ids = [artifact["artifact_id"] for artifact in case_artifacts]

            evaluation = _build_evaluation_record(
                repo_root=repo_root,
                experiment_id=experiment_id,
                case_id=case_id,
                workflow_run_id=workflow_run_id,
                score_path=dataset_dir / "score.json",
            )
            evaluation_id = None
            if evaluation is not None:
                evaluation_records.append(evaluation)
                evaluation_id = evaluation["evaluation_id"]

            workflow_status = _workflow_status(
                has_analysis_report=any(
                    artifact["type"] == "analysis_report" for artifact in case_artifacts
                ),
                evaluation=evaluation,
            )

            workflow_records.append(
                {
                    "workflow_run_id": workflow_run_id,
                    "experiment_id": experiment_id,
                    "case_id": case_id,
                    "attempt": 1,
                    "status": workflow_status,
                    "source_kind": "legacy_import",
                    "source_path": dataset_dir.relative_to(repo_root).as_posix(),
                    "config_snapshot_id": config_record["config_snapshot_id"],
                    "agent_run_ids": [agent_run_id],
                    "artifact_ids": case_artifact_ids,
                    "evaluation_id": evaluation_id,
                }
            )

            primary_agent = primary_agent_metadata(config_record.get("config", {}))
            agent_records.append(
                {
                    "agent_run_id": agent_run_id,
                    "experiment_id": experiment_id,
                    "case_id": case_id,
                    "workflow_run_id": workflow_run_id,
                    "config_snapshot_id": config_record["config_snapshot_id"],
                    "role": primary_agent.get("role", config_name),
                    "model": primary_agent.get("model"),
                    "parent_agent_run_id": None,
                    "status": workflow_status,
                    "source_kind": "legacy_import",
                    "artifact_ids": case_artifact_ids,
                }
            )

            case_records.append(
                {
                    "case_id": case_id,
                    "experiment_id": experiment_id,
                    "dataset": dataset_name,
                    "config_name": config_name,
                    "config_snapshot_id": config_record["config_snapshot_id"],
                    "workflow_run_ids": [workflow_run_id],
                    "latest_workflow_run_id": workflow_run_id,
                    "agent_run_ids": [agent_run_id],
                    "artifact_ids": case_artifact_ids,
                    "evaluation_id": evaluation_id,
                }
            )

    if config_records:
        artifact_records.extend(
            _collect_experiment_synthesis_artifacts(
                repo_root=repo_root,
                experiment_id=experiment_id,
                default_config_snapshot_id=config_records[0]["config_snapshot_id"],
                case_records=case_records,
            )
        )

    experiment_record = _build_experiment_record(
        experiment_id=experiment_id,
        title=title,
        description=description or "Imported legacy benchmark experiment metadata.",
        config_records=config_records,
        case_records=case_records,
        workflow_records=workflow_records,
        agent_records=agent_records,
        artifact_records=artifact_records,
        evaluation_records=evaluation_records,
    )
    persist_experiment(
        db_path=db_path,
        config_records=config_records,
        case_records=case_records,
        workflow_records=workflow_records,
        agent_records=agent_records,
        artifact_records=artifact_records,
        evaluation_records=evaluation_records,
        experiment_record=experiment_record,
    )
    manifest = load_experiment_manifest(db_path, experiment_id)
    if manifest is None:
        raise RuntimeError(f"imported experiment {experiment_id} was not found in catalog")

    if experiment_dir.exists():
        import shutil

        shutil.rmtree(experiment_dir)
    experiment_dir.mkdir(parents=True, exist_ok=True)
    write_json(experiment_dir / "manifest.json", manifest)
    write_json(experiments_dir / "index.json", load_experiments_index(db_path))
    refresh_frontend_dist_api(repo_root=repo_root, experiments_dir=experiments_dir)
    return experiment_dir


def _load_existing_manifest(db_path: Path, experiment_id: str) -> dict[str, Any] | None:
    if not db_path.exists():
        return None
    return load_experiment_manifest(db_path, experiment_id)


def _selected_config_names(runs_dir: Path, configs: list[str] | None) -> list[str]:
    config_names = sorted(path.name for path in runs_dir.iterdir() if path.is_dir())
    if configs is None:
        return config_names
    allowed = set(configs)
    return [config_name for config_name in config_names if config_name in allowed]


def _build_config_snapshot(
    *,
    repo_root: Path,
    experiment_id: str,
    config_name: str,
    configs_dir: Path,
) -> dict[str, Any]:
    config_path = _first_existing_path(
        [configs_dir / f"{config_name}.yaml", configs_dir / f"{config_name}.yml"]
    )
    if config_path is None:
        config_payload = {"name": config_name, "team": []}
        source_path = None
    else:
        with config_path.open() as file:
            config_payload = yaml.safe_load(file)
        source_path = config_path.relative_to(repo_root).as_posix()

    return {
        "config_snapshot_id": f"config_{experiment_id}_{config_name}",
        "experiment_id": experiment_id,
        "config_name": config_name,
        "description": config_payload.get("description"),
        "harness": config_payload.get("harness"),
        "source_path": source_path,
        "config": config_payload,
    }


def _collect_case_artifacts(
    *,
    repo_root: Path,
    experiment_id: str,
    config_snapshot_id: str,
    case_id: str,
    workflow_run_id: str,
    agent_run_id: str,
    run_dir: Path,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.iterdir()):
        if path.is_dir():
            if path.name == "plots":
                for plot_path in sorted(path.iterdir()):
                    if plot_path.is_file() and plot_path.suffix.lower() in PLOT_EXTENSIONS:
                        records.append(
                            _build_artifact_record(
                                repo_root=repo_root,
                                experiment_id=experiment_id,
                                config_snapshot_id=config_snapshot_id,
                                path=plot_path,
                                artifact_type="plot",
                                role="harness_output",
                                case_id=case_id,
                                workflow_run_id=workflow_run_id,
                                agent_run_id=agent_run_id,
                            )
                        )
                continue
            continue

        artifact_type, role = _artifact_type_and_role(path)
        records.append(
            _build_artifact_record(
                repo_root=repo_root,
                experiment_id=experiment_id,
                config_snapshot_id=config_snapshot_id,
                path=path,
                artifact_type=artifact_type,
                role=role,
                case_id=case_id,
                workflow_run_id=workflow_run_id,
                agent_run_id=agent_run_id,
            )
        )
    return records


def _collect_experiment_synthesis_artifacts(
    *,
    repo_root: Path,
    experiment_id: str,
    default_config_snapshot_id: str,
    case_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    docs_dir = repo_root / "docs" / "artifacts"
    if not docs_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(docs_dir.rglob("*.md")):
        metadata = _read_synthesis_front_matter(path)
        if metadata is None or experiment_id not in metadata["experiment_ids"]:
            continue
        related_case_ids = _select_related_case_ids(case_records, metadata)
        if metadata["scope"] != "experiment" and not related_case_ids:
            continue
        records.append(
            _build_artifact_record(
                repo_root=repo_root,
                experiment_id=experiment_id,
                config_snapshot_id=default_config_snapshot_id,
                path=path,
                artifact_type=metadata["artifact_type"],
                role="synthesis_output",
                case_id=None,
                workflow_run_id=None,
                agent_run_id=None,
                source_kind="docs_import",
                extra={
                    "title": metadata["title"],
                    "summary": metadata.get("summary"),
                    "scope": metadata["scope"],
                    "datasets": metadata["datasets"],
                    "config_names": metadata["config_names"],
                    "related_case_ids": related_case_ids,
                },
            )
        )
    return records


def _artifact_type_and_role(path: Path) -> tuple[str, str]:
    if path.name == "analysis_report.md":
        return "analysis_report", "harness_output"
    if path.name == "score.json":
        return "score", "evaluation_output"
    if path.name == "trace.jsonl":
        return "trace", "trace_output"
    if path.name in {"session.json", "session.log"}:
        return "session", "session_output"
    if path.name == "final_message.md":
        return "final_message", "harness_output"
    if path.suffix == ".py":
        return "generated_code", "harness_output"
    return "artifact", "harness_output"


def _build_artifact_record(
    *,
    repo_root: Path,
    experiment_id: str,
    config_snapshot_id: str,
    path: Path,
    artifact_type: str,
    role: str,
    case_id: str | None,
    workflow_run_id: str | None,
    agent_run_id: str | None,
    source_kind: str = "legacy_import",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relative_path = path.relative_to(repo_root).as_posix()
    record = {
        "artifact_id": f"artifact_{experiment_id}_{slugify(relative_path)}",
        "experiment_id": experiment_id,
        "config_snapshot_id": config_snapshot_id,
        "case_id": case_id,
        "workflow_run_id": workflow_run_id,
        "agent_run_id": agent_run_id,
        "type": artifact_type,
        "role": role,
        "media_type": _media_type(path, artifact_type),
        "path": relative_path,
        "size_bytes": path.stat().st_size,
        "created_at": _file_timestamp(path),
        "source_kind": source_kind,
    }
    if extra:
        record.update(extra)
    return record


def _build_evaluation_record(
    *,
    repo_root: Path,
    experiment_id: str,
    case_id: str,
    workflow_run_id: str,
    score_path: Path,
) -> dict[str, Any] | None:
    if not score_path.exists():
        return None
    with score_path.open() as file:
        payload = json.load(file)
    return {
        "evaluation_id": f"evaluation_{workflow_run_id}",
        "experiment_id": experiment_id,
        "case_id": case_id,
        "workflow_run_id": workflow_run_id,
        "source_path": score_path.relative_to(repo_root).as_posix(),
        "verdict": payload.get("verdict"),
        "run_status": payload.get("run_status"),
        "core_insight_pass": payload.get("core_insight_pass"),
        "required_coverage": payload.get("required_coverage"),
        "supporting_coverage": payload.get("supporting_coverage"),
        "fatal_errors": payload.get("fatal_errors", []),
        "summary": payload.get("summary"),
    }


def _workflow_status(*, has_analysis_report: bool, evaluation: dict[str, Any] | None) -> str:
    if evaluation is not None:
        if evaluation.get("verdict") == "run_error" or evaluation.get("run_status") == "run_error":
            return "run_error"
        return "completed"
    if has_analysis_report:
        return "completed_unscored"
    return "incomplete"


def _build_experiment_record(
    *,
    experiment_id: str,
    title: str,
    description: str,
    config_records: list[dict[str, Any]],
    case_records: list[dict[str, Any]],
    workflow_records: list[dict[str, Any]],
    agent_records: list[dict[str, Any]],
    artifact_records: list[dict[str, Any]],
    evaluation_records: list[dict[str, Any]],
) -> dict[str, Any]:
    verdict_counts = {verdict: 0 for verdict in VERDICTS}
    for evaluation in evaluation_records:
        verdict = evaluation.get("verdict")
        if verdict in verdict_counts:
            verdict_counts[verdict] += 1

    timestamp = _utc_now()
    return {
        "experiment_id": experiment_id,
        "title": title,
        "description": description,
        "source_kind": "legacy_import",
        "created_at": timestamp,
        "updated_at": timestamp,
        "config_snapshot_ids": [record["config_snapshot_id"] for record in config_records],
        "case_ids": [record["case_id"] for record in case_records],
        "workflow_run_ids": [record["workflow_run_id"] for record in workflow_records],
        "agent_run_ids": [record["agent_run_id"] for record in agent_records],
        "artifact_ids": [record["artifact_id"] for record in artifact_records],
        "evaluation_ids": [record["evaluation_id"] for record in evaluation_records],
        "summary": {
            "num_cases": len(case_records),
            "num_workflow_runs": len(workflow_records),
            "num_agent_runs": len(agent_records),
            "num_artifacts": len(artifact_records),
            "num_evaluations": len(evaluation_records),
            "verdict_counts": verdict_counts,
        },
    }


def _media_type(path: Path, artifact_type: str) -> str:
    if artifact_type in {"score", "session"} and path.suffix == ".json":
        return "application/json"
    if artifact_type == "trace":
        return "application/x-ndjson"
    if artifact_type in {"analysis_report", "final_message", "benchmark_report"}:
        return "text/markdown"
    if artifact_type == "generated_code":
        return "text/x-python"
    if path.suffix == ".md":
        return "text/markdown"
    if artifact_type == "plot":
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), "application/octet-stream")
    if path.suffix == ".log":
        return "text/plain"
    return "application/octet-stream"


def _file_timestamp(path: Path) -> str:
    return (
        datetime.fromtimestamp(path.stat().st_mtime, UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _first_existing_path(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _select_related_case_ids(
    case_records: list[dict[str, Any]], metadata: dict[str, Any]
) -> list[str]:
    if metadata["scope"] == "experiment":
        return []

    related_case_ids = []
    for case in case_records:
        if metadata["datasets"] and case["dataset"] not in metadata["datasets"]:
            continue
        if metadata["config_names"] and case["config_name"] not in metadata["config_names"]:
            continue
        related_case_ids.append(case["case_id"])
    return related_case_ids


def _read_synthesis_front_matter(path: Path) -> dict[str, Any] | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None

    _, _, remainder = text.partition("---\n")
    front_matter, separator, _body = remainder.partition("\n---\n")
    if not separator:
        return None

    payload = yaml.safe_load(front_matter) or {}
    experiment_ids = payload.get("experiment_ids")
    if isinstance(experiment_ids, str):
        experiment_ids = [experiment_ids]
    if not isinstance(experiment_ids, list) or not experiment_ids:
        return None

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        title = path.stem.replace("-", " ").replace("_", " ").title()

    summary = payload.get("summary")
    if summary is not None and not isinstance(summary, str):
        summary = str(summary)

    artifact_type = payload.get("artifact_type")
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        artifact_type = "synthesis_note"

    datasets = _normalize_string_list(payload.get("datasets"))
    config_names = _normalize_string_list(payload.get("config_names"))
    if datasets and config_names:
        scope = "case_selection"
    elif datasets:
        scope = "dataset"
    elif config_names:
        scope = "config"
    else:
        scope = "experiment"

    return {
        "title": title.strip(),
        "summary": summary.strip() if isinstance(summary, str) else None,
        "artifact_type": artifact_type.strip(),
        "experiment_ids": [str(experiment_id) for experiment_id in experiment_ids],
        "datasets": datasets,
        "config_names": config_names,
        "scope": scope,
    }


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
