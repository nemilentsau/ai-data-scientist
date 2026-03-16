#!/usr/bin/env python3
"""Benchmark orchestrator: generate datasets → run agents → score → report."""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATASETS_DIR = ROOT / "datasets" / "generated"
RESULTS_DIR = ROOT / "results"
HARNESS_DIR = ROOT / "harness"


def generate_datasets():
    """Generate all benchmark datasets."""
    print("=== Generating datasets ===")
    subprocess.run(
        [sys.executable, "-m", "datasets.generator"],
        cwd=ROOT,
        check=True,
    )
    print(f"Datasets generated in {DATASETS_DIR}\n")


def run_agent(agent: str, dataset_name: str, dataset_csv: Path, results_dir: Path):
    """Run a single agent on a single dataset."""
    script = HARNESS_DIR / f"run_{agent}.sh"
    if not script.exists():
        print(f"  WARNING: {script} not found, skipping {agent}")
        return False

    agent_results = results_dir / agent / dataset_name
    agent_results.mkdir(parents=True, exist_ok=True)

    print(f"  Running {agent} on {dataset_name}...")
    try:
        subprocess.run(
            ["bash", str(script), dataset_name, str(dataset_csv), str(agent_results)],
            timeout=600,  # 10 min timeout per analysis
            check=False,
        )
        return True
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: {agent} on {dataset_name} exceeded 10 minutes")
        return False
    except Exception as e:
        print(f"  ERROR: {agent} on {dataset_name}: {e}")
        return False


def score_results(dataset_names: list[str], agents: list[str], results_dir: Path):
    """Score all agent outputs."""
    print("\n=== Scoring results ===")
    from datasets.registry import get_dataset
    from reviewer.scorer import score_analysis

    all_scores = []
    for ds_name in dataset_names:
        metadata = get_dataset(ds_name)
        for agent in agents:
            agent_results = results_dir / agent / ds_name
            if not agent_results.exists():
                print(f"  No results for {agent}/{ds_name}, skipping")
                continue
            print(f"  Scoring {agent}/{ds_name}...")
            try:
                result = score_analysis(ds_name, agent, metadata, agent_results)
                all_scores.append(result)

                # Save individual score
                score_file = agent_results / "score.json"
                score_file.write_text(json.dumps({
                    "dataset": result.dataset_name,
                    "agent": result.agent,
                    "verdict": result.verdict,
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
                }, indent=2))
                print(
                    "    "
                    f"Verdict: {result.verdict}, "
                    f"required={result.required_coverage:.0%}, "
                    f"supporting={result.supporting_coverage:.0%}"
                )
            except Exception as e:
                print(f"    ERROR scoring {agent}/{ds_name}: {e}")

    return all_scores


def generate_report(scores, results_dir: Path):
    """Generate comparison report."""
    print("\n=== Generating report ===")
    from reviewer.report import generate_report as _generate_report

    report_path = results_dir / "benchmark_report.md"
    report = _generate_report(scores, report_path)
    print(f"Report saved to {report_path}")
    return report


def main():
    parser = argparse.ArgumentParser(description="AI Data Scientist Benchmark")
    parser.add_argument(
        "--datasets", nargs="*", default=None,
        help="Specific dataset names to run (default: all)",
    )
    parser.add_argument(
        "--agents", nargs="*", default=["claude", "codex"],
        choices=["claude", "codex"],
        help="Agents to benchmark (default: both)",
    )
    parser.add_argument(
        "--skip-generate", action="store_true",
        help="Skip dataset generation (use existing CSVs)",
    )
    parser.add_argument(
        "--skip-run", action="store_true",
        help="Skip agent runs (use existing results)",
    )
    parser.add_argument(
        "--skip-score", action="store_true",
        help="Skip scoring (use existing scores)",
    )
    parser.add_argument(
        "--results-dir", type=Path, default=RESULTS_DIR,
        help="Results directory",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Benchmark run: {timestamp}")
    print(f"Agents: {args.agents}")

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

    # Step 2: Run agents
    if not args.skip_run:
        print("=== Running agents ===")
        from datasets.generator import NAME_TO_FILENAME
        for ds_name in dataset_names:
            csv_path = DATASETS_DIR / NAME_TO_FILENAME.get(ds_name, f"{ds_name}.csv")
            if not csv_path.exists():
                print(f"  WARNING: {csv_path} not found, skipping")
                continue
            for agent in args.agents:
                run_agent(agent, ds_name, csv_path, args.results_dir)

    # Step 3: Score
    if not args.skip_score:
        scores = score_results(dataset_names, args.agents, args.results_dir)

        # Step 4: Report
        if scores:
            generate_report(scores, args.results_dir)
    else:
        print("Scoring skipped.")

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
