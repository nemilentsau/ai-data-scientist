"""Trace and session-log helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ai_data_scientist.orchestration.models import WorkflowExecutionError


def extract_codex_thread_id(trace_path: Path) -> str:
    """Extract the Codex thread id from the JSONL trace."""
    if not trace_path.exists():
        raise WorkflowExecutionError(f"Missing Codex trace file: {trace_path}")

    for line in trace_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started" and payload.get("thread_id"):
            return str(payload["thread_id"])

    raise WorkflowExecutionError(
        f"Codex trace {trace_path} does not contain a thread.started event."
    )


def append_trace(top_trace_path: Path, step_trace_path: Path) -> None:
    """Append step trace content into the top-level run trace."""
    if not step_trace_path.exists():
        return

    with top_trace_path.open("a") as top_trace, step_trace_path.open() as step_trace:
        for line in step_trace:
            top_trace.write(line)


def append_session_log(
    top_session_log_path: Path | None,
    step_id: str,
    session_log_path: Path,
) -> None:
    """Append step session logs into the top-level session log when present."""
    if top_session_log_path is None or not session_log_path.exists():
        return

    with top_session_log_path.open("a") as top_log, session_log_path.open() as step_log:
        top_log.write(f"=== step:{step_id} ===\n")
        for line in step_log:
            top_log.write(line)
        top_log.write("\n")

