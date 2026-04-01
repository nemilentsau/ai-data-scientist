#!/usr/bin/env python3
"""Benchmark orchestrator: generate datasets → run agents → score → report."""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
DATASETS_DIR = ROOT / "datasets" / "generated"
RESULTS_DIR = ROOT / "results"
CONFIGS_DIR = RESULTS_DIR / "configs"
RUNS_DIR = RESULTS_DIR / "runs"
HARNESS_DIR = ROOT / "harness"


def load_config(config_name: str) -> dict:
    """Load a config YAML by name (without .yaml extension)."""
    config_path = CONFIGS_DIR / f"{config_name}.yaml"
    if not config_path.exists():
        print(f"ERROR: Config '{config_name}' not found at {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def generate_datasets():
    """Generate all benchmark datasets."""
    print("=== Generating datasets ===")
    subprocess.run(
        [sys.executable, "-m", "datasets.generator"],
        cwd=ROOT,
        check=True,
    )
    print(f"Datasets generated in {DATASETS_DIR}\n")


def run_agent(config: dict, config_name: str, dataset_name: str, dataset_csv: Path):
    """Run an agent config on a single dataset."""
    harness_script = ROOT / config["harness"]
    if not harness_script.exists():
        print(f"  WARNING: {harness_script} not found, skipping")
        return False

    run_results = RUNS_DIR / config_name / dataset_name
    run_results.mkdir(parents=True, exist_ok=True)

    # Resolve prompt file(s) from team config
    team = config.get("team", [])
    prompt_file = ROOT / team[0]["prompt"] if team else HARNESS_DIR / "prompt_template.txt"
    max_turns = str(team[0].get("max_turns", 30)) if team else "30"
    model = team[0].get("model", "") if team else ""
    tools = ",".join(team[0].get("tools", [])) if team else "Bash,Read,Write,Edit,Glob,Grep"

    print(f"  Running {config_name} on {dataset_name}...")
    try:
        subprocess.run(
            [
                "bash",
                str(harness_script),
                dataset_name,
                str(dataset_csv),
                str(run_results),
                str(prompt_file),
                max_turns,
                model,
                tools,
            ],
            check=False,
        )
        return True
    except Exception as e:
        print(f"  ERROR: {config_name} on {dataset_name}: {e}")
        return False


def score_results(dataset_names: list[str], config_name: str, config: dict):
    """Score all outputs for a config."""
    print("\n=== Scoring results ===")
    from datasets.registry import get_dataset
    from reviewer.scorer import score_analysis

    agent_name = config.get("team", [{}])[0].get("role", config_name)
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

            # Save individual score
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
        except Exception as e:
            print(f"    ERROR scoring {config_name}/{ds_name}: {e}")

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


def main():
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
    args = parser.parse_args()

    config = load_config(args.config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Benchmark run: {timestamp}")
    print(f"Config: {args.config} — {config.get('description', '')}")

    # Step 1: Generate datasets
    if not args.skip_generate:
        generate_datasets()

    # Determine which datasets to run
    if args.datasets:
        dataset_names = args.datasets
    else:
        from datasets.registry import list_datasets

        dataset_names = list_datasets()

    print(f"Datasets ({len(dataset_names)}): {', '.join(dataset_names)}\n")

    # Step 2: Run agent
    if not args.skip_run:
        print("=== Running agent ===")
        from datasets.generator import NAME_TO_FILENAME

        for ds_name in dataset_names:
            csv_path = DATASETS_DIR / NAME_TO_FILENAME.get(ds_name, f"{ds_name}.csv")
            if not csv_path.exists():
                print(f"  WARNING: {csv_path} not found, skipping")
                continue
            run_agent(config, args.config, ds_name, csv_path)

    # Step 3: Score
    if not args.skip_score:
        scores = score_results(dataset_names, args.config, config)

        # Step 4: Report
        if scores:
            generate_report(scores, args.config)
    else:
        print("Scoring skipped.")

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
