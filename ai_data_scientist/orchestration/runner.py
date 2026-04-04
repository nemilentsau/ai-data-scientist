"""Workflow execution entrypoint."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ai_data_scientist.orchestration.adapters.base import BackendAdapter
from ai_data_scientist.orchestration.adapters.claude_cli import ClaudeCliAdapter
from ai_data_scientist.orchestration.adapters.codex_cli import CodexCliAdapter
from ai_data_scientist.orchestration.config import normalize_workflow_config
from ai_data_scientist.orchestration.models import SessionHandle, WorkflowExecutionError
from ai_data_scientist.orchestration.outputs import publish_top_level_outputs, write_run_state
from ai_data_scientist.orchestration.trace import append_session_log, append_trace
from ai_data_scientist.orchestration.workspace import prepare_run_context, resolve_step_image_inputs

BACKEND_ADAPTERS: dict[str, type[BackendAdapter]] = {
    "codex_cli": CodexCliAdapter,
    "claude_cli": ClaudeCliAdapter,
}


def get_backend_adapter(backend: str, root: Path) -> BackendAdapter:
    """Instantiate a backend adapter from the registry."""
    adapter_cls = BACKEND_ADAPTERS.get(backend)
    if adapter_cls is None:
        raise ValueError(f"Unsupported backend: {backend}")
    return adapter_cls(root)


def run_workflow(
    *,
    config: dict[str, Any],
    dataset_name: str,
    dataset_csv: Path,
    results_dir: Path,
    root: Path,
) -> bool:
    """Run a normalized workflow against one dataset."""
    spec = normalize_workflow_config(config)
    context = prepare_run_context(
        root=root,
        dataset_name=dataset_name,
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        backend=spec.backend,
    )
    adapter = get_backend_adapter(spec.backend, root)
    adapter.prepare_context(context)
    session: SessionHandle | None = None
    succeeded = False
    write_run_state(context)

    try:
        for step in spec.steps:
            image_paths = resolve_step_image_inputs(context, step)
            if step.image_inputs and not image_paths:
                if step.required:
                    raise WorkflowExecutionError(
                        f"Required step '{step.id}' matched no image inputs: {step.image_inputs}."
                    )
                context.skipped_steps.append(step.id)
                write_run_state(context)
                continue

            handle = (
                adapter.start_step(step, context)
                if session is None
                else adapter.continue_step(step, context, session)
            )
            adapter.collect_step_outputs(step, context, handle)
            context.step_sessions[step.id] = handle
            context.completed_steps.append(step.id)
            append_trace(context.top_trace_path, handle.raw_trace_path)
            if handle.session_log_path is not None:
                append_session_log(context.top_session_log_path, step.id, handle.session_log_path)
            session = handle
            write_run_state(context)

        if session is not None:
            publish_top_level_outputs(context, session)
        context.status = "completed"
        succeeded = True
    except (ValueError, WorkflowExecutionError) as exc:
        context.status = "failed"
        context.error = str(exc)
    finally:
        write_run_state(context)
        shutil.rmtree(context.work_dir, ignore_errors=True)
        context.cleaned_up = True
        write_run_state(context)

    return succeeded
