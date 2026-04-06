"""Deterministic dataset profiling helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


def profile_dataset(*, dataset_csv: Path, run_dir: Path) -> dict[str, Path]:
    """Write a canonical profile artifact set for one dataset run."""
    profile_dir = run_dir / "artifacts" / "profile"
    dataset_dir = run_dir / "artifacts" / "dataset"
    profile_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(dataset_csv)

    dataset_path = dataset_dir / "dataset.csv"
    shutil.copy2(dataset_csv, dataset_path)

    schema_path = profile_dir / "schema.json"
    column_summary_path = profile_dir / "column_summary.csv"
    sample_rows_path = profile_dir / "sample_rows.csv"
    null_summary_path = profile_dir / "null_summary.csv"

    schema_path.write_text(frame.dtypes.astype(str).to_json(indent=2))
    frame.describe(include="all").transpose().to_csv(column_summary_path)
    frame.head(20).to_csv(sample_rows_path, index=False)
    frame.isna().sum().to_csv(null_summary_path)

    return {
        "schema": schema_path,
        "column_summary": column_summary_path,
        "sample_rows": sample_rows_path,
        "null_summary": null_summary_path,
        "dataset": dataset_path,
    }
