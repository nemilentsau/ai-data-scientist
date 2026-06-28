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
            "--question",
            "Assess whether monthly_rent_usd has a simple distribution.",
        ]
    )

    run_dir = tmp_path / "multimodal" / "cli-smoke"
    assert exit_code == 0
    assert (run_dir / "01-eda-framer" / "output.json").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "query.sql").exists()
    assert (run_dir / "03-execution" / "attempt-1" / "result.parquet").exists()
    assert (run_dir / "02-artifact-builder" / "attempt-1" / "chart.vegalite.json").exists()
    assert (run_dir / "04-render" / "attempt-1" / "chart.png").exists()
    assert (run_dir / "05-visual-reviewer" / "attempt-1" / "report.md").exists()
    assert not (run_dir / "02-artifact-builder" / "attempt-1" / "report.md").exists()
    assert json.loads((run_dir / "lineage.json").read_text())["status"] == "passed_visual_gate"


def test_cli_requires_user_question(tmp_path):
    exit_code = main(
        [
            "run",
            "--adapter",
            "fake",
            "--run-id",
            "missing-question",
            "--run-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 2


def test_cli_rejects_blank_user_question(tmp_path):
    exit_code = main(
        [
            "run",
            "--adapter",
            "fake",
            "--run-id",
            "blank-question",
            "--run-root",
            str(tmp_path),
            "--question",
            "   ",
        ]
    )

    assert exit_code == 2


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
