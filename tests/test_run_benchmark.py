"""Tests for benchmark orchestration and scoring migration."""

import json
from pathlib import Path
from types import SimpleNamespace

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


def test_benchmark_run_uses_new_multiagent_config_and_canonical_analysis_report(
    tmp_path: Path, monkeypatch
):
    repo_root = tmp_path
    results_dir = repo_root / "results"
    configs_dir = results_dir / "configs"
    runs_dir = results_dir / "runs"
    datasets_dir = repo_root / "datasets" / "generated"

    _write_yaml(
        configs_dir / "codex-multiagent-v1.yaml",
        {
            "name": "codex-multiagent-v1",
            "description": "External orchestrator with Codex execution",
            "roles": {
                "task_framer": {
                    "backend": "claude_cli",
                    "prompt": "prompts/active/task-framer.md",
                    "model": "claude-opus-4-6",
                },
                "analysis_planner": {
                    "backend": "claude_cli",
                    "prompt": "prompts/active/analysis-planner.md",
                    "model": "claude-opus-4-6",
                },
                "analysis_executor": {
                    "backend": "codex_cli",
                    "prompt": "prompts/active/analysis-executor.md",
                    "model": "gpt-5.4",
                },
                "method_critic": {
                    "backend": "claude_cli",
                    "prompt": "prompts/active/method-critic.md",
                    "model": "claude-opus-4-6",
                },
                "visual_critic": {
                    "backend": "claude_cli",
                    "prompt": "prompts/active/visual-critic.md",
                    "model": "claude-opus-4-6",
                },
                "verifier": {
                    "backend": "claude_cli",
                    "prompt": "prompts/active/verifier.md",
                    "model": "claude-opus-4-6",
                },
                "memory_curator": {
                    "backend": "claude_cli",
                    "prompt": "prompts/active/memory-curator.md",
                    "model": "claude-opus-4-6",
                },
            },
            "runtime": {
                "max_revision_rounds": 1,
                "max_reframes": 1,
                "memory_curator": True,
            },
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

    prompt_capture: dict[str, str] = {}

    def fake_run_workflow_for_dataset(
        config: dict,
        config_name: str,
        dataset_name: str,
        dataset_csv: Path,
    ):
        assert config_name == "codex-multiagent-v1"
        assert config["roles"]["analysis_executor"]["backend"] == "codex_cli"
        run_dir = runs_dir / config_name / dataset_name
        run_dir.mkdir(parents=True, exist_ok=True)
        analysis_dir = run_dir / "artifacts" / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        (analysis_dir / "analysis_report.md").write_text("# Analysis\n")
        (analysis_dir / "findings.json").write_text('{"items": []}')
        verification_dir = run_dir / "artifacts" / "verification"
        verification_dir.mkdir(parents=True, exist_ok=True)
        (verification_dir / "verification.json").write_text('{"verdict":"pass"}')
        invocation_dir = run_dir / "invocations" / "analysis_executor-0001"
        (invocation_dir / "output").mkdir(parents=True, exist_ok=True)
        (invocation_dir / "logs").mkdir(exist_ok=True)
        (invocation_dir / "manifest.json").write_text(
            json.dumps({"invocation_id": "analysis_executor-0001", "role": "analysis_executor"})
        )
        (invocation_dir / "output" / "analysis_report.md").write_text("# Analysis\n")
        return True

    def fake_build_reviewer_prompt(dataset_metadata, analysis_report, session_transcript):
        del dataset_metadata, session_transcript
        prompt_capture["analysis_report"] = analysis_report
        return "prompt"

    def fake_subprocess_run(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "result": json.dumps(
                        {
                            "must_have": {},
                            "supporting": {},
                            "forbidden": {},
                            "summary": "partial result",
                        }
                    )
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(benchmark_cli, "generate_datasets", lambda: None)
    monkeypatch.setattr(benchmark_cli, "run_workflow_for_dataset", fake_run_workflow_for_dataset)
    monkeypatch.setattr("reviewer.scorer.build_reviewer_prompt", fake_build_reviewer_prompt)
    monkeypatch.setattr("reviewer.scorer.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_benchmark.py",
            "--config",
            "codex-multiagent-v1",
            "--datasets",
            "multimodal",
            "--skip-generate",
            "--skip-import",
        ],
    )

    benchmark_cli.main()

    run_dir = runs_dir / "codex-multiagent-v1" / "multimodal"
    assert (run_dir / "artifacts" / "analysis" / "analysis_report.md").exists()
    assert (run_dir / "artifacts" / "verification" / "verification.json").exists()
    assert prompt_capture.get("analysis_report") == "# Analysis\n"
