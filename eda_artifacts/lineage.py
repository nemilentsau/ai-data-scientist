import json
from pathlib import Path
from typing import Any


def write_lineage(
    run_dir: Path,
    *,
    status: str,
    artifact_statuses: dict[str, str],
) -> dict[str, Any]:
    """Write a compact lineage index for all produced run artifacts."""
    artifacts = sorted(
        str(path.relative_to(run_dir))
        for path in run_dir.rglob("*")
        if path.is_file() and path.name != "lineage.json"
    )
    lineage = {
        "status": status,
        "artifact_statuses": dict(sorted(artifact_statuses.items())),
        "artifacts": artifacts,
        "dependencies": _dependencies_for_artifact_attempts(run_dir),
    }
    destination = run_dir / "lineage.json"
    destination.write_text(json.dumps(lineage, indent=2, sort_keys=True))
    return lineage


def _dependencies_for_artifact_attempts(run_dir: Path) -> dict[str, list[str]]:
    dependencies: dict[str, list[str]] = {
        "00-dataset/profile.json": ["00-dataset/dataset.csv"],
        "01-eda-framer/output.json": [
            "01-eda-framer/prompt.md",
            "01-eda-framer/user-question.txt",
            "01-eda-framer/output.schema.json",
            "00-dataset/profile.json",
        ],
    }
    for artifact_id, attempt in _artifact_attempts(run_dir):
        builder = f"02-artifact-builder/{artifact_id}/attempt-{attempt}"
        execution = f"03-execution/{artifact_id}/attempt-{attempt}"
        render = f"04-render/{artifact_id}/attempt-{attempt}"
        reviewer = f"05-visual-reviewer/{artifact_id}/attempt-{attempt}"

        dependencies[f"{builder}/build-context.json"] = ["01-eda-framer/output.json"]
        dependencies[f"{builder}/output.json"] = [
            f"{builder}/prompt.md",
            f"{builder}/build-context.json",
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
        dependencies[f"{reviewer}/review-context.json"] = [
            "01-eda-framer/output.json",
            f"{render}/chart.png",
        ]
        dependencies[f"{reviewer}/output.json"] = [
            f"{reviewer}/prompt.md",
            f"{reviewer}/review-context.json",
            f"{reviewer}/image-inputs.json",
            f"{reviewer}/output.schema.json",
            f"{render}/chart.png",
        ]
        dependencies[f"{reviewer}/report.md"] = [
            f"{reviewer}/output.json",
            f"{render}/chart.png",
        ]

    report_dependencies = _passed_review_report_dependencies(run_dir)
    if (run_dir / "06-synthesis" / "report.md").exists():
        dependencies["06-synthesis/report.md"] = report_dependencies

    return {
        artifact: inputs
        for artifact, inputs in dependencies.items()
        if (run_dir / artifact).exists()
    }


def _artifact_attempts(run_dir: Path) -> list[tuple[str, int]]:
    attempts: list[tuple[str, int]] = []
    builder_root = run_dir / "02-artifact-builder"
    if not builder_root.exists():
        return attempts
    for artifact_dir in sorted(path for path in builder_root.iterdir() if path.is_dir()):
        for attempt_dir in sorted(path for path in artifact_dir.iterdir() if path.is_dir()):
            prefix = "attempt-"
            if attempt_dir.name.startswith(prefix):
                attempts.append(
                    (artifact_dir.name, int(attempt_dir.name.removeprefix(prefix)))
                )
    return attempts


def _passed_review_report_dependencies(run_dir: Path) -> list[str]:
    reports: list[str] = []
    reviewer_root = run_dir / "05-visual-reviewer"
    if not reviewer_root.exists():
        return reports
    for output_path in sorted(reviewer_root.glob("*/attempt-*/output.json")):
        try:
            output = json.loads(output_path.read_text())
        except json.JSONDecodeError:
            continue
        if output.get("verdict") != "pass":
            continue
        report_path = output_path.with_name("report.md")
        if report_path.exists():
            reports.append(str(report_path.relative_to(run_dir)))
    return reports
