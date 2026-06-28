import json

from eda_artifacts.cli import main


def test_fake_cli_run_creates_multimodal_artifact_tree(tmp_path):
    exit_code = main(
        [
            "run",
            "--adapter",
            "fake",
            "--run-id",
            "cli-smoke",
            "--run-root",
            str(tmp_path),
        ]
    )

    run_dir = tmp_path / "multimodal" / "cli-smoke"
    assert exit_code == 0
    assert (run_dir / "queries" / "target_distribution.sql").exists()
    assert (run_dir / "results" / "target_distribution.parquet").exists()
    assert (run_dir / "charts" / "target_distribution.vegalite.json").exists()
    assert (run_dir / "renders" / "target_distribution.png").exists()
    assert (run_dir / "reports" / "report.md").exists()
    assert json.loads((run_dir / "lineage.json").read_text())["status"] == "passed_visual_gate"


def test_cli_rejects_non_multimodal_dataset(tmp_path):
    exit_code = main(
        [
            "run",
            "--dataset",
            "simpsons_paradox",
            "--adapter",
            "fake",
            "--run-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 2
