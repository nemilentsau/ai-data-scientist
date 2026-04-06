"""Run-state and top-level artifact publishing."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai_data_scientist.orchestration.models import InvocationContext, PublishContract, RunContext, SessionHandle


def _copy_declared_output(*, source_root: Path, destination_root: Path, relative_output: Path) -> Path | None:
    output_path = Path(relative_output)
    if output_path.is_absolute() or any(part == ".." for part in output_path.parts):
        raise ValueError(f"Declared output must be relative: {relative_output}")

    source_path = source_root / output_path
    if not source_path.exists():
        return None

    destination_path = destination_root / output_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
    else:
        shutil.copy2(source_path, destination_path)
    return destination_path


def _published_relative_path(role: str, relative_output: Path) -> Path:
    if role == "memory_curator" and relative_output.parts[:1] == ("memory",):
        return Path(*relative_output.parts[1:])
    return relative_output


def publish_top_level_outputs(context: RunContext, final_session: SessionHandle) -> None:
    """Publish the final session outputs and workspace artifacts to top-level paths."""
    if final_session.final_message_path.exists() and context.top_final_message_path is not None:
        shutil.copy2(final_session.final_message_path, context.top_final_message_path)

    if context.top_session_json_path is not None and final_session.session_output_path is not None:
        if final_session.session_output_path.exists():
            shutil.copy2(final_session.session_output_path, context.top_session_json_path)

    report_path = context.work_dir / "analysis_report.md"
    if report_path.exists():
        shutil.copy2(report_path, context.results_dir / "analysis_report.md")

    plots_dir = context.work_dir / "plots"
    if plots_dir.exists() and any(plots_dir.iterdir()):
        destination = context.results_dir / "plots"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(plots_dir, destination)

    for code_path in context.work_dir.glob("*.py"):
        shutil.copy2(code_path, context.results_dir / code_path.name)


def stage_declared_outputs(
    *,
    invocation: InvocationContext,
    contract: PublishContract,
) -> list[Path]:
    """Stage declared outputs from the private workspace into the output area."""
    staged: list[Path] = []
    for relative_output in contract.declared_outputs:
        staged_path = _copy_declared_output(
            source_root=invocation.work_dir,
            destination_root=invocation.output_dir,
            relative_output=relative_output,
        )
        if staged_path is not None:
            staged.append(staged_path)
    return staged


def publish_declared_outputs(
    *,
    run_dir: Path,
    invocation: InvocationContext,
    contract: PublishContract,
) -> list[Path]:
    """Publish only declared outputs from the invocation output staging area."""
    role_dirs = {
        "task_framer": "framing",
        "analysis_planner": "planning",
        "analysis_executor": "analysis",
        "method_critic": "critiques/method_critic",
        "visual_critic": "critiques/visual_critic",
        "verifier": "verification",
        "memory_curator": "memory",
    }
    destination_root = run_dir / "artifacts" / role_dirs[contract.role]
    destination_root.mkdir(parents=True, exist_ok=True)

    published: list[Path] = []
    for relative_output in contract.declared_outputs:
        source_output_path = Path(relative_output)
        if source_output_path.is_absolute() or any(part == ".." for part in source_output_path.parts):
            raise ValueError(f"Declared output must be relative: {relative_output}")

        source_path = invocation.output_dir / source_output_path
        if not source_path.exists():
            continue

        destination_relative_output = _published_relative_path(contract.role, source_output_path)
        destination_path = destination_root / destination_relative_output
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, destination_path)
        published.append(destination_path)
    return published


def write_run_state(context: RunContext) -> None:
    """Persist current run state for debugging and resumability."""
    payload = {
        "backend": context.backend,
        "dataset_name": context.dataset_name,
        "work_dir": str(context.work_dir),
        "results_dir": str(context.results_dir),
        "status": context.status,
        "error": context.error,
        "cleaned_up": context.cleaned_up,
        "completed_steps": list(context.completed_steps),
        "skipped_steps": list(context.skipped_steps),
        "matched_inputs": {
            step_id: [str(path.relative_to(context.work_dir)) for path in paths]
            for step_id, paths in context.matched_inputs.items()
        },
        "steps": {
            step_id: {
                "backend": handle.backend,
                "session_id": handle.session_id,
                "step_id": handle.step_id,
                "raw_trace_path": str(handle.raw_trace_path),
                "final_message_path": str(handle.final_message_path),
                "session_log_path": str(handle.session_log_path)
                if handle.session_log_path is not None
                else None,
                "session_output_path": str(handle.session_output_path)
                if handle.session_output_path is not None
                else None,
            }
            for step_id, handle in context.step_sessions.items()
        },
    }
    context.run_state_path.write_text(json.dumps(payload, indent=2))
