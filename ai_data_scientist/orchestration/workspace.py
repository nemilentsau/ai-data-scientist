"""Shared workspace preparation."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_data_scientist.orchestration.models import RunContext, WorkflowStep

BENCHMARK_VENV_DIRNAME = ".benchmark-venv"
SHARED_PACKAGES = (
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "matplotlib",
    "seaborn",
    "statsmodels",
    "lifelines",
)


def ensure_shared_benchmark_venv(root: Path) -> Path:
    """Create a shared benchmark virtualenv with the common DS stack."""
    venv_dir = root / BENCHMARK_VENV_DIRNAME
    python_path = venv_dir / "bin" / "python"

    if not python_path.exists():
        subprocess.run(
            ["uv", "venv", str(venv_dir), "--python", "3.14", "--quiet"],
            cwd=root,
            check=True,
        )

    check_script = (
        "mods = "
        + repr(list(SHARED_PACKAGES))
        + "\nfor mod in mods:\n    __import__(mod)\n"
    )
    module_check = subprocess.run(
        [str(python_path), "-c", check_script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if module_check.returncode != 0:
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python_path),
                "--quiet",
                "numpy",
                "pandas",
                "scipy",
                "scikit-learn",
                "matplotlib",
                "seaborn",
                "statsmodels",
                "lifelines",
            ],
            cwd=root,
            check=True,
        )

    return venv_dir


def prepare_run_context(
    *,
    root: Path,
    dataset_name: str,
    dataset_csv: Path,
    results_dir: Path,
    backend: str,
) -> RunContext:
    """Prepare the shared temp workspace and base environment."""
    benchmark_venv = ensure_shared_benchmark_venv(root)
    work_dir = Path(tempfile.mkdtemp())
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "steps").mkdir(parents=True, exist_ok=True)

    shutil.copy2(dataset_csv, work_dir / "dataset.csv")
    (work_dir / "plots").mkdir(exist_ok=True)
    (work_dir / ".matplotlib").mkdir(exist_ok=True)
    (work_dir / ".venv").symlink_to(benchmark_venv, target_is_directory=True)

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(work_dir / ".venv")
    env["PATH"] = f"{work_dir / '.venv' / 'bin'}:{env.get('PATH', '')}"
    env["MPLCONFIGDIR"] = str(work_dir / ".matplotlib")

    return RunContext(
        root=root,
        dataset_name=dataset_name,
        results_dir=results_dir,
        work_dir=work_dir,
        backend=backend,
        env=env,
        top_trace_path=results_dir / "trace.jsonl",
        run_state_path=results_dir / "run_state.json",
        top_final_message_path=results_dir / "final_message.md",
    )


def resolve_step_image_inputs(context: RunContext, step: WorkflowStep) -> list[Path]:
    """Resolve relative glob patterns for a step inside the shared workspace."""
    matches: list[Path] = []
    seen: set[Path] = set()

    for pattern in step.image_inputs:
        for path in sorted(context.work_dir.glob(pattern)):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                matches.append(path)

    context.matched_inputs[step.id] = matches
    return matches

