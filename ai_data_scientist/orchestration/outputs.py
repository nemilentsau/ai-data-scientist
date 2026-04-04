"""Run-state and top-level artifact publishing."""

from __future__ import annotations

import json
import shutil

from ai_data_scientist.orchestration.models import RunContext, SessionHandle


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

