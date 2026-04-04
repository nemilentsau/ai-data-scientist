"""Shared orchestration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TOOLS = ("Bash", "Read", "Write", "Edit", "Glob", "Grep")


@dataclass(frozen=True)
class WorkflowStep:
    """One logical workflow step executed in the shared workspace."""

    id: str
    role: str
    prompt: str
    model: str = ""
    tools: tuple[str, ...] = DEFAULT_TOOLS
    max_turns: int = 30
    image_inputs: tuple[str, ...] = ()
    required: bool = True


@dataclass(frozen=True)
class WorkflowSpec:
    """Normalized workflow configuration."""

    name: str
    description: str
    backend: str
    steps: tuple[WorkflowStep, ...]


@dataclass(frozen=True)
class BackendCapabilities:
    """Backend behavior toggles used by the orchestrator."""

    supports_resume: bool
    supports_image_attachments: bool


@dataclass
class SessionHandle:
    """Backend session metadata for the current workflow thread."""

    backend: str
    session_id: str
    step_id: str
    raw_trace_path: Path
    final_message_path: Path
    session_log_path: Path | None = None
    session_output_path: Path | None = None


@dataclass
class RunContext:
    """Mutable run state shared across workflow steps."""

    root: Path
    dataset_name: str
    results_dir: Path
    work_dir: Path
    backend: str
    env: dict[str, str]
    top_trace_path: Path
    run_state_path: Path
    top_session_log_path: Path | None = None
    top_session_json_path: Path | None = None
    top_final_message_path: Path | None = None
    matched_inputs: dict[str, list[Path]] = field(default_factory=dict)
    step_sessions: dict[str, SessionHandle] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    status: str = "in_progress"
    error: str | None = None
    cleaned_up: bool = False

    def step_dir(self, step_id: str) -> Path:
        path = self.results_dir / "steps" / step_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class WorkflowExecutionError(RuntimeError):
    """Raised when a workflow cannot continue."""

