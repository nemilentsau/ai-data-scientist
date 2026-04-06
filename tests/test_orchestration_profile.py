"""Tests for deterministic dataset profiling."""

from __future__ import annotations

from pathlib import Path

from ai_data_scientist.orchestration.profile import profile_dataset


def test_profile_dataset_writes_expected_artifacts(tmp_path: Path):
    dataset_csv = tmp_path / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n3,4\n")

    profile_paths = profile_dataset(dataset_csv=dataset_csv, run_dir=tmp_path / "run")

    assert (tmp_path / "run" / "artifacts" / "dataset" / "dataset.csv").exists()
    assert profile_paths["schema"].exists()
    assert profile_paths["column_summary"].exists()
    assert profile_paths["sample_rows"].exists()
    assert profile_paths["null_summary"].exists()
