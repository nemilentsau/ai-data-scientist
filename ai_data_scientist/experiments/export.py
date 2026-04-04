"""Experiment manifest and frontend export helpers."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import quote


def write_json(path: Path, payload: Any) -> None:
    """Write stable, indented JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def refresh_frontend_dist_api(*, repo_root: Path, experiments_dir: Path) -> None:
    """Refresh frontend/dist/api from experiment manifests."""
    frontend_dist_dir = repo_root / "frontend" / "dist"
    if not frontend_dist_dir.exists():
        return

    api_dir = frontend_dist_dir / "api"
    detail_dir = api_dir / "experiments"

    if api_dir.exists():
        shutil.rmtree(api_dir)
    detail_dir.mkdir(parents=True, exist_ok=True)

    experiments_index_path = experiments_dir / "index.json"
    if experiments_index_path.exists():
        experiments = json.loads(experiments_index_path.read_text())
    else:
        experiments = []

    write_json(api_dir / "experiments.json", {"experiments": experiments})

    for experiment in experiments:
        experiment_id = experiment.get("experiment_id")
        if not experiment_id:
            continue

        manifest_path = experiments_dir / experiment_id / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text())
        decorated_manifest = decorate_manifest_for_frontend(manifest)
        write_json(detail_dir / f"{experiment_id}.json", decorated_manifest)

        for artifact in manifest.get("artifacts", []):
            artifact_path = artifact.get("path")
            artifact_id = artifact.get("artifact_id")
            if not artifact_path or not artifact_id:
                continue

            source_path = repo_root / artifact_path
            if not source_path.exists():
                continue

            output_path = frontend_dist_dir / artifact_content_url(
                experiment_id, artifact
            ).lstrip("/")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, output_path)


def decorate_manifest_for_frontend(manifest: dict[str, Any]) -> dict[str, Any]:
    """Add content URLs to artifact records for dashboard consumption."""
    decorated = deepcopy(manifest)
    experiment_id = decorated.get("experiment", {}).get("experiment_id")
    if not experiment_id:
        return decorated

    decorated["artifacts"] = [
        {
            **artifact,
            "content_url": artifact_content_url(experiment_id, artifact),
        }
        for artifact in decorated.get("artifacts", [])
    ]
    return decorated


def artifact_content_url(experiment_id: str, artifact: dict[str, Any]) -> str:
    """Build the static dashboard content URL for a copied artifact."""
    suffix = Path(str(artifact.get("path") or "")).suffix
    encoded_experiment_id = quote(experiment_id, safe="")
    encoded_artifact_id = quote(str(artifact.get("artifact_id") or ""), safe="")
    return f"/api/artifacts/{encoded_experiment_id}/{encoded_artifact_id}/content{suffix}"
