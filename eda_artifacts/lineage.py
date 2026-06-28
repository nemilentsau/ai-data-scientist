import json
from pathlib import Path
from typing import Any


def write_lineage(run_dir: Path, *, status: str, revision_count: int) -> dict[str, Any]:
    """Write a compact lineage index for all produced run artifacts."""
    artifacts = sorted(
        str(path.relative_to(run_dir))
        for path in run_dir.rglob("*")
        if path.is_file() and path.name != "lineage.json"
    )
    lineage = {
        "status": status,
        "revision_count": revision_count,
        "artifacts": artifacts,
        "dependencies": _dependencies_for_attempts(run_dir, revision_count + 1),
    }
    destination = run_dir / "lineage.json"
    destination.write_text(json.dumps(lineage, indent=2, sort_keys=True))
    return lineage


def _dependencies_for_attempts(run_dir: Path, attempt_count: int) -> dict[str, list[str]]:
    dependencies = {
        "00-dataset/profile.json": ["00-dataset/dataset.csv"],
        "01-eda-framer/output.json": [
            "01-eda-framer/prompt.md",
            "01-eda-framer/output.schema.json",
            "00-dataset/profile.json",
        ],
    }
    for attempt in range(1, attempt_count + 1):
        builder = f"02-artifact-builder/attempt-{attempt}"
        execution = f"03-execution/attempt-{attempt}"
        render = f"04-render/attempt-{attempt}"
        reviewer = f"05-visual-reviewer/attempt-{attempt}"

        dependencies[f"{builder}/output.json"] = [
            f"{builder}/prompt.md",
            f"{builder}/output.schema.json",
            "01-eda-framer/output.json",
        ]
        dependencies[f"{builder}/query.sql"] = [f"{builder}/output.json"]
        dependencies[f"{builder}/chart.vegalite.json"] = [f"{builder}/output.json"]
        dependencies[f"{execution}/result.parquet"] = [
            "00-dataset/dataset.csv",
            f"{builder}/query.sql",
        ]
        dependencies[f"{execution}/result.summary.json"] = [f"{execution}/result.parquet"]
        dependencies[f"{render}/chart.png"] = [
            f"{builder}/chart.vegalite.json",
            f"{execution}/result.parquet",
        ]
        dependencies[f"{reviewer}/output.json"] = [
            f"{reviewer}/prompt.md",
            f"{reviewer}/image-inputs.json",
            f"{reviewer}/output.schema.json",
            f"{render}/chart.png",
            f"{builder}/chart.vegalite.json",
            f"{execution}/result.summary.json",
        ]
        dependencies[f"{reviewer}/report.md"] = [
            f"{reviewer}/output.json",
            f"{render}/chart.png",
            f"{execution}/result.summary.json",
        ]

    return {
        artifact: inputs
        for artifact, inputs in dependencies.items()
        if (run_dir / artifact).exists()
    }
