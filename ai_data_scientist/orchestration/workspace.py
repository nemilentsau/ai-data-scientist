"""Shared workspace preparation."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_data_scientist.orchestration.models import (
    InvocationContext,
    RoleSpec,
    RunContext,
    WorkflowStep,
)
from ai_data_scientist.orchestration.ledgers import collect_memory_inputs

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

ROLE_INPUT_ARTIFACT_DIRS: dict[str, tuple[str, ...]] = {
    "task_framer": ("profile",),
    "analysis_planner": ("profile", "framing"),
    "analysis_executor": ("dataset", "profile", "framing", "planning"),
}
FULL_PUBLISHED_ARTIFACT_ROLES = {
    "method_critic",
    "visual_critic",
    "verifier",
    "memory_curator",
}


def _role_invocation_prefix(role: RoleSpec) -> str:
    return role.role.replace("_", "-")


def _next_invocation_id(run_dir: Path, role: RoleSpec) -> str:
    invocations_dir = run_dir / "invocations"
    invocations_dir.mkdir(parents=True, exist_ok=True)

    prefix = _role_invocation_prefix(role)
    highest_seen = 0
    for candidate in invocations_dir.iterdir():
        if not candidate.is_dir() or not candidate.name.startswith(f"{prefix}-"):
            continue
        suffix = candidate.name[len(prefix) + 1 :]
        if suffix.isdigit():
            highest_seen = max(highest_seen, int(suffix))

    counter = highest_seen + 1
    while True:
        invocation_id = f"{prefix}-{counter:04d}"
        if not (invocations_dir / invocation_id).exists():
            return invocation_id
        counter += 1


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


def create_invocation_context(
    *,
    run_dir: Path,
    role: RoleSpec,
    artifact_inputs: list[Path],
) -> InvocationContext:
    """Create a private workspace for one role invocation and materialize inputs."""
    invocation_id = _next_invocation_id(run_dir, role)
    root_dir = run_dir / "invocations" / invocation_id
    input_dir = root_dir / "input"
    work_dir = root_dir / "workspace"
    output_dir = root_dir / "output"
    logs_dir = root_dir / "logs"
    trace_dir = root_dir / "trace"
    for path in (input_dir, work_dir, output_dir, logs_dir, trace_dir):
        path.mkdir(parents=True, exist_ok=True)

    for source_path in artifact_inputs:
        relative_path = source_path.relative_to(run_dir)
        destination = input_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

    return InvocationContext(
        invocation_id=invocation_id,
        role=role.role,
        root_dir=root_dir,
        input_dir=input_dir,
        work_dir=work_dir,
        output_dir=output_dir,
        logs_dir=logs_dir,
        trace_dir=trace_dir,
        manifest_path=root_dir / "manifest.json",
    )


def resolve_role_inputs(run_dir: Path, role_name: str) -> list[Path]:
    """Collect published artifact files for a role invocation."""
    if role_name in FULL_PUBLISHED_ARTIFACT_ROLES:
        return collect_memory_inputs(run_dir)

    artifact_root = run_dir / "artifacts"
    role_dirs = ROLE_INPUT_ARTIFACT_DIRS.get(role_name)
    if role_dirs is None:
        raise ValueError(f"Unsupported role for input resolution: {role_name}")

    matches: list[Path] = []
    seen: set[Path] = set()
    for dir_name in role_dirs:
        candidate_root = artifact_root / dir_name
        if not candidate_root.exists():
            continue
        for path in sorted(candidate_root.rglob("*")):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            matches.append(path)
    return matches


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
