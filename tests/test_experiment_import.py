"""Tests for importing legacy benchmark runs into the normalized experiment model."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import experiment_import as experiment_import_wrapper
import yaml
from ai_data_scientist.cli import experiment_import as experiment_import_cli
from ai_data_scientist.experiments.ids import build_experiment_id
from ai_data_scientist.experiments.importer import import_legacy_experiment


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _write_run(
    run_dir: Path,
    *,
    session_kind: str = "log",
    include_score: bool = True,
    verdict: str = "partial",
    include_code: bool = True,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "analysis_report.md").write_text("# Analysis\n")
    (run_dir / "trace.jsonl").write_text('{"event":"tool"}\n')
    if session_kind == "log":
        (run_dir / "session.log").write_text("session log")
        (run_dir / "final_message.md").write_text("final summary")
    elif session_kind == "json":
        (run_dir / "session.json").write_text('{"type":"result"}')
    if include_score:
        _write_json(
            run_dir / "score.json",
            {
                "verdict": verdict,
                "run_status": "completed" if verdict != "run_error" else "run_error",
                "core_insight_pass": verdict == "solved",
                "required_coverage": 1.0 if verdict == "solved" else 0.5,
                "supporting_coverage": 0.25,
                "fatal_errors": [],
                "summary": f"{verdict} result",
            },
        )
    if include_code:
        (run_dir / "analyze_dataset.py").write_text("print('artifact')\n")
    plots_dir = run_dir / "plots"
    plots_dir.mkdir()
    (plots_dir / "distribution.png").write_bytes(b"png")
    (plots_dir / "scatter.png").write_bytes(b"png")


def _db_count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _db_value(db_path: Path, query: str, params: tuple = ()) -> object:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(query, params).fetchone()[0]


def test_build_experiment_id_slugifies_title_and_can_omit_slug():
    fixed_time = datetime(2026, 4, 1, 8, 15, 8, tzinfo=UTC)

    assert (
        build_experiment_id(fixed_time, "Imported Solo Comparison")
        == "exp_20260401_081508_imported-solo-comparison"
    )
    assert build_experiment_id(fixed_time) == "exp_20260401_081508"


def test_root_wrapper_exposes_package_main():
    assert experiment_import_wrapper.main is experiment_import_cli.main


def test_import_records_normalized_entities_and_preserves_paths(tmp_path: Path):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {
            "name": "solo-codex",
            "description": "Single Codex agent",
            "team": [{"role": "codex"}],
            "harness": "harness/run_codex.sh",
        },
    )
    run_dir = repo_root / "results" / "runs" / "solo-codex" / "multimodal"
    _write_run(run_dir, session_kind="log", include_score=True, verdict="partial")

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_081508_imported",
        title="Imported experiment",
    )

    db_path = repo_root / "results" / "experiments" / "catalog.sqlite"
    index_payload = json.loads((repo_root / "results" / "experiments" / "index.json").read_text())
    manifest = json.loads((experiment_dir / "manifest.json").read_text())
    case_summaries = manifest["cases"]
    workflow_runs = manifest["workflow_runs"]
    agent_runs = manifest["agent_runs"]
    artifacts = manifest["artifacts"]
    evaluations = manifest["evaluations"]

    assert db_path.exists()
    assert sorted(path.name for path in experiment_dir.iterdir()) == ["manifest.json"]
    assert not (experiment_dir / "cases").exists()
    assert _db_count(db_path, "experiments") == 1
    assert _db_count(db_path, "config_snapshots") == 1
    assert _db_count(db_path, "cases") == 1
    assert _db_count(db_path, "workflow_runs") == 1
    assert _db_count(db_path, "agent_runs") == 1
    assert _db_count(db_path, "artifacts") == len(artifacts)
    assert _db_count(db_path, "evaluations") == 1
    assert index_payload[0]["summary"]["num_cases"] == 1
    assert index_payload[0]["summary"]["num_workflow_runs"] == 1
    assert index_payload[0]["summary"]["num_agent_runs"] == 1
    assert index_payload[0]["summary"]["num_evaluations"] == 1
    assert index_payload[0]["summary"]["verdict_counts"]["partial"] == 1
    assert case_summaries[0]["dataset"] == "multimodal"
    assert workflow_runs[0]["source_path"] == "results/runs/solo-codex/multimodal"
    assert workflow_runs[0]["status"] == "completed"
    assert agent_runs[0]["role"] == "codex"
    assert evaluations[0]["verdict"] == "partial"

    artifact_types = {artifact["type"] for artifact in artifacts}
    assert {
        "analysis_report",
        "score",
        "trace",
        "session",
        "final_message",
        "generated_code",
        "plot",
    }.issubset(artifact_types)

    code_artifact = next(
        artifact for artifact in artifacts if artifact["type"] == "generated_code"
    )
    assert code_artifact["path"] == "results/runs/solo-codex/multimodal/analyze_dataset.py"
    assert (repo_root / code_artifact["path"]).exists()
    assert manifest["cases"][0]["artifact_count"] == len(artifacts)


def test_import_indexes_config_level_benchmark_report_and_claude_session_json(tmp_path: Path):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-baseline.yaml",
        {
            "name": "solo-baseline",
            "description": "Single Claude agent",
            "team": [{"role": "claude", "model": "claude-opus-4-6"}],
            "harness": "harness/run_claude.sh",
        },
    )
    run_dir = repo_root / "results" / "runs" / "solo-baseline" / "concept_drift"
    _write_run(run_dir, session_kind="json", include_score=True, verdict="wrong")
    (repo_root / "results" / "runs" / "solo-baseline" / "benchmark_report.md").write_text(
        "# Report\n"
    )

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_090000_imported",
        title="Imported experiment",
    )

    db_path = repo_root / "results" / "experiments" / "catalog.sqlite"
    manifest = json.loads((experiment_dir / "manifest.json").read_text())
    artifact_index = manifest["artifacts"]
    benchmark_artifact = next(
        artifact for artifact in artifact_index if artifact["type"] == "benchmark_report"
    )
    session_artifact = next(
        artifact
        for artifact in artifact_index
        if artifact["type"] == "session" and artifact["case_id"] is not None
    )
    agent_index = manifest["agent_runs"]

    assert benchmark_artifact["path"] == "results/runs/solo-baseline/benchmark_report.md"
    assert benchmark_artifact["case_id"] is None
    assert session_artifact["path"] == "results/runs/solo-baseline/concept_drift/session.json"
    assert agent_index[0]["model"] == "claude-opus-4-6"
    assert _db_value(
        db_path,
        "SELECT COUNT(*) FROM artifacts WHERE type = ?",
        ("benchmark_report",),
    ) == 1


def test_import_refreshes_static_dashboard_api_when_frontend_dist_exists(tmp_path: Path):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "multimodal")

    stale_api_dir = repo_root / "frontend" / "dist" / "api"
    stale_api_dir.mkdir(parents=True, exist_ok=True)
    _write_json(stale_api_dir / "experiments.json", {"experiments": [{"experiment_id": "stale"}]})
    _write_json(
        stale_api_dir / "experiments" / "stale.json",
        {"experiment": {"experiment_id": "stale"}},
    )

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_091500_imported",
        title="Imported experiment",
    )

    manifest = json.loads((experiment_dir / "manifest.json").read_text())
    experiments_api = json.loads((stale_api_dir / "experiments.json").read_text())
    detail_api = json.loads(
        (
            stale_api_dir
            / "experiments"
            / "exp_20260401_091500_imported.json"
        ).read_text()
    )
    artifact = next(
        artifact for artifact in manifest["artifacts"] if artifact["type"] == "analysis_report"
    )
    decorated_artifact = next(
        candidate
        for candidate in detail_api["artifacts"]
        if candidate["artifact_id"] == artifact["artifact_id"]
    )

    assert experiments_api["experiments"][0]["experiment_id"] == "exp_20260401_091500_imported"
    assert not (stale_api_dir / "experiments" / "stale.json").exists()
    assert detail_api["experiment"]["experiment_id"] == "exp_20260401_091500_imported"
    assert "content_url" in decorated_artifact
    assert (
        repo_root
        / "frontend"
        / "dist"
        / decorated_artifact["content_url"].lstrip("/")
    ).exists()


def test_import_includes_experiment_scoped_synthesis_docs_with_matching_front_matter(
    tmp_path: Path,
):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "multimodal")
    _write_markdown(
        repo_root / "docs" / "artifacts" / "overview.md",
        """---
title: General Overview
artifact_type: synthesis_note
summary: Cross-case benchmark review.
experiment_ids:
  - exp_20260401_150000_solo
---
# Overview

This is linked.
""",
    )
    _write_markdown(
        repo_root / "docs" / "artifacts" / "ignored.md",
        """---
title: Ignored Note
artifact_type: synthesis_note
experiment_ids:
  - exp_other
---
# Ignore
""",
    )

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_150000_solo",
        title="Imported experiment",
    )

    manifest = json.loads((experiment_dir / "manifest.json").read_text())
    synthesis_artifacts = [
        artifact for artifact in manifest["artifacts"] if artifact["role"] == "synthesis_output"
    ]

    assert len(synthesis_artifacts) == 1
    assert synthesis_artifacts[0]["type"] == "synthesis_note"
    assert synthesis_artifacts[0]["title"] == "General Overview"
    assert synthesis_artifacts[0]["summary"] == "Cross-case benchmark review."
    assert synthesis_artifacts[0]["path"] == "docs/artifacts/overview.md"
    assert synthesis_artifacts[0]["case_id"] is None


def test_import_links_dataset_and_config_scoped_notes_to_matching_cases(tmp_path: Path):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_yaml(
        repo_root / "results" / "configs" / "solo-baseline.yaml",
        {"name": "solo-baseline", "team": [{"role": "claude"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "multimodal")
    _write_run(repo_root / "results" / "runs" / "solo-baseline" / "multimodal")
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "mnar")
    _write_markdown(
        repo_root / "docs" / "artifacts" / "multimodal-note.md",
        """---
title: Multimodal Note
artifact_type: dataset_note
summary: Applies only to the Codex multimodal case.
experiment_ids:
  - exp_20260401_151500_scoped
datasets:
  - multimodal
config_names:
  - solo-codex
---
# Multimodal Note
""",
    )

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_151500_scoped",
        title="Imported experiment",
    )

    manifest = json.loads((experiment_dir / "manifest.json").read_text())
    scoped_artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["title"] == "Multimodal Note"
    )

    assert scoped_artifact["scope"] == "case_selection"
    assert scoped_artifact["related_case_ids"] == [
        "case_exp_20260401_151500_scoped_solo-codex_multimodal"
    ]
    assert scoped_artifact["datasets"] == ["multimodal"]
    assert scoped_artifact["config_names"] == ["solo-codex"]


def test_import_respects_config_and_dataset_filters(tmp_path: Path):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_yaml(
        repo_root / "results" / "configs" / "solo-baseline.yaml",
        {"name": "solo-baseline", "team": [{"role": "claude"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "multimodal")
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "mnar")
    _write_run(repo_root / "results" / "runs" / "solo-baseline" / "multimodal")

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_100000_filtered",
        title="Filtered import",
        configs=["solo-codex"],
        datasets=["multimodal"],
    )

    cases_index = json.loads((experiment_dir / "manifest.json").read_text())["cases"]

    assert len(cases_index) == 1
    assert cases_index[0]["config_name"] == "solo-codex"
    assert cases_index[0]["dataset"] == "multimodal"


def test_reimporting_same_experiment_preserves_existing_cases_when_adding_config(
    tmp_path: Path,
):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-baseline.yaml",
        {"name": "solo-baseline", "team": [{"role": "claude"}]},
    )
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-baseline" / "multimodal")

    import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_111000_shared",
        title="Shared experiment",
        configs=["solo-baseline"],
        datasets=["multimodal"],
    )

    _write_run(repo_root / "results" / "runs" / "solo-codex" / "concept_drift")
    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_111000_shared",
        title="Shared experiment",
        configs=["solo-codex"],
        datasets=["concept_drift"],
    )

    cases_index = json.loads((experiment_dir / "manifest.json").read_text())["cases"]

    assert {(case["config_name"], case["dataset"]) for case in cases_index} == {
        ("solo-baseline", "multimodal"),
        ("solo-codex", "concept_drift"),
    }


def test_import_omits_evaluation_when_score_is_missing_and_falls_back_to_minimal_config(
    tmp_path: Path,
):
    repo_root = tmp_path
    run_dir = repo_root / "results" / "runs" / "custom-config" / "overlapping_clusters"
    _write_run(run_dir, session_kind="log", include_score=False, verdict="partial")

    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_20260401_103000_missing-score",
        title="Missing score import",
    )

    db_path = repo_root / "results" / "experiments" / "catalog.sqlite"
    manifest = json.loads((experiment_dir / "manifest.json").read_text())
    config_snapshots = manifest["config_snapshots"]
    cases_index = manifest["cases"]
    workflow_runs = manifest["workflow_runs"]
    evaluations = manifest["evaluations"]

    assert config_snapshots[0]["config_name"] == "custom-config"
    assert config_snapshots[0]["source_path"] is None
    assert workflow_runs[0]["status"] == "completed_unscored"
    assert cases_index[0]["evaluation_id"] is None
    assert evaluations == []
    assert _db_count(db_path, "evaluations") == 0


def test_cli_writes_metadata_for_requested_filters_and_explicit_id(
    tmp_path: Path, capsys
):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "multimodal")
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "mnar")

    exit_code = experiment_import_cli.main(
        [
            "--repo-root",
            str(repo_root),
            "--title",
            "Imported experiment",
            "--experiment-id",
            "exp_20260401_120000_manual",
            "--config",
            "solo-codex",
            "--dataset",
            "multimodal",
        ]
    )

    captured = capsys.readouterr()
    cases_index = json.loads(
        (
            repo_root
            / "results"
            / "experiments"
            / "exp_20260401_120000_manual"
            / "manifest.json"
        ).read_text()
    )["cases"]

    assert exit_code == 0
    assert "exp_20260401_120000_manual" in captured.out
    assert len(cases_index) == 1
    assert cases_index[0]["dataset"] == "multimodal"


def test_cli_generates_experiment_id_when_not_provided(
    tmp_path: Path, monkeypatch, capsys
):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-baseline.yaml",
        {"name": "solo-baseline", "team": [{"role": "claude"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-baseline" / "concept_drift")
    monkeypatch.setattr(
        "ai_data_scientist.cli.experiment_import.build_experiment_id",
        lambda slug=None: "exp_auto_id",
    )

    exit_code = experiment_import_cli.main(
        [
            "--repo-root",
            str(repo_root),
            "--title",
            "Imported experiment",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "exp_auto_id" in captured.out
    assert (repo_root / "results" / "experiments" / "exp_auto_id").exists()
    assert (repo_root / "results" / "experiments" / "catalog.sqlite").exists()


def test_cli_requires_title_argument():
    try:
        experiment_import_cli.main([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse to reject missing required title")


def test_reimport_rewrites_existing_experiment_rows_without_duplicate_records(
    tmp_path: Path,
):
    repo_root = tmp_path
    _write_yaml(
        repo_root / "results" / "configs" / "solo-codex.yaml",
        {"name": "solo-codex", "team": [{"role": "codex"}]},
    )
    _write_run(repo_root / "results" / "runs" / "solo-codex" / "multimodal")

    import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_fixed",
        title="Imported experiment",
    )

    _write_run(repo_root / "results" / "runs" / "solo-codex" / "mnar")
    experiment_dir = import_legacy_experiment(
        repo_root=repo_root,
        experiment_id="exp_fixed",
        title="Imported experiment",
        datasets=["mnar"],
    )

    db_path = repo_root / "results" / "experiments" / "catalog.sqlite"
    manifest = json.loads((experiment_dir / "manifest.json").read_text())

    assert _db_count(db_path, "experiments") == 1
    assert _db_count(db_path, "cases") == 2
    assert {case["dataset"] for case in manifest["cases"]} == {"mnar", "multimodal"}
