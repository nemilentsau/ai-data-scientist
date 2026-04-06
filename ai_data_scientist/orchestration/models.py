"""Shared orchestration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TOOLS = ("Bash", "Read", "Write", "Edit", "Glob", "Grep")


@dataclass(frozen=True)
class RoleSpec:
    """Role configuration for the external orchestrator runtime."""

    role: str
    backend: str
    prompt: str
    model: str = ""
    tools: tuple[str, ...] = DEFAULT_TOOLS
    max_turns: int = 30


@dataclass(frozen=True)
class RuntimePolicy:
    """Workflow policy for bounded retries and memory curation."""

    max_revision_rounds: int = 1
    max_reframes: int = 1
    memory_curator: bool = True


@dataclass(frozen=True)
class OrchestratorSpec:
    """Normalized config for the external orchestrator runtime."""

    name: str
    description: str
    roles: dict[str, RoleSpec]
    runtime: RuntimePolicy

    @property
    def backend(self) -> str:
        raise TypeError(
            "OrchestratorSpec is not executable through the legacy workflow API; use roles + runtime."
        )

    @property
    def steps(self):
        raise TypeError(
            "OrchestratorSpec is not executable through the legacy workflow API; use roles + runtime."
        )


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


@dataclass(frozen=True)
class PublishContract:
    """Declared outputs a role may publish to the canonical run tree."""

    role: str
    declared_outputs: tuple[str, ...]


@dataclass(frozen=True)
class InvocationContext:
    """Private per-invocation workspace metadata.

    `work_dir` is the execution workspace. `output_dir` is the only staging
    area that may be published back into the canonical run tree.
    """

    invocation_id: str
    role: str
    root_dir: Path
    input_dir: Path
    work_dir: Path
    output_dir: Path
    logs_dir: Path
    trace_dir: Path
    manifest_path: Path


@dataclass(frozen=True)
class InvocationResult:
    """Outcome metadata from one invocation."""

    status: str
    final_message_path: Path | None = None
    raw_trace_path: Path | None = None


@dataclass(frozen=True)
class VerificationResult:
    """Parsed verifier outcome used to route the bounded loop."""

    verdict: str
    required_repairs: tuple[str, ...] = ()
    reframing_reasons: tuple[str, ...] = ()


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
    spec: OrchestratorSpec | None = None
    revision_rounds: int = 0
    reframes: int = 0

    def step_dir(self, step_id: str) -> Path:
        path = self.results_dir / "steps" / step_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class WorkflowExecutionError(RuntimeError):
    """Raised when a workflow cannot continue."""
