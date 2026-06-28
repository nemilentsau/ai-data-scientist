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
        "dependencies": {
            "dataset/profile.json": ["dataset/dataset.csv"],
            "results/target_distribution.parquet": [
                "dataset/dataset.csv",
                "queries/target_distribution.sql",
            ],
            "charts/target_distribution.vegalite.json": [
                "framing/framing.json",
                "results/target_distribution.summary.json",
            ],
            "renders/target_distribution.png": [
                "charts/target_distribution.vegalite.json",
                "results/target_distribution.parquet",
            ],
            "reviews/visual_review.json": [
                "renders/target_distribution.png",
                "reports/report.md",
            ],
            "reports/report.md": [
                "framing/framing.json",
                "queries/target_distribution.sql",
                "charts/target_distribution.vegalite.json",
            ],
        },
    }
    destination = run_dir / "lineage.json"
    destination.write_text(json.dumps(lineage, indent=2, sort_keys=True))
    return lineage

