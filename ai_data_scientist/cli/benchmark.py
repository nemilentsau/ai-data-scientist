#!/usr/bin/env python3
"""Benchmark orchestrator: generate datasets -> run agents -> score -> report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

from ai_data_scientist.experiments.ids import build_experiment_id
from ai_data_scientist.experiments.importer import import_legacy_experiment
from ai_data_scientist.experiments.store import catalog_db_path, load_experiment_manifest
from ai_data_scientist.orchestration.config import primary_agent_metadata
from ai_data_scientist.orchestration.runner import run_workflow

ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = ROOT / "datasets" / "generated"
RESULTS_DIR = ROOT / "results"
CONFIGS_DIR = RESULTS_DIR / "configs"
RUNS_DIR = RESULTS_DIR / "runs"


def load_config(config_name: str) -> dict:
    """Load a config YAML by name (without .yaml extension)."""
    config_path = CONFIGS_DIR / f"{config_name}.yaml"
    if not config_path.exists():
        print(f"ERROR: Config '{config_name}' not found at {config_path}")
        sys.exit(1)
    with config_path.open() as file:
        return yaml.safe_load(file)


def generate_datasets() -> None:
    """Generate all benchmark datasets."""
    print("=== Generating datasets ===")
    subprocess.run(
        [sys.executable, "-m", "datasets.generator"],
        cwd=ROOT,
        check=True,
    )
    print(f"Datasets generated in {DATASETS_DIR}\n")


def run_workflow_for_dataset(
    config: dict,
    config_name: str,
    dataset_name: str,
    dataset_csv: Path,
) -> bool:
    """Run a workflow config on a single dataset."""
    run_results = RUNS_DIR / config_name / dataset_name
    run_results.mkdir(parents=True, exist_ok=True)

    print(f"  Running {config_name} on {dataset_name}...")
    try:
        return run_workflow(
            config=config,
            dataset_name=dataset_name,
            dataset_csv=dataset_csv,
            results_dir=run_results,
            root=ROOT,
        )
    except Exception as exc:
        print(f"  ERROR: {config_name} on {dataset_name}: {exc}")
        return False


def run_agent(config: dict, config_name: str, dataset_name: str, dataset_csv: Path) -> bool:
    """Backward-compatible alias for workflow execution."""
    return run_workflow_for_dataset(config, config_name, dataset_name, dataset_csv)


def score_results(dataset_names: list[str], config_name: str, config: dict):
    """Score all outputs for a config."""
    print("\n=== Scoring results ===")
    from datasets.registry import get_dataset
    from reviewer.scorer import score_analysis

    agent_name = str(primary_agent_metadata(config).get("role") or config_name)
    all_scores = []

    for ds_name in dataset_names:
        metadata = get_dataset(ds_name)
        run_results = RUNS_DIR / config_name / ds_name
        if not run_results.exists():
            print(f"  No results for {config_name}/{ds_name}, skipping")
            continue
        print(f"  Scoring {config_name}/{ds_name}...")
        try:
            result = score_analysis(ds_name, agent_name, metadata, run_results)
            all_scores.append(result)

            score_file = run_results / "score.json"
            score_file.write_text(
                json.dumps(
                    {
                        "dataset": result.dataset_name,
                        "config": config_name,
                        "agent": result.agent,
                        "verdict": result.verdict,
                        "run_status": result.run_status,
                        "rerun_recommended": result.rerun_recommended,
                        "run_error_reasons": result.run_error_reasons,
                        "core_insight_pass": result.core_insight_pass,
                        "required_coverage": result.required_coverage,
                        "supporting_coverage": result.supporting_coverage,
                        "oracle_attainment": result.oracle_attainment,
                        "oracle_metric_name": result.oracle_metric_name,
                        "oracle_agent_value": result.oracle_agent_value,
                        "fatal_errors": result.fatal_errors,
                        "efficiency": result.efficiency,
                        "criterion_results": [
                            {
                                "criterion_id": item.criterion_id,
                                "group": item.group,
                                "status": item.status,
                                "justification": item.justification,
                                "evidence": item.evidence,
                            }
                            for item in result.criterion_results
                        ],
                        "summary": result.summary,
                        "raw_response": result.raw_response,
                    },
                    indent=2,
                )
            )
            print(
                "    "
                f"Verdict: {result.verdict}, "
                f"required={result.required_coverage:.0%}, "
                f"supporting={result.supporting_coverage:.0%}"
            )
        except Exception as exc:
            print(f"    ERROR scoring {config_name}/{ds_name}: {exc}")

    return all_scores


def generate_report(scores, config_name: str):
    """Generate report for a config run."""
    print("\n=== Generating report ===")
    from reviewer.report import generate_report as _generate_report

    report_dir = RUNS_DIR / config_name
    report_path = report_dir / "benchmark_report.md"
    report = _generate_report(scores, report_path)
    print(f"Report saved to {report_path}")
    return report


def refresh_experiment_catalog(
    *,
    config_name: str,
    config: dict,
    dataset_names: list[str],
    experiment_id: str | None,
    experiment_title: str | None,
    experiment_description: str | None,
) -> Path:
    """Import the current benchmark outputs into the experiment catalog."""
    experiments_dir = RESULTS_DIR / "experiments"
    resolved_experiment_id = experiment_id or build_experiment_id(
        slug=experiment_title or config_name
    )
    existing_manifest = None
    db_path = catalog_db_path(experiments_dir)
    if db_path.exists():
        existing_manifest = load_experiment_manifest(db_path, resolved_experiment_id)

    resolved_title = experiment_title
    if resolved_title is None and existing_manifest is not None:
        resolved_title = existing_manifest["experiment"]["title"]
    if resolved_title is None:
        resolved_title = f"{config_name} benchmark"

    resolved_description = experiment_description
    if resolved_description is None and existing_manifest is not None:
        resolved_description = existing_manifest["experiment"].get("description")
    if resolved_description is None:
        resolved_description = config.get("description") or f"Benchmark results for {config_name}."

    return import_legacy_experiment(
        repo_root=ROOT,
        experiment_id=resolved_experiment_id,
        title=resolved_title,
        description=resolved_description,
        configs=[config_name],
        datasets=dataset_names,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="AI Data Scientist Benchmark")
    parser.add_argument(
        "--config",
        required=True,
        help="Config name (matches results/configs/<name>.yaml)",
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=None,
        help="Specific dataset names to run (default: all)",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip dataset generation (use existing CSVs)",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip agent runs (use existing results)",
    )
    parser.add_argument(
        "--skip-score",
        action="store_true",
        help="Skip scoring (use existing scores)",
    )
    parser.add_argument(
        "--experiment-id",
        help="Optional experiment id to refresh in the experiment catalog.",
    )
    parser.add_argument(
        "--experiment-title",
        help=(
            "Optional experiment title. Reuses the existing title when "
            "importing into an existing experiment."
        ),
    )
    parser.add_argument(
        "--experiment-description",
        help=(
            "Optional experiment description. Reuses the existing description "
            "when importing into an existing experiment."
        ),
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Skip importing benchmark metadata into results/experiments.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Benchmark run: {timestamp}")
    print(f"Config: {args.config} — {config.get('description', '')}")

    if not args.skip_generate:
        generate_datasets()

    if args.datasets:
        dataset_names = args.datasets
    else:
        from datasets.registry import list_datasets

        dataset_names = list_datasets()

    print(f"Datasets ({len(dataset_names)}): {', '.join(dataset_names)}\n")

    if not args.skip_run:
        print("=== Running agent ===")
        from datasets.generator import NAME_TO_FILENAME

        for ds_name in dataset_names:
            csv_path = DATASETS_DIR / NAME_TO_FILENAME.get(ds_name, f"{ds_name}.csv")
            if not csv_path.exists():
                print(f"  WARNING: {csv_path} not found, skipping")
                continue
            run_workflow_for_dataset(config, args.config, ds_name, csv_path)

    if not args.skip_score:
        scores = score_results(dataset_names, args.config, config)
        if scores:
            generate_report(scores, args.config)
    else:
        print("Scoring skipped.")

    if not args.skip_import:
        experiment_dir = refresh_experiment_catalog(
            config_name=args.config,
            config=config,
            dataset_names=dataset_names,
            experiment_id=args.experiment_id,
            experiment_title=args.experiment_title,
            experiment_description=args.experiment_description,
        )
        print(f"\nExperiment metadata saved to {experiment_dir}")

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
