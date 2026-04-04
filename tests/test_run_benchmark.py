"""Tests for benchmark orchestration and experiment catalog refresh."""

import json
from pathlib import Path

import run_benchmark as run_benchmark_wrapper
import yaml
from ai_data_scientist.cli import benchmark as benchmark_cli
from datasets.generator import NAME_TO_FILENAME


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def test_root_wrapper_exposes_package_main():
    assert run_benchmark_wrapper.main is benchmark_cli.main


def test_benchmark_run_refreshes_experiment_catalog_from_current_results(
    tmp_path: Path, monkeypatch
):
    repo_root = tmp_path
    results_dir = repo_root / "results"
    configs_dir = results_dir / "configs"
    runs_dir = results_dir / "runs"
    datasets_dir = repo_root / "datasets" / "generated"

    _write_yaml(
        configs_dir / "solo-codex.yaml",
        {
            "name": "solo-codex",
            "description": "Single Codex agent",
            "team": [{"role": "codex", "model": "gpt-5.4"}],
            "harness": "harness/run_codex.sh",
        },
    )
    datasets_dir.mkdir(parents=True, exist_ok=True)
    dataset_csv = datasets_dir / NAME_TO_FILENAME["multimodal"]
    dataset_csv.write_text("feature,target\n1,2\n")

    monkeypatch.setattr(benchmark_cli, "ROOT", repo_root)
    monkeypatch.setattr(benchmark_cli, "DATASETS_DIR", datasets_dir)
    monkeypatch.setattr(benchmark_cli, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(benchmark_cli, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(benchmark_cli, "RUNS_DIR", runs_dir)

    def fake_run_workflow_for_dataset(
        config: dict,
        config_name: str,
        dataset_name: str,
        dataset_csv: Path,
    ):
        run_dir = runs_dir / config_name / dataset_name
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "analysis_report.md").write_text("# Analysis\n")
        (run_dir / "trace.jsonl").write_text('{"event":"tool"}\n')
        (run_dir / "session.log").write_text("session log")
        (run_dir / "final_message.md").write_text("final summary")
        plots_dir = run_dir / "plots"
        plots_dir.mkdir(exist_ok=True)
        (plots_dir / "distribution.png").write_bytes(b"png")
        return True

    def fake_score_results(dataset_names: list[str], config_name: str, config: dict):
        for dataset_name in dataset_names:
            _write_json(
                runs_dir / config_name / dataset_name / "score.json",
                {
                    "verdict": "partial",
                    "run_status": "completed",
                    "core_insight_pass": False,
                    "required_coverage": 0.5,
                    "supporting_coverage": 0.25,
                    "fatal_errors": [],
                    "summary": "partial result",
                },
            )
        return [object()]

    def fake_generate_report(scores: list[object], config_name: str):
        report_path = runs_dir / config_name / "benchmark_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# Report\n")
        return report_path

    monkeypatch.setattr(benchmark_cli, "generate_datasets", lambda: None)
    monkeypatch.setattr(benchmark_cli, "run_workflow_for_dataset", fake_run_workflow_for_dataset)
    monkeypatch.setattr(benchmark_cli, "score_results", fake_score_results)
    monkeypatch.setattr(benchmark_cli, "generate_report", fake_generate_report)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_benchmark.py",
            "--config",
            "solo-codex",
            "--datasets",
            "multimodal",
            "--skip-generate",
            "--experiment-id",
            "exp_20260401_130000_live",
            "--experiment-title",
            "Live benchmark",
        ],
    )

    benchmark_cli.main()

    manifest_path = (
        results_dir
        / "experiments"
        / "exp_20260401_130000_live"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())

    assert manifest_path.exists()
    assert manifest["experiment"]["experiment_id"] == "exp_20260401_130000_live"
    assert manifest["cases"][0]["dataset"] == "multimodal"
    assert any(artifact["type"] == "benchmark_report" for artifact in manifest["artifacts"])
